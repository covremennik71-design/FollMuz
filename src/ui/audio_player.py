# src/ui/audio_player.py
"""Аудио плеер для прослушивания скачанных треков."""

import os
import threading
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from mutagen.mp3 import MP3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

import shutil

FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg"))

PYDUB_AVAILABLE = False
try:
    from pydub import AudioSegment
    if FFMPEG_AVAILABLE:
        AudioSegment.converter = shutil.which("ffmpeg")
    PYDUB_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYDUB_AVAILABLE = False

try:
    import simpleaudio as sa
    SIMPLEAUDIO_AVAILABLE = True
except ImportError:
    SIMPLEAUDIO_AVAILABLE = False

PYGAME_AVAILABLE = False
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except Exception:
    PYGAME_AVAILABLE = False

from src.styles import AppColors, AppStyles, AppDimensions
from src.utils import create_ctk_font
from src.config import config


class AudioPlayerTab(ctk.CTkFrame):
    def __init__(self, master, on_log_message=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.on_log_message = on_log_message or (lambda x: None)
        self.current_playlist = []
        self.current_track_index = -1
        self.play_obj = None
        self.is_playing = False
        self.is_paused = False
        self.current_thread = None
        self.current_thread_id = None
        self.stop_playback_flag = False
        self.pause_playback_flag = False
        self.pause_event = threading.Event()
        self._progress_thread = None
        self._stop_progress = threading.Event()
        self.duration = 0.0
        self.current_position = 0.0
        self.stopped_position = 0.0
        self.track_start_position = 0.0
        self._seek_pending = False
        self._first_activation = True
        
        # Volume and Playback settings
        from src.config import config
        self._volume = config.get("player_volume", 0.8)
        self.repeat_mode = "ORDER"  # ORDER, RANDOM, LIST, TRACK
        self.autoplay = True
        # EQ settings removed
        
        
        if PYGAME_AVAILABLE:
            self.on_log_message("🎵 pygame готов")
        elif PYDUB_AVAILABLE and FFMPEG_AVAILABLE:
            self.on_log_message("🎵 pydub + ffmpeg готов")
        elif SIMPLEAUDIO_AVAILABLE:
            self.on_log_message("🎵 simpleaudio готов")
        else:
            self.on_log_message("⚠️ Не установлен ни один плеер")
        
        self.setup_ui()
        self.refresh_playlist()
        self._start_media_listener()


    def setup_ui(self):
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        main_frame = ctk.CTkFrame(self, corner_radius=20, **AppStyles.panel(colors, "card"))
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text="🎧 Аудио плеер",
            font=create_ctk_font("header", weight="bold"),
            text_color=colors["text"]
        )
        title_label.grid(row=0, column=0, pady=(15, 5), padx=15, sticky="w")
        
        list_frame = ctk.CTkFrame(main_frame, corner_radius=12, **AppStyles.panel(colors, "card_alt"))
        list_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        scroll_frame = ctk.CTkScrollableFrame(
            list_frame,
            fg_color="transparent",
            scrollbar_button_color=colors["scrollbar"],
            scrollbar_button_hover_color=colors["scrollbar_hover"]
        )
        scroll_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        self.track_buttons = []
        self.track_labels = []
        self.track_list_frame = scroll_frame
        
        controls_frame = ctk.CTkFrame(list_frame, corner_radius=8, fg_color=colors["surface"])
        controls_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(5, 8))
        
        refresh_btn = ctk.CTkButton(
            controls_frame,
            text="🔄",
            width=40,
            height=36,
            corner_radius=8,
            font=("Arial", 16),
            **AppStyles.secondary_button(colors),
            command=self.refresh_playlist
        )
        refresh_btn.pack(side="left", padx=(0, 5), pady=5)
        
        open_folder_btn = ctk.CTkButton(
            controls_frame,
            text="📂",
            width=40,
            height=36,
            corner_radius=8,
            font=("Arial", 16),
            **AppStyles.secondary_button(colors),
            command=self.open_download_folder
        )
        open_folder_btn.pack(side="left", padx=5, pady=5)
        
        self.track_count_label = ctk.CTkLabel(
            controls_frame,
            text="0 треков",
            font=create_ctk_font("small"),
            text_color=colors["text_secondary"]
        )
        self.track_count_label.pack(side="right", padx=5, pady=5)
        
        self.player_frame = ctk.CTkFrame(main_frame, corner_radius=16, **AppStyles.panel(colors, "card"))
        self.player_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.player_frame.grid_columnconfigure(0, weight=1)
        
        player_frame = self.player_frame
        
        self.now_playing_label = ctk.CTkLabel(
            player_frame,
            text="Ничего не воспроизводится",
            font=create_ctk_font("body", weight="bold"),
            text_color=colors["text"]
        )
        self.now_playing_label.pack(fill="x", padx=15, pady=(12, 2))
        
        self.artist_label = ctk.CTkLabel(
            player_frame,
            text="",
            font=create_ctk_font("small"),
            text_color=colors["text_secondary"]
        )
        self.artist_label.pack(fill="x", padx=15, pady=(0, 8))
        
        progress_frame = ctk.CTkFrame(player_frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.time_current_label = ctk.CTkLabel(
            progress_frame,
            text="0:00",
            font=create_ctk_font("micro"),
            text_color=colors["text_secondary"],
            width=40
        )
        self.time_current_label.pack(side="left")
        
        self.progress_slider = ctk.CTkSlider(
            progress_frame,
            from_=0,
            to=100,
            number_of_steps=1000,
            height=8,
            progress_color=colors["primary"],
            button_color=colors["primary"],
            button_hover_color=colors["primary_hover"]
        )
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=10)
        self.progress_slider.bind("<ButtonPress-1>", self._on_progress_press)
        self.progress_slider.bind("<ButtonRelease-1>", self._on_progress_release)
        
        self.time_total_label = ctk.CTkLabel(
            progress_frame,
            text="0:00",
            font=create_ctk_font("micro"),
            text_color=colors["text_secondary"],
            width=40
        )
        self.time_total_label.pack(side="left")
        
        buttons_frame = ctk.CTkFrame(player_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        btn_size = 40
        
        self.prev_btn = ctk.CTkButton(
            buttons_frame,
            text="⏮",
            width=btn_size,
            height=btn_size,
            corner_radius=btn_size // 2,
            font=("Arial", 22),
            **AppStyles.secondary_button(colors),
            command=self.prev_track
        )
        self.prev_btn.pack(side="left", padx=5)
        
        self.play_btn = ctk.CTkButton(
            buttons_frame,
            text="▶",
            width=btn_size + 10,
            height=btn_size + 10,
            corner_radius=(btn_size + 10) // 2,
            font=("Arial", 26),
            **AppStyles.primary_button(colors),
            command=self._toggle_play_stop
        )
        self.play_btn.pack(side="left", padx=5)
        
        # Repeat button with dropdown
        self.repeat_btn = ctk.CTkButton(
            buttons_frame,
            text="🔁",
            width=btn_size,
            height=btn_size,
            corner_radius=btn_size // 2,
            font=("Arial", 22),
            **AppStyles.secondary_button(colors),
            command=self._toggle_repeat_menu
        )
        self.repeat_btn.pack(side="left", padx=5)

        # Autoplay toggle
        self.autoplay_btn = ctk.CTkButton(
            buttons_frame,
            text="♻️",
            width=btn_size,
            height=btn_size,
            corner_radius=btn_size // 2,
            font=("Arial", 22),
            **AppStyles.secondary_button(colors),
            command=self._toggle_autoplay
        )
        self.autoplay_btn.pack(side="left", padx=5)
        
        self.next_btn = ctk.CTkButton(
            buttons_frame,
            text="⏭",
            width=btn_size,
            height=btn_size,
            corner_radius=btn_size // 2,
            font=("Arial", 22),
            **AppStyles.secondary_button(colors),
            command=self.next_track
        )
        self.next_btn.pack(side="left", padx=5)
        
        volume_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        volume_frame.pack(side="right", padx=5)
        
        self.volume_icon = ctk.CTkLabel(
            volume_frame,
            text="🔊",
            font=("Arial", 18)
        )
        self.volume_icon.pack(side="left", padx=(0, 5))
        
        self.volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=0,
            to=100,
            number_of_steps=10,
            width=80,
            height=6,
            progress_color=colors["primary"],
            button_color=colors["primary"],
            button_hover_color=colors["primary_hover"]
        )
        self.volume_slider.set(self._volume * 100)
        self.volume_slider.pack(side="left")
        self.volume_slider.bind("<Motion>", self._on_volume_change)
        self.volume_slider.bind("<ButtonRelease-1>", self._on_volume_change)
        
        # Tooltips
        self._tooltip_label = None
        self._tooltip_timer = None
        self._setup_tooltips()

    def _setup_tooltips(self):
        """Настройка подсказок для кнопок."""
        tooltips = {
            self.prev_btn: "Предыдущий трек",
            self.play_btn: "Воспроизведение / Стоп",
            self.repeat_btn: "Режим повтора",
            self.autoplay_btn: "Автоплей",
            self.next_btn: "Следующий трек",
        }
        
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        for gc in child.winfo_children():
                            if isinstance(gc, ctk.CTkButton):
                                if "🔄" in gc.cget("text"):
                                    tooltips[gc] = "Обновить список"
                                elif "📂" in gc.cget("text"):
                                    tooltips[gc] = "Открыть папку"

        for btn, text in tooltips.items():
            btn.bind("<Enter>", lambda e, t=text: self._show_tooltip(e, t))
            btn.bind("<Leave>", lambda e: self._hide_tooltip())

    def _show_tooltip(self, event, text):
        """Показать подсказку с задержкой."""
        self._tooltip_timer = self.after(500, lambda: self._create_tooltip(event, text))

    def _hide_tooltip(self):
        """Скрыть подсказку."""
        if self._tooltip_timer:
            self.after_cancel(self._tooltip_timer)
            self._tooltip_timer = None
        if self._tooltip_label:
            self._tooltip_label.destroy()
            self._tooltip_label = None

    def _create_tooltip(self, event, text):
        """Создать окно подсказки."""
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        self._tooltip_label = ctk.CTkToplevel(self)
        self._tooltip_label.overrideredirect(True)
        self._tooltip_label.attributes("-topmost", True)
        
        label = ctk.CTkLabel(
            self._tooltip_label, 
            text=text, 
            fg_color=colors["surface"], 
            text_color=colors["text"],
            corner_radius=6,
            font=create_ctk_font("micro")
        )
        label.pack(padx=5, pady=2)
        
        x = event.x_root + 10
        y = event.y_root + 10
        self._tooltip_label.geometry(f"+{x}+{y}")

    def _toggle_repeat_menu(self):

        """Переключить режим повтора (циклически)."""
        modes = ["ORDER", "RANDOM", "LIST", "TRACK"]
        current_idx = modes.index(self.repeat_mode)
        next_idx = (current_idx + 1) % len(modes)
        self.repeat_mode = modes[next_idx]
        
        icons = {
            "ORDER": "🚫",
            "RANDOM": "🔀",
            "LIST": "🔁",
            "TRACK": "🔂"
        }
        self.repeat_btn.configure(text=icons[self.repeat_mode])
        
        mode_names = {
            "ORDER": "По порядку",
            "RANDOM": "Случайно",
            "LIST": "Весь список",
            "TRACK": "Один трек"
        }
        self.on_log_message(f"🔁 Режим повтора: {mode_names[self.repeat_mode]}")

    def _toggle_autoplay(self):
        """Переключить автоплей."""
        self.autoplay = not self.autoplay
        status = "включён" if self.autoplay else "выключен"
        self.autoplay_btn.configure(text="♻️" if self.autoplay else "🚫")
        self.on_log_message(f"♻️ Автоплей {status}")

    def open_download_folder(self):
        """Выбор папки с музыкой и загрузка плейлиста."""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Выберите папку с музыкой")
        if folder:
            self.on_log_message(f"Загрузка музыки из: {folder}")
            
            supported_ext = ('.mp3', '.wav', '.ogg', '.flac')
            try:
                files = [
                    os.path.join(folder, f) 
                    for f in os.listdir(folder) 
                    if f.lower().endswith(supported_ext)
                ]
                if not files:
                    messagebox.showinfo("Папка пуста", "В выбранной папке не найдено поддерживаемых аудиофайлов.")
                    return
                
                files.sort()
                self.current_playlist = files
                self.current_track_index = 0
                
                # Автоматически запускаем первый трек
                self.play_track(0)
                self.refresh_playlist()
                self.track_count_label.configure(text=f"{len(files)} треков")
                
            except Exception as e:
                self.on_log_message(f"❌ Ошибка при загрузке папки: {e}")
                messagebox.showerror("Ошибка", f"Не удалось загрузить папку: {e}")

    def refresh_playlist(self):
        """Обновить список треков из папки загрузок."""
        for widget in self.track_list_frame.winfo_children():
            widget.destroy()
        
        self.track_buttons.clear()
        self.track_labels.clear()
        
        downloads_path = config.get_single_download_path()
        if not os.path.exists(downloads_path):
            os.makedirs(downloads_path, exist_ok=True)
        
        self.current_playlist = []
        try:
            for filename in os.listdir(downloads_path):
                if filename.lower().endswith(('.mp3', '.wav', '.ogg', '.flac')):
                    self.current_playlist.append(os.path.join(downloads_path, filename))
        except Exception as e:
            self.on_log_message(f"Ошибка чтения папки: {e}")
        
        self.current_playlist.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        
        for i, track_path in enumerate(self.current_playlist):
            filename = os.path.basename(track_path)
            track_frame = ctk.CTkFrame(self.track_list_frame, fg_color="transparent")
            track_frame.grid(row=i, column=0, sticky="ew", pady=2)
            track_frame.grid_columnconfigure(0, weight=1)
            
            name_without_ext = os.path.splitext(filename)[0]
            
            btn = ctk.CTkButton(
                track_frame,
                text=name_without_ext[:50] + ("..." if len(name_without_ext) > 50 else ""),
                height=36,
                corner_radius=8,
                font=create_ctk_font("small"),
                fg_color=colors["surface"],
                hover_color=colors["surface_hover"],
                text_color=colors["text"],
                anchor="w",
                command=lambda idx=i: self.play_track(idx)
            )
            btn.grid(row=0, column=0, sticky="ew")
            self.track_buttons.append(btn)
            
            del_btn = ctk.CTkButton(
                track_frame,
                text="🗑",
                width=36,
                height=36,
                corner_radius=8,
                font=("Arial", 14),
                fg_color=colors["card"],
                hover_color=colors["error"],
                text_color=colors["text"],
                command=lambda idx=i, path=track_path: self._confirm_delete(idx, path)
            )
            del_btn.grid(row=0, column=1, padx=(5, 0))
        
        self.track_count_label.configure(text=f"{len(self.current_playlist)} треков")
        
        if self.current_track_index >= len(self.current_playlist):
            self.current_track_index = len(self.current_playlist) - 1 if self.current_playlist else -1

    def _confirm_delete(self, index, path):
        """Запросить подтверждение удаления трека."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Удалить трек?")
        dialog.geometry("350x150")
        dialog.transient(self)
        dialog.grab_set()
        
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        dialog.configure(fg_color=colors["bg"])
        
        frame = ctk.CTkFrame(dialog, corner_radius=16, fg_color=colors["card"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        filename = os.path.basename(path)
        label = ctk.CTkLabel(
            frame,
            text=f"Удалить трек?\n{filename}",
            font=create_ctk_font("body"),
            text_color=colors["text"]
        )
        label.pack(pady=(10, 20))
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))
        
        def do_delete():
            try:
                # Сначала останавливаем воспроизведение если это текущий трек
                if self.current_track_index == index:
                    self.stop_playback()
                    import time
                    time.sleep(0.5)  # Даём время плееру освободить файл
                
                # Пробуем удалить с повторами
                if os.path.exists(path):
                    import time
                    for attempt in range(5):
                        try:
                            os.remove(path)
                            break
                        except PermissionError:
                            if attempt < 4:
                                time.sleep(0.3)
                            else:
                                raise
                
                if self.current_track_index > index:
                    self.current_track_index -= 1
                self.refresh_playlist()
                self.on_log_message(f"🗑 Трек удалён: {filename}")
            except Exception as e:
                self.on_log_message(f"❌ Ошибка удаления: {e}")
            dialog.destroy()
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Отмена",
            width=100,
            height=36,
            corner_radius=10,
            **AppStyles.secondary_button(colors),
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", padx=10)
        
        delete_btn = ctk.CTkButton(
            btn_frame,
            text="Удалить",
            width=100,
            height=36,
            corner_radius=10,
            fg_color=colors["error"],
            hover_color="#dc2626",
            text_color="white",
            command=do_delete
        )
        delete_btn.pack(side="left", padx=10)

    def play_track(self, index, from_position=0.0):
        """Воспроизвести трек по индексу."""
        if not (PYDUB_AVAILABLE or PYGAME_AVAILABLE or SIMPLEAUDIO_AVAILABLE):
            self.on_log_message("❌ Не установлен ни один плеер (pydub, pygame или simpleaudio)")
            return
        
        if index < 0 or index >= len(self.current_playlist):
            return
        
        self.stop_playback()
        self.stop_playback_flag = False
        
        try:
            track_path = self.current_playlist[index]
            self.current_track_index = index
            self.duration = self._get_duration(track_path)
            self.current_position = from_position
            self.track_start_position = from_position
            
            if PYGAME_AVAILABLE:
                import pygame
                pygame.mixer.music.load(track_path)
                pygame.mixer.music.set_volume(self._volume)
                if from_position > 0:
                    pygame.mixer.music.play(start=from_position)
                else:
                    pygame.mixer.music.play()
                self.play_mode = "pygame"
            elif PYDUB_AVAILABLE and FFMPEG_AVAILABLE:
                audio = AudioSegment.from_file(track_path)
                start_ms = int(from_position * 1000)
                audio = audio[start_ms:]
                self.play_obj = sa.play_buffer(
                    audio.raw_data,
                    num_channels=audio.channels,
                    bytes_per_sample=audio.sample_width,
                    sample_rate=audio.frame_rate
                )
                self.play_mode = "simpleaudio"
            else:
                self.on_log_message("❌ Воспроизведение недоступно")
                return
            
            filename = os.path.basename(track_path)
            name_without_ext = os.path.splitext(filename)[0]
            
            parts = name_without_ext.split(" - ", 1)
            if len(parts) == 2:
                self.now_playing_label.configure(text=parts[1][:60])
                self.artist_label.configure(text=parts[0])
            else:
                self.now_playing_label.configure(text=name_without_ext[:60])
                self.artist_label.configure(text="")
            
            self.is_playing = True
            self.is_paused = False
            self.pause_playback_flag = False
            self.pause_event.clear()
            
            self._update_track_buttons()
            self.time_total_label.configure(text=self.format_time(self.duration))
            
            if from_position > 0 and self.duration > 0:
                pct = (from_position / self.duration) * 100
                self.progress_slider.set(pct)
                self.time_current_label.configure(text=self.format_time(from_position))
            
            self._start_progress_update()
            
            self.play_btn.configure(text="⏹")
            self.on_log_message(f"▶ Воспроизведение: {filename}")
            
            if self.play_mode == "pygame":
                self.current_thread = threading.Thread(target=self._playback_watcher_pygame, daemon=True)
            else:
                self.current_thread = threading.Thread(target=self._playback_watcher, daemon=True)
            self.current_thread.start()
            self.current_thread_id = self.current_thread.ident
            
        except Exception as e:
            self.on_log_message(f"❌ Ошибка воспроизведения: {e}")
            self.is_playing = False

    def _playback_watcher_pygame(self):
        """Следить за окончанием воспроизведения (pygame)."""
        import pygame
        thread_id = threading.current_thread().ident
        
        while True:
            if self.stop_playback_flag:
                return
            if self.pause_playback_flag:
                time.sleep(0.1)
                continue
            if not pygame.mixer.music.get_busy():
                if self.stop_playback_flag:
                    return
                time.sleep(0.2)
                if self.stop_playback_flag:
                    return
                if not pygame.mixer.music.get_busy() and not self.pause_playback_flag:
                    self.after(0, self._on_track_end)
                    return
            time.sleep(0.1)

    def _playback_watcher(self):
        """Следить за окончанием воспроизведения."""
        try:
            while self.play_obj and self.play_obj.is_playing():
                if self.stop_playback_flag:
                    return
                if self.pause_playback_flag:
                    self.pause_event.wait()
                time.sleep(0.05)
            
            if not self.stop_playback_flag and not self.pause_playback_flag:
                self.after(0, self._on_track_end)
        except Exception:
            pass

    def _toggle_play_pause(self):
        """Переключить воспроизведение/паузу."""
        if self.is_playing:
            self.pause_playback()
        elif self.is_paused:
            self.resume_playback()
        elif self.current_track_index >= 0:
            self.play_track(self.current_track_index)
        elif self.current_playlist:
            self.play_track(0)

    def _toggle_play_stop(self):
        """Переключить воспроизведение/стоп."""
        if self.is_playing or self.is_paused:
            self.stop_playback()
        elif self.current_track_index >= 0:
            self.play_track(self.current_track_index, from_position=self.stopped_position)
        elif self.current_playlist:
            self.play_track(0)

    def pause_playback(self):
        """Пауза."""
        if not self.is_playing:
            return
        
        try:
            if self.play_mode == "pygame":
                import pygame
                pygame.mixer.music.pause()
            elif self.play_obj:
                self.play_obj.pause()
            self.is_playing = False
            self.is_paused = True
            self.pause_playback_flag = True
            self.play_btn.configure(text="▶")
            self._stop_progress.set()
            self.on_log_message("⏸ Пауза")
        except Exception as e:
            self.on_log_message(f"❌ Ошибка паузы: {e}")

    def resume_playback(self):
        """Возобновить воспроизведение."""
        if not self.is_paused:
            return
        
        try:
            if self.play_mode == "pygame":
                import pygame
                pygame.mixer.music.unpause()
            elif self.play_obj:
                self.play_obj.resume()
            self.is_playing = True
            self.is_paused = False
            self.pause_playback_flag = False
            self.pause_event.set()
            self.play_btn.configure(text="⏸")
            self._start_progress_update()
            self.on_log_message("▶ Продолжить воспроизведение")
        except Exception as e:
            self.on_log_message(f"❌ Ошибка возобновления: {e}")

    def stop_playback(self):
        """Остановить воспроизведение."""
        self._stop_progress.set()
        self.stop_playback_flag = True
        self.pause_playback_flag = False
        self.pause_event.set()
        
        self.stopped_position = self.current_position
        
        if getattr(self, 'play_mode', None) == "pygame":
            try:
                import pygame
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()  # Освобождаем файл
            except Exception:
                pass
        elif self.play_obj:
            try:
                self.play_obj.stop()
            except Exception:
                pass
            self.play_obj = None
        
        self.is_playing = False
        self.is_paused = False
        self.play_btn.configure(text="▶")
        
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread.join(timeout=0.1)
        self.current_thread = None
        self.current_thread_id = None
        self._update_track_buttons()

    def next_track(self):
        """Следующий трек."""
        if not self.current_playlist:
            return
        
        if self.repeat_mode == "RANDOM":
            import random
            if len(self.current_playlist) > 1:
                # Выбираем случайный индекс, отличный от текущего
                possible_indices = [i for i in range(len(self.current_playlist)) if i != self.current_track_index]
                self.current_track_index = random.choice(possible_indices)
            else:
                self.current_track_index = 0
            self.on_log_message(f"🎲 Случайный трек: {self.current_track_index + 1}")
            self.play_track(self.current_track_index)
        else:
            next_index = (self.current_track_index + 1) % len(self.current_playlist)
            self.play_track(next_index)

    def prev_track(self):
        """Предыдущий трек."""
        if not self.current_playlist:
            return
        
        # Если трек проигрывается и прошло более 3 секунд - начинаем сначала
        if (self.is_playing or self.is_paused) and self.current_position > 3.0:
            self.play_track(self.current_track_index, from_position=0.0)
            return
        
        if self.current_track_index <= 0:
            prev_index = len(self.current_playlist) - 1
        else:
            prev_index = self.current_track_index - 1
        self.play_track(prev_index)

    def seek_forward(self, seconds=10):
        """Перемотка вперёд (не поддерживается simpleaudio напрямую)."""
        if self.duration > 0 and self.current_track_index >= 0:
            self.on_log_message(f"⏩ Перемотка вперёд на {seconds}с (перезапуск трека)")

    def seek_backward(self, seconds=10):
        """Перемотка назад (не поддерживается simpleaudio напрямую)."""
        if self.duration > 0 and self.current_track_index >= 0:
            self.on_log_message(f"⏪ Перемотка назад на {seconds}с (перезапуск трека)")

    def _get_duration(self, filepath):
        """Получить длительность трека."""
        if MUTAGEN_AVAILABLE:
            try:
                audio = MP3(filepath)
                return audio.info.length
            except Exception:
                pass
        
        if PYDUB_AVAILABLE:
            try:
                audio = AudioSegment.from_file(filepath)
                return len(audio) / 1000.0
            except Exception:
                pass
        
        return 0.0

    def _on_progress_press(self, event=None):
        """Начало перемотки."""
        self._seek_pending = True

    def _on_progress_release(self, event=None):
        """Конец перемотки - перемотка к выбранной позиции."""
        if self.duration > 0 and self.play_mode == "pygame":
            new_pos = (self.progress_slider.get() / 100) * self.duration
            
            if self.is_playing or self.is_paused:
                current_volume = self._volume
                self.stop_playback()
                self.play_track(self.current_track_index, from_position=new_pos)
                self._volume = current_volume
                import pygame
                pygame.mixer.music.set_volume(self._volume)
        self._seek_pending = False

    def _on_volume_change(self, event=None):
        """Изменить громкость и сохранить в конфиг."""
        self._volume = self.volume_slider.get() / 100
        
        if self._volume == 0:
            self.volume_icon.configure(text="🔇")
        elif self._volume < 0.5:
            self.volume_icon.configure(text="🔉")
        else:
            self.volume_icon.configure(text="🔊")
        
        if PYGAME_AVAILABLE:
            import pygame
            pygame.mixer.music.set_volume(self._volume)
        
        config.set("player_volume", self._volume)

    def _start_progress_update(self):
        """Запустить поток обновления прогресса."""
        self._stop_progress.clear()
        
        def update_loop():
            while not self._stop_progress.is_set() and self.is_playing:
                try:
                    if self.play_mode == "pygame":
                        import pygame
                        pos_ms = pygame.mixer.music.get_pos()
                        if pos_ms >= 0:
                            self.current_position = self.track_start_position + (pos_ms / 1000.0)
                    elif self.play_obj and self.play_obj.is_playing():
                        self.current_position += 0.1
                    else:
                        if self.is_playing:
                            self.after(0, self._on_track_end)
                        break
                    
                    if self.duration > 0:
                        pct = (self.current_position / self.duration) * 100
                        self.after(0, lambda p=self.current_position: self._update_progress_ui(p))
                        self.after(0, lambda: self.time_current_label.configure(text=self.format_time(self.current_position)))
                    
                except Exception:
                    pass
                time.sleep(0.1)
        
        self._progress_thread = threading.Thread(target=update_loop, daemon=True)
        self._progress_thread.start()

    def _update_progress_ui(self, pos):
        """Обновить UI прогресса."""
        if not self._seek_pending and self.duration > 0:
            pct = (pos / self.duration) * 100
            pct = max(0, min(100, pct))
            self.progress_slider.set(pct)

    def _on_track_end(self):
        """Логика окончания трека (автоплей и повторы)."""
        if self.stop_playback_flag:
            return
        
        if not self.autoplay:
            self.stop_playback()
            self.on_log_message("⏸ Автоплей выключен")
            return

        if self.repeat_mode == "TRACK":
            self.on_log_message("🔁 Повтор текущего трека")
            self.play_track(self.current_track_index)
        elif self.repeat_mode == "RANDOM":
            import random
            if len(self.current_playlist) > 1:
                # Выбираем случайный индекс, отличный от текущего
                possible_indices = [i for i in range(len(self.current_playlist)) if i != self.current_track_index]
                self.current_track_index = random.choice(possible_indices)
            else:
                self.current_track_index = 0
            self.on_log_message(f"🎲 Случайный трек: {self.current_track_index + 1}")
            self.play_track(self.current_track_index)
        elif self.repeat_mode == "LIST" or self.repeat_mode == "ORDER":
            if self.current_track_index < len(self.current_playlist) - 1:
                self.next_track()
            else:
                if self.repeat_mode == "LIST":
                    self.on_log_message("🔁 Возврат к началу списка")
                    self.play_track(0)
                else:
                    self.stop_playback()
                    self.on_log_message("✅ Список воспроизведения завершён")
        else:
            self.stop_playback()

    def _update_track_buttons(self):
        """Обновить визуальное состояние кнопок треков."""
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        
        for i, btn in enumerate(self.track_buttons):
            if i == self.current_track_index:
                btn.configure(fg_color=colors["primary"])
            else:
                btn.configure(fg_color=colors["surface"])

    def format_time(self, seconds):
        """Форматировать секунды в MM:SS."""
        if seconds <= 0:
            return "0:00"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

    def on_activate(self):
        """Вызывается при активации вкладки."""
        if self._first_activation:
            self._first_activation = False
            return
        self.refresh_playlist()

    def on_deactivate(self):
        """Вызывается при деактивации вкладки."""
        pass

    def _start_media_listener(self):
        """Запуск прослушивания медиа-клавиш."""
        try:
            from pynput import keyboard
            
            def on_press(key):
                try:
                    if key == keyboard.Key.media_play_pause:
                        self.after(0, self._toggle_play_stop)
                    elif key == keyboard.Key.media_next:
                        self.after(0, self.next_track)
                    elif key == keyboard.Key.media_previous:
                        self.after(0, self.prev_track)
                except Exception:
                    pass

            self._media_listener = keyboard.Listener(on_press=on_press)
            self._media_listener.start()
            self.on_log_message("⌨️ Поддержка медиа-клавиш включена")
        except Exception as e:
            self.on_log_message(f"⚠️ Ошибка медиа-клавиш: {e}")

    def cleanup(self):
        """Очистка при закрытии."""
        if hasattr(self, '_media_listener'):
            self._media_listener.stop()
        self.stop_playback()
        self._stop_progress.set()

    def refresh_theme(self):
        """Обновить тему плеера."""
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        
        for widget in self.winfo_children():
            try:
                widget_type = widget.winfo_class()
                if widget_type == 'CTkFrame':
                    try:
                        widget.configure(fg_color=colors["surface"])
                    except:
                        pass
            except:
                pass
        
        for btn in self.track_buttons:
            try:
                if self.current_track_index >= 0 and btn == self.track_buttons[self.current_track_index]:
                    btn.configure(fg_color=colors["primary"], text_color="#ffffff")
                else:
                    btn.configure(fg_color=colors["surface"], text_color=colors["text"])
            except:
                pass
        
        self._update_track_buttons()
        
        try:
            self.now_playing_label.configure(text_color=colors["text"])
            self.artist_label.configure(text_color=colors["text_secondary"])
            self.time_current_label.configure(text_color=colors["text_secondary"])
            self.time_total_label.configure(text_color=colors["text_secondary"])
            self.track_count_label.configure(text_color=colors["text_secondary"])
        except:
            pass
