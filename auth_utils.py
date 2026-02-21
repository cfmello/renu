import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

# Configurações
SECRET_KEY = "sua_chave_secreta_super_segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 horas

def gerar_hash_senha(senha: str) -> str:
    # O bcrypt moderno exige que a senha seja convertida em bytes
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(senha.encode('utf-8'), salt)
    return hash_bytes.decode('utf-8')

def verificar_senha(senha_pura: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(
        senha_pura.encode('utf-8'), 
        senha_hash.encode('utf-8')
    )

def criar_token_acesso(data: dict):
    para_codificar = data.copy()
    # Usando timezone.utc para evitar avisos de expiração em versões novas
    expira = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    para_codificar.update({"exp": expira})
    return jwt.encode(para_codificar, SECRET_KEY, algorithm=ALGORITHM)