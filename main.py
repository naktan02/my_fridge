from fastapi import FastAPI
from .api.v1.routes import dishes

app = FastAPI(title="내 냉장고를 부탁해 API")
app.include_router(dishes.router, prefix="/api/v1/dishes", tags=["Dish Types"])

@app.get("/")
def read_root():
    return {"message": "내 냉장고를 부탁해 API 서버"}