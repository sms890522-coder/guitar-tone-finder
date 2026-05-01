from __future__ import annotations

from typing import Any


def recommend(analysis: dict[str, Any]) -> dict[str, Any]:
    s = analysis["scores"]
    gain = s["gain"]
    brightness = s["brightness"]
    warmth = s["warmth"]
    mid = s["mid_focus"]
    compression = s["compression"]
    ambience = s["ambience"]
    roughness = s["roughness"]

    if gain >= 7.2 and mid >= 6.0:
        tone_type = "British High Gain / Modern Rock Lead"
        amp = "British 800 Hot-Rod 계열"
        drive = "Tube Screamer 계열 부스터"
        cab = "4x12 Vintage 30 계열"
    elif gain >= 6.0 and brightness >= 6.5:
        tone_type = "Bright Crunch / Alternative Rock"
        amp = "Vox AC / British Crunch 계열"
        drive = "Transparent Overdrive"
        cab = "2x12 Open Back 또는 4x12 Greenback"
    elif gain >= 5.0 and warmth >= 6.0:
        tone_type = "Warm Blues Drive"
        amp = "Dumble / Fender Drive 계열"
        drive = "Low Gain Overdrive"
        cab = "1x12 또는 2x12 Alnico 계열"
    elif gain < 4.0 and brightness >= 5.5:
        tone_type = "Clean Bright / Worship Clean"
        amp = "Fender Twin / Deluxe Clean 계열"
        drive = "없음 또는 클린 부스트"
        cab = "2x12 Clean Cab"
    else:
        tone_type = "Balanced Crunch / General Guitar Tone"
        amp = "British Plexi / Classic Crunch 계열"
        drive = "Mild Overdrive"
        cab = "4x12 Greenback 계열"

    delay = "Slapback 또는 Short Delay" if ambience >= 6.5 else "거의 없음"
    reverb = "Plate/Room Reverb 중간" if ambience >= 6.0 else "짧은 Room Reverb"
    gate = "강하게" if gain >= 7.0 or roughness >= 7.0 else "약하게"

    settings = {
        "amp_gain": round(min(8.5, max(2.0, gain * 0.85)), 1),
        "bass": round(max(3.0, min(7.0, 5.5 - (s["low_tightness"] - 5) * 0.25)), 1),
        "mid": round(max(3.5, min(8.5, 4.5 + mid * 0.45)), 1),
        "treble": round(max(3.0, min(8.0, 3.5 + brightness * 0.45)), 1),
        "presence": round(max(3.0, min(8.0, 4.0 + brightness * 0.35)), 1),
        "compression": round(max(1.0, min(8.0, compression * 0.65)), 1),
        "reverb_mix": round(max(5.0, min(30.0, ambience * 2.4)), 1),
    }

    return {
        "tone_type": tone_type,
        "summary": make_summary(s, tone_type),
        "chain": ["Noise Gate", drive, amp, cab, reverb, delay],
        "amp": amp,
        "drive": drive,
        "cab": cab,
        "settings": settings,
        "disclaimer": "이 결과는 오디오 특징 기반 추정값입니다. 실제 장비와 다를 수 있지만 비슷한 톤을 만드는 출발점으로 사용하세요.",
    }


def make_summary(scores: dict[str, float], tone_type: str) -> str:
    parts = []
    if scores["gain"] >= 7:
        parts.append("게인이 높은 편")
    elif scores["gain"] >= 5:
        parts.append("중간 이상의 드라이브")
    else:
        parts.append("클린/로우게인 성향")

    if scores["mid_focus"] >= 6.5:
        parts.append("미드가 앞으로 나오는 톤")
    if scores["brightness"] >= 6.5:
        parts.append("밝고 선명한 고역")
    if scores["warmth"] >= 6.5:
        parts.append("따뜻한 저중역")
    if scores["compression"] >= 7:
        parts.append("컴프레션이 강한 느낌")

    return f"{tone_type} 성향입니다. " + ", ".join(parts) + "."
