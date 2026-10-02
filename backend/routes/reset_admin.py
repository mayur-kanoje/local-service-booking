from werkzeug.security import generate_password_hash
from db import get_db_connection


ADMIN_EMAIL = "admin@localservice.com"
NEW_PASSWORD = "Admin@123"


connection = None
cursor = None

try:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Check admin
    cursor.execute(
        """
        SELECT id, name, email
        FROM admins
        WHERE email = %s
        LIMIT 1
        """,
        (ADMIN_EMAIL,)
    )

    admin = cursor.fetchone()

    if not admin:
        print("Admin account not found.")
    else:
        new_hash = generate_password_hash(NEW_PASSWORD)

        cursor.execute(
            """
            UPDATE admins
            SET password = %s
            WHERE email = %s
            """,
            (new_hash, ADMIN_EMAIL)
        )

        connection.commit()

        print("----------------------------------------")
        print("ADMIN PASSWORD RESET SUCCESSFUL")
        print("----------------------------------------")
        print("Email:", ADMIN_EMAIL)
        print("New Password:", NEW_PASSWORD)
        print("Admin ID:", admin["id"])
        print("----------------------------------------")

except Exception as error:
    if connection:
        connection.rollback()

    print("Password reset error:", error)

finally:
    if cursor:
        cursor.close()

    if connection:
        connection.close()