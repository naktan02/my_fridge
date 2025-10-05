# My Fridge API 冷蔵庫をお願い (내 냉장고를 부탁해)

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.19-yellow.svg)](https://www.elastic.co/elasticsearch/)

`My Fridge API`는 사용자가 보유한 재료를 기반으로 만들 수 있는 요리 레시피를 추천해주는 FastAPI 기반의 백엔드 서비스입니다. PostgreSQL을 주 데이터베이스로 사용하며, 빠르고 정확한 레시피 검색을 위해 Elasticsearch를 도입했습니다.

## ✨ 주요 기능

* **재료 기반 레시피 추천**: 사용자가 가진 재료 목록을 기반으로 만들 수 있는 요리 목록을 추천합니다.
* **키워드 검색**: "매콤한", "찌개" 등 다양한 키워드로 원하는 레시피를 검색할 수 있습니다.
* **사용자 관리**: 회원가입, 로그인, 로그아웃 기능을 통해 개인화된 서비스를 제공합니다.
* **내 냉장고 관리**: 사용자가 보유한 재료를 등록하고 관리할 수 있습니다.

## 🚀 시작하기

### 사전 요구사항

* Docker
* Docker Compose

### 설치 및 실행

1.  **프로젝트 클론**
    ```bash
    git clone <your-repository-url>
    cd my_fridge
    ```

2.  **환경변수 설정**
    프로젝트 루트의 `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 내부 변수들을 환경에 맞게 수정합니다.
    ```bash
    cp .env.example .env
    ```

3.  **Docker Compose 실행**
    아래 명령어를 실행하여 API 서버, 데이터베이스, Elasticsearch 등 모든 서비스를 한번에 실행합니다.
    ```bash
    docker-compose up --build -d
    ```
    API 서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

4.  **데이터베이스 초기화 및 데이터 임포트**
    최초 실행 시, 아래 명령어들을 순서대로 실행하여 DB 스키마를 생성하고 초기 데이터를 임포트해야 합니다.

    ```bash
    # 1. 데이터베이스 스키마 생성 (Alembic)
    docker-compose exec api uv run alembic upgrade head

    # 2. 초기 데이터 임포트 (재료, 레시피 등)
    docker-compose exec api uv run python es_db_manage.py db import_all
    ```

5.  **Elasticsearch 인덱스 생성 및 색인**
    검색 기능을 사용하려면 Elasticsearch 인덱스를 생성하고 데이터를 색인해야 합니다.
    ```bash
    # 1. 검색용 인덱스 생성 (한글 분석기 설정 포함)
    docker-compose exec api uv run python es_db_manage.py es create_index

    # 2. DB 데이터를 Elasticsearch로 색인
    docker-compose exec api uv run python es_db_manage.py es reindex
    ```

## 📖 API 사용법

API는 `http://localhost:8000`을 기본 URL로 사용합니다. 모든 요청은 **로그인 후 발급받는 `session_id` 쿠키**가 필요합니다.

### 사용자 (Users)

* **회원가입**: `POST /api/v1/users/signup`
    ```json
    {
      "email": "user@example.com",
      "password": "password123"
    }
    ```
* **로그인**: `POST /api/v1/users/login`
    ```json
    {
      "email": "user@example.com",
      "password": "password123"
    }
    ```
* **로그아웃**: `POST /api/v1/users/logout`

### 내 재료 (Ingredients)

* **내 재료 추가**: `POST /api/v1/ingredients/me`
    ```json
    {
      "ingredient_name": "김치",
      "expiration_date": "2025-12-31"
    }
    ```

### 요리 및 레시피 (Dishes & Recipes)

* **통합 검색**: `POST /api/v1/dishes/search/grouped`
    * 앱의 로컬 재료 목록과 검색어를 조합하여 요리를 추천받습니다.
    ```json
    {
      "ingredients": ["김치", "돼지고기", "양파"],
      "q": "칼칼한 찌개",
      "ing_mode": "RATIO",
      "ing_ratio": 0.7
    }
    ```
* **레시피 상세 정보 조회**: `POST /api/v1/recipes/by-ids`
    * 위 통합 검색 결과로 받은 `recipe_ids` 목록을 전송하여 레시피 상세 정보를 조회합니다.
    ```json
    [15, 3, 5]
    ```

## 🛠️ 데이터베이스 및 Elasticsearch

### PostgreSQL (주 데이터베이스)

* **역할**: 사용자 정보, 전체 레시피, 재료 마스터 데이터 등 모든 원본 데이터를 저장합니다.
* **주요 테이블**:
    * `users`: 사용자 정보
    * `dishes`: 요리(음식)의 대표 정보 (e.g., 김치찌개)
    * `recipes`: 개별 레시피 상세 정보 (e.g., 백종원 김치찌개)
    * `ingredients`: 재료 마스터 정보
    * `user_ingredients`: 사용자가 보유한 재료 목록
    * `recipe_ingredients`: 레시피에 필요한 재료 목록 (M:N 관계)

### Elasticsearch (검색 엔진)

* **역할**: `nori` 한글 형태소 분석기를 활용하여 빠르고 정확한 전문(Full-text) 검색을 담당합니다.
* **인덱스**: `dishes`
* **인덱싱되는 주요 필드**:
    * `dish_name`: 요리 이름 (가중치 높음)
    * `recipe_title`: 레시피 제목
    * `ingredients`: 레시피에 포함된 재료 이름 목록
    * `description`: 요리에 대한 감성/표현 키워드 (e.g., "매콤한", "칼칼한")

## 🗂️ 프로젝트 구조