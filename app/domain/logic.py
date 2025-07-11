# app/domain/logic.py

from typing import Dict, Any, List, Optional, Tuple
from app.domain.constants import (
    UNIVERSAL_ESG_ISSUES, 
    MATERIALITY_KEYWORDS, 
    AUTO_INDUSTRY_DETECTION,
    INDUSTRY_SPECIFIC_KEYWORDS,
    ISSUE_PRIORITY_WEIGHTS,
    # 하위 호환성
    ESG_KEYWORDS, 
    ISSUE_KEYWORDS
)

# ==============================================================================
# 🏭 업종 자동 감지 함수
# ==============================================================================

def detect_industry_from_text(text: str) -> str:
    """
    문서 내용을 분석하여 업종을 자동으로 감지합니다.
    
    Args:
        text: 분석할 텍스트 (전체 문서 내용 또는 일부)
        
    Returns:
        감지된 업종명 (예: "전력", "제조", "금융" 등) 또는 "기타"
    """
    industry_scores = {}
    
    # 각 업종별 키워드 점수 계산
    for industry, keywords in AUTO_INDUSTRY_DETECTION.items():
        score = 0
        for keyword in keywords:
            # 키워드 빈도에 따른 점수 계산
            count = text.count(keyword)
            if count > 0:
                # 🔥 개선: 키워드별 가중치 적용
                if "발전" in keyword or "회사" in keyword or "한국" in keyword:
                    # 회사명이나 핵심 업종 키워드에 높은 가중치
                    score += min(count * 5, 25)  # 최대 25점
                elif len(keyword) >= 4:
                    # 구체적인 키워드 (4글자 이상)에 중간 가중치
                    score += min(count * 3, 15)  # 최대 15점
                else:
                    # 일반 키워드에 기본 가중치
                    score += min(count * 2, 10)  # 최대 10점
        
        industry_scores[industry] = score
    
    # 가장 높은 점수의 업종 반환
    if industry_scores and max(industry_scores.values()) > 0:
        detected_industry = max(industry_scores, key=industry_scores.get)
        print(f"🏭 감지된 업종: {detected_industry} (점수: {industry_scores[detected_industry]})")
        
        # 🔥 개선: 디버깅을 위한 상위 3개 업종 점수 출력
        sorted_industries = sorted(industry_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"🏭 업종별 점수: {sorted_industries}")
        
        return detected_industry
    
    return "기타"

# ==============================================================================
# 🎯 동적 키워드 매칭 함수
# ==============================================================================

def get_dynamic_keywords_for_issue(issue_name: str, industry: str = "기타") -> List[str]:
    """
    이슈와 업종에 맞는 동적 키워드 목록을 생성합니다.
    
    Args:
        issue_name: ESG 이슈명
        industry: 업종 (자동 감지된 결과)
        
    Returns:
        해당 이슈에 적합한 키워드 목록
    """
    keywords = []
    
    # 1. UNIVERSAL_ESG_ISSUES에서 기본 키워드 추출
    for category, issues in UNIVERSAL_ESG_ISSUES.items():
        if issue_name in issues:
            issue_data = issues[issue_name]
            # Core 키워드 추가
            keywords.extend(issue_data["core_keywords"])
            # Advanced 키워드 추가
            keywords.extend(issue_data["advanced_keywords"])
            
            # 2. 업종별 특화 키워드 추가
            if industry in issue_data["industry_variants"]:
                keywords.extend(issue_data["industry_variants"][industry])
            break
    
    # 3. 업종별 비즈니스 키워드 추가 (관련성이 있는 경우)
    if industry in INDUSTRY_SPECIFIC_KEYWORDS:
        industry_data = INDUSTRY_SPECIFIC_KEYWORDS[industry]
        # 특정 이슈와 관련성이 높은 비즈니스 키워드 선별 추가
        if issue_name in ["고객 및 제품책임", "공급망 관리"]:
            keywords.extend(industry_data["business_keywords"])
    
    # 중복 제거 및 반환
    return list(set(keywords))

# ==============================================================================
# 📊 개선된 중대성 이슈 추출 로직
# ==============================================================================

def extract_materiality_issues_enhanced(elements: List[Any]) -> Dict[str, Any]:
    """
    범용 키워드 사전을 활용한 개선된 중대성 이슈 추출 함수.
    업종 자동 감지와 동적 키워드 매칭을 지원합니다.
    """
    # 1. 전체 텍스트 수집 (업종 감지용)
    full_text = " ".join([getattr(element, 'text', str(element)) for element in elements])
    
    # 2. 업종 자동 감지
    detected_industry = detect_industry_from_text(full_text)
    
    # 3. 이슈 추출
    issues = []
    issue_confidence_scores = {}
    
    for element in elements:
        element_text = getattr(element, 'text', str(element))
        
        # 🔥 개선: 필터링 조건 완화 - ESG 관련 키워드만 있어도 처리
        esg_related = False
        
        # 중대성 키워드 체크
        if any(keyword in element_text for keyword in MATERIALITY_KEYWORDS):
            esg_related = True
        
        # ESG 기본 키워드 체크 (환경, 사회, 지배구조)
        basic_esg_keywords = ["환경", "사회", "지배구조", "ESG", "지속가능", "sustainability"]
        if any(keyword in element_text for keyword in basic_esg_keywords):
            esg_related = True
        
        # 텍스트가 충분히 길고 의미가 있는 경우 (20자 이상)
        if len(element_text.strip()) >= 20:
            esg_related = True
        
        if not esg_related:
            continue

        # 각 ESG 이슈별로 매칭 검사
        for category, category_issues in UNIVERSAL_ESG_ISSUES.items():
            for issue_name in category_issues.keys():
                # 동적 키워드 가져오기
                dynamic_keywords = get_dynamic_keywords_for_issue(issue_name, detected_industry)
                
                # 키워드 매칭 점수 계산
                matched_keywords = [kw for kw in dynamic_keywords if kw in element_text]
                
                if matched_keywords:
                    # 신뢰도 계산
                    confidence = calculate_enhanced_confidence(
                        element_text, issue_name, matched_keywords, 
                        dynamic_keywords, detected_industry
                    )
                    
                    # 페이지 정보 추출
                    page_number = getattr(element.metadata, 'page_number', None) if hasattr(element, 'metadata') else None
                    
                    issue = {
                        "issue_id": len(issues) + 1,
                        "category": category.split("(")[0],  # "환경(E)" -> "환경"
                        "issue_name": issue_name,
                        "content": element_text[:500],
                        "matched_keywords": matched_keywords,
                        "page_number": page_number,
                        "element_type": type(element).__name__,
                        "confidence": confidence,
                        "industry": detected_industry
                    }
                    
                    issues.append(issue)
                    
                    # 이슈별 최고 신뢰도 추적
                    if issue_name not in issue_confidence_scores or confidence > issue_confidence_scores[issue_name]:
                        issue_confidence_scores[issue_name] = confidence

    # 4. 중복 제거 및 정렬
    unique_issues = remove_duplicate_issues(issues)
    unique_issues.sort(key=lambda x: x["confidence"], reverse=True)
    
    # 5. 업종별 우선순위 적용
    prioritized_issues = apply_industry_priority(unique_issues, detected_industry)
    
    # 6. 결과 구성
    result = {
        "detected_industry": detected_industry,
        "total_issues_found": len(prioritized_issues),
        "issues": prioritized_issues[:20],  # 상위 20개
        "overall_confidence": calculate_overall_confidence_enhanced(
            prioritized_issues, issue_confidence_scores, detected_industry
        ),
        "industry_priority_applied": True
    }
    
    return result

def calculate_enhanced_confidence(
    text: str, 
    issue_name: str, 
    matched_keywords: List[str], 
    all_keywords: List[str], 
    industry: str
) -> float:
    """개선된 신뢰도 계산 함수"""
    confidence = 0.0
    
    # 1. 기본 키워드 매칭 점수 (0~0.5)
    keyword_ratio = len(matched_keywords) / len(all_keywords) if all_keywords else 0
    confidence += keyword_ratio * 0.5
    
    # 2. 정확한 이슈명 매칭 보너스 (0.3)
    if issue_name in text:
        confidence += 0.3
    
    # 3. 중대성 컨텍스트 보너스 (0.2)
    materiality_indicators = ["중대성", "materiality", "핵심이슈", "우선순위"]
    if any(indicator in text for indicator in materiality_indicators):
        confidence += 0.2
    
    # 4. 표/매트릭스 형식 보너스 (0.15)
    table_indicators = ["│", "─", "표", "매트릭스", "순위", "높음", "보통", "낮음"]
    if any(indicator in text for indicator in table_indicators):
        confidence += 0.15
    
    # 5. 업종별 가중치 적용 (0~0.1)
    if industry in ISSUE_PRIORITY_WEIGHTS:
        issue_weight = ISSUE_PRIORITY_WEIGHTS[industry].get(issue_name, 0)
        confidence += issue_weight * 0.1
    
    # 6. 고품질 키워드 보너스 (0.1)
    high_quality_keywords = ["평가", "관리", "전략", "개선", "목표", "성과"]
    if any(kw in matched_keywords for kw in high_quality_keywords):
        confidence += 0.1
    
    return min(confidence, 1.0)

def remove_duplicate_issues(issues: List[Dict]) -> List[Dict]:
    """중복 이슈 제거"""
    seen_issues = {}
    unique_issues = []
    
    for issue in issues:
        key = f"{issue['issue_name']}_{issue['page_number']}"
        
        if key not in seen_issues or issue['confidence'] > seen_issues[key]['confidence']:
            seen_issues[key] = issue
    
    return list(seen_issues.values())

def apply_industry_priority(issues: List[Dict], industry: str) -> List[Dict]:
    """업종별 우선순위 가중치 적용"""
    if industry not in ISSUE_PRIORITY_WEIGHTS:
        return issues
    
    weights = ISSUE_PRIORITY_WEIGHTS[industry]
    
    for issue in issues:
        issue_name = issue['issue_name']
        if issue_name in weights:
            # 기존 신뢰도에 업종별 가중치를 곱하여 최종 점수 계산
            priority_weight = weights[issue_name]
            issue['priority_score'] = issue['confidence'] * (1 + priority_weight)
            issue['industry_weight'] = priority_weight
        else:
            issue['priority_score'] = issue['confidence'] * 1.1  # 기타 이슈는 약간의 보너스만
            issue['industry_weight'] = 0.1
    
    # 우선순위 점수로 재정렬
    issues.sort(key=lambda x: x['priority_score'], reverse=True)
    return issues

def calculate_overall_confidence_enhanced(
    issues: List[Dict], 
    issue_scores: Dict[str, float], 
    industry: str
) -> Dict[str, Any]:
    """개선된 전체 신뢰도 계산"""
    if not issues:
        return {
            "score": 0.0, 
            "level": "낮음", 
            "reason": "이슈를 찾을 수 없음",
            "industry": industry
        }
    
    # 기본 평균 신뢰도
    avg_confidence = sum(issue["confidence"] for issue in issues) / len(issues)
    
    # 업종 감지 보너스
    industry_bonus = 0.1 if industry != "기타" else 0
    
    # 이슈 다양성 보너스 (더 많은 이슈 카테고리를 발견할수록 좋음)
    unique_categories = len(set(issue["category"] for issue in issues))
    diversity_bonus = min(unique_categories * 0.05, 0.15)
    
    # 고신뢰도 이슈 비율
    high_confidence_issues = len([i for i in issues if i["confidence"] > 0.7])
    quality_bonus = (high_confidence_issues / len(issues)) * 0.1
    
    final_score = min(1.0, avg_confidence + industry_bonus + diversity_bonus + quality_bonus)
    
    # 신뢰도 레벨 결정
    if final_score >= 0.8:
        level = "높음"
    elif final_score >= 0.6:
        level = "중간"
    else:
        level = "낮음"
    
    return {
        "score": round(final_score, 2),
        "level": level,
        "issues_found": len(issues),
        "industry": industry,
        "high_confidence_count": high_confidence_issues,
        "category_diversity": unique_categories,
        "analysis_details": {
            "base_confidence": round(avg_confidence, 2),
            "industry_bonus": industry_bonus,
            "diversity_bonus": round(diversity_bonus, 2),
            "quality_bonus": round(quality_bonus, 2)
        }
    }

# ==============================================================================
# 🔄 하위 호환성 함수들 (기존 코드와의 호환성 유지)
# ==============================================================================

def extract_materiality_issues(elements: List[Any]) -> List[Dict[str, Any]]:
    """
    기존 함수와의 호환성을 위한 래퍼 함수.
    새로운 enhanced 버전을 호출하되 기존 형식으로 반환합니다.
    """
    enhanced_result = extract_materiality_issues_enhanced(elements)
    
    # 기존 형식으로 변환
    issues = enhanced_result["issues"]
    for i, issue in enumerate(issues):
        issue["issue_id"] = i + 1
    
    return issues

def calculate_issue_confidence(text: str, issue_name: str) -> float:
    """기존 함수와의 호환성 유지"""
    # 기본 키워드 가져오기
    keywords = ISSUE_KEYWORDS.get(issue_name, [])
    if not keywords:
        return 0.0
    
    confidence = 0.0
    
    # 정확한 이슈명 매칭
    if issue_name in text:
        confidence += 0.8
    
    # 키워드 매칭
    matched_keywords = sum(1 for keyword in keywords if keyword in text)
    confidence += (matched_keywords / len(keywords)) * 0.5
    
    # 중대성 컨텍스트
    if any(word in text for word in ["중대성", "materiality", "핵심이슈"]):
        confidence += 0.3
        
    # 표/매트릭스 컨텍스트
    if any(indicator in text for indicator in ["높음", "보통", "낮음", "│", "─"]):
        confidence += 0.2
        
    return min(confidence, 1.0)

def calculate_overall_confidence(issues: List[Dict], structure: Dict) -> Dict[str, Any]:
    """기존 함수와의 호환성 유지"""
    if not issues:
        return {"score": 0.0, "level": "낮음", "reason": "이슈를 찾을 수 없음"}
    
    avg_confidence = sum(issue["confidence"] for issue in issues) / len(issues)
    
    # 문서 구조에 테이블이 포함되었는지 여부
    has_tables = bool(structure.get("tables"))
    if has_tables:
        avg_confidence = min(1.0, avg_confidence + 0.2)
    
    score = round(avg_confidence, 2)
    
    if score >= 0.8:
        level = "높음"
    elif score >= 0.5:
        level = "중간"
    else:
        level = "낮음"
    
    return {
        "score": score,
        "level": level,
        "issues_found": len(issues),
        "has_tables": has_tables
    } 