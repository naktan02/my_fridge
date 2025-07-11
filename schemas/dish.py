from pydantic import BaseModel

# --- 이 파일을 아래 내용으로 교체하는 것을 추천합니다 ---

# 공통 속성을 위한 기본 스키마
class DishTypeBase(BaseModel):
    name: str

# 생성을 위한 스키마 (입력용)
class DishTypeCreate(DishTypeBase):
    pass

# 응답을 위한 스키마 (출력용)
class DishType(DishTypeBase):
    id: int

    class Config:
        # SQLAlchemy 모델 객체의 속성을 읽어올 수 있게 합니다.
        from_attributes = True
