from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String)
    file_size_kb = Column(Integer)
    file_type = Column(String(10))
    page_count = Column(Integer, nullable=True)
    language = Column(String(5), nullable=True)
    cluster_label = Column(String(50))
    x_coord = Column(Float, nullable=True)
    y_coord = Column(Float, nullable=True)
    
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)
