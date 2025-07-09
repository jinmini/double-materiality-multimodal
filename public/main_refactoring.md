물론입니다. 현재의 `main.py` 파일을 분석하고, 이를 **관심사의 분리(Separation of Concerns)** 원칙에 입각한 **계층형 아키텍처(Layered Architecture)**로 리팩토링하는 과정을 단계별로 설명해 드리겠습니다. 이 아키텍처는 도메인 주도 설계(DDD)의 핵심 아이디어인 '도메인 로직의 분리'를 자연스럽게 포함하게 됩니다.

현재 `main.py`의 문제점은 다음과 같습니다.
*   **웹 프레임워크 로직 (FastAPI):** 라우팅, 요청/응답 처리
*   **비즈니스 로직 (Service):** 파일 처리 워크플로우, Gemini AI 호출, 결과 병합
*   **도메인 로직 (Domain):** 중대성 이슈 추출 규칙, 신뢰도 계산 규칙
*   **인프라 로직 (Infrastructure):** 로깅 설정, 파일 저장/삭제, 외부 서비스(Gemini, Cost Manager) 연동
*   **설정 (Configuration):** 앱 초기화, 미들웨어 설정

이 모든 것이 한 파일에 섞여 있어 테스트, 유지보수, 확장이 매우 어렵습니다.

---

### `main.py` 리팩토링: 최소한의 역할만 남기기

리팩토링된 `main.py`는 오직 **애플리케이션의 뼈대를 조립하는 역할**만 수행해야 합니다. 즉, FastAPI 앱 인스턴스를 생성하고, 필요한 전역 설정을 적용한 뒤, 실제 API 엔드포인트가 정의된 라우터들을 연결하는 역할입니다.

#### **수정 후 `app/main.py`**

```python
# app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 애플리케이션의 핵심 로직과 분리된 모듈들을 임포트합니다.
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1.api import api_router  # API 엔드포인트들을 모아놓은 라우터

# 1. 로깅 설정 초기화 (별도의 모듈로 분리)
setup_logging()
logger = logging.getLogger(__name__)

# 2. FastAPI 앱 인스턴스 생성
#    - 모든 설정값은 config 파일에서 가져옵니다.
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ESG 지속가능경영보고서에서 중대성 이슈를 자동 추출하는 API",
    debug=settings.DEBUG,
    # docs_url, redoc_url 등 추가 설정도 이곳에서 관리합니다.
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 3. 전역 미들웨어 설정
#    - 프로덕션에서는 allow_origins를 특정 도메인 목록으로 제한해야 합니다.
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 4. API 라우터 포함
#    - 모든 API 엔드포인트는 api_router를 통해 관리됩니다.
#    - /api/v1 접두사를 사용하여 API 버전을 명시적으로 관리합니다.
app.include_router(api_router, prefix=settings.API_V1_STR)

# 5. 루트 엔드포인트 (선택 사항)
#    - 앱이 정상적으로 실행되었는지 확인하는 간단한 경로입니다.
@app.get("/", tags=["Root"])
async def root():
    """
    API 서버의 상태와 버전을 확인합니다.
    """
    logger.info("Root endpoint was accessed.")
    return {
        "message": f"Welcome to {settings.APP_NAME}!",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_v1": settings.API_V1_STR
    }

# 6. 애플리케이션 실행 로직 제거
#    - if __name__ == "__main__": 블록은 제거합니다.
#    - 애플리케이션 실행은 Uvicorn CLI를 통해 직접 수행합니다.
#      (예: uvicorn app.main:app --reload)
```

---

### 리팩토링 상세 설명: 무엇이 어디로 갔는가?

원래 `main.py`에 있던 코드들은 다음과 같이 각자의 역할에 맞는 위치로 이동합니다.

#### 1. 로깅 설정 (`logging.basicConfig`)
*   **어디로?** `app/core/logging_config.py`
*   **이유:** 로깅은 애플리케이션 전반에 걸친 '횡단 관심사'입니다. 별도의 설정 파일로 분리하여 `main.py`를 깔끔하게 유지하고, 나중에 더 복잡한 로깅(예: JSON 포맷터, 외부 로깅 서비스 연동)으로 확장하기 용이합니다.

#### 2. API 엔드포인트 (`@app.get`, `@app.post`)
*   **어디로?** `app/api/v1/endpoints/` 디렉토리 아래의 파일들로 분리됩니다.
    *   `/health`, `/usage` -> `app/api/v1/endpoints/health.py`
    *   `/upload` -> `app/api/v1/endpoints/documents.py`
*   **이유:** 리소스(자원)별로 파일을 분리하여 관리의 용이성을 높입니다. `APIRouter`를 사용하여 각 파일의 엔드포인트를 그룹화하고, 이를 `app/api/v1/api.py`에서 하나로 모아 `main.py`에 전달합니다.

#### 3. 도우미/검증 함수 (`check_usage_limit`, `validate_file`)
*   **어디로?** `app/dependencies/common.py`
*   **이유:** 이 함수들은 여러 엔드포인트에서 재사용될 수 있으며, HTTP 요청의 맥락(context)에 의존합니다. FastAPI의 **의존성 주입(Dependency Injection)** 시스템을 활용하기에 가장 적합한 위치입니다. 이렇게 분리하면 각 엔드포인트에서는 `Depends()`를 통해 간결하게 호출만 하면 됩니다.

#### 4. 핵심 비즈니스 규칙 (`extract_materiality_issues`, `calculate_confidence`)
*   **어디로?** `app/domain/` 디렉토리 아래의 파일들.
    *   `app/domain/materiality/analyzer.py` (또는 `materiality_rules.py`)
    *   관련 상수(`ESG_KEYWORDS`)는 `app/domain/materiality/constants.py`
*   **이유:** 이것이 바로 **도메인 로직**입니다. 이 로직은 FastAPI나 데이터베이스와 같은 외부 기술에 전혀 의존하지 않는 순수한 Python 함수여야 합니다. 이렇게 분리하면 도메인 로직을 독립적으로 테스트하고 재사용할 수 있으며, 비즈니스의 핵심 가치를 코드에서 명확하게 볼 수 있습니다.

#### 5. 복잡한 워크플로우 (`upload_and_process` 함수의 내부 로직)
*   **어디로?** `app/services/document_processing_service.py`
*   **이유:** 이 로직은 여러 단계를 조율하는 **서비스 계층(Service Layer)**의 역할입니다. (파일 저장 -> 문서 분석 -> AI 호출 -> 결과 병합 -> 비용 기록). 서비스 계층은 API 계층으로부터 요청을 받아 도메인 로직과 인프라(외부 서비스)를 사용하여 비즈니스 유스케이스를 완성합니다.

#### 6. 외부 서비스 연동 (`get_cost_manager`, `get_gemini_service`)
*   **어디로?** `app/infrastructure/clients/` 또는 `app/adapters/` 디렉토리.
    *   `app/infrastructure/clients/cost_manager_client.py`
    *   `app/infrastructure/clients/gemini_client.py`
*   **이유:** 이들은 외부 세계와의 통신을 담당하는 **인프라 계층(Infrastructure Layer)**입니다. 클래스로 래핑하여 구체적인 구현을 숨기고, 서비스 계층에서는 이 클라이언트들을 주입받아 사용합니다. 이렇게 하면 나중에 Gemini API가 다른 AI 서비스로 바뀌더라도 서비스 계층의 코드는 변경할 필요가 없어집니다.

#### 7. 실행 블록 (`if __name__ == "__main__":`)
*   **어디로?** **제거합니다.**
*   **이유:** 라이브러리나 프레임워크 코드는 직접 실행되지 않도록 설계하는 것이 좋습니다. 실제 애플리케이션 실행은 `uvicorn app.main:app`과 같은 명령어를 통해 이루어져야 합니다. 이는 Docker와 같은 컨테이너 환경이나 Gunicorn과 같은 프로덕션 서버와의 통합을 훨씬 깔끔하게 만듭니다.

### 요약: 리팩토링된 `main.py`의 역할

*   **조립자(Assembler):** 애플리케이션의 각 부분을 가져와 조립합니다.
*   **설정자(Configurator):** 전역 미들웨어와 같은 앱 전체에 적용되는 설정을 담당합니다.
*   **진입점(Entrypoint):** Uvicorn이 애플리케이션을 실행할 때 찾는 시작점입니다.

이러한 리팩토링을 통해 `main.py`는 매우 간결해지며, 나머지 코드들은 각자의 책임에 따라 명확하게 분리되어 훨씬 더 견고하고 확장 가능한 아키텍처의 기반을 마련하게 됩니다. 이제 다음 단계로 각 분리된 모듈들을 구체적으로 만들어 나갈 수 있습니다.