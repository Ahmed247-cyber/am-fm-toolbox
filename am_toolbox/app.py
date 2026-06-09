import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import soundfile as sf
import io
import os

try:
    from . import core
except ImportError:
    import core

st.set_page_config(
    page_title="AM Toolbox & Interactive Lab",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium UI styling with custom CSS
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .stMetric {
        background-color: #1f2937;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-title {
        font-size: 0.9rem;
        color: #9ca3af;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #60a5fa;
    }
    .stAlert {
        border-radius: 8px;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }
    .sidebar .sidebar-content {
        background-color: #111827;
    }
</style>
""", unsafe_allow_html=True)

st.title("📡 Amplitude Modulation (AM) Lab & Playground")
st.markdown("An interactive simulation laboratory to analyze, modulate, demodulate, and visualize AM signals in both time and frequency domains.")

# Sidebar Settings
st.sidebar.header("🛠️ System Configuration")

# 1. Modulation Scheme
st.sidebar.subheader("1. Modulation Scheme")
mod_scheme = st.sidebar.selectbox(
    "Select Modulation Type",
    options=["dsb-lc", "dsb-sc", "ssb-usb", "ssb-lsb"],
    format_func=lambda x: {
        "dsb-lc": "Conventional AM (DSB-LC)",
        "dsb-sc": "Double Sideband Suppressed Carrier (DSB-SC)",
        "ssb-usb": "Single Sideband - Upper (SSB-USB)",
        "ssb-lsb": "Single Sideband - Lower (SSB-LSB)"
    }[x]
)

# 2. Modulating Signal (Message)
st.sidebar.subheader("2. Modulating Signal (Message)")
message_source = st.sidebar.radio("Message Source", options=["Synthesized Wave", "Audio File Upload"])

uploaded_file = None
if message_source == "Audio File Upload":
    uploaded_file = st.sidebar.file_uploader("Upload a WAV Audio file (Mono recommended)", type=["wav"])
    if uploaded_file is not None:
        # Load audio using soundfile
        audio_bytes = uploaded_file.read()
        audio_stream = io.BytesIO(audio_bytes)
        raw_audio, fs_audio = sf.read(audio_stream)
        if len(raw_audio.shape) > 1:
            raw_audio = np.mean(raw_audio, axis=1) # to mono
        
        # Audio length controls
        total_audio_dur = len(raw_audio) / fs_audio
        st.sidebar.info(f"Loaded: {uploaded_file.name} | fs={fs_audio} Hz | Duration={total_audio_dur:.2f}s")
        audio_dur_to_process = st.sidebar.slider("Duration to process (s)", 0.1, min(total_audio_dur, 5.0), min(total_audio_dur, 2.0), step=0.1)
        # Extract segment
        num_samples = int(audio_dur_to_process * fs_audio)
        message = raw_audio[:num_samples]
        fs = fs_audio
    else:
        st.sidebar.warning("Please upload a WAV file. Falling back to Synthesized Wave.")
        message_source = "Synthesized Wave"

if message_source == "Synthesized Wave":
    wave_type = st.sidebar.selectbox("Wave Type", options=["sine", "square", "triangle", "sawtooth", "sweep"])
    fm = st.sidebar.slider("Message Frequency (fm) [Hz]", 10, 2000, 200, step=10)
    Am = st.sidebar.slider("Message Amplitude (Am)", 0.1, 5.0, 1.0, step=0.1)
    fs = st.sidebar.slider("Sampling Frequency (fs) [Hz]", 10000, 100000, 44100, step=1000)
    duration = st.sidebar.slider("Duration [seconds]", 0.01, 1.0, 0.1, step=0.01)
    
    t, message = core.generate_wave(wave_type, fm, fs, duration, Am)

# 3. Carrier Configuration
st.sidebar.subheader("3. Carrier Configuration")
# Ensure carrier freq is higher than modulating frequency
min_fc = int(100 if message_source == "Audio File Upload" else fm * 2)
fc = st.sidebar.slider("Carrier Frequency (fc) [Hz]", min_fc, int(fs/2.1), min(int(fs/4), 5000), step=100)
Ac = st.sidebar.slider("Carrier Amplitude (Ac)", 0.1, 5.0, 1.0, step=0.1)

# Modulation Index for Conventional AM
m = 1.0
if mod_scheme == "dsb-lc":
    m = st.sidebar.slider("Modulation Index (m)", 0.0, 2.0, 0.8, step=0.05)

# 4. Channel Noise (AWGN)
st.sidebar.subheader("4. Channel Model (AWGN)")
noise_enabled = st.sidebar.checkbox("Enable Channel Noise", value=False)
snr_db = st.sidebar.slider("Channel SNR (dB)", 0, 50, 20, step=1) if noise_enabled else None

# 5. Receiver Configuration
st.sidebar.subheader("5. Receiver Configuration")
if mod_scheme == "dsb-lc":
    demod_method = st.sidebar.selectbox("Demodulation Method", options=["envelope", "coherent"])
else:
    demod_method = st.sidebar.selectbox("Demodulation Method", options=["coherent", "envelope"], index=0)
    if demod_method == "envelope":
        st.sidebar.warning("Envelope detection will fail/distort for suppressed-carrier signals!")

phase_error = 0.0
envelope_method = "hilbert"

if demod_method == "coherent":
    phase_error = st.sidebar.slider("Local Carrier Phase Error (deg)", -180.0, 180.0, 0.0, step=5.0)
else:
    envelope_method = st.sidebar.selectbox("Envelope Extraction Method", options=["hilbert", "diode"])

cutoff_override = st.sidebar.checkbox("Override Filter Cutoff", value=False)
cutoff_freq = None
if cutoff_override:
    cutoff_freq = st.sidebar.slider("Lowpass Filter Cutoff (Hz)", 50, int(fs/2.1), int(fc * 0.8))

# ----------------- Core DSP Processing -----------------
# 1. Modulate
if mod_scheme == "dsb-lc":
    modulated, carrier, t = core.modulate_dsb_lc(message, fc, fs, m, Ac)
elif mod_scheme == "dsb-sc":
    modulated, carrier, t = core.modulate_dsb_sc(message, fc, fs, Ac)
else:
    sb = 'upper' if 'usb' in mod_scheme else 'lower'
    modulated, carrier, t = core.modulate_ssb(message, fc, fs, sb, Ac)

raw_modulated = modulated.copy() # Save noiseless version for plotting

# 2. Channel noise
noise = np.zeros_like(modulated)
if noise_enabled:
    modulated, noise = core.add_awgn(modulated, snr_db)

# 3. Demodulate
if demod_method == "coherent":
    demodulated = core.demodulate_coherent(modulated, fc, fs, phase_error, cutoff_freq)
else:
    demodulated = core.demodulate_envelope(modulated, fs, envelope_method, cutoff_freq)
    # Conventional AM envelope has DC offset (carrier amplitude), subtract it
    if mod_scheme == "dsb-lc":
        demodulated = demodulated - np.mean(demodulated)

# 4. Compute metrics
metrics = core.compute_metrics(message, demodulated, modulated, carrier, m if mod_scheme == "dsb-lc" else None, mod_scheme)

# ----------------- Main View Layout -----------------
tab1, tab2, tab3 = st.tabs(["📊 Lab Dashboard", "🎵 Audio Lab", "📖 Mathematical Theory"])

with tab1:
    # --- Metrics Section ---
    m_cols = st.columns(4)
    with m_cols[0]:
        st.markdown(f"""
        <div class="stMetric">
            <div class="metric-title">Modulation Scheme</div>
            <div class="metric-value" style="font-size:1.4rem;">{mod_scheme.upper()}</div>
            <div style="font-size:0.8rem; color:#10b981;">{metrics.get('modulation_status', '')}</div>
        </div>
        """, unsafe_allow_html=True)
    with m_cols[1]:
        eff_val = f"{metrics.get('efficiency', 0.0):.2f}%" if 'efficiency' in metrics else "N/A"
        st.markdown(f"""
        <div class="stMetric">
            <div class="metric-title">Sideband Power Efficiency</div>
            <div class="metric-value">{eff_val}</div>
            <div style="font-size:0.8rem; color:#9ca3af;">P_sidebands / P_total</div>
        </div>
        """, unsafe_allow_html=True)
    with m_cols[2]:
        st.markdown(f"""
        <div class="stMetric">
            <div class="metric-title">Total Transmitted Power</div>
            <div class="metric-value">{metrics['total_power']:.4f} W</div>
            <div style="font-size:0.8rem; color:#9ca3af;">Reference carrier: {metrics.get('carrier_power', 0.0):.4f} W</div>
        </div>
        """, unsafe_allow_html=True)
    with m_cols[3]:
        sdr_val = f"{metrics['sdr_db']:.2f} dB" if not np.isinf(metrics['sdr_db']) else "Perfect (∞)"
        st.markdown(f"""
        <div class="stMetric">
            <div class="metric-title">Signal-to-Distortion Ratio</div>
            <div class="metric-value">{sdr_val}</div>
            <div style="font-size:0.8rem; color:#9ca3af;">Demodulation MSE: {metrics['mse']:.2e}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Time-Domain Plots ---
    st.subheader("📈 Time Domain Signals")
    
    # We will plot three time domain waveforms: Modulating, Modulated (full and zoomed), and Demodulated vs Original
    fig_time = make_subplots(
        rows=3, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.1,
        subplot_titles=(
            "Original Message Signal m(t)",
            "Modulated RF Signal s(t) (Blue: Noiseless | Pink: Noisy | Yellow: Envelope overlay)",
            "Recovered Message vs. Original (Phase & Gain compensated)"
        )
    )
    
    # Message Signal
    fig_time.add_trace(
        go.Scatter(x=t * 1000, y=message, name="Message", line=dict(color='#60a5fa', width=2)),
        row=1, col=1
    )
    
    # Modulated Signal
    # Plot first 10 cycles or 5ms zoom for detail, but we can plot full signal and allow zooming.
    # To prevent UI lag on huge signals, we slice if they are long
    max_plot_pts = 50000
    step = max(1, len(t) // max_plot_pts)
    t_plot = t[::step]
    modulated_plot = modulated[::step]
    raw_modulated_plot = raw_modulated[::step]
    
    fig_time.add_trace(
        go.Scatter(x=t_plot * 1000, y=raw_modulated_plot, name="Modulated (Noiseless)", line=dict(color='#ef4444', width=1.5), opacity=0.4),
        row=2, col=1
    )
    if noise_enabled:
        fig_time.add_trace(
            go.Scatter(x=t_plot * 1000, y=modulated_plot, name="Modulated (Noisy)", line=dict(color='#ec4899', width=1), opacity=0.8),
            row=2, col=1
        )
        
    # Envelope overlay for DSB-LC
    if mod_scheme == "dsb-lc":
        message_norm = core.normalize_signal(message)
        env_upper = Ac * (1.0 + m * message_norm)
        env_lower = -env_upper
        fig_time.add_trace(
            go.Scatter(x=t * 1000, y=env_upper, name="Upper Envelope", line=dict(color='#eab308', width=2, dash='dash')),
            row=2, col=1
        )
        fig_time.add_trace(
            go.Scatter(x=t * 1000, y=env_lower, name="Lower Envelope", line=dict(color='#eab308', width=2, dash='dash'), showlegend=False),
            row=2, col=1
        )
        
    # Demodulated vs Original
    orig_align, demod_align = core.align_and_scale_signals(message, demodulated)
    fig_time.add_trace(
        go.Scatter(x=t * 1000, y=orig_align, name="Original Message (Reference)", line=dict(color='#60a5fa', width=2, dash='dot')),
        row=3, col=1
    )
    fig_time.add_trace(
        go.Scatter(x=t * 1000, y=demod_align, name="Recovered Message", line=dict(color='#10b981', width=2)),
        row=3, col=1
    )
    
    fig_time.update_layout(
        height=800,
        plot_bgcolor="#1f2937",
        paper_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_time.update_xaxes(title_text="Time (milliseconds)", gridcolor="#374151")
    fig_time.update_yaxes(gridcolor="#374151")
    
    st.plotly_chart(fig_time, use_container_width=True)

    # Let's show a zoom in of the modulated signal to see the carrier cycles!
    st.markdown("#### 🔍 Zoom-in: Carrier Oscillation View")
    # Show first 5ms
    zoom_limit = min(0.005, duration)
    zoom_idx = t <= zoom_limit
    
    fig_zoom = go.Figure()
    fig_zoom.add_trace(go.Scatter(x=t[zoom_idx]*1000, y=raw_modulated[zoom_idx], name="Noiseless Modulated", line=dict(color='#ef4444', width=2)))
    if noise_enabled:
        fig_zoom.add_trace(go.Scatter(x=t[zoom_idx]*1000, y=modulated[zoom_idx], name="Noisy Modulated", line=dict(color='#ec4899', width=1.5)))
        
    if mod_scheme == "dsb-lc":
        fig_zoom.add_trace(go.Scatter(x=t[zoom_idx]*1000, y=env_upper[zoom_idx], name="Envelope", line=dict(color='#eab308', width=2, dash='dash')))
        
    fig_zoom.update_layout(
        title=f"Detailed Waveform (First {zoom_limit*1000:.1f} ms of transmission)",
        xaxis_title="Time (ms)",
        yaxis_title="Amplitude",
        plot_bgcolor="#1f2937",
        paper_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        height=300
    )
    fig_zoom.update_xaxes(gridcolor="#374151")
    fig_zoom.update_yaxes(gridcolor="#374151")
    st.plotly_chart(fig_zoom, use_container_width=True)

    st.markdown("---")

    # --- Frequency-Domain Plots ---
    st.subheader("📊 Frequency Spectrum (FFT Analysis)")
    
    # Calculate FFTs
    f_msg, mag_msg = core.compute_fft(message, fs)
    f_mod, mag_mod = core.compute_fft(modulated, fs)
    f_dem, mag_dem = core.compute_fft(demodulated, fs)
    
    # Setup subplots for spectra
    fig_freq = make_subplots(
        rows=1, cols=3,
        subplot_titles=(
            "Message Spectrum",
            "Modulated RF Spectrum",
            "Demodulated Baseband Spectrum"
        )
    )
    
    # Message Spectrum (Linear scale or dB scale)
    fig_freq.add_trace(
        go.Scatter(x=f_msg, y=mag_msg, name="Message Spec", line=dict(color='#60a5fa', width=1.5)),
        row=1, col=1
    )
    
    # Modulated Spectrum
    fig_freq.add_trace(
        go.Scatter(x=f_mod, y=mag_mod, name="Modulated Spec", line=dict(color='#ef4444', width=1.5)),
        row=1, col=2
    )
    
    # Demodulated Spectrum
    fig_freq.add_trace(
        go.Scatter(x=f_dem, y=mag_dem, name="Demodulated Spec", line=dict(color='#10b981', width=1.5)),
        row=1, col=3
    )
    
    # Zoom x-axes to appropriate ranges
    fig_freq.update_xaxes(title_text="Frequency (Hz)", gridcolor="#374151", row=1, col=1, range=[-fc * 1.5, fc * 1.5])
    fig_freq.update_xaxes(title_text="Frequency (Hz)", gridcolor="#374151", row=1, col=2, range=[-fc * 2.2, fc * 2.2])
    fig_freq.update_xaxes(title_text="Frequency (Hz)", gridcolor="#374151", row=1, col=3, range=[-fc * 1.5, fc * 1.5])
    
    fig_freq.update_yaxes(title_text="Normalized Magnitude", gridcolor="#374151")
    
    fig_freq.update_layout(
        height=400,
        plot_bgcolor="#1f2937",
        paper_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        showlegend=False
    )
    
    st.plotly_chart(fig_freq, use_container_width=True)

with tab2:
    st.subheader("🎵 Audio Laboratory")
    st.markdown("Here you can process vocal or music files through the AM modulation/demodulation chain. This allows you to hear the physical effects of carrier modulation, noise interference, and reception distortion.")
    
    if message_source != "Audio File Upload":
        st.info("To use this tab, select **Audio File Upload** as the Message Source in the sidebar, and upload a WAV file.")
    elif uploaded_file is None:
        st.warning("Please upload a WAV file in the sidebar to activate the Audio Lab.")
    else:
        # Original Audio
        st.markdown("### 1. Original Message (Baseband)")
        st.audio(audio_bytes, format="audio/wav")
        
        # Modulated Audio
        st.markdown("### 2. Modulated RF Signal")
        st.write("This is the high-frequency modulated signal. It usually sounds like high-pitched static/noise because the audio content is shifted to carrier frequency.")
        
        # Write modulated signal to buffer
        mod_buffer = io.BytesIO()
        # Scale to prevent clipping
        mod_scaled = modulated / np.max(np.abs(modulated)) if np.max(np.abs(modulated)) > 0 else modulated
        sf.write(mod_buffer, mod_scaled, fs, format='WAV', subtype='PCM_16')
        st.audio(mod_buffer.getvalue(), format="audio/wav")
        
        # Demodulated Audio
        st.markdown("### 3. Recovered Baseband Audio")
        st.write("This is the audio signal retrieved after demodulation and filtering.")
        
        demod_buffer = io.BytesIO()
        demod_scaled = demodulated / np.max(np.abs(demodulated)) if np.max(np.abs(demodulated)) > 0 else demodulated
        sf.write(demod_buffer, demod_scaled, fs, format='WAV', subtype='PCM_16')
        st.audio(demod_buffer.getvalue(), format="audio/wav")
        
        # Downloads
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download Modulated WAV",
                data=mod_buffer.getvalue(),
                file_name="am_modulated.wav",
                mime="audio/wav"
            )
        with col2:
            st.download_button(
                label="📥 Download Demodulated WAV",
                data=demod_buffer.getvalue(),
                file_name="am_demodulated.wav",
                mime="audio/wav"
            )

with tab3:
    st.subheader("📖 Mathematics of Amplitude Modulation")
    
    st.markdown(r"""
    ### 1. Conventional AM (DSB-LC)
    Double Sideband Large Carrier (DSB-LC) includes the carrier wave explicitly. This allows for simple demodulation using an **Envelope Detector**, which requires no carrier phase synchronization.
    
    The modulated signal equation is:
    $$s(t) = A_c [1 + m \cdot m_n(t)] \cos(2\pi f_c t)$$
    
    Where:
    *   $A_c$ is the carrier amplitude.
    *   $m$ is the **modulation index** (defines the modulation depth).
    *   $m_n(t)$ is the normalized message signal ($\max |m_n(t)| = 1$).
    *   $f_c$ is the carrier frequency.
    
    **Under-modulation ($m < 1$):** The envelope of the modulated carrier matches the message perfectly without crossing zero. Envelope detection works without distortion.
    
    **Over-modulation ($m > 1$):** The envelope crosses zero, causing $180^\circ$ phase reversals in the carrier. Envelope detection fails, resulting in severe non-linear distortion.
    
    **Power Efficiency:**
    $$\eta = \frac{P_{sidebands}}{P_{total}} = \frac{m^2 P_{m_n}}{1 + m^2 P_{m_n}}$$
    For a single sine wave message ($P_{m_n} = 0.5$) and critical modulation ($m=1.0$), the maximum theoretical efficiency is only **$33.3\%$**. The remaining $66.7\%$ of the power is wasted in transmitting the carrier, which carries no information.
    """)
    
    st.markdown(r"""
    ---
    ### 2. Double Sideband Suppressed Carrier (DSB-SC)
    To save power, the carrier component can be suppressed, leaving only the sidebands.
    
    $$s(t) = m(t) \cos(2\pi f_c t)$$
    
    **Efficiency:** **$100\%$** of the transmitted power is useful sideband power.
    
    **Demodulation:** Envelope detection cannot be used because the envelope shape does not match the message (due to zero-crossings). A **Coherent Receiver** is required.
    
    A coherent receiver multiplies the received signal by a local carrier:
    $$r(t) = s(t) \cos(2\pi f_c t + \theta) = m(t) \cos(2\pi f_c t) \cos(2\pi f_c t + \theta)$$
    Using trigonometric identities:
    $$r(t) = \frac{1}{2} m(t) [\cos(\theta) + \cos(4\pi f_c t + \theta)]$$
    Applying a low-pass filter (LPF) removes the high-frequency $2f_c$ component, yielding:
    $$y(t) = \frac{1}{2} m(t) \cos(\theta)$$
    
    *   **Phase Sync:** If there is a phase error $\theta$:
        *   At $\theta = 0^\circ$, the output is maximized ($y(t) = 0.5 m(t)$).
        *   At $\theta = 90^\circ$, the output is **zero** ($y(t) = 0$). This is the quadrature null effect.
    """)
    
    st.markdown(r"""
    ---
    ### 3. Single Sideband Suppressed Carrier (SSB-SC)
    A DSB-SC signal has redundant sidebands (Upper Sideband USB and Lower Sideband LSB are mirror images). SSB suppresses both the carrier and one of the sidebands to save **both power and bandwidth** (SSB bandwidth is $f_m$, compared to $2f_m$ for DSB).
    
    **SSB Modulation using the Hilbert Transform Method:**
    $$s(t) = m(t)\cos(2\pi f_c t) \mp \hat{m}(t)\sin(2\pi f_c t)$$
    
    Where:
    *   $\hat{m}(t)$ is the Hilbert transform of $m(t)$ (a $-90^\circ$ phase shift of all frequency components).
    *   $-$ sign is for the **Upper Sideband (USB)**.
    *   $+$ sign is for the **Lower Sideband (LSB)**.
    """)
