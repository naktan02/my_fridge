# /backend/main.py

from fastapi import FastAPI
from api.v1.routes import dishes, ingredients, users

app = FastAPI(title="My Fridge API")

# Alembic으로 DB 스키마를 관리하므로 startup 이벤트는 더 이상 필요 없습니다.

# ✅ 수정: 각 라우터의 전체 URL 접-두사(prefix)를 여기서 명확하게 지정
app.include_router(dishes.router, prefix="/api/v1/dishes", tags=["요리 (Dishes & Recipes)"])
app.include_router(ingredients.router, prefix="/api/v1/ingredients", tags=["재료 (Ingredients)"])
app.include_router(users.router, prefix="/api/v1/users", tags=["사용자 (Users)"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the My Fridge API!"}