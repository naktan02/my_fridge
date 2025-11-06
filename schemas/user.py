# schemas/user.py (신규 생성)
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    nickname: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    nickname: str
    email: EmailStr

    class Config:
        from_attributes = True
        