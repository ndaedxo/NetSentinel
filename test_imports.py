#!/usr/bin/env python3
"""Test ML imports"""

try:
    import torch
    import numpy as np
    from netsentinel.ml_anomaly_detector import (
        NetworkEventAnomalyDetector,
        EventFeatures,
    )
    print("All ML imports successful")
    print(f"Torch version: {torch.__version__}")
    print(f"NumPy version: {np.__version__}")
except ImportError as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
