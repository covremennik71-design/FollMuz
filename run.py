# run.py - Entry point for FollMuz
import sys
import os

def get_base_dir():
    """Get base directory (where exe and folders are)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def setup_paths():
    """Setup Python path for imports."""
    base_dir = get_base_dir()
    src_dir = os.path.join(base_dir, 'src')
    
    if os.path.exists(src_dir):
        sys.path.insert(0, src_dir)
    
    return base_dir

def ensure_dirs(base_dir):
    """Create necessary directories."""
    for name in ['downloads', 'logs', 'config']:
        path = os.path.join(base_dir, name)
        os.makedirs(path, exist_ok=True)

def hide_console():
    """Hide console window on Windows."""
    if os.name == 'nt':
        try:
            import ctypes
            windll = ctypes.windll.kernel32
            console = windll.GetConsoleWindow()
            if console:
                windll.ShowWindow(console, 0)
        except:
            pass

def run_gui():
    """Run GUI application."""
    try:
        from src.gui import main as gui_main
        gui_main()
    except Exception as e:
        import traceback
        print(f"GUI Error: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")

def run_cli():
    """Run CLI application."""
    try:
        from src.cli import FollMuzCLI
        cli = FollMuzCLI()
        cli.run()
    except Exception as e:
        print(f"CLI Error: {e}")

def main():
    base_dir = setup_paths()
    ensure_dirs(base_dir)
    
    if '--cli' in sys.argv:
        run_cli()
    else:
        hide_console()
        run_gui()

if __name__ == "__main__":
    main()
