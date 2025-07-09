# app/main.py

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 리팩토링된 모듈들을 임포트합니다.
from .core.config import settings
from app.core.logging_config import setup_logging
from app.dependencies.services import get_document_processing_service
from app.api.v1.api import api_router

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

# API 라우터 등록
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
def read_root():
    """API 서버의 상태와 버전을 확인합니다."""
    return {
        "message": f"Welcome to {settings.APP_NAME}!",
        "version": settings.APP_VERSION,
        "docs_url": "/docs"
    }

 