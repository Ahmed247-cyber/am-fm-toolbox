import argparse
import sys
import numpy as np
import soundfile as sf
import os
import matplotlib.pyplot as plt

# Try relative import first, fallback to direct import
try:
    from . import core
except ImportError:
    import core

def load_audio(file_path):
    """Loads an audio file and converts it to mono if stereo."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    try:
        data, fs = sf.read(file_path)
        if len(data.shape) > 1:
            # Convert to mono
            data = np.mean(data, axis=1)
        return data, fs
    except Exception as e:
        print(f"Error reading audio file: {e}", file=sys.stderr)
        sys.exit(1)

def save_audio(file_path, data, fs):
    """Saves audio data to a WAV file."""
    try:
        # Normalize to prevent clipping
        peak = np.max(np.abs(data))
        if peak > 1.0:
            data = data / peak
            print(f"Warning: Audio peak exceeded 1.0. Normalized by factor of {1/peak:.4f} to prevent clipping.")
        sf.write(file_path, data, fs)
        print(f"Success: Saved audio to {file_path}")
    except Exception as e:
        print(f"Error saving audio file: {e}", file=sys.stderr)
        sys.exit(1)

def handle_modulate(args):
    print(f"=== Amplitude Modulation ===")
    print(f"Carrier Frequency: {args.fc} Hz")
    print(f"Modulation Scheme: {args.type.upper()}")
    
    # Get message and fs
    if args.input:
        print(f"Loading input audio from: {args.input}")
        message, fs = load_audio(args.input)
    else:
        print(f"Synthesizing {args.wave_type} wave: {args.wave_freq} Hz, {args.duration}s, fs={args.fs} Hz")
        t, message = core.generate_wave(args.wave_type, args.wave_freq, args.fs, args.duration)
        fs = args.fs
        
    # Perform modulation
    if args.type == 'dsb-lc':
        modulated, carrier, t = core.modulate_dsb_lc(message, args.fc, fs, args.index, args.ac)
    elif args.type == 'dsb-sc':
        modulated, carrier, t = core.modulate_dsb_sc(message, args.fc, fs, args.ac)
    elif args.type in ['ssb-usb', 'ssb-lsb', 'ssb']:
        sb = 'upper' if 'usb' in args.type else 'lower'
        modulated, carrier, t = core.modulate_ssb(message, args.fc, fs, sb, args.ac)
    else:
        print(f"Error: Unknown modulation type {args.type}", file=sys.stderr)
        sys.exit(1)
        
    # Add noise if requested
    if args.snr is not None:
        print(f"Simulating Channel: Adding AWGN with SNR = {args.snr} dB")
        modulated, _ = core.add_awgn(modulated, args.snr)
        
    # Save modulated output
    save_audio(args.output, modulated, fs)

def handle_demodulate(args):
    print(f"=== Amplitude Demodulation ===")
    print(f"Carrier Frequency: {args.fc} Hz")
    print(f"Demodulation Method: {args.type.upper()}")
    
    # Load modulated signal
    modulated, fs = load_audio(args.input)
    
    # Perform demodulation
    if args.type == 'coherent':
        demodulated = core.demodulate_coherent(modulated, args.fc, fs, args.phase, args.cutoff)
    elif args.type == 'envelope':
        demodulated = core.demodulate_envelope(modulated, fs, args.envelope_method, args.cutoff)
        # For envelope detection of conventional AM, subtract mean to remove carrier offset
        if args.detrend:
            demodulated = demodulated - np.mean(demodulated)
    else:
        print(f"Error: Unknown demodulation method {args.type}", file=sys.stderr)
        sys.exit(1)
        
    # Save output
    save_audio(args.output, demodulated, fs)

def handle_analyze(args):
    print(f"=== AM Analysis ===")
    
    # Synthesize message
    fs = args.fs
    t, message = core.generate_wave(args.wave_type, args.wave_freq, fs, args.duration)
    
    # Modulate
    if args.type == 'dsb-lc':
        modulated, carrier, t = core.modulate_dsb_lc(message, args.fc, fs, args.index, args.ac)
    elif args.type == 'dsb-sc':
        modulated, carrier, t = core.modulate_dsb_sc(message, args.fc, fs, args.ac)
    elif args.type in ['ssb-usb', 'ssb-lsb', 'ssb']:
        sb = 'upper' if 'usb' in args.type else 'lower'
        modulated, carrier, t = core.modulate_ssb(message, args.fc, fs, sb, args.ac)
    else:
        print(f"Error: Unknown modulation type {args.type}", file=sys.stderr)
        sys.exit(1)
        
    # Add noise
    raw_modulated = modulated.copy()
    if args.snr is not None:
        modulated, _ = core.add_awgn(modulated, args.snr)
        
    # Demodulate
    if args.demod == 'coherent':
        demodulated = core.demodulate_coherent(modulated, args.fc, fs, args.phase, args.cutoff)
    else:
        demodulated = core.demodulate_envelope(modulated, fs, args.envelope_method, args.cutoff)
        if args.detrend or args.type == 'dsb-lc':
            demodulated = demodulated - np.mean(demodulated)
            
    # Compute Metrics
    m_val = args.index if args.type == 'dsb-lc' else None
    metrics = core.compute_metrics(message, demodulated, modulated, carrier, m_val, args.type)
    
    print("\nResults Metrics:")
    print(f"----------------------------------------")
    print(f"Modulation Scheme: {args.type.upper()}")
    print(f"Modulation Status: {metrics.get('modulation_status', 'N/A')}")
    print(f"Total Modulated Power: {metrics['total_power']:.6f} W")
    if 'carrier_power' in metrics:
        print(f"Carrier Power: {metrics['carrier_power']:.6f} W")
        print(f"Sideband Power: {metrics['sideband_power']:.6f} W")
        print(f"Power Efficiency: {metrics['efficiency']:.2f}%")
    print(f"Demodulation MSE (Aligned): {metrics['mse']:.6e}")
    print(f"Signal-to-Distortion Ratio (SDR): {metrics['sdr_db']:.2f} dB")
    print(f"----------------------------------------")
    
    # Generate static plot if requested
    if args.plot:
        fig, axes = plt.subplots(3, 2, figsize=(12, 8))
        
        # Time Domain Message
        axes[0, 0].plot(t * 1000, message, label='Message', color='#1f77b4')
        axes[0, 0].set_title('Message Signal (Time Domain)')
        axes[0, 0].set_xlabel('Time (ms)')
        axes[0, 0].set_ylabel('Amplitude')
        axes[0, 0].grid(True)
        axes[0, 0].legend()
        
        # FFT Message
        mfreqs, mspec = core.compute_fft(message, fs)
        axes[0, 1].plot(mfreqs, 20 * np.log10(mspec + 1e-6), color='#1f77b4')
        axes[0, 1].set_title('Message Spectrum')
        axes[0, 1].set_xlabel('Frequency (Hz)')
        axes[0, 1].set_ylabel('Magnitude (dB)')
        axes[0, 1].set_xlim(-args.fc * 1.5, args.fc * 1.5)
        axes[0, 1].grid(True)
        
        # Time Domain Modulated (show small segment for detail)
        # Limit plot to 5ms or 10 message periods to see carrier oscillations
        p_len = min(len(t), int(fs * 0.005))
        axes[1, 0].plot(t[:p_len] * 1000, raw_modulated[:p_len], label='Modulated (Noiseless)', color='#d62728', alpha=0.5)
        if args.snr is not None:
            axes[1, 0].plot(t[:p_len] * 1000, modulated[:p_len], label=f'Modulated + Noise ({args.snr}dB)', color='#e377c2', alpha=0.8)
        axes[1, 0].set_title('Modulated Signal (Time Domain - Zoomed)')
        axes[1, 0].set_xlabel('Time (ms)')
        axes[1, 0].set_ylabel('Amplitude')
        axes[1, 0].grid(True)
        axes[1, 0].legend()
        
        # FFT Modulated
        modfreqs, modspec = core.compute_fft(modulated, fs)
        axes[1, 1].plot(modfreqs, 20 * np.log10(modspec + 1e-6), color='#d62728')
        axes[1, 1].set_title('Modulated Signal Spectrum')
        axes[1, 1].set_xlabel('Frequency (Hz)')
        axes[1, 1].set_ylabel('Magnitude (dB)')
        axes[1, 1].set_xlim(-args.fc * 2, args.fc * 2)
        axes[1, 1].grid(True)
        
        # Time Domain Demodulated (Aligned and original overlaid)
        # Scale demod for comparison
        orig_align, demod_align = core.align_and_scale_signals(message, demodulated)
        axes[2, 0].plot(t * 1000, orig_align, label='Original (Aligned)', color='#1f77b4', linestyle='--')
        axes[2, 0].plot(t * 1000, demod_align, label='Demodulated', color='#2ca02c')
        axes[2, 0].set_title('Demodulated vs Original (Time Domain)')
        axes[2, 0].set_xlabel('Time (ms)')
        axes[2, 0].set_ylabel('Normalized Amplitude')
        axes[2, 0].grid(True)
        axes[2, 0].legend()
        
        # FFT Demodulated
        demfreqs, demspec = core.compute_fft(demodulated, fs)
        axes[2, 1].plot(demfreqs, 20 * np.log10(demspec + 1e-6), color='#2ca02c')
        axes[2, 1].set_title('Demodulated Signal Spectrum')
        axes[2, 1].set_xlabel('Frequency (Hz)')
        axes[2, 1].set_ylabel('Magnitude (dB)')
        axes[2, 1].set_xlim(-args.fc * 1.5, args.fc * 1.5)
        axes[2, 1].grid(True)
        
        plt.tight_layout()
        plt.savefig(args.plot, dpi=300)
        print(f"Saved analysis plot to: {args.plot}")
        plt.close()

def main():
    parser = argparse.ArgumentParser(description="Amplitude Modulation (AM) Toolbox CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Modulate Subparser
    p_mod = subparsers.add_parser("modulate", help="Modulate a signal (audio or synthesized) into an AM wave")
    p_mod.add_argument("-i", "--input", help="Path to input audio file (WAV). If omitted, synthesizes a signal.")
    p_mod.add_argument("-o", "--output", required=True, help="Path to save output modulated WAV file")
    p_mod.add_argument("-t", "--type", default="dsb-sc", choices=["dsb-lc", "dsb-sc", "ssb-usb", "ssb-lsb"], help="Modulation type (default: dsb-sc)")
    p_mod.add_argument("--fc", type=float, default=10000, help="Carrier frequency in Hz (default: 10000)")
    p_mod.add_argument("-m", "--index", type=float, default=1.0, help="Modulation index for DSB-LC (default: 1.0)")
    p_mod.add_argument("--ac", type=float, default=1.0, help="Carrier amplitude (default: 1.0)")
    p_mod.add_argument("--fs", type=float, default=44100, help="Sampling frequency in Hz for synthesized signal (default: 44100)")
    p_mod.add_argument("-d", "--duration", type=float, default=2.0, help="Duration in seconds for synthesized signal (default: 2.0)")
    p_mod.add_argument("-w", "--wave-type", default="sine", choices=["sine", "square", "triangle", "sawtooth", "sweep"], help="Message wave type (default: sine)")
    p_mod.add_argument("--wave-freq", type=float, default=440, help="Message wave frequency in Hz (default: 440)")
    p_mod.add_argument("--snr", type=float, help="Simulate channel: Add AWGN with this SNR in dB")
    
    # Demodulate Subparser
    p_demod = subparsers.add_parser("demodulate", help="Demodulate an AM wave to recover the message signal")
    p_demod.add_argument("-i", "--input", required=True, help="Path to input modulated WAV file")
    p_demod.add_argument("-o", "--output", required=True, help="Path to save output demodulated WAV file")
    p_demod.add_argument("-t", "--type", default="coherent", choices=["coherent", "envelope"], help="Demodulation type (default: coherent)")
    p_demod.add_argument("--fc", type=float, default=10000, help="Carrier frequency in Hz (default: 10000)")
    p_demod.add_argument("-p", "--phase", type=float, default=0.0, help="Phase offset in degrees for coherent demodulation (default: 0.0)")
    p_demod.add_argument("--envelope-method", default="hilbert", choices=["hilbert", "diode"], help="Envelope extraction method (default: hilbert)")
    p_demod.add_argument("--cutoff", type=float, help="Lowpass filter cutoff frequency in Hz (defaults to optimal value)")
    p_demod.add_argument("--detrend", action="store_true", help="Subtract mean (DC offset) from demodulated signal (helpful for envelope detection)")
    
    # Analyze Subparser
    p_ana = subparsers.add_parser("analyze", help="Simulate a complete modulation-demodulation chain and export a report plot")
    p_ana.add_argument("-t", "--type", default="dsb-sc", choices=["dsb-lc", "dsb-sc", "ssb-usb", "ssb-lsb"], help="Modulation type (default: dsb-sc)")
    p_ana.add_argument("--fc", type=float, default=5000, help="Carrier frequency in Hz (default: 5000)")
    p_ana.add_argument("-m", "--index", type=float, default=0.8, help="Modulation index for DSB-LC (default: 0.8)")
    p_ana.add_argument("--ac", type=float, default=1.0, help="Carrier amplitude (default: 1.0)")
    p_ana.add_argument("--fs", type=float, default=44100, help="Sampling frequency in Hz (default: 44100)")
    p_ana.add_argument("-d", "--duration", type=float, default=0.1, help="Duration in seconds (default: 0.1 to avoid heavy plotting)")
    p_ana.add_argument("-w", "--wave-type", default="sine", choices=["sine", "square", "triangle", "sawtooth", "sweep"], help="Message wave type (default: sine)")
    p_ana.add_argument("--wave-freq", type=float, default=200, help="Message wave frequency in Hz (default: 200)")
    p_ana.add_argument("--snr", type=float, help="Channel SNR in dB")
    p_ana.add_argument("--demod", default="coherent", choices=["coherent", "envelope"], help="Demodulation type (default: coherent)")
    p_ana.add_argument("-p", "--phase", type=float, default=0.0, help="Phase offset in degrees for coherent demodulation (default: 0.0)")
    p_ana.add_argument("--envelope-method", default="hilbert", choices=["hilbert", "diode"], help="Envelope extraction method (default: hilbert)")
    p_ana.add_argument("--cutoff", type=float, help="Filter cutoff frequency in Hz")
    p_ana.add_argument("--detrend", action="store_true", help="Subtract mean from demodulated signal")
    p_ana.add_argument("--plot", default="am_analysis.png", help="Path to save the analysis plot (default: am_analysis.png)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
        
    if args.command == "modulate":
        handle_modulate(args)
    elif args.command == "demodulate":
        handle_demodulate(args)
    elif args.command == "analyze":
        handle_analyze(args)

if __name__ == "__main__":
    main()
