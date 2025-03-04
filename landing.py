from flask import Blueprint, jsonify
from sqlalchemy import text
from app import db  # Import the db from the main app

landing_bp = Blueprint('landing', __name__)

def get_top_rented_films():
    """Fetch the top 5 most rented films."""
    query = text("""
        SELECT f.film_id, f.title, COUNT(r.rental_id) AS rental_count
        FROM film f
        JOIN inventory i ON f.film_id = i.film_id
        JOIN rental r ON i.inventory_id = r.inventory_id
        GROUP BY f.film_id, f.title
        ORDER BY rental_count DESC
        LIMIT 5
    """)
    result = db.session.execute(query).mappings().all()
    return [dict(row) for row in result]

def get_top_actors():
    """Fetch the top 5 actors with the most films in the store."""
    query = text("""
        SELECT a.actor_id, a.first_name, a.last_name, COUNT(fa.film_id) AS film_count
        FROM actor a
        JOIN film_actor fa ON a.actor_id = fa.actor_id
        GROUP BY a.actor_id, a.first_name, a.last_name
        ORDER BY film_count DESC
        LIMIT 5
    """)
    result = db.session.execute(query).mappings().all()
    return [dict(row) for row in result]

@landing_bp.route('/')
def landing_page():
    try:
        top_rented_films = get_top_rented_films()
        top_actors = get_top_actors()
        
        return jsonify({
            "top_rented_films": top_rented_films,
            "top_actors": top_actors,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
