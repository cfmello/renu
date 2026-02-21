from pydantic import BaseModel, model_validator, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class CategoriaCreate(BaseModel):
    nome: str

class ItemCreate(BaseModel):
    nome: str
    tipo_controle: str
    prazo_dias: Optional[int] = None
    data_validade_fixa: Optional[datetime] = None
    categoria_id: int

    @model_validator(mode='after')
    def validar_campos(self) -> 'ItemCreate':
        if self.tipo_controle == "PRAZO" and self.prazo_dias is None:
            raise ValueError("Informe 'prazo_dias'.")
        if self.tipo_controle == "VALIDADE" and self.data_validade_fixa is None:
            raise ValueError("Informe 'data_validade_fixa'.")
        return self