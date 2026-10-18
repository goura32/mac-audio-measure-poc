"""Signal generation and relative transfer-function measurement (not SPL calibration)."""
from __future__ import annotations

import numpy as np
from scipy.fft import next_fast_len, rfft, rfftfreq
from scipy.ndimage import gaussian_filter1d

SAMPLE_RATE = 48_000
START_HZ = 80.0
END_HZ = 16_000.0


def make_sweep(level: float, duration: float = 2.5, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Logarithmic sine sweep with silence, fades and limited peak level."""
    if not 0.0 < level <= 0.5:
        raise ValueError('Level must be greater than zero and at most 0.5')
    n = round(rate * duration)
    t = np.arange(n, dtype=np.float64) / rate
    k = np.log(END_HZ / START_HZ) / duration
    phase = (2 * np.pi * START_HZ / k) * np.expm1(k * t)
    sweep = np.sin(phase)
    fade = max(1, round(0.02 * rate))
    ramp = np.sin(np.linspace(0, np.pi / 2, fade, endpoint=True)) ** 2
    sweep[:fade] *= ramp
    sweep[-fade:] *= ramp[::-1]
    pre = np.zeros(round(0.20 * rate))
    post = np.zeros(round(0.50 * rate))
    return np.r_[pre, level * sweep, post].astype(np.float32)


def dbfs_peak(samples: np.ndarray) -> float:
    peak = float(np.max(np.abs(samples))) if np.size(samples) else 0.0
    return float(20 * np.log10(max(peak, 1e-12)))


def dbfs_rms(samples: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.asarray(samples, dtype=np.float64) ** 2))) if np.size(samples) else 0.0
    return float(20 * np.log10(max(rms, 1e-12)))


def response_db(source: np.ndarray, recorded: np.ndarray, rate: int = SAMPLE_RATE) -> tuple[np.ndarray, np.ndarray]:
    """Estimate *relative* frequency response from a sweep loopback.

    FFT-domain regularized deconvolution gives the complete acoustic path,
    including the room, microphone and any OS DSP. Plot is normalized to
    0 dB at 1 kHz. It is NOT an absolute loudspeaker response or SPL reading.
    """
    source = np.asarray(source, dtype=np.float64).reshape(-1)
    recorded = np.asarray(recorded, dtype=np.float64).reshape(-1)
    if len(source) < 2048 or len(recorded) < 2048:
        raise ValueError('Recording is too short')
    nfft = next_fast_len(len(source) + len(recorded) - 1)
    x = rfft(source, nfft)
    y = rfft(recorded, nfft)
    power = np.abs(x) ** 2
    regularization = 1e-7 * max(float(power.max()), 1e-30)
    transfer = y * np.conj(x) / (power + regularization)
    f = rfftfreq(nfft, 1.0 / rate)
    grid = np.geomspace(START_HZ, END_HZ, 240)
    magnitude_db = 20.0 * np.log10(np.maximum(np.abs(transfer), 1e-12))
    # First interpolate onto a log-frequency grid, then apply modest smoothing.
    curve = gaussian_filter1d(np.interp(grid, f, magnitude_db), sigma=2.0)
    curve = curve - np.interp(1000.0, grid, curve)
    return grid, curve


def summarize_recording(recorded: np.ndarray) -> dict:
    x = np.asarray(recorded)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    return {
        'peak_dbfs': dbfs_peak(x),
        'rms_dbfs': dbfs_rms(x),
        'near_clip': bool(peak >= 0.98),
    }
