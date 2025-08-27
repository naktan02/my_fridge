from pydantic import BaseModel
from datetime import date
from typing import List, Optional

# --- 이 파일을 아래 내용으로 전체 교체해주세요 ---

# Ingredient 모델 자체를 위한 스키마
# 이 스키마는 다른 스키마 안에서 중첩되어 사용됩니다.
class Ingredient(BaseModel):
    id: int
    name: str

    class Config:
        # Pydantic v1에서는 orm_mode = True
        # SQLAlchemy 모델 객체의 속성을 읽어올 수 있게 합니다.
        from_attributes = True

# 클라이언트로부터 재료를 생성할 때 받을 데이터 형식 (입력용)
class UserIngredientCreate(BaseModel):
    ingredient_name: str
    expiration_date: date


# 클라이언트에게 재료 정보를 반환할 때의 데이터 형식 (출력용)
class UserIngredientResponse(BaseModel):
    id: int
    user_id: int
    expiration_date: date
    
    # 'ingredient_name' 대신, 중첩된 Ingredient 스키마를 사용합니다.
    # 이렇게 하면 UserIngredient.ingredient 관계를 자동으로 인식하여 처리합니다.
    ingredient: Ingredient

    class Config:
        # Pydantic v1에서는 orm_mode = True
        from_attributes = True

class MasterIngredientCreate(BaseModel):
    name: str
    category: Optional[str] = None
    storage_type: Optional[str] = None

# '재료 사전'의 정보를 반환할 때 사용할 스키마 (출력용)
class MasterIngredientResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    storage_type: Optional[str] = None

    class Config:
        from_attributes = True