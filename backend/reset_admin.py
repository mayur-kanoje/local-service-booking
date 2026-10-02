from werkzeug.security import generate_password_hash
from db import get_db_connection


ADMIN_NAME = "Administrator"
ADMIN_EMAIL = "admin@localservice.com"
ADMIN_PASSWORD = "Admin@123"

connection = None
cursor = None

try:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Check whether admin already exists
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

    password_hash = generate_password_hash(ADMIN_PASSWORD)

    if admin:
        # Admin exists → reset password
        cursor.execute(
            """
            UPDATE admins
            SET name = %s,
                password = %s
            WHERE email = %s
            """,
            (
                ADMIN_NAME,
                password_hash,
                ADMIN_EMAIL
            )
        )

        print("----------------------------------------")
        print("ADMIN PASSWORD RESET SUCCESSFUL")
        print("----------------------------------------")

    else:
        # Admin doesn't exist → create it
        cursor.execute(
            """
            INSERT INTO admins
            (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (
                ADMIN_NAME,
                ADMIN_EMAIL,
                password_hash
            )
        )

        print("----------------------------------------")
        print("ADMIN CREATED SUCCESSFULLY")
        print("----------------------------------------")

    connection.commit()

    print("Email:", ADMIN_EMAIL)
    print("Password:", ADMIN_PASSWORD)
    print("----------------------------------------")

except Exception as error:

    if connection:
        connection.rollback()

    print("Admin creation/reset error:", error)

finally:

    if cursor:
        cursor.close()

    if connection:
        connection.close()