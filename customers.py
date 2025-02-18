from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app import db

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")

@customers_bp.route("/", methods=["GET"])
def get_customers():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = 5
        offset = (page - 1) * per_page

        query = text("""
            SELECT customer_id, first_name, last_name, email, store_id, active
            FROM sakila.customer
            ORDER BY customer_id DESC
            LIMIT :per_page OFFSET :offset
        """)
        
        result = db.session.execute(query, {"per_page": per_page, "offset": offset}).mappings().all()
        customers = [dict(row) for row in result]

        total_query = text("SELECT COUNT(*) FROM sakila.customer")
        total_customers = db.session.execute(total_query).scalar()
        has_next = (page * per_page) < total_customers

        return jsonify({
            "customers": customers,
            "has_next": has_next,
            "current_page": page
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
