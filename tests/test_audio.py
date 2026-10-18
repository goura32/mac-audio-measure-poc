import numpy as np

from audio import dbfs_peak, response_db, summarize_recording, make_sweep


def test_sweep_boundaries():
    wave = make_sweep(0.1, duration=0.5)
    assert wave.shape[0] == int(1.2 * 48000)
    assert np.max(np.abs(wave)) <= 0.101
    assert np.all(wave[:int(0.2 * 48000)] == 0)


def test_no_clipping():
    assert not summarize_recording(np.array([0.0, 0.5]))['near_clip']
    assert summarize_recording(np.array([1.0]))['near_clip']
    assert abs(dbfs_peak(np.array([0.5])) + 6.0206) < 0.001


def test_flat_loopback():
    x = make_sweep(0.1, duration=0.4)
    y = np.r_[np.zeros(97), x[:-97]] * 0.3
    freqs, response = response_db(x, y)
    assert len(freqs) == len(response) == 240
    assert abs(float(np.interp(1000, freqs, response))) < 0.05
    assert float(np.median(abs(response[(freqs > 300) & (freqs < 6000)]))) < 1.0


def test_scaled_amplitude_normalizes_out():
    x = make_sweep(0.1, duration=0.4)
    f, a = response_db(x, x * 0.2)
    _, b = response_db(x, x * 0.7)
    assert np.max(np.abs(a-b)) < 0.05
