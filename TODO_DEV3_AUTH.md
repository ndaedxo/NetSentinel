# Developer 3 TODO: Security & Integration

**Developer**: Security & Integration Specialist  
**Focus**: Authentication & API Security  
**Timeline**: 2 weeks

---

## Week 1: Authentication Infrastructure

### Day 1: Setup & Planning (Monday)

#### Morning: Team Meeting
- [ ] Attend interface definition meeting (ALL 3 developers)
- [ ] Agree on IAuthProvider interface contract
- [ ] Understand API security requirements
- [ ] Set up development environment
- [ ] Create feature branch: `feature/auth`

#### Afternoon: Architecture & Design
- [ ] Design authentication architecture
- [ ] Design user management system
- [ ] Plan JWT token management
- [ ] Document security requirements
- [ ] Create initial file structure

---

### Day 2: Authentication Manager (Tuesday)

#### Morning: Core Auth Logic
- [ ] Create `src/netsentinel/security/auth_manager.py`
- [ ] Implement login/logout logic
- [ ] Implement password hashing (bcrypt)
- [ ] Add user validation
- [ ] Implement authentication flow

#### Afternoon: User Validation
- [ ] Implement username/password validation
- [ ] Add failed login tracking
- [ ] Implement account lockout logic
- [ ] Add authentication logging

**Key Files**:
```
src/netsentinel/security/auth_manager.py  ← NEW
```

**Success Criteria**:
- Users can authenticate
- Passwords properly hashed
- Failed login attempts tracked
- Security logs generated

---

### Day 3: JWT Token Manager (Wednesday)

#### Morning: Token Generation
- [ ] Create `src/netsentinel/security/token_manager.py`
- [ ] Implement JWT token generation
- [ ] Add token signing with secret key
- [ ] Implement token expiration
- [ ] Add token claims management

#### Afternoon: Token Validation
- [ ] Implement token validation
- [ ] Add token signature verification
- [ ] Implement token expiration checking
- [ ] Add token refresh logic
- [ ] Implement token blacklisting

**Key Files**:
```
src/netsentinel/security/token_manager.py  ← NEW
```

**Success Criteria**:
- Tokens generated correctly
- Tokens validated properly
- Expiration works
- Refresh logic functional

---

### Day 4: User Management (Thursday)

#### Morning: User Store
- [ ] Create `src/netsentinel/security/user_store.py`
- [ ] Implement user CRUD operations
- [ ] Add user storage (start with in-memory/JSON)
- [ ] Implement user lookup
- [ ] Add password management

#### Afternoon: Role Management
- [ ] Implement basic role system
- [ ] Add role assignment
- [ ] Implement permission checking foundation
- [ ] Add user session management

**Key Files**:
```
src/netsentinel/security/user_store.py  ← NEW
```

**Success Criteria**:
- Users can be created/retrieved
- Passwords stored securely
- Roles can be assigned
- User sessions tracked

---

### Day 5: Testing & Validation (Friday)

#### All Day: Unit Tests & Validation
- [ ] Create `src/tests/test_auth_manager.py`
- [ ] Create `src/tests/test_token_manager.py`
- [ ] Create `src/tests/test_user_store.py`
- [ ] Test authentication flow
- [ ] Test token generation/validation
- [ ] Test password hashing
- [ ] Validate security requirements

**Success Criteria**:
- All unit tests passing
- >90% test coverage for auth components
- Authentication secure
- No security vulnerabilities found

---

## Week 2: API Integration & Security

### Day 6: Security Middleware (Monday)

#### Morning: Auth Middleware
- [ ] Create `src/netsentinel/security/middleware.py`
- [ ] Implement authentication middleware
- [ ] Add token validation in requests
- [ ] Implement user context injection
- [ ] Add protected route decorator

#### Afternoon: API Integration
- [ ] Update `api_server.py` to use auth middleware
- [ ] Add authentication decorator to all routes
- [ ] Implement unauthorized response handling
- [ ] Add security headers
- [ ] Test protected endpoints

**Key Files**:
```
src/netsentinel/security/middleware.py  ← NEW
src/netsentinel/processors/api_server.py  ← Integration
Lines to add:
- Import auth middleware
- Add @require_auth decorator to routes
- Add /auth/login endpoint
```

---

### Day 7: API Endpoints (Tuesday)

#### Morning: Auth Endpoints
- [ ] Add `/auth/login` endpoint to api_server.py
- [ ] Add `/auth/logout` endpoint
- [ ] Add `/auth/refresh` endpoint
- [ ] Implement request/response models
- [ ] Add input validation

#### Afternoon: User Management Endpoints
- [ ] Add `/auth/users` (list users) endpoint
- [ ] Add `/auth/me` (current user info) endpoint
- [ ] Implement proper authorization checks
- [ ] Add rate limiting for auth endpoints

**Key Files**:
```
src/netsentinel/processors/api_server.py  ← Add auth endpoints
```

---

### Day 8: WebSocket Security Integration (Wednesday)

#### Morning: WebSocket Auth Decorator
- [ ] Create WebSocket authentication decorator
- [ ] Add connection-time authentication
- [ ] Implement token validation for WebSocket
- [ ] Add user context for WebSocket connections

**Important**: Provide integration point for Dev 2's WebSocket server

#### Afternoon: Authorization Checks
- [ ] Implement role-based access control (basic)
- [ ] Add permission checking
- [ ] Implement audit logging
- [ ] Add security monitoring

---

### Day 9: Integration Testing (Thursday)

#### All Day: End-to-End Testing
- [ ] Create `src/tests/integration/test_auth_flow.py`
- [ ] Test login → API call flow
- [ ] Test WebSocket authentication
- [ ] Test token refresh
- [ ] Test unauthorized access handling
- [ ] Security testing (injection, token manipulation)

**Success Criteria**:
- Complete auth flow works
- All APIs secured
- WebSocket auth integration works
- Security tests pass
- No vulnerabilities found

---

### Day 10: Security Audit & Documentation (Friday)

#### Morning: Security Audit
- [ ] Review authentication implementation
- [ ] Check for common vulnerabilities
- [ ] Test password handling
- [ ] Validate token security
- [ ] Check for information leakage

#### Afternoon: Documentation & Demo
- [ ] Document authentication architecture
- [ ] Create security guide
- [ ] Document API usage with auth
- [ ] Prepare demo for team
- [ ] Final code review

---

## Critical Implementation Details

### Authentication Manager

```python
# src/netsentinel/security/auth_manager.py (NEW)

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional

class AuthManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
    def hash_password(self, password: str) -> str:
        """Hash a password for storage"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash"""
        return self.pwd_context.verify(password, hashed)
    
    async def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return token"""
        # Get user from store
        user = await self.user_store.get_user(username)
        if not user:
            return None
        
        # Verify password
        if not self.verify_password(password, user.hashed_password):
            return None
        
        # Generate token
        token = self.create_access_token(user.id)
        return token
    
    def create_access_token(self, user_id: str, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
            
        to_encode = {"sub": user_id, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
        
    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return user_id"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload.get("sub")
        except JWTError:
            return None
```

---

## Key Files & Responsibilities

### New Files to Create
```
src/netsentinel/security/
├── auth_manager.py     ← Day 2
├── token_manager.py    ← Day 3
├── user_store.py       ← Day 4
└── middleware.py       ← Day 6
```

### Files to Modify
```
src/netsentinel/processors/
└── api_server.py       ← Days 6-7 (Add auth endpoints and decorators)
```

### Test Files to Create
```
src/tests/
├── test_auth_manager.py   ← Day 5
├── test_token_manager.py  ← Day 5
├── test_user_store.py     ← Day 5
└── integration/
    └── test_auth_flow.py  ← Day 9
```

---

## API Security Implementation

### Securing API Routes

**File**: `api_server.py`

**Add imports**:
```python
from ..security.middleware import require_auth, get_current_user
```

**Add auth endpoints**:
```python
# NEW endpoint
@self.app.post("/auth/login")
async def login(credentials: LoginCredentials):
    """User login endpoint"""
    token = await auth_manager.authenticate(
        credentials.username, 
        credentials.password
    )
    if not token:
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}

# Update existing endpoints
@self.app.get("/threats")
@require_auth  ← ADD THIS DECORATOR
async def get_threats(...):
    # Existing code
    pass
```

---

## Daily Coordination

### Daily Standup (10:00 AM)
- What you completed yesterday
- What you're working on today
- Any blockers

### Merge Strategy
```bash
# Every afternoon (4:00 PM)
git checkout develop
git pull origin develop
git checkout feature/auth
git merge develop
git push origin feature/auth

# You'll merge SECOND (after Dev 1, before Dev 2)
```

---

## Success Metrics

### Week 1 Goals
- [x] Authentication working
- [x] JWT tokens generated correctly
- [x] User management functional
- [x] Unit tests passing (>90% coverage)
- [x] Security requirements met

### Week 2 Goals
- [x] All API endpoints secured
- [x] Auth flow working end-to-end
- [x] Integration tests passing
- [x] WebSocket auth ready for integration
- [x] Security audit passed
- [x] Documentation complete

---

## Security Requirements

### Password Security
- [ ] Passwords hashed with bcrypt
- [ ] Salt included in hashing
- [ ] Minimum password complexity
- [ ] Password not logged or returned

### Token Security
- [ ] Tokens signed with strong secret
- [ ] Tokens expire appropriately (24 hours)
- [ ] Refresh token mechanism
- [ ] Token blacklisting for logout

### API Security
- [ ] All endpoints require authentication
- [ ] Rate limiting on auth endpoints
- [ ] Proper error messages (no info leakage)
- [ ] Security headers set correctly

---

## Authentication Flow

### Login Flow
```
1. User sends credentials to /auth/login
2. AuthManager validates credentials
3. TokenManager generates JWT token
4. Token returned to client
5. Client stores token
6. Client includes token in subsequent requests
```

### API Request Flow
```
1. Client sends request with token in Authorization header
2. Middleware validates token
3. User context extracted from token
4. Request processed with user context
5. Response returned
```

### WebSocket Flow
```
1. Client connects to WebSocket
2. Client sends auth message with token
3. WebSocket validates token (using Auth decorator)
4. Connection accepted or rejected
5. User context stored for connection
```

---

## Blockers & Risks

### Potential Blockers
- JWT secret key management
- Token storage on client side
- WebSocket authentication complexity

### Mitigation
- Use environment variables for secrets
- Document token storage best practices
- Provide clear integration points for WebSocket

---

## Notes

### Interface Contract (Agreed Day 1)
```python
class IAuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> Optional[str]:
        """Authenticate user and return token"""
        pass
    
    @abstractmethod
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token"""
        pass
```

### Coordination Points
- Day 1: Interface meeting with all 3 devs
- Day 6-7: Integration with api_server.py (auth decorators)
- Day 8: WebSocket auth integration point (decorator only)
- Daily: Sync with team about progress

### You DO NOT Need to Touch
- ML files (Dev 1 owns these)
- WebSocket implementation (Dev 2 owns this)
- Event analyzer logic (Dev 1 owns this)

---

## Default Users (For Testing)

### Initial Users to Create
```python
users = [
    {
        "username": "admin",
        "password": "admin123",  # Change in production!
        "role": "admin",
        "id": "user_admin"
    },
    {
        "username": "analyst",
        "password": "analyst123",
        "role": "analyst",
        "id": "user_analyst"
    }
]
```

**Important**: These are for development only. Production will have secure user management.

---

**Status**: Ready to start  
**Start Date**: [To be filled]  
**Target Completion**: 2 weeks from start

