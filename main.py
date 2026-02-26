from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import List
from database import engine, get_db
import jwt, models, schemas, database, auth_utils, logging


# Cria as tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

# Configuração para o Swagger/Mobile usar o Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="RENU - Secure Multi-User API")



# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # No futuro, trocaremos o "*" pelo domínio real do app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração básica de logs (isso aparecerá no seu terminal Ubuntu)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Handler para erros inesperados (500)
@app.exception_handler(Exception)
async def gerenciar_erro_inesperado(request: Request, exc: Exception):
    # Aqui guardamos o erro "feio" no log para você ver no terminal
    logger.error(f"Erro inesperado: {str(exc)}", exc_info=True)
    
    # E retornamos uma mensagem limpa para o usuário
    return JSONResponse(
        status_code=500,
        content={
            "erro": "Erro Interno",
            "mensagem": "Ops, o servidor apresentou um erro. Por favor, tente novamente mais tarde."
        }
    )

# Handler para erros de validação (422) - Quando o JSON enviado está errado
@app.exception_handler(422)
async def gerenciar_erro_validacao(request: Request, exc: Exception):
    return JSONResponse(
        status_code=422,
        content={
            "erro": "Dados Inválidos",
            "mensagem": "Os dados enviados não estão no formato correto. Verifique os campos e tente novamente."
        }
    )

# --- DEPENDÊNCIA: OBTÉM O USUÁRIO LOGADO ---
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # PyJWT retorna o payload diretamente
        payload = jwt.decode(
            token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError: # Mudança aqui para PyJWTError
        raise credentials_exception
    
    user = db.query(models.UserDB).filter(models.UserDB.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- ROTAS DE AUTENTICAÇÃO ---

@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.UserDB).filter(models.UserDB.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")
    
    hashed_password = auth_utils.gerar_hash_senha(user.password)
    new_user = models.UserDB(email=user.email, senha_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Usuário criado com sucesso!"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.UserDB).filter(models.UserDB.email == form_data.username).first()
    if not user or not auth_utils.verificar_senha(form_data.password, user.senha_hash):
        raise HTTPException(status_code=400, detail="E-mail ou senha incorretos")
    
    access_token = auth_utils.criar_token_acesso(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- ROTAS DE CATEGORIA ---

@app.post("/categorias/")
def criar_categoria(cat: schemas.CategoriaCreate, db: Session = Depends(get_db), current_user: models.UserDB = Depends(get_current_user)):
    nova_cat = models.CategoriaDB(nome=cat.nome, dono_id=current_user.id)
    db.add(nova_cat)
    db.commit()
    db.refresh(nova_cat)
    return nova_cat

@app.get("/categorias/")
def listar_categorias(db: Session = Depends(get_db), current_user: models.UserDB = Depends(get_current_user)):
    return db.query(models.CategoriaDB).filter(models.CategoriaDB.dono_id == current_user.id).all()

@app.delete("/categorias/{cat_id}")
def eliminar_categoria(cat_id: int, db: Session = Depends(get_db), current_user: models.UserDB = Depends(get_current_user)):
    cat = db.query(models.CategoriaDB).filter(
        models.CategoriaDB.id == cat_id, 
        models.CategoriaDB.dono_id == current_user.id
    ).first()
    
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    try:
        db.delete(cat)
        db.commit()
        return {"message": "Categoria removida!"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="Não é possível apagar uma categoria que ainda possui itens vinculados."
        )

# --- ROTAS DE ITENS ---

@app.post("/items/")
def criar_item(item: schemas.ItemCreate, db: Session = Depends(get_db), current_user: models.UserDB = Depends(get_current_user)):
    # Verifica se a categoria pertence ao usuário
    cat = db.query(models.CategoriaDB).filter(
        models.CategoriaDB.id == item.categoria_id, 
        models.CategoriaDB.dono_id == current_user.id
    ).first()
    
    if not cat:
        raise HTTPException(status_code=400, detail="Categoria inválida ou não pertence a você.")

    novo_item = models.ItemDB(
        **item.model_dump(),
        dono_id=current_user.id
    )
    db.add(novo_item)
    db.commit()
    db.refresh(novo_item)
    return {"status": "sucesso", "item_id": novo_item.id}

@app.get("/items/")
def listar_itens(db: Session = Depends(get_db), current_user: models.UserDB = Depends(get_current_user)):
    # FILTRO DE SEGURANÇA: Apenas itens onde dono_id é o do usuário logado
    itens = db.query(models.ItemDB).filter(models.ItemDB.dono_id == current_user.id).all()
    resultado = []
    agora = datetime.utcnow()
    
    for i in itens:
        data_fim = i.data_inicio + timedelta(days=i.prazo_dias) if i.tipo_controle == "PRAZO" else i.data_validade_fixa
        dias_restantes = (data_fim - agora).days

        resultado.append({
            "id": i.id,
            "nome": i.nome,
            "categoria": i.categoria.nome if i.categoria else "Sem Categoria",
            "vence_em": data_fim.strftime("%d/%m/%Y"),
            "dias_restantes": max(0, dias_restantes),
            "vence_em_dt": data_fim,
            "status": "OK" if dias_restantes > 0 else "VENCIDO/TROCAR"
        })
    
    # Ordenação automática por vencimento
    resultado_ordenado = sorted(resultado, key=lambda x: x["vence_em_dt"])
    for item in resultado_ordenado: del item["vence_em_dt"]
    
    return resultado_ordenado

@app.get("/items/urgentes")
def listar_itens_urgentes(
    db: Session = Depends(get_db), 
    current_user: models.UserDB = Depends(get_current_user),
    dias_margem: int = 3
):
    itens = db.query(models.ItemDB).filter(models.ItemDB.dono_id == current_user.id).all()
    urgentes = []
    agora = datetime.utcnow()
    
    for i in itens:
        if i.tipo_controle == "PRAZO":
            data_fim = i.data_inicio + timedelta(days=i.prazo_dias)
        else:
            data_fim = i.data_validade_fixa
        
        diferenca = data_fim - agora
        
        # Filtra apenas o que já venceu ou vence dentro da margem (ex: 3 dias)
        if diferenca.days <= dias_margem:
            urgentes.append({
                "id": i.id,
                "nome": i.nome,
                "categoria": i.categoria.nome if i.categoria else "Sem Categoria",
                "vence_em": data_fim.strftime("%d/%m/%Y"),
                "dias_restantes": max(0, diferenca.days),
                "status": "VENCIDO" if diferenca.days < 0 else "URGENTE",
                "vence_em_dt": data_fim
            })
    
    return sorted(urgentes, key=lambda x: x["vence_em_dt"])

@app.patch("/items/{item_id}/renovar")
def renovar_item(item_id: int, db: Session = Depends(get_db), current_user: models.UserDB = Depends(get_current_user)):
    item = db.query(models.ItemDB).filter(models.ItemDB.id == item_id, models.ItemDB.dono_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    if item.tipo_controle != "PRAZO":
        raise HTTPException(status_code=400, detail="Apenas itens 'PRAZO' podem ser renovados.")
    
    item.data_inicio = datetime.utcnow()
    db.commit()
    return {"message": "Ciclo renovado!"}

@app.delete("/items/{item_id}")
def eliminar_item(item_id: int, db: Session = Depends(get_db), current_user: models.UserDB = Depends(get_current_user)):
    item = db.query(models.ItemDB).filter(models.ItemDB.id == item_id, models.ItemDB.dono_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(item)
    db.commit()
    return {"message": "Item removido!"}

# --- GESTÃO DE PERFIL ---

@app.get("/me")
def ver_perfil(current_user: models.UserDB = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "total_itens": len(current_user.itens),
        "total_categorias": len(current_user.categorias)
    }

@app.patch("/me/alterar-senha")
def alterar_senha(
    nova_senha: str, 
    db: Session = Depends(get_db), 
    current_user: models.UserDB = Depends(get_current_user)
):
    # Criptografa a nova senha usando a lógica moderna do auth_utils
    current_user.senha_hash = auth_utils.gerar_hash_senha(nova_senha)
    db.commit()
    return {"message": "Senha atualizada com sucesso!"}

@app.delete("/me/encerrar-conta")
def excluir_conta(
    db: Session = Depends(get_db), 
    current_user: models.UserDB = Depends(get_current_user)
):
    # O SQLAlchemy cuidará de apagar itens/categorias se configurado o 'cascade'
    # Caso contrário, removemos o usuário e o banco lida com as FKs
    db.delete(current_user)
    db.commit()
    return {"message": "Conta e todos os dados associados foram removidos."}