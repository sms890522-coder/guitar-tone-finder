'use client';

import { useMemo, useState } from 'react';

type Scores = {
  gain: number;
  brightness: number;
  warmth: number;
  mid_focus: number;
  low_tightness: number;
  compression: number;
  roughness: number;
  ambience: number;
};

type Result = {
  analysis: {
    stats: Record<string, number>;
    scores: Scores;
  };
  recommendation: {
    tone_type: string;
    summary: string;
    chain: string[];
    amp: string;
    drive: string;
    cab: string;
    settings: Record<string, number>;
    disclaimer: string;
  };
};

const scoreLabels: Array<[keyof Scores, string, string]> = [
  ['gain', 'Gain', '드라이브/왜곡감'],
  ['brightness', 'Brightness', '밝기/고역감'],
  ['warmth', 'Warmth', '따뜻한 저중역'],
  ['mid_focus', 'Mid Focus', '미드 존재감'],
  ['low_tightness', 'Low Tightness', '저음 타이트함'],
  ['compression', 'Compression', '압축감'],
  ['roughness', 'Roughness', '거친 질감'],
  ['ambience', 'Ambience', '공간계 힌트'],
];

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : ''), [file]);

  async function analyze() {
    if (!file) {
      setError('분석할 오디오 파일을 먼저 업로드해주세요.');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
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
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-white text-xl text-slate-950 shadow-glow">ϟ</div>
            <div>
              <p className="text-sm text-slate-400">Guitar Tone Analyzer</p>
              <h1 className="text-xl font-black tracking-tight">ToneScope AI</h1>
            </div>
          </div>
          <div className="rounded-full border border-white/10 px-4 py-2 text-xs text-slate-300">MVP v1 · Upload Audio</div>
        </nav>

        <div className="grid gap-6 lg:grid-cols-[1.05fr_.95fr]">
          <section className="glass rounded-[2rem] p-6 shadow-2xl md:p-9">
            <div className="mb-7 inline-flex rounded-full bg-indigo-400/10 px-4 py-2 text-sm text-indigo-200 ring-1 ring-indigo-300/20">
              MP3 · WAV · M4A · FLAC · 60초까지 분석
            </div>
            <h2 className="text-4xl font-black leading-tight tracking-tight md:text-6xl">
              기타톤을 업로드하면<br />비슷한 세팅을 찾아줘요.
            </h2>
            <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300 md:text-lg">
              오디오 특징을 분석해서 게인, 밝기, 미드, 컴프레션, 공간감 점수를 만들고 앰프·드라이브·캐비넷 추천 체인을 생성합니다.
            </p>

            <label className="mt-8 flex cursor-pointer flex-col items-center justify-center rounded-[1.5rem] border border-dashed border-slate-500/70 bg-slate-950/40 px-6 py-10 text-center transition hover:border-indigo-300 hover:bg-indigo-400/10">
              <input
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={(event) => {
                  setFile(event.target.files?.[0] || null);
                  setResult(null);
                  setError('');
                }}
              />
              <span className="text-5xl">🎸</span>
              <strong className="mt-4 text-lg">오디오 파일 선택</strong>
              <span className="mt-2 text-sm text-slate-400">권장: 기타가 잘 들리는 15~60초 클립</span>
            </label>

            {file && (
              <div className="mt-5 rounded-2xl bg-white/5 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="font-semibold">{file.name}</p>
                    <p className="text-sm text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
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

            {error && <p className="mt-4 rounded-xl bg-rose-500/15 p-4 text-sm text-rose-100">{error}</p>}
          </section>

          <section className="glass rounded-[2rem] p-6 md:p-8">
            {!result ? (
              <div className="flex h-full min-h-[520px] flex-col justify-center rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-8 text-center">
                <div className="mx-auto grid h-24 w-24 place-items-center rounded-3xl bg-white text-5xl text-slate-950 shadow-glow">♫</div>
                <h3 className="mt-7 text-2xl font-black">분석 결과가 여기에 표시됩니다</h3>
                <p className="mt-3 text-slate-400">처음 버전은 실제 장비명을 맞히는 게 아니라, 비슷한 톤을 만들기 위한 출발점 세팅을 추천합니다.</p>
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
  const { scores } = result.analysis;
  const { recommendation } = result;

  return (
    <div>
      <div className="rounded-[1.5rem] bg-white p-6 text-slate-950">
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-indigo-600">Tone Type</p>
        <h3 className="mt-2 text-2xl font-black">{recommendation.tone_type}</h3>
        <p className="mt-3 leading-7 text-slate-700">{recommendation.summary}</p>
      </div>

      <div className="mt-5 space-y-3">
        {scoreLabels.map(([key, title, desc]) => (
          <ScoreBar key={key} title={title} desc={desc} value={scores[key]} />
        ))}
      </div>

      <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
        <h4 className="font-black">추천 시그널 체인</h4>
        <div className="mt-4 flex flex-wrap gap-2">
          {recommendation.chain.map((item) => (
            <span key={item} className="rounded-full bg-indigo-400/15 px-3 py-2 text-xs text-indigo-100 ring-1 ring-indigo-300/20">
              {item}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {Object.entries(recommendation.settings).map(([key, value]) => (
          <div key={key} className="rounded-2xl bg-white/5 p-4">
            <p className="text-xs uppercase text-slate-400">{key.replaceAll('_', ' ')}</p>
            <p className="mt-1 text-2xl font-black">{value}</p>
          </div>
        ))}
      </div>

      <p className="mt-5 rounded-2xl bg-amber-400/10 p-4 text-sm leading-6 text-amber-100 ring-1 ring-amber-300/10">
        {recommendation.disclaimer}
      </p>
    </div>
  );
}

function ScoreBar({ title, desc, value }: { title: string; desc: string; value: number }) {
  return (
    <div className="rounded-2xl bg-white/5 p-4">
      <div className="mb-2 flex items-end justify-between gap-3">
        <div>
          <p className="font-bold">{title}</p>
          <p className="text-xs text-slate-400">{desc}</p>
        </div>
        <p className="text-xl font-black">{value.toFixed(1)}</p>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div className="meter-bg h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, value * 10))}%` }} />
      </div>
    </div>
  );
}
