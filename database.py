from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pg8000.dbapi

# Using creator function to avoid special character issues in password
def get_connection():
    return pg8000.dbapi.connect(
        host="localhost",
        port=5432,
        database="complaint_db",
        user="postgres",
        password="Yj@180906"
    )

engine = create_engine(
    "postgresql+pg8000://",
    creator=get_connection
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()