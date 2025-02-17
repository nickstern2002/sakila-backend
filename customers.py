from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app import db

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")

# Retrieve a paginated list of customers
@customers_bp.route("/", methods=["GET"])
def get_customers():
    try:
        page = request.args.get("page", 1, type=int)  # Get page number, default is 1
        per_page = 5  # Number of customers per page
        offset = (page - 1) * per_page  # Calculate offset

        query = text("""
            SELECT customer_id, first_name, last_name, email, phone, created_at
            FROM film_store.customers
            ORDER BY created_at DESC
            LIMIT :per_page OFFSET :offset
        """)
        
        result = db.session.execute(query, {"per_page": per_page, "offset": offset}).mappings().all()
        customers = [dict(row) for row in result]

        # Check if there's a next page
        total_query = text("SELECT COUNT(*) FROM film_store.customers")
        total_customers = db.session.execute(total_query).scalar()
        has_next = (page * per_page) < total_customers

        return jsonify({
            "customers": customers,
            "has_next": has_next,
            "current_page": page
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Add a new customer
@customers_bp.route("/", methods=["POST"])
def add_customer():
    try:
        data = request.get_json()
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        phone = data.get("phone")

        if not first_name or not last_name:
            return jsonify({"error": "First and last name are required"}), 400

        insert_query = text("""
            INSERT INTO film_store.customers (first_name, last_name, email, phone)
            VALUES (:first_name, :last_name, :email, :phone)
        """)

        db.session.execute(insert_query, {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone
        })
        db.session.commit()

        return jsonify({"message": "Customer added successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
