from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app import db

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")


@customers_bp.route("/", methods=["GET"])
def get_customers():
    """Retrieves paginated customers with optional search filters."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = 5
        offset = (page - 1) * per_page

        # Base query
        query = """
            SELECT customer_id, first_name, last_name, email, store_id, active
            FROM sakila.customer
            WHERE 1=1
        """
        params = {}

        # Add filters if search parameters exist
        customer_id = request.args.get("customer_id", type=int)
        first_name = request.args.get("first_name", "")
        last_name = request.args.get("last_name", "")

        if customer_id:
            query += " AND customer_id = :customer_id"
            params["customer_id"] = customer_id
        if first_name:
            query += " AND first_name LIKE :first_name"
            params["first_name"] = f"%{first_name}%"
        if last_name:
            query += " AND last_name LIKE :last_name"
            params["last_name"] = f"%{last_name}%"

        # Apply ordering, pagination
        query += " ORDER BY customer_id DESC LIMIT :per_page OFFSET :offset"
        params["per_page"] = per_page
        params["offset"] = offset

        result = db.session.execute(text(query), params).mappings().all()
        customers = [dict(row) for row in result]

        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM sakila.customer WHERE 1=1"
        if customer_id:
            count_query += " AND customer_id = :customer_id"
        if first_name:
            count_query += " AND first_name LIKE :first_name"
        if last_name:
            count_query += " AND last_name LIKE :last_name"

        total_customers = db.session.execute(text(count_query), params).scalar()
        has_next = (page * per_page) < total_customers

        return jsonify({
            "customers": customers,
            "has_next": has_next,
            "current_page": page
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@customers_bp.route("/", methods=["POST"])
def add_customer():
    """Adds a new customer with a new address (if needed)."""
    try:
        data = request.get_json()

        # Customer details
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        store_id = data.get("store_id")  # Must be 1 or 2

        # Address details
        address = data.get("address")
        address2 = data.get("address2") or None  # Optional
        district = data.get("district")
        city_id = data.get("city_id")  # Must already exist
        postal_code = data.get("postal_code")
        phone = data.get("phone")

        if not all([first_name, last_name, store_id, address, district, city_id, postal_code, phone]):
            return jsonify({"error": "Missing required fields"}), 400

        # Start a transaction
        with db.session.begin():
            # Insert into address table
            insert_address_query = text("""
                INSERT INTO sakila.address (address, address2, district, city_id, postal_code, phone, location)
                VALUES (:address, :address2, :district, :city_id, :postal_code, :phone, ST_GeomFromText('POINT(0 0)'))
            """)

            db.session.execute(insert_address_query, {
                "address": address,
                "address2": address2,
                "district": district,
                "city_id": city_id,
                "postal_code": postal_code,
                "phone": phone,
            })

            # Retrieve the new address_id
            address_id_query = text("SELECT LAST_INSERT_ID()")
            address_id = db.session.execute(address_id_query).scalar()

            # Insert into customer table
            insert_customer = text("""
                INSERT INTO sakila.customer (store_id, first_name, last_name, email, address_id, active, create_date)
                VALUES (:store_id, :first_name, :last_name, :email, :address_id, 1, NOW())
            """)
            db.session.execute(insert_customer, {
                "store_id": store_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "address_id": address_id
            })

            # Retrieve the new customer_id
            customer_id_query = text("SELECT LAST_INSERT_ID()")
            customer_id = db.session.execute(customer_id_query).scalar()

        return jsonify({
            "message": "Customer added successfully",
            "customer_id": customer_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@customers_bp.route("/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    """Deletes a customer and their associated rentals and payments."""
    try:
        # Start a transaction
        with db.session.begin():
            # Step 1: Delete payments related to the customer
            delete_payments = text("DELETE FROM sakila.payment WHERE customer_id = :customer_id")
            db.session.execute(delete_payments, {"customer_id": customer_id})

            # Step 2: Delete rentals related to the customer
            delete_rentals = text("DELETE FROM sakila.rental WHERE customer_id = :customer_id")
            db.session.execute(delete_rentals, {"customer_id": customer_id})

            # Step 3: Delete the customer
            delete_customer_query = text("DELETE FROM sakila.customer WHERE customer_id = :customer_id")
            result = db.session.execute(delete_customer_query, {"customer_id": customer_id})

            # Check if a customer was actually deleted
            if result.rowcount == 0:
                return jsonify({"error": "Customer not found"}), 404

        return jsonify({"message": "Customer deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
