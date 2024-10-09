import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables if in development
if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DB_URL_STRINGv2")

# Create SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args={
    #         "ssl": {
    #             "ca": "./ca.pem",
    #         }
    #     }
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declare a base class for your ORM models
Base = declarative_base()

# Import your models here
from database.models import (
    User,
    Geofence,
    AttendanceRecord,
)  # Adjust the import based on your directory structure


# Create the database tables
def create_tables():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    print("Tables created successfully")
