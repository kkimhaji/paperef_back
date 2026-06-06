<div align="center">

# <img width="30" height="30" src="https://github.com/user-attachments/assets/0100472c-0f52-46ce-9e3d-4010d03a45f0" /> Paperef

**개인 레퍼런스 관리 웹 애플리케이션**

레퍼런스, 링크, 메모 등을 그룹과 해시태그 기반으로 관리할 수 있는 웹 서비스

<br/>

![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)
![Dart](https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-323330?style=for-the-badge&logo=json-web-tokens&logoColor=pink)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white) 
![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white) 
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
</div>

### 서비스 링크

<img width="30" height="30" src="https://github.com/user-attachments/assets/0100472c-0f52-46ce-9e3d-4010d03a45f0" /> https://d29n3vqbryd7hd.cloudfront.net/

### Demo Account

- Email: kkim.haji@gmail.com
- Password: password1234
- 회원가입 없이 바로 기능을 확인할 수 있습니다.

</div>

---

# 프로젝트 소개

Paperef는 논문, 기술 문서, 아이디어 등의 레퍼런스를 그룹과 해시태그 기반으로 정리하고 검색할 수 있는 개인 레퍼런스 관리 웹 애플리케이션입니다.

대학원생 지인이 논문 작성 과정에서 참고 자료 링크와 메모를 체계적으로 정리하기 어렵다는 이야기를 하면서 개발을 시작하게 되었습니다.

Flutter Web과 FastAPI 기반으로 개발했으며 AWS 환경에 배포하여 운영 중입니다. 현재 논문·리포트 레퍼런스 정리뿐 아니라 업무 기록 및 개인 지식 관리 용도로도 활용되고 있습니다.

## Problem & Motivation

- 논문 및 기술 리서치 과정에서 참고 링크와 메모가 여러 곳에 흩어져 있어 다시 찾는 비용이 반복적으로 발생
- 기존 메모 앱은 제목 위주의 리스트 구조가 많아 메모로 저장한 내용을 빠르게 파악하기 어려웠음
- 그룹 분류와 태그 분류를 동시에 활용할 수 있는 정리 방식에 대한 요구 존재
- 현재 배포 후 논문/리포트 레퍼런스 정리 용도 뿐만 아니라 업무 로그 기록 및 개인 지식 관리 용도로도 사용 중

---

# 핵심 설계 포인트

- `updated_at + id` 기반 Cursor Pagination 적용
- PostgreSQL `WITH RECURSIVE` 기반 계층형 그룹 탐색
- JWT Access / Refresh Token + Refresh Token Rotation
- Flutter Web 딥링크 기반 비밀번호 재설정 처리
- Docker + GitHub Actions 기반 자동 배포 환경 구성

---

# 주요 기능

| 기능 | 설명 |
| --- | --- |
| **인증** | JWT 기반 로그인/회원가입 및 Access / Refresh Token 구조 |
| **계정 보안** | Refresh Token Rotation, 비밀번호 변경 시 다른 기기 로그아웃 |
| **계층형 그룹** | 무제한 Depth 하위 그룹 생성 및 Breadcrumb 탐색 |
| **레퍼런스 CRUD** | 제목, 요약, 본문, 해시태그 기반 레퍼런스 관리 |
| **검색 & 필터** | 키워드 검색, 해시태그 필터, 해시태그 검색 |
| **무한 스크롤** | Cursor 기반 페이지네이션 및 점진적 데이터 조회 |
| **비밀번호 재설정** | 이메일 기반 토큰 인증 및 딥링크 라우팅 지원 |

---

# Screenshots

## All References
<img width="897" height="1033" alt="Image" src="https://github.com/user-attachments/assets/b02275fe-84a5-44ac-87c8-6821cbe39396" />

## Group References
<img width="897" height="1033" alt="Image" src="https://github.com/user-attachments/assets/61deec53-fcfb-4028-9651-626d087693f3" />

## Sidebar
<img width="897" height="1033" alt="Image" src="https://github.com/user-attachments/assets/df976e8d-31c9-4dd9-baf9-9dc999fad57a" />

## Reference Detail
<img width="897" height="1033" alt="Image" src="https://github.com/user-attachments/assets/e8a95e93-40a5-482b-9f84-3c524516992b" />

</br>

# 기술 스택


### Frontend
![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)
![Dart](https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)

- **Flutter Web** — 반응형 크로스플랫폼 UI
- **Provider** — 전역 상태 및 UI 상태 관리
- **flutter_linkify** — 본문 내 URL 자동 감지
- **url_launcher** — 외부 링크 연결

### Backend
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white) 
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) 
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

- **FastAPI** — 비동기 REST API 서버
- **SQLAlchemy** — ORM 및 관계 데이터 처리
- **PostgreSQL** — 계층형 데이터 및 관계형 데이터 저장
- **JWT** — Access / Refresh Token 기반 인증 구조
- **Pydantic** — 요청 데이터 검증
- **Cursor Pagination** — 복합 커서 기반 페이지네이션

### Infra / DevOps
![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white) 
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white) 
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

- **AWS EC2** — 백엔드 서버 호스팅
- **AWS ECR** — Docker 이미지 저장소
- **AWS CloudFront** — CDN 및 HTTPS 엔드포인트 구성
- **AWS S3** — Flutter Web 정적 파일 호스팅
- **Docker / Docker Compose** — 컨테이너 기반 서버 구성
- **GitHub Actions** — CI/CD 자동화 파이프라인

---

# 시스템 아키텍처

```mermaid
flowchart TD
    User([Browser])

    subgraph CF["AWS CloudFront"]
        CF_F["CloudFront\\nFrontend"]
        CF_B["CloudFront\\nBackend API"]
    end

    subgraph AWS["AWS"]
        S3["S3\\nFlutter Web"]
        ECR["ECR\\nDocker Image"]

        subgraph EC2["EC2 Ubuntu"]
            subgraph Docker["Docker Compose"]
                API["FastAPI"]
                DB["PostgreSQL"]
            end
        end
    end

    subgraph CICD["CI/CD - GitHub Actions"]
        GH_B["Backend Workflow\\nbuild → ECR push → EC2 pull"]
        GH_F["Frontend Workflow\\nflutter build → S3 sync → CF invalidate"]
    end

    User --> CF_F
    User --> CF_B
    CF_F --> S3
    CF_B --> API
    ECR --> Docker
    API --> DB

    GH_B -.->|push image| ECR
    GH_F -.->|deploy| S3
```

### 아키텍처 특징

- Frontend와 Backend API에 각각 CloudFront를 적용하여 정적 파일 배포와 API 엔드포인트를 분리했습니다.
- 별도 도메인 없이 HTTPS 환경을 구성하기 위해 CloudFront를 API 프록시로 활용했습니다.
- 이를 통해 브라우저의 Mixed Content 문제를 방지하고 전체 구간 HTTPS 통신을 유지하도록 구성했습니다.

---

# Database Schema

<div align="center">
<img width="1093" height="814" alt="Image" src="https://github.com/user-attachments/assets/c84573bd-4044-406f-9541-dc1fbb318b24" />
</div>

### 데이터 구조

총 8개의 테이블로 구성되며, 모든 데이터는 사용자 단위로 관리됩니다.

- **users**: 계정 정보 저장. 모든 데이터는 `user_id` 외래 키를 통해 사용자별로 분리됩니다.
- **groups**: `parent_id` 자기 참조를 통해 무제한 계층 구조를 지원합니다.
- **refs**: 핵심 엔티티. 제목, 본문, 그룹 지정이 가능합니다.
- **ref_summaries**: 요약을 별도 테이블로 정규화하여 ref당 최대 3개의 순서 있는 요약을 저장합니다.
- **hashtags**: 중복 제거된 태그 풀로, `ref_hashtags` 다대다 조인 테이블을 통해 ref와 연결됩니다.
- **refresh_tokens**: Refresh Token Rotation을 위한 토큰 관리
- **password_reset_tokens**: 이메일 기반 비밀번호 재설정을 위한 일회성 시간 제한 토큰입니다.

---

# Technical Decisions

## Cursor Pagination 적용

레퍼런스 목록은 Cursor 기반 페이지네이션으로 구현했습니다.

Offset 방식은 데이터가 추가되거나 수정될 경우 중복 조회 또는 누락이 발생할 수 있습니다.

이를 해결하기 위해 `updated_at + id` 기반 복합 커서를 사용했으며, 정렬 기준을 커서에 함께 포함하여 정렬 변경 시 기존 커서를 무효화하도록 구성했습니다. 또한 무한 스크롤과 결합하여 데이터 변경 상황에서도 안정적으로 목록을 조회할 수 있도록 구현했습니다.

---

## WITH RECURSIVE 기반 계층 조회

그룹은 부모-자식 관계를 갖는 계층형 구조로 설계했습니다.

초기 구현에서는 Python 재귀 호출을 통해 하위 그룹을 탐색했지만, 계층 깊이가 증가할수록 반복 쿼리가 발생하는 문제가 있었습니다.

이를 PostgreSQL `WITH RECURSIVE` 기반 단일 쿼리 구조로 변경하여 계층 탐색을 DB 레벨에서 처리하도록 개선했습니다.

---

## DB 커넥션 풀 안정성 개선

장시간 서비스 운영 시 유휴 상태의 DB 커넥션이 끊어져 간헐적인 연결 오류가 발생할 수 있습니다.

이를 방지하기 위해 SQLAlchemy의 `pool_pre_ping`, `pool_recycle` 옵션을 적용하여 비정상 커넥션을 자동으로 감지하고 재생성하도록 구성했습니다.

또한 백그라운드 작업을 통해 만료된 Refresh Token과 Password Reset Token을 주기적으로 정리하도록 구현했습니다.

---

## Flutter Web 딥링크 라우팅 처리

비밀번호 재설정 이메일의 링크를 통해 서비스에 진입할 경우 URL 파라미터 전달 및 라우팅 처리 문제가 발생할 수 있습니다.

이를 해결하기 위해 비밀번호 재설정 전용 딥링크 흐름을 구성하고 URL 파라미터 기반 라우팅을 적용했습니다. 또한 SPA 환경에서 새로고침 및 직접 URL 접근 상황도 처리할 수 있도록 구성하여 일관된 사용자 경험을 제공하도록 개선했습니다.

---

## Refresh Token Rotation

Refresh Token 재발급 시 기존 토큰을 즉시 폐기하는 Rotation 방식을 적용했습니다.

이를 통해 토큰 탈취 상황에서 재사용 위험을 줄이고, 서버 측에서 토큰 상태를 관리할 수 있도록 구성했습니다.

또한 비밀번호 변경 시에는 현재 기기의 세션은 유지하고, 다른 기기의 세션만 선택적으로 종료할 수 있도록 구현했습니다.

---

# 배포 및 CI/CD

## Backend Deployment Flow

```
GitHub Push
    ↓
GitHub Actions
    ↓
Docker Image Build
    ↓
AWS ECR Push
    ↓
EC2 Pull
    ↓
Docker Compose Restart
```

## Frontend Deployment Flow

```
GitHub Push
    ↓
GitHub Actions
    ↓
Flutter Web Build
    ↓
S3 Sync
    ↓
CloudFront Cache Invalidation
```

### 배포 환경

| 구성 | 내용 |
| --- | --- |
| Frontend | AWS S3 + CloudFront |
| Backend | AWS EC2 + Docker Compose |
| Registry | AWS ECR |
| CI/CD | GitHub Actions |

---
