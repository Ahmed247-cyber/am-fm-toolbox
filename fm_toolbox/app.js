/* ═══════════════════════════════════════════════════════
   FM Synthesis Toolbox — Audio Engine & Visualizer
   ═══════════════════════════════════════════════════════ */

(() => {
  'use strict';

  // ── Constants ──
  const MIN_FREQ = 20;
  const MAX_FREQ = 4000;
  const FFT_SIZE = 2048;

  // ── Presets ──
  const PRESETS = {
    init: {
      carrierFreq: 440, carrierWave: 'sine',
      modRatio: 1, modIndex: 2, modWave: 'sine',
      ratioMode: true,
      attack: 50, decay: 200, sustain: 70, release: 300
    },
    bell: {
      carrierFreq: 440, carrierWave: 'sine',
      modRatio: 3.5, modIndex: 10, modWave: 'sine',
      ratioMode: true,
      attack: 5, decay: 800, sustain: 0, release: 1500
    },
    epiano: {
      carrierFreq: 440, carrierWave: 'sine',
      modRatio: 1, modIndex: 4, modWave: 'sine',
      ratioMode: true,
      attack: 10, decay: 600, sustain: 30, release: 400
    },
    bass: {
      carrierFreq: 110, carrierWave: 'sine',
      modRatio: 1, modIndex: 6, modWave: 'sine',
      ratioMode: true,
      attack: 10, decay: 300, sustain: 60, release: 200
    },
    brass: {
      carrierFreq: 440, carrierWave: 'sine',
      modRatio: 1, modIndex: 5, modWave: 'sine',
      ratioMode: true,
      attack: 100, decay: 200, sustain: 80, release: 150
    },
    laser: {
      carrierFreq: 880, carrierWave: 'sine',
      modRatio: 0.5, modIndex: 18, modWave: 'sine',
      ratioMode: true,
      attack: 5, decay: 100, sustain: 10, release: 800
    },
    metallic: {
      carrierFreq: 440, carrierWave: 'sine',
      modRatio: 1.41, modIndex: 12, modWave: 'sine',
      ratioMode: true,
      attack: 5, decay: 500, sustain: 10, release: 1000
    },
    organ: {
      carrierFreq: 440, carrierWave: 'sine',
      modRatio: 2, modIndex: 1.5, modWave: 'sine',
      ratioMode: true,
      attack: 30, decay: 50, sustain: 90, release: 80
    },
    pluck: {
      carrierFreq: 440, carrierWave: 'triangle',
      modRatio: 2, modIndex: 8, modWave: 'sine',
      ratioMode: true,
      attack: 3, decay: 400, sustain: 5, release: 500
    }
  };

  // ── State ──
  const state = {
    playing: false,
    carrierFreq: 440,
    carrierWave: 'sine',
    modFreq: 440,
    modRatio: 1,
    modIndex: 2,
    modWave: 'sine',
    ratioMode: true,
    attack: 0.05,
    decay: 0.2,
    sustain: 0.7,
    release: 0.3,
    volume: 0.4,
    activePreset: 'init',
    keyboardDown: false
  };

  // ── DOM Refs ──
  const $ = id => document.getElementById(id);
  const dom = {
    playBtn: $('playBtn'),
    statusDot: $('statusDot'),
    masterVolume: $('masterVolume'),
    masterVolumeVal: $('masterVolumeVal'),
    carrierFreq: $('carrierFreq'),
    carrierFreqVal: $('carrierFreqVal'),
    carrierBadge: $('carrierBadge'),
    carrierWave: $('carrierWave'),
    ratioMode: $('ratioMode'),
    ratioDisplay: $('ratioDisplay'),
    ratioRow: $('ratioRow'),
    freeFreqRow: $('freeFreqRow'),
    ratioSlider: $('ratioSlider'),
    ratioVal: $('ratioVal'),
    modFreq: $('modFreq'),
    modFreqVal: $('modFreqVal'),
    modBadge: $('modBadge'),
    modIndex: $('modIndex'),
    modIndexVal: $('modIndexVal'),
    modWave: $('modWave'),
    attack: $('attack'),
    attackVal: $('attackVal'),
    decay: $('decay'),
    decayVal: $('decayVal'),
    sustain: $('sustain'),
    sustainVal: $('sustainVal'),
    release: $('release'),
    releaseVal: $('releaseVal'),
    waveformCanvas: $('waveformCanvas'),
    spectrumCanvas: $('spectrumCanvas'),
    envelopeCanvas: $('envelopeCanvas'),
    presetsBar: $('presetsBar'),
    fCarrier: $('fCarrier'),
    fMod: $('fMod'),
    fIndex: $('fIndex'),
    sigCarrier: $('sigCarrier'),
    sigMod: $('sigMod'),
    sigIndex: $('sigIndex'),
    sigDeviation: $('sigDeviation'),
    keyboard: $('keyboard')
  };

  // ── Audio Engine ──
  let audioCtx = null;
  let carrier = null;
  let modulator = null;
  let modGain = null;
  let masterGain = null;
  let analyser = null;
  let envelopeGain = null;

  function initAudio() {
    if (audioCtx) return;
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    // Create nodes
    carrier = audioCtx.createOscillator();
    modulator = audioCtx.createOscillator();
    modGain = audioCtx.createGain();
    envelopeGain = audioCtx.createGain();
    masterGain = audioCtx.createGain();
    analyser = audioCtx.createAnalyser();

    analyser.fftSize = FFT_SIZE;
    analyser.smoothingTimeConstant = 0.8;

    // Connections: modulator → modGain → carrier.frequency
    modulator.connect(modGain);
    modGain.connect(carrier.frequency);

    // carrier → envelopeGain → masterGain → analyser → destination
    carrier.connect(envelopeGain);
    envelopeGain.connect(masterGain);
    masterGain.connect(analyser);
    analyser.connect(audioCtx.destination);

    // Set initial values
    carrier.type = state.carrierWave;
    carrier.frequency.setValueAtTime(state.carrierFreq, audioCtx.currentTime);
    modulator.type = state.modWave;
    modulator.frequency.setValueAtTime(state.modFreq, audioCtx.currentTime);
    modGain.gain.setValueAtTime(state.modIndex * state.modFreq, audioCtx.currentTime);
    masterGain.gain.setValueAtTime(state.volume, audioCtx.currentTime);
    envelopeGain.gain.setValueAtTime(0, audioCtx.currentTime);

    // Start oscillators (they run continuously; we gate with envelopeGain)
    carrier.start();
    modulator.start();
  }

  function triggerEnvelope() {
    if (!audioCtx || !envelopeGain) return;
    const now = audioCtx.currentTime;
    const g = envelopeGain.gain;
    g.cancelScheduledValues(now);
    g.setValueAtTime(0, now);
    g.linearRampToValueAtTime(1, now + state.attack);
    g.linearRampToValueAtTime(state.sustain, now + state.attack + state.decay);
  }

  function releaseEnvelope() {
    if (!audioCtx || !envelopeGain) return;
    const now = audioCtx.currentTime;
    const g = envelopeGain.gain;
    g.cancelScheduledValues(now);
    g.setValueAtTime(g.value, now);
    g.linearRampToValueAtTime(0, now + state.release);
  }

  function updateAudioParams() {
    if (!audioCtx) return;
    const now = audioCtx.currentTime;

    carrier.type = state.carrierWave;
    carrier.frequency.setTargetAtTime(state.carrierFreq, now, 0.01);

    modulator.type = state.modWave;
    modulator.frequency.setTargetAtTime(state.modFreq, now, 0.01);

    // modGain = modIndex × modFreq (frequency deviation)
    modGain.gain.setTargetAtTime(state.modIndex * state.modFreq, now, 0.01);

    masterGain.gain.setTargetAtTime(state.volume, now, 0.01);
  }

  // ── Freq Mapping (logarithmic) ──
  function sliderToFreq(val, min = MIN_FREQ, max = MAX_FREQ) {
    return min * Math.pow(max / min, val / 100);
  }

  function freqToSlider(freq, min = MIN_FREQ, max = MAX_FREQ) {
    return 100 * Math.log(freq / min) / Math.log(max / min);
  }

  // ── Ratio Mapping ──
  // Slider 0–100 maps to ratio 0.25–16 (logarithmic)
  function sliderToRatio(val) {
    return 0.25 * Math.pow(64, val / 100);
  }

  function ratioToSlider(ratio) {
    return 100 * Math.log(ratio / 0.25) / Math.log(64);
  }

  // ── UI Updates ──
  function updateCarrierUI() {
    const freq = state.carrierFreq;
    dom.carrierFreqVal.textContent = freq < 100 ? freq.toFixed(1) + ' Hz' : Math.round(freq) + ' Hz';
    dom.carrierBadge.textContent = Math.round(freq) + ' Hz';
    dom.carrierFreq.value = freqToSlider(freq);
  }

  function updateModUI() {
    const mf = state.modFreq;
    dom.modBadge.textContent = mf < 100 ? mf.toFixed(1) + ' Hz' : Math.round(mf) + ' Hz';

    if (state.ratioMode) {
      dom.ratioVal.textContent = state.modRatio.toFixed(2);
      dom.ratioSlider.value = ratioToSlider(state.modRatio);
      // Update ratio display
      dom.ratioDisplay.innerHTML = `C : M = <span class="rc">1</span> : <span class="rm">${state.modRatio.toFixed(2)}</span>`;
    } else {
      dom.modFreqVal.textContent = mf < 100 ? mf.toFixed(1) + ' Hz' : Math.round(mf) + ' Hz';
      dom.modFreq.value = freqToSlider(mf);
      dom.ratioDisplay.innerHTML = `C : M = <span class="rc">1</span> : <span class="rm">${(mf / state.carrierFreq).toFixed(2)}</span>`;
    }

    dom.modIndexVal.textContent = state.modIndex.toFixed(2);

    // Formula
    dom.fCarrier.textContent = Math.round(state.carrierFreq);
    dom.fMod.textContent = Math.round(state.modFreq);
    dom.fIndex.textContent = state.modIndex.toFixed(2);

    // Signal info
    dom.sigCarrier.textContent = `${state.carrierFreq.toFixed(1)} Hz (${capitalize(state.carrierWave)})`;
    dom.sigMod.textContent = `${state.modFreq.toFixed(1)} Hz (${capitalize(state.modWave)})`;
    dom.sigIndex.textContent = state.modIndex.toFixed(2);
    dom.sigDeviation.textContent = `${(state.modIndex * state.modFreq).toFixed(0)} Hz`;
  }

  function updateEnvelopeUI() {
    dom.attackVal.textContent = state.attack.toFixed(2) + 's';
    dom.decayVal.textContent = state.decay.toFixed(2) + 's';
    dom.sustainVal.textContent = state.sustain.toFixed(2);
    dom.releaseVal.textContent = state.release.toFixed(2) + 's';
    drawEnvelope();
  }

  function updateAllUI() {
    updateCarrierUI();
    updateModUI();
    updateEnvelopeUI();
    dom.masterVolumeVal.textContent = Math.round(state.volume * 100) + '%';
    dom.masterVolume.value = Math.round(state.volume * 100);
    dom.carrierWave.value = state.carrierWave;
    dom.modWave.value = state.modWave;
    dom.modIndex.value = Math.round(state.modIndex * 10);

    // Ratio mode
    dom.ratioMode.checked = state.ratioMode;
    dom.ratioRow.style.display = state.ratioMode ? '' : 'none';
    dom.freeFreqRow.style.display = state.ratioMode ? 'none' : '';

    // ADSR sliders
    dom.attack.value = Math.round(state.attack * 1000);
    dom.decay.value = Math.round(state.decay * 1000);
    dom.sustain.value = Math.round(state.sustain * 100);
    dom.release.value = Math.round(state.release * 1000);
  }

  function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  // ── Play / Stop ──
  function togglePlay() {
    if (!state.playing) {
      startPlaying();
    } else {
      stopPlaying();
    }
  }

  function startPlaying() {
    initAudio();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    updateAudioParams();
    triggerEnvelope();
    state.playing = true;
    dom.playBtn.textContent = '⏸';
    dom.playBtn.classList.add('active');
    dom.statusDot.classList.add('active');
  }

  function stopPlaying() {
    releaseEnvelope();
    state.playing = false;
    dom.playBtn.textContent = '▶';
    dom.playBtn.classList.remove('active');
    // Keep statusDot active briefly for release tail
    setTimeout(() => {
      if (!state.playing) dom.statusDot.classList.remove('active');
    }, state.release * 1000 + 100);
  }

  // ── Keyboard Note Play ──
  function playNote(freq) {
    state.carrierFreq = freq;
    if (state.ratioMode) {
      state.modFreq = freq * state.modRatio;
    }
    updateCarrierUI();
    updateModUI();

    initAudio();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    updateAudioParams();
    triggerEnvelope();
    state.playing = true;
    state.keyboardDown = true;
    dom.playBtn.textContent = '⏸';
    dom.playBtn.classList.add('active');
    dom.statusDot.classList.add('active');
  }

  function releaseNote() {
    if (!state.keyboardDown) return;
    state.keyboardDown = false;
    stopPlaying();
  }

  // ── Event Handlers ──

  // Play button
  dom.playBtn.addEventListener('click', togglePlay);

  // Spacebar
  document.addEventListener('keydown', e => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT') {
      e.preventDefault();
      togglePlay();
    }
  });

  // Master volume
  dom.masterVolume.addEventListener('input', () => {
    state.volume = dom.masterVolume.value / 100;
    dom.masterVolumeVal.textContent = Math.round(state.volume * 100) + '%';
    updateAudioParams();
  });

  // Carrier frequency
  dom.carrierFreq.addEventListener('input', () => {
    state.carrierFreq = sliderToFreq(parseFloat(dom.carrierFreq.value));
    if (state.ratioMode) {
      state.modFreq = state.carrierFreq * state.modRatio;
    }
    updateCarrierUI();
    updateModUI();
    updateAudioParams();
    clearActivePreset();
  });

  // Carrier waveform
  dom.carrierWave.addEventListener('change', () => {
    state.carrierWave = dom.carrierWave.value;
    updateModUI(); // updates signal info
    updateAudioParams();
    clearActivePreset();
  });

  // Ratio mode toggle
  dom.ratioMode.addEventListener('change', () => {
    state.ratioMode = dom.ratioMode.checked;
    dom.ratioRow.style.display = state.ratioMode ? '' : 'none';
    dom.freeFreqRow.style.display = state.ratioMode ? 'none' : '';
    if (state.ratioMode) {
      state.modRatio = state.modFreq / state.carrierFreq;
    }
    updateModUI();
    clearActivePreset();
  });

  // Ratio slider
  dom.ratioSlider.addEventListener('input', () => {
    state.modRatio = sliderToRatio(parseFloat(dom.ratioSlider.value));
    state.modFreq = state.carrierFreq * state.modRatio;
    updateModUI();
    updateAudioParams();
    clearActivePreset();
  });

  // Free mod freq slider
  dom.modFreq.addEventListener('input', () => {
    state.modFreq = sliderToFreq(parseFloat(dom.modFreq.value));
    updateModUI();
    updateAudioParams();
    clearActivePreset();
  });

  // Mod index
  dom.modIndex.addEventListener('input', () => {
    state.modIndex = dom.modIndex.value / 10;
    updateModUI();
    updateAudioParams();
    clearActivePreset();
  });

  // Mod waveform
  dom.modWave.addEventListener('change', () => {
    state.modWave = dom.modWave.value;
    updateModUI();
    updateAudioParams();
    clearActivePreset();
  });

  // ADSR
  dom.attack.addEventListener('input', () => {
    state.attack = dom.attack.value / 1000;
    updateEnvelopeUI();
    clearActivePreset();
  });
  dom.decay.addEventListener('input', () => {
    state.decay = dom.decay.value / 1000;
    updateEnvelopeUI();
    clearActivePreset();
  });
  dom.sustain.addEventListener('input', () => {
    state.sustain = dom.sustain.value / 100;
    updateEnvelopeUI();
    clearActivePreset();
  });
  dom.release.addEventListener('input', () => {
    state.release = dom.release.value / 1000;
    updateEnvelopeUI();
    clearActivePreset();
  });

  // Presets
  dom.presetsBar.addEventListener('click', e => {
    const btn = e.target.closest('.preset-btn');
    if (!btn) return;
    const name = btn.dataset.preset;
    if (!PRESETS[name]) return;
    applyPreset(name);
  });

  function applyPreset(name) {
    const p = PRESETS[name];
    state.carrierFreq = p.carrierFreq;
    state.carrierWave = p.carrierWave;
    state.modRatio = p.modRatio;
    state.modIndex = p.modIndex;
    state.modWave = p.modWave;
    state.ratioMode = p.ratioMode;
    state.modFreq = state.ratioMode ? state.carrierFreq * state.modRatio : p.modFreq || state.carrierFreq;
    state.attack = p.attack / 1000;
    state.decay = p.decay / 1000;
    state.sustain = p.sustain / 100;
    state.release = p.release / 1000;
    state.activePreset = name;

    updateAllUI();
    updateAudioParams();

    // If playing, retrigger envelope
    if (state.playing) triggerEnvelope();

    // Highlight preset button
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    const activeBtn = document.querySelector(`.preset-btn[data-preset="${name}"]`);
    if (activeBtn) activeBtn.classList.add('active');
  }

  function clearActivePreset() {
    state.activePreset = null;
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  }

  // ── Keyboard (mouse) ──
  const keys = dom.keyboard.querySelectorAll('.key');
  keys.forEach(key => {
    key.addEventListener('mousedown', e => {
      e.preventDefault();
      const freq = parseFloat(key.dataset.freq);
      key.classList.add('active');
      playNote(freq);
    });
    key.addEventListener('mouseup', () => {
      key.classList.remove('active');
      releaseNote();
    });
    key.addEventListener('mouseleave', () => {
      if (key.classList.contains('active')) {
        key.classList.remove('active');
        releaseNote();
      }
    });

    // Touch
    key.addEventListener('touchstart', e => {
      e.preventDefault();
      const freq = parseFloat(key.dataset.freq);
      key.classList.add('active');
      playNote(freq);
    });
    key.addEventListener('touchend', e => {
      e.preventDefault();
      key.classList.remove('active');
      releaseNote();
    });
  });

  // ── Keyboard (computer keyboard) ──
  const keyMap = {
    'KeyA': 'C4', 'KeyW': 'C#4', 'KeyS': 'D4', 'KeyE': 'D#4',
    'KeyD': 'E4', 'KeyF': 'F4', 'KeyT': 'F#4', 'KeyG': 'G4',
    'KeyY': 'G#4', 'KeyH': 'A4', 'KeyU': 'A#4', 'KeyJ': 'B4',
    'KeyK': 'C5'
  };
  const activeKeys = new Set();

  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.repeat) return;
    const note = keyMap[e.code];
    if (!note) return;
    e.preventDefault();
    activeKeys.add(e.code);
    const keyEl = dom.keyboard.querySelector(`[data-note="${note}"]`);
    if (keyEl) {
      keyEl.classList.add('active');
      playNote(parseFloat(keyEl.dataset.freq));
    }
  });

  document.addEventListener('keyup', e => {
    const note = keyMap[e.code];
    if (!note) return;
    activeKeys.delete(e.code);
    const keyEl = dom.keyboard.querySelector(`[data-note="${note}"]`);
    if (keyEl) keyEl.classList.remove('active');
    if (activeKeys.size === 0) releaseNote();
  });


  // ══════════════════════════════════════════
  // ── Visualizer ──
  // ══════════════════════════════════════════

  class Visualizer {
    constructor() {
      this.waveCanvas = dom.waveformCanvas;
      this.specCanvas = dom.spectrumCanvas;
      this.envCanvas = dom.envelopeCanvas;
      this.wCtx = this.waveCanvas.getContext('2d');
      this.sCtx = this.specCanvas.getContext('2d');
      this.animId = null;
      this.resize();
      window.addEventListener('resize', () => this.resize());
    }

    resize() {
      const dpr = window.devicePixelRatio || 1;
      [this.waveCanvas, this.specCanvas].forEach(c => {
        const rect = c.getBoundingClientRect();
        c.width = rect.width * dpr;
        c.height = rect.height * dpr;
        c.getContext('2d').scale(dpr, dpr);
      });
      this.resizeEnvelope();
    }

    resizeEnvelope() {
      const c = this.envCanvas;
      const dpr = window.devicePixelRatio || 1;
      const rect = c.getBoundingClientRect();
      c.width = rect.width * dpr;
      c.height = rect.height * dpr;
      c.getContext('2d').scale(dpr, dpr);
      drawEnvelope();
    }

    start() {
      const draw = () => {
        this.animId = requestAnimationFrame(draw);
        this.drawWaveform();
        this.drawSpectrum();
      };
      draw();
    }

    drawWaveform() {
      const ctx = this.wCtx;
      const w = this.waveCanvas.getBoundingClientRect().width;
      const h = this.waveCanvas.getBoundingClientRect().height;
      const pad = 8;

      ctx.clearRect(0, 0, w, h);

      // Background grid
      ctx.strokeStyle = 'rgba(60, 60, 120, 0.12)';
      ctx.lineWidth = 1;
      const gridLines = 8;
      for (let i = 0; i <= gridLines; i++) {
        const y = pad + (h - 2 * pad) * i / gridLines;
        ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(w - pad, y); ctx.stroke();
      }
      for (let i = 0; i <= 16; i++) {
        const x = pad + (w - 2 * pad) * i / 16;
        ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, h - pad); ctx.stroke();
      }

      // Center line
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.15)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad, h / 2);
      ctx.lineTo(w - pad, h / 2);
      ctx.stroke();

      if (!analyser) {
        // Idle sine wave animation
        this.drawIdleWave(ctx, w, h, pad);
        return;
      }

      const bufLen = analyser.fftSize;
      const data = new Float32Array(bufLen);
      analyser.getFloatTimeDomainData(data);

      // Trigger: find zero crossing
      let trigger = 0;
      for (let i = 1; i < bufLen / 2; i++) {
        if (data[i - 1] < 0 && data[i] >= 0) {
          trigger = i;
          break;
        }
      }

      const drawLen = Math.min(bufLen - trigger, Math.floor(bufLen * 0.6));
      const drawW = w - 2 * pad;
      const drawH = h - 2 * pad;

      // Glow pass
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.2)';
      ctx.lineWidth = 6;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      for (let i = 0; i < drawLen; i++) {
        const x = pad + (i / drawLen) * drawW;
        const y = h / 2 - data[trigger + i] * drawH * 0.45;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Main line
      ctx.beginPath();
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 2;
      for (let i = 0; i < drawLen; i++) {
        const x = pad + (i / drawLen) * drawW;
        const y = h / 2 - data[trigger + i] * drawH * 0.45;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    drawIdleWave(ctx, w, h, pad) {
      const t = Date.now() / 1000;
      const drawW = w - 2 * pad;
      const points = 200;

      // Glow
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.1)';
      ctx.lineWidth = 5;
      for (let i = 0; i <= points; i++) {
        const x = pad + (i / points) * drawW;
        const y = h / 2 + Math.sin((i / points) * Math.PI * 6 + t * 2) * 20 * Math.sin(t * 0.5);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Line
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.35)';
      ctx.lineWidth = 1.5;
      for (let i = 0; i <= points; i++) {
        const x = pad + (i / points) * drawW;
        const y = h / 2 + Math.sin((i / points) * Math.PI * 6 + t * 2) * 20 * Math.sin(t * 0.5);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    drawSpectrum() {
      const ctx = this.sCtx;
      const w = this.specCanvas.getBoundingClientRect().width;
      const h = this.specCanvas.getBoundingClientRect().height;
      const pad = 8;

      ctx.clearRect(0, 0, w, h);

      // Background grid
      ctx.strokeStyle = 'rgba(60, 60, 120, 0.12)';
      ctx.lineWidth = 1;
      for (let i = 0; i <= 8; i++) {
        const y = pad + (h - 2 * pad) * i / 8;
        ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(w - pad, y); ctx.stroke();
      }

      if (!analyser) {
        // Idle bars
        this.drawIdleSpectrum(ctx, w, h, pad);
        return;
      }

      const bufLen = analyser.frequencyBinCount;
      const data = new Uint8Array(bufLen);
      analyser.getByteFrequencyData(data);

      const drawW = w - 2 * pad;
      const drawH = h - 2 * pad;

      // Use logarithmic frequency scale
      const numBars = 128;
      const barW = drawW / numBars - 1;
      const nyquist = audioCtx.sampleRate / 2;

      for (let i = 0; i < numBars; i++) {
        // Map bar index to frequency (log scale)
        const fMin = 20;
        const fMax = Math.min(nyquist, 10000);
        const f = fMin * Math.pow(fMax / fMin, i / numBars);
        const binIdx = Math.round(f / nyquist * bufLen);
        if (binIdx >= bufLen) continue;

        const val = data[binIdx] / 255;
        const barH = val * drawH;
        const x = pad + (i / numBars) * drawW;
        const y = h - pad - barH;

        // Gradient bar
        const grad = ctx.createLinearGradient(x, y, x, h - pad);
        grad.addColorStop(0, `rgba(255, 42, 170, ${0.6 + val * 0.4})`);
        grad.addColorStop(0.5, `rgba(136, 51, 255, ${0.5 + val * 0.3})`);
        grad.addColorStop(1, `rgba(0, 229, 255, ${0.3 + val * 0.2})`);

        ctx.fillStyle = grad;
        ctx.fillRect(x, y, Math.max(barW, 2), barH);

        // Top glow
        if (val > 0.3) {
          ctx.fillStyle = `rgba(255, 42, 170, ${val * 0.3})`;
          ctx.fillRect(x - 1, y - 2, Math.max(barW, 2) + 2, 4);
        }
      }

      // Frequency labels
      ctx.fillStyle = 'rgba(133, 133, 184, 0.5)';
      ctx.font = '9px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      [100, 500, 1000, 2000, 5000].forEach(f => {
        const x = pad + (Math.log(f / 20) / Math.log(10000 / 20)) * drawW;
        if (x > pad && x < w - pad) {
          ctx.fillText(f >= 1000 ? (f / 1000) + 'k' : f + '', x, h - 1);
        }
      });
    }

    drawIdleSpectrum(ctx, w, h, pad) {
      const t = Date.now() / 1000;
      const numBars = 64;
      const drawW = w - 2 * pad;
      const drawH = h - 2 * pad;
      const barW = drawW / numBars - 1;

      for (let i = 0; i < numBars; i++) {
        const val = (Math.sin(i * 0.3 + t) * 0.5 + 0.5) * 0.15;
        const barH = val * drawH;
        const x = pad + (i / numBars) * drawW;
        const y = h - pad - barH;

        ctx.fillStyle = `rgba(136, 51, 255, ${0.15 + val})`;
        ctx.fillRect(x, y, Math.max(barW, 2), barH);
      }
    }
  }

  // ── Envelope Canvas ──
  function drawEnvelope() {
    const canvas = dom.envelopeCanvas;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.getBoundingClientRect().width;
    const h = canvas.getBoundingClientRect().height;

    ctx.clearRect(0, 0, w, h);

    const pad = 12;
    const drawW = w - 2 * pad;
    const drawH = h - 2 * pad;

    // Normalize times
    const totalTime = state.attack + state.decay + 0.3 + state.release; // 0.3s hold
    const aX = pad + (state.attack / totalTime) * drawW;
    const dX = aX + (state.decay / totalTime) * drawW;
    const sX = dX + (0.3 / totalTime) * drawW;
    const rX = sX + (state.release / totalTime) * drawW;

    const topY = pad;
    const bottomY = h - pad;
    const sustainY = topY + (1 - state.sustain) * drawH;

    // Filled area
    ctx.beginPath();
    ctx.moveTo(pad, bottomY);
    ctx.lineTo(aX, topY);
    ctx.lineTo(dX, sustainY);
    ctx.lineTo(sX, sustainY);
    ctx.lineTo(rX, bottomY);
    ctx.closePath();

    const grad = ctx.createLinearGradient(0, topY, 0, bottomY);
    grad.addColorStop(0, 'rgba(0, 255, 148, 0.15)');
    grad.addColorStop(1, 'rgba(0, 255, 148, 0.02)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Glow line
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(0, 255, 148, 0.25)';
    ctx.lineWidth = 4;
    ctx.lineJoin = 'round';
    ctx.moveTo(pad, bottomY);
    ctx.lineTo(aX, topY);
    ctx.lineTo(dX, sustainY);
    ctx.lineTo(sX, sustainY);
    ctx.lineTo(rX, bottomY);
    ctx.stroke();

    // Main line
    ctx.beginPath();
    ctx.strokeStyle = '#00ff94';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.moveTo(pad, bottomY);
    ctx.lineTo(aX, topY);
    ctx.lineTo(dX, sustainY);
    ctx.lineTo(sX, sustainY);
    ctx.lineTo(rX, bottomY);
    ctx.stroke();

    // Labels
    ctx.fillStyle = 'rgba(0, 255, 148, 0.5)';
    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('A', (pad + aX) / 2, bottomY + 1);
    ctx.fillText('D', (aX + dX) / 2, bottomY + 1);
    ctx.fillText('S', (dX + sX) / 2, bottomY + 1);
    ctx.fillText('R', (sX + rX) / 2, bottomY + 1);

    // Dots at vertices
    [[aX, topY], [dX, sustainY], [sX, sustainY], [rX, bottomY]].forEach(([x, y]) => {
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = '#00ff94';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(0, 255, 148, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }


  // ── Initialize ──
  function init() {
    updateAllUI();

    const viz = new Visualizer();
    viz.start();

    // Initial envelope draw (after canvas is sized)
    requestAnimationFrame(() => {
      viz.resize();
      drawEnvelope();
    });
  }

  // Wait for DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
