#!/usr/bin/env python3
"""
🧪 ESG 이슈 풀 추출기 API 테스트 스크립트 (v2.0)
개선된 범용 키워드 사전 테스트용
"""

import requests
import json
import os
import time
from pathlib import Path
from datetime import datetime

API_BASE_URL = "http://localhost:8000/api/v1"  # ✅ 수정: v1 경로 추가

def test_health_check():
    """헬스 체크 테스트"""
    print("🔍 헬스 체크 테스트...")
    try:
        response = requests.get(f"{API_BASE_URL}/health/")  # ✅ 수정: /health/ 경로
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
        response = requests.get(f"{API_BASE_URL}/health/usage")  # ✅ 수정: health/usage 경로
        print(f"✅ 상태: {response.status_code}")
        print(f"📊 응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"❌ 사용량 체크 실패: {e}")
        return False

def analyze_extraction_results(result: dict) -> None:
    """추출 결과 상세 분석"""
    print("\n🔬 **상세 분석 결과**")
    print("=" * 60)
    
    # 파일 정보
    file_info = result.get('file_info', {})
    print(f"📄 파일명: {file_info.get('filename', 'N/A')}")
    print(f"⏱️ 처리 시간: {file_info.get('processing_time', 'N/A')}")
    print(f"🔄 버전: {result.get('version', '1.0')}")
    print(f"🛠️ 추출 방법: {result.get('extraction_method', 'N/A')}")
    
    # 업종 분석 (v2.0 신기능)
    if 'industry_analysis' in result:
        industry = result['industry_analysis']
        print(f"\n🏭 **업종 분석**")
        print(f"  감지된 업종: {industry.get('detected_industry', 'N/A')}")
        print(f"  신뢰도: {industry.get('confidence', 'N/A')}")
        print(f"  사용된 키워드: {industry.get('keywords_used', 'N/A')}")
    
    # 문서 분석
    doc_analysis = result.get('document_analysis', {})
    print(f"\n📋 **문서 구조**")
    print(f"  총 요소: {doc_analysis.get('total_elements', 0)}개")
    print(f"  페이지 수: {doc_analysis.get('page_count', 0)}페이지")
    print(f"  제목 발견: {doc_analysis.get('titles_found', 0)}개")
    print(f"  표 발견: {doc_analysis.get('tables_found', 0)}개")
    
    # 신뢰도 분석 (v2.0 개선)
    if 'extraction_confidence' in result:
        confidence = result['extraction_confidence']
        print(f"\n🎯 **추출 신뢰도**")
        print(f"  전체 신뢰도: {confidence.get('level', 'N/A')} ({confidence.get('score', 0):.2f})")
        
        details = confidence.get('details', {})
        print(f"  키워드 매칭: {details.get('keyword_matching', 0):.2f}")
        print(f"  이슈명 정확성: {details.get('issue_name_accuracy', 0):.2f}")
        print(f"  중대성 컨텍스트: {details.get('materiality_context', 0):.2f}")
        print(f"  표 형식 인식: {details.get('table_format_recognition', 0):.2f}")
        print(f"  업종 가중치: {details.get('industry_weighting', 0):.2f}")
        print(f"  이슈 다양성: {details.get('issue_diversity', 0):.2f}")
    
    # 이슈 요약 (v2.0 신기능)
    if 'analysis_summary' in result:
        summary = result['analysis_summary']
        print(f"\n📈 **이슈 분석 요약**")
        print(f"  총 이슈 수: {summary.get('총_이슈_수', 0)}개")
        print(f"  높은 신뢰도 이슈: {summary.get('높은_신뢰도_이슈', 0)}개")
        print(f"  환경(E) 이슈: {summary.get('환경_이슈', 0)}개")
        print(f"  사회(S) 이슈: {summary.get('사회_이슈', 0)}개")
        print(f"  지배구조(G) 이슈: {summary.get('지배구조_이슈', 0)}개")
        print(f"  이슈 다양성 점수: {summary.get('이슈_다양성', 0):.2f}")
    
    # 추출된 이슈 상세 분석
    issues = result.get('materiality_issues', [])
    print(f"\n🎯 **추출된 이슈 목록** (총 {len(issues)}개)")
    print("=" * 60)
    
    # 신뢰도별 분류
    high_confidence = [i for i in issues if i.get('confidence', 0) >= 0.7]
    medium_confidence = [i for i in issues if 0.4 <= i.get('confidence', 0) < 0.7]
    low_confidence = [i for i in issues if i.get('confidence', 0) < 0.4]
    
    print(f"📊 신뢰도별 분포:")
    print(f"  높음 (≥0.7): {len(high_confidence)}개")
    print(f"  중간 (0.4-0.7): {len(medium_confidence)}개")
    print(f"  낮음 (<0.4): {len(low_confidence)}개")
    
    # 상위 5개 이슈 상세 표시
    print(f"\n🏆 **상위 5개 고신뢰도 이슈**")
    top_issues = sorted(issues, key=lambda x: x.get('confidence', 0), reverse=True)[:5]
    
    for i, issue in enumerate(top_issues, 1):
        issue_name = issue.get('issue_name', issue.get('content', '이름 없음'))
        category = issue.get('category', '미분류')
        confidence = issue.get('confidence', 0)
        method = issue.get('extraction_method', 'unknown')
        
        print(f"\n  {i}. 📋 {issue_name[:80]}...")
        print(f"     🏷️ 분류: {category}")
        print(f"     🎯 신뢰도: {confidence:.3f}")
        print(f"     🔧 추출 방법: {method}")
        
        if 'page_number' in issue:
            print(f"     📄 페이지: {issue['page_number']}")
        
        if 'matched_keywords' in issue:
            keywords = issue['matched_keywords'][:3]  # 상위 3개만
            print(f"     🔍 매칭 키워드: {', '.join(keywords)}")

def test_file_upload_enhanced(file_path: str):
    """개선된 파일 업로드 테스트"""
    print(f"\n📤 **파일 업로드 테스트**: {file_path}")
    print("=" * 60)
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return False
    
    try:
        # 업로드 시작 시간 기록
        upload_start = time.time()
        
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            response = requests.post(f"{API_BASE_URL}/documents/upload", files=files, timeout=300)  # 5분 타임아웃
        
        upload_time = time.time() - upload_start
        print(f"⏱️ 업로드 + 처리 시간: {upload_time:.2f}초")
        print(f"✅ HTTP 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # 상세 분석 실행
            analyze_extraction_results(result)
            
            # 결과를 타임스탬프와 함께 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"test_result_{timestamp}_{os.path.basename(file_path)}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 상세 결과가 {output_file}에 저장되었습니다.")
            
            return True
        else:
            print(f"❌ 업로드 실패: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏰ 요청 타임아웃 (5분 초과)")
        return False
    except Exception as e:
        print(f"❌ 파일 업로드 실패: {e}")
        return False

def test_comparison_analysis():
    """비교 분석 테스트 - 여러 파일 동시 테스트"""
    print(f"\n🔄 **비교 분석 테스트**")
    print("=" * 60)
    
    # temp_uploads 폴더의 PDF 파일들 확인
    temp_dir = Path("temp_uploads")
    if not temp_dir.exists():
        print("⚠️ temp_uploads 폴더가 없습니다.")
        return
    
    pdf_files = list(temp_dir.glob("*.pdf"))[:3]  # 처음 3개만 테스트
    
    if not pdf_files:
        print("⚠️ 테스트할 PDF 파일이 없습니다.")
        return
    
    print(f"📁 {len(pdf_files)}개 파일을 순차 테스트합니다...")
    
    results = []
    for pdf_file in pdf_files:
        print(f"\n{'='*20} {pdf_file.name} {'='*20}")
        success = test_file_upload_enhanced(str(pdf_file))
        results.append({"file": pdf_file.name, "success": success})
        time.sleep(2)  # 서버 부하 방지
    
    # 테스트 요약
    print(f"\n📊 **테스트 요약**")
    successful = len([r for r in results if r["success"]])
    print(f"성공: {successful}/{len(results)}개")
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {result['file']}")

def main():
    """메인 테스트 함수"""
    print("🧪 ESG 이슈 풀 추출기 API 테스트 v2.0")
    print("🚀 범용 키워드 사전 + 업종 자동 감지 테스트")
    print("=" * 80)
    
    # 서버 상태 확인
    if not test_health_check():
        print("❌ 서버가 실행되지 않았습니다. 먼저 'python run_server.py'를 실행하세요.")
        return
    
    # 사용량 확인
    test_usage_check()
    
    # 메인 파일 테스트 (한국중부발전 보고서)
    main_test_files = ["esg.pdf", "komipo_issue.pdf"]  
    
    for file_path in main_test_files:
        if os.path.exists(file_path):
            test_file_upload_enhanced(file_path)
        else:
            print(f"⚠️ 메인 테스트 파일이 없습니다: {file_path}")
    
    # 추가 비교 분석 (선택사항)
    print(f"\n❓ temp_uploads 폴더의 추가 파일들도 테스트하시겠습니까? (y/n): ", end="")
    if input().lower().startswith('y'):
        test_comparison_analysis()
    
    print("\n✅ 테스트 완료!")
    print("📖 더 많은 API 정보는 http://localhost:8000/docs에서 확인하세요.")
    print("📊 결과 파일들을 확인하여 개선 효과를 분석해보세요.")

if __name__ == "__main__":
    main() 