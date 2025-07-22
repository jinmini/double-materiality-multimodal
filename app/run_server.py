#!/usr/bin/env python3
"""
ESG 이슈 풀 추출기 서버 실행 스크립트
"""

import uvicorn
import sys
from pathlib import Path
from fastapi import FastAPI # <<--- FastAPI 임포트 추가

# 🚀 FastAPI 앱 객체를 main() 함수 바깥, 즉 파일의 최상위 레벨에 정의합니다.
app = FastAPI(
    title="ESG 이슈 풀 추출기",
    description="ESG 관련 이슈를 문서에서 추출하는 서비스",
    version="1.0.0",
)

# TODO: 여기에 실제 FastAPI 라우트(경로) 및 비즈니스 로직을 추가합니다.
# 예시:
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Server is running"}

# @app.post("/extract_esg_issues")
# async def extract_issues(payload: SomeInputModel):
#     # ... 이슈 추출 로직 ...
#     return {"issues": [...]}


def main():
    """서버 시작"""
    print("🚀 ESG 이슈 풀 추출기 서버 시작")
    print("=" * 50)
    print("📡 서버 주소: http://localhost:8000")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔍 헬스체크: http://localhost:8000/health")
    print("=" * 50)
    
    # 필요한 디렉토리 생성
    Path("temp_uploads").mkdir(exist_ok=True)
    Path("processed_docs").mkdir(exist_ok=True)
    
    try:
        uvicorn.run(
            "__main__:app",  # ✅ 변경: 'run_server:app' → '__main__:app'
                             # 현재 스크립트가 메인 모듈이므로 '__main__'을 사용
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n✅ 서버가 정상적으로 종료되었습니다.")
    except Exception as e:
        print(f"❌ 서버 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()