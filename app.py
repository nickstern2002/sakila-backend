from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flask_backend:Flask%40123@localhost/sakila'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Import blueprints (ensure these imports come after db is created to avoid circular dependencies)
from landing import landing_bp
from films import films_bp
from admin import admin_bp

# Register blueprints
app.register_blueprint(landing_bp)
app.register_blueprint(films_bp)
app.register_blueprint(admin_bp)


if __name__ == '__main__':
    app.run(debug=True)
