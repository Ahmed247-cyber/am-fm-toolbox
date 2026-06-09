import numpy as np
from scipy.signal import hilbert, butter, filtfilt, chirp, square, sawtooth

def generate_wave(wave_type, freq, fs, duration, amplitude=1.0, phase=0.0):
    """
    Generates a message signal of a specified type.
    
    Parameters:
        wave_type (str): 'sine', 'square', 'triangle', 'sawtooth', or 'sweep'
        freq (float): Frequency of the wave in Hz (start frequency for sweep)
        fs (float): Sampling frequency in Hz
        duration (float): Duration of the signal in seconds
        amplitude (float): Peak amplitude of the signal
        phase (float): Initial phase in radians
        
    Returns:
        t (ndarray): Time vector
        signal (ndarray): Generated signal vector
    """
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    
    if wave_type == 'sine':
        signal = amplitude * np.sin(2 * np.pi * freq * t + phase)
    elif wave_type == 'square':
        signal = amplitude * square(2 * np.pi * freq * t + phase)
    elif wave_type == 'triangle':
        # sawtooth(..., width=0.5) generates a triangle wave
        signal = amplitude * sawtooth(2 * np.pi * freq * t + phase, width=0.5)
    elif wave_type == 'sawtooth':
        signal = amplitude * sawtooth(2 * np.pi * freq * t + phase)
    elif wave_type == 'sweep':
        # Linear frequency sweep from freq to freq*10
        signal = amplitude * chirp(t, f0=freq, t1=duration, f1=freq * 10, method='linear')
    else:
        raise ValueError(f"Unknown wave type: {wave_type}")
        
    return t, signal

def normalize_signal(signal):
    """Normalizes the signal to have a peak value of 1.0 (maintaining zero-mean if applicable)."""
    peak = np.max(np.abs(signal))
    if peak > 0:
        return signal / peak
    return signal

def modulate_dsb_lc(message, carrier_freq, fs, m, Ac=1.0):
    """
    Double Sideband Large Carrier (Conventional AM) Modulation.
    s(t) = Ac * [1 + m * m_n(t)] * cos(2*pi*fc*t)
    
    Parameters:
        message (ndarray): Modulating message signal
        carrier_freq (float): Carrier frequency in Hz
        fs (float): Sampling rate in Hz
        m (float): Modulation index (typically 0.0 to 1.0, > 1.0 for overmodulation)
        Ac (float): Carrier amplitude
        
    Returns:
        modulated (ndarray): Modulated signal
        carrier (ndarray): Pure carrier signal
        t (ndarray): Time vector
    """
    duration = len(message) / fs
    t = np.linspace(0, duration, len(message), endpoint=False)
    
    # Normalize the message to peak amplitude of 1.0
    message_norm = normalize_signal(message)
    
    carrier = Ac * np.cos(2 * np.pi * carrier_freq * t)
    modulated = Ac * (1.0 + m * message_norm) * np.cos(2 * np.pi * carrier_freq * t)
    
    return modulated, carrier, t

def modulate_dsb_sc(message, carrier_freq, fs, Ac=1.0):
    """
    Double Sideband Suppressed Carrier (DSB-SC) Modulation.
    s(t) = Ac * m(t) * cos(2*pi*fc*t)
    
    Parameters:
        message (ndarray): Modulating message signal
        carrier_freq (float): Carrier frequency in Hz
        fs (float): Sampling rate in Hz
        Ac (float): Carrier amplitude scaling
        
    Returns:
        modulated (ndarray): Modulated signal
        carrier (ndarray): Carrier reference signal
        t (ndarray): Time vector
    """
    duration = len(message) / fs
    t = np.linspace(0, duration, len(message), endpoint=False)
    
    carrier = Ac * np.cos(2 * np.pi * carrier_freq * t)
    modulated = Ac * message * np.cos(2 * np.pi * carrier_freq * t)
    
    return modulated, carrier, t

def modulate_ssb(message, carrier_freq, fs, sideband='upper', Ac=1.0):
    """
    Single Sideband Suppressed Carrier (SSB-SC) Modulation.
    s(t) = Ac * [m(t)*cos(2*pi*fc*t) -/+ Hilbert(m(t))*sin(2*pi*fc*t)]
    - for USB, + for LSB
    
    Parameters:
        message (ndarray): Modulating message signal
        carrier_freq (float): Carrier frequency in Hz
        fs (float): Sampling rate in Hz
        sideband (str): 'upper' (USB) or 'lower' (LSB)
        Ac (float): Carrier amplitude scaling
        
    Returns:
        modulated (ndarray): Modulated signal
        carrier (ndarray): Carrier reference signal (cos)
        t (ndarray): Time vector
    """
    duration = len(message) / fs
    t = np.linspace(0, duration, len(message), endpoint=False)
    
    # Compute Hilbert transform
    analytic_signal = hilbert(message)
    message_hilbert = np.imag(analytic_signal)
    
    carrier_cos = Ac * np.cos(2 * np.pi * carrier_freq * t)
    carrier_sin = Ac * np.sin(2 * np.pi * carrier_freq * t)
    
    if sideband.lower() == 'upper' or sideband.lower() == 'usb':
        modulated = Ac * (message * np.cos(2 * np.pi * carrier_freq * t) - 
                          message_hilbert * np.sin(2 * np.pi * carrier_freq * t))
    elif sideband.lower() == 'lower' or sideband.lower() == 'lsb':
        modulated = Ac * (message * np.cos(2 * np.pi * carrier_freq * t) + 
                          message_hilbert * np.sin(2 * np.pi * carrier_freq * t))
    else:
        raise ValueError("Sideband must be 'upper' (or 'usb') or 'lower' (or 'lsb')")
        
    return modulated, carrier_cos, t

def add_awgn(signal, snr_db):
    """
    Adds Additive White Gaussian Noise (AWGN) to a signal.
    
    Parameters:
        signal (ndarray): Input signal
        snr_db (float): Target SNR in dB. If None or inf, returns original signal.
        
    Returns:
        noisy_signal (ndarray): Signal with added noise
        noise (ndarray): The added noise vector
    """
    if snr_db is None or np.isinf(snr_db):
        return signal.copy(), np.zeros_like(signal)
        
    # Calculate signal power
    sig_power = np.mean(signal ** 2)
    if sig_power == 0:
        sig_power = 1e-10
        
    # Convert SNR from dB to linear
    snr_linear = 10 ** (snr_db / 10.0)
    
    # Calculate noise power
    noise_power = sig_power / snr_linear
    
    # Generate white Gaussian noise
    noise = np.random.normal(0, np.sqrt(noise_power), len(signal))
    
    return signal + noise, noise

def design_lowpass_filter(cutoff, fs, order=5):
    """Helper to design Butterworth lowpass filter coefficients."""
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def apply_lowpass_filter(signal, cutoff, fs, order=5):
    """Applies a zero-phase Butterworth lowpass filter to the signal."""
    b, a = design_lowpass_filter(cutoff, fs, order)
    return filtfilt(b, a, signal)

def demodulate_coherent(modulated_signal, carrier_freq, fs, phase_offset_deg=0.0, cutoff_freq=None):
    """
    Coherent/Synchronous Demodulation.
    Multiplies by local carrier with phase offset and low-pass filters.
    
    Parameters:
        modulated_signal (ndarray): Received modulated signal
        carrier_freq (float): Carrier frequency in Hz
        fs (float): Sampling rate in Hz
        phase_offset_deg (float): Local oscillator phase error in degrees
        cutoff_freq (float): Cutoff frequency of the low-pass filter (LPF)
        
    Returns:
        demodulated (ndarray): Extracted message signal
    """
    duration = len(modulated_signal) / fs
    t = np.linspace(0, duration, len(modulated_signal), endpoint=False)
    
    # Generate local carrier with phase offset
    phase_offset_rad = np.radians(phase_offset_deg)
    local_carrier = np.cos(2 * np.pi * carrier_freq * t + phase_offset_rad)
    
    # Product detector
    product = modulated_signal * local_carrier
    
    # Low-pass filter to extract baseband message
    if cutoff_freq is None:
        # Default cutoff is slightly below carrier frequency to remove the 2*fc component
        cutoff_freq = carrier_freq * 0.8
        
    # Ensure cutoff frequency is less than Nyquist
    if cutoff_freq >= 0.5 * fs:
        cutoff_freq = 0.45 * fs
        
    demodulated = apply_lowpass_filter(product, cutoff_freq, fs)
    
    # For DSB-SC / Conventional AM, demodulation by multiplication results in a factor of 1/2.
    # We scale it back.
    return demodulated * 2.0

def demodulate_envelope(modulated_signal, fs, method='hilbert', cutoff_freq=None):
    """
    Envelope Demodulation (suitable for conventional AM with m <= 1.0).
    
    Parameters:
        modulated_signal (ndarray): Received modulated signal
        fs (float): Sampling rate in Hz
        method (str): 'hilbert' (analytic signal magnitude) or 'diode' (rectifier + filter)
        cutoff_freq (float): Cutoff frequency for the diode lowpass filter (if method='diode')
        
    Returns:
        envelope (ndarray): The extracted envelope of the signal
    """
    if method == 'hilbert':
        # Hilbert transform envelope detector
        analytic = hilbert(modulated_signal)
        envelope = np.abs(analytic)
    elif method == 'diode':
        # Rectify: half-wave rectification
        rectified = np.maximum(modulated_signal, 0.0)
        
        # Low-pass filter to smooth out ripples (acting as capacitor discharge)
        if cutoff_freq is None:
            # Typically set cutoff to filter out carrier frequency but keep message frequency
            # Let's say carrier_freq is high. If we don't know it, we approximate or default.
            # Let's use a default cutoff of 1000 Hz or fs/20.
            cutoff_freq = fs / 50.0
            
        if cutoff_freq >= 0.5 * fs:
            cutoff_freq = 0.45 * fs
            
        # Standard Butterworth filter to smooth the rectified wave
        envelope = apply_lowpass_filter(rectified, cutoff_freq, fs, order=4)
        
        # Scaling factor due to half-wave rectification average (pi factor for sine carrier)
        envelope = envelope * np.pi
    else:
        raise ValueError("Method must be 'hilbert' or 'diode'")
        
    return envelope

def compute_fft(signal, fs):
    """
    Computes the double-sided FFT of a signal, centered at 0 Hz.
    
    Parameters:
        signal (ndarray): Time domain signal
        fs (float): Sampling frequency in Hz
        
    Returns:
        freqs (ndarray): Center-shifted frequencies in Hz
        magnitude (ndarray): Normalized magnitude spectrum
    """
    n = len(signal)
    fft_val = np.fft.fft(signal)
    fft_shifted = np.fft.fftshift(fft_val)
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1/fs))
    
    # Normalize magnitude by signal length
    magnitude = np.abs(fft_shifted) / n
    return freqs, magnitude

def align_and_scale_signals(original, demodulated):
    """
    Aligns and scales the demodulated signal to match the original message.
    Compensates for phase delay and scaling factor changes due to filtering.
    """
    # Remove DC components
    orig_detrend = original - np.mean(original)
    demod_detrend = demodulated - np.mean(demodulated)
    
    # Compute cross-correlation to find time delay
    correlation = np.correlate(orig_detrend, demod_detrend, mode='full')
    lags = np.arange(-len(original) + 1, len(original))
    best_lag = lags[np.argmax(correlation)]
    
    # Shift demodulated signal to align
    if best_lag > 0:
        # Demodulated signal lags original
        aligned_demod = np.zeros_like(demod_detrend)
        aligned_demod[best_lag:] = demod_detrend[:-best_lag]
    elif best_lag < 0:
        # Demodulated signal leads original (unlikely, but for completeness)
        aligned_demod = np.zeros_like(demod_detrend)
        aligned_demod[:best_lag] = demod_detrend[-best_lag:]
    else:
        aligned_demod = demod_detrend.copy()
        
    # Scale aligned_demod to have the same standard deviation as orig_detrend
    orig_std = np.std(orig_detrend)
    demod_std = np.std(aligned_demod)
    
    if demod_std > 0:
        aligned_demod = aligned_demod * (orig_std / demod_std)
        
    return orig_detrend, aligned_demod

def compute_metrics(original, demodulated, modulated, carrier, m=None, scheme='dsb-lc'):
    """
    Computes power, efficiency, and distortion metrics.
    
    Parameters:
        original (ndarray): Original message signal
        demodulated (ndarray): Recovered message signal
        modulated (ndarray): Modulated carrier signal
        carrier (ndarray): Carrier reference signal
        m (float): Modulation index (only for DSB-LC)
        scheme (str): 'dsb-lc', 'dsb-sc', 'ssb'
        
    Returns:
        metrics (dict): Dictionary of calculated parameters
    """
    metrics = {}
    
    # Power Calculations
    p_total = np.mean(modulated ** 2)
    p_carrier_ref = np.mean(carrier ** 2)
    
    metrics['total_power'] = float(p_total)
    
    if scheme == 'dsb-lc':
        # In conventional AM, sideband power is total power minus carrier power.
        # Theoretical carrier power is Ac^2/2.
        # We can calculate carrier power as the power of the carrier wave Ac*cos(2*pi*fc*t).
        metrics['carrier_power'] = float(p_carrier_ref)
        metrics['sideband_power'] = float(max(0.0, p_total - p_carrier_ref))
        if p_total > 0:
            metrics['efficiency'] = float(metrics['sideband_power'] / p_total) * 100.0
        else:
            metrics['efficiency'] = 0.0
            
        if m is not None:
            if m < 1.0:
                metrics['modulation_status'] = "Under-modulation (m < 1)"
            elif np.isclose(m, 1.0):
                metrics['modulation_status'] = "Critical modulation (m = 1)"
            else:
                metrics['modulation_status'] = "Over-modulation (m > 1) - Distortion expected!"
    elif scheme == 'dsb-sc':
        metrics['carrier_power'] = 0.0 # Suppressed
        metrics['sideband_power'] = float(p_total)
        metrics['efficiency'] = 100.0 # 100% of power in sidebands
        metrics['modulation_status'] = "Suppressed Carrier (100% efficiency)"
    elif scheme == 'ssb':
        metrics['carrier_power'] = 0.0 # Suppressed
        metrics['sideband_power'] = float(p_total)
        metrics['efficiency'] = 100.0 # 100% of power in one sideband
        metrics['modulation_status'] = "Single Sideband Suppressed Carrier (100% efficiency)"
        
    # Align signals to calculate distortion metrics
    orig_align, demod_align = align_and_scale_signals(original, demodulated)
    
    # Compute Mean Squared Error (MSE)
    mse = np.mean((orig_align - demod_align) ** 2)
    metrics['mse'] = float(mse)
    
    # Signal-to-Distortion Ratio (SDR) in dB
    signal_power = np.mean(orig_align ** 2)
    distortion_power = mse
    if distortion_power > 0:
        sdr = 10 * np.log10(signal_power / distortion_power)
    else:
        sdr = float('inf')
    metrics['sdr_db'] = float(sdr)
    
    return metrics
