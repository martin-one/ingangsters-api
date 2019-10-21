from flask import Flask, Blueprint, request, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, jwt_refresh_token_required, get_jwt_identity)

from common.db import mongo
from common.utils import *
from jsonschemas.orders import validate_order_create_data
from datetime import datetime
from bson import ObjectId

orders = Blueprint('orders', __name__)


@orders.route('/orders/create', methods=['POST'])
def orders_create():
    if request.method == 'POST':
        output = defaultObject()
        data = request.get_json()
        data = validate_order_create_data(data)
        if data['ok']:
            data = data['data']

            for single_item in data['items']:
                single_product_searched = mongo.db.products.find_one(
                    {'_id': ObjectId(single_item['_id'])})
                if (single_product_searched['price'] != single_item['price']):
                    output['message'] = 'PRICE_MISMATCH'
                    return jsonify(output), 400
                if (single_product_searched['stock'] < single_item['quantity']):
                    output['message'] = 'STOCK_MISMATCH'
                    return jsonify(output), 400

            user = {'userId': None, 'guest': None}
            if (data.get('userId')):
                search_user = mongo.db.users.find_one(
                    {'_id': ObjectId(data['userId'])})
                if search_user:
                    user['userId'] = data['userId']
                    cart_deleted = mongo.db.carts.delete_one(
                        {'user': ObjectId(user['userId'])})
            else:
                if (data.get('name') and data.get('email')):
                    user['guest'] = {'name': data['name'],
                                     'email': data['email']}
                else:
                    output['message'] = 'BAD_REQUEST'
                    return jsonify(output), 400

            order = {'user': user, 'shipping_address': data['shipping_address'],
                     'billing_address': data['billing_address'], 'items': data['items'],
                     'status': 'AWAITING_FULFILLMENT',
                     'createdAt': datetime.timestamp(datetime.now()), 'updatedAt': datetime.timestamp(datetime.now())
                     }

            # Update stock
            for single_item in data['items']:
                single_product_searched = mongo.db.products.find_one(
                    {'_id': ObjectId(single_item['_id'])})
                newStock = single_product_searched['stock'] - \
                    single_item['quantity']

                updated_product = mongo.db.products.update_one(
                    {'_id': ObjectId(single_item['_id'])}, {'$set': {'stock': newStock}})

            mongo.db.orders.insert_one(order)
            output['status'] = True
            output['message'] = 'CORRECT'
            return jsonify(output), 200
        else:
            output['message'] = 'BAD_REQUEST: {}'.format(data['message'])
            return jsonify(output), 400