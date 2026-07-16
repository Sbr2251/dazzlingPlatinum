#!/usr/bin/env python3
"""Compare cry-enabled and no-cry Affine Pulse captures around the visual reveal."""

from __future__ import annotations

import argparse
import csv
import wave
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def load_wav(path: Path) -> tuple[int, np.ndarray, float]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        rate = wav.getframerate()
        width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    if width != 2:
        raise ValueError("expected 16-bit PCM")
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32).reshape(-1, channels).mean(axis=1) / 32768.0
    duration = len(samples) / rate
    return rate, samples, path.stat().st_mtime - duration


def frame_alignment(capture: Path, audio_start: float) -> list[tuple[Path, float, float]]:
    rows: list[tuple[Path, float, float]] = []
    for frame in sorted(capture.glob("07_transform_*.png")):
        image = np.asarray(Image.open(frame).convert("RGB"), dtype=np.float32)
        top = image[: image.shape[0] // 2]
        brightness = float(top.mean())
        rows.append((frame, frame.stat().st_mtime - audio_start, brightness))
    if not rows:
        raise ValueError(f"no transform frames in {capture}")
    return rows


def extract(samples: np.ndarray, rate: int, center: float, before: float, after: float) -> np.ndarray:
    left = max(0, int((center - before) * rate))
    right = min(len(samples), int((center + after) * rate))
    result = samples[left:right]
    expected = int((before + after) * rate)
    if len(result) < expected:
        result = np.pad(result, (0, expected - len(result)))
    return result[:expected]


def rms_curve(samples: np.ndarray, rate: int, step_seconds: float = 0.01) -> tuple[np.ndarray, np.ndarray]:
    step = max(1, int(rate * step_seconds))
    count = len(samples) // step
    matrix = samples[: count * step].reshape(count, step)
    return np.arange(count) * step / rate, np.sqrt(np.mean(matrix * matrix, axis=1))


def best_lag(reference: np.ndarray, candidate: np.ndarray, rate: int, max_lag_seconds: float = 0.35) -> int:
    # Downsample for a bounded deterministic cross-correlation.
    factor = max(1, rate // 4000)
    ref = reference[::factor]
    cand = candidate[::factor]
    ref = ref - ref.mean()
    cand = cand - cand.mean()
    max_lag = int(max_lag_seconds * rate / factor)
    best_score = -np.inf
    best = 0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            a = ref[-lag:]
            b = cand[: len(a)]
        elif lag > 0:
            a = ref[:-lag]
            b = cand[lag:]
        else:
            a = ref
            b = cand
        if len(a) < 100:
            continue
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        score = float(np.dot(a, b) / denom) if denom else -np.inf
        if score > best_score:
            best_score = score
            best = lag * factor
    return best


def shift(samples: np.ndarray, lag: int) -> np.ndarray:
    if lag > 0:
        return np.pad(samples[lag:], (0, lag))
    if lag < 0:
        return np.pad(samples[:lag], (-lag, 0))
    return samples.copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("accepted", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    accepted = args.accepted.resolve()
    baseline = args.baseline.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    rate_a, audio_a, start_a = load_wav(accepted / "emulator-audio.wav")
    rate_b, audio_b, start_b = load_wav(baseline / "emulator-audio.wav")
    if rate_a != rate_b:
        raise ValueError("sample rates differ")
    rate = rate_a

    frames_a = frame_alignment(accepted, start_a)
    frames_b = frame_alignment(baseline, start_b)
    reveal_a = max(frames_a, key=lambda row: row[2])
    reveal_b = max(frames_b, key=lambda row: row[2])

    before = 2.5
    after = 3.5
    clip_a = extract(audio_a, rate, reveal_a[1], before, after)
    clip_b = extract(audio_b, rate, reveal_b[1], before, after)

    # Align on the pre-reveal audio bed, where the builds are functionally identical.
    pre_left = int(0.2 * rate)
    pre_right = int((before - 0.35) * rate)
    lag = best_lag(clip_a[pre_left:pre_right], clip_b[pre_left:pre_right], rate)
    clip_b_aligned = shift(clip_b, lag)
    difference = clip_a - clip_b_aligned

    t, rms_a = rms_curve(clip_a, rate)
    _, rms_b = rms_curve(clip_b_aligned, rate)
    _, rms_diff = rms_curve(difference, rate)
    t = t - before

    reveal_band = (t >= -0.15) & (t <= 1.5)
    pre_band = (t >= -2.0) & (t <= -0.5)
    reveal_diff_peak = float(rms_diff[reveal_band].max())
    pre_diff_median = float(np.median(rms_diff[pre_band]))
    ratio = reveal_diff_peak / max(pre_diff_median, 1e-9)
    peak_index = int(np.flatnonzero(reveal_band)[np.argmax(rms_diff[reveal_band])])
    peak_relative = float(t[peak_index])

    with (output / "ab-frame-reveal.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run", "frame", "audio_time_seconds", "top_screen_mean_brightness"])
        writer.writerow(["accepted", reveal_a[0].name, f"{reveal_a[1]:.6f}", f"{reveal_a[2]:.6f}"])
        writer.writerow(["baseline", reveal_b[0].name, f"{reveal_b[1]:.6f}", f"{reveal_b[2]:.6f}"])

    summary = [
        f"sample_rate_hz={rate}",
        f"accepted_reveal_frame={reveal_a[0].name}",
        f"accepted_reveal_audio_seconds={reveal_a[1]:.6f}",
        f"baseline_reveal_frame={reveal_b[0].name}",
        f"baseline_reveal_audio_seconds={reveal_b[1]:.6f}",
        f"baseline_alignment_lag_samples={lag}",
        f"baseline_alignment_lag_seconds={lag / rate:.6f}",
        f"pre_reveal_difference_median_rms={pre_diff_median:.8f}",
        f"reveal_difference_peak_rms={reveal_diff_peak:.8f}",
        f"reveal_to_pre_difference_ratio={ratio:.4f}",
        f"difference_peak_relative_to_visual_reveal_seconds={peak_relative:.6f}",
    ]
    (output / "ab-audio-summary.txt").write_text("\n".join(summary) + "\n")

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True, constrained_layout=True)
    axes[0].plot(t, rms_a, label="cry-enabled", color="#6a4c93", linewidth=1.2)
    axes[0].plot(t, rms_b, label="no-cry baseline", color="#2a9d8f", linewidth=1.0, alpha=0.9)
    axes[0].axvline(0, color="#d7263d", linestyle="--", label="visual reveal flash")
    axes[0].set_ylabel("20 ms RMS")
    axes[0].set_title("Affine Pulse reveal audio: controlled cry-enabled vs no-cry A/B")
    axes[0].legend(loc="upper right")

    axes[1].plot(t, rms_diff, color="#d7263d", linewidth=1.2)
    axes[1].axvline(0, color="#111111", linestyle="--")
    axes[1].axhline(pre_diff_median, color="#ff9f1c", linestyle=":", label="pre-reveal median difference")
    axes[1].set_ylabel("Difference RMS")
    axes[1].legend(loc="upper right")

    start = int((before - 0.25) * rate)
    stop = int((before + 1.75) * rate)
    axes[2].specgram(difference[start:stop], NFFT=1024, Fs=rate, noverlap=768, cmap="magma", xextent=(-0.25, 1.75))
    axes[2].axvline(0, color="white", linestyle="--", linewidth=1.0)
    axes[2].set_ylim(0, 12000)
    axes[2].set_ylabel("Difference frequency (Hz)")
    axes[2].set_xlabel("Seconds relative to visual reveal flash")
    fig.savefig(output / "affine-pulse-audio-ab-comparison.png", dpi=180)
    plt.close(fig)

    print("\n".join(summary))


if __name__ == "__main__":
    main()
