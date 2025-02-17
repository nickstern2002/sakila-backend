# admin.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app import db  # assuming your main app sets up the SQLAlchemy instance as db

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    # Query the admin_users table in the admin_db database
    query = text("SELECT * FROM film_store.admin_users WHERE username = :username AND password = :password")
    result = db.session.execute(query, {"username": username, "password": password}).mappings().fetchone()
    
    if result:
        return jsonify({"message": "Login successful", "admin": dict(result)})
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@admin_bp.route('/add', methods=['POST'])
def add_admin():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    try:
        insert_query = text("INSERT INTO film_store.admin_users (username, password) VALUES (:username, :password)")
        db.session.execute(insert_query, {"username": username, "password": password})
        db.session.commit()
        return jsonify({"message": "New admin account created successfully."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

