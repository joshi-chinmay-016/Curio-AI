# Phase 2, Task 3: User Schemas, Repository & Authentication Service — Implementation Report

**Author / Owner:** Vishal (Backend Infrastructure, Security & Persistence)  
**Target System:** Curio AI Backend  
**Date:** 2026-09-22  
**Status:** **COMPLETED & VERIFIED** (237 of 237 tests passing, 0 regressions)

---

## 1. Executive Summary

Phase 2, Task 3 delivers the foundational user-management and authentication service layer for Curio AI without exposing API endpoints or FastAPI dependencies yet (strictly preserved for Tasks 4–6). 

The implementation comprises:
1. **User and Authentication Pydantic Schemas** (`backend/app/schemas/user.py`, `backend/app/schemas/auth.py`): Pydantic v2 compliant models ensuring RFC email format validation, strict password minimum length enforcement (>= 8 characters), and guaranteed exclusion of password hashes from outgoing user representations (`UserResponse`).
2. **User Persistence Repository** (`backend/app/repositories/user_repository.py`): Encapsulated infrastructure-level PostgreSQL operations including lookup by primary key UUID, case-insensitive normalized email lookup/existence checks, and salted bcrypt password hashing via `backend/app/core/security.py` prior to persistence.
3. **Authentication Service** (`backend/app/services/auth_service.py`): Orchestrates user registration with duplicate detection, timing-safe credential authentication with uniform error messages to prevent email enumeration attacks, inactive account gating, and JWT access token issuance utilizing the user's UUID as the token subject.
4. **Comprehensive Test Suites**: 22 new tests spanning schema validation unit tests, service unit tests with mock repository, and live PostgreSQL integration tests using isolated savepoints. Total passing tests increased from **215 to 237**.

---

## 2. Architectural Boundaries & Security Posture

In accordance with Phase 2 specifications:
- **No API Endpoints Added**: Endpoints (`/auth/register`, `/auth/login`, `/auth/me`) and FastAPI security dependencies (`OAuth2PasswordBearer`, `get_current_user`) were intentionally deferred to Tasks 4–6.
- **Zero AI Logic Modifications**: Chinmay's AI logic, prompts, `DecisionEngine`, `LangGraph`, and `CurioEngine` remain untouched.
- **Credential Hygiene**: Plaintext passwords are never logged, never stored, and never returned in response models. Password hashes are strictly excluded from API-facing schemas (`UserResponse`).
- **Timing & Enumeration Resistance**: `authenticate_user()` issues identical generic exceptions (`"Invalid email or password"`) regardless of whether the user does not exist or provided an incorrect password.
- **Single Source of Truth**: Reuses existing `SECRET_KEY`, `ALGORITHM`, and JWT utilities from `backend/app/core/security.py` and `backend/app/core/config.py`.

---

## 3. Component Details

### 3.1 Pydantic Schemas

#### `backend/app/schemas/user.py`
```python
class UserCreate(BaseModel):
    """Schema for user registration requests."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")

class UserResponse(BaseModel):
    """Safe user representation — never exposes hashed_password."""
    id: UUID
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```
- **Validation**: Enforces valid RFC email syntax via Pydantic `EmailStr` and a minimum of 8 characters for passwords.
- **Safety**: `UserResponse` contains no `hashed_password` or `password` fields and supports direct ORM model parsing via `ConfigDict(from_attributes=True)`.

#### `backend/app/schemas/auth.py`
```python
class UserLogin(BaseModel):
    """Schema for user login / credential submission."""
    email: EmailStr
    password: str

class Token(BaseModel):
    """JWT access token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
```

### 3.2 User Repository (`backend/app/repositories/user_repository.py`)

- **`_normalize_email(email: str) -> str`**: Lowercases and strips email strings so lookups and registrations are canonicalized.
- **`get_by_id(db: Session, user_id: UUID) -> Optional[User]`**: Primary key query.
- **`get_by_email(db: Session, email: str) -> Optional[User]`**: Queries using the normalized email.
- **`exists_by_email(db: Session, email: str) -> bool`**: Returns boolean existence indicator.
- **`create(db: Session, email: str, password: str) -> User`**:
  - Pre-checks email existence.
  - Automatically hashes the password using `backend.app.core.security.get_password_hash()`.
  - Wraps `db.commit()` with `IntegrityError` handling to ensure duplicate violations raise clean `ValueError` exceptions with automatic rollback.

### 3.3 Authentication Service (`backend/app/services/auth_service.py`)

- **`register_user(db: Session, user_in: UserCreate) -> UserResponse`**:
  - Validates duplicate email constraint.
  - Delegates persistence to `UserRepository`.
  - Returns sanitized `UserResponse`.
- **`authenticate_user(db: Session, email: str, password: str) -> User`**:
  - Retrieves user by email.
  - Verifies password hash using `verify_password()`.
  - Checks `user.is_active` status.
  - Raises uniform `ValueError("Invalid email or password")` on any credential failure.
- **`create_user_access_token(user: User) -> Token`**:
  - Signs a JWT access token with the user's UUID string as `sub`.
  - Returns `Token` with `access_token`, `token_type="bearer"`, and `expires_in` in seconds.

---

## 4. Test Verification & Results

### 4.1 Schema Unit Tests (`backend/tests/core/test_user_schemas.py`)
- `test_user_create_valid`: Valid email and password pass validation.
- `test_user_create_invalid_email`: Syntax errors rejected by `EmailStr`.
- `test_user_create_password_too_short`: Passwords < 8 characters rejected.
- `test_user_create_password_minimum_8_chars_allowed`: 8-char password boundary accepted.
- `test_user_response_fields_and_no_password_exposed`: Excludes password attributes on dump.
- `test_user_response_from_orm_object`: Safely converts ORM object without leaking hash.
- `test_user_login_valid`: Valid credentials accepted.
- `test_user_login_invalid_email`: Invalid email rejected.
- `test_token_schema`: Token schema types and default values.
**Result**: 9 passed in 0.27s.

### 4.2 AuthService Unit Tests (`backend/tests/services/test_auth_service.py`)
- `test_register_user_success`: Successful registration returning `UserResponse`.
- `test_register_user_duplicate_email_rejected`: Duplicate email raises `ValueError`.
- `test_authenticate_user_success`: Matches valid password hash and returns `User`.
- `test_authenticate_user_wrong_password_rejected`: Uniform error message on mismatch.
- `test_authenticate_user_unknown_email_rejected`: Uniform error message on missing email.
- `test_authenticate_user_inactive_account_rejected`: Inactive user blocked from login.
- `test_create_user_access_token_subject_and_type`: JWT encodes user UUID in `sub` claim.
**Result**: 7 passed in 2.81s.

### 4.3 Database Integration Tests (`backend/tests/integration/test_user_auth_integration.py`)
- `test_user_repository_create_and_lookup_by_email`: Persists bcrypt hash in PostgreSQL, normalizes mixed-case lookups.
- `test_user_repository_get_by_id`: UUID retrieval against live DB.
- `test_user_repository_exists_by_email`: Existence query verification.
- `test_user_repository_duplicate_email_rejected`: Prevents duplicate inserts.
- `test_auth_service_end_to_end_registration_and_login`: Full flow (register, authenticate, token issuance) in PostgreSQL.
- `test_auth_service_inactive_user_rejected`: Inactive DB user blocked from authentication.
**Result**: 6 passed in 4.51s.

### 4.4 Full Regression Test Run
```text
===================== 237 passed, 357 warnings in 29.04s ======================
```
- Total test count: **237 passed**.
- Regressions: **0**.

---

## 5. Next Steps for Phase 2 Task 4

Task 3 provides the complete domain and service foundation required for Task 4:
- In Task 4, FastAPI authentication endpoints (`/auth/register`, `/auth/login`, `/auth/me`) will be created and wired to `AuthService`.
- FastAPI dependencies (`OAuth2PasswordBearer`, `get_current_user`, `get_current_active_user`) will decode the JWT issued by `AuthService` and resolve the authenticated `User` from `UserRepository`.
