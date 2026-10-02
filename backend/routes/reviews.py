from flask import Blueprint, request, jsonify

from db import get_db_connection


# =========================================================
# BLUEPRINT
# =========================================================

reviews_bp = Blueprint("reviews", __name__)


# =========================================================
# CREATE REVIEW
# POST /api/reviews
# =========================================================

@reviews_bp.route("", methods=["POST"])
def create_review():

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

        user_id = data.get("user_id")
        provider_id = data.get("provider_id")
        booking_id = data.get("booking_id")
        rating = data.get("rating")
        comment = str(
            data.get("comment", "")
        ).strip()

        # -------------------------------------------------
        # REQUIRED FIELDS
        # -------------------------------------------------

        if not user_id:
            return jsonify({
                "success": False,
                "message": "User ID is required"
            }), 400

        if not provider_id:
            return jsonify({
                "success": False,
                "message": "Provider ID is required"
            }), 400

        if not booking_id:
            return jsonify({
                "success": False,
                "message": "Booking ID is required"
            }), 400

        if rating is None:
            return jsonify({
                "success": False,
                "message": "Rating is required"
            }), 400

        # -------------------------------------------------
        # RATING VALIDATION
        # -------------------------------------------------

        try:
            rating = int(rating)
        except (TypeError, ValueError):

            return jsonify({
                "success": False,
                "message": "Rating must be a number"
            }), 400

        if rating < 1 or rating > 5:

            return jsonify({
                "success": False,
                "message": "Rating must be between 1 and 5"
            }), 400

        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # CHECK BOOKING
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                provider_id,
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
        # CHECK BOOKING USER
        # -------------------------------------------------

        if int(booking["user_id"]) != int(user_id):

            return jsonify({
                "success": False,
                "message": "You cannot review this booking"
            }), 403

        # -------------------------------------------------
        # CHECK BOOKING PROVIDER
        # -------------------------------------------------

        if booking["provider_id"] is None:

            return jsonify({
                "success": False,
                "message": "No provider is assigned to this booking"
            }), 400

        if int(booking["provider_id"]) != int(provider_id):

            return jsonify({
                "success": False,
                "message": "Provider does not match this booking"
            }), 400

        # -------------------------------------------------
        # BOOKING MUST BE COMPLETED
        # -------------------------------------------------

        if str(
            booking["status"] or ""
        ).lower() != "completed":

            return jsonify({
                "success": False,
                "message": "Review can be submitted only after booking is completed"
            }), 400

        # -------------------------------------------------
        # CHECK DUPLICATE REVIEW
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id
            FROM reviews
            WHERE booking_id = %s
              AND user_id = %s
            LIMIT 1
            """,
            (
                booking_id,
                user_id
            )
        )

        existing_review = cursor.fetchone()

        if existing_review:

            return jsonify({
                "success": False,
                "message": "You have already reviewed this booking"
            }), 409

        # -------------------------------------------------
        # INSERT REVIEW
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO reviews
            (
                user_id,
                provider_id,
                booking_id,
                rating,
                comment
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                provider_id,
                booking_id,
                rating,
                comment if comment else None
            )
        )

        connection.commit()

        review_id = cursor.lastrowid

        # -------------------------------------------------
        # GET CREATED REVIEW
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                provider_id,
                booking_id,
                rating,
                comment,
                created_at
            FROM reviews
            WHERE id = %s
            LIMIT 1
            """,
            (review_id,)
        )

        review = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Review submitted successfully",
            "review": review
        }), 201

    except Exception as error:

        if connection:
            connection.rollback()

        print("Create review error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to submit review",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# GET PROVIDER REVIEWS
# GET /api/reviews/provider/<provider_id>
# =========================================================

@reviews_bp.route(
    "/provider/<int:provider_id>",
    methods=["GET"]
)
def get_provider_reviews(provider_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # CHECK PROVIDER
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                name
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

        # -------------------------------------------------
        # GET REVIEWS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                r.id,
                r.user_id,
                u.name AS user_name,
                r.provider_id,
                r.booking_id,
                r.rating,
                r.comment,
                r.created_at
            FROM reviews r

            INNER JOIN users u
                ON r.user_id = u.id

            WHERE r.provider_id = %s

            ORDER BY r.id DESC
            """,
            (provider_id,)
        )

        reviews = cursor.fetchall()

        # -------------------------------------------------
        # GET SUMMARY
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_reviews,
                COALESCE(
                    ROUND(AVG(rating), 1),
                    0
                ) AS average_rating
            FROM reviews
            WHERE provider_id = %s
            """,
            (provider_id,)
        )

        summary = cursor.fetchone()

        return jsonify({
            "success": True,
            "provider": {
                "id": provider["id"],
                "name": provider["name"]
            },
            "summary": {
                "total_reviews": summary["total_reviews"],
                "average_rating": float(
                    summary["average_rating"] or 0
                )
            },
            "reviews": reviews
        }), 200

    except Exception as error:

        print("Get provider reviews error:", error)

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