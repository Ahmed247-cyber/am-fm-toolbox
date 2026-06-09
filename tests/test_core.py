import numpy as np
import pytest

# Try relative/absolute imports depending on execution context
try:
    from am_toolbox import core
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from am_toolbox import core

def test_generate_wave():
    fs = 1000
    duration = 2.0
    freq = 10.0
    t, wave = core.generate_wave('sine', freq, fs, duration, amplitude=2.0)
    
    assert len(t) == int(fs * duration)
    assert len(wave) == int(fs * duration)
    assert np.max(wave) == pytest.approx(2.0, rel=1e-3)
    assert np.min(wave) == pytest.approx(-2.0, rel=1e-3)

def test_normalize_signal():
    sig = np.array([-5.0, 0.0, 5.0])
    norm = core.normalize_signal(sig)
    assert np.max(np.abs(norm)) == 1.0
    assert np.array_equal(norm, np.array([-1.0, 0.0, 1.0]))
    
    # Zero signal check
    zero = np.zeros(10)
    norm_zero = core.normalize_signal(zero)
    assert np.array_equal(norm_zero, zero)

def test_modulate_dsb_lc():
    fs = 10000
    duration = 0.5
    fc = 1000
    fm = 50
    m = 0.8
    Ac = 2.0
    
    _, message = core.generate_wave('sine', fm, fs, duration, amplitude=1.0)
    modulated, carrier, t = core.modulate_dsb_lc(message, fc, fs, m, Ac)
    
    # Check bounds of conventional AM: Ac * (1 - m) <= s(t) <= Ac * (1 + m)
    # Ac = 2.0, m = 0.8 => range is 0.4 to 3.6
    assert np.max(np.abs(modulated)) == pytest.approx(Ac * (1 + m), rel=1e-2)
    # At carrier peaks, the envelope is Ac * (1 + m * message)
    # Let's verify peak matches Ac * (1 + m)
    assert np.max(modulated) == pytest.approx(Ac * (1 + m), rel=1e-2)
    assert np.min(modulated) == pytest.approx(-Ac * (1 + m), rel=1e-2)

def test_modulate_dsb_sc():
    fs = 10000
    duration = 0.5
    fc = 1000
    fm = 50
    Ac = 1.5
    
    _, message = core.generate_wave('sine', fm, fs, duration, amplitude=1.0)
    modulated, carrier, t = core.modulate_dsb_sc(message, fc, fs, Ac)
    
    # For message peak = 1.0, modulated peak should be Ac
    assert np.max(np.abs(modulated)) == pytest.approx(Ac, rel=1e-2)

def test_coherent_demodulation_dsb_sc():
    fs = 20000
    duration = 0.5
    fc = 2000
    fm = 100
    
    t, message = core.generate_wave('sine', fm, fs, duration, amplitude=1.0)
    modulated, carrier, _ = core.modulate_dsb_sc(message, fc, fs, Ac=1.0)
    
    # Demodulate with zero phase offset
    demodulated = core.demodulate_coherent(modulated, fc, fs, phase_offset_deg=0.0)
    
    # Align and scale signals to compare
    orig_align, demod_align = core.align_and_scale_signals(message, demodulated)
    
    # MSE should be very small for noiseless channel
    mse = np.mean((orig_align - demod_align) ** 2)
    assert mse < 1e-3
    
    # Coherent demodulation with 90 degree phase offset should result in zero signal (null effect)
    demod_90 = core.demodulate_coherent(modulated, fc, fs, phase_offset_deg=90.0)
    # Crop filter boundary transients for assertion
    demod_90_steady = demod_90[500:-500]
    assert np.max(np.abs(demod_90_steady)) < 1e-2 # Demodulated signal is close to zero in steady state


def test_envelope_demodulation_dsb_lc():
    fs = 20000
    duration = 0.5
    fc = 2000
    fm = 100
    m = 0.5
    Ac = 2.0
    
    t, message = core.generate_wave('sine', fm, fs, duration, amplitude=1.0)
    modulated, carrier, _ = core.modulate_dsb_lc(message, fc, fs, m, Ac)
    
    # Envelope demodulation (Hilbert method)
    envelope = core.demodulate_envelope(modulated, fs, method='hilbert')
    
    # Recover message: subtract mean (Ac) and scale by 1 / (Ac * m)
    recovered = (envelope - np.mean(envelope)) / (Ac * m)
    
    orig_align, demod_align = core.align_and_scale_signals(message, recovered)
    mse = np.mean((orig_align - demod_align) ** 2)
    assert mse < 1e-3

def test_awgn_noise():
    fs = 1000
    duration = 1.0
    t, sig = core.generate_wave('sine', 10, fs, duration, amplitude=1.0)
    
    snr_db = 10.0
    noisy, noise = core.add_awgn(sig, snr_db)
    
    sig_power = np.mean(sig ** 2)
    noise_power = np.mean(noise ** 2)
    calculated_snr = 10 * np.log10(sig_power / noise_power)
    
    assert calculated_snr == pytest.approx(snr_db, abs=0.5)

def test_metrics_calculation():
    fs = 10000
    duration = 0.5
    fc = 1000
    fm = 100
    m = 0.5
    Ac = 1.0
    
    t, message = core.generate_wave('sine', fm, fs, duration, amplitude=1.0)
    modulated, carrier, _ = core.modulate_dsb_lc(message, fc, fs, m, Ac)
    demodulated = core.demodulate_coherent(modulated, fc, fs)
    
    metrics = core.compute_metrics(message, demodulated, modulated, carrier, m, 'dsb-lc')
    
    assert 'total_power' in metrics
    assert 'carrier_power' in metrics
    assert 'sideband_power' in metrics
    assert 'efficiency' in metrics
    
    # Theoretical carrier power = Ac^2 / 2 = 0.5
    # Theoretical message power (sine, peak=1) = 0.5
    # For m = 0.5, theoretical sideband power = m^2 * P_m * CarrierPower = 0.25 * 0.5 * 0.5 = 0.0625
    # Theoretical efficiency = 0.0625 / (0.5 + 0.0625) = 11.11%
    assert metrics['carrier_power'] == pytest.approx(0.5, rel=1e-2)
    assert metrics['efficiency'] == pytest.approx(11.11, rel=1e-1)
