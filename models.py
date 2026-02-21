from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    senha_hash = Column(String)
    itens = relationship("ItemDB", back_populates="dono", cascade="all, delete-orphan")
    categorias = relationship("CategoriaDB", back_populates="dono", cascade="all, delete-orphan")

class CategoriaDB(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    dono_id = Column(Integer, ForeignKey("users.id"))
    
    dono = relationship("UserDB", back_populates="categorias")
    itens = relationship("ItemDB", back_populates="categoria")

class ItemDB(Base):
    __tablename__ = "itens"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    tipo_controle = Column(String) 
    data_inicio = Column(DateTime, default=datetime.utcnow)
    prazo_dias = Column(Integer, nullable=True)
    data_validade_fixa = Column(DateTime, nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    dono_id = Column(Integer, ForeignKey("users.id"))
    
    categoria = relationship("CategoriaDB", back_populates="itens")
    dono = relationship("UserDB", back_populates="itens")