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


def _safe_mean(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


def _safe_median(values: list[float] | np.ndarray) -> float:
    if len(values) == 0:
        return 0.0
    return float(np.median(values))


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
    distortion: float
    pick_attack: float
    sustain: float
    fizz: float
    presence: float

    # v6 detail scores
    body: float
    mud: float
    core_mid: float
    upper_mid: float
    air: float
    clarity: float
    scoop: float
    bite: float
    high_gain_likelihood: float
    lead_gain_likelihood: float

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

    sub_bass_energy: float
    bass_energy: float
    mud_energy: float
    warm_body_energy: float
    core_mid_energy: float
    upper_mid_energy: float
    presence_energy: float
    fizz_energy: float
    air_energy: float


def analyze_audio(path: str) -> dict[str, Any]:
    """
    Guitar tone analyzer v6.

    목표:
    - 전체 평균만 보는 단순 분석에서 벗어나 주파수 대역을 세분화한다.
    - Warmth와 Mud, Brightness와 Fizz, Sustain과 Reverb를 구분한다.
    - 실제 장비 판별이 아니라 비슷한 톤 세팅을 위한 특징 추정값이다.
    """

    y, sr = librosa.load(path, sr=44100, mono=True, duration=90)

    if y.size == 0:
        raise ValueError("Audio file is empty or could not be decoded.")

    # 앞뒤 무음 제거
    y, _ = librosa.effects.trim(y, top_db=35)

    if len(y) < sr * 3:
        raise ValueError("오디오가 너무 짧거나 무음에 가깝습니다. 최소 3초 이상의 기타 소리를 업로드해 주세요.")

    duration = float(librosa.get_duration(y=y, sr=sr))

    # 기본 특징
    rms = librosa.feature.rms(y=y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    flatness = librosa.feature.spectral_flatness(y=y)[0]

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    # STFT 기반 대역 분석
    n_fft = 4096
    hop_length = 1024
    S_complex = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
    S = np.abs(S_complex) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # v6 세분화 대역
    sub_bass_energy = _band_energy_ratio(S, freqs, 40, 80)
    bass_energy = _band_energy_ratio(S, freqs, 80, 160)
    mud_energy = _band_energy_ratio(S, freqs, 160, 350)
    warm_body_energy = _band_energy_ratio(S, freqs, 350, 800)
    core_mid_energy = _band_energy_ratio(S, freqs, 800, 1600)
    upper_mid_energy = _band_energy_ratio(S, freqs, 1600, 3500)
    presence_energy = _band_energy_ratio(S, freqs, 3500, 6500)
    fizz_energy = _band_energy_ratio(S, freqs, 6500, 10000)
    air_energy = _band_energy_ratio(S, freqs, 10000, 14000)

    # 기존 UI/추천 로직과의 호환용 eq_profile 대역
    low_energy = sub_bass_energy + bass_energy
    low_mid_energy = mud_energy + warm_body_energy
    mid_energy = core_mid_energy
    high_mid_energy = upper_mid_energy

    # 통계값
    rms_mean = _safe_mean(rms)
    rms_std = float(np.std(rms))
    dynamic_range = float(np.percentile(rms, 95) - np.percentile(rms, 10))

    centroid_mean = _safe_mean(centroid)
    bandwidth_mean = _safe_mean(bandwidth)
    rolloff_mean = _safe_mean(rolloff)
    zcr_mean = _safe_mean(zcr)
    flatness_mean = _safe_mean(flatness)

    # -----------------------------
    # 세부 점수
    # -----------------------------

    # Mud: 160~350Hz가 과하면 뭉침/먹먹함
    mud = _score(mud_energy, 0.06, 0.24)

    # Body: 따뜻한 몸통감. mud는 조금 감점.
    body = (
        0.75 * _score(warm_body_energy, 0.07, 0.28)
        + 0.25 * _score(core_mid_energy, 0.08, 0.25)
        - 0.25 * mud
    )
    body = _clamp(body)

    core_mid = _score(core_mid_energy, 0.08, 0.28)
    upper_mid = _score(upper_mid_energy, 0.07, 0.26)
    presence = _score(presence_energy, 0.025, 0.16)
    fizz = _score(fizz_energy, 0.01, 0.11)
    air = _score(air_energy, 0.002, 0.04)

    # Brightness는 fizz보다 upper_mid/presence 중심.
    brightness = (
        0.40 * upper_mid
        + 0.40 * presence
        + 0.15 * _score(centroid_mean, 1200, 4800)
        + 0.05 * air
        - 0.15 * mud
    )
    brightness = _clamp(brightness)

    # Warmth는 저음 양이 아니라 warm body 중심. mud가 너무 높으면 감점.
    warmth = (
        0.65 * body
        + 0.25 * _score(warm_body_energy + core_mid_energy, 0.14, 0.42)
        + 0.10 * (10 - brightness)
        - 0.25 * max(0.0, mud - 6.0)
    )
    warmth = _clamp(warmth)

    # Mid focus는 core_mid + upper_mid 중심.
    mid_focus = (
        0.55 * core_mid
        + 0.35 * upper_mid
        + 0.10 * presence
    )
    mid_focus = _clamp(mid_focus)

    # Scoop: 미드가 빠지고 저역/고역이 상대적으로 두드러진 정도
    edge_energy = low_energy + presence_energy + fizz_energy
    mid_energy_total = core_mid_energy + upper_mid_energy + warm_body_energy
    scoop = _score(edge_energy / (mid_energy_total + 1e-9), 0.4, 2.2)

    # Clarity: presence/upper_mid는 살리고 mud/fizz 과다는 감점
    clarity = (
        0.40 * presence
        + 0.35 * upper_mid
        + 0.15 * air
        - 0.30 * mud
        - 0.15 * max(0.0, fizz - 6.0)
    )
    clarity = _clamp(clarity)

    # Bite: 피킹이 물리는 느낌. upper_mid/presence/onset 중심
    attack_raw = float(np.mean(onset_env) + np.percentile(onset_env, 90))
    attack_score = _score(attack_raw, 0.3, 6.0)

    bite = (
        0.45 * attack_score
        + 0.35 * upper_mid
        + 0.20 * presence
        - 0.20 * mud
    )
    bite = _clamp(bite)

    # Compression
    compression_raw = 1.0 - (dynamic_range / (rms_mean + 1e-9))
    compression = _score(compression_raw, 0.05, 0.85)

    # Distortion은 볼륨보다 flatness/zcr/compression 중심으로 조정
    distortion = (
        0.38 * _score(flatness_mean, 0.003, 0.08)
        + 0.28 * _score(zcr_mean, 0.025, 0.16)
        + 0.22 * compression
        + 0.12 * fizz
    )
    distortion = _clamp(distortion)

    # Gain은 RMS 비중을 낮추고 distortion/saturation 중심
    rms_score = _score(rms_mean, 0.015, 0.16)
    gain = (
        0.18 * rms_score
        + 0.38 * distortion
        + 0.24 * compression
        + 0.20 * _score(flatness_mean, 0.003, 0.08)
    )
    gain = _clamp(gain)

    roughness = (
        0.35 * distortion
        + 0.30 * fizz
        + 0.20 * _score(zcr_mean, 0.025, 0.16)
        + 0.15 * _score(flatness_mean, 0.003, 0.08)
    )
    roughness = _clamp(roughness)

    
    # Low Tightness:
    # mud가 많으면 감점, bite/upper_mid가 있으면 가점, bass가 과하면 감점
    bass_weight = _score(bass_energy + sub_bass_energy, 0.05, 0.25)
    low_tightness = (
        0.35 * bite
        + 0.30 * clarity
        + 0.25 * _score(upper_mid_energy / (bass_energy + mud_energy + 1e-9), 0.4, 3.0)
        + 0.10 * _score(core_mid_energy / (mud_energy + 1e-9), 0.5, 3.0)
        - 0.35 * mud
        - 0.15 * bass_weight
    )
    low_tightness = _clamp(low_tightness)

    # Sustain
    sustain_raw = rms_mean / (rms_std + 1e-9)
    sustain = _score(sustain_raw, 1.2, 8.0)

    # -----------------------------
    # High Gain Likelihood
    # -----------------------------
    # 일반 gain/distortion 점수가 낮게 나와도,
    # 하이게인 특유의 압축감, 서스테인, 중고역 밀도, 다이내믹 억제를 감지하기 위한 별도 점수.

    rms_p95 = float(np.percentile(rms, 95))
    rms_p50 = float(np.percentile(rms, 50))
    rms_p20 = float(np.percentile(rms, 20))

    # 다이내믹이 좁으면 하이게인/컴프레션 가능성
    density_dynamic = 1.0 - ((rms_p95 - rms_p20) / (rms_p95 + 1e-9))
    density_dynamic_score = _score(density_dynamic, 0.25, 0.88)

    # 중고역 밀도: 하이게인 리프/리드에서 core_mid~presence가 촘촘한 경우가 많음
    driven_band_density = _score(
        core_mid_energy + upper_mid_energy + presence_energy,
        0.16,
        0.55,
    )

    # 캐비넷/IR로 fizz가 정리된 하이게인도 있으므로 fizz 비중은 낮게
    saturation_density = (
        0.30 * compression
        + 0.22 * sustain
        + 0.22 * driven_band_density
        + 0.14 * roughness
        + 0.08 * fizz
        + 0.04 * presence
    )

    high_gain_likelihood = (
        0.45 * saturation_density
        + 0.35 * density_dynamic_score
        + 0.20 * distortion
    )

    # 하이게인 보정 규칙
    if compression >= 6.5 and sustain >= 6.0 and driven_band_density >= 5.5:
        high_gain_likelihood = max(high_gain_likelihood, 7.0)

    if roughness >= 6.0 and compression >= 6.0:
        high_gain_likelihood = max(high_gain_likelihood, 6.8)

    if distortion >= 6.0 and driven_band_density >= 6.0:
        high_gain_likelihood = max(high_gain_likelihood, 7.0)
    
    # 추가 하이게인 보정 v2
    # fizz가 적어도 중고역 밀도 + 압축 + sustain이 있으면 하이게인 가능성 높음
    if driven_band_density >= 6.8 and compression >= 5.5 and sustain >= 5.5:
        high_gain_likelihood = max(high_gain_likelihood, 7.2)

    # 캐비넷/IR로 고역이 정리된 부드러운 하이게인
    if core_mid >= 6.5 and upper_mid >= 5.5 and compression >= 5.8 and distortion >= 4.8:
        high_gain_likelihood = max(high_gain_likelihood, 7.0)

    # 미드가 강하고 sustain이 긴 록/리드 하이게인
    if mid_focus >= 6.5 and sustain >= 6.2 and compression >= 5.5:
        high_gain_likelihood = max(high_gain_likelihood, 6.9)

    # roughness가 낮아도 compression과 band density가 높으면 드라이브 가능성
    if roughness < 5.0 and compression >= 6.5 and driven_band_density >= 6.5:
        high_gain_likelihood = max(high_gain_likelihood, 6.8)

    # 팜뮤트/리프 계열: 타이트함 + bite + 중고역 밀도
    if low_tightness >= 6.5 and bite >= 5.8 and driven_band_density >= 6.0:
        high_gain_likelihood = max(high_gain_likelihood, 6.9)

    # 클린톤 오판 방지:
    # brightness만 높고 compression/sustain이 낮으면 하이게인으로 올리지 않음
    # 클린톤 보호:
    # 단순히 compression/sustain/distortion만 낮다고 바로 클린으로 누르지 말고,
    # 중고역 밀도와 bite도 낮을 때만 클린으로 제한한다.
    if (
        compression < 3.5
        and sustain < 4.0
        and distortion < 4.5
        and driven_band_density < 4.5
        and bite < 4.5
    ):
        high_gain_likelihood = min(high_gain_likelihood, 4.0)

    high_gain_likelihood = _clamp(high_gain_likelihood)

    # -----------------------------
    # Lead Gain Likelihood
    # -----------------------------
    # 솔로/리드톤은 리듬톤보다 저역 타이트함, 팜뮤트, roughness가 약하게 잡힐 수 있다.
    # 대신 sustain, compression, upper_mid/presence, smooth distortion을 더 중요하게 본다.

    lead_band_density = _score(
        upper_mid_energy + presence_energy + core_mid_energy,
        0.12,
        0.42,
    )

    singing_mid_score = (
        0.40 * core_mid
        + 0.35 * upper_mid
        + 0.25 * presence
    )

    smooth_lead_saturation = (
        0.30 * sustain
        + 0.25 * compression
        + 0.20 * distortion
        + 0.15 * singing_mid_score
        + 0.10 * lead_band_density
    )

    # 리드톤은 attack이 너무 강하지 않아도, sustain과 mid가 있으면 하이게인일 수 있음
    lead_gain_likelihood = (
        0.45 * smooth_lead_saturation
        + 0.25 * high_gain_likelihood
        + 0.20 * sustain
        + 0.10 * compression
    )

    # 솔로 하이게인 보정:
    # sustain + compression + 미드/프레즌스가 높으면 리드 하이게인 가능성
    if sustain >= 6.2 and compression >= 5.2 and singing_mid_score >= 5.8:
        lead_gain_likelihood = max(lead_gain_likelihood, 7.0)

    if sustain >= 7.0 and distortion >= 4.8 and presence >= 5.0:
        lead_gain_likelihood = max(lead_gain_likelihood, 7.2)

    if core_mid >= 6.2 and upper_mid >= 5.2 and sustain >= 6.0:
        lead_gain_likelihood = max(lead_gain_likelihood, 6.8)

    # 딜레이/리버브가 있어도 리드톤은 하이게인일 수 있음
    # ambience가 높다고 gain 판단을 낮추지 않는다.
    if sustain >= 6.5 and lead_band_density >= 5.5 and compression >= 5.0:
        lead_gain_likelihood = max(lead_gain_likelihood, 6.9)

    # 클린 솔로 보호:
    # sustain은 길지만 distortion/compression이 낮으면 클린 리드일 수 있음
    if distortion < 3.8 and compression < 4.2 and high_gain_likelihood < 4.5:
        lead_gain_likelihood = min(lead_gain_likelihood, 4.8)

    lead_gain_likelihood = _clamp(lead_gain_likelihood)
    

    pick_attack = bite

    # -----------------------------
    # 공간계 분석 v6
    # -----------------------------
    rms_safe = rms + 1e-9

    dry_sustain = sustain

    compression_like = compression
    distortion_like = distortion

    onset_frames = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        onset_envelope=onset_env,
        units="frames",
        backtrack=False,
    )

    tail_ratios = []
    decay_slopes = []

    for frame in onset_frames[:45]:
        start = int(frame)
        end = min(start + 70, len(rms_safe))

        if end <= start + 12:
            continue

        segment = rms_safe[start:end]
        peak = float(np.max(segment))

        if peak <= 1e-6:
            continue

        middle = float(np.mean(segment[int(len(segment) * 0.35): int(len(segment) * 0.55)]))
        late = float(np.mean(segment[int(len(segment) * 0.72):]))

        tail_ratios.append(late / (peak + 1e-9))
        decay_slopes.append(late / (middle + 1e-9))

    tail_persistence = _safe_median(tail_ratios)
    tail_decay_smoothness = _safe_median(decay_slopes)

    rms_95 = float(np.percentile(rms_safe, 95))
    rms_30 = float(np.percentile(rms_safe, 30))
    rms_20 = float(np.percentile(rms_safe, 20))
    rms_10 = float(np.percentile(rms_safe, 10))

    global_tail_ratio = rms_20 / (rms_95 + 1e-9)
    low_floor_ratio = rms_10 / (rms_95 + 1e-9)
    room_floor_ratio = rms_30 / (rms_95 + 1e-9)

    reverb_tail_raw = (
        0.55 * _score(tail_persistence, 0.30, 0.72)
        + 0.30 * _score(tail_decay_smoothness, 0.42, 0.88)
        + 0.15 * _score(global_tail_ratio, 0.20, 0.50)
    )

    room_wetness_raw = (
        0.45 * _score(room_floor_ratio, 0.18, 0.50)
        + 0.35 * _score(low_floor_ratio, 0.06, 0.25)
        + 0.20 * _score(bandwidth_mean, 1200, 4500)
    )

    delay_echo = 0.0
    if len(onset_frames) >= 4:
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        intervals = np.diff(onset_times)
        intervals = intervals[(intervals >= 0.12) & (intervals <= 1.2)]

        if len(intervals) >= 3:
            interval_std = float(np.std(intervals))
            interval_mean = float(np.mean(intervals))
            regularity = 1.0 - (interval_std / (interval_mean + 1e-9))
            regularity = _clamp(regularity, 0.0, 1.0)

            delay_echo = (
                0.60 * _score(regularity, 0.35, 0.90)
                + 0.40 * _score(tail_persistence, 0.24, 0.65)
            )

    dry_penalty = 0.0
    dry_penalty += dry_sustain * 0.55
    dry_penalty += compression_like * 0.30
    dry_penalty += distortion_like * 0.25

    if tail_persistence < 0.40:
        dry_penalty += 1.6

    if global_tail_ratio < 0.26:
        dry_penalty += 1.2

    if dry_sustain >= 6.0 and reverb_tail_raw < 6.5:
        dry_penalty += 1.8

    adjusted_reverb_tail = _clamp(reverb_tail_raw - dry_penalty)
    adjusted_room_wetness = _clamp(room_wetness_raw - (dry_penalty * 0.45))

    ambience = (
        0.55 * adjusted_reverb_tail
        + 0.30 * adjusted_room_wetness
        + 0.15 * delay_echo
    )

    if adjusted_reverb_tail < 4.0 and adjusted_room_wetness < 4.0:
        ambience *= 0.55

    ambience = _clamp(ambience)

    # -----------------------------
    # 결과 구성
    # -----------------------------
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
        sub_bass_energy=round(sub_bass_energy, 5),
        bass_energy=round(bass_energy, 5),
        mud_energy=round(mud_energy, 5),
        warm_body_energy=round(warm_body_energy, 5),
        core_mid_energy=round(core_mid_energy, 5),
        upper_mid_energy=round(upper_mid_energy, 5),
        presence_energy=round(presence_energy, 5),
        fizz_energy=round(fizz_energy, 5),
        air_energy=round(air_energy, 5),
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
        body=round(_clamp(body), 1),
        mud=round(_clamp(mud), 1),
        core_mid=round(_clamp(core_mid), 1),
        upper_mid=round(_clamp(upper_mid), 1),
        air=round(_clamp(air), 1),
        clarity=round(_clamp(clarity), 1),
        scoop=round(_clamp(scoop), 1),
        bite=round(_clamp(bite), 1),
        high_gain_likelihood=round(_clamp(high_gain_likelihood), 1),
        lead_gain_likelihood=round(_clamp(lead_gain_likelihood), 1),
    )

    eq_profile = {
        "sub_bass": round(sub_bass_energy * 10, 2),
        "bass": round(bass_energy * 10, 2),
        "mud": round(mud_energy * 10, 2),
        "warm_body": round(warm_body_energy * 10, 2),
        "core_mid": round(core_mid_energy * 10, 2),
        "upper_mid": round(upper_mid_energy * 10, 2),
        "presence": round(presence_energy * 10, 2),
        "fizz": round(fizz_energy * 10, 2),
        "air": round(air_energy * 10, 2),

        # 기존 프론트/추천 호환용 이름
        "low": round(low_energy * 10, 2),
        "low_mid": round(low_mid_energy * 10, 2),
        "mid": round(mid_energy * 10, 2),
        "high_mid": round(high_mid_energy * 10, 2),
        "air_fizz": round(fizz_energy * 10, 2),
    }

    space_profile = {
        "ambience": round(_clamp(ambience), 1),
        "reverb_tail": round(_clamp(adjusted_reverb_tail), 1),
        "dry_sustain": round(_clamp(dry_sustain), 1),
        "room_wetness": round(_clamp(adjusted_room_wetness), 1),
        "delay_echo": round(_clamp(delay_echo), 1),
    }

    debug_space = {
        "tail_persistence": round(tail_persistence, 4),
        "tail_decay_smoothness": round(tail_decay_smoothness, 4),
        "global_tail_ratio": round(global_tail_ratio, 4),
        "low_floor_ratio": round(low_floor_ratio, 4),
        "room_floor_ratio": round(room_floor_ratio, 4),
        "raw_reverb_tail": round(reverb_tail_raw, 2),
        "raw_room_wetness": round(room_wetness_raw, 2),
        "dry_sustain": round(dry_sustain, 2),
        "compression_like": round(compression_like, 2),
        "distortion_like": round(distortion_like, 2),
        "dry_penalty": round(dry_penalty, 2),
        "delay_echo": round(delay_echo, 2),
        "final_ambience": round(_clamp(ambience), 2),
    }

    return {
        "version": "tone-analysis-v6",
        "stats": asdict(stats),
        "scores": asdict(scores),
        "eq_profile": eq_profile,
        "space": space_profile,
        "debug_space": debug_space,
    }
