# main.py
from fastapi import FastAPI
from api.v1.routes import dishes, ingredients,users
from database import Base, engine # ✅ Base와 engine 임포트

# ✅ 데이터베이스 테이블을 생성하는 함수 추가
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="My Fridge API")

# ✅ 스타트업 이벤트 핸들러 추가
# FastAPI가 시작된 직후, create_db_and_tables 함수를 한 번 실행하라고 알려줍니다.
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

app.include_router(dishes.router, prefix="/api/v1/dishes", tags=["요리 (Dishes & Recipes)"])
app.include_router(ingredients.router, prefix="/api/v1/ingredients", tags=["나의 재료 (User Ingredients)"])
app.include_router(users.router, prefix="/api/v1/users", tags=["사용자 (Users)"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the My Fridge API!"}