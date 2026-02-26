from pydantic import BaseModel, model_validator, EmailStr, Field
from datetime import datetime, timezone
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
            agora = datetime.now(timezone.utc)
            
            if self.tipo_controle == "PRAZO":
                if self.prazo_dias is None:
                    raise ValueError("Para o tipo PRAZO, informe os dias.")
            
            elif self.tipo_controle == "VALIDADE":
                if self.data_validade_fixa is None:
                    raise ValueError("Para o tipo VALIDADE, informe a data.")
                # Impede datas retroativas (com margem de erro de 1 min)
                if self.data_validade_fixa.replace(tzinfo=timezone.utc) < agora:
                    raise ValueError("A data de validade não pode estar no passado.")
            
            return self