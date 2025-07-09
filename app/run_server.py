#!/usr/bin/env python3
"""
ESG 이슈 풀 추출기 서버 실행 스크립트
"""

import uvicorn
import sys
from pathlib import Path

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
            "app.main:app",  # ✅ 변경: main:app → app.main:app
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