from elasticsearch import AsyncElasticsearch
from contextlib import asynccontextmanager
import os, asyncio, logging

logger = logging.getLogger(__name__)
es_client: AsyncElasticsearch | None = None

DISHES_INDEX_NAME = "dishes"  # 운영 시엔 별칭/버전 인덱스 전략 권장

async def _wait_for_es(es, retries=6, base=0.25, max_delay=2.0):
    last = None
    for i in range(retries):
        try:
            await es.cluster.health(wait_for_status="yellow", timeout="5s")
            return
        except Exception as e:
            last = e
            delay = min(max_delay, base * (1.5 ** i))
            await asyncio.sleep(delay)
    raise RuntimeError(f"ES not reachable: {last}")

async def create_dishes_index(es: AsyncElasticsearch):
    """
    nori + 사용자사전/동의어를 쓰는 '텍스트 전용' 인덱스 생성.
    - dict/userdict_ko.txt, dict/synonym-set.txt 는 ES 컨테이너 내부 경로여야 함(볼륨 마운트 필수).
    """
    exists = await es.indices.exists(index=DISHES_INDEX_NAME)
    if exists:
        return

    settings = {
        "analysis": {
            "analyzer": {
                # 1) 색인 분석기: 동의어 없이 가볍게
                "ko_index_analyzer": {
                    "type": "custom",
                    "tokenizer": "my_nori_tokenizer",
                    "filter": ["my_pos_filter", "lowercase_filter"]
                },
                # 2) 검색 분석기: synonym_graph 적용
                "ko_search_analyzer": {
                    "type": "custom",
                    "tokenizer": "my_nori_tokenizer",
                    "filter": ["my_pos_filter", "lowercase_filter", "synonym_filter_query"]
                },
                # 3) ★ 동의어 '파싱 전용' 분석기: standard + lowercase (겹친 토큰 금지)
                "synonym_parse_std": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"]
                }
            },
            "tokenizer": {
                "my_nori_tokenizer": {
                    "type": "nori_tokenizer",
                    "decompound_mode": "mixed",
                    "discard_punctuation": True,      # 문자열 "true" 말고 bool
                    "user_dictionary": "userdict_ko.txt",  # ← 현재 컨테이너 경로에 맞춤
                    "lenient": True
                }
            },
            "filter": {
                "my_pos_filter": {"type": "nori_part_of_speech", "stoptags": ["E","J","IC"]},
                "lowercase_filter": {"type": "lowercase"},
                # 색인용 동의어 필터는 아예 제거(혼란 방지)
                "synonym_filter_query": {
                    "type": "synonym_graph",
                    "synonyms_path": "synonym-set.txt",    # ← 현재 컨테이너 경로에 맞춤
                    "analyzer": "synonym_parse_std",       # ← ★ 이 줄이 없으면 또 터짐
                    "updateable": True,
                    "lenient": False
                }
            },
            "similarity": {
                "bm25_desc": {"type": "BM25", "k1": 0.9, "b": 0.4}
            }
        }
    }

    mappings = {
        "properties": {
            "dish_id":   {"type": "integer"},
            "recipe_id": {"type": "integer"},
            "dish_name": {
                "type": "text",
                "analyzer": "ko_index_analyzer",
                "search_analyzer": "ko_search_analyzer",
                "fields": {"raw": {"type": "keyword"}}
            },
            "recipe_title": {
                "type": "text",
                "analyzer": "ko_index_analyzer",
                "search_analyzer": "ko_search_analyzer",
                "fields": {"raw": {"type": "keyword"}}
            },
            "ingredients": {
                "type": "keyword",  # 필터/집계/정확일치
                "fields": {
                    "tok": {
                        "type": "text",
                        "analyzer": "ko_index_analyzer",
                        "search_analyzer": "ko_search_analyzer"
                    }
                }
            },
            "description": {
                "type": "text",
                "analyzer": "ko_index_analyzer",
                "search_analyzer": "ko_search_analyzer",
                "similarity": "bm25_desc"
            }
        }
    }

    await es.indices.create(index=DISHES_INDEX_NAME, settings=settings, mappings=mappings)
    logger.info("Created index '%s' with nori analyzers.", DISHES_INDEX_NAME)

@asynccontextmanager
async def lifespan(app):
    global es_client
    es_url = os.getenv("ELASTICSEARCH_URL", "http://my_fridge_es:9200")
    es_client = AsyncElasticsearch(es_url, request_timeout=10)
    try:
        await _wait_for_es(es_client)
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
