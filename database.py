import os
from sqlalchemy import create_url, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Se existir a variável DATABASE_URL (no Render), usa ela. 
# Caso contrário, usa o SQLite local.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./renu.db")

# Ajuste para compatibilidade com versões antigas do Postgres/Heroku se necessário
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# O SQLite precisa do 'check_same_thread', o Postgres não.
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()