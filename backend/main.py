# /backend/main.py (수정)

from fastapi import FastAPI
from contextlib import asynccontextmanager

# --- 모듈 import ---
from api.v1.routes import dishes, ingredients, users
from search_client import es_client, lifespan as es_lifespan
from ml import load_embedding_model

# --- FastAPI 앱 생명주기 관리 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # AI 모델 로드
    load_embedding_model()
    
    # Elasticsearch 클라이언트 생명주기 관리
    async with es_lifespan(app) as _:
        yield

# --- FastAPI 앱 생성 ---
app = FastAPI(title="My Fridge API", lifespan=lifespan)


# --- 라우터 포함 ---
app.include_router(dishes.router, prefix="/api/v1/dishes", tags=["요리 (Dishes & Recipes)"])
app.include_router(ingredients.router, prefix="/api/v1/ingredients", tags=["재료 (Ingredients)"])
app.include_router(users.router, prefix="/api/v1/users", tags=["사용자 (Users)"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the My Fridge API!"}