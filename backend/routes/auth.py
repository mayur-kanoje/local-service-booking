from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db_connection


# =========================================================
# BLUEPRINT
# =========================================================

auth_bp = Blueprint("auth", __name__)


# =========================================================
# USER SIGNUP
# POST /api/auth/signup
# =========================================================

@auth_bp.route("/signup", methods=["POST"])
def signup():

    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Request data is required"
            }), 400

        # -------------------------------------------------
        # GET DATA
        # -------------------------------------------------

        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        phone = str(data.get("phone", "")).strip()
        password = str(data.get("password", ""))
        address = str(data.get("address", "")).strip()
        city = str(data.get("city", "")).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not name:
            return jsonify({
                "success": False,
                "message": "Name is required"
            }), 400

        if not email:
            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400

        if "@" not in email or "." not in email:
            return jsonify({
                "success": False,
                "message": "Please enter a valid email"
            }), 400

        if phone and (
            not phone.isdigit()
            or len(phone) != 10
        ):
            return jsonify({
                "success": False,
                "message": "Phone number must contain 10 digits"
            }), 400

        if not password:
            return jsonify({
                "success": False,
                "message": "Password is required"
            }), 400

        if len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Password must be at least 6 characters"
            }), 400

        # -------------------------------------------------
        # DATABASE CONNECTION
        # -------------------------------------------------

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # CHECK EXISTING EMAIL
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )

        existing_email = cursor.fetchone()

        if existing_email:

            return jsonify({
                "success": False,
                "message": "Email is already registered"
            }), 409

        # -------------------------------------------------
        # CHECK EXISTING PHONE
        # -------------------------------------------------

        if phone:

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE phone = %s
                LIMIT 1
                """,
                (phone,)
            )

            existing_phone = cursor.fetchone()

            if existing_phone:

                return jsonify({
                    "success": False,
                    "message": "Phone number is already registered"
                }), 409

        # -------------------------------------------------
        # HASH PASSWORD
        # -------------------------------------------------

        hashed_password = generate_password_hash(password)

        # -------------------------------------------------
        # INSERT USER
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                phone,
                password,
                address,
                city
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                name,
                email,
                phone if phone else None,
                hashed_password,
                address if address else None,
                city if city else None
            )
        )

        connection.commit()

        user_id = cursor.lastrowid

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "city": city
            }
        }), 201

    except Exception as error:

        if connection:
            connection.rollback()

        print("Signup error:", error)

        return jsonify({
            "success": False,
            "message": "Registration failed",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# USER LOGIN
# POST /api/auth/login
# =========================================================

@auth_bp.route("/login", methods=["POST"])
def login():

    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Request data is required"
            }), 400

        # -------------------------------------------------
        # GET DATA
        # -------------------------------------------------

        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not email:

            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400

        if not password:

            return jsonify({
                "success": False,
                "message": "Password is required"
            }), 400

        # -------------------------------------------------
        # DATABASE CONNECTION
        # -------------------------------------------------

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # FIND USER
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                password,
                address,
                city
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )

        user = cursor.fetchone()

        # -------------------------------------------------
        # USER NOT FOUND
        # -------------------------------------------------

        if not user:

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        # -------------------------------------------------
        # CHECK PASSWORD
        # -------------------------------------------------

        if not check_password_hash(
            user["password"],
            password
        ):

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        # -------------------------------------------------
        # SUCCESS RESPONSE
        # -------------------------------------------------

        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "phone": user["phone"],
                "address": user["address"],
                "city": user["city"]
            }
        }), 200

    except Exception as error:

        print("Login error:", error)

        return jsonify({
            "success": False,
            "message": "Login failed",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()