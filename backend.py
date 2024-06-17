import json
import math
import random
import string
from datetime import datetime
from typing import Annotated, Generator, List, Tuple

import mysql.connector
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from mysql.connector import errors
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from passlib.context import CryptContext

import auth
from auth import get_current_admin_user, get_current_student_user
from schemas import GeofenceCreate


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

# ----------------------------------------FastAPI App Init--------------------------------------------
app = FastAPI()
app.include_router(auth.router)


# ----------------------------------------Dependency--------------------------------------------
def get_db() -> Generator:
    db = mysql.connector.connect(
        host="sql8.freesqldatabase.com", 
        user="sql8714187", 
        passwd="CIng3QVDUe", 
        database="sql8714187"
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
# ----------------------------------------Routes--------------------------------------------
@app.get("/")
def index():
    return "Hello! Access our documentation by adding '/docs' to the url above"

@app.get("/test", status_code=status.HTTP_200_OK)
async def user(user:admin_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed")
    
    return {"User": user}

# Endpoint to get the list of users
@app.get("/get_users")
def get_users(db_tuple:db_dependency, user: admin_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail = "Authentication Failed")
    
    db, cursor = db_tuple
    cursor.execute("SELECT user_matric, username, role FROM Users")
    rows = cursor.fetchall()
    return rows 

# Endpoint to create Geofence
@app.post("/geofences/")
def create_geofence(geofence: GeofenceCreate, user:admin_dependency, db_tuple = Depends(get_db)):
    db, cursor = db_tuple   
    if user is None:
        raise HTTPException(status_code=401, detail = "Authentication Failed")
    
    cursor.execute("SELECT * FROM Geofences WHERE name = %s AND DATE(start_time) = %s", (geofence.name, geofence.start_time.date(),))
    db_geofence = cursor.fetchone()
    if db_geofence:
        raise HTTPException(status_code=400, detail= f"Geofence with this name aalready exists for today and is ending {db_geofence["end_time"]}")
    
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
        
# Endpoint to get a list of Geofences
@app.get("/get_geofences")
def get_geofences(db_tuple:db_dependency):
    db, cursor = db_tuple
    cursor.execute("SELECT * FROM Geofences")
    geofences = cursor.fetchall()
    return {"geofences": geofences}

@app.delete("/delete_geofence/", response_model=str)
async def delete_geofence(geofence_name: str, db_tuple: db_dependency, user: admin_dependency):
    db, cursor = db_tuple
    if user is None:
        raise HTTPException(status_code=401, detail = "Authentication Failed")

    try:
        # Check if geofence exists
        cursor.execute("SELECT * FROM Geofences WHERE name = %s", (geofence_name,))
        geofence = cursor.fetchone()
        if geofence is None:
            raise HTTPException(status_code=404, detail="Geofence not found")

        # Delete geofence
        cursor.execute("DELETE FROM Geofences WHERE name = %s", (geofence_name,))
        db.commit()

        return f"Successfully deleted {geofence_name} from the list of available Geofences"

    except Exception as e:
        # Handle exceptions
        print(f"Error deleting geofence: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Endpoint to validate user attendance and store in database
@app.get("/validate_attendance/")
def validate_attendance(fence_code:str, lat: float, long: float, db_tuple: db_dependency, user: student_dependency):
    db, cursor = db_tuple
    if user is None:
        raise HTTPException(status_code=401, detail = "Authentication Failed")
    today = datetime.now() # Get current datetime

    # Check if user exists
    cursor.execute("SELECT * FROM Users WHERE user_matric = %s", (user["user_matric"],))
    db_user = cursor.fetchone()
    
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Check if geofence exists
    cursor.execute("SELECT * FROM Geofences WHERE fence_code = %s", (fence_code,))
    geofence = cursor.fetchone()
    if not geofence:
        raise HTTPException(status_code=404, detail=f"Geofence code: {fence_code} not found")
    try:
        if geofence["start_time"] <= today <= geofence["end_time"]: #if geofence is still open
            if check_user_in_circular_geofence(lat, long, geofence): # Process to check if user is in geofence and record attendance
                matric_fence_code = db_user["user_matric"] + geofence["fence_code"]
                cursor.execute(
                    "INSERT INTO AttendanceRecords (user_matric, fence_code, timestamp, matric_fence_code) VALUES (%s, %s, %s, %s)",
                    (user["user_matric"], fence_code, datetime.now(), matric_fence_code,)
                )
                db.commit()
                return {"message": "Attendance recorded successfully"}
            else:
                    return {"message": "User is not within the geofence"}
        else:

            return "Geofence is not open"
        
        
    except errors.IntegrityError as e:
        if e.errno == 1062:
            return "User has already signed attendance for this class"
        else:
            raise HTTPException(status_code=500, detail="Database error")
        
        
# Endpoint to list all attendance records
@app.get("/get_attendance")
def get_attedance(db_tuple:db_dependency, user: admin_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail = "Authentication Failed")

    db, cursor = db_tuple
    cursor.execute("SELECT * FROM AttendanceRecords")
    attendances = cursor.fetchall()
    return {"attendances": attendances}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
