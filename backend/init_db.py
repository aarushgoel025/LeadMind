"""
Run this once to create all database tables.
  python init_db.py
"""
from database import engine, Base
import models  # noqa: F401 — imports must be here to register models with Base

def init():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Done! Tables created: scans, findings, decisions")

if __name__ == "__main__":
    init()
