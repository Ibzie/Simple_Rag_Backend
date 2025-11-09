# SQLAlchemy database setup

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

# make sure the directory exists before SQLAlchemy tries to create the database
# handle both sqlite:/// (3 slashes) and sqlite://// (4 slashes for absolute paths)
db_path = settings.DATABASE_URL.replace("sqlite:////", "/").replace("sqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)
    print(f"Created database directory: {db_dir}")

# create the SQLAlchemy engine
# check_same_thread=False is needed for FastAPI (multiple threads)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# session factory for database connections
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# base class for all our models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI routes
    Creates a new database session for each request, closes it when done
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database - create all tables
    Called on startup
    """
    Base.metadata.create_all(bind=engine)
