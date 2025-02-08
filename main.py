from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flask_backend:Flask%40123@localhost/sakila'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.route('/')
def landing_page():
    try:
        # Query for top 5 rented films
        top_films_query = text("""
            SELECT f.film_id, f.title, COUNT(r.rental_id) AS rental_count
            FROM film f
            JOIN inventory i ON f.film_id = i.film_id
            JOIN rental r ON i.inventory_id = r.inventory_id
            GROUP BY f.film_id, f.title
            ORDER BY rental_count DESC
            LIMIT 5
        """)
        top_films_result = db.session.execute(top_films_query)
        top_films = [dict(row) for row in top_films_result]

        # Query for top 5 actors
        top_actors_query = text("""
            SELECT a.actor_id, a.first_name, a.last_name, COUNT(fa.film_id) AS film_count
            FROM actor a
            JOIN film_actor fa ON a.actor_id = fa.actor_id
            GROUP BY a.actor_id, a.first_name, a.last_name
            ORDER BY film_count DESC
            LIMIT 5
        """)
        top_actors_result = db.session.execute(top_actors_query)
        top_actors = [dict(row) for row in top_actors_result]

        return jsonify({
            "top_rented_films": top_films,
            "top_actors": top_actors
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
