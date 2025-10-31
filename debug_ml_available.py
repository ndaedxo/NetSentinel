#!/usr/bin/env python3
"""Debug ML_AVAILABLE flag"""

try:
    import torch
    import numpy as np
    from netsentinel.ml_anomaly_detector import (
        NetworkEventAnomalyDetector,
        EventFeatures,
    )
    ML_AVAILABLE = True
    print("ML_AVAILABLE = True")
except ImportError as e:
    print(f"ML_AVAILABLE = False due to: {e}")
    ML_AVAILABLE = False

print(f"Final ML_AVAILABLE: {ML_AVAILABLE}")
