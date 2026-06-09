import sys
import subprocess
import os

def get_venv_bin(name):
    # Windows uses Scripts directory, Unix/macOS uses bin directory
    if os.name == 'nt':
        path = os.path.join('venv', 'Scripts', name)
    else:
        path = os.path.join('venv', 'bin', name)
    
    # Check if executable exists
    if os.path.exists(path):
        return path
    if os.path.exists(path + '.exe'):
        return path + '.exe'
    return name  # Fallback to system command if virtual env isn't found

def run_app():
    bin_path = get_venv_bin('streamlit')
    cmd = [bin_path, 'run', os.path.join('am_toolbox', 'app.py')]
    print(f"Starting Streamlit dashboard... ({' '.join(cmd)})")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nStopping dashboard.")

def run_test():
    bin_path = get_venv_bin('pytest')
    cmd = [bin_path]
    print(f"Running unit tests... ({' '.join(cmd)})")
    subprocess.run(cmd)

def run_cli(args):
    bin_path = get_venv_bin('python')
    cmd = [bin_path, os.path.join('am_toolbox', 'cli.py')] + args
    subprocess.run(cmd)

def main():
    if len(sys.argv) < 2:
        print("📡 Amplitude Modulation (AM) Toolbox Master Runner")
        print("==================================================")
        print("Usage: python run.py [app | test | cli | <cli-command>]")
        print("\nAvailable Commands:")
        print("  app                   Launch the Streamlit interactive dashboard web app")
        print("  test                  Execute the unit test suite using pytest")
        print("  cli <args>            Directly run the command-line interface")
        print("  modulate <args>       Shortcut for CLI modulation command")
        print("  demodulate <args>     Shortcut for CLI demodulation command")
        print("  analyze <args>        Shortcut for CLI simulation & plot generator")
        print("\nExamples:")
        print("  python run.py app")
        print("  python run.py test")
        print("  python run.py analyze --type dsb-lc --fc 3000 --snr 20 --plot analysis.png")
        print("  python run.py modulate -o modulated.wav --type dsb-sc --fc 10000 --wave-freq 440")
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == 'app':
        run_app()
    elif cmd == 'test':
        run_test()
    elif cmd == 'cli':
        run_cli(sys.argv[2:])
    elif cmd in ['modulate', 'demodulate', 'analyze']:
        # Shortcut to bypass the 'cli' word
        run_cli(sys.argv[1:])
    else:
        print(f"Error: Unknown command '{cmd}'")
        sys.exit(1)

if __name__ == '__main__':
    main()
