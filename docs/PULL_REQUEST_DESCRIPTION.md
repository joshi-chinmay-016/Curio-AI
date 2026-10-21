# PR Title: `feat(core): real user data integration, auth stability, dynamic settings & profile enhancements`

## Pull Request Summary

### Context & Objective
This pull request completely removes mock, placeholder, and hardcoded demo learner data from Curio AI across the entire frontend and client stores. It guarantees that all user details, statistics, practice queues, knowledge gaps, and learning sessions represent authentic data retrieved dynamically from backend APIs and active learning sessions.

In addition, it resolves authentication session drops and view re-mount flickering during navigation, introduces full name capture during user registration, hides the profile menu on the public landing page, and introduces the interactive Settings & Preferences suite with theme toggling.

---

## Key Changes

### 1. Mock Data Eradication & Real Data Pipelines
- **Purged Hardcoded Settings & Stats**:
  - `frontend/stores/settingsStore.ts`: Replaced default mock values (`Chinmay Joshi`, `learner@curio.ai`, 48 concepts mastered, 17 gaps resolved, 23 sessions) with clean zeroed counters and empty profile defaults.
  - Added dynamic `syncRealStats()` action that queries `/sessions` and `/users/me/progress` to aggregate genuine session counts, voice dialogue minutes, resolved misconceptions, concepts mastered, and Feynman inquiry streaks.
  - Added automatic cache sanitization in `initSettings()` to purge legacy mock user tokens and profile relics from `localStorage`.
- **Purged Mock Practice Queues**:
  - `frontend/services/historyService.ts`: Replaced static sample queue items with `curio_practice_queue` persistence scoped to the real user's local session.
- **Purged Mock Gap Reports**:
  - `frontend/services/gapReportService.ts`: Removed fallback injection of fake sessions (`session_mock_sort`, `session_mock_trees`). Unauthenticated or uncompleted sessions cleanly return `null` instead of faking data.
  - `frontend/app/session/[id]/report/page.tsx`: Added an empty-state card redirecting learners back to the Dashboard when a session report has not yet been generated.
- **Purged Demo Logins**:
  - Removed "INSTANT DEMO ACCESS" and "CONTINUE IN DEMO MODE" fallbacks from `frontend/app/login/page.tsx` and `frontend/app/register/page.tsx`. All users sign in through authenticated backend pipelines.

### 2. Authentication Stability & Session Persistence
- **Hydration Fix**:
  - `frontend/stores/authStore.ts`: Hydrated authentication state synchronously from `localStorage` upon store creation, preventing `isLoading` state flickering on page load.
  - Made `initAuth()` idempotent: if an active user and token already exist, execution returns immediately without unmounting components.
  - Network timeouts no longer clear auth tokens; only explicit HTTP 401 Unauthorized responses invalidate sessions.
- **Protected Route Smoothing**:
  - `frontend/components/curio/auth/ProtectedRoute.tsx`: Added client-mounted gating and direct rendering when authenticated to eliminate page re-prompts on navigation.

### 3. User Identity & Registration
- **Full Name Input**:
  - `frontend/app/register/page.tsx`: Added Full Name input field with real-time validation alongside email and password.
  - `backend/app/schemas/user.py` & `frontend/types/auth.ts`: Added `name` attribute to registration credentials, schema definitions, and response models.
  - Profile dropdown and dashboard now prioritize the user's real name before falling back to their email handle.

### 4. Navigation & Profile Isolation
- **Landing Page Clarity**:
  - `frontend/components/curio/CurioNav.tsx`: Profile dropdown button is suppressed on the public landing page (`/`). It is only visible inside authenticated application pages (`/dashboard`, `/audio-learning`, `/topics`, `/settings`, etc.).
- **Profile Popover & Settings Integration**:
  - `frontend/components/curio/profile/ProfileDropdown.tsx`: Displays live metrics computed from real user sessions and provides direct links to the new Settings suite.

---

## Verification & Testing
1. **Frontend Tests**:
   - `npm test` executed across all suites:
     - 11/11 tests passing in `interactive-audio-learning.test.ts`.
     - 19/19 tests passing in `audio-character-sync.test.ts`.
     - 20/20 tests passing in `history-auth-integration.test.ts`.
2. **Backend API Validation**:
   - Tested real user registration: `POST /api/v1/auth/register` -> `201 Created` with live PostgreSQL database connection.
   - Tested credential authentication: `POST /api/v1/auth/login` -> `200 OK` issuing authentic JWT bearer token.
   - Tested profile retrieval: `GET /api/v1/auth/me` -> `200 OK` with valid user payload.
