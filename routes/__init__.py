from flask import Blueprint

# Import individual route modules
from .waitlist_routes import  waitlist_bp

# Create a function to register all blueprints
def register_routes(app):
    app.register_blueprint(waitlist_bp)
    
