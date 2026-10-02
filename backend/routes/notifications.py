from flask import Blueprint, request, jsonify
from db import get_db_connection

notifications_bp = Blueprint("notifications", __name__)


# =========================================================
# GET USER NOTIFICATIONS
# GET /api/notifications/user/<user_id>
# =========================================================
@notifications_bp.route("/user/<int:user_id>", methods=["GET"])
def get_user_notifications(user_id):
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
                n.type,
                n.message,
                n.is_read,
                n.created_at
            FROM notifications n
            WHERE n.user_id = %s
            ORDER BY n.id DESC
            """,
            (user_id,)
        )

        notifications = cursor.fetchall()

        return jsonify({
            "success": True,
            "count": len(notifications),
            "notifications": notifications
        }), 200

    except Exception as error:
        print("Get user notifications error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch user notifications",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# GET PROVIDER NOTIFICATIONS
# GET /api/notifications/provider/<provider_id>
# =========================================================
@notifications_bp.route("/provider/<int:provider_id>", methods=["GET"])
def get_provider_notifications(provider_id):
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
                n.type,
                n.message,
                n.is_read,
                n.created_at
            FROM notifications n
            WHERE n.provider_id = %s
            ORDER BY n.id DESC
            """,
            (provider_id,)
        )

        notifications = cursor.fetchall()

        return jsonify({
            "success": True,
            "count": len(notifications),
            "notifications": notifications
        }), 200

    except Exception as error:
        print("Get provider notifications error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch provider notifications",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# MARK ONE NOTIFICATION AS READ
# PUT /api/notifications/<notification_id>/read
# =========================================================
@notifications_bp.route("/<int:notification_id>/read", methods=["PUT"])
def mark_notification_read(notification_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM notifications
            WHERE id = %s
            LIMIT 1
            """,
            (notification_id,)
        )

        notification = cursor.fetchone()

        if not notification:
            return jsonify({
                "success": False,
                "message": "Notification not found"
            }), 404

        cursor.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = %s
            """,
            (notification_id,)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Notification marked as read"
        }), 200

    except Exception as error:
        if connection:
            connection.rollback()

        print("Mark notification read error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to update notification",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# MARK ALL USER NOTIFICATIONS AS READ
# PUT /api/notifications/user/<user_id>/read-all
# =========================================================
@notifications_bp.route("/user/<int:user_id>/read-all", methods=["PUT"])
def mark_all_user_notifications_read(user_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE user_id = %s
            """,
            (user_id,)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "All user notifications marked as read",
            "updated": cursor.rowcount
        }), 200

    except Exception as error:
        if connection:
            connection.rollback()

        print("Mark all user notifications error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to update user notifications",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# MARK ALL PROVIDER NOTIFICATIONS AS READ
# PUT /api/notifications/provider/<provider_id>/read-all
# =========================================================
@notifications_bp.route("/provider/<int:provider_id>/read-all", methods=["PUT"])
def mark_all_provider_notifications_read(provider_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE provider_id = %s
            """,
            (provider_id,)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "All provider notifications marked as read",
            "updated": cursor.rowcount
        }), 200

    except Exception as error:
        if connection:
            connection.rollback()

        print("Mark all provider notifications error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to update provider notifications",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()