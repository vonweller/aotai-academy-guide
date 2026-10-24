/**
 * 鳌台书院 · AI 非遗导览 · 五关交互主控
 * ---------------------------------------------------------------
 * 流程：开场 → 第1关门口人脸识别 → 小人走到前院 → 第2关问答
 *      → 讲堂楹联 → 工坊问答 → 亭中结语
 * 输入：键盘 N/P/空格/L/R/1-5、按钮、K10 语音（经 Flask+MQTT → SSE）
 * 语音：播放 content.json 中的本地 audio/{lang}/{id}.mp3；缺失时保留字幕
 */
import { World, MAP, assetUrl, FALLBACK_MAP } from './scene.js';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const STAGE_TITLE = {
  1: { zh: '第一关 · 门口迎宾', yue: '第一關 · 門口迎賓' },
  2: { zh: '第二关 · 书院资料待核', yue: '第二關 · 書院資料待核' },
  3: { zh: '第三关 · 题刻待核', yue: '第三關 · 題刻待核' },
  4: { zh: '第四关 · 数字展陈', yue: '第四關 · 數字展陳' },
  5: { zh: '第五关 · 留墨寄愿', yue: '第五關 · 留墨寄願' },
};
// 机位（实机实测）：门楼 z-31 / 讲堂 z-24.7 / 工坊 (-10.5,-8) / 六角亭 (-11,-21)
const STAGE_CAM = {
  1: { walkOffset: [2.4, 3.2, 5.2], idle: { from: [7.0, 7.5, -48.0], look: [0, 4.0, -31.0] } },
  2: { walkOffset: [2.4, 3.2, 5.2], idle: { from: [6.0, 6.0, -37.0], look: [-2.2, 2.6, -24.7] } },
  3: { walkOffset: [2.4, 3.2, 5.2], idle: { from: [-1.0, 4.2, -34.0], look: [-2.2, 2.4, -24.7] } },
  4: { walkOffset: [2.4, 3.2, 5.2], idle: { from: [-2.0, 5.0, 4.0], look: [-11.0, 1.8, -8.0] } },
  5: { walkOffset: [2.4, 3.2, 5.2], idle: { from: [-4.0, 5.0, -12.0], look: [-11.0, 1.6, -21.5] } },
};

// 顺序与来源状态以 content.json.fireEyes 为准；模型与逐项素材未就绪时只展示计划。

const STAGE_ICON = { 1: '門', 2: '源', 3: '聯', 4: '藝', 5: '願' };
const LANG_NAME = { zh: '普通话', yue: '粤语' };

const state = {
  stage: 1,
  lang: 'zh',
  faceOk: false,
  visitor: '',
  walking: false,
  started: false,
  voiceOn: true,
  content: null,
  quizAnswered: {},
  relicQuiz: null,
  // 火眼金睛：五项候选只有在来源、媒体、测验和模型均验收后才可识别
  relicDone: {},
  relicPassedAll: false,
  relicModelEnabled: false,
  points: null,
  backend: false,
  mqtt: false,
  device: { cybercam: false, k10: false },
  speaking: false,
};

let world;
let audioEl = null;
let currentUtter = null;
let typeTimer = null;
let sse = null;

// ------------------------------------------------------------------
// 数据
// ------------------------------------------------------------------
async function loadJSON(url, fallback) {
  try {
    const r = await fetch(url, { cache: 'no-cache' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  } catch (e) {
    console.info('[app] 读取失败，用兜底:', url, e.message);
    return fallback;
  }
}

async function loadContent() {
  // 依次尝试：Flask 的 /data、静态 assets/data、以及直接用 file:// 打开时的相对路径
  const cands = ['/data/content.json', './assets/data/content.json', './data/content.json', '../../02_数据/content.json'];
  for (const url of cands) {
    const r = await loadJSON(url, null).catch(() => null);
    if (r && r.stages) { console.info('[app] content 来源:', url); return r; }
  }
  return { stages: [] };
}

function stageData(n) {
  const c = state.content;
  if (!c || !c.stages) return null;
  return c.stages.find((s) => Number(s.id) === Number(n)) || null;
}

function textOf(obj, lang) {
  if (!obj) return '';
  if (typeof obj === 'string') return obj;
  return obj[lang] || obj.zh || '';
}

function linesOf(n) {
  const st = stageData(n);
  return (st && st.lines) || [];
}

function quizOf(n) {
  const st = stageData(n);
  return (st && st.quiz && st.quiz[0]) || null;
}

// ------------------------------------------------------------------
// UI 基础
// ------------------------------------------------------------------
function setSubtitle(text, speaker) {
  const el = $('#subtitleText');
  const sp = $('#speaker');
  if (sp && speaker) sp.textContent = speaker;
  if (!el) return;
  el.textContent = '';
  if (typeTimer) clearInterval(typeTimer);
  if (!text) return;
  let i = 0;
  typeTimer = setInterval(() => {
    i += 2;
    el.textContent = text.slice(0, i);
    if (i >= text.length) { clearInterval(typeTimer); typeTimer = null; }
  }, 22);
}

function toast(msg, ms = 2200) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), ms);
}

function chip(id, text) {
  const el = $('#' + id);
  if (el) el.textContent = text;
}

function renderStagePanel(n) {
  const panel = $('#stagePanel');
  if (!panel) return;
  const st = stageData(n);
  const quiz = quizOf(n);
  const lines = linesOf(n);
  const name = (st && st.name && (st.name[state.lang] || st.name.zh)) || STAGE_TITLE[n][state.lang];

  let html = '<div class="sp-head"><span class="sp-index">' + n + '</span>' +
    '<div class="sp-title"><strong>' + name + '</strong>' +
    '<em>' + (state.stage === 1 ? '人脸识别 · 欢迎语' : 'AI 讲解 · 互动') + '</em></div></div>';

  // 人脸关
  if (n === 1) {
    html += '<div class="face-box" id="faceBox">' +
      '<p class="face-tip" id="faceTip">' + (state.faceOk ? '识别成功：' + (state.visitor || '预约访客') : '真实摄像头画面在左侧') + '</p>' +
      '</div>';
  } else {
    html += '<ul class="sp-lines">';
    lines.slice(1).forEach((ln) => {
      const t = textOf(ln, state.lang);
      if (t) html += '<li>' + t + '</li>';
    });
    html += '</ul>';
  }

  // 问答
  if (quiz) {
    const q = textOf(quiz.q, state.lang);
    const answered = state.quizAnswered[n];
    html += '<div class="quiz"><p class="q">' + q + '</p><div class="opts">';
    (quiz.options || []).forEach((op) => {
      const cls = answered
        ? (op.key === quiz.answer ? 'opt correct' : (op.key === answered.picked ? 'opt wrong' : 'opt dim'))
        : 'opt';
      html += '<button class="' + cls + '" data-key="' + op.key + '" type="button" ' +
        (answered ? 'disabled' : '') + '><b>' + op.key + '</b><span>' +
        textOf(op, state.lang) + '</span></button>';
    });
    html += '</div>';
    if (answered) {
      html += '<p class="explain ' + (answered.ok ? 'ok' : 'no') + '">' +
        (answered.ok ? '✓ ' : '✗ ') + textOf(quiz.explain, state.lang) + '</p>';
    }
    html += '</div>';
  }

  panel.innerHTML = html;
  panel.classList.add('show');

  panel.querySelectorAll('.opt').forEach((btn) => {
    btn.addEventListener('click', () => answerQuiz(n, btn.dataset.key));
  });
  const sim = $('#simFaceBtn');
  if (sim) sim.addEventListener('click', () => simulateFace());
}

function renderProgress() {
  const nav = $('#progress');
  if (!nav) return;
  let html = '';
  for (let i = 1; i <= 5; i++) {
    const cls = i === state.stage ? 'step active' : (i < state.stage ? 'step done' : 'step');
    html += '<button class="' + cls + '" data-stage="' + i + '" type="button">' +
      '<span class="dot">' + (i < state.stage ? '✓' : STAGE_ICON[i]) + '</span>' +
      '<span class="lbl">' + STAGE_TITLE[i][state.lang].split('·')[0].trim() + '</span></button>';
  }
  nav.innerHTML = html;
  nav.querySelectorAll('.step').forEach((b) => {
    b.addEventListener('click', () => gotoStage(Number(b.dataset.stage)));
  });
}

function syncChips() {
  const dev = state.device || {};
  chip('chipLang', LANG_NAME[state.lang]);
  chip('chipStage', '第 ' + state.stage + ' 关');
  const devTxt = [];
  if (dev.k10_online) devTxt.push('K10 在线');
  if (dev.cybercam_online) devTxt.push('CyberCAM 在线');
  chip('chipNet', (state.mqtt ? 'MQTT 已连接' : (state.backend ? '后端在线' : '本地演示')) +
       (devTxt.length ? ' · ' + devTxt.join(' · ') : ''));
  chip('chipScene', world && world.glbLoaded ? 'Blender 场景' : '程序化场景');
  $$('.lang-btn').forEach((b) => b.classList.toggle('active', b.dataset.lang === state.lang));
}

// ------------------------------------------------------------------
// 语音
// ------------------------------------------------------------------
function speak(lineId, lang = state.lang, text = '') {
  if (!state.voiceOn) { setSubtitle(text); return; }
  stopSpeak();
  const url = assetUrl('/audio/' + lang + '/' + lineId + '.mp3');
  // 兜底不再用浏览器语音合成（机器音）。音频缺失就只显示字幕。
  const fallback = () => { state.speaking = false; };
  if (lineId) {
    if (!audioEl) audioEl = new Audio();
    audioEl.onerror = fallback;
    audioEl.onended = () => { state.speaking = false; };
    audioEl.src = url;
    const p = audioEl.play();
    state.speaking = true;
    if (p && p.catch) p.catch(() => fallback());
    return;
  }
  fallback();
}

// 浏览器语音合成：只用做最后兜底，且默认关闭（听起来像机器音）
const ALLOW_BROWSER_TTS = false;
function speakTTS(text, lang) {
  if (!ALLOW_BROWSER_TTS) return;
  if (!text || !('speechSynthesis' in window)) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang === 'yue' ? 'zh-HK' : 'zh-CN';
    u.rate = 0.95;
    u.pitch = 1.02;
    const voices = window.speechSynthesis.getVoices();
    const pick = voices.find((v) => v.lang === u.lang) ||
      voices.find((v) => v.lang && v.lang.startsWith('zh'));
    if (pick) u.voice = pick;
    currentUtter = u;
    window.speechSynthesis.speak(u);
  } catch (e) {
    console.info('[tts] 失败', e);
  }
}

function stopSpeak() {
  try { if (audioEl) { audioEl.pause(); audioEl.currentTime = 0; } } catch (e) {}
  try { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); } catch (e) {}
  state.speaking = false;
}

function speakStage(n) {
  const st = stageData(n);
  if (!st) return;
  const line = (st.lines && st.lines[0]) || null;
  if (line) {
    speak(line.id, state.lang, textOf(line, state.lang));
    setSubtitle(textOf(line, state.lang));
  }
}

function speakLine(line) {
  if (!line) return;
  const t = textOf(line, state.lang);
  setSubtitle(t);
  speak(line.id, state.lang, t);
}

// ------------------------------------------------------------------
// 后端 / MQTT
// ------------------------------------------------------------------
async function connectBackend() {
  try {
    const r = await fetch('/api/health', { cache: 'no-cache' });
    if (!r.ok) throw new Error('no backend');
    const j = await r.json();
    state.backend = true;
    state.mqtt = !!j.mqtt;
    if (j.device) state.device = j.device;
    syncChips();
    console.info('[app] 后端在线', j);
    startSSE();
    // 每 15 秒刷一次设备在线状态
    setInterval(async () => {
      try {
        const rr = await fetch('/api/health', { cache: 'no-cache' });
        const h = await rr.json();
        state.mqtt = !!h.mqtt;
        if (h.device) state.device = h.device;
        syncChips();
      } catch (e) {}
    }, 15000);
    return true;
  } catch (e) {
    state.backend = false;
    state.mqtt = false;
    syncChips();
    console.info('[app] 无 Flask 后端，纯前端演示');
    return false;
  }
}

function startSSE() {
  if (sse || !window.EventSource) return;
  try {
    sse = new EventSource('/api/stream');
    sse.onmessage = (ev) => {
      try { onBackendEvent(JSON.parse(ev.data)); } catch (e) {}
    };
    sse.onerror = () => { /* 浏览器自动重连 */ };
  } catch (e) { sse = null; }
}

function onBackendEvent(payload) {
  const { topic, data } = payload || {};
  if (!topic || !data) return;
  if (topic === 'aotai/state') {
    state.mqtt = true;
    if (data.lang && data.lang !== state.lang) setLang(data.lang, false);
    if (data.face_ok) { state.faceOk = true; state.visitor = data.visitor || state.visitor; }
    if (data.stage && Number(data.stage) !== state.stage && !state.walking) gotoStage(Number(data.stage), { silent: true });
    syncChips();
    return;
  }
  if (topic === 'aotai/cmd' || topic === 'aotai/k10') {
    const cmd = data.cmd || data.voice_cmd || (data.type === 'voice_cmd' ? data.cmd : null);
    if (cmd) handleCmd(cmd, data);
    return;
  }
  if (topic === 'aotai/event') {
    state.mqtt = true;
    state.device.cybercam = true;
    if (data.type === 'face_recognized') {
      state.faceOk = true;
      state.visitor = data.visitor || '预约访客';
      renderStagePanel(state.stage);
      toast('CyberCAM：识别到 ' + state.visitor);
    } else if (data.type === 'face_unknown') {
      toast('CyberCAM：未注册访客，可现场按 K 键录入');
    } else if (data.type === 'lang_changed' && data.lang) {
      setLang(data.lang, false);
    } else if (data.type === 'tour_start') {
      syncTourFromCamera(Number(data.stage || 1), data.lang);
    } else if (data.type === 'stage_enter' && data.stage) {
      syncTourFromCamera(Number(data.stage), data.lang);
    } else if (data.type === 'relic_mode') {
      // 相机进入识别环节；禁用期间仅展示候选计划，不启动自动识别。
      state.relicDone = state.relicDone || {};
      state.relicModelEnabled = data.recognition_enabled === true && relicRecognitionReady();
      (data.done || []).forEach((k) => { state.relicDone[k] = true; });
      if (data.lang) setLang(data.lang, false);
      enterRelicStage(true);
    } else if (data.type === 'relic') {
      if (!relicRecognitionReady() || !state.relicModelEnabled) return;
      relicRecognized(data.key, !!data.spoken || !!data.fromCamera);
      // 相机已经发声时不要再播一遍，否则粤语和普通话会叠在一起
      if (!(data.spoken || state.camAudio)) {
        if (data.id) playConfiguredSpeech(data.id, data.lang);
      }
    } else if (data.type === 'relic_quiz') {
      if (relicRecognitionReady() && state.relicModelEnabled && data.quiz && !Object.prototype.hasOwnProperty.call(data.quiz, 'answer')) relicQuiz(data.key, data.quiz);
    } else if (data.type === 'relic_quiz_result') {
      if (relicRecognitionReady() && state.relicModelEnabled) relicQuizResult(data.key, !!data.ok);
    } else if (data.type === 'relic_pass') {
      if (relicRecognitionReady() && state.relicModelEnabled) relicPassed(data.key, data.done, data.all);
    } else if (data.type === 'relic_all_done') {
      if (!relicRecognitionReady() || !state.relicModelEnabled) return;
      state.relicPassedAll = true;
      (data.done || []).forEach((k) => { state.relicDone[k] = true; });
      finishAllTasks();
    } else if (data.type === 'speak_stop') {
      stopSpeak();
    } else if (data.type === 'speak' && typeof data.id === 'string') {
      // Public MQTT clients must not replay orphaned legacy audio IDs or stale copy.
      playConfiguredSpeech(data.id, data.lang);
    } else if (data.type === 'reset') {
      resetTour();
    }
    syncChips();
    return;
  }
  if (topic === 'aotai/points') {
    loadPoints(true);
    if (data && data.gain) toast('积分 +' + data.gain);
    return;
  }
  if (topic === 'web/cmd') {
    handleCmd(data.cmd || data.action, data);
  }
}

function handleCmd(cmd, data) {
  switch (cmd) {
    case 'next': nextStage(); break;
    case 'prev': prevStage(); break;
    case 'repeat': repeatLine(); break;
    case 'set_lang': setLang(data.lang || 'zh'); break;
    case 'lang_yue': setLang('yue'); break;
    case 'lang_zh': setLang('zh'); break;
    case 'goto': case 'goto_stage':
      if (data.stage) gotoStage(Number(data.stage));
      break;
    case 'speak':
      playConfiguredSpeech(data.id, data.lang);
      break;
    case 'reset': resetTour(); break;
    case 'relic_start': hideRelicPanel(); break;
    case 'quiz':
      if (data.qid && data.answer) answerQuiz(Number(data.stage || state.stage), data.answer, true);
      break;
    default: break;
  }
}

async function sendCmd(body) {
  try {
    await fetch('/api/cmd', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (e) { /* 纯前端模式忽略 */ }
}

async function pushState(patch) {
  try {
    await fetch('/api/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
  } catch (e) {}
}

// ------------------------------------------------------------------
// 关卡流程
// ------------------------------------------------------------------
function stopAt(stage) {
  const st = MAP.stages.find((s) => Number(s.stage) === Number(stage));
  return (st && st.actorStop) || [0, 0, 0];
}

function pathBetween(from, to) {
  const k = from + '-' + to;
  if (MAP.walkPaths && MAP.walkPaths[k]) return MAP.walkPaths[k];
  const a = stopAt(from), b = stopAt(to);
  return [a, [(a[0] + b[0]) / 2, Math.max(a[1], b[1]), (a[2] + b[2]) / 2], b];
}

function syncTourFromCamera(n, lang) {
  if (lang) setLang(lang, false);
  const intro = document.querySelector('#intro');
  if (intro) { intro.classList.add('hide'); intro.setAttribute('hidden', ''); }
  state.started = true;
  state.walking = false;
  if (world && world.stopWalk) world.stopWalk();
  n = Math.max(1, Math.min(5, Number(n) || 1));
  state.stage = n;
  if (world) world.placeScholar(stopAt(n), [0, 0, 1]);
  renderProgress();
  renderStagePanel(n);
  updateStageCamera(n, true);
  syncChips();
  toast('CyberCAM 同步到第 ' + n + ' 关');
}

function gotoStage(n, opts = {}) {
  n = Math.max(1, Math.min(5, Number(n) || 1));
  // 首次到达某关：给通关积分（同一关只加一次）
  if (!opts.silent && n > (state._maxStage || 1)) {
    state._maxStage = n;
    addPointsLocal('stage_clear', '第' + n + '关');
  }
  if (state.walking) {
    if (opts.force) {
      world.stopWalk();
      state.walking = false;
    } else {
      // 排队：等走到后立刻前往目标关（演示时连按 N 也能到）
      state.pendingStage = n;
      toast('正在赶路，到站后立即前往第 ' + n + ' 关');
      return;
    }
  }
  const from = state.stage;
  if (from === n && state.started) {
    speakStage(n);
    renderStagePanel(n);
    return;
  }
  state.stage = n;
  state.quizAnswered[n] = state.quizAnswered[n] || null;
  renderProgress();
  syncChips();
  renderStagePanel(n);

  const pts = pathBetween(from, n);
  if (world && world.scholar) {
    if (world.pathVisible) world.showPath(pts);
    state.walking = true;
    // 先播一句"前往第X关"
    const goText = state.lang === 'yue'
      ? '我哋去第' + n + '關，跟實我行。'
      : '我们去第' + n + '关，跟着我走。';
    setSubtitle(goText);
    const camCfg = STAGE_CAM[n] || STAGE_CAM[1];
    world.followActor(camCfg.walkOffset);
    world.walkPath(pts, (MAP.actor && MAP.actor.walkSpeed ? MAP.actor.walkSpeed : 1.6) * 1.8, () => {
      state.walking = false;
      onArrive(n);
      const pend = state.pendingStage;
      state.pendingStage = null;
      if (pend && pend !== n) setTimeout(() => gotoStage(pend), 400);
    });
  } else {
    onArrive(n);
  }
  if (!opts.silent) {
    pushState({ stage: n, lang: state.lang });
    sendCmd({ cmd: 'goto_stage', stage: n });
  }
  updateStageCamera(n);
}

function onArrive(n) {
  const st = MAP.stages.find((s) => Number(s.stage) === Number(n));
  if (st && world) {
    world.placeScholar(st.actorStop || [0, 0, 0], null);
  }
  renderStagePanel(n);
  // 到站后再播讲解
  setTimeout(() => speakStage(n), 350);
  if (n === 1 && !state.faceOk) {
    setTimeout(() => runFaceDetect(), 900);
  }
  updateStageCamera(n);
}

function updateStageCamera(n, instant) {
  if (!world) return;
  const cfg = STAGE_CAM[n] || STAGE_CAM[1];
  if (instant) {
    world.followActor(null);
    if (world.camera) world.camera.position.set(cfg.idle.from[0], cfg.idle.from[1], cfg.idle.from[2]);
    if (world.orbit) {
      world.orbit.target.set(cfg.idle.look[0], cfg.idle.look[1], cfg.idle.look[2]);
      world.orbit.update();
    }
    return;
  }
  world.followActor(null);
  world.setCameraPreset(cfg.idle);
}

function nextStage() {
  if (state.stage >= 5 && !state.walking) {
    // 五关走完：进入火眼金睛环节（最后一道任务），而不是停在结尾
    enterRelicStage();
    return;
  }
  gotoStage(state.stage + 1);
}

/** Five stages lead to the planned, disabled candidate-review screen. */
const RELIC_ORDER_FALLBACK = ['houjie_yuexiu', 'houjie_shuangshou_hongquan', 'aotai_aoyu_brick', 'guancao', 'qingxi_qilin_zhazuo'];

function relicOrder() {
  const configured = state.content && state.content.fireEyes && state.content.fireEyes.order;
  if (Array.isArray(configured) && configured.length) return configured.slice();
  return RELIC_ORDER_FALLBACK.slice();
}

function configuredSpeechIds() {
  const content = state.content && typeof state.content === 'object' ? state.content : {};
  const ids = new Set(['p_points']);
  const add = (id) => { if (typeof id === 'string' && id.trim()) ids.add(id); };
  const stages = Array.isArray(content.stages) ? content.stages : [];
  stages.forEach((stage) => {
    if (!stage || typeof stage !== 'object') return;
    add(stage.entry);
    (Array.isArray(stage.lines) ? stage.lines : []).forEach((line) => add(line && line.id));
    (Array.isArray(stage.quiz) ? stage.quiz : []).forEach((quiz) => {
      if (!quiz || typeof quiz !== 'object' || typeof quiz.qid !== 'string') return;
      add(quiz.qid + '_q'); add(quiz.qid + '_a'); add(quiz.qid + '_wrong');
      (Array.isArray(quiz.options) ? quiz.options : []).forEach((option) => {
        if (option && typeof option.key === 'string') add(quiz.qid + '_op' + option.key);
      });
    });
  });
  (Array.isArray(content.prompts) ? content.prompts : []).forEach((prompt) => add(prompt && prompt.id));
  (Array.isArray(content.relics) ? content.relics : []).forEach((relic) => {
    if (!relic || typeof relic !== 'object') return;
    add(relic.id);
    const quiz = relic.quiz;
    if (quiz && typeof quiz === 'object') { add(relic.id + '_q'); add(relic.id + '_ok'); add(relic.id + '_no'); }
  });
  return ids;
}

function configuredSpeechText(id, lang) {
  const content = state.content && typeof state.content === 'object' ? state.content : {};
  const language = lang === 'yue' ? 'yue' : 'zh';
  const textFrom = (pair) => pair && (pair[language] || pair.zh || '');
  if (id === 'p_points') return language === 'yue' ? '积分又多咗。' : '积分又多了。';

  for (const stage of (Array.isArray(content.stages) ? content.stages : [])) {
    const line = (Array.isArray(stage.lines) ? stage.lines : []).find((item) => item && item.id === id);
    if (line) return textFrom(line);
    for (const quiz of (Array.isArray(stage.quiz) ? stage.quiz : [])) {
      if (!quiz || typeof quiz.qid !== 'string') continue;
      if (id === quiz.qid + '_q') return textFrom(quiz.q);
      if (id === quiz.qid + '_a') return textFrom(quiz.explain);
      if (id === quiz.qid + '_wrong') return textFrom(quiz.explain_wrong);
      const optionPrefix = quiz.qid + '_op';
      if (id.startsWith(optionPrefix)) {
        const option = (Array.isArray(quiz.options) ? quiz.options : []).find((item) =>
          item && typeof item.key === 'string' && id === optionPrefix + item.key);
        if (option) return textFrom(option);
      }
    }
  }
  const prompt = (Array.isArray(content.prompts) ? content.prompts : []).find((item) => item && item.id === id);
  if (prompt) return textFrom(prompt);
  for (const relic of (Array.isArray(content.relics) ? content.relics : [])) {
    if (!relic || typeof relic !== 'object') continue;
    if (relic.id === id) return textFrom(relic);
    const quiz = relic.quiz;
    if (!quiz || typeof relic.id !== 'string') continue;
    if (id === relic.id + '_q') return textFrom(quiz.q);
    if (id === relic.id + '_ok') return textFrom(quiz.ok);
    if (id === relic.id + '_no') return textFrom(quiz.no);
  }
  return '';
}

function playConfiguredSpeech(id, requestedLang) {
  if (typeof id !== 'string' || !configuredSpeechIds().has(id)) return false;
  const lang = requestedLang === 'zh' || requestedLang === 'yue'
    ? requestedLang
    : (state.lang === 'yue' ? 'yue' : 'zh');
  const text = configuredSpeechText(id, lang);
  if (typeof text !== 'string' || !text.trim()) return false;
  speak(id, lang, text);
  setSubtitle(text);
  return true;
}

function relicRecognitionReady() {
  const keys = relicOrder();
  if (keys.length !== RELIC_ORDER_FALLBACK.length ||
      keys.some((key, index) => key !== RELIC_ORDER_FALLBACK[index])) return false;
  const content = state.content;
  if (!content || typeof content !== 'object' || Array.isArray(content) ||
      !Array.isArray(content.relics) || content.relics.length !== keys.length) return false;
  const fireEyes = content.fireEyes;
  if (!fireEyes || typeof fireEyes !== 'object' || Array.isArray(fireEyes) ||
      fireEyes.status !== 'verified' || !Array.isArray(fireEyes.order) ||
      fireEyes.order.length !== keys.length ||
      fireEyes.order.some((key, index) => key !== keys[index])) return false;
  const byKey = new Map();
  for (const row of content.relics) {
    if (!row || typeof row !== 'object' || Array.isArray(row) ||
        typeof row.key !== 'string' || byKey.has(row.key)) return false;
    byKey.set(row.key, row);
  }
  if (keys.some((key) => !byKey.has(key))) return false;
  const isRecord = (value) => !!value && typeof value === 'object' && !Array.isArray(value);
  const refsReady = (refs, fields) => Array.isArray(refs) && refs.length > 0 && refs.every((ref) =>
    isRecord(ref) && fields.every((field) => typeof ref[field] === 'string' && ref[field].trim()));
  return keys.every((key) => {
    const item = byKey.get(key);
    const recognition = item.recognition;
    const quiz = item.quiz;
    const validation = item.model_validation;
    if (!isRecord(recognition) || !isRecord(quiz) || !isRecord(validation)) return false;
    const question = quiz.q;
    const options = quiz.options;
    const report = validation.independent_test_report;
    const deployment = validation.deployment_report;
    if (!isRecord(question) || !Array.isArray(options) || options.length < 2 ||
        !isRecord(report) || !isRecord(deployment) || !options.every(isRecord)) return false;
    const optionKeys = options.map((op) => op.key);
    const uniqueKeys = new Set(optionKeys);
    // 识别可用性只看模型/授权/题卡；史实出处属于展陈核验，不阻塞识别。
    return item.media_rights_status === 'authorized' &&
      refsReady(item.media_rights_refs, ['rights_holder', 'permission_ref']) &&
      recognition.enabled === true && recognition.status === 'verified' &&
      validation.status === 'passed' &&
      ['report_ref', 'test_set_id'].every((field) => typeof report[field] === 'string' && report[field].trim()) &&
      validation.deployment_validation === 'passed' &&
      ['report_ref', 'device_model', 'firmware_version'].every((field) => typeof deployment[field] === 'string' && deployment[field].trim()) &&
      ['zh', 'yue'].every((lang) => typeof question[lang] === 'string' && question[lang].trim()) &&
      optionKeys.every((optionKey) => typeof optionKey === 'string' && optionKey.trim()) &&
      uniqueKeys.size === optionKeys.length && options.every((op) =>
        ['zh', 'yue'].every((lang) => typeof op[lang] === 'string' && op[lang].trim())) &&
      optionKeys.includes(quiz.answer);
  });
}

function enterRelicStage(silentAudio = false) {
  const contentReady = relicRecognitionReady();
  // 内容就绪即可进入流程；设备在线时再叠加设备侧识别，
  // 不能因为设备没回连就把整个环节判为未启用。
  if (contentReady) state.relicModelEnabled = true;
  if (!contentReady) {
    const groups = (state.content && state.content.fireEyes && state.content.fireEyes.groups) || [];
    const keys = relicOrder();
    const groupMarkup = groups.length ? groups.map((group) =>
      '<h3 class="rp-group">' + ((group.label || {})[state.lang] || (group.label || {}).zh || group.id) + '</h3>' +
      '<div class="rp-grid">' + (group.keys || []).map((key) => relicCardMarkup(key)).join('') + '</div>'
    ).join('') : '<div class="rp-grid">' + keys.map((key) => relicCardMarkup(key)).join('') + '</div>' ;
    const text = !contentReady
      ? (state.lang === 'yue'
        ? '候選清單已列出，但類別來源、實物相片與模型仍待核實，暫不自動識別或計分。'
        : '候选清单已列出，但类别来源、实物图片与模型仍待核实，暂不自动识别或计分。')
      : (state.lang === 'yue'
        ? '候選清單已列出，但設備尚未回報啟用；目前不會識別或計分。'
        : '候选清单已列出，但设备尚未确认启用；当前不会识别或计分。');
    state.relicModelEnabled = false;
    state.relicPassedAll = false;
    setSubtitle(text);
    if (!silentAudio) speak('p_relic_task_v2', state.lang, text);
    showRelicPanel('<p class="rp-name">火眼金睛 · 候选清单（未启用）</p>' +
      '<p class="rp-line">' + text + '</p>' + groupMarkup +
      '<p class="rp-tip">补齐权威来源、类别对应的授权示范图片和独立验证模型后，再评估是否启用识别。</p>');
    return;
  }
  if (state.relicPassedAll) {
    finishAllTasks();
    return;
  }
  const need = relicOrder().filter((k) => !state.relicDone[k]);
  const names = need.map(relicName).join('、');
  setSubtitle('火眼金睛已启动。把非遗图片放到 CyberCAM 镜头前即可识别，也可直接点击下面的卡片进入答题。');
  if (!silentAudio) speak('p_relic_intro_active_v2', state.lang, '本次图像识别流程已启动。');
  renderRelicChooser();
  toast('五关走完！进入火眼金睛');
}

/** 可点击的候选卡片：设备未连上时也能直接进入该项目答题。 */
function renderRelicChooser() {
  const keys = relicOrder();
  const doneCount = keys.filter((k) => state.relicDone[k]).length;
  const cards = keys.map((key) => {
    const done = !!state.relicDone[key];
    const r = relicOf(key) || {};
    const note = (r.photo_note || {})[state.lang] || (r.photo_note || {}).zh || '';
    return '<button class="rp-pick' + (done ? ' is-done' : '') + '" type="button" data-pick="' + key + '">' +
      '<img src="/assets/relics/' + key + '.jpg" alt="' + relicName(key) + '" loading="lazy" ' +
      'onerror="this.classList.add(\'is-missing\')">' +
      '<span class="rp-pick-name">' + (done ? '✓ ' : '') + relicName(key) + '</span>' +
      '<span class="rp-pick-note">' + (done ? (state.lang === 'yue' ? '已完成' : '已完成') : note) + '</span>' +
      '</button>';
  }).join('');
  showRelicPanel(
    '<p class="rp-name">火眼金睛 · 选一项开始</p>' +
    '<p class="rp-line">已识别 ' + doneCount + ' / ' + keys.length + ' 项。把卡片放到 CyberCAM 前会自动识别，' +
    '也可以直接点下面的图片进入该项目。</p>' +
    '<div class="rp-pick-grid">' + cards + '</div>' +
    '<p class="rp-tip">' + (doneCount >= keys.length ? '全部完成，正在打开兑换…' : '全部完成后进入兑换页面') + '</p>');
  $$('.rp-pick').forEach((b) => {
    b.addEventListener('click', () => startRelicByKey(b.dataset.pick));
  });
}

/** 网页端直接开始某一项（不依赖设备识别事件）。 */
function startRelicByKey(key, opts) {
  if (!relicRecognitionReady()) return;
  if (!relicOrder().includes(key)) return;
  if (state.relicDone[key] && !(opts && opts.force)) return;
  state.relicModelEnabled = true;
  focusRelicScene(key);
  const r = relicOf(key) || {};
  const text = r[state.lang] || r.zh || '';
  const name = relicName(key);
  showRelicPanel(
    '<div class="rp-card">' +
    '<img class="rp-photo" src="/assets/relics/' + key + '.jpg" alt="' + name + '" ' +
    'onerror="this.style.display=\'none\'">' +
    '<div class="rp-body">' +
    '<p class="rp-kicker">' + (state.lang === 'yue' ? '項目講解' : '项目讲解') + '</p>' +
    '<p class="rp-name">' + name + '</p>' +
    '<p class="rp-line">' + text + '</p>' +
    '<p class="rp-tip">讲解结束后出题</p>' +
    '</div></div>');
  if (!(opts && opts.silent)) speak(r.id || '', state.lang, text);
  // 先听再答：3 秒后弹题
  state._relicTimer = setTimeout(() => {
    const quiz = r.quiz;
    if (quiz) relicQuiz(key, quiz);
  }, 3000);
}

/** 所有任务完成 → 先道喜、再总结书院，最后打开兑换 */
function finishAllTasks() {
  if (!relicRecognitionReady() || !state.relicModelEnabled) return;
  if (state._finished) return;
  state._finished = true;
  state.relicPassedAll = true;
  setSubtitle('本次图像匹配体验已完成。');
  toast('五项非遗展项全部完成！');
  // 1) 恭喜
  speak('p_congrats_v2', state.lang, '本次数字导览已完成，多谢参与。');
  // 2) 书院总结（等恭喜播完）
  setTimeout(() => {
    setSubtitle('谢谢你陪小鳌完成数字导览。');
    speak('p_summary_v2', state.lang, '谢谢你陪小鳌走完这一程。');
  }, 6200);
  // 3) 总结之后弹出兑换
  setTimeout(() => openShop(), 12000);
}

function prevStage() {
  if (state.stage <= 1 && !state.walking) { speakStage(1); return; }
  gotoStage(state.stage - 1);
}

function repeatLine() {
  speakStage(state.stage);
  toast('重播本关讲解');
}

function setLang(lang, announce = true) {
  if (lang !== 'zh' && lang !== 'yue') return;
  if (state.lang === lang) return;
  state.lang = lang;
  renderProgress();
  renderStagePanel(state.stage);
  syncChips();
  if (announce) {
    const pid = lang === 'yue' ? 'p_lang_yue' : 'p_lang_zh';
    const t = lang === 'yue' ? '好，我改用粵語同你講。' : '好的，改用普通话为你讲解。';
    setSubtitle(t);
    speak(pid, lang, t);
  }
  pushState({ lang });
  sendCmd({ cmd: 'set_lang', lang });
}

function resetTour() {
  if (world && world.stopWalk) {
    try { world.stopWalk(); } catch (e) {}
  }
  state.walking = false;
  state.faceOk = false;
  state.visitor = '';
  state.quizAnswered = {};
  state.relicDone = {};
  state.relicPassedAll = false;
  state.relicModelEnabled = false;
  state._finished = false;
  state._maxStage = 1;
  state.stage = 1;
  if (world && world.scholar) {
    world.placeScholar(stopAt(1), [0, 0, 0]);
  }
  renderProgress();
  renderStagePanel(1);
  syncChips();
  updateStageCamera(1);
  setSubtitle('回到第一关，门口迎宾。');
  pushState({ stage: 1, face_ok: false, visitor: '' });
  sendCmd({ cmd: 'reset' });
}

function answerQuiz(n, key, fromRemote = false) {
  const quiz = quizOf(n);
  if (!quiz || state.quizAnswered[n]) return;
  const ok = key === quiz.answer;
  state.quizAnswered[n] = { picked: key, ok };
  renderStagePanel(n);
  // 答错必须播“错”的解释，不能一律播正确答案的讲解。
  const wrong = textOf(quiz.explain_wrong || {}, state.lang);
  const explain = ok
    ? (textOf(quiz.explain, state.lang) || '答对了！')
    : (wrong || textOf(quiz.explain, state.lang) || '再想想哦。');
  setSubtitle(explain);
  // 用已生成的 mp3：对 q1_a，错 q1_wrong。浏览器 TTS 在没粤语音色时会落回普通话。
  const lineId = quiz.qid ? (quiz.qid + (ok ? '_a' : '_wrong')) : '';
  if (lineId) speak(lineId, state.lang, explain);
  // 没有对应音频就只显示字幕，不退回浏览器 TTS
  if (!fromRemote && ok) addPointsLocal('quiz_right');
  if (!fromRemote) {
    sendCmd({ cmd: 'quiz', stage: n, qid: quiz.qid, answer: key });
  }
  toast(ok ? '✓ 回答正确' : '✗ 再试一次也没关系');
  if (ok) setTimeout(() => toast('按 N 前往下一关'), 1600);
}

// ---------- 人脸（网页演示） ----------
function simulateFace() {
  state.faceOk = true;
  state.visitor = state.visitor || '预约访客';
  renderStagePanel(1);
  const line = linesOf(1).find((l) => l.id === 's1_welcome_ok_v2') || linesOf(1)[1];
  if (line) speakLine(line);
  toast('识别成功：' + state.visitor);
  pushState({ face_ok: true, visitor: state.visitor });
}

function runFaceDetect() {
  toast('门口摄像头正在识别…');
  const tip = $('#faceTip');
  if (tip) tip.textContent = '识别中，请正对镜头…';
  // 尝试请求真实后端（CyberCAM 经 MQTT 上报），3 秒无响应则提示可模拟
  setTimeout(() => {
    if (!state.faceOk) {
      const t = $('#faceTip');
      if (t) t.textContent = '等待 CyberCAM 上报…（可点「模拟识别」演示）';
    }
  }, 2600);
}

// ------------------------------------------------------------------
// 事件绑定
// ------------------------------------------------------------------
function bindUI() {
  $$('.lang-btn').forEach((b) => b.addEventListener('click', () => setLang(b.dataset.lang)));
  $$('[data-action]').forEach((b) => {
    b.addEventListener('click', () => {
      switch (b.dataset.action) {
        case 'next': nextStage(); break;
        case 'prev': prevStage(); break;
        case 'repeat': repeatLine(); break;
        case 'reset': resetTour(); break;
        default: break;
      }
    });
  });
  const voiceBtn = $('#voiceBtn');
  if (voiceBtn) voiceBtn.addEventListener('click', () => {
    state.voiceOn = !state.voiceOn;
    voiceBtn.classList.toggle('off', !state.voiceOn);
    voiceBtn.textContent = state.voiceOn ? '🔊 语音' : '🔇 静音';
    if (!state.voiceOn) stopSpeak();
  });
  const pathBtn = $('#pathBtn');
  if (pathBtn) pathBtn.addEventListener('click', () => {
    if (!world) return;
    const v = !world.pathVisible;
    world.setPathVisible(v);
    pathBtn.classList.toggle('on', v);
    if (v) world.showPath(pathBetween(Math.max(1, state.stage - 1), state.stage));
  });
  const camBtn = $('#camBtn');
  if (camBtn) camBtn.addEventListener('click', cycleCamera);
  const fsBtn = $('#fsBtn');
  if (fsBtn) fsBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen && document.documentElement.requestFullscreen();
    else document.exitFullscreen && document.exitFullscreen();
  });
  const helpBtn = $('#helpBtn');
  const helpModal = $('#helpModal');
  const helpClose = $('#helpClose');
  if (helpBtn && helpModal) helpBtn.addEventListener('click', () => helpModal.removeAttribute('hidden'));
  if (helpClose && helpModal) helpClose.addEventListener('click', () => helpModal.setAttribute('hidden', ''));
  const startBtn = $('#startBtn');
  if (startBtn) startBtn.addEventListener('click', startTour);
  const scoreBtn = $('#scoreBtn');
  if (scoreBtn) scoreBtn.addEventListener('click', openShop);
  const shopClose = $('#shopClose');
  const shopModal = $('#shopModal');
  if (shopClose && shopModal) shopClose.addEventListener('click', () => { shopModal.hidden = true; });

  document.addEventListener('keydown', onKey);
}

function onKey(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === 'n' || k === 'arrowright') { e.preventDefault(); nextStage(); }
  else if (k === 'p' || k === 'arrowleft') { e.preventDefault(); prevStage(); }
  else if (k === ' ') { e.preventDefault(); repeatLine(); }
  else if (k === 'l') { setLang(state.lang === 'zh' ? 'yue' : 'zh'); }
  else if (k === 'r') { resetTour(); }
  else if (k === 'c') { cycleCamera(); }
  else if (k === 'v') { const b = $('#voiceBtn'); if (b) b.click(); }
  else if (k === 'h') { const b = $('#helpBtn'); if (b) b.click(); }
  else if (k >= '1' && k <= '5') { gotoStage(Number(k)); }
}

// ------------------------------------------------------------------
// 火眼金睛（跟随 CyberCAM 上报）
// ------------------------------------------------------------------
const RELIC_INFO = {
  houjie_yuexiu: { zh: '厚街粤绣（候选）', yue: '厚街粵繡（候選）' },
  houjie_shuangshou_hongquan: { zh: '厚街双手洪拳（候选）', yue: '厚街雙手洪拳（候選）' },
  aotai_aoyu_brick: { zh: '鳌鱼砖（出处待核）', yue: '鰲魚磚（出處待核）' },
  guancao: { zh: '莞草编织（候选）', yue: '莞草編織（候選）' },
  qingxi_qilin_zhazuo: { zh: '清溪麒麟扎作（候选）', yue: '清溪麒麟紮作（候選）' },
};

function relicOf(key) {
  const list = (state.content && state.content.relics) || [];
  return list.find((r) => r.key === key) || null;
}

function relicName(key) {
  const r = relicOf(key);
  if (r && r.name) {
    const raw = r.name[state.lang] || r.name.zh || key;
    if (r.proposal_status === 'proposed_candidate')
      return raw + (key === 'aotai_aoyu_brick' ? '（出处待核）' : '（候选）');
    return raw;
  }
  const f = RELIC_INFO[key];
  return f ? (f[state.lang] || f.zh) : key;
}

function relicCardMarkup(key) {
  const name = relicName(key);
  const r = relicOf(key) || {};
  const note = (r.photo_note || {})[state.lang] || (r.photo_note || {}).zh || '';
  const tip = state.lang === 'yue' ? '示意相片，非本地實物' : '示意图片，非本地实物';
  return '<figure class="rp-item">' +
    '<img src="/assets/relics/' + key + '.jpg" alt="' + name + '" loading="lazy" ' +
    'onerror="this.classList.add(\'is-missing\')">' +
    '<figcaption><span class="rp-item-name">' + name + '</span>' +
    '<span class="rp-item-note">' + (note || tip) + '</span></figcaption></figure>';
}

function showRelicPanel(html) {
  const p = $('#relicPanel');
  const b = $('#rpBody');
  if (!p || !b) return;
  b.innerHTML = html;
  p.hidden = false;
}

function focusRelicScene(key) {
  if (!world || !world.setCameraPreset) return false;
  const presets = (MAP && MAP.cameraPresets) || {};
  const preset = presets['relic_' + key];
  if (!preset) return false;
  state.relicFocused = key;
  world.followActor(null);
  world.setCameraPreset(preset);
  const tag = $('#chipScene');
  if (tag) tag.textContent = '识别画面 · ' + relicName(key);
  return true;
}

function reloadRelicScene(key) {
  // 设备认出类别后，把网页镜头切到该项目对应的展陈画面
  state.relicFocusKey = key;
  if (!focusRelicScene(key)) {
    // 机位缺失时退回工坊总视角
    const presets = (MAP && MAP.cameraPresets) || {};
    if (presets.stageWorkshop) world && world.setCameraPreset(presets.stageWorkshop);
  }
}

function relicRecognized(key, silentAudio) {
  if (!relicRecognitionReady() || !state.relicModelEnabled) return;
  if (!relicOrder().includes(key)) return;
  reloadRelicScene(key);
  const r = relicOf(key);
  const text = r ? (r[state.lang] || r.zh || '') : '';
  const name = relicName(key);
  // 识别卡片：文物照片 + 名称 + 历史讲解（带说明是 AI 正在介绍）
  showRelicPanel(
    '<div class="rp-card">' +
    '<img class="rp-photo" src="/assets/relics/' + key + '.jpg" alt="' + name + '" ' +
    'onerror="this.style.display=\'none\'">' +
    '<div class="rp-body">' +
    '<p class="rp-kicker">' + (state.lang === 'yue' ? '圖像匹配' : '图像匹配') + '</p>' +
    '<p class="rp-name">' + name + '</p>' +
    '<p class="rp-line">' + text + '</p>' +
    '<p class="rp-tip">讲解结束后会出题，请听题目</p>' +
    '</div></div>');
  // 用预生成音频讲历史（不用浏览器 TTS，避免机器音）
  // 相机端已经播过时，这里只显示卡片不重复发声
  if (!silentAudio) {
    if (r && r.id) speak(r.id, state.lang, text);
  } else {
    stopSpeak();
  }
  // Recognition rewards are disabled here until one authenticated backend ledger is used.
}

function relicQuiz(key, quiz) {
  if (!relicRecognitionReady() || !state.relicModelEnabled || !relicOrder().includes(key)) return;
  const q = (quiz && quiz.q) ? (quiz.q[state.lang] || quiz.q.zh) : '';
  const opts = (quiz && Array.isArray(quiz.options)) ? quiz.options : [];
  if (!q || opts.length < 2 || opts.some((op) => !op || typeof op.key !== 'string')) return;
  let html = '<p class="rp-name">' + relicName(key) + '</p>';
  html += '<p class="rp-q">' + q + '</p><div class="rp-opts">';
  opts.forEach((op) => {
    html += '<button class="rp-opt" type="button" data-k="' + op.key + '">' +
      '<b>' + op.key + '</b> ' + (op[state.lang] || op.zh) + '</button>';
  });
  html += '</div><p class="rp-res" id="rpRes"></p>';
  showRelicPanel(html);
  const correct = quiz && quiz.answer;
  $$('.rp-opt').forEach((b) => {
    b.addEventListener('click', () => {
      const picked = b.dataset.k;
      sendCmd({ cmd: 'relic_answer', key: key, answer: picked });
      // 设备在线时由设备判定；离线时网页本地判定并推进
      if (typeof correct === 'string' && correct) {
        const ok = picked === correct;
        relicQuizResult(key, ok);
        if (ok) setTimeout(() => passRelicLocally(key), 900);
      } else {
        sendCmd({ cmd: 'relic_start' });
      }
    });
  });
  state.relicQuiz = { key: key, quiz: { q: quiz.q, options: opts } };
}

/** 网页端本地过关：计入完成、加分展示、回到选择页或结束。 */
function passRelicLocally(key) {
  if (!relicOrder().includes(key)) return;
  state.relicDone[key] = true;
  const keys = relicOrder();
  const left = keys.filter((k) => !state.relicDone[k]);
  if (!left.length) {
    state.relicPassedAll = true;
    showRelicPanel('<p class="rp-name">全部完成！</p>' +
      '<p class="rp-line">五项非遗展项都认完了，正在打开兑换页面…</p>');
    setTimeout(() => finishAllTasks(), 1200);
    return;
  }
  const presets = (MAP && MAP.cameraPresets) || {};
  if (presets.stageWorkshop && world && world.setCameraPreset) world.setCameraPreset(presets.stageWorkshop);
  renderRelicChooser();
}

function relicQuizResult(key, ok) {
  if (!relicRecognitionReady() || !state.relicModelEnabled) return;
  const res = $('#rpRes');
  $$('.rp-opt').forEach((b) => { b.disabled = !!ok; });
  if (res) res.textContent = ok ? '✓ 答对了，请再拿一次给摄像头认' : '✗ 再想想，可以重选';
  // The answer key stays on the trusted device; the browser only shows the result.
}

function relicPassed(key, doneFromCam, allFromCam) {
  if (!relicRecognitionReady() || !state.relicModelEnabled || !relicOrder().includes(key)) return;
  state.relicDone[key] = true;
  // 过关后回到工坊总视角，等下一项
  const presets = (MAP && MAP.cameraPresets) || {};
  if (presets.stageWorkshop && world && world.setCameraPreset) {
    world.setCameraPreset(presets.stageWorkshop);
  }
  state.relicFocused = null;
  const tag = $('#chipScene');
  if (tag) tag.textContent = '工坊 · 等待下一件';
  // 相机端带来的已完成列表优先（两端进度对齐）
  if (Array.isArray(doneFromCam)) {
    doneFromCam.forEach((k) => { state.relicDone[k] = true; });
  }
  const need = relicOrder();
  const left = need.filter((k) => !state.relicDone[k]);
  if (allFromCam || left.length === 0) {
    state.relicPassedAll = true;
    showRelicPanel('<p class="rp-name">五项识别任务完成！</p>' +
      '<p class="rp-line">所有任务完成，正在打开兑换…</p>');
    setTimeout(() => finishAllTasks(), 1200);
    return;
  }
  showRelicPanel('<p class="rp-name">' + relicName(key) + ' · 图像匹配确认</p>' +
    '<p class="rp-line">本次图像匹配已确认；尚有 ' + left.length + ' 项：' +
    left.map(relicName).join('、') + '</p>' +
    '<ul class="rp-list">' +
    need.map((k) => '<li class="' + (state.relicDone[k] ? 'done' : '') + '">' +
      (state.relicDone[k] ? '✓ ' : '○ ') + relicName(k) + '</li>').join('') +
    '</ul>');
}

function hideRelicPanel() {
  const p = $('#relicPanel');
  if (p) p.hidden = true;
  state.relicQuiz = null;
}

// ------------------------------------------------------------------
// 积分与兑换
// ------------------------------------------------------------------
const ICONS = {
  badge: '<svg viewBox="0 0 64 64"><circle cx="32" cy="26" r="16" fill="#1b1f22" stroke="#d9b45b" stroke-width="2"/><path d="M20 26c4-7 20-7 24 0" fill="none" stroke="#8b6a2f" stroke-width="2"/><path d="M24 44l8-6 8 6-2 12-6-5-6 5z" fill="#c9a24a"/></svg>',
  bookmark: '<svg viewBox="0 0 64 64"><path d="M20 8h24v48l-12-9-12 9z" fill="#3b3126" stroke="#d9b45b" stroke-width="2"/><path d="M25 20h14M25 28h14M25 36h9" stroke="#c9a24a" stroke-width="2" stroke-linecap="round"/></svg>',
  lantern: '<svg viewBox="0 0 64 64"><rect x="30" y="4" width="4" height="8" fill="#7a5a2a"/><path d="M32 12c12 0 18 9 18 18s-6 18-18 18-18-9-18-18 6-18 18-18z" fill="#a83a32" stroke="#d9b45b" stroke-width="1.6"/><path d="M32 50v8" stroke="#7a5a2a" stroke-width="3"/><path d="M32 54l-5 6h10z" fill="#c94a3a"/></svg>',
  figure: '<svg viewBox="0 0 64 64"><circle cx="32" cy="16" r="8" fill="#e8d7b4" stroke="#8b6a2f" stroke-width="1.6"/><path d="M18 58c0-12 6-22 14-22s14 10 14 22z" fill="#2a2622" stroke="#d9b45b" stroke-width="1.6"/><path d="M26 40h12" stroke="#c9a24a" stroke-width="2"/></svg>',
};

async function loadPoints(force) {
  try {
    const r = await fetch('/api/points' + (force ? '?t=' + Date.now() : ''), { cache: 'no-store' });
    if (!r.ok) return null;
    const d = await r.json();
    if (d && typeof d.score === 'number') {
      state.points = d;
      const n = $('#scoreNum');
      if (n) n.textContent = d.score;
    }
    return d;
  } catch (e) { return null; }
}

function renderShop() {
  const p = state.points || { score: 0, who: '—', shop: [] };
  const who = $('#shopWho'); if (who) who.textContent = p.who || '—';
  const sc = $('#shopScore'); if (sc) sc.textContent = p.score || 0;
  const grid = $('#shopGrid');
  if (!grid) return;
  grid.innerHTML = (p.shop || []).map((it) => {
    const owned = (p.redeemed || []).filter((x) => x.id === it.id).length;
    const can = (p.score || 0) >= it.cost;
    return '<div class="shop-item' + (can ? '' : ' locked') + '" data-id="' + it.id + '">' +
      '<div class="thumb"><img src="/assets/prizes/' + it.id + '.jpg" alt="' + it.name + '" ' +
        'onerror="this.style.display=\'none\'"></div>' +
      '<span class="nm">' + it.name + '</span>' +
      '<span class="cost">' + it.cost + ' 积分</span>' +
      (owned ? '<span class="owned">已兑换 ' + owned + ' 个</span>' :
        '<button class="btn ' + (can ? 'btn-primary' : 'btn-ghost') + '" type="button" ' +
        (can ? '' : 'disabled ') + 'data-redeem="' + it.id + '">兑换</button>') +
    '</div>';
  }).join('');
  grid.querySelectorAll('[data-redeem]').forEach((b) => {
    b.addEventListener('click', () => redeem(b.dataset.redeem));
  });
}

async function redeem(id) {
  const msg = $('#shopMsg');
  try {
    const r = await fetch('/api/redeem', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id }),
    });
    const d = await r.json();
    if (msg) msg.textContent = d.msg || (d.ok ? '兑换成功' : '积分不够，继续加油');
    if (d.ok) toast('兑换成功，请到工作人员处领取兑换品');
  } catch (e) {
    if (msg) msg.textContent = '兑换失败，请检查网页后端';
  }
  await loadPoints(true);
  renderShop();
}

function addPointsLocal(kind, note) {
  const body = { kind: kind, note: note || '' };
  fetch('/api/add', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((r) => r.json()).then((d) => {
    loadPoints(true);
    if (d && d.score != null) {
      const el = $('#scoreNum');
      if (el) el.textContent = d.score;
    }
  }).catch(() => {});
}

function openShop() {
  loadPoints(true).then(() => {
    renderShop();
    const m = $('#shopModal');
    if (m) m.hidden = false;
  });
}

let camIdx = 0;
function cycleCamera() {
  const presets = ['overview', 'gate', 'hall', 'north'];
  camIdx = (camIdx + 1) % presets.length;
  const name = presets[camIdx];
  if (world && MAP.cameraPresets && MAP.cameraPresets[name]) {
    world.setCameraPreset(MAP.cameraPresets[name]);
    toast('机位：' + name);
  }
}

// ------------------------------------------------------------------
// 启动
// ------------------------------------------------------------------
function startTour() {
  const intro = $('#intro');
  if (intro) { intro.classList.add('hide'); setTimeout(() => intro.setAttribute('hidden', ''), 700); }
  state.started = true;
  if (world) {
    world.placeScholar(stopAt(1), [0, 0, 1]);
    updateStageCamera(1, true);
  }
  renderProgress();
  renderStagePanel(1);
  syncChips();
  setTimeout(() => { speakStage(1); runFaceDetect(); }, 700);
  pushState({ stage: 1, lang: state.lang });
}

async function boot() {
  const loading = $('#loading');
  const setLoad = (t) => { const el = $('#loadingText'); if (el) el.textContent = t; };

  setLoad('读取讲解内容');
  state.content = await loadContent();
  // 地图契约（关卡坐标/行走路径）— 以 02_数据/map.json 为准
  const mapData = await loadJSON('/data/map.json', null).catch(() => null)
    || await loadJSON('./assets/map.json', null).catch(() => null);
  if (mapData && mapData.stages) {
    Object.assign(MAP, mapData);
    console.info('[app] map.json 已应用:', mapData.stages.length, '关');
  }

  setLoad('生成三维场景');
  try {
    world = new World($('#scene'));
  } catch (e) {
    console.error('[app] 三维初始化失败', e);
    setLoad('WebGL 初始化失败：' + e.message);
    return;
  }

  // 轨道控制（简易自实现，避免额外依赖）
  try {
    const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');
    world.orbit = new OrbitControls(world.camera, world.renderer.domElement);
    world.orbit.enableDamping = true;
    world.orbit.dampingFactor = 0.08;
    world.orbit.minDistance = 4;
    world.orbit.maxDistance = 70;
    world.orbit.maxPolarAngle = Math.PI * 0.49;
    world.orbit.target.set(0, 2, 6);
    world.orbit.update();
  } catch (e) {
    console.info('[app] OrbitControls 不可用，用固定机位', e && e.message);
  }

  // 尝试加载 Blender 产出的 GLB
  setLoad('载入 Blender 书院模型');
  const ok = await world.tryLoadGLB(assetUrl('./assets/aotai_academy.glb'));
  if (!ok) {
    console.info('[app] 使用程序化场景演示');
  }

  world.addScholar();
  world.placeScholar(stopAt(1), [0, 0, 1]);
  updateStageCamera(1, true);

  bindUI();
  await connectBackend();

  renderProgress();
  syncChips();
  if (loading) loading.classList.add('hide');
  setTimeout(() => { if (loading) loading.setAttribute('hidden', ''); }, 600);

  // 开场卡片里的五关列表
  const ol = $('#introStages');
  if (ol) {
    ol.innerHTML = [1, 2, 3, 4, 5].map((n) =>
      '<li><b>' + STAGE_ICON[n] + '</b><span>' + STAGE_TITLE[n].zh + '</span></li>').join('');
  }
  // favicon（内联，避免控制台 404）
  try {
    const link = document.createElement('link');
    link.rel = 'icon';
    link.href = 'data:image/svg+xml,' + encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0d1214"/><text x="32" y="44" font-size="34" text-anchor="middle" fill="#d9b45b" font-family="serif">鰲</text></svg>'
    );
    document.head.appendChild(link);
  } catch (e) {}
  // 语音列表预热
  if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
  }
  if (!window._camTick) {
    window._camTick = setInterval(() => {
      const img = document.getElementById('camFeed');
      const tip = document.getElementById('camStatus');
      if (!img) return;
      const probe = new Image();
      const url = '/api/camera.jpg?t=' + Date.now();
      probe.onload = () => {
        img.src = url;
        img.style.display = 'block';
        if (tip) tip.textContent = 'CyberCAM 实时画面';
      };
      probe.onerror = () => {
        if (tip && !img.getAttribute('src')) tip.textContent = '等待摄像头画面';
      };
      probe.src = url;
    }, 450);
  }
  console.info('[app] 就绪');
}

boot();

window.AOTAI = {
  state, gotoStage, nextStage, prevStage, setLang, resetTour,
  get world() { return world; },
  // 测试钩子：模拟相机上报
  __testRelicPass: (k) => relicPassed(k),
  __testRelicRecognized: (k) => relicRecognized(k),
  __testOpenShop: () => openShop(),
};
