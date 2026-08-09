"""Unit tests for app/_app_lib.py pure helpers.

Only covers calibration_verdict (audit P2 #5): the dashboard must not claim
"well calibrated / dependable" unless the numbers actually support it. The
rest of _app_lib.py is Streamlit-caching glue around pricing/*, already
covered indirectly by pricing/ tests, so it stays untested here.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from _app_lib import CALIBRATION_TOLERANCE, calibration_verdict  # noqa: E402


def test_calibration_verdict_true_when_close():
    msg, well_calibrated = calibration_verdict(0.42, 0.40)  # 2 points apart
    assert well_calibrated is True
    assert "well calibrated" in msg.lower()
    assert "dependable" in msg.lower()


def test_calibration_verdict_false_when_far_apart():
    msg, well_calibrated = calibration_verdict(0.60, 0.30)  # 30 points apart
    assert well_calibrated is False
    assert "well calibrated" not in msg.lower()
    assert "dependable" not in msg.lower()
    # Still states the actual numbers, honestly, with no verdict.
    assert "60.0%" in msg
    assert "30.0%" in msg


def test_calibration_verdict_boundary_is_inclusive():
    # Exactly at the tolerance still counts as calibrated.
    msg, well_calibrated = calibration_verdict(0.45, 0.40, tol=CALIBRATION_TOLERANCE)
    assert well_calibrated is True


def test_calibration_verdict_respects_custom_tolerance():
    msg, well_calibrated = calibration_verdict(0.44, 0.40, tol=0.02)
    assert well_calibrated is False
