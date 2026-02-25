
<div align="center">

# 📎 Paperef

**개인 레퍼런스 관리 웹 앱**  
링크, 메모, 아이디어를 그룹과 해시태그로 체계적으로 정리하세요.

<br/>

![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)
![Dart](https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-323330?style=for-the-badge&logo=json-web-tokens&logoColor=pink)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)

</div>

---

## 📌 프로젝트 소개

**Paperef**는 개인 레퍼런스(링크, 메모, 아이디어 등)를 저장하고 체계적으로 관리할 수 있는 풀스택 웹 애플리케이션입니다.  
Flutter Web 기반의 반응형 UI와 FastAPI 백엔드로 구성되어 있으며, 계층형 그룹 구조와 해시태그 필터링을 통해 빠른 검색과 분류가 가능합니다.

> 💡 개발 목적: 개인 학습 자료, 유용한 링크, 아이디어 메모를 한 곳에서 관리하기 위해 직접 설계·개발한 프로젝트입니다.

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 🔐 **인증** | JWT 기반 로그인/회원가입, Access Token(30분) + Refresh Token(7일) |
| 📁 **계층형 그룹** | 무제한 뎁스의 하위 그룹 생성, 브레드크럼 네비게이션 |
| 📝 **레퍼런스 CRUD** | 제목, 요약, 본문, 해시태그 포함 레퍼런스 작성/수정/삭제 |
| 🔍 **검색 & 필터** | 키워드 검색(디바운싱 500ms), 해시태그 필터, 하위 그룹 포함 여부 토글 |
| 🔗 **링크 자동 감지** | 본문 내 URL 자동 인식 및 클릭 가능한 링크로 변환 |
| 📋 **전체 복사** | 레퍼런스 전체 내용을 클립보드에 복사 |
| 📱 **반응형 UI** | iPad 스플릿 뷰, Stage Manager 등 다양한 화면 크기 대응 |
| 🔑 **비밀번호 재설정** | 이메일 기반 토큰 인증 비밀번호 재설정 |

---

## 🛠️ 기술 스택

### Frontend
![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)
![Dart](https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)

- **Flutter Web** — 반응형 크로스플랫폼 UI
- **Provider** — 상태 관리
- **flutter_linkify** — URL 자동 감지
- **url_launcher** — 외부 링크 열기

### Backend
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

- **FastAPI** — 비동기 REST API 서버
- **SQLAlchemy** — ORM (joinedload, @property 활용)
- **PostgreSQL** — 관계형 데이터베이스
- **JWT** — 인증 토큰 (Access 30분 + Refresh 7일)
- **Pydantic** — 데이터 검증

### Infra
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

- **Docker / Docker Compose** — 컨테이너 환경

---

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────┐
│            Flutter Web (Frontend)       │
│  Provider  ──  Screens  ──  Widgets     │
└──────────────────┬──────────────────────┘
                   │ REST API (HTTP/JSON)
┌──────────────────▼──────────────────────┐
│            FastAPI (Backend)            │
│  Router  ──  Service  ──  SQLAlchemy    │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│           PostgreSQL (Database)         │
└─────────────────────────────────────────┘
```

---

## 📸 스크린샷

> 준비 중

---

## 📄 License

This project is for portfolio purposes.
