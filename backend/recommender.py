from __future__ import annotations

from typing import Any


def _get_score(scores: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = scores.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def _amp_setting(value: float) -> float:
    return round(_clamp(value, 0.0, 10.0), 1)


def recommend_tone(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    analyzer.py의 결과를 바탕으로 기타톤 추천값을 생성한다.

    analysis 구조:
    {
        "stats": {...},
        "scores": {
            "gain": ...,
            "brightness": ...,
            "warmth": ...,
            "mid_focus": ...,
            "low_tightness": ...,
            "compression": ...,
            "roughness": ...,
            "ambience": ...,
            "distortion": ...,
            "pick_attack": ...,
            "sustain": ...,
            "fizz": ...,
            "presence": ...
        },
        "eq_profile": {...}
    }
    """

    scores = analysis.get("scores", {})
    eq = analysis.get("eq_profile", {})
    space = analysis.get("space", {})

    gain = _get_score(scores, "gain")
    brightness = _get_score(scores, "brightness")
    warmth = _get_score(scores, "warmth")
    mid_focus = _get_score(scores, "mid_focus")
    low_tightness = _get_score(scores, "low_tightness")
    compression = _get_score(scores, "compression")
    roughness = _get_score(scores, "roughness")
    ambience = _get_score(scores, "ambience")

    distortion = _get_score(scores, "distortion", roughness)
    pick_attack = _get_score(scores, "pick_attack")
    sustain = _get_score(scores, "sustain")
    fizz = _get_score(scores, "fizz")
    presence = _get_score(scores, "presence", brightness)

    reverb_tail = _get_score(space, "reverb_tail", ambience)
    dry_sustain = _get_score(space, "dry_sustain", sustain)
    room_wetness = _get_score(space, "room_wetness", ambience)
    delay_echo = _get_score(space, "delay_echo", 0.0)

    # -----------------------------
    # 1. 톤 타입 분류
    # -----------------------------
    if gain >= 7.2 and low_tightness >= 6.0 and mid_focus >= 5.5:
        tone_type = "Tight Modern Rock / Metal Rhythm"
        tone_summary = "게인이 높고 저음이 비교적 타이트한 리듬톤 성향입니다."
    elif gain >= 7.0 and sustain >= 6.5 and mid_focus >= 5.0:
        tone_type = "Singing High-Gain Lead"
        tone_summary = "서스테인과 게인이 높은 리드톤 성향입니다."
    elif gain >= 5.0 and mid_focus >= 6.0:
        tone_type = "British Crunch / Classic Rock"
        tone_summary = "중음이 앞으로 나온 브리티시 크런치 계열 성향입니다."
    elif gain >= 5.0 and mid_focus < 5.0:
        tone_type = "Scooped Modern Drive"
        tone_summary = "중음이 살짝 빠지고 저역/고역이 강조된 모던 드라이브 성향입니다."
    elif gain < 4.0 and brightness >= 6.0:
        tone_type = "Bright Clean / Edge of Breakup"
        tone_summary = "밝고 깨끗한 클린 또는 엣지 오브 브레이크업 성향입니다."
    elif gain < 4.0 and warmth >= 6.0:
        tone_type = "Warm Clean / Blues Clean"
        tone_summary = "따뜻하고 부드러운 클린톤 성향입니다."
    else:
        tone_type = "Balanced Guitar Tone"
        tone_summary = "특정 성향이 과하게 치우치지 않은 밸런스형 기타톤입니다."

    # -----------------------------
    # 2. 앰프 계열 추천
    # -----------------------------
    if gain >= 7.5 and low_tightness >= 6.2 and mid_focus < 5.5:
        amp_family = "Modern American High-Gain"
        amp_examples = ["Mesa Rectifier 계열", "Peavey/EVH 5150 계열", "PRS Archon 계열"]
        amp_reason = "높은 게인, 타이트한 저역, 비교적 넓은 대역감이 모던 하이게인 계열과 잘 맞습니다."
    elif gain >= 7.0 and mid_focus >= 5.8:
        amp_family = "Hot-Rodded British High-Gain"
        amp_examples = ["Marshall JCM800 Hot Rod 계열", "Friedman BE 계열", "Soldano SLO 계열"]
        amp_reason = "중음이 살아 있고 게인이 높아 브리티시 핫로드 앰프 계열과 잘 맞습니다."
    elif gain >= 5.0 and mid_focus >= 6.0:
        amp_family = "British Crunch"
        amp_examples = ["Marshall Plexi 계열", "JCM800 Crunch 계열", "Orange Rockerverb 계열"]
        amp_reason = "중음이 앞으로 나오고 드라이브가 적당해 클래식 브리티시 크런치에 가깝습니다."
    elif gain < 4.5 and brightness >= 6.0:
        amp_family = "American Clean / Sparkle Clean"
        amp_examples = ["Fender Twin Reverb 계열", "Deluxe Reverb 계열", "Jazz Chorus Clean 계열"]
        amp_reason = "게인은 낮고 밝기가 높아 깨끗하고 선명한 클린 앰프와 잘 맞습니다."
    elif gain < 4.5 and warmth >= 6.0:
        amp_family = "Warm Vintage Clean"
        amp_examples = ["Fender Bassman 계열", "Vox AC Clean 계열", "Dumble Clean 계열"]
        amp_reason = "따뜻한 중저역이 살아 있어 빈티지 클린 계열과 잘 맞습니다."
    else:
        amp_family = "Versatile British/American Hybrid"
        amp_examples = ["Vox AC30 Breakup 계열", "Marshall DSL 계열", "Fender Hot Rod 계열"]
        amp_reason = "밸런스가 좋아 범용적인 브리티시/아메리칸 하이브리드 계열로 접근하기 좋습니다."

    # -----------------------------
    # 3. 드라이브/부스터 추천
    # -----------------------------
    if gain >= 6.0 and low_tightness < 5.5:
        drive = {
            "type": "Tube Screamer 계열",
            "drive": 1.5,
            "tone": 4.8 if brightness >= 6.5 else 5.5,
            "level": 7.5,
            "purpose": "저음을 조이고 중음을 앞으로 밀어 타이트하게 만드는 용도",
        }
    elif gain >= 6.0 and low_tightness >= 5.5:
        drive = {
            "type": "Clean Boost / Tight Boost",
            "drive": 0.8,
            "tone": 5.0,
            "level": 6.8,
            "purpose": "기존 하이게인 톤의 어택과 선명도를 살짝 밀어주는 용도",
        }
    elif gain >= 4.0 and mid_focus >= 6.0:
        drive = {
            "type": "Klon / Transparent OD 계열",
            "drive": 3.0,
            "tone": 5.2,
            "level": 5.8,
            "purpose": "중음 캐릭터를 유지하면서 자연스럽게 밀어주는 용도",
        }
    elif gain < 4.0:
        drive = {
            "type": "Light Overdrive / Edge Boost",
            "drive": 2.0,
            "tone": 5.5,
            "level": 5.5,
            "purpose": "클린톤을 살짝 깨지게 만들어 반응성을 높이는 용도",
        }
    else:
        drive = {
            "type": "Transparent Overdrive 계열",
            "drive": 2.8,
            "tone": 5.0,
            "level": 5.8,
            "purpose": "원톤을 크게 바꾸지 않고 자연스럽게 게인을 추가하는 용도",
        }

    # -----------------------------
    # 4. 앰프 노브 추천값
    # -----------------------------
    bass = 5.8 - (low_tightness * 0.25)
    if warmth >= 7.0:
        bass -= 0.5
    if gain < 4.0:
        bass += 0.4

    mids = 4.2 + (mid_focus * 0.45)
    if mid_focus < 4.5:
        mids -= 0.4

    treble = 4.0 + (brightness * 0.42) - (fizz * 0.18)
    presence_knob = 3.8 + (presence * 0.35) - (fizz * 0.25)

    amp_gain = 2.5 + (gain * 0.65)
    if distortion >= 7.5:
        amp_gain -= 0.4

    amp_settings = {
        "gain": _amp_setting(amp_gain),
        "bass": _amp_setting(bass),
        "mid": _amp_setting(mids),
        "treble": _amp_setting(treble),
        "presence": _amp_setting(presence_knob),
        "master": 5.0,
    }

    # -----------------------------
    # 5. 캐비넷/마이크/IR 추천
    # -----------------------------
    if gain >= 6.5 and brightness >= 6.0:
        cabinet = {
            "cab": "4x12 V30 계열",
            "mic": "SM57 + Ribbon R121 블렌드",
            "tip": "하이게인 선명도는 유지하되, 리본 마이크를 섞어 고역 fizz를 부드럽게 줄이는 방향이 좋습니다.",
        }
    elif gain >= 6.5 and warmth >= 6.0:
        cabinet = {
            "cab": "4x12 Greenback 또는 V30/Greenback Mix",
            "mic": "SM57 off-axis",
            "tip": "중저역이 많으므로 마이크를 살짝 off-axis로 두고 하이패스 필터를 추천합니다.",
        }
    elif gain < 4.5 and brightness >= 6.0:
        cabinet = {
            "cab": "2x12 Open Back",
            "mic": "Condenser + SM57 소량 블렌드",
            "tip": "밝고 열린 클린톤을 살리기 위해 오픈백 캐비넷과 컨덴서 계열 마이크가 잘 맞습니다.",
        }
    elif gain < 4.5:
        cabinet = {
            "cab": "1x12 또는 2x12 Vintage Open Back",
            "mic": "Ribbon 또는 Dynamic off-axis",
            "tip": "따뜻하고 자연스러운 클린톤을 위해 고역이 부드러운 마이크 조합이 좋습니다.",
        }
    else:
        cabinet = {
            "cab": "2x12 또는 4x12 Balanced IR",
            "mic": "SM57 + R121",
            "tip": "밸런스형 톤이므로 SM57과 리본 마이크 조합으로 기본기를 잡는 것이 좋습니다.",
        }

    # -----------------------------
    # 6. EQ 보정 팁
    # -----------------------------
    eq_tips: list[str] = []

    if fizz >= 7.0:
        eq_tips.append("7kHz~10kHz 대역의 fizz가 강합니다. 하이컷을 7~8kHz 근처로 낮춰보세요.")
    elif fizz <= 3.0 and brightness < 5.0:
        eq_tips.append("고역 공기감이 적은 편입니다. 하이컷을 너무 낮게 두지 말고 Presence를 조금 올려보세요.")

    if warmth >= 7.0 or _get_score(eq, "low") >= 2.0:
        eq_tips.append("저역/저중역이 두꺼운 편입니다. 80~120Hz 하이패스와 250~350Hz 소폭 컷을 추천합니다.")

    if mid_focus >= 7.0:
        eq_tips.append("중음이 강한 편입니다. 밴드 믹스에서 답답하면 800Hz~1.2kHz를 살짝 줄여보세요.")
    elif mid_focus <= 4.0 and gain >= 5.0:
        eq_tips.append("중음이 부족한 드라이브 톤입니다. 700Hz~1.6kHz를 조금 올리면 기타가 앞으로 나옵니다.")

    if brightness >= 7.5:
        eq_tips.append("전체적으로 밝은 톤입니다. Treble/Presence를 과하게 올리지 않는 것이 좋습니다.")

    if not eq_tips:
        eq_tips.append("EQ 밸런스가 크게 치우치지 않았습니다. 앰프 기본 세팅에서 미세 조정하는 방향이 좋습니다.")

        # -----------------------------
    # 7. 공간계 추천
    # -----------------------------
    # 이제 ambience 하나가 아니라 reverb_tail / room_wetness / delay_echo / dry_sustain을 분리해서 판단한다.

    if reverb_tail >= 8.0:
        reverb_name = "Large Hall / Ambient Reverb"
        reverb_mix = 28
        reverb_tip = "긴 잔향 tail이 강하게 감지됩니다. Hall, Ambient, Shimmer 계열처럼 길게 퍼지는 리버브가 잘 맞습니다."
    elif reverb_tail >= 6.4:
        reverb_name = "Plate Reverb / Medium Hall"
        reverb_mix = 20
        reverb_tip = "분명한 리버브 tail이 있습니다. Plate 또는 Medium Hall로 넓이를 만들기 좋습니다."
    elif reverb_tail >= 4.6:
        reverb_name = "Room Reverb / Small Plate"
        reverb_mix = 11
        reverb_tip = "약한 잔향이 감지됩니다. 짧은 Room 또는 Small Plate 정도가 잘 맞습니다."
    elif room_wetness >= 4.5:
        reverb_name = "Small Room"
        reverb_mix = 6
        reverb_tip = "큰 리버브 tail보다는 작은 방 울림 또는 room감에 가깝습니다."
    else:
        reverb_name = "Dry / Reverb Off"
        reverb_mix = 0
        reverb_tip = "공간계가 거의 없는 드라이 톤에 가깝습니다. 리버브는 끄거나 최소화하는 편이 좋습니다."

    if delay_echo >= 7.0:
        delay_name = "Dotted 8th / Stereo Delay"
        delay_mix = 16
        delay_tip = "반복성 있는 에너지 패턴이 강합니다. 딜레이가 톤의 중요한 요소일 가능성이 있습니다."
    elif delay_echo >= 4.8:
        delay_name = "Quarter Delay / Analog Delay"
        delay_mix = 10
        delay_tip = "약한 딜레이 또는 반복감이 감지됩니다."
    elif reverb_tail >= 6.5:
        delay_name = "Subtle Quarter Delay"
        delay_mix = 6
        delay_tip = "리버브가 큰 톤이므로 딜레이는 보조적으로만 섞는 편이 좋습니다."
    else:
        delay_name = "Off 또는 매우 약하게"
        delay_mix = 0
        delay_tip = "딜레이 성향은 강하게 감지되지 않습니다."

    if dry_sustain >= 7.0 and reverb_tail <= 4.5:
        space_character = "Dry Sustain"
        space_note = "공간계가 큰 톤이라기보다 기타 자체의 서스테인이 긴 드라이 톤에 가깝습니다."
    elif reverb_tail >= 6.5:
        space_character = "Reverb Tail"
        space_note = "어택 이후 잔향 tail이 비교적 길게 남는 톤입니다."
    elif room_wetness >= 5.0:
        space_character = "Room Wetness"
        space_note = "큰 리버브보다는 작은 room감 또는 녹음 공간의 울림이 감지됩니다."
    else:
        space_character = "Dry"
        space_note = "공간감이 적고 직접적인 톤입니다."

    ambience_recommendation = {
        "character": space_character,
        "reverb": reverb_name,
        "reverb_mix": reverb_mix,
        "delay": delay_name,
        "delay_mix": delay_mix,
        "tip": f"{reverb_tip} {delay_tip}",
        "space_note": space_note,
        "reverb_tail": reverb_tail,
        "dry_sustain": dry_sustain,
        "room_wetness": room_wetness,
        "delay_echo": delay_echo,
    }

    # -----------------------------
    # 8. 최종 체인
    # -----------------------------
    chain = [
        "Noise Gate",
        drive["type"],
        amp_family,
        cabinet["cab"],
        ambience_recommendation["reverb"],
    ]

    if ambience_recommendation["delay_mix"] > 0:
        chain.append(ambience_recommendation["delay"])

    # -----------------------------
    # 9. 신뢰도/주의 문구
    # -----------------------------
    confidence = 70

    if gain >= 8.5 or fizz >= 8.5:
        confidence -= 8
    if ambience >= 8.0:
        confidence -= 5
    if sustain <= 2.5:
        confidence -= 5
    if abs(brightness - warmth) < 1.0 and gain < 4.0:
        confidence += 5

    confidence = int(_clamp(confidence, 45, 88))

    return {
        "tone_type": tone_type,
        "tone_summary": tone_summary,
        "confidence": confidence,
        "amp_family": amp_family,
        "amp_examples": amp_examples,
        "amp_reason": amp_reason,
        "drive": drive,
        "amp_settings": amp_settings,
        "cabinet": cabinet,
        "ambience": ambience_recommendation,
        "eq_tips": eq_tips,
        "chain": chain,
        "notes": [
            "이 결과는 실제 장비 판별이 아니라 오디오 특징 기반 톤 추정입니다.",
            "정확도를 높이려면 기타가 잘 들리는 15~60초 클립을 사용하는 것이 좋습니다.",
            "MP3보다 WAV 파일이 분석 안정성이 더 좋습니다.",
        ],
    }