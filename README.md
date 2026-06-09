# 📡 Amplitude Modulation (AM) Toolbox in Python

A high-fidelity, interactive Amplitude Modulation (AM) simulation lab and software toolbox written in Python. This toolkit includes a mathematical core for signal generation, multiple AM modulation/demodulation schemes, channel noise simulation, spectral analysis, a CLI, and a feature-rich Streamlit web dashboard.

---

## 🚀 Features

- **Mathematical DSP Core (`am_toolbox/core.py`)**:
  - **Signal Synthesis**: Generates sines, square waves, triangle waves, sawtooths, and frequency sweeps.
  - **Modulation Schemes**:
    - *DSB-LC (Double Sideband Large Carrier)*: Conventional AM with carrier component and adjustable modulation index ($m$).
    - *DSB-SC (Double Sideband Suppressed Carrier)*: Suppresses the carrier to save transmission power.
    - *SSB (Single Sideband Suppressed Carrier)*: Suppresses both carrier and one sideband (USB or LSB) to save power and bandwidth. Implemented using the **Hilbert Transform**.
  - **Demodulation Methods**:
    - *Coherent / Synchronous Demodulator*: Multiplying by a local carrier with phase offset and low-pass filtering. Allows analyzing the quadrature null effect.
    - *Envelope Detector*: Hilbert-transform based analytical envelope and physical diode-capacitor discharge filter emulation.
  - **Metrics & Analysis**: FFT spectra, transmitted power, sideband power efficiency, alignment-based Mean Squared Error (MSE), and Signal-to-Distortion Ratio (SDR).
- **Interactive Dashboard (`am_toolbox/app.py`)**:
  - Live parameter sweeping for carrier, message wave, channel noise (AWGN SNR), and receiver settings.
  - Multi-panel Plotly interactive charts showing aligned time-domain signals, zoomed-in carrier oscillations, and double-sided frequency spectra.
  - **Audio Lab**: Upload a WAV audio file, modulate it, listen to the high-frequency modulated sound, demodulate it, and listen to/download the recovered audio.
  - Mathematical reference notes rendered with LaTeX formulas.
- **Command Line Interface (`am_toolbox/cli.py`)**:
  - Modulate, demodulate, and analyze WAV files or synthesized signals from the command line.
  - Generate and save analysis reports as publication-quality static plots.

---

## 📦 Installation & Setup

1. **Prerequisites**: Python 3.8+ (Tested on Python 3.13)
2. **Create virtual environment** (if not already created):
   ```bash
   python -m venv venv
   ```
3. **Activate the environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   - **Linux / macOS**:
     ```bash
     source venv/bin/activate
     ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🏃 Usage (Master Runner)

The package includes a unified `run.py` script. You can run all actions through it:

### 1. Launch the Interactive Web Dashboard
```bash
python run.py app
```

### 2. Run the Unit Test Suite
```bash
python run.py test
```

### 3. Run the CLI Simulator & Report Generator
Simulate a complete modulation-demodulation chain with noise and export an analysis plot:
```bash
python run.py analyze --type dsb-lc --fc 3000 --snr 20 --plot my_analysis.png
```
This command generates an `am_analysis.png` dashboard highlighting time and frequency domain comparisons.

### 4. Modulate a WAV File (CLI)
```bash
python run.py modulate --input input_voice.wav --output modulated_carrier.wav --type ssb-usb --fc 8000
```

### 5. Demodulate a WAV File (CLI)
```bash
python run.py demodulate --input modulated_carrier.wav --output recovered_voice.wav --type coherent --fc 8000 --phase 0.0
```

---

## 📖 Mathematical Reference

### Modulation Schemes
- **DSB-LC (Conventional AM)**:
  $$s(t) = A_c [1 + m \cdot m_n(t)] \cos(2\pi f_c t)$$
  *   $m < 1$: Under-modulated. Envelope matches message.
  *   $m > 1$: Over-modulated. Phase reversals occur; envelope detector output will distort.
  *   Sideband Efficiency: $\eta = \frac{m^2 P_{m_n}}{1 + m^2 P_{m_n}}$ (Max $33.3\%$ for a sine wave).
- **DSB-SC**:
  $$s(t) = m(t) \cos(2\pi f_c t)$$
  *   Carrier is suppressed ($100\%$ efficiency).
  *   Requires coherent demodulation.
- **SSB-SC**:
  $$s(t) = m(t)\cos(2\pi f_c t) \mp \hat{m}(t)\sin(2\pi f_c t)$$
  *   $\hat{m}(t)$ is the Hilbert transform of $m(t)$.
  *   $-$ selects Upper Sideband (USB); $+$ selects Lower Sideband (LSB).

### Demodulation
- **Coherent Receiver**:
  Multiplies incoming $s(t)$ by local oscillator $c_{local}(t) = \cos(2\pi f_c t + \theta)$ and passes through a low-pass filter (LPF).
  $$y(t) = \text{LPF}\{s(t) \cos(2\pi f_c t + \theta)\} = \frac{1}{2} m(t) \cos(\theta)$$
  *   If $\theta = 0^\circ$ (synchronized): recovered signal is maximum.
  *   If $\theta = 90^\circ$ (quadrature error): recovered signal is zero (quadrature null effect).
- **Envelope Detector**:
  Computes the magnitude of the analytic signal:
  $$a(t) = |s(t) + j \hat{s}(t)|$$
  For conventional AM, subtracting the DC offset ($A_c$) recovers the message.
