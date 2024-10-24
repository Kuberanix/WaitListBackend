from flask import request, jsonify, Blueprint, session 
from db import sqldb  # Ensure you import your sqldb instance
from entity.waitlist import WaitlistEntry
import logging, random, string, hashlib
import csv, os
from io import StringIO
import datetime
from flask import Response

log = logging.getLogger(__name__)

WL_API_KEY = os.getenv("WL_API_KEY")

def get_client_ip():
    if request.headers.get('user-request-from-ip'):
        ip = request.headers.get('user-request-from-ip')
    else:
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
        phone_number = request.args.get("phone_number")
        message = request.args.get("message")

        if not email:
            return jsonify({"message": "Email is missing"}), 400
        
        if not phone_number:
            return jsonify({"message": "Phone number is missing"}), 400
        
        # Check if the email already exists in the waitlist
        existingEntry: WaitlistEntry = WaitlistEntry.query.filter_by(email=email).first() or WaitlistEntry.query.filter_by(ip_address=user_ip).first()
        if existingEntry:
            return jsonify({
                "message": "User already exists.",
                "email": existingEntry.email,
                "unique_code": existingEntry.unique_code,
                "inWaitList" : existingEntry.in_waitlist
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
            reffered_by=reffered_by,
            phone_number=phone_number,
            message=message
        )
        sqldb.session.add(new_entry)
        sqldb.session.commit()

        session['unique_code'] = unique_code

        return jsonify({
            "message": "New waitlist entry created",
            "unique_code": unique_code,
            "email": email,
            "inWaitList" : new_entry.in_waitlist
        }), 201

    # If the request is GET
    entry:WaitlistEntry = None
    unique_code = session.get('unique_code')
    if unique_code:
        entry = WaitlistEntry.query.filter_by(unique_code=unique_code).first()
    else:
        # Fallback to IP-based lookup if no session is found
        entry = WaitlistEntry.query.filter_by(ip_address=user_ip).first()

    if entry:
        return jsonify({
            "email": entry.email,
            "unique_code": entry.unique_code,
            "visit_count": entry.visit_count,
            "inWaitList" : entry.in_waitlist
        }), 200
    
    return jsonify({
        "message" : "User not registered"
        }), 404

# Route to verify the unique code
@waitlist_bp.route('/waitlist/<unique_code>', methods=['GET'])
def verify_code(unique_code, incrementVisitCount=True):
    entry: WaitlistEntry = WaitlistEntry.query.filter_by(unique_code=unique_code).first()

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
        "inWaitList" : entry.in_waitlist,
        "sameUser": is_same_user
    }, 200

# Route to get stats for a specific unique code
@waitlist_bp.route('/waitlist/stats/<unique_code>', methods=['GET'])
def get_waitlist_stats(unique_code):
    entry:WaitlistEntry = WaitlistEntry.query.filter_by(unique_code=unique_code).first()

    if entry is None:
        return jsonify({"message": "Invalid code."}), 404

    return jsonify({
        "unique_code": entry.unique_code,
        "email": entry.email,
        "visit_count": entry.visit_count,
        "created_at": entry.created_at.isoformat(),
        "ip_address": entry.ip_address,
        "inWaitList" : entry.in_waitlist
    }), 200


@waitlist_bp.route('/waitlist/export', methods=['GET'])
def export_waitlist():
    # Check if the Authorization header is present and matches the expected API key
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or auth_header != f"Bearer {WL_API_KEY}":
        return jsonify({"message": "Forbidden: Invalid API Key"}), 403

    entries = WaitlistEntry.query.all()

    csv_file = StringIO()
    csv_writer = csv.writer(csv_file)

    columns = [column.name for column in WaitlistEntry.__table__.columns]
    csv_writer.writerow(columns)

    for entry in entries:
        csv_writer.writerow([getattr(entry, column) for column in columns])

    # Create a Flask response with the CSV content
    csv_file.seek(0)  # Move the cursor to the start of the file
    response = Response(csv_file.getvalue(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="waitlist_export.csv")

    return response


@waitlist_bp.route('/waitlist/import', methods=['POST'])
def import_waitlist():
    # Check if the Authorization header is present and matches the expected API key
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or auth_header != f"Bearer {WL_API_KEY}":
        return jsonify({"message": "Forbidden: Invalid API Key"}), 403

    if 'file' not in request.files:
        return jsonify({"message": "No file provided"}), 400

    file = request.files['file']

    if not file or not file.filename.endswith('.csv'):
        return jsonify({"message": "Invalid file format. Please upload a CSV file."}), 400

    # Read the CSV content
    csv_file = StringIO(file.stream.read().decode('utf-8'))
    csv_reader = csv.DictReader(csv_file)  # Use DictReader to handle header automatically

    # Get the columns dynamically from the WaitlistEntry model
    columns = [column.name for column in WaitlistEntry.__table__.columns]

    entries_created = 0
    for row in csv_reader:
        # Ensure all required fields are present in the CSV by checking against columns dynamically
        if not all(key in row for key in columns):
            return jsonify({"message": "Invalid CSV format: Missing columns"}), 400

        # Extract data dynamically based on column names
        entry_data = {column: row[column] for column in columns}

        # Parse values as needed, e.g., convert types
        entry_data['visit_count'] = int(entry_data.get('visit_count', 0))
        entry_data['in_waitlist'] = entry_data['in_waitlist'].lower() == 'true'
        entry_data['created_at'] = datetime.fromisoformat(entry_data['created_at']) if 'created_at' in entry_data else None
        entry_data['reffered_by'] = entry_data['reffered_by'] if entry_data['reffered_by'] != "None" else None

        # Check if the entry already exists
        existing_entry = WaitlistEntry.query.filter_by(email=entry_data['email']).first()
        if existing_entry:
            continue  # Skip if entry already exists

        # Create a new waitlist entry
        new_entry = WaitlistEntry(**entry_data)

        # Add and commit the new entry to the database
        sqldb.session.add(new_entry)
        entries_created += 1

    sqldb.session.commit()

    return jsonify({
        "message": f"Successfully imported {entries_created} entries into the waitlist."
    }), 201



@waitlist_bp.route('/waitlist/clear', methods=['DELETE'])
def clear_waitlist():
    # Check if the Authorization header is present and matches the expected API key
    auth_header = request.headers.get('Authorization')

    if not auth_header or auth_header != f"Bearer {WL_API_KEY}":
        return jsonify({"message": "Forbidden: Invalid API Key"}), 403

    try:
        # Delete all entries from the WaitlistEntry table
        num_rows_deleted = sqldb.session.query(WaitlistEntry).delete()

        # Commit the changes
        sqldb.session.commit()

        return jsonify({
            "message": f"Successfully deleted {num_rows_deleted} entries from the waitlist."
        }), 200

    except Exception as e:
        sqldb.session.rollback()
        return jsonify({"message": "Failed to clear waitlist.", "error": str(e)}), 500
