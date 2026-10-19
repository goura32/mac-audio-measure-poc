"""One low-level audible sweep using the same sounddevice path as the GUI.

This deliberately avoids GUI automation, Core Audio volume changes, and
Pa_IsFormatSupported/check_input_settings. It does not calibrate a microphone.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from audio import SAMPLE_RATE, dbfs_rms, make_sweep, response_db, summarize_recording

FIRST_LEVEL = 0.02  # Fixed until the first actual audible measurement is verified.
DURATION = 2.5


def analyze_capture(stimulus: np.ndarray, capture: np.ndarray) -> dict:
    """Reject near-clipped, silent, or clearly noise-dominated recordings."""
    captured = np.asarray(capture, dtype=np.float32).reshape(-1)
    if captured.size != stimulus.size or not np.all(np.isfinite(captured)):
        raise ValueError("Invalid recording length or non-finite samples")

    # The stimulus begins with 200 ms of digital silence.
    noise_dbfs = dbfs_rms(captured[:round(0.15 * SAMPLE_RATE)])
    signal_dbfs = dbfs_rms(captured[round(0.35 * SAMPLE_RATE):round(2.55 * SAMPLE_RATE)])
    stats = summarize_recording(captured)
    diagnostics = {
        **stats,
        "baseline_rms_dbfs": noise_dbfs,
        "sweep_rms_dbfs": signal_dbfs,
        "sweep_over_baseline_db": signal_dbfs - noise_dbfs,
    }
    if stats["near_clip"] or stats["peak_dbfs"] > -6:
        raise ValueError(f"Recording level too high: {diagnostics}")
    if signal_dbfs < -55 or signal_dbfs - noise_dbfs < 8:
        raise ValueError(f"Sweep not clearly above ambient noise: {diagnostics}")
    frequencies, response = response_db(stimulus, captured)
    return {
        "frequencies_hz": frequencies.tolist(),
        "response_db": response.tolist(),
        "diagnostics": diagnostics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Single low-level sweep on built-in MacBook Pro audio")
    parser.add_argument(
        "--confirm-low-volume", action="store_true",
        help="Confirm that a person has lowered macOS output volume and approved an audible sweep",
    )
    parser.add_argument("--output", type=Path, default=Path("measurements/first-sweep.json"))
    args = parser.parse_args()

    if not args.confirm_low_volume:
        parser.error(
            "No sound was played. A person must lower macOS speaker volume first; "
            "then explicitly pass --confirm-low-volume."
        )

    import sounddevice as sd

    input_id, output_id = (int(x) for x in sd.default.device)
    if input_id < 0 or output_id < 0:
        raise RuntimeError("No default input and output devices")
    input_info = sd.query_devices(input_id)
    output_info = sd.query_devices(output_id)
    input_name, output_name = str(input_info["name"]), str(output_info["name"])
    if (input_info["max_input_channels"] < 1 or output_info["max_output_channels"] < 1
            or "MacBook Pro" not in input_name or "MacBook Pro" not in output_name):
        raise RuntimeError(
            f"Expected built-in MacBook Pro devices, got input={input_name!r}, output={output_name!r}"
        )
    if args.output.exists():
        raise FileExistsError(f"Will not overwrite existing measurement: {args.output}")

    stimulus = make_sweep(FIRST_LEVEL, duration=DURATION)
    print(f"Input: {input_name}; output: {output_name}", flush=True)
    print("One 80Hz-16kHz audible sweep, fixed amplitude 0.02; macOS system volume unchanged.", flush=True)
    recorded = sd.playrec(
        stimulus.reshape(-1, 1), samplerate=SAMPLE_RATE, channels=1, dtype="float32",
        device=(input_id, output_id), blocking=True,
    )
    outcome = analyze_capture(stimulus, recorded)
    details = outcome.pop("diagnostics")
    payload = {
        "measurement": {
            "type": "measure",
            "level": FIRST_LEVEL,
            "frequencies_hz": outcome["frequencies_hz"],
            "response_db": outcome["response_db"],
            "peak_dbfs": details["peak_dbfs"],
            "rms_dbfs": details["rms_dbfs"],
            "input_name": input_name,
            "output_name": output_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "sample_rate": SAMPLE_RATE,
        },
        "reference": None,
        "diagnostics": details,
        "note": "Uncalibrated relative response; includes room, mic and OS DSP.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"MEASUREMENT_COMPLETE: {args.output}", flush=True)
    print(f"peak={details['peak_dbfs']:.1f} dBFS; signal/baseline={details['sweep_over_baseline_db']:.1f} dB", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"MEASUREMENT_NOT_COMPLETED: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
