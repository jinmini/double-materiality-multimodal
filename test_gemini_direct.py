#!/usr/bin/env python3
"""
Gemini API 직접 테스트
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini_api():
    # .env 파일 로드
    load_dotenv()
    
    api_key = os.getenv('GEMINI_API_KEY')
    print(f"🔑 API Key: {api_key[:20]}..." if api_key else "❌ API Key 없음")
    
    if not api_key:
        print("❌ GEMINI_API_KEY가 설정되지 않았습니다!")
        return
    
    try:
        # Gemini 설정
        genai.configure(api_key=api_key)
        
        # 간단한 텍스트 테스트
        print("🔍 Gemini 1.5 Flash 테스트...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello! Can you respond with 'API working'?")
        print(f"✅ 응답: {response.text}")
        
        # 2.0 Flash 테스트
        print("🔍 Gemini 2.0 Flash 테스트...")
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Hello! Can you respond with 'API working'?")
        print(f"✅ 응답: {response.text}")
        
    except Exception as e:
        print(f"❌ Gemini API 오류: {str(e)}")
        print("💡 가능한 원인:")
        print("   - API 키가 유효하지 않음")
        print("   - 네트워크 연결 문제")
        print("   - Gemini 2.0 Flash 모델 접근 권한 없음")

if __name__ == "__main__":
    test_gemini_api() 