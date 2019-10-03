# Import flask and necesary dependencies.
from flask import Flask, Blueprint, request, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, jwt_refresh_token_required, get_jwt_identity)

from common.db import mongo
from common.utils import *
from jsonschemas.cart import validate_cart_create
from jsonschemas.cart import validate_cart_summary
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

# Create the blueprint
cart = Blueprint('cart', __name__)

# POST cart
@cart.route('/cart', methods=['POST'])
@jwt_required
def cart_create():
    if request.method == 'POST':
        output = defaultObject()
        data = request.get_json()
        data = validate_cart_create(data)
        current_user = get_jwt_identity()

        if data['ok']:
            data = data['data']
            # Check if cart exists
            search_user_cart = mongo.db.carts.find_one(
                {'user': ObjectId(current_user['_id'])})

            items = []
            for item in data['items']:
                # Look for product
                product = mongo.db.products.find_one(
                    {'_id': ObjectId(item['_id'])})
                # Validations
                if(product == None):
                    output['message'] = 'PRODUCT_NOT_FOUND'
                    return jsonify(output), 404

                if(item['quantity'] > product['stock']):
                    output['message'] = 'NO_ENOUGH_STOCK'
                    return jsonify(output), 400

                if(item['price'] != product['price']):
                    output['message'] = 'PRICE_MISMATCH'
                    return jsonify(output), 400

                item['_id'] = ObjectId(item['_id'])
                items.append(item)

            if (search_user_cart):
                # Update Cart
                data['updatedAt'] = datetime.timestamp(datetime.now())
                mongo.db.carts.update_one({'user': ObjectId(current_user['_id'])}, {
                    '$set': {'updatedAt': data['updatedAt'], 'items': items}})

                output['status'] = True
                output['message'] = 'CART_UPDATED'

            else:
                # Create Cart
                newCart = {}
                newCart['user'] = ObjectId(current_user['_id'])
                newCart['items'] = items
                newCart['createdAt'] = datetime.timestamp(datetime.now())
                newCart['updatedAt'] = datetime.timestamp(datetime.now())

                mongo.db.carts.insert_one(newCart)
                output['status'] = True
                output['message'] = 'CART_CREATED'

            return jsonify(output), 200
        else:
            output['message'] = 'BAD_REQUEST: {}'.format(data['message'])
            return jsonify(output), 400

# GET cart
@cart.route('/cart', methods=['GET'])
@jwt_required
def cart_get():
    if request.method == 'GET':
        output = defaultObject()
        current_user = get_jwt_identity()

        # Check if cart exists
        user_cart = mongo.db.carts.find_one(
            {'user': ObjectId(current_user['_id'])})

        if (user_cart):
            # Change Object_Ids to Strings
            items = []
            for item in user_cart['items']:
                item['_id'] = str(item['_id'])
                items.append(item)

            if not items:
                output['message'] = 'EMPTY_CART'
                return jsonify(output), 404

            output['status'] = True
            output['message'] = 'CORRECT'
            output['data'] = items
            return jsonify(output), 200
        else:
            output['message'] = 'EMPTY_CART'
            return jsonify(output), 404


# Get products summary (via POST)
@cart.route('/cart/summary', methods=['POST'])
def getCartSummary():
    if request.method == 'POST':
        output = defaultObject()
        data = request.get_json()
        data = validate_cart_summary(data)
        if(data['ok']):
            itemsList = data['data']['_ids']
            resultSet = {}
            for _id in itemsList:
                try:
                    productData = mongo.db.products.find_one(
                        {'_id': ObjectId(_id)})
                    resultSet[_id] = {"image": productData['image'],
                                      "name": productData["name"],
                                      "price": productData["price"],
                                      "stock": productData["stock"]}
                except InvalidId:
                    resultSet[_id] = "ERROR: This product does not exist"

            output['status'] = True
            output['message'] = 'FETCHED'
            output['data'] = resultSet

            return jsonify(output), 200
        else:
            output['message'] = 'BAD_REQUEST: {}'.format(data['message'])
            return jsonify(output), 400

# For Testing
@cart.route('/cart/delete', methods=['DELETE'])
@jwt_required
def delete_admin():
    if request.method == 'DELETE':
        output = defaultObject()
        current_user = get_jwt_identity()
        cart_deleted = mongo.db.carts.delete_one(
            {'user': ObjectId(current_user['_id'])})
        if (cart_deleted.deleted_count):
            output['status'] = True
            output['message'] = 'DELETED_CORRECTLY'
            return jsonify(output), 200
        else:
            output['message'] = 'CART_NOT_FOUND'
            return jsonify(output), 404
