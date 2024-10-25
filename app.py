from flask import Flask
from db import init_app
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///waitlist.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get("APP_SECRET")

    init_app(app)

    from routes import register_routes
    register_routes(app)
    
    return app

if __name__ == "__main__":
    app = create_app()   
    app.run(debug=False)
