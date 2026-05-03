'use client';

import { useEffect, useMemo, useState } from 'react';

type Scores = {
  gain: number;
  brightness: number;
  warmth: number;
  mid_focus: number;
  low_tightness: number;
  compression: number;
  roughness: number;
  ambience: number;
  distortion: number;
  pick_attack: number;
  sustain: number;
  fizz: number;
  presence: number;
  body: number;
  mud: number;
  core_mid: number;
  upper_mid: number;
  air: number;
  clarity: number;
  scoop: number;
  bite: number;
  high_gain_likelihood: number;
  lead_gain_likelihood: number;
};
type EqProfile = {
  sub_bass?: number;
  bass?: number;
  mud?: number;
  warm_body?: number;
  core_mid?: number;
  upper_mid?: number;
  presence?: number;
  fizz?: number;
  air?: number;

  // 기존 호환용
  low?: number;
  low_mid?: number;
  mid?: number;
  high_mid?: number;
  air_fizz?: number;
};

type Recommendation = {
  tone_type: string;
  tone_summary: string;
  tone_traits?: string[];
  confidence: number;
  amp_family: string;
  amp_model?: string;
  amp_examples: string[];
  amp_reason: string;
  drive: {
    type: string;
    model_examples?: string[];
    drive: number;
    tone: number;
    level: number;
    purpose: string;
  };
  amp_settings: Record<string, number>;
  cabinet: {
    cab: string;
    mic: string;
    tip: string;
  };
  ambience: {
    character?: string;
    reverb: string;
    reverb_mix: number;
    delay: string;
    delay_mix: number;
    tip: string;
    space_note?: string;
    reverb_tail?: number;
    dry_sustain?: number;
    room_wetness?: number;
    delay_echo?: number;
  };
  eq_tips: string[];
  chain: string[];
  notes: string[];
};

type SpaceProfile = {
  ambience: number;
  reverb_tail: number;
  dry_sustain: number;
  room_wetness: number;
  delay_echo: number;
};

type Result = {
  ok: boolean;
  filename: string;
  analysis: {
    version?: string;
    stats: Record<string, number>;
    scores: Scores;
    eq_profile: EqProfile;
    space?: SpaceProfile;
    debug_space?: Record<string, number>;
  };
  recommendation: Recommendation;
};

const scoreLabels: Array<[keyof Scores, string, string]> = [
  ['gain', 'Gain', '드라이브/출력감'],
  ['brightness', 'Brightness', '밝기/고역감'],
  ['warmth', 'Warmth', '따뜻한 저중역'],
  ['mid_focus', 'Mid Focus', '미드 존재감'],
  ['low_tightness', 'Low Tightness', '저음 타이트함'],
  ['compression', 'Compression', '압축감'],
  ['roughness', 'Roughness', '거친 질감'],
  ['ambience', 'Ambience', '공간감 추정'],
  ['distortion', 'Distortion', '왜곡/새츄레이션'],
  ['high_gain_likelihood', 'High Gain Likelihood', '하이게인 가능성'],
  ['lead_gain_likelihood', 'Lead Gain Likelihood', '리드 하이게인 가능성'],
  ['pick_attack', 'Pick Attack', '피킹 어택'],
  ['sustain', 'Sustain', '서스테인'],
  ['fizz', 'Fizz', '고역 지글거림'],
  ['presence', 'Presence', '존재감/상중역'],
  ['body', 'Body', '기타 몸통감'],
  ['mud', 'Mud', '저중역 뭉침'],
  ['core_mid', 'Core Mid', '중심 미드'],
  ['upper_mid', 'Upper Mid', '상중역 어택'],
  ['air', 'Air', '공기감'],
  ['clarity', 'Clarity', '선명도'],
  ['scoop', 'Scoop', '미드가 빠진 정도'],
  ['bite', 'Bite', '물리는 어택감'],
];

const eqLabels: Record<string, { title: string; range: string; desc: string }> = {
    sub_bass: {
      title: 'Sub Bass',
      range: '40–80Hz',
      desc: '초저역 / 기타톤에서는 거의 필요 없는 영역',
    },
    bass: {
      title: 'Bass',
      range: '80–160Hz',
      desc: '저역 무게감 / 너무 많으면 답답할 수 있음',
    },
    mud: {
      title: 'Mud',
      range: '160–350Hz',
      desc: '먹먹함 / 뭉침이 생기기 쉬운 대역',
    },
    warm_body: {
      title: 'Warm Body',
      range: '350–800Hz',
      desc: '따뜻함 / 기타 몸통감',
    },
    core_mid: {
      title: 'Core Mid',
      range: '800Hz–1.6kHz',
      desc: '중심 미드 / 기타가 앞으로 나오는 대역',
    },
    upper_mid: {
      title: 'Upper Mid',
      range: '1.6–3.5kHz',
      desc: '상중역 / 피킹 어택과 존재감',
    },
    presence: {
      title: 'Presence',
      range: '3.5–6.5kHz',
      desc: '선명도 / 앞으로 튀어나오는 느낌',
    },
    fizz: {
      title: 'Fizz',
      range: '6.5–10kHz',
      desc: '지글거림 / 하이게인 고역 거칠음',
    },
    air: {
      title: 'Air',
      range: '10–14kHz',
      desc: '공기감 / 아주 높은 고역',
    },
};

const MAX_FILE_SIZE = 25 * 1024 * 1024;

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';

    fetch(`${API_BASE_URL}/health`)
      .then(() => {
        console.log('Backend is awake');
      })
      .catch((error) => {
        console.log('Backend wake-up failed:', error);
      });
  }, []);
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : ''), [file]);

  async function analyze() {
    if (!file) {
      setError('분석할 오디오 파일을 먼저 업로드해주세요.');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError('파일이 너무 큽니다. 25MB 이하의 MP3 또는 WAV 파일을 업로드해 주세요.');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';

      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      console.log('ANALYZE RESULT:', data);

      if (!response.ok) {
        throw new Error(data.detail || '분석에 실패했습니다.');
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,#2e1065,transparent_34%),radial-gradient(circle_at_top_right,#0f766e,transparent_28%),#080913] px-5 py-8 md:px-10">
      <section className="mx-auto max-w-6xl">
        <nav className="mb-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-white text-xl text-slate-950 shadow-glow">
              ϟ
            </div>
            <div>
              <p className="text-sm text-slate-400">Guitar Tone Analyzer</p>
              <h1 className="text-xl font-black tracking-tight">ToneScope AI</h1>
            </div>
          </div>
          <div className="rounded-full border border-white/10 px-4 py-2 text-xs text-slate-300">
            MVP v2 · Improved Analysis
          </div>
        </nav>

        <div className="grid gap-6 lg:grid-cols-[1.05fr_.95fr]">
          <section className="glass rounded-[2rem] p-6 shadow-2xl md:p-9">
            <div className="mb-7 inline-flex rounded-full bg-indigo-400/10 px-4 py-2 text-sm text-indigo-200 ring-1 ring-indigo-300/20">
              MP3 · WAV · M4A · FLAC · 25MB 이하 권장
            </div>

            <h2 className="text-4xl font-black leading-tight tracking-tight md:text-6xl">
              기타톤을 업로드하면
              <br />
              비슷한 세팅을 찾아줘요.
            </h2>

            <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300 md:text-lg">
              오디오 특징을 분석해서 게인, 밝기, 미드, 컴프레션, 피킹 어택, 서스테인, fizz,
              presence를 계산하고 앰프·드라이브·캐비넷 추천 체인을 생성합니다.
            </p>

            <label className="mt-8 flex cursor-pointer flex-col items-center justify-center rounded-[1.5rem] border border-dashed border-slate-500/70 bg-slate-950/40 px-6 py-10 text-center transition hover:border-indigo-300 hover:bg-indigo-400/10">
              <input
                type="file"
                accept=".mp3,.wav,.m4a,.aac,.flac,.ogg,audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/mp4,audio/aac,audio/flac,audio/ogg"
                className="hidden"
                onChange={(event) => {
                  setFile(event.target.files?.[0] || null);
                  setResult(null);
                  setError('');
                }}
              />
              <span className="text-5xl">🎸</span>
              <strong className="mt-4 text-lg">오디오 파일 선택</strong>
              <span className="mt-2 text-sm text-slate-400">
                권장: 기타가 잘 들리는 15~60초 클립 / 1MB 이하
              </span>
            </label>

            {file && (
              <div className="mt-5 rounded-2xl bg-white/5 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="font-semibold">{file.name}</p>
                    <p className="text-sm text-slate-400">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <audio className="w-full md:w-72" controls src={previewUrl} />
                </div>
              </div>
            )}

            <button
              onClick={analyze}
              disabled={loading || !file}
              className="mt-6 w-full rounded-2xl bg-white px-6 py-4 font-black text-slate-950 transition hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? '분석 중...' : '톤 분석 시작'}
            </button>
            <p className="mt-3 text-xs leading-5 text-slate-400">
              무료 서버 특성상 첫 분석은 서버가 깨어나는 데 시간이 걸릴 수 있습니다.
            </p>
            {error && (
              <p className="mt-4 rounded-xl bg-rose-500/15 p-4 text-sm text-rose-100">
                {error}
              </p>
            )}
          </section>

          <section className="glass rounded-[2rem] p-6 md:p-8">
            {!result ? (
              <div className="flex h-full min-h-[520px] flex-col justify-center rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-8 text-center">
                <div className="mx-auto grid h-24 w-24 place-items-center rounded-3xl bg-white text-5xl text-slate-950 shadow-glow">
                  ♫
                </div>
                <h3 className="mt-7 text-2xl font-black">분석 결과가 여기에 표시됩니다</h3>
                <p className="mt-3 text-slate-400">
                  실제 장비명을 완벽히 맞히는 것이 아니라, 비슷한 톤을 만들기 위한 출발점
                  세팅을 추천합니다.
                </p>
              </div>
            ) : (
              <ResultPanel result={result} />
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function ResultPanel({ result }: { result: Result }) {
  const scores = result?.analysis?.scores || ({} as Scores);
  const eqProfile = result?.analysis?.eq_profile || ({} as EqProfile);
  const recommendation = result?.recommendation || ({} as Recommendation);
  const space = result?.analysis?.space;

  const ampExamples = Array.isArray(recommendation.amp_examples)
    ? recommendation.amp_examples
    : [];

  const chain = Array.isArray(recommendation.chain)
    ? recommendation.chain
    : [];

  const eqTips = Array.isArray(recommendation.eq_tips)
    ? recommendation.eq_tips
    : [];

  const notes = Array.isArray(recommendation.notes)
    ? recommendation.notes
    : [];

  const ampSettings = recommendation.amp_settings || {};
  const drive = recommendation.drive || {
    type: '추천 없음',
    model_examples: [],
    drive: 0,
    tone: 0,
    level: 0,
    purpose: '드라이브 추천 데이터가 없습니다.',
  };

  const cabinet = recommendation.cabinet || {
    cab: '추천 없음',
    mic: '추천 없음',
    tip: '캐비넷 추천 데이터가 없습니다.',
  };

  const ambience = recommendation.ambience || {
    reverb: '추천 없음',
    tip: '공간계 추천 데이터가 없습니다.',
  };

  return (
    <div>
      <div className="rounded-[1.5rem] bg-white p-6 text-slate-950">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.25em] text-indigo-600">
              Tone Type
            </p>
            <h3 className="mt-2 text-2xl font-black">
              {recommendation.tone_type || 'Unknown Tone'}
            </h3>
          </div>

          <div className="rounded-full bg-slate-950 px-3 py-2 text-xs font-black text-white">
            {recommendation.confidence ?? 0}% confidence
          </div>
        </div>

        <p className="mt-3 leading-7 text-slate-700">
          {recommendation.tone_summary || '톤 요약 데이터가 없습니다.'}
        </p>

        {recommendation.tone_traits && recommendation.tone_traits.length > 0 && (
          <div className="mt-4 space-y-2">
            {recommendation.tone_traits.map((trait) => (
              <p
                key={trait}
                className="rounded-xl bg-slate-100 px-4 py-3 text-sm leading-6 text-slate-700"
              >
                {trait}
              </p>
            ))}
          </div>
        )}

        <div className="mt-5 rounded-2xl bg-slate-100 p-4">
          <p className="text-xs font-bold uppercase text-slate-500">Recommended Amp</p>
          <p className="mt-1 text-lg font-black">{recommendation.amp_family}</p>

          {recommendation.amp_model && (
            <p className="mt-1 text-sm font-bold text-indigo-700">
              {recommendation.amp_model}
            </p>
          )}

          <p className="mt-2 text-sm leading-6 text-slate-600">
            {recommendation.amp_reason}
          </p>

          {ampExamples.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {ampExamples.map((amp) => (
                <span key={amp} className="rounded-full bg-white px-3 py-1 text-xs font-bold">
                  {amp}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {scoreLabels.map(([key, title, desc]) => (
          <ScoreBar
            key={key}
            title={title}
            desc={desc}
            value={typeof scores[key] === 'number' ? scores[key] : 0}
          />
        ))}
      </div>

  <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
    <h4 className="font-black">EQ Profile</h4>
    <p className="mt-2 text-sm leading-6 text-slate-400">
      기타톤의 주파수 대역을 나눠서 본 값입니다. 숫자가 높을수록 해당 대역이 많이 감지된 것입니다.
    </p>
  
    <div className="mt-4 grid gap-3">
      {Object.entries(eqLabels).map(([key, meta]) => {
        const value = Number(eqProfile[key as keyof EqProfile] || 0);
  
        return (
          <div key={key} className="rounded-2xl bg-white/5 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold">
                  {meta.title}
                  <span className="ml-2 text-xs font-normal text-indigo-200">
                    {meta.range}
                  </span>
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-400">
                  {meta.desc}
                </p>
              </div>
  
              <p className="text-xl font-black">{value.toFixed(2)}</p>
            </div>
  
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
              <div
                className="meter-bg h-full rounded-full"
                style={{ width: `${Math.max(0, Math.min(100, value * 10))}%` }}
              />
              </div>
          </div>
        );
      })}
    </div>
  </div>

      {space && (
        <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
          <h4 className="font-black">Space Analysis</h4>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            리버브와 드라이 서스테인을 분리해서 추정한 값입니다.
          </p>

          <div className="mt-4 space-y-3">
            <ScoreBar title="Reverb Tail" desc="어택 이후 잔향 꼬리" value={space.reverb_tail} />
            <ScoreBar title="Dry Sustain" desc="기타 자체 서스테인" value={space.dry_sustain} />
            <ScoreBar title="Room Wetness" desc="방 울림/저레벨 공간감" value={space.room_wetness} />
            <ScoreBar title="Delay Echo" desc="반복 딜레이 가능성" value={space.delay_echo} />
          </div>
        </div>
      )}

      <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
        <h4 className="font-black">추천 시그널 체인</h4>
        <div className="mt-4 flex flex-wrap gap-2">
          {chain.map((item) => (
            <span
              key={item}
              className="rounded-full bg-indigo-400/15 px-3 py-2 text-xs text-indigo-100 ring-1 ring-indigo-300/20"
            >
              {item}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <InfoCard title="Drive" main={drive.type} body={drive.purpose} />

        <InfoCard title="Cabinet" main={cabinet.cab} body={cabinet.tip} />

        <InfoCard title="Mic" main={cabinet.mic} body="추천 마이크/IR 방향" />

        <InfoCard
          title={ambience.character || 'Ambience'}
          main={ambience.reverb}
          body={ambience.space_note || ambience.tip}
        />

        {drive.model_examples && drive.model_examples.length > 0 && (
          <div className="rounded-2xl bg-white/5 p-4 sm:col-span-2">
            <p className="text-xs uppercase text-slate-400">Drive Model Examples</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {drive.model_examples.map((model) => (
                <span
                  key={model}
                  className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-200"
                >
                  {model}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-2xl bg-white/5 p-4 sm:col-span-2">
          <p className="text-xs uppercase text-slate-400">Drive Settings</p>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <div className="rounded-xl bg-white/5 p-3">
              <p className="text-xs text-slate-400">Drive</p>
              <p className="text-xl font-black">{Number(drive.drive || 0).toFixed(1)}</p>
            </div>
            <div className="rounded-xl bg-white/5 p-3">
              <p className="text-xs text-slate-400">Tone</p>
              <p className="text-xl font-black">{Number(drive.tone || 0).toFixed(1)}</p>
            </div>
            <div className="rounded-xl bg-white/5 p-3">
              <p className="text-xs text-slate-400">Level</p>
              <p className="text-xl font-black">{Number(drive.level || 0).toFixed(1)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
        <h4 className="font-black">추천 앰프 세팅</h4>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {Object.entries(ampSettings).map(([key, value]) => (
            <div key={key} className="rounded-2xl bg-white/5 p-4">
              <p className="text-xs uppercase text-slate-400">{key.replaceAll('_', ' ')}</p>
              <p className="mt-1 text-2xl font-black">{Number(value || 0).toFixed(1)}</p>
            </div>
          ))}
        </div>
      </div>

      {eqTips.length > 0 && (
        <div className="mt-6 rounded-[1.5rem] bg-amber-400/10 p-5 ring-1 ring-amber-300/10">
          <h4 className="font-black text-amber-100">EQ 보정 팁</h4>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-amber-100">
            {eqTips.map((tip) => (
              <li key={tip}>• {tip}</li>
            ))}
          </ul>
        </div>
      )}

      {notes.length > 0 && (
        <div className="mt-5 rounded-2xl bg-white/5 p-4 text-sm leading-6 text-slate-300">
          {notes.map((note) => (
            <p key={note}>※ {note}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function InfoCard({ title, main, body }: { title: string; main: string; body: string }) {
  return (
    <div className="rounded-2xl bg-white/5 p-4">
      <p className="text-xs uppercase text-slate-400">{title}</p>
      <p className="mt-1 font-black">{main}</p>
      <p className="mt-2 text-xs leading-5 text-slate-400">{body}</p>
    </div>
  );
}

function ScoreBar({ title, desc, value }: { title: string; desc: string; value: number }) {
  const safeValue = Number.isFinite(value) ? value : 0;

  return (
    <div className="rounded-2xl bg-white/5 p-4">
      <div className="mb-2 flex items-end justify-between gap-3">
        <div>
          <p className="font-bold">{title}</p>
          <p className="text-xs text-slate-400">{desc}</p>
        </div>
        <p className="text-xl font-black">{safeValue.toFixed(1)}</p>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className="meter-bg h-full rounded-full"
          style={{ width: `${Math.max(0, Math.min(100, safeValue * 10))}%` }}
        />
      </div>
    </div>
  );
}
