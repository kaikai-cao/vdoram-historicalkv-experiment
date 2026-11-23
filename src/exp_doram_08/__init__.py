#!/usr/bin/env python3
"""EXP-DORAM-08: symbolic MPC primitive cost structure audit.

Pure integer/parametric model. No upstream imports, no VDORAM dependency,
no MPC timing, no claim that R1CS constraints equal secret multiplications.
"""

from .costs import CostParams, fetch_mults, e0_step, e1_step, e0_total, e1_total, cross_threshold_n
from .counters import SelectCounters, e0_fetch_counters, e1_fetch_counters

__all__ = [
    "CostParams",
    "fetch_mults",
    "e0_step",
    "e1_step",
    "e0_total",
    "e1_total",
    "cross_threshold_n",
    "SelectCounters",
    "e0_fetch_counters",
    "e1_fetch_counters",
]
