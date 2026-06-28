# src/gui.py
import os
import sys
import re
import time
import traceback
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import config
from src.styles import AppColors, AppFonts, AppDimensions, AppStyles, AppEffects, AnimatedWidget
from src.widgets import SimpleProgressLabel, PlaylistProgressLabel, TrackVariantSelector, SettingsWindow, AnimatedButton, AnimatedProgressBar, SkeletonLoader, ToastNotification
from src.constants import TRACK_TYPES
from src.utils import sanitize_filename, create_ctk_font
from src.translations import Translations

def debug_excepthook(exctype, value, tb):
    print(f"!!! ОШИБКА: {exctype.__name__}: {value}")
    print("Стек вызовов:")
    traceback.print_tb(tb)
    
    stack = traceback.extract_tb(tb)
    for frame in stack:
        if frame.filename.endswith('.py'):
            print(f"  Файл: {frame.filename}, строка {frame.lineno}, функция {frame.name}")
            print(f"  Код: {frame.line}")
    
    with open("crash_report.txt", "w", encoding="utf-8") as f:
        traceback.print_exception(exctype, value, tb, file=f)
    
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = debug_excepthook


class AnimatedTabview(ctk.CTkTabview):
    """Tabview с плавной анимацией переключения."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._animation_running = False

    def set(self, tab_name, animate=True):
        if not animate or self._animation_running:
            super().set(tab_name)
            return

        current_tab = self._get_current_tab_name()
        if current_tab == tab_name:
            return

        self._animation_running = True
        current_frame = self.tab(current_tab)

        def switch_and_fade():
            super().set(tab_name)
            self._fade_in(tab_name)

        self._fade_out(current_frame, switch_and_fade)

    def _get_current_tab_name(self):
        try:
            names = self._names
            for name in names:
                frame = self.tab(name)
                if frame.winfo_viewable():
                    return name
            return names[0] if names else ""
        except Exception:
            return ""

    def _fade_out(self, widget, callback, alpha=1.0):
        if alpha <= 0.0:
            callback()
            return
        try:
            widget.configure(fg_color=self._adjust_alpha(alpha))
        except tk.TclError:
            pass
        self.after(20, lambda: self._fade_out(widget, callback, alpha - 0.08))

    def _fade_in(self, tab_name, alpha=0.0):
        if alpha >= 1.0:
            self._animation_running = False
            return
        try:
            widget = self.tab(tab_name)
            widget.configure(fg_color=self._adjust_alpha(alpha))
        except tk.TclError:
            self._animation_running = False
            return
        self.after(20, lambda: self._fade_in(tab_name, alpha + 0.08))

    def _adjust_alpha(self, alpha):
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        base = colors.get("surface", "#0a1220")
        r = int(base[1:3], 16)
        g = int(base[3:5], 16)
        b = int(base[5:7], 16)
        ar = int(r * alpha)
        ag = int(g * alpha)
        ab = int(b * alpha)
        return f"#{ar:02x}{ag:02x}{ab:02x}"


class FollMuzGUI:
    def __init__(self):
        self.downloader = None
        self.config = config
        self.bypass_process = None
        
        # Запуск обхода
        if self.config.get("use_bypass", False):
            self.start_bypass()

        self.current_lang = self.config.get("language", "ru")

        self.is_downloading = False
        self.tray_icon = None
        self.tray_thread = None
        self.tray_modules = None
        self.is_tray_hidden = False
        self.is_quitting = False
        self.log_history = []
        self.audio_player_widget = None
        self.downloaded_file_path = None
        # Header auto-hide state
        self.header_visible = True
        self._header_hide_after = None

        self.window = ctk.CTk()
        self.window.withdraw()
        
        self.is_frameless = self.config.get("frameless_window", False)
        if self.is_frameless:
            self.window.overrideredirect(True)
        
        self.update_title()
        self.splash_started_at = time.monotonic()
        self.splash_window = None

        geometry = self.config.get_window_geometry()
        self.window.geometry(geometry)
        self.window.minsize(AppDimensions.WINDOW_MIN_WIDTH, AppDimensions.WINDOW_MIN_HEIGHT)

        # Иконка приложения
        if getattr(sys, 'frozen', False):
            # Если приложение скомпилировано в .exe
            icon_path = os.path.join(os.path.dirname(sys.executable), "icon.ico")
        else:
            # Если запущен обычный скрипт
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.ico")
        
        try:
            if os.path.exists(icon_path):
                self.window.iconbitmap(icon_path)
            else:
                print(f"Иконка не найдена по пути: {icon_path}")
        except Exception as e:
            print(f"Ошибка загрузки иконки: {e}")


        self.apply_theme()
        self.center_window()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.protocol("<<CloseWindow>>", self.on_closing)
        self.window.bind("<Configure>", self.on_window_resize)
        self.window.bind("<Unmap>", self.on_window_unmap)
        # Track mouse movement to auto-show/hide header
        self.window.bind("<Motion>", self._on_mouse_motion)

        # Привязка горячих клавиш для русской раскладки
        self.setup_keyboard_shortcuts()

        self.create_splash_screen()
        self.setup_ui()
        self.finish_splash_screen()

    def start_bypass(self):
        try:
            import subprocess
            import sys
            
            # Определяем корневую папку приложения для работы в .exe и в скрипте
            if getattr(sys, 'frozen', False):
                # Если запущено как скомпилированный файл (.exe)
                base_dir = os.path.dirname(sys.executable)
            else:
                # Если запущено как обычный скрипт
                base_dir = os.path.dirname(os.path.dirname(__file__))
            
            bypass_path = os.path.join(base_dir, "bypass", "general (ALT10).bat")
            
            # Проверяем существование файла перед запуском
            if not os.path.exists(bypass_path):
                self.window.after(0, lambda: self.log_message(f"Ошибка: файл обхода не найден по пути {bypass_path}"))
                return

            self.bypass_process = subprocess.Popen(
                [bypass_path],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                shell=True,
                cwd=os.path.join(base_dir, "bypass") # Устанавливаем рабочую директорию для .bat файла
            )
        except Exception as e:
            print(f"Ошибка запуска bypass: {e}")

    def stop_bypass(self):
        if self.bypass_process:
            try:
                self.bypass_process.terminate()
            except Exception:
                pass
            self.bypass_process = None
        import subprocess
        # Принудительное завершение winws.exe
        subprocess.run(["taskkill", "/F", "/IM", "winws.exe"], capture_output=True)

    def update_title(self):

        self.window.title(Translations.get_string("app_title", self.current_lang))

    def create_splash_screen(self):
        colors = AppColors.get_theme(self.config.get("theme", "dark") or "dark")
        splash = ctk.CTkToplevel(self.window)
        splash.overrideredirect(True)
        splash.attributes("-topmost", True)
        splash.geometry("560x260")
        splash.configure(fg_color=colors["bg"])

        width = 560
        height = 260
        x = (splash.winfo_screenwidth() // 2) - (width // 2)
        y = (splash.winfo_screenheight() // 2) - (height // 2)
        splash.geometry(f"{width}x{height}+{x}+{y}")

        outer = ctk.CTkFrame(splash, corner_radius=28, fg_color=colors["surface"], border_width=1, border_color=colors["border_strong"])
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        hero = ctk.CTkFrame(outer, corner_radius=24, fg_color=colors["card"], border_width=1, border_color=colors["border"])
        hero.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(hero, text="FollMuz", font=create_ctk_font("title"), text_color=colors["text"]).pack(anchor="center", pady=(42, 8))
        ctk.CTkLabel(hero, text="YouTube, playlist links and clean downloads", font=create_ctk_font("body"), text_color=colors["text_secondary"]).pack(anchor="center")

        progress = ctk.CTkProgressBar(hero, height=12, corner_radius=999, fg_color=colors["progress_track"], progress_color=colors["primary"])
        progress.pack(fill="x", padx=54, pady=(28, 8))
        progress.set(0.72)

        ctk.CTkLabel(hero, text="Preparing interface...", font=create_ctk_font("small"), text_color=colors["accent"]).pack(anchor="center")
        self.splash_window = splash

    def finish_splash_screen(self):
        elapsed_ms = int((time.monotonic() - self.splash_started_at) * 1000)
        delay = max(0, 3000 - elapsed_ms)

        def reveal():
            if self.splash_window is not None:
                try:
                    self.splash_window.destroy()
                except tk.TclError:
                    pass
                self.splash_window = None
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()

        self.window.after(delay, reveal)

    def setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш для русской и английской раскладки."""
        
        def handle_ctrl_key(event, action):
            """Обработка Ctrl+клавиша независимо от раскладки."""
            widget = self.window.focus_get()
            if widget:
                try:
                    widget.event_generate(action)
                except tk.TclError:
                    pass
            return "break"
        
        # Физические коды клавиш (не зависят от раскладки)
        # Windows VK codes: C=67, V=86, X=88, A=65, Z=90, Y=89
        key_actions = {
            67: "<<Copy>>",      # C / С
            88: "<<Cut>>",       # X / Ч
            65: "<<SelectAll>>", # A / Ф
            90: "<<Undo>>",      # Z / Я
            89: "<<Redo>>",      # Y / Н
        }
        
        def on_ctrl_press(event):
            """Перехват всех Ctrl+клавиша по keycode."""
            if event.state & 0x4:  # Ctrl нажат
                # Специальная обработка для V (Paste), если надо
                if event.keycode == 86:
                    return None # Позволяем дефолтную обработку
                
                action = key_actions.get(event.keycode)
                if action:
                    return handle_ctrl_key(event, action)
            return None
        
        # Привязываем по keycode через универсальный обработчик
        self.window.bind("<Control-KeyPress>", on_ctrl_press)
        
        # Дублируем стандартные привязки на случай если keycode не сработает
        try:
            self.window.bind("<Control-c>", lambda e: handle_ctrl_key(e, "<<Copy>>"))
            # Удаляем привязку для V, чтобы не дублировать
            self.window.bind("<Control-x>", lambda e: handle_ctrl_key(e, "<<Cut>>"))
            self.window.bind("<Control-a>", lambda e: handle_ctrl_key(e, "<<SelectAll>>"))
            self.window.bind("<Control-z>", lambda e: handle_ctrl_key(e, "<<Undo>>"))
            self.window.bind("<Control-y>", lambda e: handle_ctrl_key(e, "<<Redo>>"))
        except tk.TclError:
            pass

    def choose_download_folder(self, download_type="single"):
        """
        Выбор папки для загрузки.
        
        Args:
            download_type: 'single' для одиночных треков, 'playlist' для плейлистов
        
        Returns:
            str: Выбранный путь или None
        """
        lang = self.current_lang
        
        # Определяем заголовок и начальную папку
        if download_type == "playlist":
            title = "Выберите папку для плейлиста"
            initial_dir = self.config.get_playlist_download_path()
        else:
            title = "Выберите папку для треков"
            initial_dir = self.config.get_single_download_path()
        
        # Показываем диалог выбора папки
        folder = filedialog.askdirectory(
            title=title,
            initialdir=initial_dir if initial_dir and os.path.exists(initial_dir) else os.path.expanduser("~")
        )
        
        if folder:
            # Сохраняем выбранный путь
            if download_type == "playlist":
                self.config.set_playlist_download_path(folder)
            else:
                self.config.set_single_download_path(folder)
            
            self.log_message(f"Папка загрузки: {folder}")
            return folder
        
        return None

    def update_ui(self):
        current_url = self.url_entry.get() if hasattr(self, 'url_entry') else ""
        current_artist = self.artist_entry.get() if hasattr(self, 'artist_entry') else ""
        current_title = self.title_entry.get() if hasattr(self, 'title_entry') else ""

        for widget in self.window.winfo_children():
            widget.destroy()

        self.current_lang = self.config.get("language", "ru")
        self.update_title()
        self.setup_ui()

        if hasattr(self, 'url_entry') and current_url:
            self.url_entry.insert(0, current_url)
        if hasattr(self, 'artist_entry') and current_artist:
            self.artist_entry.insert(0, current_artist)
        if hasattr(self, 'title_entry') and current_title:
            self.title_entry.insert(0, current_title)

    def apply_theme(self):
        theme_name = self.config.get("theme", "dark")
        ctk.set_appearance_mode("dark" if theme_name == "dark" else "light")
        
        colors = AppColors.get_theme(theme_name)
        self.window.configure(fg_color=colors["bg"])
        
        if hasattr(self, 'sidebar'):
            self.sidebar.configure(fg_color=colors.get("sidebar_bg", colors["surface"]))
            self.sidebar._on_theme_changed(theme_name)
        
        self.refresh_theme()

    def center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def on_closing(self):
        if not self.is_quitting and self.config.get("minimize_to_tray", False):
            if self.minimize_to_tray():
                return

        self.quit_application()

    def quit_application(self):
        self.is_quitting = True
        self.config.save_window_geometry(self.window.geometry())
        self.stop_tray_icon()
        self.stop_bypass()
        self.window.destroy()


    def on_window_unmap(self, event):
        if event.widget != self.window:
            return
        if self.is_quitting or self.is_tray_hidden:
            return
        if not self.config.get("minimize_to_tray", False):
            return
        try:
            if self.window.state() == "iconic":
                self.window.after(0, self.minimize_to_tray)
        except tk.TclError:
            pass

    def on_window_resize(self, event):
        if event.widget == self.window:
            width = self.window.winfo_width()
            if hasattr(self, 'artist_entry'):
                if width > 1000:
                    self.artist_entry.configure(width=600)
                    self.title_entry.configure(width=600)
                elif width > 800:
                    self.artist_entry.configure(width=500)
                    self.title_entry.configure(width=500)
                else:
                    self.artist_entry.configure(width=400)
                    self.title_entry.configure(width=400)

    def open_settings(self):
        SettingsWindow(self.window, self.config, None, self.change_language)

    def change_theme(self, theme_name):
        self.apply_theme()
        self.refresh_theme()
    
    def refresh_theme(self):
        """Обновить тему всех виджетов без перезапуска."""
        theme_name = self.config.get("theme", "dark") or "dark"
        colors = AppColors.get_theme(theme_name)
        
        self.window.configure(fg_color=colors["bg"])
        
        if hasattr(self, 'sidebar'):
            self.sidebar._on_theme_changed(theme_name)
        
        if hasattr(self, 'single_frame'):
            self._refresh_frame_theme(self.single_frame, colors)
        if hasattr(self, 'playlist_frame'):
            self._refresh_frame_theme(self.playlist_frame, colors)
        if hasattr(self, 'player_instance'):
            self.player_instance.refresh_theme()
        
        if hasattr(self, 'url_entry'):
            self.url_entry.configure(**AppStyles.entry(colors))
        if hasattr(self, 'artist_entry'):
            self.artist_entry.configure(**AppStyles.entry(colors))
        if hasattr(self, 'title_entry'):
            self.title_entry.configure(**AppStyles.entry(colors))
        
        if hasattr(self, 'download_btn'):
            self.download_btn.configure(**AppStyles.primary_button(colors))
            AppEffects.bind_button(self.download_btn, colors, "primary")
    
    def _refresh_frame_theme(self, frame, colors):
        """Рекурсивно обновить тему виджетов в frame."""
        for widget in frame.winfo_children():
            try:
                widget_type = widget.winfo_class()
                if widget_type in ('CTkFrame', 'CTkLabel', 'CTkButton', 'CTkEntry'):
                    if hasattr(widget, 'configure'):
                        try:
                            widget.configure(fg_color=colors.get("card", colors["surface"]))
                        except:
                            pass
            except:
                pass

    def change_language(self, lang):
        self.update_ui()

    def get_downloader(self):
        """Возвращает экземпляр загрузчика."""
        if not hasattr(self, 'downloader') or self.downloader is None:
            from src.follmuz_downloader import FollMuzDownloader
            self.downloader = FollMuzDownloader(output_dir=self.config.get_single_download_path())
        return self.downloader


    def get_tray_modules(self):
        if self.tray_modules is None:
            try:
                import importlib
                pystray = importlib.import_module('pystray')
                from PIL import Image, ImageDraw
                self.tray_modules = (pystray, Image, ImageDraw)
            except ImportError:
                self.tray_modules = False
        return self.tray_modules

    def _setup_tray_double_click(self):
        """Setup double-click detection for tray icon."""
        self._tray_last_click_time = 0
        self._tray_double_click_ms = 500

    def _handle_tray_event(self, icon, method_name):
        """Handle tray click event with double-click detection."""
        import time
        current_time = time.time() * 1000
        time_diff = current_time - self._tray_last_click_time
        
        if time_diff < self._tray_double_click_ms:
            self._tray_last_click_time = 0
            self.window.after(0, self.restore_from_tray)
        else:
            self._tray_last_click_time = current_time

    def create_tray_image(self):
        _, Image, ImageDraw = self.get_tray_modules()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            return Image.open(icon_path)

        image = Image.new("RGBA", (64, 64), (59, 130, 246, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=14, fill=(139, 92, 246, 255))
        draw.polygon([(22, 18), (46, 32), (22, 46)], fill=(255, 255, 255, 255))
        return image

    def run_tray_icon(self):
        if self.tray_icon is None:
            return
        self.tray_icon.run()

    def ensure_tray_icon(self):
        if self.tray_icon is not None:
            return True

        modules = self.get_tray_modules()
        if not modules:
            return False

        pystray, _, _ = modules

        tr = Translations.get_string
        
        self._setup_tray_double_click()
        
        def on_tray_action(icon, item):
            self._handle_tray_event(icon, getattr(item, 'id', None))
        
        menu = pystray.Menu(
            pystray.MenuItem(tr("tray_show", self.current_lang), lambda icon, item: self.restore_from_tray()),
            pystray.MenuItem(tr("tray_exit", self.current_lang), lambda icon, item: self.exit_from_tray())
        )
        
        self.tray_icon = pystray.Icon(
            "follmuz",
            self.create_tray_image(),
            tr("app_title", self.current_lang),
            menu,
            on_click=on_tray_action
        )
        self.tray_thread = threading.Thread(target=self.run_tray_icon, daemon=True)
        self.tray_thread.start()
        return True

    def stop_tray_icon(self):
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
            self.tray_thread = None

    def minimize_to_tray(self):
        if self.is_tray_hidden:
            return True
        if not self.ensure_tray_icon():
            return False

        try:
            self.config.save_window_geometry(self.window.geometry())
        except tk.TclError:
            pass

        self.is_tray_hidden = True
        self.window.withdraw()
        return True

    def restore_from_tray(self):
        if not self.is_tray_hidden:
            return

        def restore():
            self.is_tray_hidden = False
            self.stop_tray_icon()
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()

        self.window.after(0, restore)

    def exit_from_tray(self):
        def close():
            self.is_tray_hidden = False
            self.quit_application()

        self.window.after(0, close)

    def setup_ui(self):
        lang = self.current_lang
        colors = AppColors.get_theme(self.config.get("theme", "dark") or "dark")

        self.setup_sidebar()

    def setup_sidebar(self):
        colors = AppColors.get_theme(self.config.get("theme", "dark") or "dark")

        self.main_container = ctk.CTkFrame(self.window, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        from src.ui.sidebar import Sidebar
        self.sidebar = Sidebar(
            self.main_container,
            on_item_selected=self._on_sidebar_select,
            current_theme=self.config.get("theme", "dark"),
            is_frameless=self.is_frameless,
            window=self.window
        )

        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.pack(side="left", fill="both", expand=True)

        self.single_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.playlist_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.player_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        self._setup_single_tab(self.single_frame)
        self._setup_playlist_tab(self.playlist_frame)
        self._setup_audio_player_tab(self.player_frame)

        self.window.update_idletasks()
        self._show_frame("single")

    def _show_frame(self, frame_name):
        frames = {
            "single": self.single_frame,
            "playlist": self.playlist_frame,
            "player": self.player_frame,
        }
        for name, frame in frames.items():
            if name == frame_name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        if frame_name == "player":
            if hasattr(self, 'player_instance') and hasattr(self.player_instance, 'on_activate'):
                self.player_instance.on_activate()

    def _on_sidebar_select(self, item_key):
        self._show_frame(item_key)

    def _setup_single_tab(self, frame):
        lang = self.current_lang
        colors = AppColors.get_theme(self.config.get("theme", "dark") or "dark")

        frame.configure(corner_radius=20, **AppStyles.panel(colors, "card"))
        frame.grid_columnconfigure((0, 1), weight=1)
        frame.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(
            frame,
            text="Ссылка (YouTube):",
            font=create_ctk_font("body"),
            text_color=colors["text_secondary"]
        ).grid(row=0, column=0, columnspan=2, pady=(28, 5), padx=20, sticky="w")

        self.url_entry = ctk.CTkEntry(
            frame,
            height=AppDimensions.ENTRY_HEIGHT,
            placeholder_text="https://youtube.com/watch?v=...",
            corner_radius=10,
            font=create_ctk_font("body"),
            **AppStyles.entry(colors)
        )
        self.url_entry.grid(row=1, column=0, columnspan=2, pady=5, padx=20, sticky="ew")

        ctk.CTkLabel(
            frame,
            text="Исполнитель:",
            font=create_ctk_font("body"),
            text_color=colors["text_secondary"]
        ).grid(row=2, column=0, columnspan=2, pady=(15, 5), padx=20, sticky="w")

        self.artist_entry = ctk.CTkEntry(
            frame,
            height=AppDimensions.ENTRY_HEIGHT,
            placeholder_text="Например: Miyagi",
            corner_radius=10,
            font=create_ctk_font("body"),
            **AppStyles.entry(colors)
        )
        self.artist_entry.grid(row=3, column=0, columnspan=2, pady=5, padx=20, sticky="ew")

        ctk.CTkLabel(
            frame,
            text="Название трека:",
            font=create_ctk_font("body"),
            text_color=colors["text_secondary"]
        ).grid(row=4, column=0, columnspan=2, pady=(15, 5), padx=20, sticky="w")

        self.title_entry = ctk.CTkEntry(
            frame,
            height=AppDimensions.ENTRY_HEIGHT,
            placeholder_text="Например: Тамада",
            corner_radius=10,
            font=create_ctk_font("body"),
            **AppStyles.entry(colors)
        )
        self.title_entry.grid(row=5, column=0, columnspan=2, pady=5, padx=20, sticky="ew")

        self.download_btn = ctk.CTkButton(
            frame,
            text="🚀 Скачать",
            height=AppDimensions.BUTTON_HEIGHT,
            corner_radius=12,
            font=create_ctk_font("body", weight="bold"),
            **AppStyles.primary_button(colors),
            command=self.start_single_download
        )
        self.download_btn.grid(row=6, column=0, columnspan=2, pady=30, padx=20, sticky="ew")
        AppEffects.bind_button(self.download_btn, colors, "primary")

        self.progress_label = SimpleProgressLabel(frame)
        self.progress_label.grid(row=7, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        self.progress_label.grid_remove()

    def _setup_playlist_tab(self, frame):
        lang = self.current_lang
        colors = AppColors.get_theme(self.config.get("theme", "dark") or "dark")

        frame.configure(corner_radius=20, **AppStyles.panel(colors, "card"))
        frame.pack_propagate(False)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        ctk.CTkLabel(
            header,
            text="📋 Плейлист",
            font=create_ctk_font("header", weight="bold"),
            text_color=colors["text"]
        ).pack(side="left")

        self.playlist_count_label = ctk.CTkLabel(
            header,
            text="0 треков",
            font=create_ctk_font("small"),
            text_color=colors["text_secondary"]
        )
        self.playlist_count_label.pack(side="right")

        file_card = ctk.CTkFrame(frame, corner_radius=16, **AppStyles.panel(colors, "card_alt"))
        file_card.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        file_card.grid_columnconfigure(0, weight=1)

        scroll_frame = ctk.CTkScrollableFrame(
            file_card,
            fg_color="transparent",
            scrollbar_button_color=colors["scrollbar"],
            scrollbar_button_hover_color=colors["scrollbar_hover"]
        )
        scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scroll_frame.grid_columnconfigure(0, weight=1)

        self.playlist_items = []
        self.playlist_scroll_frame = scroll_frame
        self.playlist_content_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        self.playlist_content_frame.grid(row=0, column=0, sticky="nsew")
        self.playlist_content_frame.grid_columnconfigure(0, weight=1)

        button_frame = ctk.CTkFrame(file_card, fg_color="transparent", height=50)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 10))
        button_frame.grid_propagate(False)

        add_btn = ctk.CTkButton(
            button_frame,
            text="➕ Добавить",
            width=120,
            height=36,
            corner_radius=10,
            font=create_ctk_font("small"),
            **AppStyles.secondary_button(colors),
            command=self._show_add_playlist_dialog
        )
        add_btn.pack(side="left", padx=5)

        remove_btn = ctk.CTkButton(
            button_frame,
            text="➖ Удалить",
            width=120,
            height=36,
            corner_radius=10,
            font=create_ctk_font("small"),
            **AppStyles.secondary_button(colors),
            command=self.remove_playlist_item
        )
        remove_btn.pack(side="left", padx=5)

        self.download_playlist_btn = ctk.CTkButton(
            button_frame,
            text="📥 Скачать плейлист",
            height=36,
            corner_radius=10,
            font=create_ctk_font("small", weight="bold"),
            **AppStyles.primary_button(colors),
            command=self.start_playlist_download
        )
        self.download_playlist_btn.pack(side="right", padx=5)

        self.playlist_progress_label = PlaylistProgressLabel(frame)
        self.playlist_progress_label.grid(row=2, column=0, pady=(0, 10), padx=20, sticky="ew")
        self.playlist_progress_label.grid_remove()

    def _show_add_playlist_dialog(self):
        from src.ui.playlist_add_dialog import PlaylistAddDialog
        dialog = PlaylistAddDialog(self.window, on_tracks_added=self._on_playlist_tracks_added)

    def _on_playlist_tracks_added(self, tracks):
        for track in tracks:
            artist = self.clean_input(track.get('artist', ''))
            title = self.clean_input(track.get('title', ''))
            if artist and title:
                self._add_playlist_row(artist, title)
        self.log_message(f"Добавлено треков: {len(tracks)}")

    def _setup_audio_player_tab(self, frame):
        from src.ui.audio_player import AudioPlayerTab
        
        self.player_instance = AudioPlayerTab(frame, on_log_message=self.log_message)
        self.player_instance.pack(fill="both", expand=True)

    def log_message(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.log_history.append(entry)
        self.log_history = self.log_history[-300:]
        print(entry)
        self.window.update_idletasks()

    def _on_mouse_motion(self, event):
        header_h = AppDimensions.HEADER_HEIGHT
        try:
            if event.y <= header_h:
                self.show_header()
            else:
                if self._header_hide_after is None and self.header_visible:
                    self._header_hide_after = self.window.after(800, self.hide_header)
        except Exception:
            pass

    def show_header(self):
        if not hasattr(self, "header_frame"):
            return
        if not self.header_visible:
            try:
                if self._header_hide_after:
                    self.window.after_cancel(self._header_hide_after)
                    self._header_hide_after = None
                self.header_frame.pack(fill="x", padx=AppDimensions.PADDING_LARGE, pady=(10, 0))
            except Exception:
                pass
            self.header_visible = True

    def hide_header(self):
        if not hasattr(self, "header_frame"):
            return
        if self.header_visible:
            try:
                self.header_frame.pack_forget()
            except Exception:
                pass
            self.header_visible = False
            self._header_hide_after = None

    def start_single_download(self):
        if self.is_downloading:
            return

        # Проверяем папку загрузки
        save_path = self.config.get_single_download_path()
        if not save_path or not os.path.exists(save_path):
            save_path = self.choose_download_folder("single")
            if not save_path:
                return

        url = self.url_entry.get().strip()
        if url:
            # Определяем тип ссылки
            if 'youtube.com' in url or 'youtu.be' in url:
                self.download_by_url(url, 'youtube')
                return
            elif 'music.yandex.ru' in url:
                self.download_by_url(url, 'yandex')
                return

        artist = self.clean_input(self.artist_entry.get())
        title = self.clean_input(self.title_entry.get())

        if not artist or not title:
            messagebox.showerror(
                Translations.get_string("error_title", self.current_lang),
                Translations.get_string("error_empty_fields", self.current_lang)
            )
            return

        query = f"{artist} - {title}"
        TrackVariantSelector(
            self.window,
            artist,
            title,
            self.download_selected_variant,
            lang=self.current_lang
        )

    def clean_input(self, text: str) -> str:
        """Очищает спецсимволы из имени артиста и названия трека."""
        if not text:
            return text
        
        # Удаляем эмодзи и спецсимволы Unicode (BMP plane)
        text = re.sub(r'[\u2600-\u26FF\u2700-\u27BF]', '', text)
        
        # Удаляем эмодзи (supplementary planes)
        text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
        text = re.sub(r'[\U0001FA00-\U0001FAFF]', '', text)
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)
        text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)
        text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)
        text = re.sub(r'[\U00002702-\U000027B0]', '', text)
        text = re.sub(r'[\U0000FE00-\U0000FE0F]', '', text)
        
        # Удаляем символы валют (включая $ € £ ¥ ₽)
        text = re.sub(r'[\$\u20A0-\u20CF]', '', text)
        
        # Удаляем стрелки
        text = re.sub(r'[\u2190-\u21FF]', '', text)
        
        # Удаляем геометрические фигуры
        text = re.sub(r'[\u25A0-\u25FF]', '', text)
        
        # Удаляем музыкальные символы
        text = re.sub(r'[\u2669-\u266F]', '', text)
        text = re.sub(r'[\U0001D100-\U0001D1FF]', '', text)
        
        # Удаляем звёздочки, сердечки и декоративные символы
        text = re.sub(r'[\u2605-\u2606\u2665-\u2666\u2764-\u2767\u2728\u272A-\u2730\u2733-\u2747\u2749-\u274C\u274E-\u2757\u2763-\u2767]', '', text)
        
        # Удаляем невидимые символы и управляющие коды
        text = re.sub(r'[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u2028-\u202F\u205F-\u206F\uFEFF]', '', text)
        
        # Удаляем комбинированные диакритические знаки
        text = re.sub(r'[\u0300-\u036F\u1AB0-\u1AFF\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]', '', text)
        
        # Удаляем псевдографику
        text = re.sub(r'[\u2500-\u257F]', '', text)
        
        # Удаляем технические символы
        text = re.sub(r'[\u2300-\u23FF]', '', text)
        
        # Удаляем спецсимволы поиска и пунктуации: # @ ^ ? ! ~ ` \ | /
        text = re.sub(r'[#@^?!~`\\|]', '', text)
        
        # Удаляем кавычки разных типов
        text = re.sub(r'[""„""]', '', text)
        text = re.sub(r"[''']", '', text)
        
        # Удаляем паттерны like (feat. x) или [feat x] но оставляем feat
        text = re.sub(r'[\(\[\{][^\)\]\}]*?(feat|featuring|ft)[\s.]*([^\)\]\}]*?)[\)\]\}]', r' \1 \2 ', text, flags=re.IGNORECASE)
        
        # Удаляем оставшиеся скобки и угловые скобки
        text = re.sub(r'[\(\)\[\]\{\}<>]', ' ', text)
        
        # Удаляем повторяющиеся дефисы и точки
        text = re.sub(r'[-_.]{2,}', ' ', text)
        
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def download_by_url(self, url, platform='youtube'):
        """Скачивание трека по ссылке (YouTube, VK, Spotify)."""
        self.show_progress_mode()
        thread = threading.Thread(target=self._download_url_thread, args=(url, platform))
        thread.daemon = True
        thread.start()

    def _download_url_thread(self, url, platform='youtube'):
        """Поток для скачивания по ссылке."""
        try:
            save_path = self.config.get_single_download_path()
            
            # Проверяем папку загрузки
            if not save_path or not os.path.exists(save_path):
                save_path = self.choose_download_folder("single")
                if not save_path:
                    return

            if platform == 'youtube':
                self._download_youtube(url, save_path)
            else:
                self.window.after(0, lambda: self.log_message(f"Неизвестная или неподдерживаемая платформа: {platform}"))
                self.window.after(0, self.hide_progress_mode)
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Ошибка: {e}"))
            self.window.after(0, self.hide_progress_mode)

        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Ошибка: {e}"))
            self.window.after(0, self.hide_progress_mode)

    def _download_youtube(self, url, save_path):
        """Скачивание с YouTube."""
        try:
            import yt_dlp

            # Лучшие доступные форматы для максимального качества
            format_candidates = [
                'bestaudio/best',
                'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
                'bestaudio*',
            ]
            
            last_error = None
            downloaded = False
            
            # Получаем настройки качества из конфига
            quality = self.config.get("mp3_quality", "320")
            channels = self.config.get("audio_channels", "stereo")
            
            # Мапинг каналов для FFmpeg
            channel_map = {
                "stereo": "2",
                "mono": "1",
                "joint_stereo": "2",
                "dual_mono": "2"
            }
            ac_value = channel_map.get(channels.lower(), "2")
            
            for format_name in format_candidates:
                ydl_opts = {
                    'format': format_name,
                    'format_sort': ['bestaudio', 'best'],
                    'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality,
                    }],
                    'postprocessor_args': [
                        '-ac', ac_value
                    ],
                    'quiet': True,
                    'no_warnings': True,
                    'retries': 5,
                    'fragment_retries': 5,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios', 'android', 'web'],
                        }
                    },
                }

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)
                        for ext in ['.webm', '.m4a', '.ogg']:
                            if filename.endswith(ext):
                                filename = filename[:-len(ext)] + '.mp3'
                                break
                        self.window.after(0, lambda: self.log_message(f"Скачано ({quality}kbps, {channels}): {os.path.basename(filename)}"))
                    downloaded = True
                    break
                except Exception as e:
                    last_error = e
                    self.window.after(0, lambda: self.log_message(f"Формат {format_name} не удался, пробую другой..."))
                    continue
            
            if downloaded:
                self.window.after(0, lambda: self.progress_label.set_progress(100))
                self.window.after(2000, self.hide_progress_mode)
            else:
                self.window.after(0, lambda: self.log_message(f"Ошибка: {last_error}"))
                self.window.after(0, self.hide_progress_mode)
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Ошибка: {e}"))
            self.window.after(0, self.hide_progress_mode)

        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Ошибка: {e}"))
            self.window.after(0, self.hide_progress_mode)

    def _download_vk(self, url, save_path):
        """Скачивание с VK."""
        try:
            # VK support removed
            self.window.after(0, lambda: self.log_message("Поддержка VK временно недоступна. Пожалуйста, введите название трека вручную."))
            self.window.after(0, self.hide_progress_mode)
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Ошибка VK: {e}"))
            self.window.after(0, self.hide_progress_mode)

    def _download_mts(self, url, save_path):
        """Скачивание с MTS Music."""
        try:
            self.log_message(f"Получение информации из MTS Music: {url}")
            downloader = self.get_downloader()
            success, result = downloader.download_by_url(url, save_path)
            
            if success:
                self.window.after(0, lambda: self.log_message(f"✅ Скачано: {os.path.basename(result)}"))
                self.window.after(0, lambda: self.progress_label.set_progress(100))
                self.window.after(2000, self.hide_progress_mode)
            elif result == "captcha":
                self.window.after(0, lambda: self.log_message("❌ Сервис MTS заблокировал запрос (капча). Пожалуйста, введите название трека вручную."))
                self.window.after(0, self.hide_progress_mode)
            else:
                self.window.after(0, lambda: self.log_message(f"❌ Ошибка MTS: {result}"))
                self.window.after(0, self.hide_progress_mode)
                
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Критическая ошибка MTS: {e}"))
            self.window.after(0, self.hide_progress_mode)

    def _download_yandex(self, url, save_path):
        """Скачивание с Yandex Music."""
        try:
            self.log_message(f"Получение информации из Yandex Music: {url}")
            downloader = self.get_downloader()
            success, result = downloader.download_by_url(url, save_path)
            
            if success:
                self.window.after(0, lambda: self.log_message(f"✅ Скачано: {os.path.basename(result)}"))
                self.window.after(0, lambda: self.progress_label.set_progress(100))
                self.window.after(2000, self.hide_progress_mode)
            elif result == "captcha":
                self.window.after(0, lambda: self.log_message("❌ Яндекс Музыка заблокировала запрос (капча). Пожалуйста, введите название трека вручную."))
                self.window.after(0, self.hide_progress_mode)
            else:
                self.window.after(0, lambda: self.log_message(f"❌ Ошибка Yandex: {result}"))
                self.window.after(0, self.hide_progress_mode)
                
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Критическая ошибка Yandex: {e}"))
            self.window.after(0, self.hide_progress_mode)

    def _download_spotify(self, url, save_path):
        """Скачивание с Spotify (извлекает метаданные, ищет на YouTube)."""
        try:
            self.log_message(f"Получение информации о треке: {url}")
            
            # Используем наш новый FollMuzDownloader
            downloader = self.get_downloader()
            success, result = downloader.download_spotify_track(url, save_path)
            
            if success:
                self.window.after(0, lambda: self.log_message(f"✅ Скачано: {os.path.basename(result)}"))
                self.window.after(0, lambda: self.progress_label.set_progress(100))
                self.window.after(2000, self.hide_progress_mode)
            else:
                self.window.after(0, lambda: self.log_message(f"❌ Ошибка Spotify: {result}"))
                self.window.after(0, self.hide_progress_mode)
                
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Критическая ошибка Spotify: {e}"))
            self.window.after(0, self.hide_progress_mode)

    def _search_and_download_youtube(self, artist, title, save_path):
        """Ищет трек на YouTube и скачивает."""
        try:
            from src.api.youtube_client import YouTubeClient
            from src.exceptions import SearchError
            
            client = YouTubeClient()
            try:
                search_result = client.search_track(artist, title)
            except SearchError:
                self.window.after(0, lambda: self.log_message(f"Не найдено: {artist} - {title}"))
                self.window.after(0, self.hide_progress_mode)
                return
            
            # Проверяем что результат - словарь (не список)
            if search_result and isinstance(search_result, dict) and search_result.get('webpage_url'):
                self.window.after(0, lambda: self.log_message(f"Найдено: {search_result.get('title', '')}"))
                try:
                    filepath = client.download_track(search_result, save_path)
                    self.window.after(0, lambda: self.log_message(f"Скачано: {os.path.basename(filepath)}"))
                    self.window.after(0, lambda: self.progress_label.set_progress(100))
                    self.window.after(2000, self.hide_progress_mode)
                except Exception as e:
                    self.window.after(0, lambda: self.log_message(f"Ошибка скачивания: {e}"))
                    self.window.after(0, self.hide_progress_mode)
            else:
                self.window.after(0, lambda: self.log_message(f"Не найдено: {artist} - {title}"))
                self.window.after(0, self.hide_progress_mode)
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Ошибка поиска: {e}"))
            self.window.after(0, self.hide_progress_mode)

    def _download_spotify_playlist(self, tracks, save_path):
        """Скачивает плейлист из Spotify."""
        try:
            from src.follmuz_downloader import FollMuzDownloader
            
            downloader = FollMuzDownloader()
            total = len(tracks)
            
            self.window.after(0, lambda: self.show_playlist_progress())
            self.window.after(0, lambda: self.playlist_progress_label.set_total(total))
            
            for i, track in enumerate(tracks):
                artist = track.get('artist', '')
                title = track.get('title', '')
                
                self.window.after(0, lambda a=artist, t=title: self.playlist_progress_label.set_current_track(a, t))
                self.window.after(0, lambda idx=i+1, tot=total: self.playlist_progress_label.set_status(f"Завершено: {idx}/{tot}"))
                
                self.log_message(f"[{i+1}/{total}] {artist} - {title}")
                
                try:
                    from src.api.youtube_client import YouTubeClient
                    from src.exceptions import SearchError
                    
                    client = YouTubeClient()
                    try:
                        search_result = client.search_track(artist, title)
                    except SearchError:
                        self.log_message(f"  ❌ Не найдено")
                        continue
                    
                    if search_result and isinstance(search_result, dict) and search_result.get('webpage_url'):
                        filepath = client.download_track(search_result, save_path)
                        self.log_message(f"  ✅ {os.path.basename(filepath)}")
                    else:
                        self.log_message(f"  ❌ Не найдено")
                except Exception as e:
                    self.log_message(f"  ❌ {e}")
                
                self.window.after(0, lambda: self.playlist_progress_label.track_done())
            
            self.window.after(0, lambda: self.playlist_progress_label.stop())
            self.window.after(3000, lambda: self.hide_playlist_progress())
            self.log_message(f"Плейлист Spotify завершён: {total} треков")
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"Ошибка плейлиста Spotify: {e}"))
            self.window.after(0, self.hide_playlist_progress)

    def download_selected_variant(self, variant_data):
        """Скачивание выбранного варианта трека."""
        print(f"DEBUG: Selected variant: {variant_data}")

        artist = variant_data.get("artist", "")
        title = variant_data.get("title", "")
        modification = variant_data.get("modification", "")
        
        # Проверяем папку загрузки
        save_path = self.config.get_single_download_path()
        if not save_path or not os.path.exists(save_path):
            save_path = self.choose_download_folder("single")
            if not save_path:
                return

        print(f"DEBUG: Starting download - artist: {artist}, title: {title}, modification: {modification}")

        self.show_progress_mode()

        thread = threading.Thread(
            target=self.perform_download,
            args=(artist, title, save_path, modification)
        )
        thread.daemon = True
        thread.start()

    def perform_download(self, artist, title, save_path, modification):
    
        lang = self.current_lang
        self.is_downloading = True
    
        def _progress_cb(pct, msg):
            self.window.after(0, lambda: self.progress_label.set_progress(pct))
            self.window.after(0, lambda: self.progress_label.set_status_text(msg))
    
        try:
            full_title = f"{artist} - {title}"
            if modification:
                full_title += f" ({modification})"
            self.log_message(f"🔍 Поиск: {full_title}")
        
            self.progress_label.set_progress(5)
            self.progress_label.set_status_text("Поиск на YouTube...")
            self.window.update()
        
            success = self.get_downloader().search_and_download(
                artist=artist,
                title=title,
                save_path=save_path,
                modification=modification,
                progress_callback=_progress_cb,
            )
        
            self.progress_label.set_progress(100)
            self.window.update()
            
            if success and isinstance(success, tuple):
                filepath = success[1]
                self.log_message(
                    f"✅ {Translations.get_string('download_success', lang).format(artist, title)}"
                )
                if filepath and hasattr(self, 'audio_player'):
                    self.audio_player.load_track(filepath, artist, title)
                    self.audio_player.play()
            elif success:
                self.log_message(
                    f"✅ {Translations.get_string('download_success', lang).format(artist, title)}"
                )
            else:
                self.log_message(
                    f"❌ {Translations.get_string('download_error', lang).format(artist, title)}"
                )
        
            # Возвращаемся в обычный режим через 2 секунды
            self.window.after(2000, self.hide_progress_mode)
        
        except Exception as e:
            self.log_message(f"❌ Ошибка: {e}")
            self.hide_progress_mode()
        finally:
            self.is_downloading = False

    def show_progress_mode(self):
        self.progress_label.grid()
        self.progress_label.start()
        if hasattr(self, 'download_btn'):
            self.download_btn.configure(state="disabled")

    def hide_progress_mode(self):
        self.progress_label.grid_remove()
        self.progress_label.stop()
        if hasattr(self, 'download_btn'):
            self.download_btn.configure(state="normal")

    def show_playlist_progress(self):
        """Показать прогресс-бар плейлиста."""
        self.playlist_progress_label.grid()
        self.playlist_progress_label.start()

    def hide_playlist_progress(self):
        """Скрыть прогресс-бар плейлиста."""
        self.playlist_progress_label.grid_remove()
        self.playlist_progress_label.stop()

    def add_playlist_item(self):
        colors = AppColors.get_theme(self.config.get("theme", "dark") or "dark")
        
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Добавить трек")
        dialog.geometry("500x250")
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        
        dialog.configure(fg_color=colors["bg"])
        
        ctk.CTkLabel(dialog, text="Исполнитель:", font=create_ctk_font("body"), text_color=colors["text"]).pack(pady=(20, 5), padx=20, anchor="w")
        artist_entry = ctk.CTkEntry(dialog, height=AppDimensions.ENTRY_HEIGHT, corner_radius=10, font=create_ctk_font("body"), **AppStyles.entry(colors))
        artist_entry.pack(pady=(0, 10), padx=20, fill="x")
        artist_entry.focus()
        
        ctk.CTkLabel(dialog, text="Название трека:", font=create_ctk_font("body"), text_color=colors["text"]).pack(pady=(0, 5), padx=20, anchor="w")
        title_entry = ctk.CTkEntry(dialog, height=AppDimensions.ENTRY_HEIGHT, corner_radius=10, font=create_ctk_font("body"), **AppStyles.entry(colors))
        title_entry.pack(pady=(0, 15), padx=20, fill="x")
        
        def save():
            artist = self.clean_input(artist_entry.get())
            title = self.clean_input(title_entry.get())
            if artist and title:
                self._add_playlist_row(artist, title)
                dialog.destroy()
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=(0, 15), padx=20, fill="x")
        
        ctk.CTkButton(btn_frame, text="Отмена", width=100, height=36, corner_radius=10, font=create_ctk_font("body"), **AppStyles.secondary_button(colors), command=dialog.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Добавить", width=100, height=36, corner_radius=10, font=create_ctk_font("body", weight="bold"), **AppStyles.primary_button(colors), command=save).pack(side="right", padx=5)
        
        dialog.bind("<Return>", lambda e: save())
        
        x = self.window.winfo_x() + (self.window.winfo_width() // 2) - 250
        y = self.window.winfo_y() + (self.window.winfo_height() // 2) - 125
        dialog.geometry(f"500x250+{x}+{y}")

    def _add_playlist_row(self, artist, title):
        colors = AppColors.get_theme(self.config.get("theme", "dark") or "dark")
        
        self.playlist_items.append({"artist": artist, "title": title, "selected": tk.BooleanVar(value=True)})
        
        row = ctk.CTkFrame(self.playlist_content_frame, corner_radius=14, **AppStyles.panel(colors, "card_alt"))
        row.pack(fill="x", pady=4, padx=2)
        
        text = f"{artist} - {title}"
        idx = len(self.playlist_items) - 1
        
        chk = ctk.CTkCheckBox(
            row,
            text=text,
            variable=self.playlist_items[idx]["selected"],
            font=create_ctk_font("body"),
            **AppStyles.checkbox(colors)
        )
        chk.pack(side="left", padx=12, pady=10)
        
        if hasattr(self, 'playlist_count_label'):
            self.playlist_count_label.configure(text=f"{len(self.playlist_items)} треков")

    def remove_playlist_item(self):
        for i in range(len(self.playlist_items) - 1, -1, -1):
            if not self.playlist_items[i]["selected"].get():
                del self.playlist_items[i]
        
        for widget in self.playlist_content_frame.winfo_children():
            widget.destroy()
        
        for item in self.playlist_items:
            self._add_playlist_row(item["artist"], item["title"])

    def load_playlist_from_file(self):
        file = filedialog.askopenfilename(
            title="Выберите файл плейлиста",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file:
            return
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '|' in line:
                        parts = [part.strip() for part in line.split('|')]
                        if len(parts) >= 2:
                            artist = self.clean_input(parts[0])
                            title = self.clean_input(parts[1])
                            if artist and title:
                                self._add_playlist_row(artist, title)
            self.log_message(f"Загружено треков: {len(self.playlist_items)}")
        except Exception as e:
            self.log_message(f"Ошибка чтения файла: {e}")

    def start_playlist_download(self):
        if not self.playlist_items:
            messagebox.showwarning("Пустой плейлист", "Добавьте треки в плейлист перед скачиванием.")
            return
        
        save_path = self.config.get_playlist_download_path()
        if not save_path or not os.path.exists(save_path):
            save_path = self.choose_download_folder("playlist")
            if not save_path:
                return
        
        self.download_playlist_btn.configure(state="disabled", text="Загрузка...")
        self.log_message(f"Начало скачивания плейлиста ({len(self.playlist_items)} треков)")
        
        thread = threading.Thread(target=self._playlist_download_thread, args=(save_path,))
        thread.daemon = True
        thread.start()

    def _playlist_download_thread(self, save_path):
        lang = self.current_lang
        tr = Translations.get_string
        playlist_tracks = [{"artist": item["artist"], "title": item["title"], "modification": ""} for item in self.playlist_items]

        self.window.after(0, lambda: self.show_playlist_progress())
        self.window.after(0, lambda: self.playlist_progress_label.set_total(len(playlist_tracks)))

        successful = 0

        def on_track_done(index, total, track, success):
            nonlocal successful
            self.log_message(tr("playlist_progress", lang).format(index, total, track["artist"], track["title"]))
            if success:
                successful += 1
                self.log_message("  ✅")
            else:
                self.log_message("  ❌")
            
            self.window.after(0, lambda: self.playlist_progress_label.set_current_track(track["artist"], track["title"]))
            self.window.after(0, lambda: self.playlist_progress_label.track_done(success))
            self.window.after(0, lambda: self.playlist_progress_label.set_status(f"Завершено: {index}/{total}"))

        def on_track_progress(index, total, pct, msg):
            self.window.after(0, lambda: self.playlist_progress_label.set_track_progress(pct, msg))

        self.get_downloader().download_tracks_batch(
            playlist_tracks,
            save_path=save_path,
            callback=on_track_done,
            progress_callback=on_track_progress,
            search_workers=6,
            download_workers=3,
        )

        self.window.after(0, lambda: self.playlist_progress_label.stop())
        self.window.after(3000, lambda: self.hide_playlist_progress())

        self.log_message(tr("playlist_complete", lang).format(successful, len(playlist_tracks)))
        self.window.after(0, lambda: self.download_playlist_btn.configure(state="normal", text="📥 Скачать плейлист"))


def main():
    app = FollMuzGUI()
    app.window.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Ошибка GUI: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")
