# Import flask and necesary dependencies.
from flask import Flask, Blueprint, request, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_jwt_extended import (create_access_token, create_refresh_token, jwt_required, jwt_refresh_token_required, get_jwt_identity)

from common.db import mongo
from common.utils import *
from jsonschemas.products import validate_products_post, validate_products_put, validate_just_id
from datetime import datetime
from bson import ObjectId
from utils.aws import S3Instance
# Create the blueprint
products = Blueprint('products', __name__)

# Create the route
@products.route('/products', methods=['GET'])
def get_products():
    if request.method == 'GET':
        output = defaultObject()
        for single_product in mongo.db.products.find():
            if (single_product['available']):
                del single_product['description']
                del single_product['updatedAt']
                del single_product['createdAt']
                del single_product['sold']
                single_product['_id'] = str(single_product['_id'])
                output['data'].append(single_product)
        return jsonify(output), 200


@products.route('/products/<int:total_items>/<int:page>', methods=['GET'])
def get_products_paginated(total_items, page):
    if request.method == 'GET':
        output = defaultObjectDataAsAnObject()
        output['data']['total_products'] = mongo.db.products.count_documents({'available': True})

        products_array = []
        skip = (total_items * page) - total_items
        for single_product in mongo.db.products.find().skip(skip).limit(total_items):
            if (single_product['available']):
                del single_product['description']
                del single_product['updatedAt']
                del single_product['createdAt']
                del single_product['sold']
                single_product['_id'] = str(single_product['_id'])
                products_array.append(single_product)

        output['data']['products'] = products_array
        return jsonify(output), 200


@products.route('/products/single', methods=['POST'])
def get_single_product():
    if request.method == 'POST':
        output = defaultObject()
        data = request.get_json()
        data = validate_just_id(data)
        if (data['ok']):
            data = data['data']
            print(data)
            searched_product = mongo.db.products.find_one({'_id': ObjectId(data['_id'])})
            print(searched_product)
            if (searched_product):
                del searched_product['_id']
                del searched_product['sold']
                searched_product['createdAt'] = convertTimestampToDateTime(searched_product['createdAt'])
                searched_product['updatedAt'] = convertTimestampToDateTime(searched_product['updatedAt'])
                output['message'] = 'CORRECT'
                output['status'] = True
                output['data'] = searched_product
                return jsonify(output), 200
            else:
                output['message'] = 'PRODUCT_NOT_FOUND'
                return jsonify(output), 404
        else:
            output['message'] = 'BAD_REQUEST: {}'.format(data['message'])
            return jsonify(output), 400


@products.route('/products/all', methods=['GET'])
@jwt_required
def get_products_all():
    if request.method == 'GET':
        output = defaultObject()
        current_user = get_jwt_identity()
        search_current_admin = mongo.db.admins.find_one({'email': current_user['email']})
        if (search_current_admin):
            for single_product in mongo.db.products.find():
                single_product['_id'] = str(single_product['_id'])
                single_product['createdAt'] = convertTimestampToDateTime(single_product['createdAt'])
                single_product['updatedAt'] = convertTimestampToDateTime(single_product['updatedAt'])
                output['data'].append(single_product)
            return jsonify(output), 200


@products.route('/products/create', methods=['POST'])
@jwt_required
def create_product():
    if request.method == 'POST':
        output = defaultObject()
        current_user = get_jwt_identity()
        search_current_admin = mongo.db.admins.find_one({'email': current_user['email']})
        if (search_current_admin):
            data = request.get_json()
            data = validate_products_post(data)
            if data['ok']:
                data = data['data']
                data['available'] = True
                data['sold'] = 0
                data['createdAt'] = datetime.timestamp(datetime.now())
                data['updatedAt'] = datetime.timestamp(datetime.now())
                new_product = mongo.db.products.insert_one(data)
                output['data'] = str(new_product.inserted_id)
                output['status'] = True
                output['message'] = 'CORRECTLY_REGISTERED'
                return jsonify(output), 200
            else:
                output['message'] = 'BAD_REQUEST: {}'.format(data['message'])
                return jsonify(output), 400
        else:
            output['status'] = False
            output['message'] = 'FORBIDDEN'
            return jsonify(output), 403


@products.route('/products/update', methods=['PUT'])
@jwt_required
def update_product():
    if request.method == 'PUT':
        output = defaultObject()
        current_user = get_jwt_identity()
        search_current_admin = mongo.db.admins.find_one({'email': current_user['email']})
        if (search_current_admin):
            data = request.get_json()
            data = validate_products_put(data)
            if data['ok']:
                data = data['data']
                data['updatedAt'] = datetime.timestamp(datetime.now())
                updated_product = mongo.db.products.update_one({'_id': ObjectId(data['_id'])}, {'$set': {'available': data['available'], 'name': data['name'], 'description': data['description'],
                                                                                                         'shippable': data['shippable'], 'price': data['price'], 'stock': data['stock'], 'image': data['image'], 'updatedAt': data['updatedAt']}})

                if (updated_product.modified_count):
                    output['status'] = True
                    output['message'] = 'UPDATED_CORRECTLY'
                    return jsonify(output), 200
                else:
                    output['message'] = 'PRODUCT_NOT_FOUND'
                    return jsonify(output), 404
            else:
                output['message'] = 'BAD_REQUEST: {}'.format(data['message'])
                return jsonify(output), 400
        else:
            output['status'] = False
            output['message'] = 'FORBIDDEN'
            return jsonify(output), 403


@products.route('/products/delete', methods=['DELETE'])
@jwt_required
def delete_product():
    if request.method == 'DELETE':
        output = defaultObject()
        current_user = get_jwt_identity()
        search_current_admin = mongo.db.admins.find_one({'email': current_user['email']})
        if (search_current_admin):
            data = request.get_json()
            data = validate_just_id(data)
            if data['ok']:
                data = data['data']
                data['updatedAt'] = datetime.timestamp(datetime.now())
                update_product_availability = mongo.db.products.update_one({'_id': ObjectId(data['_id'])}, {'$set': {'available': False, 'updatedAt': data['updatedAt']}})
                if (update_product_availability.modified_count):
                    output['status'] = True
                    output['message'] = 'DELETED_CORRECTLY'
                    return jsonify(output), 200
                else:
                    output['message'] = 'PRODUCT_NOT_FOUND'
                    return jsonify(output), 404
            else:
                output['message'] = 'BAD_REQUEST: {}'.format(data['message'])
                return jsonify(output), 400
        else:
            output['status'] = False
            output['message'] = 'FORBIDDEN'
            return jsonify(output), 403


@products.route('/products/delete/real', methods=['DELETE'])
@jwt_required
def delete_product_real():
    if request.method == 'DELETE':
        output = defaultObject()
        current_user = get_jwt_identity()
        search_current_admin = mongo.db.admins.find_one({'email': current_user['email']})
        if (search_current_admin):
            data = request.get_json()
            data = validate_just_id(data)
            if data['ok']:
                data = data['data']
                deleted_products = mongo.db.products.delete_one({'_id': ObjectId(data['_id'])})
                if (deleted_products.deleted_count):
                    output['status'] = True
                    output['message'] = 'DELETED_CORRECTLY'
                    return jsonify(output), 200
                else:
                    output['message'] = 'PRODUCT_NOT_FOUND'
                    return jsonify(output), 404
            else:
                output['message'] = 'BAD_REQUEST: {}'.format(data['message'])
                return jsonify(output), 400
        else:
            output['status'] = False
            output['message'] = 'FORBIDDEN'
            return jsonify(output), 403


@products.route('/products/images/upload', methods=['POST'])
@jwt_required
def upload_image():
    if request.method == 'POST':
        output = defaultObject()
        current_user = get_jwt_identity()
        search_current_admin = mongo.db.admins.find_one({'email': current_user['email']})
        if (search_current_admin):
            formData = dict(request.files)
            image = formData.get("image")
            uploadedURL = S3Instance().uploadImage(image)
            output['status'] = True
            output['message'] = 'DONE'
            output['data'] = uploadedURL
            return jsonify(output), 200
        else:
            output['status'] = False
            output['message'] = "FORBIDDEN"
            return jsonify(output), 403
