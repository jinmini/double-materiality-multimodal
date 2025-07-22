#!/usr/bin/env python3
"""
Gemini API 연결 테스트 스크립트
"""
import os
import sys
import asyncio
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_key_validity():
    """API 키 유효성 확인"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        return False
    
    if len(api_key) < 20:
        print("❌ GEMINI_API_KEY가 너무 짧습니다. 올바른 키인지 확인하세요.")
        return False
    
    print(f"✅ API 키 형식 확인: {api_key[:10]}...")
    return True

def test_google_generativeai_import():
    """google-generativeai 라이브러리 임포트 테스트"""
    try:
        import google.generativeai as genai
        print("✅ google-generativeai 라이브러리 임포트 성공")
        return True
    except ImportError as e:
        print(f"❌ google-generativeai 라이브러리 임포트 실패: {e}")
        print("해결방법: pip install google-generativeai")
        return False

def test_gemini_configuration():
    """Gemini 설정 테스트"""
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        
        # API 키 설정
        genai.configure(api_key=api_key)
        print("✅ Gemini API 설정 완료")
        return True
    except Exception as e:
        print(f"❌ Gemini API 설정 실패: {e}")
        return False

def test_model_listing():
    """사용 가능한 모델 목록 확인"""
    try:
        import google.generativeai as genai
        
        print("📋 Gemini 모델 목록 확인 중...")
        models = list(genai.list_models())
        
        if not models:
            print("❌ 사용 가능한 모델이 없습니다. API 키를 확인하세요.")
            return False
        
        print(f"✅ 총 {len(models)}개 모델 사용 가능:")
        for model in models[:5]:  # 처음 5개만 표시
            print(f"  - {model.name}")
            if "vision" in model.name.lower():
                print(f"    📷 Vision 모델 발견!")
        
        return True
    except Exception as e:
        print(f"❌ 모델 목록 조회 실패: {e}")
        error_msg = str(e).lower()
        if "403" in error_msg or "unauthorized" in error_msg:
            print("🔑 API 키 권한 문제일 가능성이 높습니다.")
        elif "429" in error_msg:
            print("⏰ API 요청 한도 초과. 잠시 후 다시 시도하세요.")
        return False

async def test_simple_text_generation():
    """간단한 텍스트 생성 테스트"""
    try:
        import google.generativeai as genai
        
        print("🧪 간단한 텍스트 생성 테스트...")
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # 짧은 타임아웃으로 테스트
        start_time = asyncio.get_event_loop().time()
        
        # 비동기 래퍼
        async def generate_async():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                lambda: model.generate_content("Hello, respond with just 'Hi'")
            )
        
        # 10초 타임아웃
        response = await asyncio.wait_for(generate_async(), timeout=10.0)
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        if response.text:
            print(f"✅ 텍스트 생성 성공: '{response.text.strip()}' ({elapsed:.2f}초)")
            return True
        else:
            print("❌ 응답이 비어있습니다.")
            return False
            
    except asyncio.TimeoutError:
        print("❌ 텍스트 생성 타임아웃 (10초 초과)")
        return False
    except Exception as e:
        print(f"❌ 텍스트 생성 실패: {e}")
        return False

async def test_vision_model():
    """Vision 모델 사용 가능성 테스트"""
    try:
        import google.generativeai as genai
        import base64
        from PIL import Image
        import io
        
        print("👁️ Vision 모델 테스트...")
        
        # 1x1 픽셀 PNG 이미지 생성 (최소 테스트용)
        img = Image.new('RGB', (1, 1), color='white')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_data = img_buffer.getvalue()
        
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        image_part = {
            "mime_type": "image/png",
            "data": img_data
        }
        
        # 매우 짧은 타임아웃으로 연결 테스트
        async def vision_test():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: model.generate_content([
                    "What color is this image? Answer in one word.",
                    image_part
                ])
            )
        
        response = await asyncio.wait_for(vision_test(), timeout=15.0)
        
        if response.text:
            print(f"✅ Vision API 연결 성공: '{response.text.strip()}'")
            return True
        else:
            print("❌ Vision API 응답이 비어있습니다.")
            return False
            
    except asyncio.TimeoutError:
        print("❌ Vision API 타임아웃 (15초 초과)")
        return False
    except Exception as e:
        print(f"❌ Vision API 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 실행"""
    print("🔍 Gemini API 연결 진단을 시작합니다...\n")
    
    tests = [
        ("API 키 유효성", test_api_key_validity),
        ("라이브러리 임포트", test_google_generativeai_import),
        ("Gemini 설정", test_gemini_configuration),
        ("모델 목록 조회", test_model_listing),
        ("텍스트 생성", test_simple_text_generation),
        ("Vision API", test_vision_model)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name} 테스트")
        print('='*50)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 테스트 중 예외 발생: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print(f"\n{'='*50}")
    print("📊 테스트 결과 요약")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n총 {len(results)}개 테스트 중 {passed}개 통과 ({passed/len(results)*100:.1f}%)")
    
    if passed == len(results):
        print("\n🎉 모든 테스트 통과! Gemini API가 정상적으로 설정되었습니다.")
    elif passed >= 4:
        print("\n⚠️ 기본 기능은 작동하지만 일부 문제가 있습니다.")
    else:
        print("\n🚨 심각한 설정 문제가 있습니다. API 키와 환경을 다시 확인하세요.")

if __name__ == "__main__":
    asyncio.run(main())