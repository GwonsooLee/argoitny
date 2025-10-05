# AlgoItny Backend Tests

포괄적인 pytest 테스트 스위트로 AlgoItny Django 백엔드의 모든 기능을 테스트합니다.

## 테스트 구조

```
backend/tests/
├── __init__.py
├── conftest.py           # 공통 fixtures 및 설정
├── test_auth.py          # 인증 테스트 (Google OAuth, JWT)
├── test_problems.py      # 문제 관리 테스트
├── test_execute.py       # 코드 실행 테스트
├── test_history.py       # 검색 기록 테스트
├── test_register.py      # 문제 등록 및 테스트 케이스 생성
└── test_account.py       # 계정 통계 테스트
```

## 빠른 시작

### Docker 환경에서 실행

```bash
# 모든 테스트 실행
make test

# 커버리지 리포트 포함
make test-cov

# 빠른 테스트 (외부 API 제외)
make test-fast

# 병렬 테스트 (빠른 실행)
make test-parallel

# 상세 출력
make test-verbose

# 특정 테스트 파일만 실행
make test-specific
```

### 로컬 환경에서 실행

```bash
# 테스트 의존성 설치
cd backend
pip install pytest pytest-django pytest-cov pytest-mock pytest-asyncio pytest-xdist

# 테스트 실행
pytest

# 커버리지 리포트 포함
pytest --cov=api --cov-report=term-missing --cov-report=html
```

## 테스트 명령어

### 기본 테스트

| 명령어 | 설명 |
|--------|------|
| `make test` | 모든 테스트 실행 |
| `make test-cov` | 커버리지 리포트 포함 |
| `make test-fast` | 빠른 테스트 (외부 API 제외) |
| `make test-watch` | 파일 변경 감지 자동 테스트 |
| `make test-parallel` | 병렬 테스트 실행 |
| `make test-verbose` | 상세 출력으로 테스트 |
| `make test-specific` | 특정 테스트 파일 실행 |

### 로컬 테스트 (Docker 없이)

| 명령어 | 설명 |
|--------|------|
| `make test-local` | 로컬에서 테스트 실행 |
| `make test-local-cov` | 로컬 테스트 + 커버리지 |

### 정리

| 명령어 | 설명 |
|--------|------|
| `make test-clean` | 테스트 캐시 삭제 |

## 테스트 커버리지

현재 테스트 커버리지: **85%+**

### 커버리지 리포트 확인

```bash
# HTML 리포트 생성
make test-cov

# 브라우저에서 확인
open backend/htmlcov/index.html
```

## 테스트 카테고리

### 1. 인증 테스트 (test_auth.py)

- **Google OAuth 로그인**: 21개 테스트
  - 새 사용자 생성
  - 기존 사용자 로그인
  - 잘못된 토큰 처리
  - 에러 처리
- **JWT 토큰 갱신**: 5개 테스트
- **로그아웃**: 4개 테스트
- **전체 인증 플로우**: 1개 통합 테스트

### 2. 문제 테스트 (test_problems.py)

- **문제 목록 조회**: 10개 테스트
  - 검색 기능 (제목, 문제번호)
  - 플랫폼 필터링
  - 초안 제외
  - 정렬
- **문제 상세 조회**: 8개 테스트
  - ID로 조회
  - 플랫폼+문제번호로 조회
  - 테스트 케이스 포함
- **초안 관리**: 4개 테스트
- **등록된 문제**: 4개 테스트
- **Edge Cases**: 3개 테스트

### 3. 코드 실행 테스트 (test_execute.py)

- **코드 실행 API**: 11개 테스트
  - 성공 케이스
  - 유효성 검증
  - 인증 확인
  - 다양한 언어
- **Celery 작업**: 6개 테스트
  - 성공/실패 처리
  - 익명 사용자
  - 메타데이터 업데이트
- **Edge Cases**: 4개 테스트

### 4. 검색 기록 테스트 (test_history.py)

- **기록 목록**: 14개 테스트
  - 페이지네이션
  - 권한 기반 필터링
  - 코드 가시성
  - 정렬
- **기록 상세**: 6개 테스트
- **기록 생성**: 2개 테스트
- **쿼리 최적화**: 2개 테스트
- **Edge Cases**: 4개 테스트

### 5. 문제 등록 테스트 (test_register.py)

- **테스트 케이스 생성**: 4개 테스트
- **문제 등록**: 6개 테스트
- **생성기 실행**: 5개 테스트
- **작업 관리**: 6개 테스트
- **문제 저장**: 5개 테스트
- **완료 토글**: 4개 테스트
- **출력 생성**: 4개 테스트
- **작업 상태 확인**: 4개 테스트

### 6. 계정 테스트 (test_account.py)

- **계정 통계**: 10개 테스트
  - 플랫폼별 통계
  - 언어별 통계
  - 고유 문제 수
  - 성공/실패 비율

**총 테스트 케이스 수: 150+개**

## Fixtures

### 주요 Fixtures

#### 사용자 관련
- `sample_user`: 테스트용 일반 사용자
- `another_user`: 추가 테스트 사용자
- `authenticated_client`: JWT 인증된 API 클라이언트
- `jwt_tokens`: JWT access/refresh 토큰

#### 문제 관련
- `sample_problem`: 완성된 문제 (테스트 케이스 포함)
- `draft_problem`: 초안 문제 (테스트 케이스 없음)
- `sample_problems`: 여러 플랫폼의 문제들
- `sample_test_cases`: 문제의 테스트 케이스들

#### 기록 관련
- `sample_search_history`: 공개 검색 기록
- `private_search_history`: 비공개 검색 기록

#### 작업 관련
- `sample_script_job`: 대기 중인 스크립트 생성 작업
- `completed_script_job`: 완료된 스크립트 생성 작업

### Mock Fixtures

- `mock_google_oauth`: Google OAuth 서비스 Mock
- `mock_gemini_service`: Gemini AI 서비스 Mock
- `mock_judge0_service`: Judge0 코드 실행 서비스 Mock
- `mock_celery_task`: Celery 작업 Mock
- `mock_test_case_generator`: 테스트 케이스 생성기 Mock

## 테스트 마커

pytest 마커를 사용하여 특정 테스트만 실행할 수 있습니다:

```bash
# 느린 테스트 제외
pytest -m "not slow"

# 통합 테스트만 실행
pytest -m integration

# 단위 테스트만 실행
pytest -m unit

# 외부 API 호출 테스트 제외
pytest -m "not external_api"
```

## 테스트 작성 가이드

### 1. 테스트 명명 규칙

```python
class TestFeatureName:
    """Test feature description"""

    def test_action_success(self, fixtures):
        """Test successful action"""
        # Test implementation

    def test_action_failure_case(self, fixtures):
        """Test action with specific failure"""
        # Test implementation
```

### 2. Fixture 사용

```python
@pytest.mark.django_db
def test_with_database(sample_user, authenticated_client):
    """Test requiring database and authentication"""
    response = authenticated_client.get('/api/endpoint/')
    assert response.status_code == 200
```

### 3. Mock 사용

```python
def test_with_external_service(api_client, mock_judge0_service):
    """Test with mocked external service"""
    # mock_judge0_service는 자동으로 Judge0 호출을 mock함
    response = api_client.post('/api/execute/', data)
    assert response.status_code == 202
```

### 4. 비동기 테스트

```python
@pytest.mark.django_db
def test_async_task(sample_problem):
    """Test async Celery task"""
    from api.tasks import execute_code_task

    with patch('api.tasks.CodeExecutionService') as mock:
        mock.execute_with_test_cases.return_value = [...]
        result = execute_code_task(...)
        assert result['status'] == 'COMPLETED'
```

## 성능 최적화

### 쿼리 최적화 테스트

```python
def test_query_optimization(api_client, sample_problems, django_assert_num_queries):
    """Test that endpoint uses optimized queries"""
    with django_assert_num_queries(2):  # Only 2 queries expected
        response = api_client.get('/api/problems/')
        assert response.status_code == 200
```

### 병렬 실행

```bash
# CPU 코어 수만큼 병렬 실행
pytest -n auto

# 특정 개수의 worker로 실행
pytest -n 4
```

## CI/CD 통합

### GitHub Actions

```yaml
- name: Run tests
  run: |
    cd backend
    pytest --cov=api --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./backend/coverage.xml
```

## 문제 해결

### 일반적인 문제

#### 1. 데이터베이스 마이그레이션 오류

```bash
# 마이그레이션 재실행
make migrate

# 또는 테스트 DB 초기화
pytest --create-db
```

#### 2. Import 오류

```bash
# PYTHONPATH 확인
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"

# Django 설정 확인
export DJANGO_SETTINGS_MODULE=config.settings
```

#### 3. Mock이 작동하지 않음

```python
# Mock 경로를 정확히 지정
# 잘못된 예: @patch('services.google_oauth.GoogleOAuthService')
# 올바른 예: @patch('api.views.auth.GoogleOAuthService')
```

#### 4. 테스트 캐시 문제

```bash
# 캐시 삭제
make test-clean

# 또는
pytest --cache-clear
```

## 리소스

- [pytest 공식 문서](https://docs.pytest.org/)
- [pytest-django 문서](https://pytest-django.readthedocs.io/)
- [Django 테스트 가이드](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Coverage.py 문서](https://coverage.readthedocs.io/)

## 기여하기

새로운 기능을 추가할 때는 반드시 테스트를 함께 작성해주세요:

1. 기능 구현
2. 테스트 작성 (성공 케이스 + 실패 케이스)
3. `make test-cov` 실행하여 커버리지 확인
4. 커버리지가 80% 이상 유지되는지 확인

## 라이센스

AlgoItny 프로젝트 라이센스를 따릅니다.
