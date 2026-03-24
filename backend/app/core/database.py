from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.metadata import Base
import logging

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # 1. Enable Extensions 
    with engine.connect() as conn:
        logger.info("Enabling vector extensions...")
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector CASCADE;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;"))
            conn.commit()
            logger.info("Extensions enabled.")
        except Exception as e:
            logger.error(f"Failed to enable extensions: {e}")
            conn.rollback()

    # 2. Create tables
    Base.metadata.create_all(bind=engine)
    
    # 3. Setup Indexes
    with engine.connect() as conn:
        logger.info("Initializing vector indexes...")
        try:
            # Create pgvectorscale diskann index for dense search
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_document_dense_embedding 
                ON document_metadata 
                USING diskann (dense_embedding)
                WITH (num_neighbors = 32);
            """))
            
            # Create GIN index for sparse search
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_document_sparse_embedding 
                ON document_metadata 
                USING GIN (sparse_embedding);
            """))
            
            conn.commit()
            logger.info("Vector indexes created successfully.")
        except Exception as e:
            logger.error(f"Vector indexing failed: {e}")
            conn.rollback()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
