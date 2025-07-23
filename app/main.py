# app/main.py

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime

# 리팩토링된 모듈들을 임포트합니다.
from .core.config import settings
from app.core.logging_config import setup_logging, configure_third_party_loggers, get_logger
from app.dependencies.services import get_document_processing_service
from app.api.v1.api import api_router
from app.schemas.responses import ErrorResponse

# 로깅 설정
setup_logging()
configure_third_party_loggers()  # 서드파티 라이브러리 로그 노이즈 감소
logger = get_logger(__name__)

# 애플리케이션 시작/종료 시 실행될 로직 (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    logger.info(f"Starting up {settings.APP_NAME}...")
    
    # 🔧 API 키 디버깅
    if settings.GEMINI_API_KEY:
        logger.info(f"✅ Gemini API 키 로드됨: {settings.GEMINI_API_KEY[:20]}...")
    else:
        logger.error("❌ Gemini API 키가 없습니다!")
        logger.info("💡 .env 파일 확인: GEMINI_API_KEY=...")
    
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

# 전역 예외 핸들러 등록
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTPException에 대한 전역 핸들러
    모든 HTTPException을 일관된 ErrorResponse 형태로 반환합니다.
    """
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail} - URL: {request.url}")
    
    error_response = ErrorResponse(
        detail=exc.detail,
        error_code=f"HTTP_{exc.status_code}",
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    요청 유효성 검사 오류에 대한 전역 핸들러
    Pydantic 모델 검증 실패 시 일관된 형태로 반환합니다.
    """
    error_details = []
    for error in exc.errors():
        location = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(f"{location}: {error['msg']}")
    
    detail = f"입력 데이터 검증 실패: {'; '.join(error_details)}"
    logger.error(f"Validation Error: {detail} - URL: {request.url}")
    
    error_response = ErrorResponse(
        detail=detail,
        error_code="VALIDATION_ERROR",
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    예상치 못한 서버 오류에 대한 전역 핸들러
    모든 처리되지 않은 예외를 안전하게 처리합니다.
    """
    logger.error(f"Unexpected Error: {str(exc)} - URL: {request.url}", exc_info=True)
    
    # 프로덕션에서는 상세한 오류 정보를 숨깁니다
    detail = str(exc) if settings.DEBUG else "서버 내부 오류가 발생했습니다"
    
    error_response = ErrorResponse(
        detail=detail,
        error_code="INTERNAL_SERVER_ERROR",
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
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

 