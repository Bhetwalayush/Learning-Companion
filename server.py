# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.json_util import dumps
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = MongoClient(MONGODB_URI)
db = client["chatbot_db"]
users_col = db["users"]

app = Flask(__name__)
CORS(app)


def user_to_response(doc):
    """Convert Mongo doc to JSON-friendly dict"""
    return {
        "user_id": str(doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "level": doc.get("level", 1),
        "streak": doc.get("streak", 0),
        "history": doc.get("history", []),
    }


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "name, email and password required"}), 400

    # check if exists
    if users_col.find_one({"email": email}):
        return jsonify({"error": "email already registered"}), 400

    hashed = generate_password_hash(password)
    new_user = {
        "name": name,
        "email": email,
        "password": hashed,
        "level": 1,
        "streak": 0,
        "history": []  # store chat history or activity
    }
    result = users_col.insert_one(new_user)
    user = users_col.find_one({"_id": result.inserted_id})
    return jsonify({"message": "signup_success", "user": user_to_response(user)}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    user = users_col.find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "invalid credentials"}), 401

    return jsonify({"message": "login_success", "user": user_to_response(user)}), 200


@app.route("/user/<user_id>", methods=["GET"])
def get_user(user_id):
    try:
        doc = users_col.find_one({"_id": ObjectId(user_id)})
        if not doc:
            return jsonify({"error": "user not found"}), 404
        return jsonify({"user": user_to_response(doc)}), 200
    except Exception as e:
        return jsonify({"error": "invalid id", "detail": str(e)}), 400


@app.route("/user/<user_id>/update", methods=["POST"])
def update_user(user_id):
    """
    Example endpoint to update level/streak/history
    POST payload: {"level": <int>, "streak": <int>, "history_item": {...}}
    """
    try:
        updates = {}
        body = request.get_json(force=True)
        if "level" in body:
            updates["level"] = int(body["level"])
        if "streak" in body:
            updates["streak"] = int(body["streak"])

        if updates:
            users_col.update_one({"_id": ObjectId(user_id)}, {"$set": updates})

        if "history_item" in body:
            users_col.update_one({"_id": ObjectId(user_id)}, {"$push": {"history": body["history_item"]}})

        user = users_col.find_one({"_id": ObjectId(user_id)})
        return jsonify({"message": "updated", "user": user_to_response(user)}), 200
    except Exception as e:
        return jsonify({"error": "update failed", "detail": str(e)}), 400


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
