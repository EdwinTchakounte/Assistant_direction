"""
Fixtures Pytest partagees par les tests.

- `db` : session SQLAlchemy sur une DB SQLite en memoire, recreee
  pour chaque test (isolation totale).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.db_models import Base


@pytest.fixture
def db():
    """
    Base de donnees SQLite en memoire, isolee par test.
    Les tables sont creees au setup et droppees au teardown.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestSession()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
