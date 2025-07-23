# app/core/logging_config.py

import logging
import sys
from typing import Optional
from pathlib import Path

from app.core.config import settings

def setup_logging():
    """
    환경별 최적화된 로깅 시스템을 설정합니다.
    
    - 개발 환경 (DEBUG=True): coloredlogs + 파일 로깅
    - 운영 환경 (DEBUG=False): JSON 구조화 로깅 + stdout
    """
    
    # 기존 핸들러 정리
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 로그 레벨 설정
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    if settings.DEBUG:
        _setup_development_logging(log_level)
    else:
        _setup_production_logging(log_level)
    
    # 애플리케이션 시작 로그
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 로깅 시스템 초기화 완료 - 모드: {'개발' if settings.DEBUG else '운영'}")

def _setup_development_logging(log_level: int):
    """개발 환경용 컬러 로깅 설정"""
    try:
        import coloredlogs
        
        # 컬러 로깅 설정
        coloredlogs.install(
            level=log_level,
            fmt='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level_styles={
                'debug': {'color': 'cyan'},
                'info': {'color': 'green'},
                'warning': {'color': 'yellow', 'bold': True},
                'error': {'color': 'red', 'bold': True},
                'critical': {'color': 'red', 'bold': True, 'background': 'yellow'},
            },
            field_styles={
                'asctime': {'color': 'blue'},
                'levelname': {'color': 'black', 'bold': True},
                'name': {'color': 'magenta'},
            }
        )
        
        # 파일 핸들러 추가 (개발 시에도 파일에 로그 저장)
        file_handler = _create_file_handler(log_level)
        if file_handler:
            logging.getLogger().addHandler(file_handler)
            
    except ImportError:
        # coloredlogs가 설치되지 않은 경우 기본 로깅 사용
        _setup_basic_logging(log_level)

def _setup_production_logging(log_level: int):
    """운영 환경용 JSON 구조화 로깅 설정"""
    try:
        from pythonjsonlogger import jsonlogger
        
        # JSON 포맷터 생성
        json_formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(pathname)s %(lineno)d %(funcName)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        
        # 표준 출력 핸들러 (컨테이너 환경 최적화)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(log_level)
        stdout_handler.setFormatter(json_formatter)
        
        # 에러 로그는 stderr로 분리
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR)
        stderr_handler.setFormatter(json_formatter)
        
        # 핸들러 등록
        root_logger = logging.getLogger()
        root_logger.addHandler(stdout_handler)
        root_logger.addHandler(stderr_handler)
        
    except ImportError:
        # python-json-logger가 설치되지 않은 경우 기본 로깅 사용
        _setup_basic_logging(log_level)

def _setup_basic_logging(log_level: int):
    """기본 로깅 설정 (폴백)"""
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)8s] %(name)s (%(pathname)s:%(lineno)d): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # 파일 핸들러 (개발 환경에서만)
    handlers = [console_handler]
    if settings.DEBUG:
        file_handler = _create_file_handler(log_level)
        if file_handler:
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
    
    # 핸들러 등록
    root_logger = logging.getLogger()
    for handler in handlers:
        root_logger.addHandler(handler)

def _create_file_handler(log_level: int) -> Optional[logging.FileHandler]:
    """파일 핸들러 생성 (안전한 파일 경로 처리)"""
    try:
        log_file_path = Path(settings.LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_file_path, 
            encoding='utf-8',
            mode='a'  # append 모드
        )
        file_handler.setLevel(log_level)
        return file_handler
        
    except (OSError, PermissionError) as e:
        # 파일 생성 실패 시 경고 후 None 반환
        print(f"⚠️  로그 파일 생성 실패: {e}", file=sys.stderr)
        return None

def get_logger(name: str = None) -> logging.Logger:
    """
    애플리케이션 전용 로거 생성 헬퍼 함수
    
    Args:
        name: 로거 이름 (보통 __name__ 사용)
    
    Returns:
        설정된 로거 인스턴스
    """
    return logging.getLogger(name)

# 특정 라이브러리의 로그 레벨 조정 (노이즈 감소)
def configure_third_party_loggers():
    """서드파티 라이브러리의 로그 레벨을 조정하여 노이즈를 줄입니다."""
    
    # 자주 로그를 남기는 라이브러리들의 레벨 조정
    noisy_loggers = [
        'urllib3.connectionpool',
        'httpx',
        'httpcore',
        'unstructured',
        'PIL',
        'google.auth',
        'google.generativeai'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
        
    # 운영 환경에서는 더 엄격하게
    if not settings.DEBUG:
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING) 