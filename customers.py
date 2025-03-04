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

@customers_bp.route("/<int:customer_id>", methods=["GET"])
def get_customer_details(customer_id):
    """Retrieves customer details along with their rental history."""
    try:
        # Fetch customer details
        customer_query = text("""
            SELECT c.customer_id, c.first_name, c.last_name, c.email, 
                   c.store_id, c.active, a.address, a.address2, 
                   a.district, a.postal_code, a.phone
            FROM sakila.customer c
            JOIN sakila.address a ON c.address_id = a.address_id
            WHERE c.customer_id = :customer_id
        """)
        customer_result = db.session.execute(customer_query, {"customer_id": customer_id}).mappings().fetchone()

        if not customer_result:
            return jsonify({"error": "Customer not found"}), 404

        customer_details = dict(customer_result)

        # Fetch rental history for the customer
        rental_query = text("""
            SELECT r.rental_id, f.film_id, f.title, r.rental_date, r.return_date
            FROM sakila.rental r
            JOIN sakila.inventory i ON r.inventory_id = i.inventory_id
            JOIN sakila.film f ON i.film_id = f.film_id
            WHERE r.customer_id = :customer_id
            ORDER BY r.rental_date DESC
        """)
        rental_results = db.session.execute(rental_query, {"customer_id": customer_id}).mappings().all()

        customer_details["rental_history"] = [dict(row) for row in rental_results]

        return jsonify(customer_details)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@customers_bp.route("/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id):
    """Updates a customer's details including address information."""
    try:
        data = request.get_json()

        # Extract customer details
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        store_id = data.get("store_id")  # Must be 1 or 2

        # Extract address details
        address = data.get("address")
        address2 = data.get("address2", None)  # Optional
        district = data.get("district")
        city_id = data.get("city_id")  # Must exist
        postal_code = data.get("postal_code")
        phone = data.get("phone")

        if not all([first_name, last_name, store_id, address, district, city_id, postal_code, phone]):
            return jsonify({"error": "Missing required fields"}), 400

        # Start transaction
        with db.session.begin():
            # Update customer details
            update_customer_query = text("""
                UPDATE sakila.customer 
                SET first_name = :first_name, last_name = :last_name, email = :email, store_id = :store_id
                WHERE customer_id = :customer_id
            """)
            db.session.execute(update_customer_query, {
                "customer_id": customer_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "store_id": store_id
            })

            # Get customer's address_id
            address_id_query = text("""
                SELECT address_id FROM sakila.customer WHERE customer_id = :customer_id
            """)
            address_id = db.session.execute(address_id_query, {"customer_id": customer_id}).scalar()

            if address_id:
                # Update address details
                update_address_query = text("""
                    UPDATE sakila.address 
                    SET address = :address, address2 = :address2, district = :district, city_id = :city_id, 
                        postal_code = :postal_code, phone = :phone
                    WHERE address_id = :address_id
                """)
                db.session.execute(update_address_query, {
                    "address_id": address_id,
                    "address": address,
                    "address2": address2,
                    "district": district,
                    "city_id": city_id,
                    "postal_code": postal_code,
                    "phone": phone
                })

        return jsonify({"message": "Customer updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@customers_bp.route("/return_rental/<int:rental_id>", methods=["PUT"])
def return_rental(rental_id):
    """Marks a rental as returned by setting the return_date to the current timestamp."""
    try:
        # Check if the rental exists and hasn't been returned yet
        rental_check_query = text("""
            SELECT return_date FROM sakila.rental WHERE rental_id = :rental_id
        """)
        rental_result = db.session.execute(rental_check_query, {"rental_id": rental_id}).fetchone()

        if not rental_result:
            return jsonify({"error": "Rental not found"}), 404

        # If return_date is already set, the rental has been returned
        if rental_result[0] is not None:
            return jsonify({"error": "Rental already returned"}), 400

        # Update rental with return_date as current timestamp
        update_rental_query = text("""
            UPDATE sakila.rental 
            SET return_date = NOW() 
            WHERE rental_id = :rental_id
        """)
        db.session.execute(update_rental_query, {"rental_id": rental_id})
        db.session.commit()

        return jsonify({"message": "Rental returned successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

