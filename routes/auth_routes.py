
import os, secrets
from flask import redirect, url_for, session, jsonify, Blueprint
from entity.response_body import ResponseBody
from auth import google
auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/login')
def login():
    nonce = secrets.token_urlsafe(16)
    session['nonce'] = nonce
    # Redirect to Google's OAuth page with the nonce
    redirect_uri = url_for('users.authorize', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce, prompt='select_account')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))