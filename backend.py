import json
import math
import random
import string
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import Annotated, Generator, List, Tuple

import mysql.connector
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from mysql.connector import errors
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from passlib.context import CryptContext

import auth
from auth import get_current_admin_user, get_current_student_user, get_current_user
from schemas import GeofenceCreate

if os.getenv('ENVIRONMENT') == 'development':
    load_dotenv()
    
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
    latitude = geofence['latitude']
    longitude = geofence['longitude']
    radius = geofence['radius']
    distance = haversine(user_lat, user_lng, latitude, longitude)
    return distance <= radius


def generate_alphanumeric_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))
# ----------------------------------------Password Hashing--------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----------------------------------------Password Hashing--------------------------------------------
origins = ["http://localhost:3000",
           "http://localhost",
           ]
# ----------------------------------------FastAPI App Init--------------------------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)
app.include_router(auth.router)

# ----------------------------------------Dependency--------------------------------------------
def get_db() -> Generator:
    db = mysql.connector.connect(
        host= os.getenv("DB_HOST"), 
        user=os.getenv("DB_USER"), 
        passwd=os.getenv("DB_PSWORD"), 
        database=os.getenv("DB_DB")
    )
    try:
        cursor = db.cursor(dictionary=True)  # Use dictionary cursor for better readability
        yield db, cursor
    finally:
        cursor.close()
        db.close()

db_dependency = Annotated[Tuple[MySQLConnection, MySQLCursorDict], Depends(get_db)]
admin_dependency = Annotated[dict, Depends(get_current_admin_user)]
student_dependency = Annotated[dict, Depends(get_current_student_user)]
general_user = Annotated[dict, Depends(get_current_user)]
# ----------------------------------------Routes--------------------------------------------
@app.get("/")
def index():
    return "Hello! Access our documentation by adding '/docs' to the url above"


# Endpoint to get the list of users
@app.get("/user/")
def get_user(user_matric:str, db_tuple:db_dependency):
    #if user is None:
    #   raise HTTPException(status_code=401, detail = "Authentication Failed")
    
    db, cursor = db_tuple
    Query = """
            SELECT Users.user_matric, Users.username, Users.role,AttendanceRecords.geofence_name, AttendanceRecords.timestamp 
            FROM Users 
            LEFT JOIN AttendanceRecords 
            ON Users.user_matric = AttendanceRecords.user_matric 
            WHERE Users.user_matric = %s
            """
    cursor.execute(Query, (user_matric,))
    rows = cursor.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    
    attendances= [
        {
            "Class name" : row["geofence_name"],
            "Attendance timestamp": row["timestamp"]
         }
        for row in rows if row["geofence_name"] is not None and row["timestamp"] is not None
    ]
    
    record = {
        "user_matric": rows[0]["user_matric"],
        "username": rows[0]["username"],
        "role" : rows[0]["role"],
        "Attendances ": attendances
    }
    return record 

# Endpoint to list all attendance records
@app.get("/get_attendance/")
def get_attedance(course_title:str, date:datetime, db_tuple:db_dependency):
    #if user is None:
    #    raise HTTPException(status_code=401, detail = "Authentication Failed")

    db, cursor = db_tuple
    QUERY = """
            SELECT Users.username, AttendanceRecords.user_matric, AttendanceRecords.timestamp 
            FROM AttendanceRecords 
            INNER JOIN Users
            ON AttendanceRecords.user_matric = Users.user_matric
            WHERE geofence_name = %s AND DATE(timestamp) = %s 
            """
    cursor.execute(QUERY,(course_title, date,) )
    attendances = cursor.fetchall()
    
    if not attendances:
        return "No attendance records yet"
    
    return {f"{course_title} attendance records": attendances}


# Endpoint to get a list of Geofences
@app.get("/get_geofences/")
def get_geofences(db_tuple:db_dependency):
    db, cursor = db_tuple
    cursor.execute("SELECT * FROM Geofences")
    geofences = cursor.fetchall()
    return {"geofences": geofences}


# Endpoint to create Geofence
@app.post("/geofences/")
def create_geofence(geofence: GeofenceCreate,db_tuple = Depends(get_db)):
    db, cursor = db_tuple   
    #if user is None:
    #    raise HTTPException(status_code=401, detail = "Authentication Failed")
    
    cursor.execute("SELECT * FROM Geofences WHERE name = %s AND DATE(start_time) = %s", (geofence.name, geofence.start_time.date(),))
    db_geofence = cursor.fetchone()
    if db_geofence:
        raise HTTPException(status_code=400, detail= f"Geofence with this name already exists for today and is ending {db_geofence["end_time"]}")
    
    try:
        code = generate_alphanumeric_code()
        cursor.execute(
            "INSERT INTO Geofences (fence_code, name, latitude, longitude, radius, fence_type, start_time, end_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (code, geofence.name, geofence.latitude, geofence.longitude, geofence.radius, geofence.fence_type, geofence.start_time, geofence.end_time)
        )
        db.commit()
        return {"Code": code, "name": geofence.name}
    except errors.IntegrityError as e:
        if e.errno == 1062:  # Duplicate entry error code
            raise HTTPException(status_code=400, detail="Geofence with this code already exists")
        else:
            raise HTTPException(status_code=500, detail="Database error")
        


@app.put("/manual_deactivate_geofence/", response_model=str)
async def manual_deactivate_geofence(geofence_name: str,date:datetime, db_tuple: db_dependency):
    db, cursor = db_tuple
    #if user is None:
    #    raise HTTPException(status_code=401, detail = "Authentication Failed")

    try:
        # Check if geofence exists
        cursor.execute("SELECT * FROM Geofences WHERE name = %s AND DATE(start_time) = %s", (geofence_name, date, ))
        geofence = cursor.fetchone()
        if geofence is None:
            raise HTTPException(status_code=404, detail="Geofence doesn't exist or not found for specified date")
        
        if geofence['status'] == 'inactive':
            return "Geofence is already set to inactive"
        
        # Deactivate geofence
        cursor.execute("UPDATE Geofences SET status = 'inactive' WHERE name = %s AND DATE(start_time) = %s", (geofence_name, date,))
        db.commit()

        return f"Successfully deactivated geofence {geofence_name} for {date} "

    except Exception as e:
        # Handle exceptions
        print(f"Error deactivating geofence: {e}")
        raise HTTPException(status_code=500, detail=f"Error deactivating geofence: {e}")

# Endpoint to validate user attendance and store in database
@app.post("/validate_attendance/")
def validate_attendance(fence_code:str, lat: float, long: float, db_tuple: db_dependency,user:general_user):
    db, cursor = db_tuple
    #Authentication
    #if user is None:
    #    raise HTTPException(status_code=401, detail = "Authentication Failed")
    today = datetime.now() # Get current datetime

    # Check if user exists
    cursor.execute("SELECT * FROM Users WHERE user_matric = %s", (user["user_matric"],))
    db_user = cursor.fetchone()
    
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if geofence exists
    cursor.execute("SELECT * FROM Geofences WHERE fence_code = %s AND status = %s", (fence_code, 'active',))
    geofence = cursor.fetchone()
    if not geofence:
        raise HTTPException(status_code=404, detail=f"Geofence code: {fence_code} not found or is not active")
    
    try:
        if geofence["start_time"] <= today <= geofence["end_time"]: #if geofence is still open
            if check_user_in_circular_geofence(lat, long, geofence): # Proceed to check if user is in geofence and record attendance
                matric_fence_code = db_user["user_matric"] + geofence["fence_code"]
                cursor.execute(
                    "INSERT INTO AttendanceRecords (user_matric, fence_code, geofence_name, timestamp, matric_fence_code) VALUES (%s, %s, %s, %s, %s)",
                    (db_user["user_matric"], fence_code, geofence["name"], datetime.now(), matric_fence_code,)
                )
                db.commit()
                return {"message": "Attendance recorded successfully"}
            else:
                    return {"message": "User is not within the geofence, no attendance recorded"}
        
    except errors.IntegrityError as e:
        if e.errno == 1062:
            return "User has already signed attendance for this class"
        else:
            raise HTTPException(status_code=500, detail="Database error")
        
        

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
