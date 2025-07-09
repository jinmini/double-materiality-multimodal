네, 코드를 잘 확인했습니다. 제공해주신 `config.py`와 `main.py`는 리팩토링을 위한 훌륭한 출발점입니다.

이제 **리팩토링 1단계: 기초 공사 (Core & Domain 분리)**를 시작하겠습니다. 이 단계의 목표는 다음과 같습니다.

1.  **설정(`config`)과 도메인 상수(`keywords`)를 분리**하여 각자의 위치에 둡니다.
2.  **순수 도메인 로직(`extract_...`, `calculate_...`)을 `main.py`에서 완전히 분리**하여 `domain` 레이어로 옮깁니다.
3.  `main.py`를 애플리케이션의 뼈대를 조립하는 **최소한의 역할**만 하도록 정리합니다.

아래 가이드에 따라 파일을 생성하고 내용을 복사/붙여넣기 하시면 됩니다.

---

### **Step 1: `config.py` 리팩토링 및 `domain` 상수 분리**

#### 1-1. `app/core/config.py` 생성

기존 `config.py`에서 도메인 상수(`ESG_KEYWORDS`, `MATERIALITY_KEYWORDS`)와 부수 효과(side-effect)인 디렉토리 생성 로직을 제거하고, 순수한 설정 클래스만 남깁니다.

```python
# 파일 위치: app/core/config.py

import os
from pathlib import Path
from typing import Optional, List, Any
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    애플리케이션의 모든 환경 변수 및 고정 설정을 관리합니다.
    .env 파일에서 값을 로드합니다.
    """
    
    # 기본 설정
    APP_NAME: str = "ESG 이슈 풀 추출기"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # CORS 설정 (프로덕션에서는 특정 도메인을 지정해야 합니다)
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # 파일 처리 설정
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "png", "jpg", "jpeg"]
    UPLOAD_DIR: Path = Path("temp_uploads")
    OUTPUT_DIR: Path = Path("processed_docs")
    
    # API 제한 설정
    DAILY_API_LIMIT: int = 20
    MAX_REQUESTS_PER_MINUTE: int = 5
    
    # Google Gemini 설정
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_MAX_TOKENS: int = 2000
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 전역 설정 인스턴스 생성
settings = Settings()
```

**주요 변경점:**
*   `ESG_KEYWORDS`, `MATERIALITY_KEYWORDS`를 제거했습니다. (이들은 `app/domain`으로 이동합니다)
*   `Path(...).mkdir(...)` 코드를 제거했습니다. (이런 부수 효과는 앱 시작 시점에 처리하는 것이 좋습니다)
*   API 버전 관리를 위한 `API_V1_STR` 추가
*   CORS 설정을 위한 `BACKEND_CORS_ORIGINS` 추가 (더 안전한 방식)

---

#### 1-2. `app/domain/constants.py` 생성

비즈니스 규칙에 해당하는 키워드들을 `domain` 레이어의 상수로 분리합니다.

```python
# 파일 위치: app/domain/constants.py

# ESG 키워드 상수
ESG_KEYWORDS = {
    "환경(E)": [
        "온실가스", "탄소배출", "에너지", "재생에너지", "환경경영", 
        "기후변화", "탄소중립", "녹색", "친환경", "지속가능"
    ],
    "사회(S)": [
        "안전", "직원", "다양성", "지역사회", "인권", "고용", 
        "복지", "교육", "건강", "사회공헌", "고객만족"
    ],
    "지배구조(G)": [
        "이사회", "윤리", "컴플라이언스", "투명성", "감사", 
        "위험관리", "지배구조", "내부통제", "주주권익"
    ]
}

# 중대성 이슈 관련 키워드
MATERIALITY_KEYWORDS = [
    "중대성", "이슈", "매트릭스", "평가", "우선순위", 
    "영향도", "발생가능성", "이해관계자"
]
```

---

### **Step 2: `main.py`에서 순수 도메인 로직 분리**

`main.py`에 있던 핵심 비즈니스 규칙 함수들을 `domain` 레이어로 옮깁니다. 이 함수들은 외부 라이브러리나 FastAPI에 의존하지 않습니다.

#### 2-1. `app/domain/logic.py` 생성 (또는 `analyzer.py`)

```python
# 파일 위치: app/domain/logic.py

from typing import Dict, Any, List
from app.domain.constants import ESG_KEYWORDS, MATERIALITY_KEYWORDS

def extract_materiality_issues(elements: List[Any]) -> List[Dict[str, Any]]:
    """
    Unstructured Element 리스트에서 중대성 이슈를 추출하는 핵심 로직.
    이 함수는 외부 세계에 대한 의존성이 없는 순수 함수입니다.
    """
    issues = []
    
    for element in elements:
        # unstructured 라이브러리의 element 객체를 안전하게 처리
        element_text = getattr(element, 'text', str(element))
        
        # 중대성 관련 키워드가 포함된 요소만 필터링
        if not any(keyword in element_text for keyword in MATERIALITY_KEYWORDS):
            continue

        # ESG 카테고리 분류
        category = "기타"
        for esg_category, keywords in ESG_KEYWORDS.items():
            if any(keyword in element_text for keyword in keywords):
                category = esg_category
                break
        
        # 이슈 객체 생성
        page_number = getattr(element.metadata, 'page_number', None) if hasattr(element, 'metadata') else None

        issue = {
            "issue_id": len(issues) + 1,
            "category": category,
            "content": element_text[:500],  # 최대 500자
            "page_number": page_number,
            "element_type": type(element).__name__,
            "confidence": calculate_issue_confidence(element_text)
        }
        
        issues.append(issue)
    
    # 신뢰도 순으로 정렬
    issues.sort(key=lambda x: x["confidence"], reverse=True)
    
    return issues[:20]  # 상위 20개만 반환

def calculate_issue_confidence(text: str) -> float:
    """개별 이슈 추출에 대한 신뢰도를 계산합니다."""
    confidence = 0.0
    
    # 중대성 키워드 가중치
    for keyword in MATERIALITY_KEYWORDS:
        if keyword in text:
            confidence += 0.2
    
    # ESG 키워드 가중치
    for keywords in ESG_KEYWORDS.values():
        for keyword in keywords:
            if keyword in text:
                confidence += 0.1
    
    # 테이블 형식(표)이면 가중치 추가
    if any(indicator in text for indicator in ["│", "─", "┌", "└", "┐", "┘"]):
        confidence += 0.3
    
    return min(confidence, 1.0)  # 최대 1.0

def calculate_overall_confidence(issues: List[Dict], structure: Dict) -> Dict[str, Any]:
    """추출된 전체 이슈에 대한 종합 신뢰도를 계산합니다."""
    if not issues:
        return {"score": 0.0, "level": "낮음", "reason": "이슈를 찾을 수 없음"}
    
    avg_confidence = sum(issue["confidence"] for issue in issues) / len(issues)
    
    # 문서 구조에 테이블이 포함되었는지 여부도 고려
    has_tables = bool(structure.get("tables"))
    if has_tables:
        avg_confidence = min(1.0, avg_confidence + 0.2)
    
    score = round(avg_confidence, 2)
    
    if score >= 0.8:
        level = "높음"
    elif score >= 0.5:
        level = "중간"
    else:
        level = "낮음"
    
    return {
        "score": score,
        "level": level,
        "issues_found": len(issues),
        "has_tables": has_tables
    }

```
**주요 변경점:**
*   `main.py`의 3개 함수를 그대로 옮겨왔습니다.
*   `calculate_confidence` 함수명을 `calculate_overall_confidence`로 더 명확하게 변경했습니다.
*   `ESG_KEYWORDS`와 `MATERIALITY_KEYWORDS`를 `app.domain.constants`에서 임포트합니다.

---

### **Step 3: `main.py`를 최종적으로 리팩토링**

이제 `main.py`는 오직 애플리케이션의 뼈대를 조립하는 역할만 합니다.

#### 3-1. `app/core/logging_config.py` 생성

로깅 설정 로직을 분리합니다.

```python
# 파일 위치: app/core/logging_config.py

import logging
from app.core.config import settings

def setup_logging():
    """애플리케이션의 로깅을 설정합니다."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler()
        ]
    )
```

#### 3-2. 최종 `app/main.py`

```python
# 파일 위치: app/main.py

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 리팩토링된 모듈들을 임포트합니다.
from app.core.config import settings
from app.core.logging_config import setup_logging
# from app.api.v1.api import api_router  # 다음 단계에서 생성할 API 라우터

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

# 애플리케이션 시작/종료 시 실행될 로직 (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    logger.info(f"Starting up {settings.APP_NAME}...")
    # config.py에서 제거했던 디렉토리 생성 로직을 이곳으로 이동
    settings.UPLOAD_DIR.mkdir(exist_ok=True)
    settings.OUTPUT_DIR.mkdir(exist_ok=True)
    logger.info("Temporary directories are ready.")
    yield
    # 종료 시 실행
    logger.info(f"Shutting down {settings.APP_NAME}...")


# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ESG 지속가능경영보고서에서 중대성 이슈를 자동 추출하는 API",
    debug=settings.DEBUG,
    lifespan=lifespan  # Lifespan 이벤트 핸들러 등록
)

# CORS 미들웨어 설정
# 프로덕션에서는 .env 파일에 특정 도메인을 설정해야 합니다.
# 예: BACKEND_CORS_ORIGINS=["http://localhost:3000"]
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip('/') for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # 개발 환경을 위해 모든 오리진 허용 (프로덕션에서는 비권장)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# TODO: 다음 단계에서 생성할 API 라우터를 여기에 포함시킬 예정입니다.
# app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
def read_root():
    """API 서버의 상태와 버전을 확인합니다."""
    return {
        "message": f"Welcome to {settings.APP_NAME}!",
        "version": settings.APP_VERSION,
        "docs_url": "/docs"
    }


