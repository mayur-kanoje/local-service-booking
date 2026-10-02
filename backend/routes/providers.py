from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db_connection


providers_bp = Blueprint("providers", __name__)


# =========================================================
# ALLOWED SERVICES
# =========================================================

ALLOWED_SERVICE_TYPES = {
    "Carpenter",
    "Plumber",
    "Cleaner",
    "Home Designer"
}


# =========================================================
# PROVIDER SIGNUP
# POST /api/providers/signup
# =========================================================

@providers_bp.route("/signup", methods=["POST"])
def provider_signup():

    connection = None
    cursor = None

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Request data is required"
            }), 400


        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        phone = str(data.get("phone", "")).strip()
        password = str(data.get("password", "")).strip()
        service_type = str(data.get("service_type", "")).strip()
        experience = data.get("experience", 0)
        address = str(data.get("address", "")).strip()
        city = str(data.get("city", "")).strip()
        price = data.get("price")


        # -------------------------------------------------
        # REQUIRED FIELDS
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

        if not phone:
            return jsonify({
                "success": False,
                "message": "Phone is required"
            }), 400

        if not password:
            return jsonify({
                "success": False,
                "message": "Password is required"
            }), 400

        if not service_type:
            return jsonify({
                "success": False,
                "message": "Service type is required"
            }), 400


        # -------------------------------------------------
        # PHONE VALIDATION
        # -------------------------------------------------

        if not phone.isdigit() or len(phone) != 10:

            return jsonify({
                "success": False,
                "message": "Phone number must contain exactly 10 digits"
            }), 400


        # -------------------------------------------------
        # SERVICE VALIDATION
        # -------------------------------------------------

        if service_type not in ALLOWED_SERVICE_TYPES:

            return jsonify({
                "success": False,
                "message": "Invalid service type",
                "allowed_services": sorted(
                    list(ALLOWED_SERVICE_TYPES)
                )
            }), 400


        # -------------------------------------------------
        # EXPERIENCE VALIDATION
        # -------------------------------------------------

        try:

            experience = int(
                experience if experience not in (None, "") else 0
            )

        except (TypeError, ValueError):

            return jsonify({
                "success": False,
                "message": "Experience must be a valid number"
            }), 400


        if experience < 0:

            return jsonify({
                "success": False,
                "message": "Experience cannot be negative"
            }), 400


        # -------------------------------------------------
        # PRICE VALIDATION
        # -------------------------------------------------

        if price in (None, ""):

            price = None

        else:

            try:

                price = float(price)

            except (TypeError, ValueError):

                return jsonify({
                    "success": False,
                    "message": "Price must be a valid number"
                }), 400


            if price < 0:

                return jsonify({
                    "success": False,
                    "message": "Price cannot be negative"
                }), 400


        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)


        # -------------------------------------------------
        # CHECK EMAIL
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM service_providers
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )

        existing_provider = cursor.fetchone()


        if existing_provider:

            return jsonify({
                "success": False,
                "message": "Provider with this email already exists"
            }), 409


        # -------------------------------------------------
        # PASSWORD HASH
        # -------------------------------------------------

        hashed_password = generate_password_hash(
            password
        )


        # -------------------------------------------------
        # INSERT PROVIDER
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO service_providers
            (
                name,
                email,
                phone,
                password,
                service_type,
                experience,
                price,
                address,
                city,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'pending'
            )
            """,
            (
                name,
                email,
                phone,
                hashed_password,
                service_type,
                experience,
                price,
                address,
                city
            )
        )


        connection.commit()

        provider_id = cursor.lastrowid


        return jsonify({
            "success": True,
            "message": "Provider registration successful. Waiting for admin approval.",
            "provider_id": provider_id,
            "status": "pending"
        }), 201


    except Exception as error:

        if connection:

            connection.rollback()


        print(
            "Provider signup error:",
            error
        )


        return jsonify({
            "success": False,
            "message": "Provider registration failed",
            "error": str(error)
        }), 500


    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()


# =========================================================
# PROVIDER LOGIN
# POST /api/providers/login
# =========================================================

@providers_bp.route("/login", methods=["POST"])
def provider_login():

    connection = None
    cursor = None

    try:

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "success": False,
                "message": "Request data is required"
            }), 400


        email = str(
            data.get("email", "")
        ).strip().lower()

        password = str(
            data.get("password", "")
        ).strip()


        if not email or not password:

            return jsonify({
                "success": False,
                "message": "Email and password are required"
            }), 400


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                password,
                service_type,
                experience,
                price,
                address,
                city,
                status,
                created_at,
                latitude
            FROM service_providers
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )


        provider = cursor.fetchone()


        if not provider:

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401


        # -------------------------------------------------
        # PASSWORD CHECK
        # -------------------------------------------------

        if not check_password_hash(
            provider["password"],
            password
        ):

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401


        # -------------------------------------------------
        # STATUS CHECK
        # -------------------------------------------------

        status = (
            str(provider["status"] or "pending")
            .strip()
            .lower()
        )


        if status == "pending":

            return jsonify({
                "success": False,
                "message": "Your provider account is waiting for admin approval.",
                "status": "pending"
            }), 403


        if status == "rejected":

            return jsonify({
                "success": False,
                "message": "Your provider account has been rejected by admin.",
                "status": "rejected"
            }), 403


        # -------------------------------------------------
        # REMOVE PASSWORD
        # -------------------------------------------------

        provider.pop(
            "password",
            None
        )


        return jsonify({
            "success": True,
            "message": "Provider login successful",
            "provider": provider
        }), 200


    except Exception as error:

        print(
            "Provider login error:",
            error
        )


        return jsonify({
            "success": False,
            "message": "Provider login failed",
            "error": str(error)
        }), 500


    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()


# =========================================================
# GET PROVIDER PROFILE
# GET /api/providers/<provider_id>
# =========================================================

@providers_bp.route("/<int:provider_id>", methods=["GET"])
def get_provider(provider_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                service_type,
                experience,
                price,
                address,
                city,
                status,
                created_at,
                latitude
            FROM service_providers
            WHERE id = %s
            LIMIT 1
            """,
            (provider_id,)
        )


        provider = cursor.fetchone()


        if not provider:

            return jsonify({
                "success": False,
                "message": "Provider not found"
            }), 404


        return jsonify({
            "success": True,
            "provider": provider
        }), 200


    except Exception as error:

        print(
            "Get provider error:",
            error
        )


        return jsonify({
            "success": False,
            "message": "Unable to fetch provider",
            "error": str(error)
        }), 500


    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()


# =========================================================
# UPDATE PROVIDER PROFILE
# PUT /api/providers/<provider_id>
# =========================================================

@providers_bp.route("/<int:provider_id>", methods=["PUT"])
def update_provider(provider_id):

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
        # GET VALUES
        # -------------------------------------------------

        name = data.get("name")
        phone = data.get("phone")
        service_type = data.get("service_type")
        experience = data.get("experience")
        price = data.get("price")
        address = data.get("address")
        city = data.get("city")


        # -------------------------------------------------
        # CLEAN VALUES
        # -------------------------------------------------

        if name is not None:

            name = str(name).strip()

        if phone is not None:

            phone = str(phone).strip()

        if service_type is not None:

            service_type = str(
                service_type
            ).strip()

        if address is not None:

            address = str(
                address
            ).strip()

        if city is not None:

            city = str(
                city
            ).strip()


        # -------------------------------------------------
        # CHECK PROVIDER
        # -------------------------------------------------

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT id
            FROM service_providers
            WHERE id = %s
            LIMIT 1
            """,
            (provider_id,)
        )


        provider_exists = cursor.fetchone()


        if not provider_exists:

            return jsonify({
                "success": False,
                "message": "Provider not found"
            }), 404


        # -------------------------------------------------
        # NAME
        # -------------------------------------------------

        if name is not None and not name:

            return jsonify({
                "success": False,
                "message": "Name cannot be empty"
            }), 400


        # -------------------------------------------------
        # PHONE
        # -------------------------------------------------

        if phone is not None:

            if (
                not phone.isdigit()
                or len(phone) != 10
            ):

                return jsonify({
                    "success": False,
                    "message": "Phone number must contain exactly 10 digits"
                }), 400


        # -------------------------------------------------
        # SERVICE
        # -------------------------------------------------

        if service_type is not None:

            if service_type not in ALLOWED_SERVICE_TYPES:

                return jsonify({
                    "success": False,
                    "message": "Invalid service type",
                    "allowed_services": sorted(
                        list(ALLOWED_SERVICE_TYPES)
                    )
                }), 400


        # -------------------------------------------------
        # EXPERIENCE
        # -------------------------------------------------

        if experience is not None:

            try:

                experience = int(
                    experience
                )

            except (TypeError, ValueError):

                return jsonify({
                    "success": False,
                    "message": "Experience must be a valid number"
                }), 400


            if experience < 0:

                return jsonify({
                    "success": False,
                    "message": "Experience cannot be negative"
                }), 400


        # -------------------------------------------------
        # PRICE
        # -------------------------------------------------

        if price is not None:

            if price == "":

                price = None

            else:

                try:

                    price = float(price)

                except (TypeError, ValueError):

                    return jsonify({
                        "success": False,
                        "message": "Price must be a valid number"
                    }), 400


                if price < 0:

                    return jsonify({
                        "success": False,
                        "message": "Price cannot be negative"
                    }), 400


        # -------------------------------------------------
        # UPDATE PROVIDER
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE service_providers
            SET
                name = COALESCE(%s, name),
                phone = COALESCE(%s, phone),
                service_type = COALESCE(%s, service_type),
                experience = COALESCE(%s, experience),
                price = COALESCE(%s, price),
                address = COALESCE(%s, address),
                city = COALESCE(%s, city)
            WHERE id = %s
            """,
            (
                name,
                phone,
                service_type,
                experience,
                price,
                address,
                city,
                provider_id
            )
        )


        connection.commit()


        # -------------------------------------------------
        # GET UPDATED PROVIDER
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                service_type,
                experience,
                price,
                address,
                city,
                status,
                created_at,
                latitude
            FROM service_providers
            WHERE id = %s
            LIMIT 1
            """,
            (provider_id,)
        )


        updated_provider = cursor.fetchone()


        return jsonify({
            "success": True,
            "message": "Provider profile updated successfully",
            "provider": updated_provider
        }), 200


    except Exception as error:

        if connection:

            connection.rollback()


        print(
            "Update provider error:",
            error
        )


        return jsonify({
            "success": False,
            "message": "Unable to update provider profile",
            "error": str(error)
        }), 500


    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()


# =========================================================
# UPDATE PROVIDER LOCATION
# PUT /api/providers/<provider_id>/location
# =========================================================

@providers_bp.route(
    "/<int:provider_id>/location",
    methods=["PUT"]
)
def update_provider_location(provider_id):

    connection = None
    cursor = None

    try:

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "success": False,
                "message": "Request data is required"
            }), 400


        latitude = data.get("latitude")
        longitude = data.get("longitude")


        if latitude is None or longitude is None:

            return jsonify({
                "success": False,
                "message": "Latitude and longitude are required"
            }), 400


        try:

            latitude = float(latitude)
            longitude = float(longitude)

        except (TypeError, ValueError):

            return jsonify({
                "success": False,
                "message": "Latitude and longitude must be valid numbers"
            }), 400


        if not (-90 <= latitude <= 90):

            return jsonify({
                "success": False,
                "message": "Invalid latitude"
            }), 400


        if not (-180 <= longitude <= 180):

            return jsonify({
                "success": False,
                "message": "Invalid longitude"
            }), 400


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT id
            FROM service_providers
            WHERE id = %s
            LIMIT 1
            """,
            (provider_id,)
        )


        provider = cursor.fetchone()


        if not provider:

            return jsonify({
                "success": False,
                "message": "Provider not found"
            }), 404


        cursor.execute(
            """
            UPDATE service_providers
            SET
                latitude = %s
            WHERE id = %s
            """,
            (
                latitude,
                provider_id
            )
        )


        connection.commit()


        return jsonify({
            "success": True,
            "message": "Provider location updated successfully",
            "latitude": latitude,
            "longitude": longitude
        }), 200


    except Exception as error:

        if connection:

            connection.rollback()


        print(
            "Provider location error:",
            error
        )


        return jsonify({
            "success": False,
            "message": "Unable to update provider location",
            "error": str(error)
        }), 500


    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()


# =========================================================
# GET ALL PROVIDERS
# GET /api/providers
# =========================================================

@providers_bp.route("", methods=["GET"])
def get_all_providers():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                service_type,
                experience,
                price,
                address,
                city,
                status,
                created_at,
                latitude
            FROM service_providers
            WHERE LOWER(status) = 'approved'
            ORDER BY id DESC
            """
        )


        providers = cursor.fetchall()


        return jsonify({
            "success": True,
            "count": len(providers),
            "providers": providers
        }), 200


    except Exception as error:

        print(
            "Get all providers error:",
            error
        )


        return jsonify({
            "success": False,
            "message": "Unable to fetch providers",
            "error": str(error)
        }), 500


    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()