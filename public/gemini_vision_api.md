# Gemini Vision API 무한 로딩 문제 분석 및 해결 방안

## 📋 문제 요약

### 현재 상황
- **핵심 문제**: ESG 문서 처리 API에서 무한 로딩 발생 (30초+ 타임아웃)
- **영향도**: 사용자가 PDF 업로드 후 응답을 받지 못해 서비스 이용 불가
- **발생 범위**: Gemini Vision API (`/api/v1/documents/upload-vision`) 및 일부 기본 API

### 기술적 근본 원인
1. **Gemini Vision API 호출 시 무한 대기**: Google API 서버와의 네트워크 연결에서 응답 지연
2. **텍스트 기반 분석의 한계**: 기존 `upload-fast` 엔드포인트는 중대성 이슈를 전혀 추출하지 못함 (`materiality_issues: []`)
3. **타임아웃 처리 부재**: API 호출에 적절한 타임아웃이 설정되지 않음

---

## 🔍 기술적 분석

### 1. 현재 아키텍처
```
Client → FastAPI → DocumentProcessingService → GeminiVisionProcessor → Gemini API
```

### 2. 병목 지점
- **PDF → 이미지 변환**: PyMuPDF를 사용한 변환 (정상 동작)
- **Gemini Vision API 호출**: `google.generativeai.generate_content()` 에서 무한 대기
- **네트워크 레이어**: gRPC 타임아웃 설정 부족

### 3. 환경 문제
- **가상환경 미사용**: 서버가 시스템 Python에서 실행되어 `google.generativeai` 모듈 누락
- **의존성 문제**: 필수 라이브러리가 올바른 환경에 설치되지 않음

---

## ✅ 구현된 해결책

### 1. 강력한 타임아웃 시스템 구축
```python
# 다층 타임아웃 설정
- gRPC 레벨: 15초
- asyncio.wait_for: 20초  
- 페이지별 처리: 30초
- 전체 문서 처리: 180초 (3분)
```

### 2. 에러 처리 및 폴백 메커니즘
```python
try:
    # 1차: 정확한 중대성 이슈 추출
    result = await extract_materiality_issues()
except TimeoutError:
    # 2차: 일반 ESG 콘텐츠 분석  
    result = await fallback_general_analysis()
```

### 3. 최적화된 프롬프트 엔지니어링
- **1-5페이지 테스트 파일 특화**: 불필요한 페이지 범위 분석 제거
- **간소화된 JSON 스키마**: 응답 파싱 안정성 향상
- **최신 모델 사용**: `gemini-2.0-flash-exp` 적용

### 4. 중복 엔드포인트 정리
- **문제**: `/upload-vision` 엔드포인트가 2개 정의되어 충돌
- **해결**: 단일 엔드포인트로 통합, 명확한 API 스펙 정의

---

## 🚨 현재 미해결 이슈

### 1. Google API 연결 불안정
**증상**: Health check 엔드포인트도 응답하지 않음
```bash
curl http://localhost:8000/api/v1/health/  # 10초 타임아웃
```

**가능한 원인**:
- Gemini API 키 유효성 문제
- Google API 서버 지역별 접근 제한
- 네트워크 방화벽/프록시 이슈
- API 할당량 초과

### 2. 환경 설정 복잡성
- 가상환경 활성화 필수
- 시스템 Python vs 가상환경 Python 혼동

---

## 🎯 제안하는 해결 방안

### Option 1: API 키 및 권한 검증
```bash
# 1. API 키 유효성 확인
curl -H "x-goog-api-key: $GEMINI_API_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models"

# 2. Vision API 권한 확인  
curl -H "x-goog-api-key: $GEMINI_API_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision"
```

### Option 2: 모델 다운그레이드
```python
# 실험적 모델 대신 안정적 모델 사용
model_name = "gemini-1.5-pro"  # 대신 "gemini-2.0-flash-exp"
```

### Option 3: 이미지 최적화
```python
# DPI 축소로 이미지 크기 감소
pdf_converter = PDFConverter(dpi=100)  # 기존 200에서 축소
```

### Option 4: 하이브리드 접근법
```python
async def smart_document_processing(file_path):
    try:
        # Vision API 우선 시도 (20초 타임아웃)
        return await vision_api_process(file_path)
    except TimeoutError:
        # 텍스트 기반 분석으로 폴백
        return await text_based_process(file_path)
```

### Option 5: 비동기 처리 아키텍처
```
Client → Job Queue (Redis/Celery) → Background Worker → Vision API
       ↓
    Job Status API (폴링/WebSocket)
```

---

## 📊 성능 및 안정성 목표

### 단기 목표 (1주)
- [ ] Vision API 기본 연결 안정화
- [ ] 90% 이상 요청이 3분 내 응답
- [ ] 실제 중대성 이슈 추출 성공률 80%+

### 중기 목표 (1개월)  
- [ ] 평균 응답 시간 60초 이하
- [ ] 99% 가용성 달성
- [ ] 다양한 PDF 형식 지원

### 장기 목표 (3개월)
- [ ] 실시간 처리 (30초 이하)
- [ ] 자동 스케일링
- [ ] 멀티 모델 앙상블

---

## 🔧 즉시 시도 가능한 디버깅 단계

### 1. API 키 검증
```python
# test_api_key.py
import os
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

try:
    models = genai.list_models()
    print("✅ API 키 유효")
    for model in models:
        if "vision" in model.name.lower():
            print(f"📷 Vision 모델: {model.name}")
except Exception as e:
    print(f"❌ API 키 문제: {e}")
```

### 2. 네트워크 연결 테스트
```bash
# Google API 서버 접근성 확인
ping generativelanguage.googleapis.com
telnet generativelanguage.googleapis.com 443
```

### 3. 최소 재현 케이스
```python
# minimal_test.py - 가장 간단한 Vision API 호출
import google.generativeai as genai
genai.configure(api_key="your-key")
model = genai.GenerativeModel('gemini-1.5-pro')
response = model.generate_content("Hello")  # 텍스트만
print(response.text)
```

---

## 📞 CTO 의사결정 요청사항

1. **우선순위 설정**: Vision API 안정화 vs 텍스트 기반 폴백 강화
2. **예산 승인**: Google Cloud 크레딧 추가 구매 필요성
3. **아키텍처 방향**: 동기 처리 vs 비동기 Job Queue 도입
4. **외부 지원**: Google Cloud Professional Services 컨설팅 고려

---

## 📈 예상 효과

### 해결 후 기대 효과
- **사용자 경험**: 무한 로딩 → 3분 내 결과 제공
- **기능 정확도**: 중대성 이슈 추출 성공률 0% → 80%+
- **서비스 안정성**: 타임아웃으로 인한 서버 다운 방지
- **개발 생산성**: 명확한 에러 처리로 디버깅 시간 단축

### 비즈니스 임팩트
- ESG 분석 서비스의 핵심 가치 제안 실현
- 고객 만족도 향상 및 이탈률 감소  
- 프리미엄 기능으로서의 Vision API 차별화

---

**최종 업데이트**: 2025-07-22
**작성자**: AI Assistant  
**검토 필요**: CTO, Backend Team Lead
