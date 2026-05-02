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

    high_gain_likelihood = _get_score(scores, "high_gain_likelihood", gain)

        # 실제 분류용 드라이브 강도
    # gain보다 high_gain_likelihood를 우선한다.
    drive_intensity = _clamp(
        0.18 * gain
        + 0.34 * high_gain_likelihood
        + 0.20 * distortion
        + 0.14 * roughness
        + 0.10 * compression
        + 0.04 * sustain
    )

    # 하이게인 강제 보정
    if high_gain_likelihood >= 7.0:
        drive_intensity = max(drive_intensity, 7.2)

    if high_gain_likelihood >= 8.0:
        drive_intensity = max(drive_intensity, 8.0)

    if distortion >= 6.0 and compression >= 6.0 and sustain >= 5.5:
        drive_intensity = max(drive_intensity, 7.0)

    if roughness >= 6.5 and high_gain_likelihood >= 6.5:
        drive_intensity = max(drive_intensity, 7.2)

    # 클린 보호:
    # high_gain_likelihood, distortion, compression이 전부 낮을 때만 클린으로 허용
    is_probably_clean = (
        high_gain_likelihood < 4.5
        and distortion < 4.5
        and compression < 4.5
        and roughness < 5.0
    )

    body = _get_score(scores, "body", warmth)
    mud = _get_score(scores, "mud", 0.0)
    core_mid = _get_score(scores, "core_mid", mid_focus)
    upper_mid = _get_score(scores, "upper_mid", mid_focus)
    air = _get_score(scores, "air", 0.0)
    clarity = _get_score(scores, "clarity", brightness)
    scoop = _get_score(scores, "scoop", 0.0)
    bite = _get_score(scores, "bite", pick_attack)

    reverb_tail = _get_score(space, "reverb_tail", ambience)
    dry_sustain = _get_score(space, "dry_sustain", sustain)
    room_wetness = _get_score(space, "room_wetness", ambience)
    delay_echo = _get_score(space, "delay_echo", 0.0)

    # -----------------------------
    # 1. 톤 타입 분류
    # -----------------------------
    # gain보다 drive_intensity를 우선 사용한다.
    # 이유: 하이게인 톤도 녹음 볼륨이 낮으면 gain 점수가 낮게 나올 수 있음.

    if drive_intensity >= 7.4 and low_tightness >= 6.0 and mid_focus >= 5.0:
        tone_type = "Tight Modern High-Gain Rhythm"
        tone_summary = "왜곡감과 타이트함이 강한 모던 하이게인 리듬톤 성향입니다."

    elif drive_intensity >= 7.2 and sustain >= 6.0:
        tone_type = "Singing High-Gain Lead"
        tone_summary = "왜곡감과 서스테인이 강한 하이게인 리드톤 성향입니다."

    elif drive_intensity >= 6.4 and scoop >= 6.0:
        tone_type = "Scooped Modern High-Gain"
        tone_summary = "미드가 살짝 빠지고 저역/고역이 강조된 모던 하이게인 성향입니다."

    elif drive_intensity >= 6.0 and mid_focus >= 6.0:
        tone_type = "British High-Gain / Hard Rock"
        tone_summary = "중음이 살아 있고 왜곡감이 강한 브리티시 하드록/하이게인 성향입니다."

    elif drive_intensity >= 5.0 and mid_focus >= 6.0:
        tone_type = "British Crunch / Classic Rock"
        tone_summary = "중음이 앞으로 나온 브리티시 크런치 계열 성향입니다."

    elif drive_intensity >= 5.0 and mid_focus < 5.5:
        tone_type = "Modern Drive"
        tone_summary = "중음이 덜 강조되고 드라이브가 있는 모던 드라이브 성향입니다."

    elif drive_intensity >= 3.5:
        tone_type = "Edge of Breakup / Light Drive"
        tone_summary = "클린보다는 살짝 깨지는 엣지 오브 브레이크업 또는 라이트 드라이브 성향입니다."

    elif is_probably_clean and brightness >= 6.0:
        tone_type = "Bright Clean"
        tone_summary = "게인은 낮고 밝은 클린톤 성향입니다."

    elif is_probably_clean and warmth >= 6.0:
        tone_type = "Warm Clean"
        tone_summary = "따뜻하고 부드러운 클린톤 성향입니다."

    elif is_probably_clean:
        tone_type = "Balanced Clean / Low Gain"
        tone_summary = "드라이브가 강하지 않은 밸런스형 클린 또는 로우게인 톤입니다."

    else:
        tone_type = "Driven Guitar Tone"
        tone_summary = "클린보다는 드라이브나 왜곡 성향이 감지되는 기타톤입니다."

    # -----------------------------
    # 2. 앰프 계열 추천 - 세분화 v2
    # -----------------------------
    # 기준:
    # gain: 드라이브 양
    # brightness/presence/fizz: 고역 성향
    # warmth: 저중역 두께
    # mid_focus: 미드 존재감
    # low_tightness: 저음 타이트함
    # sustain: 리드톤/서스테인 성향

    if drive_intensity < 3.2:
        if brightness >= 7.0 and warmth < 5.5:
            amp_family = "American Sparkle Clean"
            amp_model = "Fender Twin Reverb / Deluxe Reverb 계열"
            amp_examples = ["Fender Twin Reverb", "Fender Deluxe Reverb", "Tone King Imperial"]
            amp_reason = "게인은 낮고 고역이 선명해 아메리칸 클린 특유의 반짝이는 톤과 잘 맞습니다."
        elif brightness >= 6.0 and mid_focus >= 5.5:
            amp_family = "Vox Chime Clean"
            amp_model = "Vox AC30 / AC15 Clean 계열"
            amp_examples = ["Vox AC30", "Vox AC15", "Matchless DC-30"]
            amp_reason = "밝고 미드가 살아 있어 Vox 계열의 차임감 있는 클린톤과 잘 맞습니다."
        elif warmth >= 6.5 and mid_focus >= 5.0:
            amp_family = "Dumble / Boutique Smooth Clean"
            amp_model = "Dumble Clean / Two-Rock / Boutique Clean 계열"
            amp_examples = ["Dumble Clean", "Two-Rock Classic", "Morgan SW-style Clean"]
            amp_reason = "따뜻한 저중역과 부드러운 미드가 있어 부티크 클린 계열과 잘 맞습니다."
        elif compression >= 6.5 and brightness >= 5.5:
            amp_family = "Hi-Fi Solid State Clean"
            amp_model = "Jazz Chorus / Studio Clean 계열"
            amp_examples = ["Roland JC-120", "Studio Clean", "Hi-Fi Clean"]
            amp_reason = "압축감과 선명도가 있어 깨끗한 솔리드스테이트/스튜디오 클린 계열에 가깝습니다."
        else:
            amp_family = "Warm Vintage Clean"
            amp_model = "Fender Bassman / Tweed Clean 계열"
            amp_examples = ["Fender Bassman", "Tweed Deluxe", "Vintage American Clean"]
            amp_reason = "게인은 낮고 따뜻한 성향이 있어 빈티지 클린 앰프와 잘 맞습니다."

    elif drive_intensity < 5.2:
        if brightness >= 6.7 and mid_focus >= 5.2:
            amp_family = "Vox Edge of Breakup"
            amp_model = "Vox AC30 Breakup / Matchless 계열"
            amp_examples = ["Vox AC30 Breakup", "Matchless DC-30", "Bad Cat Black Cat"]
            amp_reason = "밝고 미드가 살아 있는 엣지 오브 브레이크업 성향이라 Vox/Matchless 계열이 잘 맞습니다."
        elif warmth >= 6.4 and mid_focus >= 5.5:
            amp_family = "Tweed / Blues Breakup"
            amp_model = "Tweed Deluxe / Bassman Breakup 계열"
            amp_examples = ["Fender Tweed Deluxe", "Fender Bassman", "Victoria Tweed"]
            amp_reason = "따뜻하고 살짝 깨지는 블루스 브레이크업 톤에 가깝습니다."
        elif mid_focus >= 6.5:
            amp_family = "Marshall Plexi Low Gain"
            amp_model = "Marshall Plexi / Bluesbreaker 계열"
            amp_examples = ["Marshall Plexi", "Marshall Bluesbreaker", "JTM45"]
            amp_reason = "미드가 앞으로 나오며 게인이 과하지 않아 Plexi/JTM 계열 크런치와 잘 맞습니다."
        else:
            amp_family = "Boutique Edge Drive"
            amp_model = "Dumble OD / Two-Rock Drive 계열"
            amp_examples = ["Dumble OD", "Two-Rock Drive", "Fuchs ODS"]
            amp_reason = "중간 게인과 부드러운 반응성 때문에 부티크 오버드라이브 앰프 계열과 잘 맞습니다."

    elif drive_intensity < 7.0:
        if mid_focus >= 7.0 and brightness < 6.8:
            amp_family = "Marshall JCM800 Crunch"
            amp_model = "JCM800 / JMP Master Volume 계열"
            amp_examples = ["Marshall JCM800", "Marshall JMP", "Friedman Smallbox"]
            amp_reason = "중음이 강하고 게인이 중상 정도라 JCM800 계열의 록 크런치와 잘 맞습니다."
        elif brightness >= 7.0 and fizz < 5.5:
            amp_family = "Bright British Rock"
            amp_model = "Plexi Hot / AC-style Rock 계열"
            amp_examples = ["Marshall Plexi Hot", "Vox Rock", "Matchless Driven"]
            amp_reason = "밝고 선명한 록 드라이브 성향이라 브리티시 계열의 열린 톤과 잘 맞습니다."
        elif warmth >= 6.5 and mid_focus >= 5.5:
            amp_family = "Orange Thick Rock"
            amp_model = "Orange Rockerverb / OR 계열"
            amp_examples = ["Orange Rockerverb", "Orange OR100", "Matamp-style Rock"]
            amp_reason = "두꺼운 저중역과 미드가 있어 Orange 계열의 굵은 록톤과 잘 맞습니다."
        elif sustain >= 6.5 and compression >= 5.5:
            amp_family = "Smooth Lead Amp"
            amp_model = "Soldano / Dumble Lead 계열"
            amp_examples = ["Soldano SLO Lead", "Dumble Lead", "Bogner Ecstasy Blue"]
            amp_reason = "서스테인과 압축감이 있어 부드러운 리드 앰프 계열과 잘 맞습니다."
        else:
            amp_family = "Balanced Classic Rock Amp"
            amp_model = "Marshall DSL / Friedman / Bogner 계열"
            amp_examples = ["Marshall DSL", "Friedman Runt", "Bogner Shiva"]
            amp_reason = "밸런스 좋은 중게인 록톤이라 범용 브리티시 록 앰프와 잘 맞습니다."

    else:
        if low_tightness >= 7.0 and mid_focus < 5.5 and fizz >= 5.5:
            amp_family = "Mesa Rectifier Modern High-Gain"
            amp_model = "Mesa Dual Rectifier / Modern Recto 계열"
            amp_examples = ["Mesa Dual Rectifier", "Mesa Triple Rectifier", "Modern Recto"]
            amp_reason = "저음이 타이트하고 중음이 살짝 파인 모던 하이게인 성향이라 Rectifier 계열과 잘 맞습니다."
        elif low_tightness >= 7.0 and mid_focus >= 5.5:
            amp_family = "5150 / EVH Tight High-Gain"
            amp_model = "Peavey 5150 / EVH 5150III 계열"
            amp_examples = ["Peavey 5150", "EVH 5150III", "Peavey 6505"]
            amp_reason = "타이트한 저역과 강한 게인, 살아 있는 미드가 5150/EVH 계열과 잘 맞습니다."
        elif mid_focus >= 6.8 and sustain >= 6.0:
            amp_family = "Soldano Singing Lead"
            amp_model = "Soldano SLO / Hot Lead 계열"
            amp_examples = ["Soldano SLO-100", "Bogner Ecstasy Red", "Friedman BE Lead"]
            amp_reason = "중음과 서스테인이 좋아 노래하듯 이어지는 Soldano 계열 리드톤에 가깝습니다."
        elif warmth >= 6.8 and low_tightness < 6.0:
            amp_family = "Thick Saturated British High-Gain"
            amp_model = "Orange / Bogner / Friedman 계열"
            amp_examples = ["Orange Rockerverb High Gain", "Bogner Uberschall", "Friedman BE"]
            amp_reason = "저중역이 두껍고 포화감이 있어 굵은 브리티시 하이게인 계열과 잘 맞습니다."
        elif fizz >= 7.0:
            amp_family = "Aggressive Modern High-Gain"
            amp_model = "5150 / Recto / ENGL 계열"
            amp_examples = ["EVH 5150III", "ENGL Powerball", "Mesa Rectifier"]
            amp_reason = "고역 fizz와 공격적인 질감이 있어 모던 메탈 하이게인 계열과 잘 맞습니다."
        else:
            amp_family = "Hot-Rodded British High-Gain"
            amp_model = "Friedman BE / Marshall Hot Rod / SLO 계열"
            amp_examples = ["Friedman BE-100", "Marshall JCM800 Hot Rod", "Soldano SLO"]
            amp_reason = "높은 게인과 미드 중심 성향이 핫로드 브리티시 하이게인 계열과 잘 맞습니다."

    # -----------------------------
    # 3. 드라이브/부스터 추천 - 세분화 v2
    # -----------------------------
    if drive_intensity >= 7.0:
        if low_tightness < 5.8:
            drive = {
                "type": "Tube Screamer Tight Boost",
                "model_examples": ["Ibanez TS808", "Maxon OD808", "Horizon Devices Precision Drive"],
                "drive": 1.0,
                "tone": 4.6 if brightness >= 6.5 else 5.3,
                "level": 8.0,
                "purpose": "하이게인 앰프 앞에서 저음을 조이고 미드를 밀어 리프를 타이트하게 만드는 용도",
            }
        elif fizz >= 7.0:
            drive = {
                "type": "Clean Boost / Dark Tight Boost",
                "model_examples": ["Fortin Grind 낮은 톤", "TC Spark Boost", "Klon 낮은 게인"],
                "drive": 0.5,
                "tone": 4.0,
                "level": 6.8,
                "purpose": "이미 고역 fizz가 많으므로 밝은 부스터보다 어두운 클린 부스트가 적합합니다.",
            }
        elif mid_focus >= 6.5:
            drive = {
                "type": "SD-1 / Mid Push Boost",
                "model_examples": ["Boss SD-1", "MXR GT-OD", "TS Mini"],
                "drive": 1.2,
                "tone": 5.0,
                "level": 7.2,
                "purpose": "중음을 더 앞으로 밀어 솔로와 록 리프의 존재감을 높이는 용도",
            }
        else:
            drive = {
                "type": "Precision Tight Boost",
                "model_examples": ["Horizon Precision Drive", "Fortin 33", "Pepers Dirty Tree"],
                "drive": 0.8,
                "tone": 5.2,
                "level": 7.5,
                "purpose": "하이게인 톤의 저역을 정리하고 피킹 어택을 선명하게 만드는 용도",
            }

    elif drive_intensity >= 5.0:
        if mid_focus >= 7.0:
            drive = {
                "type": "Klon / Transparent Mid Boost",
                "model_examples": ["Klon Centaur", "Wampler Tumnus", "J. Rockett Archer"],
                "drive": 2.8,
                "tone": 5.2,
                "level": 6.0,
                "purpose": "미드 캐릭터를 유지하면서 자연스럽게 게인과 존재감을 추가하는 용도",
            }
        elif brightness >= 7.0:
            drive = {
                "type": "Bluesbreaker Style OD",
                "model_examples": ["Marshall Bluesbreaker", "JHS Morning Glory", "Analogman King of Tone"],
                "drive": 3.0,
                "tone": 4.7,
                "level": 5.8,
                "purpose": "밝은 앰프에 과한 고역을 더하지 않고 부드러운 크런치를 더하는 용도",
            }
        elif warmth >= 6.5:
            drive = {
                "type": "Rat Style Distortion",
                "model_examples": ["ProCo RAT", "JHS PackRat", "Walrus Iron Horse"],
                "drive": 3.5,
                "tone": 4.2,
                "level": 5.5,
                "purpose": "두꺼운 저중역에 거친 질감을 더해 굵은 록톤을 만드는 용도",
            }
        elif pick_attack >= 6.5:
            drive = {
                "type": "Hard Clipping Distortion",
                "model_examples": ["Boss DS-1", "MXR Distortion+", "Suhr Riot 낮은 게인"],
                "drive": 3.2,
                "tone": 5.0,
                "level": 5.6,
                "purpose": "강한 어택을 살리고 직선적인 록 디스토션을 만드는 용도",
            }
        else:
            drive = {
                "type": "Transparent Overdrive",
                "model_examples": ["Timmy", "Paul Cochrane Timmy", "Nobels ODR-1"],
                "drive": 3.0,
                "tone": 5.0,
                "level": 5.8,
                "purpose": "원톤을 크게 바꾸지 않고 자연스럽게 드라이브를 추가하는 용도",
            }

    elif drive_intensity >= 3.2:
        if brightness >= 6.5 and mid_focus >= 5.5:
            drive = {
                "type": "Treble Booster / Chime Boost",
                "model_examples": ["Dallas Rangemaster", "Brian May Treble Booster", "Vox-style Boost"],
                "drive": 2.0,
                "tone": 6.0,
                "level": 6.2,
                "purpose": "밝고 차임감 있는 앰프를 더 앞으로 밀어주는 용도",
            }
        elif warmth >= 6.5:
            drive = {
                "type": "Blues Overdrive",
                "model_examples": ["Boss BD-2", "Nobels ODR-1", "Keeley Super Phat Mod"],
                "drive": 3.2,
                "tone": 4.8,
                "level": 5.6,
                "purpose": "따뜻한 클린/브레이크업 톤에 블루지한 질감을 더하는 용도",
            }
        elif compression >= 6.0:
            drive = {
                "type": "Low Gain Compressor Boost",
                "model_examples": ["Compressor + Clean Boost", "Keeley Compressor", "Xotic RC Booster"],
                "drive": 1.2,
                "tone": 5.2,
                "level": 6.0,
                "purpose": "게인은 낮게 유지하면서 음의 밀도와 sustain을 보강하는 용도",
            }
        else:
            drive = {
                "type": "Light Transparent OD",
                "model_examples": ["Timmy", "Morning Glory 낮은 게인", "RC Booster"],
                "drive": 2.0,
                "tone": 5.2,
                "level": 5.5,
                "purpose": "클린톤을 살짝 밀어 엣지 오브 브레이크업을 만드는 용도",
            }

    else:
        if warmth >= 6.5:
            drive = {
                "type": "Clean Boost",
                "model_examples": ["Xotic RC Booster", "MXR Micro Amp", "TC Spark Boost"],
                "drive": 0.3,
                "tone": 5.0,
                "level": 5.8,
                "purpose": "톤 색깔은 유지하면서 볼륨과 반응성만 살짝 올리는 용도",
            }
        elif brightness >= 7.0:
            drive = {
                "type": "Warm Boost",
                "model_examples": ["EP Booster", "Klon 낮은 게인", "Analog Boost"],
                "drive": 0.5,
                "tone": 4.4,
                "level": 5.8,
                "purpose": "밝은 클린톤에 약간의 두께와 따뜻함을 더하는 용도",
            }
        else:
            drive = {
                "type": "No Drive / Compressor First",
                "model_examples": ["Compressor", "Studio Comp", "Clean Preamp"],
                "drive": 0.0,
                "tone": 5.0,
                "level": 5.0,
                "purpose": "드라이브보다 컴프레서나 프리앰프로 기본 톤을 정리하는 편이 좋습니다.",
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

    if mud >= 7.0:
        eq_tips.append("Mud 대역이 강합니다. 180~350Hz를 살짝 줄이면 뭉침이 줄어듭니다.")
    elif mud <= 3.0 and body <= 4.0:
        eq_tips.append("저중역 바디가 부족합니다. 350~700Hz를 조금 올리면 톤이 덜 얇게 느껴집니다.")

    if body >= 7.0 and mud < 5.5:
        eq_tips.append("Body가 좋은 편입니다. 350~800Hz는 과하게 깎지 않는 것이 좋습니다.")

    if clarity <= 4.0:
        eq_tips.append("선명도가 낮은 편입니다. 2~4kHz를 소폭 올리거나 200~350Hz를 정리해 보세요.")

    if fizz >= 7.0:
        eq_tips.append("Fizz가 강합니다. 6.5~10kHz 대역을 하이컷 또는 좁은 컷으로 정리해 보세요.")

    if air <= 2.5 and brightness <= 4.5:
        eq_tips.append("공기감이 적은 편입니다. 하이컷을 너무 낮게 두지 말고 10kHz 이상을 살짝 열어보세요.")

    if scoop >= 7.0:
        eq_tips.append("미드가 빠진 성향입니다. 기타가 묻히면 800Hz~1.6kHz를 조금 올려보세요.")

    if upper_mid >= 7.5 and bite >= 7.0:
        eq_tips.append("상중역 어택이 강합니다. 귀에 쏘면 2~3.5kHz를 살짝 줄여보세요.")
       
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

    tone_traits = []

    if body >= 7.0 and mud < 5.5:
        tone_traits.append("몸통감이 풍부하지만 과하게 뭉치지는 않습니다.")
    elif body >= 7.0 and mud >= 6.0:
        tone_traits.append("저중역이 두꺼워 따뜻하지만 약간 뭉칠 수 있습니다.")
    elif body <= 3.5:
        tone_traits.append("저중역 바디가 적어 얇게 느껴질 수 있습니다.")

    if clarity >= 7.0:
        tone_traits.append("선명도가 좋아 믹스에서 잘 앞으로 나올 가능성이 큽니다.")
    elif clarity <= 3.5 and mud >= 5.5:
        tone_traits.append("선명도가 낮고 저중역이 많아 답답하게 들릴 수 있습니다.")

    if fizz >= 7.0 and brightness < 6.0:
        tone_traits.append("밝다기보다는 고역 fizz가 두드러지는 거친 톤입니다.")
    elif brightness >= 7.0 and fizz < 5.5:
        tone_traits.append("거친 fizz보다는 선명한 밝기가 있는 톤입니다.")

    if scoop >= 7.0:
        tone_traits.append("미드가 빠진 scooped 성향이 강합니다.")
    elif core_mid >= 7.0:
        tone_traits.append("중심 미드가 강해서 기타가 앞으로 나오는 성향입니다.")

    if bite >= 7.0:
        tone_traits.append("피킹 어택이 강하고 물리는 느낌이 뚜렷합니다.")
    elif bite <= 3.5:
        tone_traits.append("피킹 어택이 부드럽거나 둥글게 느껴질 수 있습니다.")

    if drive_intensity >= 6.5 and gain < 5.0:
        tone_traits.append(
            "녹음 볼륨 기준의 Gain 점수는 낮지만, 왜곡/거칠기/압축 특성이 높아 실제로는 드라이브가 강한 톤으로 판단했습니다."
        )

    return {
        "tone_type": tone_type,
        "tone_summary": tone_summary,
        "tone_traits": tone_traits,
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