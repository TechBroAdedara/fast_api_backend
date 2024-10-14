from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship

from app.database.session import Base

class Geofence(Base):
    __tablename__ = "Geofences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fence_code = Column(String(15), unique=True)
    name = Column(String(60))
    latitude = Column(Float)
    longitude = Column(Float)
    radius = Column(Float)
    fence_type = Column(String(60))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String(60))
    time_created = Column(DateTime)
    
    #foreign key
    creator_matric = Column(String(50), ForeignKey("Users.user_matric"))

    creator = relationship("User", back_populates="geofences")
