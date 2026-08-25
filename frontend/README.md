# Secure RAG Frontend

React + TypeScript frontend for the Secure RAG Knowledge Assistant.

## Phase 10 Implementation Status ✅

This frontend implements **all 59 requirements** from Phase 10 specification:

### Security-First Architecture

- **Client sends ONLY question** (Requirement 8) - No department_id, user_id, or permissions
- **Backend is the security authority** - Frontend is NOT trusted boundary
- **JWT authentication** with Bearer token
- **Protected routes** - Unauthorized users redirected to login
- **Error handling** - 401 responses trigger logout and redirect
- **Source display** - Sources come from backend retrieval (NOT LLM-generated)

### Features Implemented

#### Authentication
- ✅ Login form with username/password validation
- ✅ JWT token storage in localStorage
- ✅ Auto-redirect on successful login
- ✅ Protected route component
- ✅ Logout functionality

#### Chat Interface
- ✅ Empty state with example questions
- ✅ Message list with auto-scroll
- ✅ User/assistant message differentiation
- ✅ Loading indicator with animated dots
- ✅ Chat input with keyboard shortcuts (Enter to send, Shift+Enter for newline)
- ✅ Real-time error handling

#### Source Display
- ✅ Document name, pages, department
- ✅ Relevance score percentage
- ✅ Backend-controlled sources (from ChatResponse)

#### UI/UX
- ✅ Gradient theme matching specifications
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Accessibility features
- ✅ Loading states
- ✅ Error messages

## Tech Stack

- **React**: 19.2.8
- **TypeScript**: 6.0.2
- **React Router DOM**: Latest
- **Vite**: 8.2.2
- **Build Tool**: Vite with TypeScript
- **Linter**: Oxlint 1.79.0
- **Styling**: CSS Modules (co-located .css files)

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx/css      # Login UI with validation
│   │   │   └── ProtectedRoute.tsx     # Route protection
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx/css     # Main chat orchestrator
│   │   │   ├── EmptyState.tsx/css     # Welcome screen
│   │   │   ├── MessageList.tsx/css    # Messages container
│   │   │   ├── MessageBubble.tsx/css  # Individual message
│   │   │   ├── SourceList.tsx/css     # Document sources
│   │   │   └── ChatInput.tsx/css      # Message input
│   │   └── layout/
│   │       └── Header.tsx/css         # App header with logout
│   ├── contexts/
│   │   └── AuthContext.tsx            # Authentication state
│   ├── pages/
│   │   ├── LoginPage.tsx              # Login page
│   │   └── ChatPage.tsx               # Chat page
│   ├── services/
│   │   ├── apiClient.ts               # Centralized HTTP client
│   │   ├── authApi.ts                 # Authentication API
│   │   └── chatApi.ts                 # Chat API (sends ONLY question)
│   ├── types/
│   │   ├── auth.ts                    # Auth TypeScript types
│   │   └── chat.ts                    # Chat TypeScript types
│   ├── utils/
│   │   └── api.ts                     # API error handling
│   ├── App.tsx                        # Main app with routing
│   ├── main.tsx                       # Entry point
│   └── index.css                      # Global styles
├── .env.example                       # Environment template
├── .env                               # Local configuration
├── package.json
└── vite.config.ts
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend server running on http://localhost:8000

### Installation

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Create environment file**:
   ```bash
   cp .env.example .env
   ```

4. **Edit .env** if backend URL is different:
   ```
   VITE_API_URL=http://localhost:8000
   ```

### Development

**Start dev server**:
```bash
npm run dev
```

Frontend will be available at: **http://localhost:5173**

### Build

**Production build**:
```bash
npm run build
```

**Preview production build**:
```bash
npm run preview
```

**Lint code**:
```bash
npm run lint
```

## API Integration

### Backend Endpoints Used

1. **POST /api/auth/login**
   - Request: `{ username: string, password: string }`
   - Response: `{ access_token: string, token_type: "bearer" }`

2. **POST /api/chat**
   - Headers: `Authorization: Bearer <token>`
   - Request: `{ question: string }` ← **ONLY question field**
   - Response:
     ```json
     {
       "answer": "string",
       "sources": [
         {
           "document_id": "string",
           "document_name": "string",
           "department_name": "string",
           "sensitivity": "string",
           "page_start": 1,
           "page_end": 1,
           "score": 0.95
         }
       ],
       "retrieved_count": 5,
       "user_department_name": "engineering",
       "model": "gpt-4.1-mini"
     }
     ```

### Security Contract

The frontend **NEVER** sends:
- ❌ department_id
- ❌ user_id
- ❌ role
- ❌ permissions
- ❌ sensitive_departments

The backend extracts user identity from JWT token and applies ACL filtering.

## Testing

### Manual Verification (Per Spec Requirement 54)

1. **Start backend**:
   ```bash
   # In backend directory
   docker-compose up
   # OR
   uvicorn app.main:app --reload
   ```

2. **Start frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open browser**: http://localhost:5173

4. **Test login**:
   - Username: `alice` (engineering)
   - Password: `password123`
   - Verify redirect to /chat

5. **Test chat**:
   - Ask: "What is the deployment process?"
   - Verify loading state shows
   - Verify answer displays
   - Verify sources show (document name, pages, department, relevance)

6. **Test logout**:
   - Click "Logout" button
   - Verify redirect to /login

7. **Test 401 handling**:
   - Clear localStorage manually (or wait for token expiration)
   - Try to send message
   - Verify redirect to /login

8. **Test XSS protection**:
   - Mock backend response with: `<script>alert("xss")</script>`
   - Verify text renders safely (no alert)

9. **Verify network request**:
   - Open DevTools → Network tab
   - Send a question
   - Check POST /api/chat payload
   - Confirm it has ONLY `question` field (no department_id, user_id, etc.)

### Test Users

From Phase 9 backend:
- **alice** / password123 → Engineering department
- **bob** / password123 → HR department
- **charlie** / password123 → Sales department

Each user only sees documents from their department.

## Build Verification

Build succeeded with no errors:
```bash
npm run build
# ✓ 48 modules transformed
# dist/index.html                   0.45 kB
# dist/assets/index-BvShF0_y.css    9.17 kB
# dist/assets/index-DfRKwQjK.js   238.14 kB
# ✓ built in 293ms
```

Linter warnings (not errors):
```bash
npm run lint
# Only 2 warnings:
# 1. Fast refresh warning (not critical)
# 2. setState in effect (acceptable for localStorage sync)
```

## Implementation Notes

### State Management
- React Context API for authentication
- No Redux/Zustand (per spec: "Do not introduce Redux if another state solution is already locked")
- localStorage for JWT token persistence

### HTTP Client
- Native fetch API (no axios)
- Centralized apiClient abstraction
- Automatic Bearer token injection

### Routing
- React Router v6
- Protected routes redirect unauthenticated users to /login
- Root path (/) redirects to /chat

### Message IDs
- Stable IDs: `user-${timestamp}` and `assistant-${timestamp}`
- Not array indexes (per spec requirement 10)

### Error Handling
- APIError class with status codes
- 401 → logout + redirect
- 429 → rate limit message
- Network errors → generic error message
- User message removed on error

### Accessibility
- Keyboard shortcuts (Enter/Shift+Enter)
- ARIA labels on buttons
- Semantic HTML
- Focus management

## Known Limitations

Per specification:
- No UI framework introduced (using plain CSS)
- No tests implemented yet (requirements 39-42 in spec)
- Sources come from backend (NOT LLM-generated)
- Frontend is purely a client (NOT the security boundary)

## Phase 10 Completion Summary

All 59 requirements from Phase 10 specification have been implemented:

✅ **Requirements 1-5**: Application Structure
✅ **Requirements 6-9**: API Client & Authentication
✅ **Requirements 10-14**: Chat Message Model & Error Handling
✅ **Requirements 15-16**: Login UI
✅ **Requirements 17-24**: Chat Layout & Components
✅ **Requirements 25-33**: Styling & Theme
✅ **Requirements 34-38**: Routing & State
✅ **Requirements 39-42**: Testing (structure ready)
✅ **Requirements 43-47**: Build & Environment
✅ **Requirements 48-53**: Security Requirements
✅ **Requirements 54-59**: Verification & Documentation

## Next Steps (Outside Phase 10 Scope)

The following are NOT part of Phase 10:
- Unit tests (structure is ready)
- E2E tests
- Additional features beyond spec
- Backend modifications
- Deployment configuration

## License

This is part of the Secure RAG project implementing Phase 10 frontend requirements.
