from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os

from db import get_db_connection

from routes.auth import auth_bp
from routes.providers import providers_bp
from routes.admin import admin_bp
from routes.bookings import bookings_bp
from routes.payments import payments_bp
from routes.reviews import reviews_bp
from routes.notifications import notifications_bp


# --------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


# --------------------------------------------------
# FLASK APP
# --------------------------------------------------

app = Flask(__name__)


app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "local-service-booking-secret-key"
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*"
        }
    }
)


# --------------------------------------------------
# REGISTER API BLUEPRINTS
# --------------------------------------------------

app.register_blueprint(
    auth_bp,
    url_prefix="/api/auth"
)

app.register_blueprint(
    providers_bp,
    url_prefix="/api/providers"
)

app.register_blueprint(
    admin_bp,
    url_prefix="/api/admin"
)

app.register_blueprint(
    bookings_bp,
    url_prefix="/api/bookings"
)

app.register_blueprint(
    payments_bp,
    url_prefix="/api/payments"
)

app.register_blueprint(
    reviews_bp,
    url_prefix="/api/reviews"
)

app.register_blueprint(
    notifications_bp,
    url_prefix="/api/notifications"
)


# ==================================================
# FRONTEND ROUTES
# ==================================================


# --------------------------------------------------
# HOME
# Opens login.html
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return send_from_directory(
        FRONTEND_DIR,
        "login.html"
    )


# --------------------------------------------------
# SERVE FRONTEND HTML FILES
# Example:
# /signup.html
# /index.html
# /booking.html
# --------------------------------------------------

@app.route("/<path:filename>", methods=["GET"])
def frontend_files(filename):

    file_path = os.path.join(
        FRONTEND_DIR,
        filename
    )

    if os.path.isfile(file_path):
        return send_from_directory(
            FRONTEND_DIR,
            filename
        )

    return jsonify({
        "success": False,
        "message": "Frontend file not found"
    }), 404


# ==================================================
# API HEALTH CHECK
# ==================================================

@app.route("/api/health", methods=["GET"])
def health():

    connection = None

    try:

        connection = get_db_connection()

        if connection.is_connected():

            return jsonify({
                "success": True,
                "message": "Backend and MySQL connected successfully"
            })

        return jsonify({
            "success": False,
            "message": "MySQL connection failed"
        }), 500

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Database connection error",
            "error": str(error)
        }), 500

    finally:

        if connection is not None:

            try:
                if connection.is_connected():
                    connection.close()
            except Exception:
                pass


# ==================================================
# ERROR HANDLERS
# ==================================================


@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "message": "API endpoint or frontend file not found"
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify({
        "success": False,
        "message": "HTTP method not allowed"
    }), 405


# ==================================================
# RUN SERVER
# ==================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )