#!/usr/bin/env python
"""Script to initialize database and create tables."""
from app.app import create_app
from app.models import db, User, News

app = create_app('development')

with app.app_context():
    # Drop all tables and recreate (for development)
    db.drop_all()
    db.create_all()
    print("Database tables created successfully!")
    
    # Verify tables
    print("\nExisting tables:")
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    for table in inspector.get_table_names():
        print(f"  - {table}")