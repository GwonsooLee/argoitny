# GitHub Secrets 설정 가이드

GitHub Actions를 사용한 자동 배포를 위해 필요한 Secrets를 설정하는 가이드입니다.

## 1. GitHub Secrets란?

GitHub Secrets는 GitHub Actions 워크플로우에서 사용할 수 있는 암호화된 환경 변수입니다. AWS 자격 증명과 같은 민감한 정보를 안전하게 저장할 수 있습니다.

## 2. Secrets 설정 방법

### 단계별 가이드

1. **GitHub Repository 접속**
   - 프로젝트 Repository 페이지로 이동

2. **Settings 탭 클릭**
   - 상단 메뉴에서 "Settings" 클릭
   - Repository settings 페이지로 이동

3. **Secrets and variables 선택**
   - 왼쪽 사이드바에서 "Secrets and variables" > "Actions" 클릭

4. **New repository secret 추가**
   - "New repository secret" 버튼 클릭
   - 각 Secret을 아래 목록대로 추가

## 3. 필수 Secrets 목록

### AWS_ACCESS_KEY_ID
- **설명**: AWS IAM 사용자의 Access Key ID
- **값 형식**: `AKIAIOSFODNN7EXAMPLE`
- **획득 방법**:
  1. AWS IAM Console 접속
  2. Users > 사용자 선택 > Security credentials 탭
  3. "Create access key" 클릭
  4. Access key ID 복사

**중요**: Access Key는 한 번만 표시되므로 반드시 안전한 곳에 저장하세요.

---

### AWS_SECRET_ACCESS_KEY
- **설명**: AWS IAM 사용자의 Secret Access Key
- **값 형식**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
- **획득 방법**:
  1. `AWS_ACCESS_KEY_ID`와 동일한 과정에서 함께 생성
  2. Secret access key 복사

**중요**: Secret Access Key는 생성 시 한 번만 표시됩니다. 잃어버린 경우 새로 생성해야 합니다.

---

### AWS_REGION
- **설명**: AWS 리전
- **값**: `us-east-1`
- **추천 리전**:
  - CloudFront SSL 인증서는 반드시 `us-east-1` 필요
  - S3 버킷은 어느 리전에나 생성 가능하지만 `us-east-1` 권장

---

### S3_BUCKET_NAME
- **설명**: 빌드 파일을 업로드할 S3 버킷 이름
- **값 형식**: `algoitny-frontend-prod`
- **주의사항**:
  - 버킷 이름은 전역에서 고유해야 함
  - 소문자, 숫자, 하이픈만 사용 가능
  - 3-63자 사이

**버킷 생성 예시**:
```bash
aws s3 mb s3://algoitny-frontend-prod --region us-east-1
```

---

### CLOUDFRONT_DISTRIBUTION_ID
- **설명**: CloudFront Distribution ID (캐시 무효화용)
- **값 형식**: `E1XXXXXXXXXX`
- **획득 방법**:
  1. AWS CloudFront Console 접속
  2. Distributions 목록에서 해당 Distribution 선택
  3. Distribution ID 복사 (예: `E2ABCDEFGHIJK`)

**CLI로 확인**:
```bash
aws cloudfront list-distributions \
  --query "DistributionList.Items[*].[Id,Comment]" \
  --output table
```

---

## 4. IAM 사용자 생성 및 권한 설정

GitHub Actions에서 사용할 IAM 사용자를 생성하고 적절한 권한을 부여해야 합니다.

### 4.1 IAM 사용자 생성

```bash
# IAM 사용자 생성
aws iam create-user --user-name github-actions-deploy

# Access Key 생성
aws iam create-access-key --user-name github-actions-deploy
```

### 4.2 권한 정책 생성

**정책 파일 생성** (`github-actions-policy.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Deployment",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::algoitny-frontend-prod",
        "arn:aws:s3:::algoitny-frontend-prod/*"
      ]
    },
    {
      "Sid": "CloudFrontInvalidation",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation",
        "cloudfront:ListInvalidations"
      ],
      "Resource": "*"
    }
  ]
}
```

**정책 적용**:

```bash
# 정책 생성
aws iam create-policy \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://github-actions-policy.json

# 사용자에게 정책 연결
aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/GitHubActionsDeployPolicy
```

**YOUR_ACCOUNT_ID 확인**:
```bash
aws sts get-caller-identity --query Account --output text
```

---

## 5. Secrets 추가 방법 (스크린샷 가이드)

### 방법 1: GitHub UI 사용

1. **Repository 접속**
   ```
   https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions
   ```

2. **"New repository secret" 클릭**

3. **Name과 Value 입력**
   - Name: `AWS_ACCESS_KEY_ID`
   - Value: `AKIAIOSFODNN7EXAMPLE`

4. **"Add secret" 클릭**

5. **나머지 Secrets도 동일하게 추가**

### 방법 2: GitHub CLI 사용

```bash
# GitHub CLI 설치 (macOS)
brew install gh

# GitHub 인증
gh auth login

# Secrets 추가
gh secret set AWS_ACCESS_KEY_ID
gh secret set AWS_SECRET_ACCESS_KEY
gh secret set AWS_REGION
gh secret set S3_BUCKET_NAME
gh secret set CLOUDFRONT_DISTRIBUTION_ID
```

---

## 6. Secrets 확인

### Secrets 목록 확인

```bash
# GitHub CLI로 확인
gh secret list
```

**예상 출력**:
```
AWS_ACCESS_KEY_ID              Updated 2025-01-01
AWS_SECRET_ACCESS_KEY          Updated 2025-01-01
AWS_REGION                     Updated 2025-01-01
S3_BUCKET_NAME                 Updated 2025-01-01
CLOUDFRONT_DISTRIBUTION_ID     Updated 2025-01-01
```

### 워크플로우에서 Secrets 사용 확인

`.github/workflows/deploy-cloudfront.yml` 파일에서 Secrets가 올바르게 참조되는지 확인:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ${{ env.AWS_REGION }}
```

---

## 7. 보안 모범 사례

### 7.1 최소 권한 원칙
- IAM 사용자에게 필요한 최소한의 권한만 부여
- 특정 S3 버킷과 CloudFront Distribution만 접근 가능하도록 제한

### 7.2 Access Key 관리
- Access Key를 절대 코드에 하드코딩하지 말 것
- Access Key를 공개 저장소에 커밋하지 말 것
- 정기적으로 Access Key 교체 (90일마다 권장)
- 사용하지 않는 Access Key는 즉시 삭제

### 7.3 Secrets 보호
- Secrets는 GitHub에서 암호화되어 저장됨
- 워크플로우 로그에 Secrets가 출력되지 않도록 주의
- 민감한 정보를 `echo`로 출력하지 말 것

### 7.4 권한 감사
- CloudTrail을 사용하여 API 호출 기록 확인
- 정기적으로 IAM 사용자의 활동 검토
- 비정상적인 활동 발견 시 즉시 Access Key 비활성화

---

## 8. 문제 해결

### Secret이 워크플로우에서 인식되지 않는 경우

**원인**:
- Secret 이름이 정확하지 않음 (대소문자 구분)
- Secret이 Repository level이 아닌 Organization level에 설정됨

**해결**:
1. Secret 이름 재확인 (정확히 일치해야 함)
2. Repository Settings > Secrets and variables > Actions에서 확인
3. 필요 시 Secret 삭제 후 재생성

### Access Denied 에러

**원인**:
- IAM 사용자 권한 부족
- Access Key가 비활성화됨
- 잘못된 Access Key 사용

**해결**:
1. IAM Console에서 사용자 권한 확인
2. Access Key 상태 확인 (Active인지)
3. Secret 값이 정확한지 재확인
4. IAM 정책에서 필요한 권한 추가

### CloudFront Invalidation 실패

**원인**:
- Distribution ID가 잘못됨
- CloudFront 권한 부족

**해결**:
1. Distribution ID 재확인
2. IAM 정책에 `cloudfront:CreateInvalidation` 권한 추가
3. Distribution이 Deployed 상태인지 확인

---

## 9. 체크리스트

배포 전 다음 항목을 확인하세요:

- [ ] AWS IAM 사용자 생성 완료
- [ ] Access Key 생성 및 안전하게 저장
- [ ] IAM 정책 생성 및 사용자에게 연결
- [ ] S3 버킷 생성 완료
- [ ] CloudFront Distribution 생성 완료
- [ ] GitHub Secrets 추가:
  - [ ] `AWS_ACCESS_KEY_ID`
  - [ ] `AWS_SECRET_ACCESS_KEY`
  - [ ] `AWS_REGION`
  - [ ] `S3_BUCKET_NAME`
  - [ ] `CLOUDFRONT_DISTRIBUTION_ID`
- [ ] GitHub CLI로 Secrets 목록 확인
- [ ] 워크플로우 파일에서 Secrets 참조 확인
- [ ] `main` 브랜치에 코드 push 하여 자동 배포 테스트

---

## 10. 참고 자료

- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

---

**도움이 필요하면 AWS Support 또는 GitHub Support에 문의하세요.**
