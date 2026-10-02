from db import get_db_connection
from werkzeug.security import check_password_hash


connection = None
cursor = None

try:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT email, password
        FROM admins
        WHERE email = %s
        LIMIT 1
        """,
        ("admin@localservice.com",)
    )

    admin = cursor.fetchone()

    if not admin:
        print("ADMIN NOT FOUND")
    else:
        result = check_password_hash(
            admin["password"],
            "Admin@123"
        )

        print("Admin found:", admin["email"])
        print("Password matches:", result)

finally:
    if cursor:
        cursor.close()

    if connection:
        connection.close()