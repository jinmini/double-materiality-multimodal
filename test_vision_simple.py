"""
Gemini Vision API 테스트 스크립트
"""
import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from app.infrastructure.clients.gemini_client import GeminiClient
from app.infrastructure.clients.pdf_converter import PDFConverter
from app.infrastructure.clients.cost_manager_client import CostManagerClient

async def test_vision_api():
    """Vision API 기본 테스트"""
    print("🔍 Vision API 테스트 시작...")
    
    try:
        # 1. 클라이언트 초기화
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
            return
        
        cost_manager = CostManagerClient(
            daily_request_limit=20,
            daily_cost_limit=5.0,
            usage_file=Path("temp_usage.json")
        )
        gemini_client = GeminiClient(api_key, cost_manager)
        
        if not gemini_client.is_available():
            print("❌ Gemini 클라이언트를 초기화할 수 없습니다.")
            return
        
        print("✅ Gemini 클라이언트 초기화 완료")
        
        # 2. PDF 변환 테스트
        pdf_path = "komipo_issue.pdf"
        if not Path(pdf_path).exists():
            print(f"❌ 테스트 파일을 찾을 수 없습니다: {pdf_path}")
            return
        
        pdf_converter = PDFConverter(dpi=150)  # 낮은 DPI로 테스트
        print("🖼️ PDF → 이미지 변환 시작...")
        
        page_images = pdf_converter.convert_pdf_to_images(pdf_path)
        print(f"✅ {len(page_images)}페이지 변환 완료")
        
        # 3. 첫 페이지만 간단히 분석
        first_page = page_images[0]
        simple_prompt = """
        이 페이지에 어떤 내용이 있는지 간단히 설명해주세요.
        한 줄로 답변해주세요.
        """
        
        print("🔍 Vision API 호출 시작...")
        response = await gemini_client.analyze_image_with_text(
            image_base64=first_page["image_base64"],
            prompt=simple_prompt,
            model_name="gemini-2.0-flash-exp",
            max_tokens=100
        )
        
        print(f"✅ Vision API 응답: {response.get('content', '응답 없음')}")
        print("🎉 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vision_api()) 