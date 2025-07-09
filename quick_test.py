#!/usr/bin/env python3
"""
komipo_issue.pdf 빠른 테스트 스크립트
"""

import requests
import json
import time
from pathlib import Path

def test_komipo():
    print("🧪 komipo_issue.pdf 범용 키워드 사전 테스트")
    print("=" * 60)
    
    # 1. 헬스체크
    print("🔍 서버 헬스체크...")
    try:
        health = requests.get("http://localhost:8000/api/v1/health/")
        print(f"✅ 서버 상태: {health.status_code}")
        
        if health.status_code != 200:
            print("❌ 서버가 실행되지 않았습니다.")
            return
            
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return
    
    # 2. 파일 업로드 테스트
    file_path = "komipo_issue.pdf"
    if not Path(file_path).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return
    
    print(f"📤 파일 업로드 시작: {file_path}")
    start_time = time.time()
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path, f, 'application/pdf')}
            response = requests.post(
                "http://localhost:8000/api/v1/documents/upload", 
                files=files, 
                timeout=300
            )
        
        upload_time = time.time() - start_time
        print(f"⏱️ 처리 시간: {upload_time:.2f}초")
        print(f"📊 HTTP 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 업로드 및 처리 성공!")
            
            # 결과 분석
            print("\n🔬 분석 결과:")
            print("-" * 40)
            
            # 업종 분석
            industry_info = result.get("industry_analysis", {})
            print(f"🏭 감지된 업종: {industry_info.get('detected_industry', 'N/A')}")
            print(f"📊 업종 신뢰도: {industry_info.get('confidence', 'N/A')}")
            print(f"🔧 사용된 키워드: {industry_info.get('keywords_used', 'N/A')}")
            
            # 추출 결과
            issues = result.get("materiality_issues", [])
            confidence = result.get("extraction_confidence", {})
            summary = result.get("analysis_summary", {})
            
            print(f"\n📈 추출 통계:")
            print(f"  총 이슈 수: {len(issues)}개")
            print(f"  높은 신뢰도 이슈: {summary.get('높은_신뢰도_이슈', 0)}개")
            print(f"  환경(E) 이슈: {summary.get('환경_이슈', 0)}개")
            print(f"  사회(S) 이슈: {summary.get('사회_이슈', 0)}개")
            print(f"  지배구조(G) 이슈: {summary.get('지배구조_이슈', 0)}개")
            
            print(f"\n🎯 전체 신뢰도: {confidence.get('level', 'N/A')} ({confidence.get('score', 0):.2f})")
            
            # 상위 5개 이슈 표시
            print(f"\n🏆 상위 5개 고신뢰도 이슈:")
            print("-" * 60)
            
            for i, issue in enumerate(issues[:5], 1):
                name = issue.get('issue_name', '이름없음')
                category = issue.get('category', '미분류')
                conf = issue.get('confidence', 0)
                industry = issue.get('industry', 'N/A')
                keywords = issue.get('matched_keywords', [])[:2]
                
                print(f"{i}. [{category}] {name}")
                print(f"   🎯 신뢰도: {conf:.3f} | 🏭 업종: {industry}")
                print(f"   🔍 매칭 키워드: {', '.join(keywords) if keywords else '없음'}")
                print()
            
            # 결과 저장
            output_file = f"test_result_komipo_{int(time.time())}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"💾 상세 결과가 {output_file}에 저장되었습니다.")
            
        else:
            print(f"❌ 업로드 실패 ({response.status_code})")
            print(f"오류 내용: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ 요청 타임아웃 (5분 초과)")
    except Exception as e:
        print(f"❌ 처리 중 오류: {e}")

if __name__ == "__main__":
    test_komipo() 