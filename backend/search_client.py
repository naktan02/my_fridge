# /backend/search_client.py (수정)

from elasticsearch import AsyncElasticsearch
from contextlib import asynccontextmanager
import os

es_client = None

# --- 1. 인덱스 이름 정의 ---
DISHES_INDEX_NAME = "dishes" 

async def create_dishes_index():
    """'dishes' 인덱스가 없으면 생성합니다."""
    if not await es_client.indices.exists(index=DISHES_INDEX_NAME):
        index_mapping = {
            "properties": {
                # --- 검색에 사용될 필드들 ---
                "dish_name": {"type": "text", "analyzer": "nori"},
                "ingredients": {"type": "keyword"},
                "recipe_embedding": {
                    "type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"
                },
                
                # --- 식별 및 결과 표시용 필드들 ---
                "dish_id": {"type": "integer"},
                "recipe_id": {"type": "integer"},
                "thumbnail_url": {"type": "keyword", "index": False}
            }
        }
        
        print(f"Creating index '{DISHES_INDEX_NAME}'...")
        await es_client.indices.create(
            index=DISHES_INDEX_NAME,
            mappings=index_mapping
        )


@asynccontextmanager
async def lifespan(app):
    """FastAPI 앱 시작/종료 시 이벤트 처리"""
    global es_client
    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    es_client = AsyncElasticsearch(es_url)
    print("Elasticsearch client connected.")
    
    # --- 2. 앱 시작 시 인덱스 생성 함수 호출 ---
    await create_dishes_index()
    
    yield
    
    await es_client.close()
    print("Elasticsearch client disconnected.")


def get_es_client() -> AsyncElasticsearch:
    """Elasticsearch 클라이언트 의존성 주입 함수"""
    return es_client