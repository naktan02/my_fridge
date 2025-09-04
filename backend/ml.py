# /backend/ml.py (신규 생성)

from sentence_transformers import SentenceTransformer

# --- 모델 설정 ---
MODEL_NAME = "nlpai-lab/KURE-v1"
embedding_model = None

def load_embedding_model():
    """앱 시작 시 임베딩 모델을 로드합니다."""
    global embedding_model
    embedding_model = SentenceTransformer(MODEL_NAME)
    print(f"Embedding model '{MODEL_NAME}' loaded.")

def get_embedding_model() -> SentenceTransformer:
    """임베딩 모델 의존성 주입 함수"""
    return embedding_model