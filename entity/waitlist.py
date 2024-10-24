from datetime import datetime
from db import sqldb

class WaitlistEntry(sqldb.Model):
    __tablename__ = 'waitlist_entries'

    id = sqldb.Column(sqldb.Integer, primary_key=True)
    unique_code = sqldb.Column(sqldb.String(36), nullable=False, unique=True)
    email = sqldb.Column(sqldb.String(120), nullable=False, unique=True)
    phone_number = sqldb.Column(sqldb.String(15), nullable=False) 
    ip_address = sqldb.Column(sqldb.String(45), nullable=False, unique=True)
    visit_count = sqldb.Column(sqldb.Integer, default=0)
    reffered_by = sqldb.Column(sqldb.String(120))
    created_at = sqldb.Column(sqldb.DateTime, default=datetime.utcnow)
    in_waitlist = sqldb.Column(sqldb.Boolean, default=False)
    message = sqldb.Column(sqldb.Text, nullable=True)


    def __repr__(self):
        return f'<WaitlistEntry {self.email}>'