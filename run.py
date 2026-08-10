# Точка входа в приложение FollMuz
import sys
import os

def get_base_dir():
    # Определяем где мы запущены — из под exe или как обычный скрипт
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def setup_paths():
    root = get_base_dir()
    src_path = os.path.join(root, 'src')
    
    if os.path.exists(src_path):
        sys.path.insert(0, src_path)
    
    return root

def ensure_dirs(root):
    # Создаем базовые папки если их нет
    for folder in ['downloads', 'logs', 'config']:
        p = os.path.join(root, folder)
        os.makedirs(p, exist_ok=True)

def hide_console():
    # Хак для скрытия консольного окна под виндой при запуске GUI
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                kernel32.ShowWindow(hwnd, 0) # SW_HIDE = 0
        except Exception:
            pass # Если не получилось — ну и ладно, не падать же

def run_gui():
    try:
        from src.gui import main as gui_main
        gui_main()
    except Exception as e:
        import traceback
        print(f"[FATAL] GUI Error: {e}")
        traceback.print_exc()
        input("Нажмите Enter для выхода...")

def run_cli():
    try:
        from src.cli import FollMuzCLI
        cli = FollMuzCLI()
        cli.run()
    except Exception as e:
        print(f"[FATAL] CLI Error: {e}")

def main():
    root = setup_paths()
    ensure_dirs(root)
    
    # TODO: добавить нормальный парсер аргументов (argparse), когда руки дойдут
    if '--cli' in sys.argv:
        run_cli()
    else:
        hide_console()
        run_gui()

if __name__ == "__main__":
    main()
