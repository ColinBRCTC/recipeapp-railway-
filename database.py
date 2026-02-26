"""
database.py – User account storage for Recipe Finder & Meal Planner
Uses SQLite via Flask-SQLAlchemy to store user accounts.
Flask-Login's UserMixin provides the required is_authenticated, is_active,
is_anonymous, and get_id methods automatically.
"""

import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    Represents a registered user account.
    Inherits UserMixin for Flask-Login compatibility.
    """
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password: str) -> None:
        """Hash and store a password. Never stores the plain-text password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the given password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"
