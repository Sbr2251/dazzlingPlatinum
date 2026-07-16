#!/usr/bin/env python3
"""Align an Affine Pulse emulator capture to audio and analyze reveal-window events."""

from __future__ import annotations

import argparse
import csv
import wave
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_wav(path: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        rate = wav.getframerate()
        width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    if width != 2:
        raise ValueError(f"expected 16-bit PCM, got {width * 8}-bit")
    data = np.frombuffer(frames, dtype="<i2").astype(np.float32)
    data = data.reshape(-1, channels).mean(axis=1) / 32768.0
    return rate, data


def rms_envelope(samples: np.ndarray, rate: int, step_seconds: float = 0.02) -> tuple[np.ndarray, np.ndarray]:
    step = max(1, int(rate * step_seconds))
    count = len(samples) // step
    trimmed = samples[: count * step].reshape(count, step)
    rms = np.sqrt(np.mean(trimmed * trimmed, axis=1))
    times = (np.arange(count) * step + step / 2) / rate
    return times, rms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture_dir", type=Path)
    args = parser.parse_args()

    capture = args.capture_dir.resolve()
    audio = capture / "emulator-audio.wav"
    rate, samples = load_wav(audio)
    duration = len(samples) / rate

    # The WAV is finalized when the recorder exits. Back-compute its start time,
    # then align screenshot mtimes to the audio clock.
    audio_start = audio.stat().st_mtime - duration
    frames = sorted(capture.glob("07_transform_*.png"))
    if not frames:
        raise SystemExit("no transformation frames found")
    frame_times = [(frame.name, frame.stat().st_mtime - audio_start) for frame in frames]

    times, rms = rms_envelope(samples, rate)
    start = max(0.0, frame_times[0][1] - 1.0)
    end = min(duration, frame_times[-1][1] + 1.0)
    mask = (times >= start) & (times <= end)
    window_times = times[mask]
    window_rms = rms[mask]

    baseline_mask = (times >= max(0.0, start - 4.0)) & (times < start)
    baseline = float(np.median(rms[baseline_mask])) if np.any(baseline_mask) else float(np.median(rms))
    threshold = max(baseline * 1.8, float(np.percentile(window_rms, 82)))

    active = window_rms >= threshold
    events: list[tuple[float, float, float]] = []
    event_start = None
    for index, value in enumerate(active):
        if value and event_start is None:
            event_start = index
        if event_start is not None and (not value or index == len(active) - 1):
            event_end = index if not value else index + 1
            if event_end - event_start >= 2:
                segment = window_rms[event_start:event_end]
                events.append(
                    (
                        float(window_times[event_start]),
                        float(window_times[event_end - 1] + 0.02),
                        float(segment.max()),
                    )
                )
            event_start = None

    with (capture / "audio-frame-alignment.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["frame", "audio_time_seconds"])
        for name, timestamp in frame_times:
            writer.writerow([name, f"{timestamp:.6f}"])

    with (capture / "audio-event-analysis.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_start_seconds", "event_end_seconds", "peak_rms"])
        for event in events:
            writer.writerow([f"{event[0]:.6f}", f"{event[1]:.6f}", f"{event[2]:.8f}"])

    # Spectrogram and RMS envelope centered on the transformation capture.
    left = int(start * rate)
    right = int(end * rate)
    excerpt = samples[left:right]
    fig, (ax_wave, ax_spec) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, constrained_layout=True)
    excerpt_times = np.arange(len(excerpt)) / rate + start
    decimation = max(1, rate // 2000)
    ax_wave.plot(excerpt_times[::decimation], excerpt[::decimation], color="#32325d", linewidth=0.4)
    ax_wave.plot(window_times, window_rms, color="#d7263d", linewidth=1.3, label="20 ms RMS")
    ax_wave.axhline(threshold, color="#ff9f1c", linestyle="--", linewidth=1.0, label="event threshold")
    for index, (_, timestamp) in enumerate(frame_times):
        if index % 5 == 0:
            ax_wave.axvline(timestamp, color="#2a9d8f", alpha=0.25, linewidth=0.8)
    ax_wave.set_ylabel("Amplitude / RMS")
    ax_wave.legend(loc="upper right")
    ax_wave.set_title("Affine Pulse live audio aligned to dense transformation frames")

    ax_spec.specgram(excerpt, NFFT=1024, Fs=rate, noverlap=768, cmap="magma", xextent=(start, end))
    ax_spec.set_ylim(0, 12000)
    ax_spec.set_xlabel("Audio time (seconds)")
    ax_spec.set_ylabel("Frequency (Hz)")
    fig.savefig(capture / "affine-pulse-audio-analysis.png", dpi=180)
    plt.close(fig)

    summary = [
        f"sample_rate_hz={rate}",
        f"duration_seconds={duration:.6f}",
        f"transform_window_start_seconds={start:.6f}",
        f"transform_window_end_seconds={end:.6f}",
        f"baseline_rms={baseline:.8f}",
        f"event_threshold_rms={threshold:.8f}",
        f"detected_events={len(events)}",
    ]
    for index, event in enumerate(events, start=1):
        summary.append(f"event_{index}={event[0]:.6f}-{event[1]:.6f},peak={event[2]:.8f}")
    (capture / "audio-analysis-summary.txt").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
