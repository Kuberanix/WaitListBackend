from flask import Blueprint, request
from services import item_service
from db import mongo
from decorators.decorators import json_response, login_required
from entity.item import Item
from entity.response_body import ResponseBody
from pydantic import ValidationError
from exceptions.CustomExceptions import *

item_bp = Blueprint("items", __name__)

@item_bp.route("/items", methods=["POST"])
@json_response
@login_required
def create_item():
    data = request.json
    try:
        item = Item(**data)  # Validate and create an Item instance
    except ValidationError as ex:
        raise InvalidRequestException(ex)
    
    return item_service.create_item(item)

@item_bp.route("/items", methods=["GET"])
@json_response
def get_all_items():
    items = item_service.get_all_items()
    return ResponseBody(items)

@item_bp.route("/items/<item_id>", methods=["GET"])
@json_response
def get_item(item_id):
    return item_service.get_item_by_item_id(item_id)

@item_bp.route("/items/user", methods=["GET"])
@json_response
def get_items_by_user():
    user_id = request.args.get("user_id")
    include_private: bool = bool(request.args.get("include_private") == "true")

    if user_id:
        items = item_service.get_items_by_user_id(user_id, include_private)
        return ResponseBody(items)

    raise InvalidRequestException(f"Please provide 'user_id' as a query parameter")

@item_bp.route("/items/<item_id>", methods=["PATCH"])
@json_response
def update_item(item_id):
    data = request.json
    updated_item = item_service.update_item(item_id, data)
    
    if updated_item:
        return ResponseBody(updated_item)
    
    raise NotFoundException("Item not found or no changes made")

@item_bp.route("/items/<item_id>", methods=["DELETE"])
@json_response
def delete_item(item_id):
    result = item_service.delete_item(item_id)
    return ResponseBody(result)