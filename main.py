import logging
import math
import random
import string
from datetime import datetime
import os
from typing import Annotated, Tuple, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from icecream import ic
from mysql.connector import errors
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from passlib.context import CryptContext

import auth.auth as auth
from auth.auth import get_current_admin_user, get_current_student_user, get_current_user
from auth.schemas import GeofenceCreate

from sqlalchemy import func
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import User, Geofence, AttendanceRecord


if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()


def get_db():
    db = SessionLocal()  # Create a new session
    try:
        yield db  # Yield the session to be used
    finally:
        db.close()  # Close the session when done


# ----------------------------------------Geolocation Logic/Algorithm--------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return (
        2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 1000
    )  # Convert to meters


def check_user_in_circular_geofence(user_lat, user_lng, geofence):
    latitude = geofence["latitude"]
    longitude = geofence["longitude"]
    radius = geofence["radius"]
    distance = haversine(user_lat, user_lng, latitude, longitude)
    return distance <= radius


def generate_alphanumeric_code(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


# ----------------------------------------Password Hashing--------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----------------------------------------Allowed Origins--------------------------------------------
origins = [
    "http://localhost:3000",
    "http://localhost",
]
# ----------------------------------------FastAPI App Init--------------------------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Just for Development. Would be changed later.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)


# ----------------------------------------Dependencies--------------------------------------------
db_dependency = Annotated[Session, Depends(get_db)]
admin_dependency = Annotated[dict, Depends(get_current_admin_user)]
student_dependency = Annotated[dict, Depends(get_current_student_user)]
general_user = Annotated[dict, Depends(get_current_user)]


# ----------------------------------------Routes--------------------------------------------
@app.get("/")
def index():
    return "Hello! Access our documentation by adding '/docs' to the url above"


# Webhook
# @app.webhooks.post("New attendance")
# def new_attendance():
#     return "Hello"


# ---------------------------- Endpoint to get the list of users
@app.get("/user/")
def get_user(user_matric: str, db: db_dependency, _: admin_dependency):
    """Get the user and their records from the database."""
    try:
        user_records = (
            db.query(
                User.user_matric,
                User.username,
                User.role,
                AttendanceRecord.geofence_name,
                AttendanceRecord.timestamp,
            )
            .outerjoin(
                AttendanceRecord, User.user_matric == AttendanceRecord.user_matric
            )
            .filter(User.user_matric == user_matric)
            .all()
        )

        if not user_records:
            raise HTTPException(status_code=404, detail="User not found")

        # Extract user details and attendance records
        attendances = [
            {
                "Class name": geofence_name,
                "Attendance timestamp": timestamp,
            }
            for user_matric, username, role, geofence_name, timestamp in user_records
            if geofence_name is not None and timestamp is not None
        ]

        # Assuming user_records will have at least one record
        record = {
            "user_matric": user_records[0][0],  # user_matric
            "username": user_records[0][1],  # username
            "role": user_records[0][2],  # role
            "Attendances": attendances,
        }

        return record

    except Exception as e:
        print(e)  # Use logging instead of print for production
        raise HTTPException(
            status_code=500,
            detail="Internal Error: Contact Administrator (This wasn't even supposed to happen lol)",
        )


# ---------------------------- Endpoint to list all attendance records
@app.get("/get_attendance/")
def get_attedance(
    course_title: str, date: datetime, db: db_dependency, user: admin_dependency
):
    """Gets the attendace record for a given course.
    User can only see the records if they created the class.
    """
    geofence_exists = (
        db.query(Geofence)
        .filter(Geofence.name == course_title, func.date(Geofence.start_time) == date)
        .first()
    )

    if not geofence_exists:
        raise HTTPException(
            status_code=404,
            detail="Geofence doesn't exist for specified course and date. No records",
        )

    if geofence_exists.creator_matric != user["user_matric"]:
        raise HTTPException(
            status_code=401,
            detail="No permission to view this class attendances, as you're not the creator of the geofence",
        )

    attendances = (
        db.query(
            User.username, AttendanceRecord.user_matric, AttendanceRecord.timestamp
        )
        .join(AttendanceRecord.user_matric == User.user_matric)
        .filter(AttendanceRecord.geofence_name == course_title, func.date(AttendanceRecord.timestamp) == date)
        .all()
    )

    if not attendances:
        raise HTTPException(status_code=404, detail="No attendance records yet")

    return {f"{course_title} attendance records": attendances}


# ---------------------------- Endpoint to list user attendance records
@app.get("/user_get_attendance/")
def user_get_attendance(
    db_tuple: db_dependency,
    user: student_dependency,
    course_title: Optional[str] = None,
):
    """Gets the attendance records of a student, for the student.
    If no class is specified, returns all records of the student.
    if specified, returns all records of the student for the particular class.
    """
    try:
        _, cursor = db_tuple

        # when a user provides a geofence/course name
        if course_title is not None:
            cursor.execute("SELECT * FROM Geofences WHERE name = %s", (course_title,))
            course_exist = cursor.fetchall()

            if not course_exist:
                raise HTTPException(status_code=404, detail="Geofence Not found")

            QUERY = "SELECT * FROM AttendanceRecords WHERE user_matric = %s and geofence_name = %s"
            cursor.execute(
                QUERY,
                (
                    user["user_matric"],
                    course_title,
                ),
            )
            user_attendances = cursor.fetchall()
            if not user_attendances:
                raise HTTPException(
                    status_code=404,
                    detail="No attendance records for {course_title} yet",
                )

            return user_attendances

        else:
            # when the user doesn't specify a course_title
            QUERY = "SELECT * FROM AttendanceRecords WHERE user_matric = %s"
            cursor.execute(QUERY, (user["user_matric"],))
            user_attendances = cursor.fetchall()
            if not user_attendances:
                raise HTTPException(status_code=404, detail="No Attendance records yet")

            return user_attendances

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {e}")


# ---------------------------- Endpoint to get a list of Geofences
@app.get("/get_geofences/")
def get_geofences(
    db_tuple: db_dependency,
    _: general_user,
    course_title: Optional[str] = None,
):
    """Gets all the active geofences.
    (Will later be implemented as a websocket to update list in real-time)
    """
    _, cursor = db_tuple

    if course_title is None:
        cursor.execute("SELECT * FROM Geofences")
        geofences = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM Geofences WHERE name = %s", (course_title,))
        geofences = cursor.fetchall()

    if not geofences:
        raise HTTPException(status_code=404, detail="No geofences found")

    return {"geofences": geofences}


# ---------------------------- Endpoint to create Geofence
@app.post("/create_geofences/")
def create_geofence(
    geofence: GeofenceCreate, user: admin_dependency, db_tuple: db_dependency
):
    """Creates a Geofence with a specific start_time and end_time."""
    db, cursor = db_tuple

    cursor.execute(
        "SELECT * FROM Geofences WHERE name = %s AND DATE(start_time) = %s",
        (
            geofence.name,
            geofence.start_time.date(),
        ),
    )
    db_geofence = cursor.fetchone()
    if db_geofence:
        raise HTTPException(
            status_code=400,
            detail="Geofence with this name already exists for today",
        )

    try:
        code = generate_alphanumeric_code()
        cursor.execute(
            "INSERT INTO Geofences (fence_code, name, creator_matric, latitude, longitude, radius, fence_type, start_time, end_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                code,
                geofence.name,
                user["user_matric"],
                geofence.latitude,
                geofence.longitude,
                geofence.radius,
                geofence.fence_type,
                geofence.start_time,
                geofence.end_time,
            ),
        )
        db.commit()
        return {"Code": code, "name": geofence.name}
    except errors.IntegrityError as e:
        if e.errno == 1062:  # Duplicate entry error code
            raise HTTPException(
                status_code=400, detail="Geofence with this code already exists"
            )
        else:
            raise HTTPException(status_code=500, detail="Database error")


# ---------------------------- Endpoint to manually deactivate geofence
@app.put("/manual_deactivate_geofence/", response_model=str)
def manual_geofence(
    geofence_name: str, date: datetime, db_tuple: db_dependency, user: admin_dependency
):
    """Manually deactivates the Geofence for the admin."""
    db, cursor = db_tuple
    try:
        # Check if geofence exists
        cursor.execute(
            "SELECT * FROM Geofences WHERE name = %s AND DATE(start_time) = %s",
            (
                geofence_name,
                date,
            ),
        )
        geofence = cursor.fetchone()
        if geofence is None:
            raise HTTPException(
                status_code=404,
                detail="Geofence doesn't exist or not found for specified date",
            )

        if geofence["status"] == "inactive":
            raise HTTPException(status_code=400, detail="Geofence is already inactive")

        if user["user_matric"] != geofence["creator_matric"]:
            raise HTTPException(
                status_code=401,
                detail="You don't have permission to delete this class as you are not the creator.",
            )

        # Deactivate geofence
        cursor.execute(
            "UPDATE Geofences SET status = 'inactive' WHERE name = %s AND DATE(start_time) = %s",
            (
                geofence_name,
                date,
            ),
        )
        db.commit()

        return f"Successfully deactivated geofence {geofence_name} for {date} "

    except Exception as e:
        # Handle exceptions
        logging.error(f"Error deactivating geofence: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deactivating geofence. Contact administrator.",
        )


# ---------------------------- Endpoint to validate user attendance and store in database
@app.post("/record_attendance/")
def validate_attendance(
    fence_code: str,
    lat: float,
    long: float,
    db_tuple: db_dependency,
    user: student_dependency,
):
    """Student Endpoint for validating attendance"""

    db, cursor = db_tuple

    # Check if user exists
    cursor.execute("SELECT * FROM Users WHERE user_matric = %s", (user["user_matric"],))
    db_user = cursor.fetchone()

    # if the user doesn't exist...
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if geofence exists
    cursor.execute(
        "SELECT * FROM Geofences WHERE fence_code = %s AND status = %s",
        (
            fence_code,
            "active",
        ),
    )
    geofence = cursor.fetchone()
    if not geofence:
        raise HTTPException(
            status_code=404,
            detail=f"Geofence code: {fence_code} not found or is not active",
        )

    try:
        if (
            geofence["status"].lower() == "active"
        ):  # Proceed to check if user is in geofence and record attendance
            if check_user_in_circular_geofence(lat, long, geofence):
                matric_fence_code = db_user["user_matric"] + geofence["fence_code"]
                cursor.execute(
                    "INSERT INTO AttendanceRecords (user_matric, fence_code, geofence_name, timestamp, matric_fence_code) VALUES (%s, %s, %s, %s, %s)",
                    (
                        db_user["user_matric"],
                        fence_code,
                        geofence["name"],
                        datetime.now(),
                        matric_fence_code,
                    ),
                )
                db.commit()

                # THE ONLY SUCCESS
                return {"message": "Attendance recorded successfully"}

            raise HTTPException(
                status_code=400,
                detail="User is not within geofence, attendance not recorded",
            )
        else:
            raise HTTPException(
                status_code=404, detail="Geofence is not open for attendance"
            )

    except errors.IntegrityError as e:
        if e.errno == 1062:
            raise HTTPException(
                status_code=400,
                detail="User has already signed attendance for this class",
            )

        print(e)
        raise HTTPException(
            status_code=500, detail=f"Internal Error. Contact administrator."
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)