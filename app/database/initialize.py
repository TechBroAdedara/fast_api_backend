# initialize.py
from session import engine, Base
from models import User, Geofence, AttendanceRecord  # Import models that need tables
# Create the database tables
def create_tables():
    Base.metadata.create_all(bind=engine)



if __name__ == "__main__":
    create_tables()
    print("Tables created successfully")