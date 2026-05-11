from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import time


BASE_DIR = Path(__file__).resolve().parent
GE250_TEMPLATE_PATH = BASE_DIR / "preset_templates" / "ge250_base.mo"


def _clamp_int(value: float, low: int = 0, high: int = 100) -> int:
    try:
        value = float(value)
    except Exception:
        return low

    return int(max(low, min(high, round(value))))


def _score_to_100(value: Any, default: int = 50) -> int:
    """
    ToneScope 내부 점수 0~10 값을 GE250 0~100 값으로 변환.
    이미 100 단위에 가까운 값이면 그대로 보정.
    """
    try:
        number = float(value)
    except Exception:
        return default

    if number <= 10:
        return _clamp_int(number * 10)

    return _clamp_int(number)


def _safe_preset_name(name: str) -> str:
    name = name.strip() or "ToneScope GE250"
    name = re.sub(r"[^\w가-힣 \-]", "", name)
    return name[:24]


def _pick_amp_type(recommendation: dict[str, Any], scores: dict[str, Any]) -> int:
    text = " ".join(
        [
            str(recommendation.get("tone_type", "")),
            str(recommendation.get("amp_family", "")),
            str(recommendation.get("amp_model", "")),
            " ".join(recommendation.get("amp_examples", []) or []),
        ]
    ).lower()

    rectifier = float(scores.get("rectifier_likelihood", 0) or 0)
    high_gain = float(scores.get("high_gain_likelihood", 0) or 0)

    if "soldano" in text or "slo" in text:
        return 82

    if "rect" in text or "rectifier" in text or "mesa" in text or "boogie" in text or "dual" in text or rectifier >= 4:
        return 71

    if "dark" in text or "terror" in text or "orange" in text:
        return 22

    if "5150" in text or "evh" in text or "peavey" in text:
        return 44

    if "mark" in text:
        return 16

    if "jcm" in text or "j800" in text:
        return 6

    if "plexi" in text:
        return 8

    if "engl" in text or "e650" in text:
        return 10

    if "clean" in text or "twin" in text or "fender" in text:
        return 32

    if high_gain >= 6:
        return 71

    return 20



def _pick_cab_type(recommendation: dict[str, Any], scores: dict[str, Any]) -> int:
    text = " ".join(
        [
            str(recommendation.get("tone_type", "")),
            str(recommendation.get("amp_family", "")),
            str(recommendation.get("amp_model", "")),
            str(recommendation.get("cabinet", {}).get("cab", "")),
        ]
    ).lower()

    scoop = float(scores.get("scoop", 0) or 0)
    presence = float(scores.get("presence", 0) or 0)
    body = float(scores.get("body", 0) or 0)

    if "soldano" in text or "slo" in text:
        if presence >= 5:
            return 38
        return 39

    if "rect" in text or "rectifier" in text or "mesa" in text or "boogie" in text:
        if scoop >= 6:
            return 39
        if body >= 6:
            return 34
        return 37

    if "dark" in text or "terror" in text or "orange" in text:
        if body >= 6:
            return 23
        return 18

    if "5150" in text or "evh" in text or "peavey" in text:
        return 18

    if "mark" in text:
        return 8

    if "jcm" in text or "plexi" in text or "marshall" in text:
        return 5

    if "clean" in text or "twin" in text or "fender" in text:
        return 27

    return 37

def _build_eq_data(eq_profile: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, int]:
    """
    GE250 그래픽 EQ Type 2 기준.
    업로드된 Recto 프리셋의 EQ 구조를 기준으로 사용.
    기본값 50 근처에서 분석값에 따라 보정.
    """
    bass = float(eq_profile.get("bass", 5) or 5)
    mud = float(eq_profile.get("mud", 5) or 5)
    warm_body = float(eq_profile.get("warm_body", 5) or 5)
    core_mid = float(eq_profile.get("core_mid", 5) or 5)
    upper_mid = float(eq_profile.get("upper_mid", 5) or 5)
    presence = float(eq_profile.get("presence", 5) or 5)
    fizz = float(eq_profile.get("fizz", 5) or 5)

    eq = {
        "100Hz": 50,
        "200Hz": 50,
        "400Hz": 50,
        "800Hz": 50,
        "1.6KHz": 50,
        "3.2KHz": 50,
    }

    # 저역이 많으면 100/200Hz 살짝 컷
    eq["100Hz"] = _clamp_int(52 - max(0, bass - 5) * 3)
    eq["200Hz"] = _clamp_int(50 - max(0, mud - 5) * 4)

    # 바디/미드
    eq["400Hz"] = _clamp_int(48 + (warm_body - 5) * 2)
    eq["800Hz"] = _clamp_int(48 + (core_mid - 5) * 3)

    # 어택/존재감
    eq["1.6KHz"] = _clamp_int(50 + (upper_mid - 5) * 3)
    eq["3.2KHz"] = _clamp_int(50 + (presence - 5) * 2 - max(0, fizz - 5) * 3)

    for move in recommendation.get("suggested_eq_moves", []) or []:
        frequency = str(move.get("frequency", "")).lower()
        gain_db = float(move.get("gain_db", 0) or 0)

        if "100" in frequency:
            eq["100Hz"] = _clamp_int(eq["100Hz"] + gain_db * 4)
        elif "200" in frequency or "250" in frequency:
            eq["200Hz"] = _clamp_int(eq["200Hz"] + gain_db * 4)
        elif "400" in frequency or "500" in frequency:
            eq["400Hz"] = _clamp_int(eq["400Hz"] + gain_db * 4)
        elif "800" in frequency or "1k" in frequency:
            eq["800Hz"] = _clamp_int(eq["800Hz"] + gain_db * 4)
        elif "1.6" in frequency or "2k" in frequency:
            eq["1.6KHz"] = _clamp_int(eq["1.6KHz"] + gain_db * 4)
        elif "3.2" in frequency or "4k" in frequency:
            eq["3.2KHz"] = _clamp_int(eq["3.2KHz"] + gain_db * 4)

    return eq


def build_ge250_preset(
    analysis: dict[str, Any],
    recommendation: dict[str, Any],
) -> tuple[str, bytes]:

    scores = analysis.get("scores", {}) or {}
    eq_profile = analysis.get("eq_profile", {}) or {}
    effects = analysis.get("effects", {}) or {}

    template_path = _pick_template_file(recommendation, scores)

    if not template_path.exists():
        template_path = BASE_DIR / "preset_templates" / "ge250_base.mo"

    if not template_path.exists():
        raise FileNotFoundError(
            "GE250 템플릿 파일이 없습니다. backend/preset_templates/ 안에 ge250_base.mo 또는 타입별 템플릿을 추가해주세요."
        )

    template = json.loads(template_path.read_text(encoding="utf-8"))

    preset = copy.deepcopy(template)


    amp_settings = recommendation.get("amp_settings", {}) or {}
    drive = recommendation.get("drive", {}) or {}
    ambience = recommendation.get("ambience", {}) or {}


    tone_type = recommendation.get("tone_type", "ToneScope")
    unique_suffix = str(int(time.time()))[-5:]
    
    base_name = _safe_preset_name(f"TS {tone_type}", max_len=18)
    preset_name = f"{base_name} {unique_suffix}"
    
    preset["fileInfo"]["name"] = preset_name
    filename = f"{preset_name.replace(' ', '_')}.mo"
    
    preset["fileInfo"]["device"] = "MOOER GE250"
    preset["fileInfo"]["schema"] = "GE250 Preset"
    
    filename = f"{preset_name.replace(' ', '_')}.mo"
    # Others
    preset.setdefault("Others", {})
    preset["Others"]["BPM"] = int(preset["Others"].get("BPM", 80) or 80)
    preset["Others"]["Volume"] = 100

    effect_module = preset.setdefault("effectModule", {})

    # Noise Gate
    gate = effect_module.setdefault("NS GATE", {"Data": {}, "Switch": 1, "Type": 0})
    high_gain = float(scores.get("high_gain_likelihood", 0) or 0)
    gate["Switch"] = 1 if high_gain >= 4 else 0
    gate["Type"] = gate.get("Type", 0)

    if "Thres" in gate.get("Data", {}):
        gate["Data"]["Thres"] = _clamp_int(18 + high_gain * 3)
    else:
        gate["Data"] = {"Thres": _clamp_int(18 + high_gain * 3)}

    # DS/OD
    od = effect_module.setdefault("DS/OD", {"Data": {}, "Switch": 0, "Type": 19})
    drive_type = str(drive.get("type", "")).lower()

    od["Switch"] = 1 if high_gain >= 4 or "overdrive" in drive_type or "boost" in drive_type else 0
    od["Type"] = 19

    od["Data"] = {
        "Gain": _score_to_100(drive.get("drive", 1.5), 15),
        "Tone": _score_to_100(drive.get("tone", 6.0), 60),
        "Volume": _score_to_100(drive.get("level", 7.0), 70),
    }

    # AMP
    amp = effect_module.setdefault("AMP", {"Data": {}, "Switch": 1, "Type": 20})
    amp["Switch"] = 1
    amp["Type"] = _pick_amp_type(recommendation, scores)

    amp["Data"] = {
        "Gain": _score_to_100(amp_settings.get("gain", scores.get("gain", 5)), 50),
        "Bass": _score_to_100(amp_settings.get("bass", 5), 50),
        "Mid": _score_to_100(amp_settings.get("mid", 5), 50),
        "Treble": _score_to_100(amp_settings.get("treble", 5), 50),
        "Pres": _score_to_100(amp_settings.get("presence", scores.get("presence", 5)), 50),
        "Mst": _score_to_100(amp_settings.get("master", 8), 80),
    }

    # CAB
    cab = effect_module.setdefault("CAB", {"Data": {}, "Switch": 1, "Type": 8})
    cab["Switch"] = 1
    cab["Type"] = _pick_cab_type(recommendation, scores)

    cab["Data"] = {
        "Center": 15,
        "Distance": 18,
        "Level": 80,
        "Mic": 2,
        "Sync": 1,
        "Tube": 2,
    }

    # EQ
    eq = effect_module.setdefault("EQ", {"Data": {}, "Switch": 1, "Type": 2})
    eq["Switch"] = 1
    eq["Type"] = 2
    eq["Data"] = _build_eq_data(eq_profile, recommendation)

    # Delay
    delay = effect_module.setdefault("DELAY", {"Data": {}, "Switch": 0, "Type": 0})
    delay_likelihood = float(effects.get("delay_likelihood", 0) or 0)
    delay_mix = float(ambience.get("delay_mix", 0) or 0)

    delay["Switch"] = 1 if delay_likelihood >= 4 or delay_mix >= 8 else 0
    delay["Type"] = delay.get("Type", 0)
    delay["Data"] = {
        "Time": 460,
        "F.Back": _clamp_int(18 + delay_likelihood * 2),
        "Level": _clamp_int(delay_mix if delay_mix > 0 else 25),
        "Sub D": 1,
    }

    # Reverb
    reverb = effect_module.setdefault("REVERB", {"Data": {}, "Switch": 0, "Type": 1})
    reverb_mix = float(ambience.get("reverb_mix", 0) or 0)
    ambience_score = float(scores.get("ambience", 0) or 0)

    reverb["Switch"] = 1 if reverb_mix >= 5 or ambience_score >= 4 else 0
    reverb["Type"] = reverb.get("Type", 1)
    reverb["Data"] = {
        "Decay": _clamp_int(15 + ambience_score * 5),
        "Level": _clamp_int(reverb_mix if reverb_mix > 0 else ambience_score * 5),
        "Pre delay": 15,
        "Tone": 35,
    }

    filename = f"{preset_name.replace(' ', '_')}.mo"
    content = json.dumps(preset, ensure_ascii=False, indent=4).encode("utf-8")

    return filename, content


def _pick_template_file(recommendation: dict[str, Any], scores: dict[str, Any]) -> Path:
    text = " ".join(
        [
            str(recommendation.get("tone_type", "")),
            str(recommendation.get("amp_family", "")),
            str(recommendation.get("amp_model", "")),
            " ".join(recommendation.get("amp_examples", []) or []),
        ]
    ).lower()

    high_gain = float(scores.get("high_gain_likelihood", 0) or 0)
    gain = float(scores.get("gain", 0) or 0)

    template_dir = BASE_DIR / "preset_templates"

    if "soldano" in text or "slo" in text:
        return template_dir / "ge250_soldano.mo"

    if "rect" in text or "rectifier" in text or "mesa" in text or "boogie" in text:
        return template_dir / "ge250_recto.mo"

    if "5150" in text or "evh" in text or "peavey" in text:
        return template_dir / "ge250_5150.mo"

    if "orange" in text or "dark" in text or "terror" in text:
        return template_dir / "ge250_orange.mo"

    if "jcm" in text or "j800" in text or "marshall" in text:
        return template_dir / "ge250_jcm800.mo"

    if "clean" in text or "twin" in text or "fender" in text:
        return template_dir / "ge250_clean.mo"

    if high_gain >= 6 or gain >= 6:
        return template_dir / "ge250_recto.mo"

    if gain >= 3.5:
        return template_dir / "ge250_crunch.mo"

    return template_dir / "ge250_clean.mo"


