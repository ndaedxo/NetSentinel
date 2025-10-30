# Developer 1 TODO: ML & Anomaly Detection

**Developer**: ML Specialist  
**Focus**: ML Inference & Event Processing  
**Timeline**: 2 weeks

---

## Week 1: Foundation & Implementation

### Day 1: Setup & Planning (Monday)

#### Morning: Team Meeting
- [ ] Attend interface definition meeting (ALL 3 developers)
- [ ] Agree on IMLDetector interface contract
- [ ] Understand EventAnalyzer integration points
- [ ] Set up development environment
- [ ] Create feature branch: `feature/ml-inference`

#### Afternoon: ML Infrastructure Setup
- [ ] Create `src/netsentinel/ml_models/` directory
- [ ] Create `__init__.py` for ml_models module
- [ ] Setup Anomalib dependencies (verify installation)
- [ ] Create initial `ml_anomaly_detector.py` backup
- [ ] Document current implementation issues

---

### Day 2: Training Pipeline (Tuesday)

#### Morning: Model Training Implementation
- [ ] Create `src/netsentinel/ml_models/training_pipeline.py`
- [ ] Implement proper Anomalib Engine integration
- [ ] Add dataset creation from network events
- [ ] Implement proper data preprocessing
- [ ] Add model persistence after training

**Key Files**:
```
src/netsentinel/ml_models/training_pipeline.py  ← NEW
```

**Success Criteria**:
- Can train Anomalib models on network data
- Models save to disk properly
- Training progress visible

---

### Day 3: Model Manager (Wednesday)

#### Morning: Model Management
- [ ] Create `src/netsentinel/ml_models/model_manager.py`
- [ ] Implement model loading/versioning
- [ ] Add model registry
- [ ] Implement model state management
- [ ] Add model health checks

#### Afternoon: Feature Extractor
- [ ] Create `src/netsentinel/ml_models/feature_extractor.py`
- [ ] Implement proper feature normalization
- [ ] Add feature validation
- [ ] Create feature-to-image conversion for Anomalib
- [ ] Test feature extraction on sample events

**Key Files**:
```
src/netsentinel/ml_models/model_manager.py     ← NEW
src/netsentinel/ml_models/feature_extractor.py ← NEW
```

---

### Day 4: Inference Engine (Thursday)

#### Morning: Fix ML Inference Implementation
- [ ] **CRITICAL**: Rewrite `_ml_anomaly_detection()` method in `ml_anomaly_detector.py`
  - Current: lines 353-377 (distance-based, NOT using Anomalib)
  - Target: Actual TorchInferencer usage
- [ ] Implement proper inference pipeline
- [ ] Add error handling for inference failures
- [ ] Add inference metrics collection

#### Afternoon: Integration Setup
- [ ] Update `_initialize_model()` to use new model manager
- [ ] Update `_load_model()` for proper model loading
- [ ] Add fallback mechanisms for untrained models
- [ ] Create inference test utilities

**Key Files**:
```
src/netsentinel/ml_anomaly_detector.py  ← MAJOR REWRITE
Lines to fix:
- _initialize_model (99-115)
- _ml_anomaly_detection (353-377)  ← CRITICAL
- _load_model (503-516)
```

**Success Criteria**:
- ML models actually perform inference (not simulated)
- Inference uses real Anomalib TorchInferencer
- Proper confidence scores returned

---

### Day 5: Testing & Validation (Friday)

#### All Day: Unit Tests & Validation
- [ ] Create `src/tests/test_ml_anomaly_detector.py`
- [ ] Test model initialization
- [ ] Test feature extraction
- [ ] Test inference with sample data
- [ ] Test model training pipeline
- [ ] Validate model persistence
- [ ] Test error handling

**Success Criteria**:
- All unit tests passing
- >90% test coverage for ML components
- No import errors
- Can train and infer on sample data

---

## Week 2: Integration & Polish

### Day 6: Event Analyzer Integration (Monday)

#### Morning: Integration with Event Analyzer
- [ ] Update `src/netsentinel/processors/event_analyzer.py`
- [ ] Modify `analyze_event()` to use new ML interface
- [ ] Integrate proper ML confidence scores
- [ ] Add ML analysis to threat scoring
- [ ] Test end-to-end event processing

**Key Files**:
```
src/netsentinel/processors/event_analyzer.py  ← Integration
Lines to update:
- analyze_event method (add proper ML integration)
- _initialize_ml_analyzer if exists
```

#### Afternoon: Testing Integration
- [ ] Create integration tests
- [ ] Test event → analysis → scoring flow
- [ ] Verify ML scores affect final threat scores
- [ ] Performance testing

---

### Day 7: Performance Optimization (Tuesday)

#### Morning: Inference Performance
- [ ] Profile ML inference performance
- [ ] Optimize feature extraction
- [ ] Implement batching for multiple events
- [ ] Add caching for feature normalization
- [ ] Optimize model loading

#### Afternoon: Memory Management
- [ ] Review memory usage in ML components
- [ ] Optimize event history storage
- [ ] Implement proper cleanup for old data
- [ ] Add memory profiling

---

### Day 8: Monitoring & Metrics (Wednesday)

#### Morning: ML Metrics
- [ ] Add ML performance metrics
- [ ] Track inference latency
- [ ] Monitor model confidence scores
- [ ] Add model health metrics
- [ ] Create ML dashboard data

#### Afternoon: Error Handling
- [ ] Improve error handling in training
- [ ] Add graceful degradation for ML failures
- [ ] Implement retry logic for inference
- [ ] Add comprehensive logging

---

### Day 9: Integration Testing (Thursday)

#### All Day: Integration Testing
- [ ] Create `src/tests/integration/test_ml_pipeline.py`
- [ ] Test complete ML pipeline
- [ ] Test training → inference flow
- [ ] Test with real network events
- [ ] Test error scenarios
- [ ] Performance benchmarking

**Success Criteria**:
- Complete pipeline works end-to-end
- Integration tests passing
- Performance meets requirements (<100ms inference)
- No memory leaks

---

### Day 10: Documentation & Handoff (Friday)

#### Morning: Code Cleanup
- [ ] Review all code changes
- [ ] Ensure code quality standards
- [ ] Remove debug code
- [ ] Optimize imports
- [ ] Add docstrings where missing

#### Afternoon: Documentation & Demo
- [ ] Document ML integration
- [ ] Update architecture docs
- [ ] Create usage examples
- [ ] Prepare demo for team
- [ ] Final code review

---

## Critical Implementation Details

### Must Fix: Inference Not Working

**Current Problem** (lines 353-377):
```python
# ❌ NOT WORKING - Just calculates distance, doesn't use model
def _ml_anomaly_detection(self, features, normalized_features):
    distances = torch.cdist(image_tensor, self.training_data)
    min_distance = torch.min(distances).item()
    anomaly_score = min(min_distance * 10, 1.0)
    return anomaly_score
```

**Required Fix**:
```python
# ✅ PROPER IMPLEMENTATION
def _ml_anomaly_detection(self, features, normalized_features):
    if self.inferencer is None:
        self.inferencer = TorchInferencer(
            model=self.model, 
            model_path=self.model_path
        )
    
    # Convert features to image tensor for Anomalib
    image_tensor = self._create_feature_image(normalized_features)
    
    # Run actual inference
    prediction = self.inferencer.predict(image_tensor)
    
    # Extract anomaly score from prediction
    anomaly_score = prediction.pred_score
    
    return anomaly_score
```

---

## Key Files & Responsibilities

### New Files to Create
```
src/netsentinel/ml_models/
├── __init__.py                    ← Day 1
├── training_pipeline.py           ← Day 2
├── model_manager.py              ← Day 3
└── feature_extractor.py          ← Day 3
```

### Files to Modify
```
src/netsentinel/
├── ml_anomaly_detector.py        ← Days 4-5 (MAJOR REWRITE)
└── processors/
    └── event_analyzer.py         ← Day 6 (Integration)
```

### Test Files to Create
```
src/tests/
├── test_ml_anomaly_detector.py   ← Day 5
└── integration/
    └── test_ml_pipeline.py       ← Day 9
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
git checkout feature/ml-inference
git merge develop
git push origin feature/ml-inference

# You'll merge FIRST when ready
```

---

## Success Metrics

### Week 1 Goals
- [x] ML training actually works (not simulated)
- [x] Models save/load properly
- [x] Feature extraction complete
- [x] Unit tests passing (>90% coverage)
- [x] Inference foundation ready

### Week 2 Goals
- [x] Complete ML integration with event analyzer
- [x] End-to-end pipeline working
- [x] Integration tests passing
- [x] Performance <100ms inference
- [x] Documentation complete

---

## Blockers & Risks

### Potential Blockers
- Anomalib version compatibility
- Model loading performance
- Feature-to-image conversion complexity

### Mitigation
- Start with simplest Anomalib model (FastFlow)
- Use proven Anomalib patterns from documentation
- Test incrementally at each step

---

## Notes

### Interface Contract (Agreed Day 1)
```python
class IMLDetector(ABC):
    @abstractmethod
    async def analyze_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze event and return anomaly score"""
        pass
    
    @abstractmethod
    async def train_on_events(self, events: List[Dict[str, Any]]) -> bool:
        """Train model on events"""
        pass
```

### Coordination Points
- Day 1: Interface meeting with all 3 devs
- Day 6: Integration with event_analyzer.py (minimal changes)
- Daily: Sync with team about progress

### You DO NOT Need to Touch
- `api_server.py` (Dev 3 owns this)
- WebSocket files (Dev 2 owns these)
- Auth files (Dev 3 owns these)

---

**Status**: Ready to start  
**Start Date**: [To be filled]  
**Target Completion**: 2 weeks from start

