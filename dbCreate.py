from app import create_app
from db import sqldb

app = create_app()

with app.app_context():
    sqldb.create_all()  # This will create all the tables based on your defined models.