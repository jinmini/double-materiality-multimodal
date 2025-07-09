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
    DEBUG: bool = True  # 개발 환경을 위해 True로 변경
    
    # CORS 설정 (프로덕션에서는 특정 도메인을 지정해야 합니다)
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # 파일 처리 설정
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "png", "jpg", "jpeg"]
    UPLOAD_DIR: Path = Path("temp_uploads")
    OUTPUT_DIR: Path = Path("processed_docs")
    
    # API 제한 설정
    DAILY_API_LIMIT: int = 20
    DAILY_COST_LIMIT: float = 5.0  # 달러
    MAX_REQUESTS_PER_MINUTE: int = 5
    
    # Google Gemini 설정
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"  # Gemini 2.0 Flash 모델로 통일
    GEMINI_MAX_TOKENS: int = 2000
    
    # 로깅 설정
    LOG_LEVEL: str = "DEBUG"  # 상세한 디버깅을 위해 DEBUG로 변경
    LOG_FILE: str = "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 전역 설정 인스턴스 생성
settings = Settings() 