"""
Engine/session plumbing for the SQLite (or any SQLAlchemy URL) database.

DATABASE_URL overrides the location (tests point it at a temp file); default is database/altcredit.db.
"""
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from database.models import Base, ProductRecord, Score, User, UserData

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "altcredit.db")

_engine = None
_Session = None


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or f"sqlite:///{DEFAULT_PATH}"


def get_engine():
    global _engine, _Session
    if _engine is None:
        url = database_url()
        kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        _engine = create_engine(url, echo=False, **kwargs)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


@contextmanager
def session_scope():
    """Commit on success, roll back on error."""
    get_engine()
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create missing tables and add columns introduced since an older altcredit.db was created."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            have = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name not in have:
                    coltype = col.type.compile(engine.dialect)
                    conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {coltype}"))


def sync_reference_data(demographics: list[dict], products: list, scores: dict) -> None:
    """Mirror the dataset users, product catalogue and latest scores into the DB."""
    now = datetime.now(timezone.utc).isoformat()
    with session_scope() as s:
        for d in demographics:
            s.merge(User(
                user_id=d["user_id"], age=d.get("age"), employment_status=d.get("employment_status"),
                months_employed=d.get("months_employed"), education_level=d.get("education_level"),
                monthly_income=d.get("monthly_income"), city_tier=d.get("city_tier"),
                housing_status=d.get("housing_status"), housing_months=d.get("housing_months"),
            ))
        for p in products:
            s.merge(ProductRecord(product_id=p.product_id, name=p.name, type=getattr(p, "type", None),
                                  min_score_required=p.min_score_required, interest_rate=p.interest_rate))
        s.query(Score).delete()
        for uid, r in scores.items():
            s.add(Score(user_id=uid, total_score=r.total_score, risk_category=r.risk_category,
                        breakdown_json=r.model_dump_json(), computed_at=now))


def save_user_data(user_id: str, features: dict, demographics: dict, score) -> None:
    """Persist a user's submitted data and replace their latest score row."""
    now = datetime.now(timezone.utc).isoformat()
    with session_scope() as s:
        s.merge(UserData(user_id=user_id, features_json=json.dumps(features),
                         demographics_json=json.dumps(demographics), updated_at=now))
        s.query(Score).filter(Score.user_id == user_id).delete()
        s.add(Score(user_id=user_id, total_score=score.total_score, risk_category=score.risk_category,
                    breakdown_json=score.model_dump_json(), computed_at=now))


def load_all_user_data() -> list[tuple[str, dict, dict]]:
    with session_scope() as s:
        return [(r.user_id, json.loads(r.features_json), json.loads(r.demographics_json or "{}"))
                for r in s.query(UserData)]
