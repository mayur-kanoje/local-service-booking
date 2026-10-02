from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from datetime import datetime, date, time, timedelta
from decimal import Decimal

from db import get_db_connection


# =========================================================
# BLUEPRINT
# =========================================================

admin_bp = Blueprint("admin", __name__)


# =========================================================
# JSON SERIALIZER
# =========================================================

def serialize_value(value):

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, timedelta):

        total_seconds = int(value.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    return value


def serialize_rows(rows):

    return [
        {
            key: serialize_value(value)
            for key, value in row.items()
        }
        for row in rows
    ]


# =========================================================
# ADMIN LOGIN
# POST /api/admin/login
# =========================================================

@admin_bp.route("/login", methods=["POST"])
def admin_login():

    connection = None
    cursor = None

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Request data is required"
            }), 400

        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

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

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password
            FROM admins
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )

        admin = cursor.fetchone()

        if not admin:
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        if not check_password_hash(
            admin["password"],
            password
        ):
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        return jsonify({
            "success": True,
            "message": "Admin login successful",
            "admin": {
                "id": admin["id"],
                "name": admin["name"],
                "email": admin["email"]
            }
        }), 200

    except Exception as error:

        print("Admin login error:", error)

        return jsonify({
            "success": False,
            "message": "Admin login failed",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN DASHBOARD STATS
# GET /api/admin/dashboard-stats
# =========================================================

@admin_bp.route("/dashboard-stats", methods=["GET"])
def dashboard_stats():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # TOTAL USERS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total_users
            FROM users
            """
        )

        user_result = cursor.fetchone()

        total_users = int(
            user_result["total_users"] or 0
        )

        # -------------------------------------------------
        # TOTAL PROVIDERS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total_providers
            FROM service_providers
            """
        )

        provider_result = cursor.fetchone()

        total_providers = int(
            provider_result["total_providers"] or 0
        )

        # -------------------------------------------------
        # TOTAL BOOKINGS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total_bookings
            FROM bookings
            """
        )

        booking_result = cursor.fetchone()

        total_bookings = int(
            booking_result["total_bookings"] or 0
        )

        # -------------------------------------------------
        # TOTAL REVENUE
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS total_revenue
            FROM payments
            WHERE LOWER(status) IN (
                'success',
                'successful',
                'completed',
                'paid'
            )
            """
        )

        revenue_result = cursor.fetchone()

        total_revenue = float(
            revenue_result["total_revenue"] or 0
        )

        # -------------------------------------------------
        # BOOKING STATUS COUNTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT

                SUM(
                    CASE
                        WHEN LOWER(status) = 'pending'
                        THEN 1
                        ELSE 0
                    END
                ) AS pending_bookings,

                SUM(
                    CASE
                        WHEN LOWER(status) = 'accepted'
                        THEN 1
                        ELSE 0
                    END
                ) AS accepted_bookings,

                SUM(
                    CASE
                        WHEN LOWER(status) = 'completed'
                        THEN 1
                        ELSE 0
                    END
                ) AS completed_bookings,

                SUM(
                    CASE
                        WHEN LOWER(status) = 'rejected'
                        THEN 1
                        ELSE 0
                    END
                ) AS rejected_bookings,

                SUM(
                    CASE
                        WHEN LOWER(status) = 'cancelled'
                        THEN 1
                        ELSE 0
                    END
                ) AS cancelled_bookings

            FROM bookings
            """
        )

        status_result = cursor.fetchone()

        return jsonify({
            "success": True,

            "stats": {

                "total_users": total_users,

                "total_providers": total_providers,

                "total_bookings": total_bookings,

                "total_revenue": total_revenue,

                "pending_bookings": int(
                    status_result["pending_bookings"] or 0
                ),

                "accepted_bookings": int(
                    status_result["accepted_bookings"] or 0
                ),

                "completed_bookings": int(
                    status_result["completed_bookings"] or 0
                ),

                "rejected_bookings": int(
                    status_result["rejected_bookings"] or 0
                ),

                "cancelled_bookings": int(
                    status_result["cancelled_bookings"] or 0
                )
            }

        }), 200

    except Exception as error:

        print("Admin dashboard stats error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch dashboard statistics",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# GET ALL USERS FOR ADMIN
# GET /api/admin/users
# =========================================================

@admin_bp.route("/users", methods=["GET"])
def get_admin_users():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                address,
                city,
                created_at
            FROM users
            ORDER BY id DESC
            """
        )

        users = cursor.fetchall()

        users = serialize_rows(users)

        return jsonify({
            "success": True,
            "count": len(users),
            "users": users
        }), 200

    except Exception as error:

        print("Admin users error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch users",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# RECENT BOOKINGS
# GET /api/admin/recent-bookings
# =========================================================

@admin_bp.route("/recent-bookings", methods=["GET"])
def recent_bookings():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT

                b.id,
                b.user_id,
                b.provider_id,
                b.service_id,

                b.booking_date,
                b.booking_time,
                b.address,

                b.amount,
                b.total_amount,
                b.status,
                b.created_at,

                u.name AS user_name,
                u.email AS user_email,

                sp.name AS provider_name,
                sp.service_type AS provider_service,

                s.name AS service_name

            FROM bookings b

            LEFT JOIN users u
                ON b.user_id = u.id

            LEFT JOIN service_providers sp
                ON b.provider_id = sp.id

            LEFT JOIN services s
                ON b.service_id = s.id

            ORDER BY b.id DESC

            LIMIT 10
            """
        )

        bookings = cursor.fetchall()

        bookings = serialize_rows(bookings)

        return jsonify({
            "success": True,
            "count": len(bookings),
            "bookings": bookings
        }), 200

    except Exception as error:

        print("Admin recent bookings error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch recent bookings",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# GET ALL PROVIDERS FOR ADMIN
# GET /api/admin/providers
# =========================================================

@admin_bp.route("/providers", methods=["GET"])
def get_admin_providers():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                service_type,
                experience,
                address,
                city,
                status,
                latitude,
                longitude,
                created_at
            FROM service_providers
            ORDER BY id DESC
            """
        )

        providers = cursor.fetchall()

        providers = serialize_rows(providers)

        return jsonify({
            "success": True,
            "count": len(providers),
            "providers": providers
        }), 200

    except Exception as error:

        print("Admin providers error:", error)

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


# =========================================================
# APPROVE PROVIDER
# PUT /api/admin/providers/<provider_id>/approve
# =========================================================

@admin_bp.route(
    "/providers/<int:provider_id>/approve",
    methods=["PUT"]
)
def approve_provider(provider_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                status
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

        if provider["status"] == "approved":

            return jsonify({
                "success": True,
                "message": "Provider is already approved",
                "provider": provider
            }), 200

        cursor.execute(
            """
            UPDATE service_providers
            SET status = 'approved'
            WHERE id = %s
            """,
            (provider_id,)
        )

        connection.commit()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                service_type,
                experience,
                address,
                city,
                status,
                latitude,
                longitude
            FROM service_providers
            WHERE id = %s
            LIMIT 1
            """,
            (provider_id,)
        )

        updated_provider = cursor.fetchone()

        updated_provider = {
            key: serialize_value(value)
            for key, value in updated_provider.items()
        }

        return jsonify({
            "success": True,
            "message": "Provider approved successfully",
            "provider": updated_provider
        }), 200

    except Exception as error:

        if connection:
            connection.rollback()

        print("Approve provider error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to approve provider",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# REJECT PROVIDER
# PUT /api/admin/providers/<provider_id>/reject
# =========================================================

@admin_bp.route(
    "/providers/<int:provider_id>/reject",
    methods=["PUT"]
)
def reject_provider(provider_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                status
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
            SET status = 'rejected'
            WHERE id = %s
            """,
            (provider_id,)
        )

        connection.commit()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                service_type,
                experience,
                address,
                city,
                status,
                latitude,
                longitude
            FROM service_providers
            WHERE id = %s
            LIMIT 1
            """,
            (provider_id,)
        )

        updated_provider = cursor.fetchone()

        updated_provider = {
            key: serialize_value(value)
            for key, value in updated_provider.items()
        }

        return jsonify({
            "success": True,
            "message": "Provider rejected successfully",
            "provider": updated_provider
        }), 200

    except Exception as error:

        if connection:
            connection.rollback()

        print("Reject provider error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to reject provider",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()
            # =========================================================
# ADMIN - ALL BOOKINGS
# GET /api/admin/bookings
# =========================================================

@admin_bp.route("/bookings", methods=["GET"])
def get_admin_bookings():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                b.id,
                b.user_id,
                b.provider_id,
                b.service_id,

                u.name AS user_name,
                u.email AS user_email,

                sp.name AS provider_name,
                sp.service_type AS provider_service,

                s.name AS service_name,

                b.booking_date,
                b.booking_time,
                b.address,
                b.description,

                b.amount,
                b.total_amount,
                b.status,
                b.notes,
                b.created_at

            FROM bookings b

            LEFT JOIN users u
                ON b.user_id = u.id

            LEFT JOIN service_providers sp
                ON b.provider_id = sp.id

            LEFT JOIN services s
                ON b.service_id = s.id

            ORDER BY b.id DESC
            """
        )

        bookings = cursor.fetchall()

        bookings = serialize_rows(bookings)

        return jsonify({
            "success": True,
            "count": len(bookings),
            "bookings": bookings
        }), 200

    except Exception as error:

        print("Admin bookings error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch bookings",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - ALL PAYMENTS
# GET /api/admin/payments
# =========================================================

@admin_bp.route("/payments", methods=["GET"])
def get_admin_payments():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                p.id,
                p.booking_id,
                p.user_id,

                u.name AS user_name,
                u.email AS user_email,

                b.provider_id,
                sp.name AS provider_name,

                b.service_id,
                s.name AS service_name,

                p.amount,
                p.payment_method,
                p.transaction_id,
                p.status,
                p.payment_date

            FROM payments p

            LEFT JOIN users u
                ON p.user_id = u.id

            LEFT JOIN bookings b
                ON p.booking_id = b.id

            LEFT JOIN service_providers sp
                ON b.provider_id = sp.id

            LEFT JOIN services s
                ON b.service_id = s.id

            ORDER BY p.id DESC
            """
        )

        payments = cursor.fetchall()

        payments = serialize_rows(payments)

        return jsonify({
            "success": True,
            "count": len(payments),
            "payments": payments
        }), 200

    except Exception as error:

        print("Admin payments error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch payments",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - ALL REVIEWS
# GET /api/admin/reviews
# =========================================================

@admin_bp.route("/reviews", methods=["GET"])
def get_admin_reviews():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                r.id,
                r.booking_id,
                r.user_id,
                r.provider_id,

                u.name AS user_name,
                u.email AS user_email,

                sp.name AS provider_name,

                r.rating,
                r.comment,
                r.created_at

            FROM reviews r

            LEFT JOIN users u
                ON r.user_id = u.id

            LEFT JOIN service_providers sp
                ON r.provider_id = sp.id

            ORDER BY r.id DESC
            """
        )

        reviews = cursor.fetchall()

        reviews = serialize_rows(reviews)

        return jsonify({
            "success": True,
            "count": len(reviews),
            "reviews": reviews
        }), 200

    except Exception as error:

        print("Admin reviews error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch reviews",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - ALL NOTIFICATIONS
# GET /api/admin/notifications
# =========================================================

@admin_bp.route("/notifications", methods=["GET"])
def get_admin_notifications():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                n.id,
                n.user_id,
                n.provider_id,
                n.booking_id,

                u.name AS user_name,
                sp.name AS provider_name,

                n.type,
                n.message,
                n.is_read,
                n.created_at

            FROM notifications n

            LEFT JOIN users u
                ON n.user_id = u.id

            LEFT JOIN service_providers sp
                ON n.provider_id = sp.id

            ORDER BY n.id DESC
            """
        )

        notifications = cursor.fetchall()

        notifications = serialize_rows(notifications)

        return jsonify({
            "success": True,
            "count": len(notifications),
            "notifications": notifications
        }), 200

    except Exception as error:

        print("Admin notifications error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch notifications",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()
            # =========================================================
# ADMIN SETTINGS
# GET /api/admin/settings/<admin_id>
# =========================================================

@admin_bp.route("/settings/<int:admin_id>", methods=["GET"])
def get_admin_settings(admin_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email
            FROM admins
            WHERE id = %s
            LIMIT 1
            """,
            (admin_id,)
        )

        admin = cursor.fetchone()

        if not admin:
            return jsonify({
                "success": False,
                "message": "Admin not found"
            }), 404

        return jsonify({
            "success": True,
            "admin": admin
        }), 200

    except Exception as error:

        print("Admin settings error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to load admin settings",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# UPDATE ADMIN PROFILE
# PUT /api/admin/settings/<admin_id>
# =========================================================

@admin_bp.route("/settings/<int:admin_id>", methods=["PUT"])
def update_admin_settings(admin_id):

    connection = None
    cursor = None

    try:

        data = request.get_json(silent=True) or {}

        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()

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

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM admins
            WHERE email = %s
              AND id != %s
            LIMIT 1
            """,
            (email, admin_id)
        )

        existing = cursor.fetchone()

        if existing:
            return jsonify({
                "success": False,
                "message": "This email is already used by another admin"
            }), 409

        cursor.execute(
            """
            UPDATE admins
            SET name = %s,
                email = %s
            WHERE id = %s
            """,
            (name, email, admin_id)
        )

        connection.commit()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email
            FROM admins
            WHERE id = %s
            LIMIT 1
            """,
            (admin_id,)
        )

        admin = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Admin profile updated successfully",
            "admin": admin
        }), 200

    except Exception as error:

        if connection:
            connection.rollback()

        print("Update admin settings error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to update admin profile",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# CHANGE ADMIN PASSWORD
# PUT /api/admin/settings/<admin_id>/password
# =========================================================

@admin_bp.route(
    "/settings/<int:admin_id>/password",
    methods=["PUT"]
)
def change_admin_password(admin_id):

    connection = None
    cursor = None

    try:

        data = request.get_json(silent=True) or {}

        current_password = str(
            data.get("current_password", "")
        )

        new_password = str(
            data.get("new_password", "")
        )

        if not current_password:
            return jsonify({
                "success": False,
                "message": "Current password is required"
            }), 400

        if not new_password:
            return jsonify({
                "success": False,
                "message": "New password is required"
            }), 400

        if len(new_password) < 6:
            return jsonify({
                "success": False,
                "message": "New password must contain at least 6 characters"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT password
            FROM admins
            WHERE id = %s
            LIMIT 1
            """,
            (admin_id,)
        )

        admin = cursor.fetchone()

        if not admin:
            return jsonify({
                "success": False,
                "message": "Admin not found"
            }), 404

        if not check_password_hash(
            admin["password"],
            current_password
        ):
            return jsonify({
                "success": False,
                "message": "Current password is incorrect"
            }), 401

        from werkzeug.security import generate_password_hash

        new_password_hash = generate_password_hash(
            new_password
        )

        cursor.execute(
            """
            UPDATE admins
            SET password = %s
            WHERE id = %s
            """,
            (new_password_hash, admin_id)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Password changed successfully"
        }), 200

    except Exception as error:

        if connection:
            connection.rollback()

        print("Change admin password error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to change password",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()