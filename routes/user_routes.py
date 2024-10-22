from flask import Blueprint, request, session, redirect, url_for
from services import user_service
from auth import google
from decorators.decorators import json_response, login_required
from entity.user import User
from entity.response_body import ResponseBody
from pydantic import ValidationError
from exceptions.CustomExceptions import InternalServerError
import logging

log = logging.getLogger(__name__)

user_bp = Blueprint("users", __name__)

# TODO: Hidden (only superuser can hit)
@user_bp.route("/users", methods=["POST"])
@json_response
def create_user():
    data = request.json
    try:
        user: User = User(**data)
    except ValidationError as ex:
        return ResponseBody({"error": str(ex)} , 400)
    return user_service.create_user(user)

# TODO: Hidden (only superuser can hit)
@user_bp.route("/users", methods=["GET"])
@json_response
def get_users():
    return user_service.get_all_users()

# TODO: Shouldn't be used
@user_bp.route("/users/<id>", methods=["GET"])
@json_response
def get_user(id):
    return user_service.get_user_by_user_id(id)

# TODO: Based on cookie return full response else half
@user_bp.route("/users/user", methods=["GET"])
@json_response
def get_user_by_username():
    username = request.args.get("username")
    if username:
        return user_service.get_user_by_username(username)
    else:
        return ResponseBody({"error": "Please provide either 'username' as a query parameter"}, 400)


@user_bp.route("/users/<id>", methods=["PATCH"])
@json_response
@login_required
def update_user(id):
    data = request.json
    update_user: User = user_service.update_user(id, data)
    return ResponseBody(update_user)


@user_bp.route("/users/<id>", methods=["DELETE"])
@json_response
@login_required
def delete_user(id):
    return user_service.delete_user(id)

@user_bp.route("/home")
@login_required
@json_response
def home():
    user_session_info = session.get('user')
    username = user_session_info.get('username')
    return ResponseBody(f"Welcome, {username}!")  


# Google callback route
@user_bp.route('/callback')
def authorize():
    if(google):
        token = google.authorize_access_token()
        
        # Retrieve the nonce from the session
        nonce = session.get('nonce')
        if nonce is None:
            return "Nonce is missing, authentication failed", 400
        
        # Parse and verify the ID token using the nonce
        user_info = google.parse_id_token(token, nonce=nonce)
        user:User = user_service.get_or_create_user_by_email(user_info['email']).obj
        
        # Store user info in session or database
        session['user'] = {
            'user_id': user.id,
            'email': user.email,
            'username' : user.username,
            'email_verified': user_info['email_verified'],
            'sub': user_info['sub'],
            'hd': user_info.get('hd')  # Optional, in case you want to store the domain
        }
        
        # Clear the nonce from the session after it's been used
        session.pop('nonce', None)
        next_url = session.pop('next', None)
        return redirect(next_url or url_for('users.home'))
    else:
        log.error("Google from auth is null")
        raise InternalServerError("Something wrong in auth")
