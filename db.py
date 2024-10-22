from flask_sqlalchemy import SQLAlchemy 

sqldb = SQLAlchemy()

def init_app(app):
    sqldb.init_app(app)
    with app.app_context():
        sqldb.create_all()
