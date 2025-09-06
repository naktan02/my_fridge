from elasticsearch import AsyncElasticsearch
from contextlib import asynccontextmanager
import os, asyncio, logging

logger = logging.getLogger(__name__)
es_client: AsyncElasticsearch | None = None

DISHES_INDEX_NAME = "dishes"

async def _wait_for_es(es: AsyncElasticsearch, retries=12, base=0.5):
    last = None
    for i in range(retries):
        try:
            await es.info()
            return
        except Exception as e:
            last = e
            delay = base * (1.5 ** i)
            logger.warning("ES not ready (%s). retry %d/%d in %.2fs",
                           e.__class__.__name__, i+1, retries, delay)
            await asyncio.sleep(delay)
    raise RuntimeError(f"ES not reachable: {last}")

async def create_dishes_index(es: AsyncElasticsearch):
    exists = await es.indices.exists(index=DISHES_INDEX_NAME)
    if exists:
        return
    # nori 사용 시 플러그인 필요(아래 참고)
    mappings = {
        "properties": {
            "dish_name":     {"type": "text", "analyzer": "nori"},
            "recipe_title":  {"type": "text", "analyzer": "nori"},
            "ingredients":   {"type": "keyword"},
            "core_identity_embedding": {"type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"},
            "context_embedding":       {"type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"},
            "dish_id":       {"type": "integer"},
            "recipe_id":     {"type": "integer"},
            "thumbnail_url": {"type": "keyword", "index": False}
        }
    }
    await es.indices.create(index=DISHES_INDEX_NAME, mappings=mappings)

@asynccontextmanager
async def lifespan(app):
    global es_client
    es_url = os.getenv("ELASTICSEARCH_URL", "http://my_fridge_es:9200")
    es_client = AsyncElasticsearch(es_url, request_timeout=10)
    try:
        await _wait_for_es(es_client)          # 재시도 포함
        print("Elasticsearch client connected.")
        await create_dishes_index(es_client)
        yield
    finally:
        if es_client:
            await es_client.close()
            es_client = None
            print("Elasticsearch client disconnected.")

def get_es_client() -> AsyncElasticsearch:
    assert es_client is not None, "ES client not initialized yet"
    return es_client
