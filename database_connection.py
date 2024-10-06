import os
from dotenv import load_dotenv
import mysql

if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()


def get_db():
    db = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        passwd=os.getenv("DB_PSWORD"),
        database=os.getenv("DB_DB"),
        port=10652,
    )
    try:
        cursor = db.cursor(dictionary=True)
        yield db, cursor
    finally:
        cursor.close()
        db.close()
