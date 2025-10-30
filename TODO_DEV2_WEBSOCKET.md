# Developer 2 TODO: Real-time Infrastructure (WebSocket)

**Developer**: Real-time Infrastructure Specialist  
**Focus**: WebSocket & Event Broadcasting  
**Timeline**: 2 weeks

---

## Week 1: Foundation & Core Implementation

### Day 1: Setup & Planning (Monday)

#### Morning: Team Meeting
- [ ] Attend interface definition meeting (ALL 3 developers)
- [ ] Agree on IWebSocketBroadcaster interface contract
- [ ] Understand event broadcasting requirements
- [ ] Set up development environment
- [ ] Create feature branch: `feature/websocket`

#### Afternoon: Architecture & Design
- [ ] Design WebSocket architecture
- [ ] Design event bus system
- [ ] Document connection management approach
- [ ] Plan subscription system
- [ ] Create initial file structure

---

### Day 2: WebSocket Manager Core (Tuesday)

#### Morning: Connection Management
- [ ] Create `src/netsentinel/processors/websocket_manager.py`
- [ ] Implement WebSocket connection pool
- [ ] Implement connection lifecycle management
- [ ] Add connection health checks
- [ ] Implement automatic reconnection logic

#### Afternoon: Subscription System
- [ ] Add channel subscription management
- [ ] Implement subscribe/unsubscribe
- [ ] Add client registry per channel
- [ ] Implement subscription validation

**Key Files**:
```
src/netsentinel/processors/websocket_manager.py  ← NEW
```

**Success Criteria**:
- Can manage WebSocket connections
- Subscribe/unsubscribe works
- Connection health checks pass

---

### Day 3: Event Bus System (Wednesday)

#### Morning: Event Bus Core
- [ ] Create `src/netsentinel/core/event_bus.py`
- [ ] Implement publish/subscribe pattern
- [ ] Add event routing by type
- [ ] Implement event filtering
- [ ] Add event serialization

#### Afternoon: Event Bus Integration
- [ ] Integrate with event types (Threat, Alert, Status)
- [ ] Add event transformation
- [ ] Implement event batching
- [ ] Add event metrics

**Key Files**:
```
src/netsentinel/core/event_bus.py  ← NEW
```

**Success Criteria**:
- Events can be published
- Subscribers receive events
- Event filtering works
- Metrics tracked

---

### Day 4: WebSocket Server (Thursday)

#### Morning: FastAPI WebSocket Integration
- [ ] Create `src/netsentinel/processors/websocket_server.py`
- [ ] Implement WebSocket endpoint
- [ ] Add WebSocket authentication integration point
- [ ] Implement message parsing
- [ ] Add error handling

#### Afternoon: Message Routing
- [ ] Implement message type routing
- [ ] Add subscription message handling
- [ ] Implement ping/pong for keepalive
- [ ] Add connection cleanup

**Key Files**:
```
src/netsentinel/processors/websocket_server.py  ← NEW
```

**Success Criteria**:
- Can connect via WebSocket
- Messages can be sent/received
- Ping/pong works
- Authentication ready for integration

---

### Day 5: Testing & Validation (Friday)

#### All Day: Unit Tests & Validation
- [ ] Create `src/tests/test_websocket_manager.py`
- [ ] Create `src/tests/test_websocket_server.py`
- [ ] Test connection management
- [ ] Test subscription handling
- [ ] Test event broadcasting
- [ ] Test reconnection logic
- [ ] Validate error handling

**Success Criteria**:
- All unit tests passing
- >90% test coverage for WebSocket components
- Can broadcast messages to multiple clients
- Connection failures handled gracefully

---

## Week 2: Integration & Event Broadcasting

### Day 6: Event Processor Integration (Monday)

#### Morning: Integrate with Event Processor
- [ ] Add websocket_manager to `refactored_event_processor.py`
- [ ] Initialize WebSocket manager in processor
- [ ] Add broadcast calls for threats
- [ ] Add broadcast calls for alerts
- [ ] Add broadcast calls for status changes

**Key Files**:
```
src/netsentinel/processors/refactored_event_processor.py  ← Integration
Lines to add:
- __init__: Initialize websocket_manager (~line 87)
- _process_event: Add broadcasts (~line 200-220)
```

**Important**: Only 10-15 lines of changes needed. No logic changes to event processing.

#### Afternoon: Testing Integration
- [ ] Create integration tests
- [ ] Test threat broadcasting
- [ ] Test alert broadcasting
- [ ] Test real-time updates
- [ ] Performance testing with multiple clients

---

### Day 7: Event Bus Integration (Tuesday)

#### Morning: Connect Event Bus to Processor
- [ ] Integrate event bus with processor
- [ ] Add event publishers for threats
- [ ] Add event publishers for alerts
- [ ] Implement event streaming
- [ ] Add event batching

#### Afternoon: Performance Optimization
- [ ] Profile broadcast performance
- [ ] Optimize message serialization
- [ ] Implement connection pooling improvements
- [ ] Add message queuing for disconnected clients

---

### Day 8: WebSocket Routes (Wednesday)

#### Morning: API Integration
- [ ] Add WebSocket routes to `api_server.py`
- [ ] Implement `/ws` endpoint
- [ ] Add WebSocket authentication decorator (integration point)
- [ ] Add connection logging

#### Afternoon: Security
- [ ] Implement rate limiting for connections
- [ ] Add origin validation
- [ ] Implement message size limits
- [ ] Add security headers

**Key Files**:
```
src/netsentinel/processors/api_server.py  ← Add WebSocket routes
Lines to add:
- New WebSocket endpoint (~line 100-150)
- Integration point for auth decorator
```

---

### Day 9: Integration Testing (Thursday)

#### All Day: End-to-End Testing
- [ ] Create `src/tests/integration/test_websocket_flow.py`
- [ ] Test complete event flow
- [ ] Test multiple client connections
- [ ] Test reconnection scenarios
- [ ] Load testing (100+ concurrent connections)
- [ ] Performance benchmarking

**Success Criteria**:
- End-to-end flow works
- Multiple clients receive updates
- Load testing passes
- Latency <100ms for broadcasts

---

### Day 10: Documentation & Handoff (Friday)

#### Morning: Code Cleanup
- [ ] Review all code changes
- [ ] Ensure code quality standards
- [ ] Remove debug code
- [ ] Optimize imports
- [ ] Add docstrings

#### Afternoon: Documentation & Demo
- [ ] Document WebSocket architecture
- [ ] Create connection guide
- [ ] Document event types
- [ ] Prepare demo for team
- [ ] Final code review

---

## Critical Implementation Details

### WebSocket Manager Architecture

```python
# src/netsentinel/processors/websocket_manager.py (NEW)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        # Remove from all subscriptions
        for channel in self.subscriptions.values():
            channel.discard(websocket)
            
    async def subscribe(self, websocket: WebSocket, channel: str):
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
        self.subscriptions[channel].add(websocket)
        
    async def broadcast(self, channel: str, data: dict):
        if channel in self.subscriptions:
            message = json.dumps(data)
            disconnected = set()
            for websocket in self.subscriptions[channel]:
                try:
                    await websocket.send_text(message)
                except:
                    disconnected.add(websocket)
            # Clean up disconnected websockets
            for ws in disconnected:
                self.subscriptions[channel].discard(ws)
```

---

## Key Files & Responsibilities

### New Files to Create
```
src/netsentinel/processors/
├── websocket_manager.py          ← Day 2
└── websocket_server.py           ← Day 4

src/netsentinel/core/
└── event_bus.py                  ← Day 3
```

### Files to Modify (Minimal Changes)
```
src/netsentinel/processors/
├── refactored_event_processor.py ← Day 6 (10-15 lines)
└── api_server.py                 ← Day 8 (WebSocket routes)
```

### Test Files to Create
```
src/tests/
├── test_websocket_manager.py     ← Day 5
├── test_websocket_server.py      ← Day 5
└── integration/
    └── test_websocket_flow.py    ← Day 9
```

---

## Integration with Event Processor

### Minimal Changes Required

**File**: `refactored_event_processor.py`

**Add in __init__ (~line 87-100)**:
```python
# Initialize WebSocket manager if enabled
if self.config.websocket_enabled:
    from .websocket_manager import WebSocketManager
    self.websocket_manager = WebSocketManager()
    await self.websocket_manager.start()
```

**Add in _process_event (~line 200-220)**:
```python
# Broadcast threat to WebSocket clients
if self.websocket_manager and result.threat_score > 5.0:
    await self.websocket_manager.broadcast("threats", {
        "type": "new_threat",
        "data": {
            "source_ip": result.event.source_ip,
            "threat_score": result.threat_score,
            "timestamp": time.time()
        }
    })

# Broadcast alert
if result.threat_level.value in ["high", "critical"]:
    await self.websocket_manager.broadcast("alerts", {
        "type": "new_alert",
        "data": alert_data
    })
```

**Total Changes**: Only 10-15 lines added. No existing logic modified.

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
git checkout feature/websocket
git merge develop
git push origin feature/websocket

# You'll merge LAST (after Dev 1 and Dev 3)
```

---

## Success Metrics

### Week 1 Goals
- [x] WebSocket manager complete
- [x] Event bus system working
- [x] Connection management robust
- [x] Unit tests passing (>90% coverage)
- [x] Can broadcast to multiple clients

### Week 2 Goals
- [x] Integrated with event processor
- [x] Real-time updates working
- [x] Integration tests passing
- [x] Load testing passes (100+ clients)
- [x] Latency <100ms
- [x] Documentation complete

---

## Event Types to Support

### Threat Events
```json
{
  "type": "threat.new",
  "data": {
    "source_ip": "192.168.1.100",
    "threat_score": 8.5,
    "threat_level": "high",
    "timestamp": 1234567890.123
  }
}
```

### Alert Events
```json
{
  "type": "alert.new",
  "data": {
    "id": "alert_123",
    "severity": "critical",
    "message": "High threat detected",
    "timestamp": 1234567890.123
  }
}
```

### Status Events
```json
{
  "type": "status.update",
  "data": {
    "component": "event_processor",
    "status": "healthy",
    "metrics": {...}
  }
}
```

---

## Blockers & Risks

### Potential Blockers
- FastAPI WebSocket integration complexity
- Event bus design complexity
- Connection management at scale

### Mitigation
- Use proven FastAPI WebSocket patterns
- Start with simple event bus implementation
- Test incrementally with 1, 10, 100 clients

---

## Notes

### Interface Contract (Agreed Day 1)
```python
class IWebSocketBroadcaster(ABC):
    @abstractmethod
    async def broadcast_threat(self, threat_data: Dict[str, Any]) -> None:
        """Broadcast threat to connected clients"""
        pass
    
    @abstractmethod
    async def broadcast_alert(self, alert_data: Dict[str, Any]) -> None:
        """Broadcast alert to connected clients"""
        pass
```

### Coordination Points
- Day 1: Interface meeting with all 3 devs
- Day 6: Integration with processor (minimal changes)
- Day 8: Auth integration point (decorator only, no implementation)
- Daily: Sync with team about progress

### You DO NOT Need to Touch
- ML files (Dev 1 owns these)
- Auth implementation files (Dev 3 owns these)
- Event analyzer logic (Dev 1 owns this)

---

## Channels to Implement

### Required Channels
- `threats` - New threat detections
- `alerts` - System alerts
- `status` - Component status updates
- `metrics` - Performance metrics

### Optional Channels
- `events` - Raw event stream
- `correlations` - Event correlations
- `system` - System-wide updates

---

**Status**: Ready to start  
**Start Date**: [To be filled]  
**Target Completion**: 2 weeks from start

