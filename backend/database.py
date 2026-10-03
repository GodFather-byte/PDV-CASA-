import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# Padrão: SQLite local (./pdv_casa.db). Em produção use PDV_NUVEM_DB_URL, por exemplo
# postgresql+psycopg://usuario:senha@servidor/pdv
SQLALCHEMY_DATABASE_URL = os.environ.get("PDV_NUVEM_DB_URL") or "sqlite:///./pdv_casa.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
