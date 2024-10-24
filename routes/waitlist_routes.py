from flask import request, jsonify, Blueprint, session 
from db import sqldb  # Ensure you import your sqldb instance
from entity.waitlist import WaitlistEntry
import logging, random, string, hashlib
import csv, os
from io import StringIO
from flask import Response

log = logging.getLogger(__name__)

WL_API_KEY = os.getenv("WL_API_KEY")

def get_client_ip():
    # Check if the request went through a proxy, e.g., Cloudflare or a load balancer
    if request.headers.getlist('X-Forwarded-For'):
        # X-Forwarded-For contains a list of IPs, the first one is the client's real IP
        ip = request.headers.getlist('X-Forwarded-For')[0]
    else:
        # Fallback to get_client_ip() if no proxy is involved
        ip = request.remote_addr
    return ip

def generate_unique_key(email):
    """Generate a unique key starting with 'KYU' based on the email and followed by 1-3 random alphanumeric characters."""
    prefix = "KYU"

    # Create a base key using a hash of the email
    email_hash = hashlib.md5(email.encode()).hexdigest()  # Create a hash of the email
    # Use part of the hash to ensure randomness
    base_key = email_hash[:3].upper()  # Take the first 3 characters of the hash

    # Generate a random suffix length between 1 and 3 characters
    length = random.randint(1, 3)
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    # Create the unique code
    unique_code = prefix + base_key + random_suffix

    # Check for uniqueness in the database
    checkForUniqueCode = WaitlistEntry.query.filter_by(unique_code=unique_code).first()
    if checkForUniqueCode:
        return generate_unique_key(email)  # Recursive call to ensure uniqueness
    return unique_code

waitlist_bp = Blueprint("waitlist", __name__)

@waitlist_bp.route('/waitlist', methods=['GET', 'POST'])
def waitlist():
    user_ip = get_client_ip()
    if request.method == 'POST':
        referral_code = request.args.get("refferal_code")
        email = request.args.get("email")

        if not email:
            return jsonify({"message": "Email is missing"}), 400
        
        # Check if the email already exists in the waitlist
        existingEntry: WaitlistEntry = WaitlistEntry.query.filter_by(email=email).first() or WaitlistEntry.query.filter_by(ip_address=user_ip).first()
        if existingEntry:
            return jsonify({
                "message": "User already exists.",
                "email": existingEntry.email,
                "unique_code": existingEntry.unique_code
            }), 302

        unique_code = str(generate_unique_key(email))
        
        # Initialize reffered_by as None initially
        reffered_by = None
        
        # Call verify_code to check the referral_code
        verify_code_response, status_code = verify_code(referral_code, incrementVisitCount = False)
        if status_code == 200 and not verify_code_response.get("sameUser"):
            reffered_by = verify_code_response.get('email')

        # Create a new waitlist entry
        new_entry = WaitlistEntry(
            unique_code=unique_code, 
            ip_address=user_ip, 
            email=email, 
            reffered_by=reffered_by
        )
        sqldb.session.add(new_entry)
        sqldb.session.commit()

        session['unique_code'] = unique_code

        return jsonify({
            "message": "New waitlist entry created",
            "unique_code": unique_code,
            "email": email
        }), 201

    # If the request is GET
    entry:WaitlistEntry = None
    unique_code = session.get('unique_code')
    if unique_code:
        entry = WaitlistEntry.query.filter_by(unique_code=unique_code).first()
    else:
        # Fallback to IP-based lookup if no session is found
        entry = WaitlistEntry.query.filter_by(ip_address=user_ip).first()

    log.info(f"Entry Unique Code: {unique_code},  User IP: {user_ip}, Entry IP: {entry.ip_address}")
    log.error(f"Entry Unique Code: {unique_code},  User IP: {user_ip}, Entry IP: {entry.ip_address}")
    print(f"Entry Unique Code: {unique_code}, User IP: {user_ip}, Entry IP: {entry.ip_address}")

    if entry:
        return jsonify({
            "email": entry.email,
            "unique_code": entry.unique_code,
            "visit_count": entry.visit_count
        }), 200
    
    return jsonify({
            "email": None,
            "unique_code": None,
            "visit_count": 0
        }), 200

# Route to verify the unique code
@waitlist_bp.route('/waitlist/<unique_code>', methods=['GET'])
def verify_code(unique_code, incrementVisitCount=True):
    entry = WaitlistEntry.query.filter_by(unique_code=unique_code).first()

    if entry is None:
        return jsonify({"message": "Invalid code."}), 404

    user_ip = get_client_ip()
    stored_code = session.get('unique_code')

    # Check if the request is from the same user
    is_same_user = entry.unique_code == stored_code and user_ip == entry.ip_address

    if (not is_same_user) and incrementVisitCount:
        entry.visit_count += 1

        if entry.visit_count >= 10:
            entry.in_waitlist = True
        
        sqldb.session.commit()

    return {
        "message": "Code verified",
        "email": entry.email,
        "visit_count": entry.visit_count,
        "sameUser": is_same_user
    }, 200

# Route to get stats for a specific unique code
@waitlist_bp.route('/waitlist/stats/<unique_code>', methods=['GET'])
def get_waitlist_stats(unique_code):
    entry = WaitlistEntry.query.filter_by(unique_code=unique_code).first()

    if entry is None:
        return jsonify({"message": "Invalid code."}), 404

    return jsonify({
        "unique_code": entry.unique_code,
        "email": entry.email,
        "visit_count": entry.visit_count,
        "created_at": entry.created_at.isoformat(),
        "ip_address": entry.ip_address
    }), 200


@waitlist_bp.route('/waitlist/export', methods=['GET'])
def export_waitlist():
    # Check if the Authorization header is present and matches the expected API key
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or auth_header != f"Bearer {WL_API_KEY}":
        return jsonify({"message": "Forbidden: Invalid API Key"}), 403

    # Query all the waitlist entries from the database
    entries = WaitlistEntry.query.all()

    # Create an in-memory file to store the CSV data
    csv_file = StringIO()
    csv_writer = csv.writer(csv_file)

    # Write the header row to the CSV
    csv_writer.writerow(['unique_code', 'email', 'visit_count', 'created_at', 'ip_address', 'reffered_by'])

    # Write data rows for each entry in the database
    for entry in entries:
        csv_writer.writerow([
            entry.unique_code,
            entry.email,
            entry.visit_count,
            entry.created_at.isoformat(),
            entry.ip_address,
            entry.reffered_by
        ])

    # Create a Flask response with the CSV content
    csv_file.seek(0)  # Move the cursor to the start of the file
    response = Response(csv_file.getvalue(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="waitlist_export.csv")

    return response