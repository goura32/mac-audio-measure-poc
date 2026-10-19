import numpy as np
import pytest

from audio import make_sweep
from measure_once import analyze_capture


def test_valid_synthetic_sweep():
    emitted = make_sweep(0.02, duration=2.5)
    captured = np.r_[np.zeros(120), emitted[:-120]] * 0.4
    result = analyze_capture(emitted, captured)
    assert len(result["frequencies_hz"]) == 240
    assert result["diagnostics"]["sweep_over_baseline_db"] > 8
    assert abs(np.interp(1000, result["frequencies_hz"], result["response_db"])) < 0.05


def test_silence_rejected():
    emitted = make_sweep(0.02)
    with pytest.raises(ValueError, match="not clearly above ambient noise"):
        analyze_capture(emitted, np.zeros_like(emitted))


def test_clipping_risk_rejected():
    emitted = make_sweep(0.02)
    with pytest.raises(ValueError, match="too high"):
        analyze_capture(emitted, emitted * 45)


def test_nonfinite_samples_rejected():
    emitted = make_sweep(0.02)
    recorded = emitted.copy()
    recorded[-1] = np.nan
    with pytest.raises(ValueError, match="Invalid recording"):
        analyze_capture(emitted, recorded)
