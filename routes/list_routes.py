from flask import Blueprint, request
from services.list_service import ListService
from db import mongo
from decorators.decorators import json_response, login_required, paginate_and_sort
from entity.list import List
from entity.response_body import ResponseBody
from pydantic import ValidationError
from exceptions.CustomExceptions import InvalidRequestException
from services import list_service

list_bp = Blueprint("lists", __name__)

@list_bp.route("/lists", methods=["POST"])
@json_response
@login_required
def create_list():
    data = request.json
    try:
        list_item = List(**data)  # Validate and create a List instance
    except ValidationError as ex:
        return ResponseBody({"error": str(ex)}, 400)
    
    return list_service.create_list(list_item)

# TODO : Hide this (only for superuser)
@list_bp.route("/lists", methods=["GET"])
@json_response
def get_all_lists():
    return list_service.get_all_lists()

@list_bp.route("/lists/<list_id>", methods=["GET"])
@json_response
def get_list(list_id):
    return list_service.get_list_by_list_id(list_id)

@list_bp.route("/lists/user", methods=["GET"])
@paginate_and_sort(default_per_page=20)
@json_response
def get_lists_by_user(page, per_page, sort_by, sort_order):
    user_id = request.args.get("user_id")
    username = request.args.get("username")
    include_private: bool = bool(request.args.get("include_private", "true").lower() == "true")  # default is true

    if not user_id and not username:
        raise InvalidRequestException("Please provide either 'user_id' or 'username' as a query parameter")

    # Fetch lists based on user_id or username
    if user_id:
        # Pass pagination parameters to the service method
        lists = list_service.get_lists_by_user_id(user_id, include_private, page, per_page, sort_by, sort_order)
    elif username:
        # Pass pagination parameters to the service method
        lists = list_service.get_lists_by_username(username, include_private, page, per_page, sort_by, sort_order)

    return lists

@list_bp.route("/lists/<list_id>", methods=["PATCH"])
@json_response
@login_required
def update_list(list_id):
    data = request.json
    updated_list = list_service.update_list(list_id, data)
    
    if updated_list:
        return ResponseBody(updated_list)
    
    return ResponseBody({"error": "List not found or no changes made"}, 404)

@list_bp.route("/lists/<list_id>", methods=["DELETE"])
@json_response
def delete_list(list_id):
    return list_service.delete_list(list_id)
