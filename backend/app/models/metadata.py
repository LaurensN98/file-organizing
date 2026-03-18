from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from sqlalchemy.ext.declarative import declarative_base
import datetime
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default="PENDING") # PENDING, PROCESSING, SUCCESS, FAILED
    error_message = Column(Text, nullable=True)
    summary = Column(JSON, nullable=True) # stores stats + description
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationship to docs
    documents = relationship("DocumentMetadata", back_populates="batch")

class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("upload_batches.id"), nullable=True)
    
    filename = Column(String)
    file_size_kb = Column(Integer)
    file_type = Column(String(20))
    page_count = Column(Integer, nullable=True)
    language = Column(String(10), nullable=True)
    cluster_label = Column(String)
    x_coord = Column(Float, nullable=True)
    y_coord = Column(Float, nullable=True)
    
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Embeddings
    dense_embedding = Column(Vector(4096), nullable=True)
    sparse_embedding = Column(JSONB, nullable=True)

    # Relationship to batch
    batch = relationship("UploadBatch", back_populates="documents")
