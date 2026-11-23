#!/usr/bin/env python3
"""EXP-DORAM-07-R1: faithful E0-FullScan baseline + fixed-domain applicability.

All models here are INDEPENDENT reference models. They do not modify or import
state from src.exp_doram_07 (except the read-only E0-EarlyExit adapter, which
delegates to the untouched original implementation).

No cryptographic claim: counters are abstract operation counts, Python wall
time is reference time; neither is an MPC gate count / round count.
"""
