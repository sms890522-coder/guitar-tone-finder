from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import librosa
import numpy as np


STANDARD_TUNING = {
    "E": 40,  # 6th string low E2
    "A": 45,
    "D": 50,
    "G": 55,
    "B": 59,
    "e": 64,  # 1st string high E4
}

STRING_ORDER = ["e", "B", "G", "D", "A", "E"]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if math.isnan(value) or math.isinf(value):
        return low
    return max(low, min(high, value))


def _hz_to_midi(freq: float) -> int | None:
    if freq <= 0 or math.isnan(freq) or math.isinf(freq):
        return None

    midi = int(round(69 + 12 * math.log2(freq / 440.0)))

    # 기타 표준 튜닝에서 현실적으로 자주 쓰는 범위
    # E2(40) ~ E6(88)
    if midi < 40 or midi > 88:
        return None

    return midi


def _midi_to_note_name(midi: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi // 12) - 1
    return f"{names[midi % 12]}{octave}"


def _midi_to_tab_position(
    midi: int,
    preferred_position: int = 5,
    max_fret: int = 22,
) -> dict[str, Any] | None:
    """
    하나의 MIDI 음을 기타 줄/프렛 후보로 변환.
    같은 음이 여러 위치에 있을 수 있으므로,
    preferred_position 근처의 프렛을 우선 선택한다.
    """

    candidates = []

    for string_name, open_midi in STANDARD_TUNING.items():
        fret = midi - open_midi
        if 0 <= fret <= max_fret:
            # 낮은 줄보다 중간 포지션을 우선
            position_penalty = abs(fret - preferred_position)
            open_string_penalty = 1.5 if fret == 0 else 0.0

            # 너무 높은 프렛은 약간 감점
            high_fret_penalty = 0.5 if fret >= 17 else 0.0

            score = position_penalty + open_string_penalty + high_fret_penalty

            candidates.append(
                {
                    "string": string_name,
                    "fret": fret,
                    "score": score,
                }
            )

    if not candidates:
        return None

    candidates.sort(key=lambda item: item["score"])
    best = candidates[0]

    return {
        "string": best["string"],
        "fret": best["fret"],
    }


def _merge_repeated_notes(notes: list[dict[str, Any]], min_gap: float = 0.08) -> list[dict[str, Any]]:
    """
    너무 촘촘하게 같은 음이 반복되는 경우 보기 좋게 병합.
    """
    if not notes:
        return []

    merged = [notes[0]]

    for note in notes[1:]:
        prev = merged[-1]

        same_pitch = note["midi"] == prev["midi"]
        close_time = note["start"] - prev["end"] <= min_gap

        if same_pitch and close_time:
            prev["end"] = note["end"]
            prev["duration"] = round(prev["end"] - prev["start"], 3)
            prev["confidence"] = max(prev["confidence"], note["confidence"])
        else:
            merged.append(note)

    return merged


def _build_ascii_tab(notes: list[dict[str, Any]], max_width: int = 96) -> str:
    """
    간단한 텍스트 타브 생성.
    시간 간격을 대략적인 칸 간격으로 변환한다.
    """

    if not notes:
        return "\n".join([f"{s}|-" for s in STRING_ORDER])

    total_duration = max(note["end"] for note in notes)
    total_duration = max(total_duration, 1.0)

    # 너무 긴 파일은 가독성을 위해 너비 제한
    width = min(max_width, max(32, int(total_duration * 8)))

    lines = {s: ["-"] * width for s in STRING_ORDER}

    for note in notes:
        string_name = note["string"]
        fret_text = str(note["fret"])

        col = int((note["start"] / total_duration) * (width - 2))
        col = max(0, min(width - len(fret_text), col))

        # 프렛 숫자 삽입
        for i, char in enumerate(fret_text):
            if col + i < width:
                lines[string_name][col + i] = char

    return "\n".join([f"{s}|{''.join(lines[s])}|" for s in STRING_ORDER])


def analyze_tab(path: str) -> dict[str, Any]:
    """
    단음 리프용 타브 초안 생성기.

    한계:
    - 단음 리프/멜로디에 최적화
    - 코드, 빠른 솔로, 벤딩/비브라토/슬라이드는 정확하지 않을 수 있음
    - 기타 단독 소스일수록 정확함
    """

    y, sr = librosa.load(path, sr=22050, mono=True, duration=30)

    if y.size == 0:
        raise ValueError("Audio file is empty or could not be decoded.")

    y, _ = librosa.effects.trim(y, top_db=35)

    if len(y) < sr * 2:
        raise ValueError("오디오가 너무 짧거나 무음에 가깝습니다. 최소 2초 이상의 단음 리프를 업로드해 주세요.")

    duration = float(librosa.get_duration(y=y, sr=sr))

    # 너무 작은 소스 보정
    rms = float(np.sqrt(np.mean(y ** 2)) + 1e-9)
    if rms < 0.06:
        gain = min(0.06 / rms, 6.0)
        y = y * gain
        peak = float(np.max(np.abs(y)) + 1e-9)
        if peak > 0.98:
            y = y / peak * 0.98

    hop_length = 512

    # onset으로 음 시작점 감지
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_frames = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        onset_envelope=onset_env,
        hop_length=hop_length,
        units="frames",
        backtrack=True,
        delta=0.18,
        wait=3,
    )

    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)

    # pitch 추정
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("E2"),
        fmax=librosa.note_to_hz("E6"),
        sr=sr,
        hop_length=hop_length,
    )

    frame_times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)

    # onset이 너무 적으면 일정 간격으로 보조 분할
    if len(onset_times) < 2:
        onset_times = np.arange(0, duration, 0.5)

    notes: list[dict[str, Any]] = []
    previous_position: dict[str, Any] | None = None
    
    for index, start_time in enumerate(onset_times):
        end_time = onset_times[index + 1] if index + 1 < len(onset_times) else min(duration, start_time + 0.75)
    
        note_duration = float(end_time - start_time)
    
        # 너무 짧은 구간은 스킵
        if note_duration < 0.07:
            continue
    
        frame_idx = np.where((frame_times >= start_time) & (frame_times < end_time))[0]
    
        if len(frame_idx) == 0:
            continue
    
        segment_f0 = f0[frame_idx]
        segment_prob = voiced_prob[frame_idx] if voiced_prob is not None else np.ones_like(segment_f0)
    
        freq, confidence = _stable_pitch_from_segment(
            segment_f0,
            segment_prob,
            min_confidence=0.55,
        )
    
        if freq is None:
            continue
    
        if confidence < 0.50:
            continue
    
        midi = _hz_to_midi(freq)
    
        if midi is None:
            continue
    
        position = _midi_to_tab_position_with_context(
            midi,
            previous_position=previous_position,
            preferred_position=5,
            max_fret=22,
        )
    
        if position is None:
            continue
    
        note = {
            "start": round(float(start_time), 3),
            "end": round(float(end_time), 3),
            "duration": round(note_duration, 3),
            "frequency": round(freq, 2),
            "midi": midi,
            "note": _midi_to_note_name(midi),
            "string": position["string"],
            "fret": position["fret"],
            "confidence": round(_clamp(confidence), 2),
        }
    
        notes.append(note)
        previous_position = position
        
    notes = _remove_tiny_glitches(notes)
    notes = _smooth_octave_errors(notes)
    
    # 옥타브 보정 후 줄/프렛 다시 계산
    repositioned_notes: list[dict[str, Any]] = []
    previous_position = None
    
    for note in notes:
        position = _midi_to_tab_position_with_context(
            note["midi"],
            previous_position=previous_position,
            preferred_position=5,
            max_fret=22,
        )
    
        if position is None:
            continue
    
        note["string"] = position["string"]
        note["fret"] = position["fret"]
        repositioned_notes.append(note)
        previous_position = position
    
    notes = _merge_repeated_notes(repositioned_notes, min_gap=0.10)
    notes = _remove_tiny_glitches(notes)
    
    # 너무 많은 음이면 앞쪽 100개까지만
    notes = notes[:100]
    
    tab = _build_ascii_tab(notes)
    confidence_avg = round(float(np.mean([n["confidence"] for n in notes])) if notes else 0.0, 2)

    warnings: list[str] = []

    if not notes:
        warnings.append("명확한 단음 피치를 찾지 못했습니다. 기타 단독 단음 리프 파일을 사용해 주세요.")

    if duration > 30:
        warnings.append("타브 초안은 30초 이하 클립에서 가장 안정적입니다.")

    if confidence_avg < 0.6:
        warnings.append("피치 추정 신뢰도가 낮습니다. 디스토션, 코드, 배경 악기가 많으면 부정확할 수 있습니다.")

    return {
        "version": "tab-draft-v2",
        "duration": round(duration, 2),
        "tuning": "Standard EADGBE",
        "note_count": len(notes),
        "confidence": confidence_avg,
        "tab": tab,
        "notes": notes,
        "warnings": warnings,
        "debug": {
            "onset_count": int(len(onset_times)),
            "raw_note_count": int(len(notes)),
            "pitch_method": "librosa.pyin + stable segment median",
            "position_strategy": "context aware preferred position 5",
        },
        "disclaimer": "이 타브는 단음 리프/멜로디를 오디오에서 추정한 초안입니다. 코드, 벤딩, 비브라토, 빠른 솔로는 정확하지 않을 수 있습니다.",
    }

def _stable_pitch_from_segment(
    f0_values: np.ndarray,
    prob_values: np.ndarray,
    min_confidence: float = 0.55,
) -> tuple[float | None, float]:
    """
    한 음 구간에서 안정적인 pitch만 골라 대표 주파수를 반환.
    pyin 결과에는 흔들리는 값이 많아서 전체 median보다 안정 구간만 쓰는 게 낫다.
    """
    if len(f0_values) == 0:
        return None, 0.0

    valid = np.where((~np.isnan(f0_values)) & (prob_values >= min_confidence))[0]

    if len(valid) < 2:
        valid = np.where(~np.isnan(f0_values))[0]

    if len(valid) == 0:
        return None, 0.0

    valid_f0 = f0_values[valid]
    valid_prob = prob_values[valid]

    midi_values = []
    for freq in valid_f0:
        midi = _hz_to_midi(float(freq))
        if midi is not None:
            midi_values.append(midi)

    if not midi_values:
        return None, 0.0

    # 가장 많이 나온 MIDI 음을 대표 pitch로 사용
    midi_array = np.array(midi_values)
    unique, counts = np.unique(midi_array, return_counts=True)
    dominant_midi = int(unique[np.argmax(counts)])

    # dominant midi 주변 주파수만 다시 모음
    selected_freqs = []
    selected_probs = []

    for freq, prob in zip(valid_f0, valid_prob):
        midi = _hz_to_midi(float(freq))
        if midi is not None and abs(midi - dominant_midi) <= 1:
            selected_freqs.append(float(freq))
            selected_probs.append(float(prob))

    if not selected_freqs:
        return None, 0.0

    confidence = float(np.median(selected_probs))
    freq = float(np.median(selected_freqs))

    return freq, confidence


def _midi_to_tab_position_with_context(
    midi: int,
    previous_position: dict[str, Any] | None = None,
    preferred_position: int = 5,
    max_fret: int = 22,
) -> dict[str, Any] | None:
    """
    이전 음의 줄/프렛과 가까운 위치를 선호해서 타브가 튀지 않게 만든다.
    """
    candidates = []

    string_index_map = {name: index for index, name in enumerate(STRING_ORDER)}

    for string_name, open_midi in STANDARD_TUNING.items():
        fret = midi - open_midi

        if 0 <= fret <= max_fret:
            position_penalty = abs(fret - preferred_position) * 0.55
            open_string_penalty = 1.2 if fret == 0 else 0.0
            high_fret_penalty = 0.6 if fret >= 17 else 0.0

            context_penalty = 0.0

            if previous_position:
                prev_string = previous_position.get("string")
                prev_fret = previous_position.get("fret")

                if prev_string in string_index_map and isinstance(prev_fret, int):
                    string_jump = abs(string_index_map[string_name] - string_index_map[prev_string])
                    fret_jump = abs(fret - prev_fret)

                    context_penalty = string_jump * 0.8 + fret_jump * 0.25

            score = position_penalty + open_string_penalty + high_fret_penalty + context_penalty

            candidates.append(
                {
                    "string": string_name,
                    "fret": fret,
                    "score": score,
                }
            )

    if not candidates:
        return None

    candidates.sort(key=lambda item: item["score"])

    return {
        "string": candidates[0]["string"],
        "fret": candidates[0]["fret"],
    }


def _remove_tiny_glitches(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    너무 짧고 신뢰도 낮은 음 제거.
    """
    cleaned = []

    for note in notes:
        duration = float(note.get("duration", 0.0))
        confidence = float(note.get("confidence", 0.0))

        if duration < 0.08 and confidence < 0.72:
            continue

        cleaned.append(note)

    return cleaned


def _smooth_octave_errors(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    pyin이 가끔 한 옥타브 위/아래로 튀는 문제 완화.
    앞뒤 음과 비교해서 12반음 차이로 갑자기 튀면 보정.
    """
    if len(notes) < 3:
        return notes

    smoothed = [dict(note) for note in notes]

    for i in range(1, len(smoothed) - 1):
        prev_midi = smoothed[i - 1]["midi"]
        curr_midi = smoothed[i]["midi"]
        next_midi = smoothed[i + 1]["midi"]

        # 현재 음만 한 옥타브 튄 경우
        if abs(curr_midi - prev_midi) >= 11 and abs(curr_midi - next_midi) >= 11:
            down = curr_midi - 12
            up = curr_midi + 12

            if abs(down - prev_midi) < abs(curr_midi - prev_midi) and 40 <= down <= 88:
                smoothed[i]["midi"] = down
            elif abs(up - prev_midi) < abs(curr_midi - prev_midi) and 40 <= up <= 88:
                smoothed[i]["midi"] = up

            smoothed[i]["note"] = _midi_to_note_name(smoothed[i]["midi"])

    return smoothed

