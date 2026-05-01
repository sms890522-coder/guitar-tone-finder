from __future__ import annotations

import math
from dataclasses import asdict, dataclass
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

def _band_energy_ratio(S: np.ndarray, freqs: np.ndarray, low: float, high: float) -> float:
    idx = np.where((freqs >= low) & (freqs < high))[0]
    if len(idx) == 0:
        return 0.0

    band_energy = float(np.sum(S[idx, :]))
    total_energy = float(np.sum(S) + 1e-9)
    return band_energy / total_energy

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

    # 새로 추가되는 정교 분석 점수
    distortion: float
    pick_attack: float
    sustain: float
    fizz: float
    presence: float

@dataclass
class AudioStats:
    duration: float
    sample_rate: int
    rms_mean: float
    rms_std: float
    dynamic_range: float
    spectral_centroid: float
    spectral_bandwidth: float
    spectral_rolloff: float
    zero_crossing_rate: float
    spectral_flatness: float

    low_energy: float
    low_mid_energy: float
    mid_energy: float
    high_mid_energy: float
    presence_energy: float
    air_fizz_energy: float

def analyze_audio(path: str) -> dict[str, Any]:
    """
    기타톤 성향 분석기.

    주의:
    - 실제 장비를 정확히 맞히는 모델이 아니라 오디오 특징 기반 추정값.
    - 무료 서버 안정성을 위해 최대 90초까지만 분석.
    """

    y, sr = librosa.load(path, sr=44100, mono=True, duration=90)

    if y.size == 0:
        raise ValueError("Audio file is empty or could not be decoded.")

    # 앞뒤 무음 제거
    y, _ = librosa.effects.trim(y, top_db=35)

    if len(y) < sr * 3:
        raise ValueError("오디오가 너무 짧거나 무음에 가깝습니다. 최소 3초 이상의 기타 소리를 업로드해 주세요.")

    # 너무 큰 음량 차이를 줄이고 분석 안정화
    y = librosa.util.normalize(y)

    duration = float(librosa.get_duration(y=y, sr=sr))

    # 기본 특징
    rms = librosa.feature.rms(y=y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    flatness = librosa.feature.spectral_flatness(y=y)[0]

    # 피킹 어택 추정
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    attack_raw = float(np.mean(onset_env) + np.percentile(onset_env, 90))

    # STFT 기반 EQ 대역 분석
    n_fft = 4096
    hop_length = 1024
    S_complex = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
    S = np.abs(S_complex) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    low_energy = _band_energy_ratio(S, freqs, 80, 250)
    low_mid_energy = _band_energy_ratio(S, freqs, 250, 700)
    mid_energy = _band_energy_ratio(S, freqs, 700, 1600)
    high_mid_energy = _band_energy_ratio(S, freqs, 1600, 4000)
    presence_energy = _band_energy_ratio(S, freqs, 4000, 7000)
    air_fizz_energy = _band_energy_ratio(S, freqs, 7000, 11000)

    # 통계값
    rms_mean = float(np.mean(rms))
    rms_std = float(np.std(rms))
    dynamic_range = float(np.percentile(rms, 95) - np.percentile(rms, 10))

    centroid_mean = float(np.mean(centroid))
    bandwidth_mean = float(np.mean(bandwidth))
    rolloff_mean = float(np.mean(rolloff))
    zcr_mean = float(np.mean(zcr))
    flatness_mean = float(np.mean(flatness))

    # 기존 recommender.py가 쓰는 값들을 유지하면서 더 정교하게 계산
    gain = (
        0.40 * _score(rms_mean, 0.015, 0.16)
        + 0.30 * _score(flatness_mean, 0.002, 0.08)
        + 0.30 * _score(zcr_mean, 0.025, 0.16)
    )

    brightness = (
        0.45 * _score(centroid_mean, 1000, 4800)
        + 0.30 * _score(presence_energy, 0.02, 0.18)
        + 0.25 * _score(air_fizz_energy, 0.01, 0.16)
    )

    warmth = (
        0.55 * _score(low_energy + low_mid_energy, 0.08, 0.40)
        + 0.25 * _score(low_mid_energy, 0.05, 0.25)
        + 0.20 * (10 - brightness)
    )

    mid_focus = _score(mid_energy + high_mid_energy, 0.18, 0.55)

    low_tightness = (
        0.50 * (10 - _score(low_energy, 0.08, 0.35))
        + 0.50 * _score(high_mid_energy / (low_energy + 1e-9), 0.8, 5.0)
    )

    compression_raw = 1.0 - (dynamic_range / (rms_mean + 1e-9))
    compression = _score(compression_raw, 0.05, 0.85)

    roughness = (
        0.50 * _score(zcr_mean, 0.025, 0.16)
        + 0.30 * _score(flatness_mean, 0.003, 0.08)
        + 0.20 * _score(air_fizz_energy, 0.01, 0.16)
    )

    # 리버브/공간감 추정 개선
    # 핵심: 어택 이후 에너지가 얼마나 오래 남는지, 프레임 간 변화가 얼마나 부드러운지 측정
    rms_safe = rms + 1e-9

    # RMS 변화량이 작으면 소리가 길게 퍼지는 경향이 있음
    rms_delta = np.abs(np.diff(rms_safe))
    smooth_energy = 1.0 - (float(np.mean(rms_delta)) / (float(np.mean(rms_safe)) + 1e-9))
    smooth_energy = _clamp(smooth_energy, 0.0, 1.0)

    # 낮은 레벨의 tail 에너지가 얼마나 많이 남아있는지
    rms_90 = float(np.percentile(rms_safe, 90))
    rms_30 = float(np.percentile(rms_safe, 30))
    tail_ratio = rms_30 / (rms_90 + 1e-9)

    # Onset 이후 잔향 tail 추정
    onset_frames = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        onset_envelope=onset_env,
        units="frames",
        backtrack=False,
    )

    tail_scores = []

    for frame in onset_frames[:30]:
        start = int(frame)
        end = min(start + 45, len(rms_safe))  # 약 1초 전후 tail 관찰
        if end <= start + 5:
            continue

        segment = rms_safe[start:end]
        peak = float(np.max(segment))
        tail = float(np.mean(segment[int(len(segment) * 0.45):]))

        if peak > 1e-6:
            tail_scores.append(tail / peak)

    tail_persistence = float(np.mean(tail_scores)) if tail_scores else tail_ratio

    ambience = (
        0.45 * _score(tail_persistence, 0.08, 0.55)
        + 0.35 * _score(tail_ratio, 0.08, 0.45)
        + 0.20 * _score(smooth_energy, 0.55, 0.98)
    )
    # 새 점수들
    distortion = (
        0.45 * _score(flatness_mean, 0.003, 0.08)
        + 0.35 * _score(zcr_mean, 0.025, 0.16)
        + 0.20 * _score(rms_mean, 0.015, 0.16)
    )

    pick_attack = _score(attack_raw, 0.3, 6.0)

    sustain_raw = rms_mean / (rms_std + 1e-9)
    sustain = _score(sustain_raw, 1.2, 8.0)

    fizz = _score(air_fizz_energy, 0.01, 0.16)

    presence = _score(presence_energy + high_mid_energy, 0.08, 0.35)

    stats = AudioStats(
        duration=round(duration, 2),
        sample_rate=sr,
        rms_mean=round(rms_mean, 5),
        rms_std=round(rms_std, 5),
        dynamic_range=round(dynamic_range, 5),
        spectral_centroid=round(centroid_mean, 2),
        spectral_bandwidth=round(bandwidth_mean, 2),
        spectral_rolloff=round(rolloff_mean, 2),
        zero_crossing_rate=round(zcr_mean, 5),
        spectral_flatness=round(flatness_mean, 5),
        low_energy=round(low_energy, 5),
        low_mid_energy=round(low_mid_energy, 5),
        mid_energy=round(mid_energy, 5),
        high_mid_energy=round(high_mid_energy, 5),
        presence_energy=round(presence_energy, 5),
        air_fizz_energy=round(air_fizz_energy, 5),
    )

    scores = ToneScores(
        gain=round(_clamp(gain), 1),
        brightness=round(_clamp(brightness), 1),
        warmth=round(_clamp(warmth), 1),
        mid_focus=round(_clamp(mid_focus), 1),
        low_tightness=round(_clamp(low_tightness), 1),
        compression=round(_clamp(compression), 1),
        roughness=round(_clamp(roughness), 1),
        ambience=round(_clamp(ambience), 1),
        distortion=round(_clamp(distortion), 1),
        pick_attack=round(_clamp(pick_attack), 1),
        sustain=round(_clamp(sustain), 1),
        fizz=round(_clamp(fizz), 1),
        presence=round(_clamp(presence), 1),
    )

    eq_profile = {
        "low": round(low_energy * 10, 2),
        "low_mid": round(low_mid_energy * 10, 2),
        "mid": round(mid_energy * 10, 2),
        "high_mid": round(high_mid_energy * 10, 2),
        "presence": round(presence_energy * 10, 2),
        "air_fizz": round(air_fizz_energy * 10, 2),
    }

    return {
        "stats": asdict(stats),
        "scores": asdict(scores),
        "eq_profile": eq_profile,
    }
