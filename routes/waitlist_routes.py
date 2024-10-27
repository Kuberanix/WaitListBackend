from flask import request, jsonify, Blueprint, session 
from db import sqldb  # Ensure you import your sqldb instance
from entity.waitlist import WaitlistEntry
import logging, random, string, hashlib
import csv, os
from io import StringIO
import datetime
from flask import Response
import json, base64
from google.oauth2 import service_account
from googleapiclient.discovery import build

log = logging.getLogger(__name__)

WL_API_KEY = os.getenv("WL_API_KEY")

GOOGLE_SHEET_ID = os.getenv("SHEET_ID")  # Replace with your actual Google Sheet ID
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Load Google credentials from environment variable
encoded_credentials = "eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsInByb2plY3RfaWQiOiAia3l1cmF0aW9uZGV2IiwicHJpdmF0ZV9rZXlfaWQiOiAiNTZlNjIzMzI3OWEyNTFhNWI1NWJmZTY2MGI2MDI4Zjk2OTI2NDU5NiIsInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZRSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS2N3Z2dTakFnRUFBb0lCQVFDbTJvbVp4RmZMME1qclxuUmJOMC83enFBZGNKeUh0V3pReTU2WGtZdWRjSnY2ZDFLdSs5WjRTcSswZTZ2dGFCeVVzdGFyQjJnb2w1Zk50cFxuSDl0TmQvcDRQbFZmR09oeU01QUkzeGRvUVFQY3FZVDNWVi9HRVdZSy9RRnhIa1h0RE9sdXlhQTNzRzZnL3YyWVxuWEVUM1Jqekl0MGlCN3B1bjhCYTExb1hmME14VlRVNU5sRlkvVUp4NlcrTjFYdUR5b1lMcWRZV1ZlUUpHaWQwWlxucmdaT3NCV3VseUZPMVRRb2ozVkxEb0JDc05hMzNVYjFrbkJCQmxSWUFoWThMd2J4WWczRzBtQk1taDRQZHl2RlxucjVnb0dqa1pkNnRvUlJLOWdPVThZRTRVVjlNM1dXYzhyRFQvcjR5NW5SR1QrQVViZ1k0Q05YYWVHalhVM09qNlxuNzRVMUhhc3BBZ01CQUFFQ2dnRUFKalhQUTZtNVltbEFqZEtETjVTMlRrK1lEM3M4TmFOVkdnRXIxSHdBa1JDMVxuR0dtNkI4RzhXY3ljUDFtak5Zc2p2bldiampRMEorQnVQYnVJSlF4SURYL1czS1dQVzlIUGx4eUIxNFBtRHNNNlxuZWtxd21XTVVING1UcWpSQTFybTVmbi9KZzE5UjRtZ3FxcGpjeVZUcUtCd0RESkJZVUtQMGkzVmlhS0JBSHZ0clxucFRhTW5mNDh1YmZMMzdWMGI4ampHTDRyRjkwd3VKRGNRZk9ZTDVxdjJvMW4xNGN6d3Y3djMrZHBpSWJudkJrOFxuM29qZ0pGeHdLeGRBZnhqRU9DTy96MXVuY21JOW9zSHkzb1VuTnZ4TXNTeStzaGdKWE1pZzZJMncwRjl5elRuSFxuSEFLT0tSTU5pbk9pWUhXeXJyQW1yL1NqSUJUWkE4Q245ZXRyUExFM3BRS0JnUURZSFF5cE1obE1WcUEyeW1Fa1xuRWhQcEU3MEx1cTFHNjVuNWZDOE1vRUc2dTRpaDlWbE1iOUp6ZFBia2VTaTVtakhFN2FqcWdYOXhSSnFXNzhUbFxubTlWeDllRUsvUzVPa29ubHRybFVrbWNhQlJQUDJNT2V6QXpUUnQxTjZITUU1OEsxNDZ6MTczTU1oN2R0am8zTFxualhYbkRpdUJXU2hkbVcwY1d3ZkVCVnVualFLQmdRREZwZzQ5VWtpVFYzOVEwcWtxVVI4VnBIL2JiUkhyejRPQlxuZ1VLYmRCc1pjTzByV1FvdDVvUkVzTmFtdFkzdEFYbUgxOEZicWU1V3hVWldIdHEySUdEQ2JwcVRIdlZMMEhhbFxuaUducG82dGJlSzN3aldRUVhyMVZDYmY1YmJFcGVIZ21kbHFtTDI5S2gwSFozcERSbXY2dGpwQlhyNldpcFI3b1xuOStGYkFNUU5EUUtCZ0hhbWRFWU1VR0ZlQ2ZZcTVHeFdWSUlacVNmZ1pMUFVOQ1FLTHhhaWdaUFExREgvTHZqTlxuUitERnJhdEFiY0NBektST3l2ZDlBNGdmWHpSUkRXdjJRNWllb3VCU29uTFc5MGljS21JcFF0dkJQK0JVSlFweFxuQXZXWUtYWlZrWmgyMmFyZEJoKzhTQkR3RGgvakxTdzlUU2IrMjVuWFpsY0ZIaWQ4UHVZNi90Z2RBb0dBVEVMcFxuUmFIbEhPenEwLzJraGc1czV3WGt5MzZISnF5WCtqVXN4UnlFaEVsOVNYZCtwUDFIMWRWQnpXdEtDc1BCNTdkSlxuQlJ4Sk9UTy9FdVd1MEEwb0tIMVNxU2VOMENYc1VheVQ2VEZjb2R1cmlhQ1VsbmhucDFNcnFGTTV3MTJYUm9mdVxuTENjclV0OWplalFWUHJzR1AyTTlzSWUyYWs0NTRmd2ErT2tQdkZVQ2dZRUFyQUhJc0ZwblpzU3JRTHc5TmlhR1xuLzlxVGpmTmR4dnRPbUZWYWJDNmlaVU50VCtJRDJ5YlZIWHFkVnNwUjg2ZWxwalU1RjQ3Y0xSWTZsWGttOUhkTFxuQUhmM3lTOEpTNE1kTFFZeDlERnVKcGxYRzB4Q3h2ckpuYWszemlMZzhaaHNJOHJCQVB1TlpEUHpwR2lYamRFQlxuWjY0RjB1aytGNTRDU3NSYWxlaC9VdGM9XG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLCJjbGllbnRfZW1haWwiOiAid2xzaGVldEBreXVyYXRpb25kZXYuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb20iLCJjbGllbnRfaWQiOiAiMTAzNjQwMzAyNjQ5NzQwNzMxMTAxIiwiYXV0aF91cmkiOiAiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tL28vb2F1dGgyL2F1dGgiLCJ0b2tlbl91cmkiOiAiaHR0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW4iLCJhdXRoX3Byb3ZpZGVyX3g1MDlfY2VydF91cmwiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vb2F1dGgyL3YxL2NlcnRzIiwiY2xpZW50X3g1MDlfY2VydF91cmwiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vcm9ib3QvdjEvbWV0YWRhdGEveDUwOS93bHNoZWV0JTQwa3l1cmF0aW9uZGV2LmlhbS5nc2VydmljZWFjY291bnQuY29tIiwidW5pdmVyc2VfZG9tYWluIjogImdvb2dsZWFwaXMuY29tIn0K"

google_credentials = None
if encoded_credentials:
    google_credentials = json.loads(base64.b64decode(encoded_credentials))
else:
    log.error("Null sheets creds")

creds = service_account.Credentials.from_service_account_info(google_credentials, scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=creds)

BOT_USER_AGENTS = [
    'facebookexternalhit',  # Facebook
    'Twitterbot',           # Twitter
    'LinkedInBot',          # LinkedIn
    'Googlebot',            # Google
    'Bingbot',              # Bing
    'YandexBot',            # Yandex
    'Facebot',              # Facebook
    'ia_archiver',          # Alexa/Wayback Machine
]

def is_bot(user_agent):
    """Check if the User-Agent matches a known bot."""
    return any(bot in user_agent for bot in BOT_USER_AGENTS)

def get_client_ip():
    if request.headers.get('user-request-from-ip'):
        ip = request.headers.get('user-request-from-ip')
    else:
        ip = request.remote_addr
    
    return ip

def append_to_google_sheet(data):
    # Define the range to append data
    range_name = "Sheet1!A1"  # Replace with your sheet's range if different

    # Prepare the data in the format Google Sheets API expects
    body = {
        "values": [data]
    }

    # Append the data to the sheet
    sheets_service.spreadsheets().values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=range_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()


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
        existingEntry: WaitlistEntry = WaitlistEntry.query.filter_by(email=email).first() or WaitlistEntry.query.filter_by(phone_number=phone_number).first()  or WaitlistEntry.query.filter_by(ip_address=user_ip).first()
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
        
        try:
            sheet_data = [
                new_entry.email,
                new_entry.phone_number,
                new_entry.unique_code,
                new_entry.message,
                new_entry.ip_address,
                new_entry.reffered_by,
                datetime.datetime.now().isoformat()
            ]
            append_to_google_sheet(sheet_data)

        except Exception as ex:
            print(ex)
            print("Failure in updating sheet for email: " + new_entry.email)
            log.error("Failure in updating sheet for email: " + new_entry.email)
        
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
    user_agent = request.headers.get('User-Agent', '')

    # Check if the request is from the same user
    is_same_user = entry.unique_code == stored_code and user_ip == entry.ip_address

    log.error(unique_code, user_agent, is_bot(user_agent))

    if (not is_same_user) and incrementVisitCount and (not is_bot(user_agent)):
        entry.visit_count += 1

        if entry.visit_count >= 5:
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
    auth_header = request.headers.get('Authorization')
    
    # Check Authorization
    if not auth_header or auth_header != f"Bearer {WL_API_KEY}":
        return jsonify({"message": "Forbidden: Invalid API Key"}), 403

    # Check if file is provided
    if 'file' not in request.files:
        return jsonify({"message": "No file provided"}), 400

    file = request.files['file']
    if not file or not file.filename.endswith('.csv'):
        return jsonify({"message": "Invalid file format. Please upload a CSV file."}), 400

    try:
        csv_file = StringIO(file.stream.read().decode('utf-8'))
        csv_reader = csv.DictReader(csv_file)
        columns = [column.name for column in WaitlistEntry.__table__.columns]

        entries_created = 0
        for row in csv_reader:
            # Skip empty rows
            if not row or all(value == "" for value in row.values()):
                continue

            # Check for required columns
            if not all(key in row for key in columns):
                return jsonify({"message": "Invalid CSV format: Missing columns"}), 400

            # Prepare entry data
            entry_data = {column: row[column] for column in columns if column in row}
            entry_data.pop('id', None)
            entry_data.pop('created_at', None)

            # Parse values as needed
            entry_data['visit_count'] = int(entry_data.get('visit_count', 0))
            entry_data['in_waitlist'] = entry_data['in_waitlist'].strip().lower() == 'true'
            entry_data['reffered_by'] = entry_data['reffered_by'] if entry_data['reffered_by'] != "None" else None

            # Check if entry already exists
            if WaitlistEntry.query.filter_by(email=entry_data['email']).first() or WaitlistEntry.query.filter_by(phone_number=entry_data['phone_number']).first():
                continue  # Skip if entry already exists

            # Add new entry
            new_entry = WaitlistEntry(**entry_data)
            sqldb.session.add(new_entry)
            entries_created += 1

        # Commit once at the end
        sqldb.session.commit()

    except Exception as e:
        # Handle unexpected errors
        sqldb.session.rollback()
        return jsonify({"message": "An error occurred during import", "error": str(e)}), 500

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

@waitlist_bp.route('/')
def home():
    log.info("Home route accessed")
    return "Hello, World"