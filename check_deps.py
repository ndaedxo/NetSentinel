#!/usr/bin/env python3
"""Check ML dependencies"""

try:
    import torch
    print("Torch available")
except ImportError:
    print("Torch not available")

try:
    import anomalib
    print("Anomalib available")
except ImportError:
    print("Anomalib not available")

try:
    import numpy as np
    print("NumPy available")
except ImportError:
    print("NumPy not available")
