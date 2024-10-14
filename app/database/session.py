import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables if in development
if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DB_URL_STRING")

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

def get_db():
    db = SessionLocal()  # Create a new session
    try:
        yield db  # Yield the session to be used
    finally:
        db.close()  # Close the session when done


