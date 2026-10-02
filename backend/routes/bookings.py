from flask import Blueprint, request, jsonify
from datetime import date, datetime, timedelta
from decimal import Decimal

from db import get_db_connection


# =========================================================
# BLUEPRINT
# =========================================================

bookings_bp = Blueprint("bookings", __name__)


# =========================================================
# ALLOWED BOOKING STATUS
# =========================================================

ALLOWED_STATUS = {
    "pending",
    "accepted",
    "rejected",
    "completed",
    "cancelled"
}


# =========================================================
# JSON SERIALIZATION HELPERS
# =========================================================

def serialize_value(value):

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, timedelta):
        return str(value)

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    return value


def serialize_row(row):

    if not row:
        return row

    return {
        key: serialize_value(value)
        for key, value in row.items()
    }


def serialize_rows(rows):

    return [
        serialize_row(row)
        for row in rows
    ]


# =========================================================
# CREATE BOOKING
# POST /api/bookings
# =========================================================

@bookings_bp.route("", methods=["POST"])
def create_booking():

    connection = None
    cursor = None

    try:

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "success": False,
                "message": "Request data is required"
            }), 400

        user_id = data.get("user_id")
        provider_id = data.get("provider_id")
        service_id = data.get("service_id")

        booking_date = data.get("booking_date")
        booking_time = data.get("booking_time")

        address = str(
            data.get("address", "")
        ).strip()

        description = str(
            data.get("description", "")
        ).strip()

        notes = str(
            data.get("notes", "")
        ).strip()

        latitude = data.get("latitude")
        longitude = data.get("longitude")

        amount = data.get("amount", 0)

        total_amount = data.get(
            "total_amount",
            amount
        )

        # -------------------------------------------------
        # REQUIRED VALIDATION
        # -------------------------------------------------

        if not user_id:

            return jsonify({
                "success": False,
                "message": "User ID is required"
            }), 400

        if not service_id:

            return jsonify({
                "success": False,
                "message": "Service ID is required"
            }), 400

        if not booking_date:

            return jsonify({
                "success": False,
                "message": "Booking date is required"
            }), 400

        if not booking_time:

            return jsonify({
                "success": False,
                "message": "Booking time is required"
            }), 400

        if not address:

            return jsonify({
                "success": False,
                "message": "Service address is required"
            }), 400

        # -------------------------------------------------
        # AMOUNT VALIDATION
        # -------------------------------------------------

        try:

            amount = float(amount or 0)

            total_amount = float(
                total_amount or amount
            )

        except (TypeError, ValueError):

            return jsonify({
                "success": False,
                "message": "Invalid booking amount"
            }), 400

        if amount < 0 or total_amount < 0:

            return jsonify({
                "success": False,
                "message": "Booking amount cannot be negative"
            }), 400

        # -------------------------------------------------
        # LOCATION VALIDATION
        # -------------------------------------------------

        if latitude is not None:

            try:

                latitude = float(latitude)

            except (TypeError, ValueError):

                return jsonify({
                    "success": False,
                    "message": "Invalid latitude"
                }), 400

            if latitude < -90 or latitude > 90:

                return jsonify({
                    "success": False,
                    "message": "Invalid latitude"
                }), 400

        if longitude is not None:

            try:

                longitude = float(longitude)

            except (TypeError, ValueError):

                return jsonify({
                    "success": False,
                    "message": "Invalid longitude"
                }), 400

            if longitude < -180 or longitude > 180:

                return jsonify({
                    "success": False,
                    "message": "Invalid longitude"
                }), 400

        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # CHECK USER
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                name
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        if not user:

            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        # -------------------------------------------------
        # CHECK SERVICE
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                name,
                description,
                base_price
            FROM services
            WHERE id = %s
            LIMIT 1
            """,
            (service_id,)
        )

        service = cursor.fetchone()

        if not service:

            return jsonify({
                "success": False,
                "message": "Service not found"
            }), 404

        # -------------------------------------------------
        # SERVICE BASE PRICE
        # -------------------------------------------------

        if total_amount <= 0:

            total_amount = float(
                service["base_price"] or 0
            )

        if amount <= 0:

            amount = total_amount

        # -------------------------------------------------
        # CHECK PROVIDER
        # -------------------------------------------------

        if provider_id is not None:

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    service_type,
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

            if str(
                provider["status"] or ""
            ).lower() != "approved":

                return jsonify({
                    "success": False,
                    "message": "Selected provider is not approved"
                }), 400

        # -------------------------------------------------
        # CREATE BOOKING
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO bookings
            (
                user_id,
                provider_id,
                service_id,
                booking_date,
                booking_time,
                address,
                description,
                amount,
                status,
                notes,
                total_amount,
                latitude,
                longitude
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
                'pending',
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                provider_id,
                service_id,
                booking_date,
                booking_time,
                address,
                description if description else None,
                amount,
                notes if notes else None,
                total_amount,
                latitude,
                longitude
            )
        )

        booking_id = cursor.lastrowid

        # -------------------------------------------------
        # PROVIDER NOTIFICATION
        # -------------------------------------------------

        if provider_id is not None:

            notification_message = (
                f"New booking received for "
                f"{service['name']}."
            )

            cursor.execute(
                """
                INSERT INTO notifications
                (
                    user_id,
                    provider_id,
                    booking_id,
                    type,
                    message,
                    is_read
                )
                VALUES
                (
                    NULL,
                    %s,
                    %s,
                    %s,
                    %s,
                    0
                )
                """,
                (
                    provider_id,
                    booking_id,
                    "new_booking",
                    notification_message
                )
            )

        connection.commit()

        # -------------------------------------------------
        # GET CREATED BOOKING
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                b.id,
                b.user_id,
                b.provider_id,
                b.service_id,
                s.name AS service_name,
                b.booking_date,
                b.booking_time,
                b.address,
                b.description,
                b.amount,
                b.total_amount,
                b.status,
                b.notes,
                b.latitude,
                b.longitude,
                b.created_at
            FROM bookings b
            INNER JOIN services s
                ON b.service_id = s.id
            WHERE b.id = %s
            LIMIT 1
            """,
            (booking_id,)
        )

        booking = cursor.fetchone()

        booking = serialize_row(booking)

        return jsonify({
            "success": True,
            "message": "Booking created successfully",
            "booking": booking
        }), 201

    except Exception as error:

        if connection:

            try:
                connection.rollback()
            except Exception:
                pass

        print(
            "Create booking error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to create booking",
            "error": str(error)
        }), 500

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if connection:

            try:
                connection.close()
            except Exception:
                pass


# =========================================================
# GET USER BOOKINGS
# GET /api/bookings/user/<user_id>
# =========================================================

@bookings_bp.route(
    "/user/<int:user_id>",
    methods=["GET"]
)
def get_user_bookings(user_id):

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
                b.id,
                b.user_id,
                b.provider_id,
                b.service_id,

                s.name AS service_name,
                s.description AS service_description,

                p.name AS provider_name,
                p.phone AS provider_phone,
                p.service_type AS provider_service,
                p.price AS provider_price,
                p.experience AS provider_experience,
                p.address AS provider_address,
                p.city AS provider_city,

                b.booking_date,
                b.booking_time,
                b.address,
                b.description,
                b.amount,
                b.total_amount,
                b.status,
                b.notes,
                b.latitude,
                b.longitude,
                b.created_at

            FROM bookings b

            INNER JOIN services s
                ON b.service_id = s.id

            LEFT JOIN service_providers p
                ON b.provider_id = p.id

            WHERE b.user_id = %s

            ORDER BY b.id DESC
            """,
            (user_id,)
        )

        bookings = cursor.fetchall()

        bookings = serialize_rows(
            bookings
        )

        return jsonify({
            "success": True,
            "count": len(bookings),
            "bookings": bookings
        }), 200

    except Exception as error:

        print(
            "Get user bookings error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to fetch user bookings",
            "error": str(error)
        }), 500

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if connection:

            try:
                connection.close()
            except Exception:
                pass


# =========================================================
# GET PROVIDER BOOKINGS
# GET /api/bookings/provider/<provider_id>
# =========================================================

@bookings_bp.route(
    "/provider/<int:provider_id>",
    methods=["GET"]
)
def get_provider_bookings(provider_id):

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
                b.id,
                b.user_id,
                b.provider_id,
                b.service_id,

                u.name AS user_name,
                u.email AS user_email,
                u.phone AS user_phone,

                s.name AS service_name,
                s.description AS service_description,

                b.booking_date,
                b.booking_time,
                b.address,
                b.description,
                b.amount,
                b.total_amount,
                b.status,
                b.notes,
                b.latitude,
                b.longitude,
                b.created_at

            FROM bookings b

            INNER JOIN users u
                ON b.user_id = u.id

            INNER JOIN services s
                ON b.service_id = s.id

            WHERE b.provider_id = %s

            ORDER BY b.id DESC
            """,
            (provider_id,)
        )

        bookings = cursor.fetchall()

        bookings = serialize_rows(
            bookings
        )

        return jsonify({
            "success": True,
            "count": len(bookings),
            "bookings": bookings
        }), 200

    except Exception as error:

        print(
            "Get provider bookings error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to fetch provider bookings",
            "error": str(error)
        }), 500

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if connection:

            try:
                connection.close()
            except Exception:
                pass


# =========================================================
# UPDATE BOOKING STATUS
# PUT /api/bookings/<booking_id>/status
# =========================================================

@bookings_bp.route(
    "/<int:booking_id>/status",
    methods=["PUT"]
)
def update_booking_status(booking_id):

    connection = None
    cursor = None

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "message": "Request data is required"
            }), 400

        new_status = str(
            data.get("status", "")
        ).strip().lower()

        if new_status not in ALLOWED_STATUS:

            return jsonify({
                "success": False,
                "message": "Invalid booking status"
            }), 400

        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # GET BOOKING
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                b.id,
                b.user_id,
                b.provider_id,
                b.service_id,
                b.amount,
                b.total_amount,
                b.status,
                s.name AS service_name
            FROM bookings b
            INNER JOIN services s
                ON b.service_id = s.id
            WHERE b.id = %s
            LIMIT 1
            """,
            (booking_id,)
        )

        booking = cursor.fetchone()

        if not booking:

            return jsonify({
                "success": False,
                "message": "Booking not found"
            }), 404

        old_status = str(
            booking["status"] or ""
        ).lower()

        # -------------------------------------------------
        # PREVENT SAME STATUS
        # -------------------------------------------------

        if old_status == new_status:

            return jsonify({
                "success": True,
                "message": (
                    f"Booking is already "
                    f"{new_status}"
                ),
                "status": new_status
            }), 200

        # =================================================
        # IMPORTANT PAYMENT CHECK
        # =================================================
        #
        # A provider cannot complete a booking
        # until the user has successfully paid.
        #

        if new_status == "completed":

            # ---------------------------------------------
            # BOOKING MUST BE ACCEPTED FIRST
            # ---------------------------------------------

            if old_status != "accepted":

                return jsonify({
                    "success": False,
                    "message": (
                        "Only an accepted booking "
                        "can be completed."
                    )
                }), 400

            # ---------------------------------------------
            # CHECK SUCCESSFUL PAYMENT
            # ---------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    booking_id,
                    user_id,
                    amount,
                    payment_method,
                    transaction_id,
                    status,
                    payment_date
                FROM payments
                WHERE booking_id = %s
                  AND user_id = %s
                  AND LOWER(status) IN
                      (
                          'success',
                          'successful',
                          'completed',
                          'paid'
                      )
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    booking_id,
                    booking["user_id"]
                )
            )

            payment = cursor.fetchone()

            if not payment:

                return jsonify({
                    "success": False,
                    "message": (
                        "Payment is required "
                        "before completing this booking."
                    ),
                    "payment_required": True
                }), 400

            # ---------------------------------------------
            # VERIFY PAYMENT AMOUNT
            # ---------------------------------------------

            booking_amount = float(
                booking["total_amount"]
                or booking["amount"]
                or 0
            )

            payment_amount = float(
                payment["amount"]
                or 0
            )

            if booking_amount > 0:

                if abs(
                    payment_amount - booking_amount
                ) > 0.01:

                    return jsonify({
                        "success": False,
                        "message": (
                            "Payment amount does not "
                            "match the booking amount."
                        ),
                        "payment_required": True
                    }), 400

        # =================================================
        # UPDATE STATUS
        # =================================================

        cursor.execute(
            """
            UPDATE bookings
            SET status = %s
            WHERE id = %s
            """,
            (
                new_status,
                booking_id
            )
        )

        # =================================================
        # USER NOTIFICATION
        # =================================================

        status_message = (
            f"Your booking for "
            f"{booking['service_name']} "
            f"is now {new_status}."
        )

        cursor.execute(
            """
            INSERT INTO notifications
            (
                user_id,
                provider_id,
                booking_id,
                type,
                message,
                is_read
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                0
            )
            """,
            (
                booking["user_id"],
                booking["provider_id"],
                booking_id,
                "booking_status",
                status_message
            )
        )

        connection.commit()

        # -------------------------------------------------
        # GET UPDATED BOOKING
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                b.id,
                b.user_id,
                b.provider_id,
                b.service_id,
                s.name AS service_name,
                b.booking_date,
                b.booking_time,
                b.address,
                b.description,
                b.amount,
                b.total_amount,
                b.status,
                b.notes,
                b.latitude,
                b.longitude,
                b.created_at
            FROM bookings b
            INNER JOIN services s
                ON b.service_id = s.id
            WHERE b.id = %s
            LIMIT 1
            """,
            (booking_id,)
        )

        updated_booking = cursor.fetchone()

        updated_booking = serialize_row(
            updated_booking
        )

        return jsonify({
            "success": True,
            "message": "Booking status updated successfully",
            "booking": updated_booking
        }), 200

    except Exception as error:

        if connection:

            try:
                connection.rollback()
            except Exception:
                pass

        print(
            "Update booking status error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to update booking status",
            "error": str(error)
        }), 500

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if connection:

            try:
                connection.close()
            except Exception:
                pass