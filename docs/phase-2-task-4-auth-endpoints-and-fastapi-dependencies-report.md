# Phase 2, Task 4: Authentication Endpoints & FastAPI Dependencies — Implementation Report

**Author / Owner:** Vishal (Backend Infrastructure, Security & Persistence)  
**Target System:** Curio AI Backend  
**Date:** 2026-09-22  
**Status:** **COMPLETED & VERIFIED** (252 of 252 tests passing, 0 regressions)

---

## 1. Executive Summary

Phase 2, Task 4 exposed authentication capabilities to clients via FastAPI dependencies and HTTP endpoints under `/api/v1/auth`. Building upon the cryptographic foundations (Task 2) and service/repository infrastructure (Task 3), this task establishes the OAuth2 Bearer security scheme, implements user authentication dependencies with RFC-standard `WWW-Authenticate` header handling, and exposes registration, login, and profile introspection routes.

The implementation comprises:
1. **FastAPI Security Dependencies** (`backend/app/api/deps.py`):
   - `oauth2_scheme`: Configured with `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` for automatic Swagger UI authorization integration.
   - `get_current_user`: Decodes JWT tokens, validates subject UUID format, queries persistent `User` records from `UserRepository`, and returns HTTP 401 Unauthorized on invalid/expired/missing credentials.
   - `get_current_active_user`: Enforces that the authenticated user account has `is_active=True`, raising HTTP 400 Bad Request if deactivated.
2. **Authentication API Router** (`backend/app/api/v1/auth.py`):
   - `POST /api/v1/auth/register`: Validates user inputs, creates user via `AuthService.register_user()`, and returns HTTP 201 Created with safe `UserResponse` (strictly excluding password hashes). Duplicate email attempts return HTTP 400 Bad Request.
   - `POST /api/v1/auth/login`: Authenticates credentials with timing-safe verification, issues JWT access tokens, and returns `Token` with HTTP 200 OK. Invalid credentials return HTTP 401 Unauthorized with `WWW-Authenticate: Bearer`.
   - `GET /api/v1/auth/me`: Protected route returning the current user's profile with HTTP 200 OK.
3. **Router Registration** (`backend/app/api/router.py`):
   - Included `auth.router` with tag `"Authentication"`, prefixing routes with `/api/v1`.
4. **Comprehensive Test Suite**:
   - 15 new tests (14 endpoint tests in `test_auth_api.py`, 1 complete end-to-end integration test in `test_auth_api_integration.py`).
   - Total test suite expanded from **237 to 252 passing tests**, with 0 regressions.

---

## 2. Architectural Boundaries & Security Posture

- **Preservation of Core Boundaries**:
  - `MOCK_USER_ID` was preserved for Phase 1 session, message, document, and report workflows. No session ownership logic was altered (strictly deferred to Tasks 5–6).
  - Chinmay's AI logic, prompts, `DecisionEngine`, `LangGraph`, and `CurioEngine` remain completely untouched.
  - No live Groq API calls were made.
- **Security & Hygiene**:
  - Zero password or hash leakage in response schemas or logs.
  - All 401 Unauthorized exceptions emit the standard `WWW-Authenticate: Bearer` challenge header.
  - Generic authentication failure messages prevent user enumeration attacks.
  - All database interactions in tests strictly target `curio_test_db` with transaction savepoint rollbacks.

---

## 3. Component Details

### 3.1 FastAPI Dependencies (`backend/app/api/deps.py`)

```python
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

user_repo = UserRepository()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: SQLAlchemySession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = UUID(str(sub))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_exception

    user = user_repo.get_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user
```

### 3.2 Authentication Endpoints (`backend/app/api/v1/auth.py`)

| Method | Endpoint | Status | Request Body | Response Model | Auth Required |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | `201 Created` | `UserCreate` | `UserResponse` | No |
| `POST` | `/api/v1/auth/login` | `200 OK` | `UserLogin` | `Token` | No |
| `GET` | `/api/v1/auth/me` | `200 OK` | None | `UserResponse` | **Bearer JWT** |

### 3.3 Swagger / OpenAPI Verification

Verified via programmatic inspection of the generated OpenAPI schema:
- Routes registered: `['/api/v1/auth/register', '/api/v1/auth/login', '/api/v1/auth/me']`
- Security Schemes defined: `{'OAuth2PasswordBearer': {'type': 'oauth2', 'flows': {'password': {'scopes': {}, 'tokenUrl': '/api/v1/auth/login'}}}}`
- `/api/v1/auth/me` security requirement: `[{'OAuth2PasswordBearer': []}]`
- Swagger displays the interactive "Authorize" modal and padlock indicator on protected endpoints.

---

## 4. Test Verification & Results

### 4.1 Endpoint Tests (`backend/tests/api/test_auth_api.py`)
- `test_register_valid_user`: Creates user, returns 201, excludes password/hash.
- `test_register_duplicate_email`: Duplicate registration returns 400 Bad Request.
- `test_register_invalid_email_format`: Malformed email returns 422 Unprocessable Entity.
- `test_register_password_too_short`: Password < 8 characters returns 422.
- `test_login_valid_credentials`: Valid login returns 200 with JWT access token.
- `test_login_wrong_password`: Incorrect password returns 401 with `WWW-Authenticate: Bearer`.
- `test_login_unknown_email`: Missing email returns identical 401 Unauthorized.
- `test_login_inactive_user`: Deactivated account returns 400 Bad Request.
- `test_auth_me_valid_token`: Valid Bearer token retrieves profile (200 OK).
- `test_auth_me_missing_token`: Missing Authorization header returns 401.
- `test_auth_me_malformed_token`: Malformed token string returns 401.
- `test_auth_me_expired_token`: Expired token rejected with 401.
- `test_auth_me_nonexistent_user_in_token`: Nonexistent UUID subject returns 401.
- `test_auth_me_inactive_user`: Inactive user accessing `/me` returns 400.
**Result**: 14 passed in 7.31s.

### 4.2 Integration Tests (`backend/tests/integration/test_auth_api_integration.py`)
- `test_full_auth_lifecycle_integration`: End-to-end user registration, credential login, JWT extraction, protected `/auth/me` verification, and case-insensitive login validation against live PostgreSQL database (`curio_test_db`).
**Result**: 1 passed in 3.79s.

### 4.3 Full Pytest Regression Suite
```text
===================== 252 passed, 357 warnings in 34.80s ======================
```
- Total test count: **252 passed** (237 baseline + 15 new tests).
- Regressions: **0**.

---

## 5. Next Steps for Phase 2 Task 5

With authentication endpoints and dependencies operational:
- Task 5 will establish session ownership and user association across session creation, listing, retrieval, and termination.
- Session authorization checks will ensure users can only access their own sessions, while preserving backward compatibility during the transition.
