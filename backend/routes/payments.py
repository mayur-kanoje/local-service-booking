from flask import Blueprint, request, jsonify
import uuid

from db import get_db_connection


# =========================================================
# BLUEPRINT
# =========================================================

payments_bp = Blueprint("payments", __name__)


# =========================================================
# CREATE DEMO PAYMENT
# POST /api/payments
# =========================================================

@payments_bp.route("", methods=["POST"])
def create_payment():

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

        booking_id = data.get("booking_id")
        user_id = data.get("user_id")
        amount = data.get("amount")
        payment_method = str(
            data.get("payment_method", "Demo Payment")
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not booking_id:
            return jsonify({
                "success": False,
                "message": "Booking ID is required"
            }), 400

        if not user_id:
            return jsonify({
                "success": False,
                "message": "User ID is required"
            }), 400

        if amount is None:
            return jsonify({
                "success": False,
                "message": "Payment amount is required"
            }), 400

        try:
            amount = float(amount)
        except (TypeError, ValueError):

            return jsonify({
                "success": False,
                "message": "Invalid payment amount"
            }), 400

        if amount <= 0:

            return jsonify({
                "success": False,
                "message": "Payment amount must be greater than zero"
            }), 400

        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # CHECK USER
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
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
        # CHECK BOOKING
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                provider_id,
                total_amount,
                status
            FROM bookings
            WHERE id = %s
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

        # -------------------------------------------------
        # CHECK BOOKING OWNER
        # -------------------------------------------------

        if int(booking["user_id"]) != int(user_id):

            return jsonify({
                "success": False,
                "message": "This booking does not belong to this user"
            }), 403

        # -------------------------------------------------
        # CHECK EXISTING SUCCESSFUL PAYMENT
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                transaction_id,
                amount,
                payment_method,
                status,
                payment_date
            FROM payments
            WHERE booking_id = %s
              AND user_id = %s
              AND status = 'success'
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                booking_id,
                user_id
            )
        )

        existing_payment = cursor.fetchone()

        if existing_payment:

            return jsonify({
                "success": False,
                "message": "Payment has already been completed for this booking",
                "payment": existing_payment
            }), 409

        # -------------------------------------------------
        # CHECK BOOKING AMOUNT
        # -------------------------------------------------

        booking_amount = float(
            booking["total_amount"] or 0
        )

        if booking_amount > 0:

            if abs(amount - booking_amount) > 0.01:

                return jsonify({
                    "success": False,
                    "message": (
                        f"Payment amount must be "
                        f"{booking_amount:.2f}"
                    )
                }), 400

        # -------------------------------------------------
        # DEMO TRANSACTION ID
        # -------------------------------------------------

        transaction_id = (
            "DEMO_TXN_"
            + uuid.uuid4().hex[:12].upper()
        )

        # -------------------------------------------------
        # INSERT PAYMENT
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO payments
            (
                booking_id,
                user_id,
                amount,
                payment_method,
                transaction_id,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                'success'
            )
            """,
            (
                booking_id,
                user_id,
                amount,
                payment_method,
                transaction_id
            )
        )

        connection.commit()

        payment_id = cursor.lastrowid

        # -------------------------------------------------
        # GET PAYMENT
        # -------------------------------------------------

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
            WHERE id = %s
            LIMIT 1
            """,
            (payment_id,)
        )

        payment = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Demo payment successful",
            "payment": payment
        }), 201

    except Exception as error:

        if connection:
            connection.rollback()

        print("Create payment error:", error)

        return jsonify({
            "success": False,
            "message": "Payment failed",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# GET PAYMENT FOR BOOKING
# GET /api/payments/booking/<booking_id>
# =========================================================

@payments_bp.route(
    "/booking/<int:booking_id>",
    methods=["GET"]
)
def get_booking_payment(booking_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

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
            ORDER BY id DESC
            """,
            (booking_id,)
        )

        payments = cursor.fetchall()

        return jsonify({
            "success": True,
            "count": len(payments),
            "payments": payments
        }), 200

    except Exception as error:

        print("Get booking payment error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch payment",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()