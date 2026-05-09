'use client';

import { useEffect, useMemo, useState } from 'react';

type GlobalStats = {
  tone_analysis: number;
  tab_generation: number;
};

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
  playing_role?: string;
  playing_hints?: string[];
  confidence: number;
  amp_family: string;
  amp_model?: string;
  amp_examples: string[];
  amp_candidates?: Array<{
    name: string;
    score: number;
    reason: string;
  }>;
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
    suggested_eq_moves?: Array<{
    type: string;
    frequency: string;
    gain_db: number;
    q: number | string;
    reason: string;
  }>;

  cab_detail?: {
    cab_type: string;
    primary_mic: string;
    secondary_mic: string;
    mic_position: string;
    low_cut: string;
    high_cut: string;
    room_level: string;
    proximity: string;
    tip: string;
  };

  fm3_preset_guide?: {
    preset_name: string;
    grid: string[];
    blocks: Record<string, any>;
    notes: string[];
  };
  chain: string[];
  notes: string[];
  effects_recommendation?: {
    stereo_width: number;
    is_stereo_source: boolean;
    chorus_likelihood: number;
    delay_likelihood: number;
    ping_pong_delay: number;
    double_tracking: number;
    modulation: {
      effect: string;
      mix: number;
      rate: number;
      depth: number;
      tip: string;
    };
    delay: {
      type: string;
      mix: number;
      time: string;
      feedback: number;
      tip: string;
    };
  };
};

type SpaceProfile = {
  ambience: number;
  reverb_tail: number;
  dry_sustain: number;
  room_wetness: number;
  delay_echo: number;
};

type EffectsProfile = {
  is_stereo_source: boolean;
  stereo_width: number;
  chorus_likelihood: number;
  modulation_depth: number;
  delay_likelihood: number;
  ping_pong_delay: number;
  double_tracking: number;
  lr_correlation?: number;
  side_mid_ratio?: number;
};


type TabNote = {
  start: number;
  end: number;
  duration: number;
  frequency: number;
  midi: number;
  note: string;
  string: string;
  fret: number;
  confidence: number;
};

type TabAnalysis = {
  version: string;
  duration: number;
  tuning: string;
  tempo?: {
    bpm: number;
    time_signature: string;
    beat_duration: number;
    bar_duration: number;
  };
  note_count: number;
  confidence: number;
  tab: string;
  notes: TabNote[];
  warnings: string[];
  disclaimer: string;
};
type TabResult = {
  ok: boolean;
  filename: string;
  tab_analysis: TabAnalysis;
};

type MultiFxDevice = 'fm3' | 'mooer_ge250';

const multiFxDevices: Array<{
  id: MultiFxDevice;
  name: string;
  label: string;
  extension: string;
}> = [
  {
    id: 'fm3',
    name: 'Fractal Audio FM3',
    label: 'FM3 / Fractal 계열',
    extension: 'txt',
  },
  {
    id: 'mooer_ge250',
    name: 'Mooer GE250',
    label: 'Mooer GE250',
    extension: 'mo',
  },
];

type Result = {
  ok?: boolean;
  filename?: string;
  analysis: {
    version?: string;
    stats: Record<string, number>;
    scores: Scores;
    eq_profile: EqProfile;
    space?: SpaceProfile;
    effects?: EffectsProfile;
    debug_space?: Record<string, number>;
    segment_profile?: {
      segment_count: number;
      representative_start_sec: number;
      representative_end_sec: number;
      representative_energy: number;
      representative_mid_density: number;
      representative_onset_density: number;
      mix_complexity: number;
      low_chug_likelihood: number;
      single_note_lead_likelihood: number;
      chord_strum_likelihood: number;
    };    
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
  const [progress, setProgress] = useState(0);
  const [tabResult, setTabResult] = useState<TabResult | null>(null);
  const [tabLoading, setTabLoading] = useState(false);
  const [tabError, setTabError] = useState('');
  const [tabProgress, setTabProgress] = useState(0);
  const [queuePosition, setQueuePosition] = useState<number | null>(null);
  const [tabQueuePosition, setTabQueuePosition] = useState<number | null>(null);
  const [jobStatus, setJobStatus] = useState('');
  const [tabJobStatus, setTabJobStatus] = useState('');
  const [globalStats, setGlobalStats] = useState<GlobalStats | null>(null);

  async function fetchGlobalStats() {
    try {
      const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';
  
      const response = await fetch(`${API_BASE_URL}/stats`);
      const data = await response.json();
  
      if (response.ok && data.stats) {
        setGlobalStats(data.stats);
      }
    } catch (error) {
      console.log('Stats fetch failed:', error);
    }
  }
  useEffect(() => {
    const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';

    fetch(`${API_BASE_URL}/health`)
      .then(() => {
        console.log('Backend is awake');
      })
      .catch((error) => {
        console.log('Backend wake-up failed:', error);
      });
    fetchGlobalStats();
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


    setQueuePosition(null);
    setTabQueuePosition(null);
    
    setLoading(true);
    setError('');
    setResult(null);
    setProgress(0);
    
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';

    const response = await fetch(`${API_BASE_URL}/analyze-queue`, {
      method: 'POST',
      body: formData,
    });
    
    const queued = await response.json();
    
    if (!response.ok) {
      throw new Error(queued.detail || '분석 대기열 등록에 실패했습니다.');
    }
    
    setJobStatus(queued.status || 'queued');
    setProgress(queued.status === 'queued' ? 5 : 0);
    
    setQueuePosition(
      typeof queued.queue_position === 'number' && queued.queue_position > 0
        ? queued.queue_position
        : 1
    );
    
    const resultData = await pollAnalyzeJob(queued.job_id);
    setProgress(100);
    setResult(resultData);  
    fetchGlobalStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.');
    } finally {
      setTimeout(() => {
        setLoading(false);
        setProgress(0);
        setJobStatus('');
        setTabJobStatus('');
      }, 500);
    }
  }

  async function analyzeTab() {
    if (!file) {
      setTabError('타브를 만들 오디오 파일을 먼저 업로드해주세요.');
      return;
    }
  
    if (file.size > MAX_FILE_SIZE) {
      setTabError('파일이 너무 큽니다. 25MB 이하 파일을 업로드해 주세요.');
      return;
    }
  
    setTabLoading(true);
    setTabError('');
    setTabResult(null);
    setTabProgress(0);
  
  
    const formData = new FormData();
    formData.append('file', file);
  
    try {
      const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';
    
      const response = await fetch(`${API_BASE_URL}/tab-queue`, {
        method: 'POST',
        body: formData,
      });
    
      const queued = await response.json();
    
      if (!response.ok) {
        throw new Error(queued.detail || '타브 대기열 등록에 실패했습니다.');
      }
    
   setTabJobStatus(queued.status || 'queued');
   setTabProgress(queued.status === 'queued' ? 5 : 0);
    
   setTabQueuePosition(
     typeof queued.queue_position === 'number' && queued.queue_position > 0
       ? queued.queue_position
       : 1
   );
    
    const tabData = await pollTabJob(queued.job_id); 
    setTabProgress(100);
    setTabResult(tabData);
    fetchGlobalStats();
    } catch (err) {
      setTabError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.');
    } finally {
      setTimeout(() => {
        setTabLoading(false);
        setTabProgress(0);
        setTabQueuePosition(null);
        setJobStatus('');
        setTabJobStatus('');
      }, 500);
    }
  }

  async function pollAnalyzeJob(jobId: string) {
    const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';
  
    return new Promise<Result>((resolve, reject) => {
      let timer: ReturnType<typeof setInterval> | null = null;
  
      const checkStatus = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
          const data = await response.json();
  
          if (!response.ok) {
            throw new Error(data.detail || '작업 상태 확인에 실패했습니다.');
          }
  
          setProgress(typeof data.progress === 'number' ? data.progress : 0);
          setJobStatus(data.status || '');
  
          if (data.status === 'queued') {
            setQueuePosition(
              typeof data.queue_position === 'number' && data.queue_position > 0
                ? data.queue_position
                : 1
            );
          } else if (data.status === 'processing') {
            setQueuePosition(null);
          }  
          
          if (data.status === 'done') {
            if (timer) clearInterval(timer);
            setQueuePosition(null);
            resolve(data.result);
          }
  
          if (data.status === 'failed') {
            if (timer) clearInterval(timer);
            setQueuePosition(null);
            reject(new Error(data.error || '분석 작업에 실패했습니다.'));
          }
        } catch (err) {
          if (timer) clearInterval(timer);
          setQueuePosition(null);
          reject(err);
        }
      };
  
      checkStatus();
      timer = setInterval(checkStatus, 1000);
    });
  }

  async function pollTabJob(jobId: string) {
    const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';
  
    return new Promise<TabResult>((resolve, reject) => {
      let timer: ReturnType<typeof setInterval> | null = null;
  
      const checkStatus = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
          const data = await response.json();
  
          if (!response.ok) {
            throw new Error(data.detail || '타브 작업 상태 확인에 실패했습니다.');
          }
  
          setTabProgress(typeof data.progress === 'number' ? data.progress : 0);
          setTabJobStatus(data.status || '');
  
          if (data.status === 'queued') {
            setTabQueuePosition(
              typeof data.queue_position === 'number' && data.queue_position > 0
                ? data.queue_position
                : 1
            );
          } else if (data.status === 'processing') {
            setTabQueuePosition(null);
          }
  
          if (data.status === 'done') {
            if (timer) clearInterval(timer);
            setTabQueuePosition(null);
  
            resolve({
              ok: true,
              filename: file?.name || 'tab-draft',
              tab_analysis: data.result.tab_analysis,
            });
          }
  
          if (data.status === 'failed') {
            if (timer) clearInterval(timer);
            setTabQueuePosition(null);
            reject(new Error(data.error || '타브 작업에 실패했습니다.'));
          }
        } catch (err) {
          if (timer) clearInterval(timer);
          setTabQueuePosition(null);
          reject(err);
        }
      };
  
      checkStatus();
      timer = setInterval(checkStatus, 1000);
    });
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
          <div className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-300">
            {globalStats
              ? `분석 ${globalStats.tone_analysis.toLocaleString()} · 타브 ${globalStats.tab_generation.toLocaleString()}`
              : 'MVP v3'}
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
                  setTabResult(null);
                  setTabError('');
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
            {loading ? `분석 중... ${progress}%` : '톤 분석 시작'}  
            </button>
            
            {loading && (
              <div className="mt-4 rounded-2xl bg-white/5 p-4">
                <div className="mb-2 flex items-center justify-between text-xs text-slate-300">
                  <span>
                   {queuePosition
                      ? `대기열에서 순서를 기다리는 중... ${queuePosition}번째`
                      : jobStatus === 'processing'
                        ? '현재 분석 작업 처리 중...'
                        : progress < 30
                          ? '오디오 업로드 중...'
                          : progress < 70
                            ? '톤 특성 분석 중...'
                            : progress < 95
                              ? '앰프·이펙터 추천 생성 중...'
                              : '결과 정리 중...'}
                  </span>
                  <span className="font-bold">{progress}%</span>
                </div>
                {queuePosition && (
                  <p className="mt-2 text-xs text-indigo-200">
                    현재 대기 순번: {queuePosition}번째
                  </p>
                )}
                
            
                <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="meter-bg h-full rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}
            
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
            {result && (
              <div className="mb-5 rounded-[1.5rem] bg-white/5 p-5 ring-1 ring-white/10">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.2em] text-indigo-200">
                      Tab Draft
                    </p>
                    <h4 className="mt-1 font-black">단음 리프 타브 초안 만들기</h4>
                    <p className="mt-1 text-sm leading-6 text-slate-400">
                      오디오에서 들리는 주요 단음 라인을 추정해 기타 타브 초안을 만듭니다.
                    </p>
                  </div>
                
                  <button
                    onClick={analyzeTab}
                    disabled={tabLoading || !file}
                    className="rounded-2xl bg-white px-5 py-3 text-sm font-black text-slate-950 transition hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {tabLoading ? '타브 생성 중...' : '타브 초안 만들기'}
                  </button>
                </div>
                
                {tabLoading && (
                  <div className="mt-4 rounded-2xl bg-white/5 p-4">
                    <div className="mb-2 flex items-center justify-between text-xs text-slate-300">
                      <span>
                        {tabQueuePosition
                          ? `타브 생성 대기열에서 순서를 기다리는 중... ${tabQueuePosition}번째`
                          : tabJobStatus === 'processing'
                            ? '현재 타브 생성 작업 처리 중...'
                            : tabProgress < 35
                              ? '피치 분석 중...'
                              : tabProgress < 70
                                ? '음표와 프렛 위치 계산 중...'
                                : tabProgress < 95
                                  ? '타브 마디 정리 중...'
                                  : 'TXT 파일 준비 중...'}
                      </span>
                      <span className="font-bold">{tabProgress}%</span>
                    </div>
                
                    {tabQueuePosition && (
                      <p className="mb-2 text-xs text-indigo-200">
                        현재 타브 생성 대기 순번: {tabQueuePosition}번째
                      </p>
                    )}
                
                    <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="meter-bg h-full rounded-full transition-all duration-500"
                        style={{ width: `${tabProgress}%` }}
                      />
                    </div>
                  </div>
                )}
                
          
                {tabError && (
                  <p className="mt-4 rounded-xl bg-rose-500/15 p-4 text-sm text-rose-100">
                    {tabError}
                  </p>
                )}
          
                {tabResult && <TabPanel tabResult={tabResult} />}
              </div>
            )}
          
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

function buildFm3PresetGuideText(result: Result) {
  const recommendation = result.recommendation;
  const guide = recommendation.fm3_preset_guide;

  if (!guide) {
    return 'FM3 프리셋 가이드 데이터가 없습니다.';
  }

  const blocks = guide.blocks || {};
  const amp = blocks.amp || {};
  const drive = blocks.drive || {};
  const cab = blocks.cab || {};
  const eq = Array.isArray(blocks.eq) ? blocks.eq : [];
  const modulation = blocks.modulation || {};
  const delay = blocks.delay || {};
  const reverb = blocks.reverb || {};
  const gate = blocks.input_gate || {};

  return `
ToneScope AI - FM3 Preset Guide
================================

Preset Name:
${guide.preset_name}

Tone Type:
${recommendation.tone_type}

Summary:
${recommendation.tone_summary}

Confidence:
${recommendation.confidence}%

Playing Role:
${recommendation.playing_role || 'N/A'}


Grid
----
${guide.grid.map((item, index) => `${index + 1}. ${item}`).join('\n')}


Input Gate
----------
Type: ${gate.type || 'Input Gate'}
Threshold: ${gate.threshold || '-'}
Ratio: ${gate.ratio || '-'}
Attack: ${gate.attack || '-'}
Release: ${gate.release || '-'}
Tip: ${gate.tip || '-'}


Drive Block
-----------
Model: ${drive.model || '-'}
Examples: ${(drive.model_examples || []).join(', ')}
Drive: ${drive.drive ?? '-'}
Tone: ${drive.tone ?? '-'}
Level: ${drive.level ?? '-'}
Purpose: ${drive.purpose || '-'}


Amp Block
---------
Family: ${amp.family || '-'}
Model: ${amp.model || '-'}
Examples: ${(amp.examples || []).join(', ')}

Gain: ${amp.gain ?? '-'}
Bass: ${amp.bass ?? '-'}
Mid: ${amp.mid ?? '-'}
Treble: ${amp.treble ?? '-'}
Presence: ${amp.presence ?? '-'}
Master: ${amp.master ?? '-'}

Tip:
${amp.tip || '-'}


Cab Block
---------
Cab: ${cab.cab || '-'}
Cab Type: ${cab.cab_type || '-'}
Mic: ${cab.mic || '-'}
Primary Mic: ${cab.primary_mic || '-'}
Secondary Mic: ${cab.secondary_mic || '-'}
Mic Position: ${cab.mic_position || '-'}
Low Cut: ${cab.low_cut || '-'}
High Cut: ${cab.high_cut || '-'}
Room Level: ${cab.room_level || '-'}
Proximity: ${cab.proximity || '-'}

Tip:
${cab.tip || '-'}


Suggested EQ Moves
------------------
${eq
  .map(
    (move: any, index: number) =>
      `${index + 1}. ${move.type}
   Frequency: ${move.frequency}
   Gain: ${move.gain_db}dB
   Q: ${move.q}
   Reason: ${move.reason}`
  )
  .join('\n\n')}


Modulation
----------
Effect: ${modulation.effect || '-'}
Mix: ${modulation.mix ?? '-'}%
Rate: ${modulation.rate ?? '-'}
Depth: ${modulation.depth ?? '-'}
Tip: ${modulation.tip || '-'}


Delay
-----
Type: ${delay.type || '-'}
Time: ${delay.time || '-'}
Mix: ${delay.mix ?? '-'}%
Feedback: ${delay.feedback ?? '-'}%
Tip: ${delay.tip || '-'}


Reverb
------
Type: ${reverb.type || '-'}
Mix: ${reverb.mix ?? '-'}%
Delay: ${reverb.delay || '-'}
Delay Mix: ${reverb.delay_mix ?? '-'}%
Tip: ${reverb.tip || '-'}


Notes
-----
${guide.notes.map((note) => `- ${note}`).join('\n')}
`.trim();
}

function buildMooerGe250PresetGuideText(result: Result) {
  const recommendation = result.recommendation;
  const guide = recommendation.fm3_preset_guide;

  const ampSettings = recommendation.amp_settings || {};
  const drive = recommendation.drive || {};
  const cabinet = recommendation.cabinet || {};
  const ambience = recommendation.ambience || {};
  const eqMoves = recommendation.suggested_eq_moves || [];
  const effects = recommendation.effects_recommendation;

  const gain = Number(ampSettings.gain ?? 5).toFixed(1);
  const bass = Number(ampSettings.bass ?? 5).toFixed(1);
  const mid = Number(ampSettings.mid ?? 5).toFixed(1);
  const treble = Number(ampSettings.treble ?? 5).toFixed(1);
  const presence = Number(ampSettings.presence ?? 5).toFixed(1);
  const master = Number(ampSettings.master ?? 5).toFixed(1);

  return `
ToneScope AI - Mooer GE250 Preset Guide
=======================================

Device:
Mooer GE250

Preset Name:
${guide?.preset_name || `ToneScope ${recommendation.tone_type || 'Guitar Tone'}`}

Tone Type:
${recommendation.tone_type || 'Unknown Tone'}

Summary:
${recommendation.tone_summary || '-'}

Confidence:
${recommendation.confidence ?? 0}%


Recommended GE250 Signal Chain
------------------------------
1. Noise Gate
2. Drive / OD
3. Amp
4. Cab
5. EQ
6. Modulation
7. Delay
8. Reverb


Noise Gate
----------
Threshold: -55dB ~ -45dB
Decay/Release: Medium
Tip:
하이게인 톤이면 노이즈 게이트를 강하게, 클린/크런치면 약하게 설정하세요.


Drive / OD
----------
Type:
${drive.type || 'Overdrive'}

Model Examples:
${Array.isArray(drive.model_examples) ? drive.model_examples.join(', ') : '-'}

Suggested GE250 Direction:
- Tube Screamer 계열 OD 또는 Clean Boost 계열을 먼저 선택
- Drive는 낮게, Level은 높게 두고 앰프 앞단을 밀어주는 방식 추천

Drive: ${drive.drive ?? '-'}
Tone: ${drive.tone ?? '-'}
Level: ${drive.level ?? '-'}

Purpose:
${drive.purpose || '-'}


Amp
---
Recommended Amp Family:
${recommendation.amp_family || '-'}

Recommended Amp Model:
${recommendation.amp_model || '-'}

Amp Examples:
${Array.isArray(recommendation.amp_examples) ? recommendation.amp_examples.join(', ') : '-'}

GE250 Setting Start Point:
Gain: ${gain}
Bass: ${bass}
Middle: ${mid}
Treble: ${treble}
Presence: ${presence}
Master: ${master}

Tip:
GE250에 동일한 앰프명이 없으면, 비슷한 계열을 선택하세요.
- Mesa/Rectifier 계열: Modern High Gain / Cali / Recto 계열
- Marshall 계열: British / Plexi / JCM 계열
- Soldano 계열: SLO / American High Gain 계열
- Fender 계열: US Clean / Deluxe / Twin 계열


Cab / IR
--------
Recommended Cab:
${cabinet.cab || '-'}

Recommended Mic:
${cabinet.mic || '-'}

GE250 Cab Direction:
- 하이게인: 4x12 V30 계열
- 클래식 록: 4x12 Greenback 계열
- 클린/크런치: 2x12 Open Back 계열
- 저음이 과하면 Low Cut 80~120Hz
- 지글거림이 많으면 High Cut 6.5~8.5kHz

Cab Tip:
${cabinet.tip || '-'}


EQ
--
${eqMoves.length > 0
  ? eqMoves
      .map(
        (move, index) =>
          `${index + 1}. ${move.type}
   Frequency: ${move.frequency}
   Gain: ${move.gain_db > 0 ? `+${move.gain_db}` : move.gain_db}dB
   Q: ${move.q}
   Reason: ${move.reason}`
      )
      .join('\n\n')
  : '추천 EQ 보정값이 없습니다.'}


Modulation
----------
Effect:
${effects?.modulation?.effect || 'Off / 필요 시 Chorus'}

Mix:
${effects?.modulation?.mix ?? 0}%

Rate:
${effects?.modulation?.rate ?? '-'}

Depth:
${effects?.modulation?.depth ?? '-'}

Tip:
${effects?.modulation?.tip || '원본 톤에 코러스 느낌이 없으면 꺼두는 것을 추천합니다.'}


Delay
-----
Type:
${effects?.delay?.type || ambience.delay || 'Digital Delay'}

Time:
${effects?.delay?.time || '-'}

Mix:
${effects?.delay?.mix ?? ambience.delay_mix ?? 0}%

Feedback:
${effects?.delay?.feedback ?? '-'}%

Tip:
${effects?.delay?.tip || '리듬톤은 낮게, 리드톤은 10~20% 정도로 시작하세요.'}


Reverb
------
Type:
${ambience.reverb || 'Room / Plate'}

Mix:
${ambience.reverb_mix ?? 0}%

Tip:
${ambience.tip || '-'}


Notes
-----
${Array.isArray(recommendation.notes) && recommendation.notes.length > 0
  ? recommendation.notes.map((note) => `- ${note}`).join('\n')
  : '- 이 파일은 GE250에서 그대로 불러오는 전용 프리셋 파일이 아니라, GE250에서 수동으로 따라 만들기 위한 세팅 가이드입니다.'}
`.trim();
}

function buildMultiFxPresetGuideText(result: Result, device: MultiFxDevice) {
  if (device === 'fm3') {
    return buildFm3PresetGuideText(result);
  }

  if (device === 'mooer_ge250') {
    return buildMooerGe250PresetGuideText(result);
  }

  return '지원하지 않는 멀티이펙터입니다.';
}


async function downloadMultiFxPresetGuide(result: Result, device: MultiFxDevice) {
  if (device === 'mooer_ge250') {
    await downloadGe250Preset(result);
    return;
  }

  const selectedDevice = multiFxDevices.find((item) => item.id === device);
  const text = buildMultiFxPresetGuideText(result, device);

  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  const toneName =
    result.recommendation.tone_type
      ?.toLowerCase()
      .replaceAll('/', '-')
      .replaceAll(' ', '-')
      .replaceAll('--', '-')
      .replace(/[^a-z0-9가-힣-]/gi, '') || 'preset-guide';

  const deviceName = selectedDevice?.id || 'multi-fx';

  const link = document.createElement('a');
  link.href = url;
  link.download = `${deviceName}-${toneName}-preset-guide.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

function downloadFm3PresetGuide(result: Result) {
  const text = buildFm3PresetGuideText(result);
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  const safeName =
    result.recommendation.tone_type
      ?.toLowerCase()
      .replaceAll('/', '-')
      .replaceAll(' ', '-')
      .replaceAll('--', '-')
      .replace(/[^a-z0-9가-힣-]/gi, '') || 'fm3-preset-guide';

  const link = document.createElement('a');
  link.href = url;
  link.download = `${safeName}-fm3-preset-guide.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

async function downloadGe250Preset(result: Result) {
  const API_BASE_URL = 'https://guitar-tone-finder-api.onrender.com';

  const response = await fetch(`${API_BASE_URL}/preset/ge250`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      analysis: result.analysis,
      recommendation: result.recommendation,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || 'GE250 프리셋 생성에 실패했습니다.');
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  const contentDisposition = response.headers.get('Content-Disposition') || '';
  const filenameMatch = contentDisposition.match(/filename="(.+)"/);
  const filename = filenameMatch?.[1] || 'tonescope-ge250.mo';

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

function ResultPanel({ result }: { result: Result }) {
  const [selectedMultiFx, setSelectedMultiFx] = useState<MultiFxDevice | ''>('');

  const scores = result?.analysis?.scores || ({} as Scores);
  const eqProfile = result?.analysis?.eq_profile || ({} as EqProfile);
  const recommendation = result?.recommendation || ({} as Recommendation);
  const space = result?.analysis?.space;

  const segmentProfile = result?.analysis?.segment_profile;
  
  const effects = result?.analysis?.effects;
  const effectsRecommendation = recommendation.effects_recommendation;  

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
      <div className="mb-5 rounded-[1.5rem] bg-indigo-400/10 p-5 ring-1 ring-indigo-300/20">
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-indigo-200">
              Preset Guide
            </p>
            <h4 className="mt-1 font-black">멀티이펙터 프리셋 가이드 다운로드</h4>
            <p className="mt-1 text-sm leading-6 text-slate-300">
              분석 결과를 바탕으로 선택한 멀티이펙터에서 따라 만들 수 있는 세팅 가이드를 다운로드합니다.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <label className="block">
              <span className="mb-2 block text-xs font-bold text-slate-300">
                멀티이펙터 선택
              </span>

              <select
                value={selectedMultiFx}
                onChange={(event) => setSelectedMultiFx(event.target.value as MultiFxDevice)}
                className="w-full rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-sm font-bold text-white outline-none transition focus:border-indigo-300"
              >
                <option value="">기기를 선택해주세요</option>
                {multiFxDevices.map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.label}
                  </option>
                ))}
              </select>
            </label>

            <button
              onClick={async () => {
                if (!selectedMultiFx) return;

                try {
                  await downloadMultiFxPresetGuide(result, selectedMultiFx);
                } catch (error) {
                  alert(error instanceof Error ? error.message : '다운로드에 실패했습니다.');
                }
              }}
              disabled={!selectedMultiFx}
              className="rounded-2xl bg-white px-5 py-3 text-sm font-black text-slate-950 transition hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-40"
            >
              다운로드
            </button>
          </div>

          {selectedMultiFx && (
            <p className="text-xs leading-5 text-indigo-100">
              선택됨:{' '}
              {multiFxDevices.find((device) => device.id === selectedMultiFx)?.name}
            </p>
          )}
        </div>
      </div>

      <div className="rounded-[1.5rem] bg-white p-6 text-slate-950">        <div className="flex items-start justify-between gap-4">
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

        {recommendation.playing_role && (
          <p className="mt-3 inline-flex rounded-full bg-indigo-100 px-3 py-1 text-xs font-bold text-indigo-700">
            Playing Role: {recommendation.playing_role.replaceAll('_', ' ')}
          </p>
        )}
        

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

        {recommendation.amp_candidates && recommendation.amp_candidates.length > 0 && (
          <div className="mt-5 rounded-2xl bg-slate-100 p-4">
            <p className="text-xs font-bold uppercase text-slate-500">
              Alternative Amp Candidates
            </p>
        
            <div className="mt-3 space-y-3">
              {recommendation.amp_candidates.map((candidate, index) => (
                <div key={candidate.name} className="rounded-xl bg-white p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-black">
                        {index + 1}. {candidate.name}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-slate-600">
                        {candidate.reason}
                      </p>
                    </div>
                    <p className="rounded-full bg-slate-950 px-2 py-1 text-xs font-black text-white">
                      {candidate.score}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
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


      {segmentProfile && (
        <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
          <h4 className="font-black">Representative Segment</h4>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            전체 파일 중 기타톤이 가장 잘 드러나는 대표 구간을 기준으로 보조 판단했습니다.
          </p>
      
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bg-white/5 p-4">
              <p className="text-xs uppercase text-slate-400">Best Section</p>
              <p className="mt-1 text-xl font-black">
                {segmentProfile.representative_start_sec}s – {segmentProfile.representative_end_sec}s
              </p>
            </div>
      
            <div className="rounded-2xl bg-white/5 p-4">
              <p className="text-xs uppercase text-slate-400">Mix Complexity</p>
              <p className="mt-1 text-xl font-black">
                {Number(segmentProfile.mix_complexity || 0).toFixed(1)}
              </p>
            </div>
          </div>
      
          <div className="mt-4 space-y-3">
            <ScoreBar
              title="Low Chug"
              desc="팜뮤트/저역 리프 가능성"
              value={segmentProfile.low_chug_likelihood}
            />
            <ScoreBar
              title="Single Note Lead"
              desc="단음 리드/솔로 가능성"
              value={segmentProfile.single_note_lead_likelihood}
            />
            <ScoreBar
              title="Chord Strum"
              desc="코드 스트럼 가능성"
              value={segmentProfile.chord_strum_likelihood}
            />
          </div>
        </div>
      )}

      
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

      {effects && (
        <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
          <h4 className="font-black">Effects Analysis</h4>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            스테레오 폭, 코러스, 딜레이, 더블트래킹 가능성을 추정한 값입니다.
          </p>

          <div className="mt-4 space-y-3">
            <ScoreBar
              title="Stereo Width"
              desc={effects.is_stereo_source ? '좌우 스테레오 폭' : '모노 파일이어서 정확도가 낮음'}
              value={effects.stereo_width}
            />
            <ScoreBar
              title="Chorus Likelihood"
              desc="코러스/모듈레이션 가능성"
              value={effects.chorus_likelihood}
            />
            <ScoreBar
              title="Delay Likelihood"
              desc="반복 딜레이 가능성"
              value={effects.delay_likelihood}
            />
            <ScoreBar
              title="Ping-Pong Delay"
              desc="좌우 교차 딜레이 가능성"
              value={effects.ping_pong_delay}
            />
            <ScoreBar
              title="Double Tracking"
              desc="더블트래킹/스테레오 와이드닝 가능성"
              value={effects.double_tracking}
            />
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

      
        {recommendation.cab_detail && (
          <div className="rounded-2xl bg-white/5 p-4 sm:col-span-2">
            <p className="text-xs uppercase text-slate-400">Cab / Mic Detail</p>
            <p className="mt-1 font-black">{recommendation.cab_detail.cab_type}</p>
        
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-white/5 p-3">
                <p className="text-xs text-slate-400">Primary Mic</p>
                <p className="font-bold">{recommendation.cab_detail.primary_mic}</p>
              </div>
              <div className="rounded-xl bg-white/5 p-3">
                <p className="text-xs text-slate-400">Secondary Mic</p>
                <p className="font-bold">{recommendation.cab_detail.secondary_mic}</p>
              </div>
              <div className="rounded-xl bg-white/5 p-3">
                <p className="text-xs text-slate-400">Low Cut</p>
                <p className="font-bold">{recommendation.cab_detail.low_cut}</p>
              </div>
              <div className="rounded-xl bg-white/5 p-3">
                <p className="text-xs text-slate-400">High Cut</p>
                <p className="font-bold">{recommendation.cab_detail.high_cut}</p>
              </div>
            </div>
        
            <p className="mt-3 text-xs leading-5 text-slate-400">
              {recommendation.cab_detail.tip}
            </p>
          </div>
        )}
        
        <InfoCard
          title={ambience.character || 'Ambience'}
          main={ambience.reverb}
          body={ambience.space_note || ambience.tip}
        />

         {effectsRecommendation && (
          <>
            <InfoCard
              title="Modulation"
              main={effectsRecommendation.modulation.effect}
              body={effectsRecommendation.modulation.tip}
            />

            <InfoCard
              title="Delay"
              main={effectsRecommendation.delay.type}
              body={effectsRecommendation.delay.tip}
            />

            <div className="rounded-2xl bg-white/5 p-4 sm:col-span-2">
              <p className="text-xs uppercase text-slate-400">Effects Settings</p>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-white/5 p-3">
                  <p className="text-xs text-slate-400">Chorus Mix</p>
                  <p className="text-xl font-black">
                    {Number(effectsRecommendation.modulation.mix || 0)}%
                  </p>
                </div>
                <div className="rounded-xl bg-white/5 p-3">
                  <p className="text-xs text-slate-400">Chorus Depth</p>
                  <p className="text-xl font-black">
                    {Number(effectsRecommendation.modulation.depth || 0).toFixed(1)}
                  </p>
                </div>
                <div className="rounded-xl bg-white/5 p-3">
                  <p className="text-xs text-slate-400">Delay Mix</p>
                  <p className="text-xl font-black">
                    {Number(effectsRecommendation.delay.mix || 0)}%
                  </p>
                </div>
                <div className="rounded-xl bg-white/5 p-3">
                  <p className="text-xs text-slate-400">Delay Time</p>
                  <p className="text-lg font-black">
                    {effectsRecommendation.delay.time}
                  </p>
                </div>
              </div>
            </div>
          </>
        )}

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

      {recommendation.playing_hints && recommendation.playing_hints.length > 0 && (
        <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
          <h4 className="font-black">Playing Style Hints</h4>
          <div className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
            {recommendation.playing_hints.map((hint) => (
              <p key={hint}>• {hint}</p>
            ))}
          </div>
        </div>
      )}

      {recommendation.suggested_eq_moves && recommendation.suggested_eq_moves.length > 0 && (
        <div className="mt-6 rounded-[1.5rem] bg-white/5 p-5">
          <h4 className="font-black">Suggested EQ Moves</h4>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            실제 EQ에서 적용해볼 수 있는 보정값입니다. 환경에 따라 ±0.5~1dB 정도 조정하세요.
          </p>
      
          <div className="mt-4 space-y-3">
            {recommendation.suggested_eq_moves.map((move, index) => (
              <div key={`${move.type}-${index}`} className="rounded-2xl bg-white/5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-black">{move.type}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-400">
                      {move.reason}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-black">{move.frequency}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {move.gain_db > 0 ? `+${move.gain_db}` : move.gain_db}dB / Q {move.q}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      
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


function buildTabDraftText(tabResult: TabResult) {
  const tab = tabResult.tab_analysis;

  const detectedNotes = tab.notes
    .map(
      (note, index) =>
        `${index + 1}. ${note.start}s - ${note.note} - ${note.string} string / fret ${note.fret} - confidence ${Math.round(
          note.confidence * 100
        )}%`
    )
    .join('\n');

  const warnings =
    tab.warnings && tab.warnings.length > 0
      ? tab.warnings.map((warning) => `- ${warning}`).join('\n')
      : '- 없음';

  return `
ToneScope AI - Tab Draft
========================

File:
${tabResult.filename}

Tuning:
${tab.tuning}

Duration:
${tab.duration}s

Tempo:
${tab.tempo ? `${tab.tempo.bpm} BPM / ${tab.tempo.time_signature}` : 'N/A'}

Detected Notes:
${tab.note_count}

Confidence:
${Math.round((tab.confidence || 0) * 100)}%

Disclaimer:
${tab.disclaimer}


Estimated Tab
-------------
${tab.tab}


Detected Notes
--------------
${detectedNotes || '감지된 음이 없습니다.'}


Warnings
--------
${warnings}
`.trim();
}

function downloadTabDraft(tabResult: TabResult) {
  const text = buildTabDraftText(tabResult);
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  const safeName =
    tabResult.filename
      ?.toLowerCase()
      .replace(/\.[^/.]+$/, '')
      .replaceAll(' ', '-')
      .replace(/[^a-z0-9가-힣-]/gi, '') || 'tab-draft';

  const link = document.createElement('a');
  link.href = url;
  link.download = `${safeName}-tab-draft.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}



function TabPanel({ tabResult }: { tabResult: TabResult }) {
  const tab = tabResult.tab_analysis;
  
  return (
    <div className="mt-5 rounded-2xl bg-slate-950/60 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase text-slate-400">Estimated Tab</p>
          <h4 className="font-black">단음 리프 타브 초안 생성 완료</h4>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            모바일에서는 전체 타브가 길게 보일 수 있어 TXT 파일 다운로드를 추천합니다.
          </p>
        </div>

        <button
          onClick={() => downloadTabDraft(tabResult)}
          className="rounded-2xl bg-white px-5 py-3 text-sm font-black text-slate-950 transition hover:scale-[1.02]"
        >
          타브 TXT 다운로드
        </button>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <div className="rounded-xl bg-white/5 p-3">
          <p className="text-xs text-slate-400">Tuning</p>
          <p className="font-bold">{tab.tuning}</p>
        </div>
      
        <div className="rounded-xl bg-white/5 p-3">
          <p className="text-xs text-slate-400">Tempo</p>
          <p className="font-bold">
            {tab.tempo ? `${tab.tempo.bpm} BPM` : 'N/A'}
          </p>
        </div>
      
        <div className="rounded-xl bg-white/5 p-3">
          <p className="text-xs text-slate-400">Notes</p>
          <p className="font-bold">{tab.note_count}</p>
        </div>
      
        <div className="rounded-xl bg-white/5 p-3">
          <p className="text-xs text-slate-400">Confidence</p>
          <p className="font-bold">{Math.round((tab.confidence || 0) * 100)}%</p>
        </div>
      </div>
      {tab.warnings.length > 0 && (
        <div className="mt-4 rounded-xl bg-amber-400/10 p-4 text-sm leading-6 text-amber-100">
          {tab.warnings.map((warning) => (
            <p key={warning}>※ {warning}</p>
          ))}
        </div>
      )}

      <p className="mt-4 text-xs leading-5 text-slate-400">{tab.disclaimer}</p>
    </div>
  );
}
