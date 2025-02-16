from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS

app = Flask(__name__)

CORS(app, origins=["http://localhost:3000"])
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flask_backend:Flask%40123@localhost/sakila'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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


@app.route('/')
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

@app.route('/film/<int:film_id>', methods=['GET'])
def film_details(film_id):
    """Fetch details for a specific film."""
    try:
        query = text("""
            SELECT f.film_id, f.title, f.description, f.release_year, l.name AS language, f.rating
            FROM film f
            JOIN language l ON f.language_id = l.language_id
            WHERE f.film_id = :film_id
        """)
        result = db.session.execute(query, {"film_id": film_id}).mappings().fetchone()
        
        if not result:
            return jsonify({"error": "Film not found"}), 404
        
        return jsonify(dict(result))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/actor/<int:actor_id>', methods=['GET'])
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

