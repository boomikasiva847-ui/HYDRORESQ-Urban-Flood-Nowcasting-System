from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ForecastCycle(Base):
    __tablename__ = 'forecast_cycle'

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, index=True)
    timestamp = Column(String)  # Storing as string for simplicity, or DateTime
    cycle_offset_min = Column(Integer)
    flood_depth_cm = Column(Float)
    blocked = Column(Boolean)
