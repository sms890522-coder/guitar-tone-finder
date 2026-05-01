from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any

import librosa
import numpy as np


def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(low, min(high, value))


def _score(value: float, min_value: float, max_value: float) -> float:
    if max_value <= min_value:
        return 0.0
    return _clamp(((value - min_value) / (max_value - min_value)) * 10.0)


@dataclass
class ToneScores:
    gain: float
    brightness: float
    warmth: float
    mid_focus: float
    low_tightness: float
    compression: float
    roughness: float
    ambience: float


@dataclass
class AudioStats:
    duration: float
    sample_rate: int
    rms_mean: float
    dynamic_range: float
    spectral_centroid: float
    spectral_rolloff: float
    zero_crossing_rate: float
    low_energy: float
    mid_energy: float
    high_energy: float
    flatness: float


def analyze_audio(path: str) -> dict[str, Any]:
    # 60초만 분석해서 무료 서버에서도 버티게 함
    y, sr = librosa.load(path, sr=22050, mono=True, duration=60)
    if y.size == 0:
        raise ValueError("Audio file is empty or could not be decoded.")

    y = librosa.util.normalize(y)
    duration = float(librosa.get_duration(y=y, sr=sr))

    rms = librosa.feature.rms(y=y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    flatness = librosa.feature.spectral_flatness(y=y)[0]

    # 주파수 대역 에너지 계산
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    total_energy = float(np.sum(S) + 1e-9)

    low_energy = float(np.sum(S[(freqs >= 80) & (freqs < 250), :]) / total_energy)
    mid_energy = float(np.sum(S[(freqs >= 250) & (freqs < 2500), :]) / total_energy)
    high_energy = float(np.sum(S[(freqs >= 2500) & (freqs < 8000), :]) / total_energy)

    rms_mean = float(np.mean(rms))
    dynamic_range = float(np.percentile(rms, 95) - np.percentile(rms, 10))
    centroid_mean = float(np.mean(centroid))
    rolloff_mean = float(np.mean(rolloff))
    zcr_mean = float(np.mean(zcr))
    flatness_mean = float(np.mean(flatness))

    stats = AudioStats(
        duration=round(duration, 2),
        sample_rate=sr,
        rms_mean=round(rms_mean, 5),
        dynamic_range=round(dynamic_range, 5),
        spectral_centroid=round(centroid_mean, 2),
        spectral_rolloff=round(rolloff_mean, 2),
        zero_crossing_rate=round(zcr_mean, 5),
        low_energy=round(low_energy, 5),
        mid_energy=round(mid_energy, 5),
        high_energy=round(high_energy, 5),
        flatness=round(flatness_mean, 5),
    )

    # 경험적 매핑. 정확한 장비 식별이 아니라 톤 성향 추정용.
    gain = 0.45 * _score(rms_mean, 0.025, 0.22) + 0.35 * _score(flatness_mean, 0.002, 0.08) + 0.20 * _score(zcr_mean, 0.02, 0.16)
    brightness = 0.55 * _score(centroid_mean, 900, 4200) + 0.45 * _score(high_energy, 0.05, 0.45)
    warmth = 0.60 * _score(low_energy + mid_energy * 0.35, 0.10, 0.55) + 0.40 * (10 - brightness)
    mid_focus = _score(mid_energy, 0.25, 0.75)
    low_tightness = 0.55 * (10 - _score(low_energy, 0.18, 0.55)) + 0.45 * _score(rolloff_mean, 2200, 6500)
    compression = 10 - _score(dynamic_range, 0.025, 0.18)
    roughness = 0.55 * _score(zcr_mean, 0.025, 0.15) + 0.45 * _score(flatness_mean, 0.003, 0.08)
    # 1차 버전에서는 진짜 reverb/delay 분리가 아니라 잔향 가능성 힌트만 계산
    ambience = 0.60 * _score(dynamic_range, 0.02, 0.16) + 0.40 * _score(rolloff_mean, 1800, 6500)

    scores = ToneScores(
        gain=round(_clamp(gain), 1),
        brightness=round(_clamp(brightness), 1),
        warmth=round(_clamp(warmth), 1),
        mid_focus=round(_clamp(mid_focus), 1),
        low_tightness=round(_clamp(low_tightness), 1),
        compression=round(_clamp(compression), 1),
        roughness=round(_clamp(roughness), 1),
        ambience=round(_clamp(ambience), 1),
    )

    return {
        "stats": asdict(stats),
        "scores": asdict(scores),
    }
