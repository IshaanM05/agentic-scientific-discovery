"""LabLoop: a closed-loop, multi-agent AI scientist with pluggable lab adapters."""
import os as _os
_os.environ.setdefault("OMP_NUM_THREADS", "1")  # GP fits are bit-reproducible only single-threaded
__version__ = "0.1.0"
