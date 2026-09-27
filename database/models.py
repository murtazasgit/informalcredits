"""
Database models — SQLAlchemy ORM models for SQLite persistence.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)
    age = Column(Integer)
    employment_status = Column(String)
    months_employed = Column(Integer)
    education_level = Column(String)
    monthly_income = Column(Float)
    city_tier = Column(String)
    housing_status = Column(String)
    housing_months = Column(Integer)
    existing_credit_lines = Column(Integer, default=0)


class TransactionRecord(Base):
    __tablename__ = "transactions"
    transaction_id = Column(String, primary_key=True)
    user_id = Column(String)
    date = Column(String)
    amount = Column(Float)
    category = Column(String)
    type = Column(String)
    on_time = Column(Boolean, nullable=True)


class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    total_score = Column(Integer)
    risk_category = Column(String)
    breakdown_json = Column(Text)
    computed_at = Column(String)


class ProductRecord(Base):
    __tablename__ = "products"
    product_id = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)
    min_score_required = Column(Integer)
    interest_rate = Column(Float)


class Offer(Base):
    __tablename__ = "offers"
    offer_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    candidate_ref = Column(String)
    lender = Column(String, index=True)
    product_id = Column(String)
    product_name = Column(String)
    interest_rate = Column(Float)
    message = Column(Text, default="")
    status = Column(String, default="pushed")
    pushed_at = Column(String)
    responded_at = Column(String, nullable=True)


class Account(Base):
    """Consumer login: the platform user_id plus a salted password hash."""
    __tablename__ = "accounts"
    user_id = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(String)


class UserSession(Base):
    """Bearer sessions; only a SHA-256 of the token is stored."""
    __tablename__ = "sessions"
    token_hash = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    expires_at = Column(Float)


class UserData(Base):
    """Latest data a registered/updating user submitted (features JSON + optional demographics JSON)."""
    __tablename__ = "user_data"
    user_id = Column(String, primary_key=True)
    features_json = Column(Text, nullable=False)
    demographics_json = Column(Text)
    updated_at = Column(String)


class Lender(Base):
    """A registered lending institution. `username` is the identity stamped on its offers and applications."""
    __tablename__ = "lenders"
    lender_id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    bank_name = Column(String)
    created_at = Column(String)


class Application(Base):
    """A consumer's pre-approval application to one specific lender for one product."""
    __tablename__ = "applications"
    application_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    lender = Column(String, index=True)          # Lender.username
    product_id = Column(String)
    product_name = Column(String)
    interest_rate = Column(Float)
    requested_amount = Column(Float)
    tenure_months = Column(Integer)
    purpose = Column(String)
    applicant_name = Column(String)
    phone = Column(String)
    score_at_submit = Column(Integer)
    status = Column(String, default="submitted")  # submitted | approved | declined
    lender_note = Column(Text, default="")
    created_at = Column(String)
    decided_at = Column(String, nullable=True)


def get_engine(db_path: str = None):
    """Create SQLAlchemy engine."""
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), "altcredit.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    return engine


def create_tables(engine):
    """Create all tables."""
    Base.metadata.create_all(engine)


def get_session(engine):
    """Get a new session."""
    Session = sessionmaker(bind=engine)
    return Session()
