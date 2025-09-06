# /backend/api/v1/routes/dishes.py (코드 추가)

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

import models
from schemas.dish import Dish, DishCreate, Recipe, RecipeCreate 
from repositories.dishes import DishRepository
from database import get_db
from auth.dependencies import get_current_user, is_admin

# --- 검색 관련 모듈 import ---
from search_client import get_es_client, DISHES_INDEX_NAME
from ml import get_embedding_model
from repositories.search import SearchRepository
from elasticsearch import AsyncElasticsearch
from sentence_transformers import SentenceTransformer

# ... 기존 라우터 코드 ...
router = APIRouter(tags=["Dishes"])

def get_repo(db: Session = Depends(get_db)) -> DishRepository:
    return DishRepository(db=db)

# --- 검색 리포지토리 의존성 주입 함수 ---
def get_search_repo(es: AsyncElasticsearch = Depends(get_es_client)) -> SearchRepository:
    return SearchRepository(es_client=es)
    
# --- 관리자용 배치 인덱싱 API ---
@router.post("/admin/search/reindex", status_code=202) # 202 Accepted: 작업이 접수되었음을 의미
async def reindex_dishes_for_search(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    dish_repo: DishRepository = Depends(get_repo),
    search_repo: SearchRepository = Depends(get_search_repo),
    embedding_model: SentenceTransformer = Depends(get_embedding_model),
    admin_user: models.User = Depends(is_admin)
):
    """
    **관리자용 API** - PostgreSQL의 모든 요리 데이터를 Elasticsearch에 재색인합니다.
    시간이 오래 걸릴 수 있으므로 백그라운드 작업으로 처리됩니다.
    """
    
    def background_reindexing():
        """백그라운드에서 실행될 실제 재색인 로직"""
        print("Starting background reindexing...")
        
        # 1. PostgreSQL에서 모든 요리 데이터 가져오기
        all_dishes = dish_repo.get_all_dishes()
        
        # 2. Elasticsearch에 넣을 문서 형태로 가공
        documents = []
        texts_to_embed = []
        for dish in all_dishes:
            for recipe in dish.recipes:
                ingredient_names = [item.ingredient.name for item in recipe.ingredients]
                # 임베딩할 텍스트 생성 (요리명, 재료, 조리법 등을 조합)
                text_for_embedding = f"요리명: {dish.name}. 재료: {', '.join(ingredient_names)}. 설명: {dish.semantic_description}"
                
                texts_to_embed.append(text_for_embedding)
                
                # Elasticsearch 문서 구조 생성
                doc = {
                    "_index": DISHES_INDEX_NAME,
                    "_id": f"{dish.id}_{recipe.id}",
                    "_source": {
                        "dish_id": dish.id,
                        "recipe_id": recipe.id,
                        "dish_name": dish.name,
                        "thumbnail_url": dish.thumbnail_url,
                        "ingredients": ingredient_names
                    }
                }
                documents.append(doc)

        # 3. AI 모델로 텍스트들을 한번에 벡터로 변환 (배치 처리)
        if texts_to_embed:
            embeddings = embedding_model.encode(texts_to_embed)
            
            # 3. 문서에 생성된 벡터만 추가
            for doc, embedding in zip(documents, embeddings):
                doc["recipe_embedding"] = embedding.tolist()
        
            # 4. Elasticsearch에 최종 문서 대량 색인
            # documents 리스트를 bulk 헬퍼에 맞게 action 형태로 변환
            actions = [
                {"_index": doc.pop("_index"), "_id": doc.pop("_id"), "_source": doc}
                for doc in documents
            ]
            import asyncio
            asyncio.run(search_repo.bulk_index_dishes(actions))
            
        print("Background reindexing finished.")

    # 백그라운드 작업으로 재색인 함수를 실행
    background_tasks.add_task(background_reindexing)
    
    return {"message": "데이터 재색인 작업이 백그라운드에서 시작되었습니다."}

# 관리자용: 새로운 요리와 레시피 생성
@router.post("", response_model=Dish, status_code=201)
def create_dish(
    dish_create: DishCreate, 
    repo: DishRepository = Depends(get_repo),
    # ✅ 추가: 관리자 권한이 있는지 확인
    admin_user: models.User = Depends(is_admin)
):
    return repo.create_dish_with_recipes(dish_create=dish_create)

# 사용자용: 모든 요리 정보 조회
@router.get("", response_model=List[Dish])
def get_all_dishes(repo: DishRepository = Depends(get_repo)):
    return repo.get_all_dishes()

# 관리자용: 기존 요리에 새로운 레시피 추가
@router.post("/{dish_id}/recipes", response_model=Recipe, status_code=201)
def add_recipe_to_dish(
    dish_id: int,
    recipe_create: RecipeCreate,
    repo: DishRepository = Depends(get_repo),
    # ✅ 추가: 관리자 권한이 있는지 확인
    admin_user: models.User = Depends(is_admin)
):
    return repo.add_recipe_to_dish(dish_id=dish_id, recipe_data=recipe_create)

# ✅ 추가: 요리 추천 API
@router.get("/recommendations", response_model=List[Dish])
def get_recommended_dishes(
    repo: DishRepository = Depends(get_repo),
    current_user: models.User = Depends(get_current_user)
):
    """
    **사용자용 API** - 현재 보유한 재료로 만들 수 있는 요리를 추천합니다.
    """
    return repo.get_dishes_by_user_ingredients(user_id=current_user.id)