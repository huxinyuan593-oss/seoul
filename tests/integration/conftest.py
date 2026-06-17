"""Set up sys.path so integration tests can import from all subsystems."""

import sys
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Insert module paths
_quant_src = os.path.join(_PROJECT_ROOT, "quant-engine")
_audit_src = os.path.join(_PROJECT_ROOT, "audit-layer")

for _p in [_quant_src, _audit_src]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
