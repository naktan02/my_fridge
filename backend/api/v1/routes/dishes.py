# /backend/api/v1/routes/dishes.py (코드 추가)

from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import models
from schemas.dish import Dish, DishCreate, Recipe, RecipeCreate , SearchResponse
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
@router.post("/admin/search/reindex", status_code=202)
async def reindex_dishes_for_search(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # ✅ 개선: 의존성 주입 함수를 사용하도록 통일합니다.
    dish_repo: DishRepository = Depends(get_repo),
    search_repo: SearchRepository = Depends(get_search_repo),
    embedding_model: SentenceTransformer = Depends(get_embedding_model),
    admin_user: models.User = Depends(is_admin)
):
    """
    **관리자용 API** - PostgreSQL의 모든 요리 데이터를 Elasticsearch에 재색인합니다.
    대용량 데이터를 처리하기 위해 백그라운드에서 배치 작업으로 수행됩니다.
    """

    # ✅ 개선 1: 함수 자체를 async def로 만들어 FastAPI가 직접 await하게 합니다.
    async def background_reindexing():
        """백그라운드에서 실행될 실제 재색인 로직"""
        print("Starting background reindexing...")
        BATCH_SIZE = 100  # 한 번에 처리할 문서 개수
        offset = 0
        total_processed = 0

        while True:
            # ✅ 개선 2 & 3: 배치 단위로 데이터를 가져옵니다 (Eager Loading 적용됨).
            dishes_batch = dish_repo.get_all_dishes(skip=offset, limit=BATCH_SIZE)
            if not dishes_batch:
                break # 처리할 데이터가 더 이상 없으면 루프 종료

            texts_for_core_identity = []
            texts_for_context = []
            documents_metadata = []

            for dish in dishes_batch:
                for recipe in dish.recipes:
                    ingredient_names = [item.ingredient.name for item in recipe.ingredients]
                    core_text = f"{dish.name}, {', '.join(ingredient_names)}"
                    texts_for_core_identity.append(core_text)
                    context_text = dish.semantic_description or ""
                    texts_for_context.append(context_text)
                    doc_meta = {
                        "_index": DISHES_INDEX_NAME, "_id": f"{dish.id}_{recipe.id}",
                        "dish_id": dish.id, "recipe_id": recipe.id,
                        "dish_name": dish.name, 
                        "recipe_title": recipe.title, # ✅ 추가: 레시피 제목
                        "thumbnail_url": recipe.thumbnail_url, # ✅ 수정: dish -> recipe
                        "ingredients": ingredient_names,
                    }
                    documents_metadata.append(doc_meta)

            if documents_metadata:
                # CPU 바운드 작업을 이벤트 루프에서 분리
                loop = asyncio.get_running_loop()
                core_embeddings, context_embeddings = await asyncio.gather(
                    loop.run_in_executor(None, embedding_model.encode, texts_for_core_identity),
                    loop.run_in_executor(None, embedding_model.encode, texts_for_context)
                )

                final_actions = []
                for meta, core_vec, ctx_vec in zip(documents_metadata, core_embeddings, context_embeddings):
                    meta["core_identity_embedding"] = core_vec.tolist()
                    meta["context_embedding"] = ctx_vec.tolist()
                    final_actions.append(meta)

                # ✅ 개선 1: asyncio.run() 대신 await을 사용합니다.
                await search_repo.bulk_index_dishes(final_actions)
                total_processed += len(final_actions)
                print(f"Processed batch of {len(final_actions)}. Total processed: {total_processed}")

            offset += BATCH_SIZE
            await asyncio.sleep(1) # DB와 ES에 가해지는 부하를 줄이기 위한 약간의 딜레이

        print(f"Background reindexing finished. Total {total_processed} documents.")

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


@router.get("/search", response_model=SearchResponse)
async def search_dishes_endpoint(
    request: Request, # 이벤트 루프에 접근하기 위해 필요
    q: Optional[str] = None,
    ingredients: Optional[str] = None, # 콤마로 구분된 문자열
    search_repo: SearchRepository = Depends(get_search_repo),
    embedding_model: SentenceTransformer = Depends(get_embedding_model)
):
    """
    **사용자용 API** - 키워드, 보유 재료를 사용하여 요리를 검색합니다.
    - `q`: 검색어 (예: "김치찌개", "얼큰한 국물요리")
    - `ingredients`: 보유 재료 목록 (예: "돼지고기,두부,김치")
    """
    query_vector = None
    if q:
        # ✅ 개선: CPU 바운드 작업을 이벤트 루프에서 분리하여 비동기 실행
        loop = asyncio.get_running_loop()
        query_vector = await loop.run_in_executor(
            None,  # 기본 스레드 풀 사용
            embedding_model.encode,
            q
        )
        query_vector = query_vector.tolist()

    user_ingredients_list = ingredients.split(',') if ingredients else None

    search_results = await search_repo.search_dishes(
        query=q,
        query_vector=query_vector,
        user_ingredients=user_ingredients_list
    )
    return search_results