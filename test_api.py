#!/usr/bin/env python3
"""
ESG 이슈 풀 추출기 API 테스트 스크립트
"""

import requests
import json
import os
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def test_health_check():
    """헬스 체크 테스트"""
    print("🔍 헬스 체크 테스트...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"✅ 상태: {response.status_code}")
        print(f"📊 응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"❌ 헬스 체크 실패: {e}")
        return False

def test_usage_check():
    """사용량 체크 테스트"""
    print("\n📊 사용량 체크 테스트...")
    try:
        response = requests.get(f"{API_BASE_URL}/usage")
        print(f"✅ 상태: {response.status_code}")
        print(f"📊 응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"❌ 사용량 체크 실패: {e}")
        return False

def test_file_upload(file_path: str):
    """파일 업로드 테스트"""
    print(f"\n📤 파일 업로드 테스트: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return False
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        print(f"✅ 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("📋 추출 결과:")
            print(f"  - 파일명: {result['file_info']['filename']}")
            print(f"  - 처리 시간: {result['file_info']['processed_at']}")
            print(f"  - 전체 요소: {result['document_analysis']['total_elements']}개")
            print(f"  - 페이지 수: {result['document_analysis']['page_count']}페이지")
            print(f"  - 추출된 이슈: {len(result['materiality_issues'])}개")
            print(f"  - 추출 방법: {result.get('extraction_method', 'unstructured_only')}")
            print(f"  - 신뢰도: {result['extraction_confidence']['level']} ({result['extraction_confidence']['score']})")
            
            # Gemini 메타데이터 표시
            if result.get('gemini_metadata'):
                gemini_meta = result['gemini_metadata']
                print(f"  - Gemini 모델: {gemini_meta.get('model', 'N/A')}")
                print(f"  - 토큰 사용: {gemini_meta.get('tokens_used', 'N/A')}개")
                print(f"  - 응답 시간: {gemini_meta.get('response_time', 0):.2f}초")
            
            # 추출된 이슈 미리보기
            print("\n🎯 추출된 주요 이슈 (상위 3개):")
            for i, issue in enumerate(result['materiality_issues'][:3], 1):
                issue_name = issue.get('issue_name', issue.get('content', '이름 없음'))
                category = issue.get('category', '미분류')
                confidence = issue.get('confidence', 0)
                method = issue.get('extraction_method', 'unknown')
                
                print(f"  {i}. [{category}] {issue_name[:100]}...")
                print(f"     신뢰도: {confidence}, 방법: {method}")
                
                if 'page_number' in issue:
                    print(f"     페이지: {issue['page_number']}")
            
            # 결과를 파일로 저장
            output_file = f"test_result_{os.path.basename(file_path)}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 상세 결과가 {output_file}에 저장되었습니다.")
            
            return True
        else:
            print(f"❌ 업로드 실패: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 파일 업로드 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🧪 ESG 이슈 풀 추출기 API 테스트 시작")
    print("=" * 60)
    
    # 서버 상태 확인
    if not test_health_check():
        print("❌ 서버가 실행되지 않았습니다. 먼저 'python run_server.py'를 실행하세요.")
        return
    
    # 사용량 확인
    test_usage_check()
    
    # 파일 업로드 테스트
    test_files = ["esg.pdf"]  # 기존 파일 활용
    
    for file_path in test_files:
        if os.path.exists(file_path):
            test_file_upload(file_path)
        else:
            print(f"⚠️ 테스트 파일이 없습니다: {file_path}")
    
    print("\n✅ 테스트 완료!")
    print("📖 더 많은 API 정보는 http://localhost:8000/docs에서 확인하세요.")

if __name__ == "__main__":
    main() 