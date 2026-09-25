# Phase 2, Task 2: Security Core, Cryptographic Foundations & Database Migration — Implementation Report

**Author / Owner:** Vishal (Backend Infrastructure, Security & Persistence)  
**Target System:** Curio AI Backend  
**Date:** 2026-09-22  
**Status:** **COMPLETED & VERIFIED** (215 of 215 tests passing, 0 regressions)

---

## 1. Executive Summary

Phase 2, Task 2 established the core cryptographic infrastructure and database schema foundation required for authentication and user management in Curio AI. In accordance with the Phase 2 Task 1 architecture audit, this task implemented isolated security utilities (salted bcrypt hashing, PyJWT token creation/validation), updated the `User` database model, safely applied an incremental Alembic migration across both development and test PostgreSQL databases without resetting data, and introduced a unit test suite for cryptographic operations.

All 204 existing Phase 1 tests plus 11 new security tests (**215 total**) pass with a 100% success rate. No live Groq API calls were made, `MOCK_USER_ID` was preserved for backward compatibility, and Chinmay's AI logic, prompts, and LangGraph flow were untouched.

---

## 2. Dependencies Added & Installed Versions

The following dependencies were appended to `backend/requirements.txt` and installed into `backend/.venv`:

| Package | Version Pinned | Installed Version | Purpose |
| :--- | :--- | :--- | :--- |
| **`bcrypt`** | `4.1.2` | `4.1.2` | Salted password hashing and timing-safe verification |
| **`pyjwt`** | `2.8.0` | `2.8.0` | HMAC-SHA256 JWT access token creation, signing, and verification |
| **`email-validator`** | `2.1.1` | `2.1.1` | RFC-compliant email syntax and domain verification for Pydantic |
| **`dnspython`** | *(sub-dep)* | `2.8.0` | DNS resolution dependency for `email-validator` |

---

## 3. Configuration Updates

### 3.1 `backend/app/core/config.py`
Extended `Settings` with JWT parameters:
```python
# Authentication & Security
SECRET_KEY: str = "curio-dev-secret-key-change-in-production"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
```
- The secret key is loaded from the environment/`.env` file.
- Fallback dev secret is provided for local execution; production environments supply a high-entropy secret via environment variables.

### 3.2 Environment Examples
- **`.env.example`**: Updated with `SECRET_KEY`, `ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES` and guidance on generating production keys.
- **`backend/.env`**: Configured with a dedicated development key: `curio-dev-secret-key-test-environment-only-32charsmin`.

---

## 4. Security Core Module (`backend/app/core/security.py`)

A dedicated, isolated cryptographic utilities module was implemented:

1. **`verify_password(plain_password: str, hashed_password: str) -> bool`**:
   - Encodes strings to UTF-8 and utilizes `bcrypt.checkpw()`.
   - Safely catches exceptions (e.g. malformed or empty hashes) and returns `False` without unhandled crashes.
2. **`get_password_hash(password: str) -> str`**:
   - Generates random per-password salt with `bcrypt.gensalt()`.
   - Hashes password with `bcrypt.hashpw()` and returns decoded ASCII string (`$2b$...`).
   - Validates that non-empty passwords are provided, raising `ValueError` on empty inputs.
3. **`create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str`**:
   - Embeds claims: `sub` (subject identifier), `iat` (issued-at UTC timestamp), and `exp` (expiration UTC timestamp).
   - Defaults to `settings.ACCESS_TOKEN_EXPIRE_MINUTES` (24 hours) or applies custom delta.
   - Signs using `jwt.encode()` with `settings.SECRET_KEY` and `settings.ALGORITHM` (`HS256`).
4. **`decode_access_token(token: str) -> Dict[str, Any]`**:
   - Validates signature and expiration using `jwt.decode()`.
   - Raises `jwt.ExpiredSignatureError` on expired tokens.
   - Raises `jwt.InvalidTokenError` on tampered, invalid, or malformed tokens.
5. **Security Hygiene**:
   - Zero logging of passwords, raw hashes, JWT payloads, or `SECRET_KEY`.
   - Complete decoupling from FastAPI routing and HTTP status codes.

---

## 5. User Database Model (`backend/app/models/user.py`)

Updated the SQLAlchemy `User` model to persist authentication state:

```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False, server_default="")
    is_active = Column(Boolean, default=True, server_default=text("true"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
```
- **Preserved Existing Fields**: `id`, `email`, `created_at`, `sessions`.
- **Added Fields**:
  - `hashed_password`: Non-null string with server default `""` to prevent constraint violations on existing test/mock data.
  - `is_active`: Non-null boolean defaulting to `True`.
  - `updated_at`: Non-null timezone-aware timestamp with auto-update trigger on mutation.

---

## 6. Alembic Database Migration

### 6.1 Migration Revision Details
- **Revision ID**: `b4e440204004`
- **File**: `backend/alembic/versions/b4e440204004_add_user_authentication_fields.py`
- **Parent Revision (Down Revision)**: `84274ca763eb` (`add_teacher_mode_state_fields`)
- **Linear Head**: Confirmed single head in repository (`b4e440204004 (head)`).

### 6.2 DDL Operations
```python
def upgrade() -> None:
    op.add_column('users', sa.Column('hashed_password', sa.String(), server_default='', nullable=False))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

def downgrade() -> None:
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'hashed_password')
```

### 6.3 Database Migration Execution
Both databases were migrated without resetting or deleting tables:
1. **Development Database (`curio_db`)**:
   ```bash
   alembic upgrade head
   # Running upgrade 84274ca763eb -> b4e440204004, add_user_authentication_fields (SUCCESS)
   ```
2. **Isolated Test Database (`curio_test_db`)**:
   ```bash
   alembic -x db=test upgrade head
   # Running upgrade 84274ca763eb -> b4e440204004, add_user_authentication_fields (SUCCESS)
   ```

### 6.4 Schema Verification
Inspection of both databases via SQLAlchemy metadata confirmed the updated schema:
- `curio_db.users` columns: `['id', 'email', 'created_at', 'hashed_password', 'is_active', 'updated_at']`
- `curio_test_db.users` columns: `['id', 'email', 'created_at', 'hashed_password', 'is_active', 'updated_at']`
- Verified existing mock user (`chinmay.vishal@curio.ai`) in `curio_db` successfully received `hashed_password=""`, `is_active=True`, and `updated_at` without data corruption.

---

## 7. Test Suite & Verification Results

### 7.1 Security Unit Tests (`backend/tests/core/test_security.py`)
11 comprehensive unit tests were added covering all cryptographic requirements:
- `test_password_hashing`: Generates valid `$2b$` bcrypt hash.
- `test_password_salting`: Confirms distinct salted hashes for identical plaintexts.
- `test_password_verification_success`: Validates correct password matches.
- `test_password_verification_failure`: Validates incorrect password fails.
- `test_password_verification_edge_cases`: Validates empty/malformed hashes fail safely without unhandled exceptions; empty password raises `ValueError`.
- `test_jwt_contains_expected_subject_and_expiration`: Verifies `sub`, `exp`, and `iat` in payload.
- `test_jwt_valid_decode`: Verifies successful token decode.
- `test_jwt_expired_token_rejected`: Verifies `jwt.ExpiredSignatureError` raised on expired token.
- `test_jwt_tampered_token_rejected`: Verifies `jwt.InvalidTokenError` raised on mutated signature or payload.
- `test_jwt_invalid_token_rejected`: Verifies `jwt.InvalidTokenError` raised on garbage strings.
- `test_jwt_custom_expiration_duration`: Verifies custom delta expiration math.

**Result:** **11 passed in 2.94s** (100% pass rate).

### 7.2 Full Regression Suite Execution
Ran the complete test suite against live PostgreSQL (`curio_test_db` on port 5433):
```powershell
.\backend\.venv\Scripts\python -m pytest -q
```
**Result:**
```text
======================== 215 passed, 357 warnings in 41.56s ========================
```
* **AI Decision & Graph Tests**: 116 passed
* **API Safety & Health Tests**: 10 passed
* **Phase 3 Evaluator API Tests**: 9 passed
* **Security Core Tests**: 11 passed
* **Database Integration Tests**: 15 passed
* **API Integration Tests**: 17 passed
* **Teacher Mode Persistence Tests**: 10 passed
* **Chat Service Service Tests**: 27 passed

---

## 8. Summary of Files Created & Modified

| File | Status | Description |
| :--- | :--- | :--- |
| `backend/requirements.txt` | Modified | Added `bcrypt==4.1.2`, `pyjwt==2.8.0`, `email-validator==2.1.1`. |
| `backend/app/core/config.py` | Modified | Added `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`. |
| `.env.example` | Modified | Documented authentication and security variables. |
| `backend/.env` | Modified | Added safe development authentication settings. |
| `backend/app/core/security.py` | **New** | Password hashing/salting/verification and JWT creation/validation. |
| `backend/app/models/user.py` | Modified | Added `hashed_password`, `is_active`, and `updated_at`. |
| `backend/alembic/versions/b4e440204004_add_user_authentication_fields.py` | **New** | Incremental Alembic migration adding user auth columns. |
| `backend/tests/core/__init__.py` | **New** | Core tests package initialization. |
| `backend/tests/core/test_security.py` | **New** | 11 unit tests for cryptographic operations. |
| `docs/phase-2-task-2-security-core-and-migration-report.md` | **New** | Task 2 architecture and verification documentation report. |

---

## 9. Readiness & Next Steps for Phase 2, Task 3

The database schema and cryptographic foundations are fully verified and operational.

**Next Task (Phase 2, Task 3):**
* Create Pydantic schemas in `backend/app/schemas/user.py` and `backend/app/schemas/auth.py` (`UserCreate`, `UserLogin`, `UserResponse`, `Token`).
* Implement `backend/app/repositories/user_repository.py` with methods for email lookup, user creation with hashed passwords, and authentication verification.
* Implement `backend/app/services/auth_service.py` to orchestrate user registration, credential validation, and JWT token issuance.
