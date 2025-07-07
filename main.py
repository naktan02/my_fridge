# main.py
import sys
import os
from fastapi import FastAPI
from api.v1.routes import dishes, ingredients

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

app = FastAPI(title="My Fridge API")
app.include_router(dishes.router, prefix="/api/v1/dishes", tags=["Dish Types"])
app.include_router(ingredients.router, prefix="/api/v1", tags=["User Ingredients"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the My Fridge API!"}