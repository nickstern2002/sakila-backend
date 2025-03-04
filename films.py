from flask import Blueprint, jsonify, request
from sqlalchemy import text
from app import db  # Import the db from the main app

films_bp = Blueprint('films', __name__)

@films_bp.route('/film/<int:film_id>', methods=['GET'])
def film_details(film_id):
    """Fetch details for a specific film along with its actors."""
    try:
        # Fetch film details
        film_query = text("""
            SELECT f.film_id, f.title, f.description, f.release_year, l.name AS language, f.rating
            FROM film f
            JOIN language l ON f.language_id = l.language_id
            WHERE f.film_id = :film_id
        """)
        film_result = db.session.execute(film_query, {"film_id": film_id}).mappings().fetchone()
        
        if not film_result:
            return jsonify({"error": "Film not found"}), 404

        film_details = dict(film_result)

        # Fetch actors for the film
        actor_query = text("""
            SELECT a.actor_id, a.first_name, a.last_name
            FROM actor a
            JOIN film_actor fa ON a.actor_id = fa.actor_id
            WHERE fa.film_id = :film_id
        """)
        actor_results = db.session.execute(actor_query, {"film_id": film_id}).mappings().all()
        film_details["actors"] = [dict(row) for row in actor_results]

        return jsonify(film_details)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@films_bp.route('/actor/<int:actor_id>', methods=['GET'])
def actor_details(actor_id):
    """Fetch details for a specific actor and their top 5 rented films."""
    try:
        # Query for actor details
        actor_query = text("""
            SELECT a.actor_id, a.first_name, a.last_name, COUNT(fa.film_id) AS film_count
            FROM actor a
            JOIN film_actor fa ON a.actor_id = fa.actor_id
            WHERE a.actor_id = :actor_id
            GROUP BY a.actor_id, a.first_name, a.last_name
        """)
        actor_result = db.session.execute(actor_query, {"actor_id": actor_id}).mappings().fetchone()

        if not actor_result:
            return jsonify({"error": "Actor not found"}), 404
        
        # Query for top 5 rented films by the actor
        films_query = text("""
            SELECT f.film_id, f.title, COUNT(r.rental_id) AS rental_count
            FROM film f
            JOIN film_actor fa ON f.film_id = fa.film_id
            JOIN inventory i ON f.film_id = i.film_id
            JOIN rental r ON i.inventory_id = r.inventory_id
            WHERE fa.actor_id = :actor_id
            GROUP BY f.film_id, f.title
            ORDER BY rental_count DESC
            LIMIT 5
        """)
        films_result = db.session.execute(films_query, {"actor_id": actor_id}).mappings().all()
        
        # Combine actor details with their top 5 films
        actor_details = dict(actor_result)
        actor_details["top_rented_films"] = [dict(row) for row in films_result]
        
        return jsonify(actor_details)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@films_bp.route('/films', methods=['GET'])
def search_films():
    """
    Search films by film title, actor name, and/or genre.
    Query parameters:
      - film: (partial) film title
      - actor: (partial) actor's first or last name
      - genre: (partial) genre name
    """
    film = request.args.get('film', '')
    actor = request.args.get('actor', '')
    genre = request.args.get('genre', '')
    
    # Base SQL query
    query = """
        SELECT DISTINCT f.film_id, f.title, f.release_year, g.name AS genre
        FROM film f
        LEFT JOIN film_actor fa ON f.film_id = fa.film_id
        LEFT JOIN actor a ON fa.actor_id = a.actor_id
        LEFT JOIN film_category fc ON f.film_id = fc.film_id
        LEFT JOIN category g ON fc.category_id = g.category_id
        WHERE 1=1
    """
    
    params = {}
    if film:
        query += " AND f.title LIKE :film"
        params['film'] = f"%{film}%"
    if actor:
        query += " AND (a.first_name LIKE :actor OR a.last_name LIKE :actor)"
        params['actor'] = f"%{actor}%"
    if genre:
        query += " AND g.name LIKE :genre"
        params['genre'] = f"%{genre}%"
    
    query += " LIMIT 50"
    
    try:
        result = db.session.execute(text(query), params).mappings().all()
        films = [dict(row) for row in result]
        return jsonify(films)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@films_bp.route('/rentals/rent', methods=['POST'])
def rent_film():
    """Handles renting a film to a customer."""
    try:
        data = request.get_json()
        customer_id = data.get("customer_id")
        film_id = data.get("film_id")

        if not customer_id or not film_id:
            return jsonify({"error": "Missing customer_id or film_id"}), 400

        # Check if there's an available copy of the film
        availability_query = text("""
            SELECT i.inventory_id FROM inventory i
            LEFT JOIN rental r ON i.inventory_id = r.inventory_id AND r.return_date IS NULL
            WHERE i.film_id = :film_id AND r.inventory_id IS NULL
            LIMIT 1
        """)
        inventory_result = db.session.execute(availability_query, {"film_id": film_id}).mappings().fetchone()

        if not inventory_result:
            return jsonify({"error": "No available copies for this film"}), 400

        inventory_id = inventory_result["inventory_id"]

        # Insert rental record
        rent_query = text("""
            INSERT INTO rental (rental_date, inventory_id, customer_id, return_date, staff_id)
            VALUES (NOW(), :inventory_id, :customer_id, NULL, 1)
        """)
        db.session.execute(rent_query, {"inventory_id": inventory_id, "customer_id": customer_id})
        db.session.commit()

        return jsonify({"message": "Rental successful", "inventory_id": inventory_id}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
