import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    APP_NAME: str = "ESG 이슈 풀 추출기"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 파일 처리 설정
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list = ["pdf", "png", "jpg", "jpeg"]
    UPLOAD_DIR: str = "temp_uploads"
    OUTPUT_DIR: str = "processed_docs"
    
    # API 제한 설정 (CTO 조언 반영)
    DAILY_API_LIMIT: int = 20  # 일일 API 호출 제한
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

# 전역 설정 인스턴스
settings = Settings()

# 디렉토리 생성
Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
Path(settings.OUTPUT_DIR).mkdir(exist_ok=True)

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