from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    cluster_id = Column(Integer)
    cluster_name = Column(String)
    x_coord = Column(Float, nullable=True)
    y_coord = Column(Float, nullable=True)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)
