# /backend/schemas/dish.py

from pydantic import BaseModel
from typing import List, Optional

# --- Recipe 스키마를 이곳에 함께 정의하거나, recipe.py로 분리해도 좋습니다. ---

# RecipeIngredient의 상세 정보를 담는 스키마
class RecipeIngredientInfo(BaseModel):
    name: str
    quantity_display: Optional[str] = None

# Recipe의 기본 정보 (생성 시에는 id가 없음)
class RecipeBase(BaseModel):
    title: Optional[str] = None
    difficulty: Optional[int] = None
    serving_size: Optional[str] = None
    cooking_time: Optional[int] = None
    instructions: str
    youtube_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

# Recipe 생성 시 입력받는 스키마
class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientInfo] # 재료 정보를 함께 받음

# 1. Ingredient 모델을 위한 스키마
class IngredientResponse(BaseModel):
    name: str
    class Config:
        from_attributes = True

# 2. RecipeIngredient 모델을 위한 스키마 (IngredientResponse를 중첩)
class RecipeIngredientResponse(BaseModel):
    quantity_display: Optional[str] = None
    ingredient: IngredientResponse  # 'ingredient' 객체 안에 'name'이 있는 구조
    class Config:
        from_attributes = True

# 3. Recipe 응답 스키마가 새로운 RecipeIngredientResponse를 사용하도록 수정
class Recipe(RecipeBase):
    id: int
    ingredients: List[RecipeIngredientResponse]
    class Config:
        from_attributes = True

# --- Dish 스키마 ---

class DishBase(BaseModel):
    name: str
    cuisine_type: Optional[str] = None
    tags: Optional[List[str]] = None

# 관리자가 Dish를 생성할 때 입력하는 스키마
class DishCreate(DishBase):
    recipes: List[RecipeCreate] # Dish를 만들 때 레시피 정보도 함께 받음

# Dish 정보를 반환하는 스키마 (모든 레시피 포함)
class Dish(DishBase):
    id: int
    recipes: List[Recipe]

    class Config:
        from_attributes = True
        
        
class DishSearchResult(BaseModel):
    """개별 검색 결과를 위한 스키마"""
    score: Optional[float] = None  # Elasticsearch의 연관성 점수
    dish_id: int
    recipe_id: int
    dish_name: str
    recipe_title: Optional[str] = None 
    thumbnail_url: Optional[str] = None

    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    """전체 검색 응답을 위한 스키마"""
    total: int # 총 검색 결과 개수
    results: List[DishSearchResult]