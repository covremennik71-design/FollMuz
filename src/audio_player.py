# src/audio_player.py
import os
import threading
import time
from typing import Optional, Callable, List, Dict

PYGAME_AVAILABLE = False
pygame = None

def _init_pygame():
    global PYGAME_AVAILABLE, pygame
    if pygame is None:
        try:
            pygame = __import__('pygame')
            pygame.mixer.init()
            PYGAME_AVAILABLE = True
        except ImportError:
            try:
                pygame_ce = __import__('pygame-ce')
                globals()['pygame'] = pygame_ce
                pygame_ce.mixer.init()
                PYGAME_AVAILABLE = True
            except ImportError:
                PYGAME_AVAILABLE = False


class AudioPlayer:
    """Аудиоплеер для воспроизведения скачанных треков."""

    def __init__(self):
        _init_pygame()
        from src.config import config
        self.config = config
        self.is_playing = False
        self.is_paused = False
        self.current_file = None
        self.current_track_info = None
        self.duration = 0
        self.position = 0
        self.volume = self.config.get("player_volume", 0.8)
        self._position_thread = None
        self._stop_event = threading.Event()
        self._callbacks = {}

        # Playlist & Playback settings
        self.playlist = []
        self.current_track_index = -1
        self.repeat_mode = "ORDER"  # ORDER, RANDOM, LIST, TRACK
        self.autoplay = True
        self.eq_settings = {
            "60Hz": 0, "170Hz": 0, "310Hz": 0, "600Hz": 0, 
            "1kHz": 0, "3kHz": 0, "6kHz": 0, "12kHz": 0, 
            "14kHz": 0, "16kHz": 0
        }

    def set_callback(self, event: str, callback: Callable):
        """Установить callback для событий плеера."""
        self._callbacks[event] = callback

    def _trigger_callback(self, event: str, *args):
        if event in self._callbacks:
            self._callbacks[event](*args)

    def load_track(self, filepath: str, artist: str = "", title: str = "") -> bool:
        """Загрузить трек для воспроизведения."""
        if not os.path.exists(filepath):
            return False
        
        if not PYGAME_AVAILABLE:
            return False

        try:
            self.stop()
            pygame.mixer.music.load(filepath)
            self.current_file = filepath
            self.current_track_info = {
                "artist": artist,
                "title": title,
                "filepath": filepath
            }
            self.duration = self._get_duration(filepath)
            self.position = 0
            self._trigger_callback("on_load", self.current_track_info)
            return True
        except Exception as e:
            print(f"Ошибка загрузки трека: {e}")
            return False

    def _get_duration(self, filepath: str) -> float:
        """Получить длительность трека в секундах."""
        try:
            from mutagen.mp3 import MP3
            audio = MP3(filepath)
            return audio.info.length
        except:
            return 0

    def play(self):
        """Воспроизвести трек."""
        if not PYGAME_AVAILABLE or not self.current_file:
            return

        try:
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self._start_position_updates()
            self._trigger_callback("on_play")
        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")

    def pause(self):
        """Пауза."""
        if not PYGAME_AVAILABLE:
            return

        try:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.is_playing = False
            self._trigger_callback("on_pause")
        except Exception as e:
            print(f"Ошибка паузы: {e}")

    def resume(self):
        """Продолжить воспроизведение."""
        if not PYGAME_AVAILABLE:
            return

        try:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.is_playing = True
            self._trigger_callback("on_resume")
        except Exception as e:
            print(f"Ошибка продолжения: {e}")

    def toggle_play_pause(self):
        """Переключить воспроизведение/паузу."""
        if self.is_playing:
            self.pause()
        elif self.is_paused:
            self.resume()
        else:
            self.play()

    def stop(self):
        """Остановить воспроизведение."""
        if not PYGAME_AVAILABLE:
            return

        try:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self._stop_event.set()
            if self._position_thread:
                self._position_thread.join(timeout=0.5)
            self._stop_event.clear()
            self.position = 0
            self._trigger_callback("on_stop")
        except Exception as e:
            print(f"Ошибка остановки: {e}")

    def seek(self, position: float):
        """Переместиться к позиции (в секундах)."""
        if not PYGAME_AVAILABLE or not self.current_file:
            return

        try:
            current_pos = pygame.mixer.music.get_pos() / 1000.0
            delta = position - self.position
            
            if delta > 0:
                pass
            
            self.position = position
            self._trigger_callback("on_seek", position)
        except Exception as e:
            print(f"Ошибка seek: {e}")

    def set_volume(self, volume: float):
        """Установить громкость (0.0 - 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(self.volume)
        self.config.set("player_volume", self.volume)
        self._trigger_callback("on_volume_change", self.volume)

    def load_folder(self, folder_path: str) -> bool:
        """Загрузить все аудиофайлы из папки в плейлист."""
        if not os.path.exists(folder_path):
            return False
        
        supported_ext = ('.mp3', '.wav', '.ogg', '.flac')
        files = [
            os.path.join(folder_path, f) 
            for f in os.listdir(folder_path) 
            if f.lower().endswith(supported_ext)
        ]
        
        if not files:
            return False
            
        self.playlist = files
        self.current_track_index = 0
        
        # Load first track
        first_file = self.playlist[0]
        # Try to extract artist/title from filename
        filename = os.path.basename(first_file)
        name_without_ext = os.path.splitext(filename)[0]
        artist, title = "Unknown", name_without_ext
        if " - " in name_without_ext:
            parts = name_without_ext.split(" - ", 1)
            artist, title = parts[0], parts[1]
            
        return self.load_track(first_file, artist, title)

    def play_next(self):
        """Воспроизвести следующий трек."""
        if not self.playlist:
            return False
            
        if self.repeat_mode == "RANDOM":
            import random
            self.current_track_index = random.randint(0, len(self.playlist) - 1)
        else:
            self.current_track_index += 1
            if self.current_track_index >= len(self.playlist):
                if self.repeat_mode == "LIST" or self.repeat_mode == "ORDER":
                    self.current_track_index = 0
                else:
                    return False

        next_file = self.playlist[self.current_track_index]
        filename = os.path.basename(next_file)
        name_without_ext = os.path.splitext(filename)[0]
        artist, title = "Unknown", name_without_ext
        if " - " in name_without_ext:
            parts = name_without_ext.split(" - ", 1)
            artist, title = parts[0], parts[1]
            
        return self.load_track(next_file, artist, title)

    def play_previous(self):
        """Воспроизвести предыдущий трек."""
        if not self.playlist:
            return False
            
        self.current_track_index -= 1
        if self.current_track_index < 0:
            if self.repeat_mode == "LIST" or self.repeat_mode == "ORDER":
                self.current_track_index = len(self.playlist) - 1
            else:
                self.current_track_index = 0
                
        prev_file = self.playlist[self.current_track_index]
        filename = os.path.basename(prev_file)
        name_without_ext = os.path.splitext(filename)[0]
        artist, title = "Unknown", name_without_ext
        if " - " in name_without_ext:
            parts = name_without_ext.split(" - ", 1)
            artist, title = parts[0], parts[1]
            
        return self.load_track(prev_file, artist, title)

    def get_position(self) -> float:
        """Получить текущую позицию в секундах."""
        if not PYGAME_AVAILABLE:
            return 0
        
        try:
            if self.is_playing:
                pos = pygame.mixer.music.get_pos() / 1000.0
                self.position = pos
                return pos
            return self.position
        except:
            return 0

    def _start_position_updates(self):
        """Запустить поток обновления позиции."""
        self._stop_event.clear()
        
        def update_loop():
            while not self._stop_event.is_set() and self.is_playing:
                try:
                    pos = pygame.mixer.music.get_pos() / 1000.0
                    self.position = pos
                    self._trigger_callback("on_position_update", pos)
                    
                    if not pygame.mixer.music.get_busy() and not self.is_paused:
                        self.is_playing = False
                        self._trigger_callback("on_end")
                        
                        if self.autoplay:
                            if self.repeat_mode == "TRACK":
                                self.play()
                            else:
                                self.play_next()
                                if self.current_file:
                                    self.play()
                        break
                        
                except:
                    pass
                time.sleep(0.1)
        
        self._position_thread = threading.Thread(target=update_loop, daemon=True)
        self._position_thread.start()

    def get_track_info(self) -> Optional[Dict]:
        """Получить информацию о текущем треке."""
        return self.current_track_info

    def format_time(self, seconds: float) -> str:
        """Форматировать секунды в MM:SS."""
        if seconds <= 0:
            return "0:00"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"


class AudioPlayerWidget:
    """UI виджет аудиоплеера для интеграции в GUI."""

    def __init__(self, master, audio_player: AudioPlayer):
        import customtkinter as ctk
        from src.styles import AppColors, AppStyles, AppDimensions
        from src.utils import create_ctk_font
        from src.config import config

        self.master = master
        self.player = audio_player
        self.colors = AppColors.get_theme(config.get("theme", "dark") or "dark")

        self.frame = ctk.CTkFrame(master, corner_radius=16, **AppStyles.panel(self.colors, "card"))

        if not PYGAME_AVAILABLE:
            ctk.CTkLabel(
                self.frame,
                text="🎵 Для воспроизведения установите: pip install pygame-ce",
                font=create_ctk_font("small"),
                text_color=self.colors["text_secondary"]
            ).pack(pady=15)
            return
        
        self.track_label = ctk.CTkLabel(
            self.frame,
            text="Трек не выбран",
            font=create_ctk_font("body", weight="bold"),
            text_color=self.colors["text"]
        )
        self.track_label.pack(pady=(12, 4))

        self.artist_label = ctk.CTkLabel(
            self.frame,
            text="",
            font=create_ctk_font("small"),
            text_color=self.colors["text_secondary"]
        )
        self.artist_label.pack(pady=(0, 8))

        self.progress_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=(0, 8))
        
        self.time_current = ctk.CTkLabel(
            self.progress_frame,
            text="0:00",
            font=create_ctk_font("micro"),
            text_color=self.colors["text_secondary"],
            width=45
        )
        self.time_current.pack(side="left")

        self.progress_slider = ctk.CTkSlider(
            self.progress_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            height=8,
            progress_color=self.colors["primary"],
            button_color=self.colors["primary"],
            button_hover_color=self.colors["primary_hover"]
        )
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=8)
        self.progress_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        self.time_total = ctk.CTkLabel(
            self.progress_frame,
            text="0:00",
            font=create_ctk_font("micro"),
            text_color=self.colors["text_secondary"],
            width=45
        )
        self.time_total.pack(side="right")

        self.controls_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.controls_frame.pack(pady=(0, 12))
        
        # Folder selection button
        self.folder_btn = ctk.CTkButton(
            self.controls_frame,
            text="📁",
            width=50,
            height=50,
            corner_radius=25,
            font=("Arial", 20),
            **AppStyles.icon_button(self.colors),
            command=self._on_choose_folder
        )
        self.folder_btn.pack(side="left", padx=10)

        self.play_btn = ctk.CTkButton(
            self.controls_frame,
            text="▶",
            width=50,
            height=50,
            corner_radius=25,
            font=("Arial", 20),
            **AppStyles.primary_button(self.colors),
            command=self._toggle_play
        )
        self.play_btn.pack(side="left", padx=15)

        # Repeat button with dropdown
        self.repeat_btn = ctk.CTkButton(
            self.controls_frame,
            text="🔁",
            width=50,
            height=50,
            corner_radius=25,
            font=("Arial", 20),
            **AppStyles.icon_button(self.colors),
            command=self._toggle_repeat_menu
        )
        self.repeat_btn.pack(side="left", padx=10)

        # Autoplay toggle
        self.autoplay_btn = ctk.CTkButton(
            self.controls_frame,
            text="♻️",
            width=50,
            height=50,
            corner_radius=25,
            font=("Arial", 20),
            **AppStyles.icon_button(self.colors),
            command=self._toggle_autoplay
        )
        self.autoplay_btn.pack(side="left", padx=10)
        
        # Equalizer button
        self.eq_btn = ctk.CTkButton(
            self.controls_frame,
            text="🎚️",
            width=50,
            height=50,
            corner_radius=25,
            font=("Arial", 20),
            **AppStyles.icon_button(self.colors),
            command=self._open_equalizer
        )
        self.eq_btn.pack(side="left", padx=10)

        self.volume_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.volume_frame.pack(side="right", padx=15)
        
        self.volume_label = ctk.CTkLabel(
            self.volume_frame,
            text="🔊",
            font=("Arial", 14)
        )
        self.volume_label.pack(side="left")
        
        self.volume_slider = ctk.CTkSlider(
            self.volume_frame,
            from_=0,
            to=100,
            number_of_steps=10,
            width=80,
            height=6,
            progress_color=self.colors["primary"],
            button_color=self.colors["primary"],
            button_hover_color=self.colors["primary_hover"]
        )
        self.volume_slider.set(self.player.volume * 100)
        self.volume_slider.pack(side="left", padx=5)
        self.volume_slider.bind("<Motion>", self._on_volume_change)
        self.volume_slider.bind("<ButtonRelease-1>", self._on_volume_change)

        self.player.set_callback("on_load", self._on_track_load)
        self.player.set_callback("on_play", self._on_play)
        self.player.set_callback("on_pause", self._on_pause)
        self.player.set_callback("on_position_update", self._on_position_update)
        self.player.set_callback("on_end", self._on_end)
        self.player.set_callback("on_seek", self._on_seek)

    def _toggle_play(self):
        self.player.toggle_play_pause()

    def _on_choose_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory()
        if folder:
            if self.player.load_folder(folder):
                self.player.play()
                # Trigger load callback to update UI
                first_track = self.player.current_track_info
                self._on_track_load(first_track)
                self._on_play()

    def _toggle_autoplay(self):
        self.player.autoplay = not self.player.autoplay
        self.autoplay_btn.configure(
            fg_color=self.colors["primary"] if self.player.autoplay else self.colors["button_secondary"]
        )

    def _toggle_repeat_menu(self):
        import customtkinter as ctk
        from src.utils import create_ctk_font
        
        menu = ctk.CTkToplevel(self.master)
        menu.title("Repeat Mode")
        menu.geometry("250x200")
        menu.attributes("-topmost", True)
        menu.overrideredirect(True)
        
        # Position menu near the button
        x = self.repeat_btn.winfo_rootx()
        y = self.repeat_btn.winfo_rooty() + self.repeat_btn.winfo_height()
        menu.geometry(f"+{x}+{y}")

        frame = ctk.CTkFrame(menu, corner_radius=12, **AppStyles.panel(self.colors, "card"))
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        modes = {
            "По порядку": "ORDER",
            "Случайный порядок": "RANDOM",
            "Повтор списка треков": "LIST",
            "Повтор трека": "TRACK"
        }

        for text, mode in modes.items():
            btn = ctk.CTkButton(
                frame,
                text=text,
                font=create_ctk_font("small"),
                command=lambda m=mode: self._set_repeat_mode(m, menu)
            )
            btn.pack(fill="x", padx=10, pady=5)

    def _set_repeat_mode(self, mode, menu):
        self.player.repeat_mode = mode
        menu.destroy()

    def _open_equalizer(self):
        import customtkinter as ctk
        from src.utils import create_ctk_font
        
        eq_win = ctk.CTkToplevel(self.master)
        eq_win.title("Equalizer")
        eq_win.geometry("400x500")
        eq_win.attributes("-topmost", True)
        
        container = ctk.CTkFrame(eq_win, corner_radius=20, **AppStyles.panel(self.colors, "card"))
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            container, 
            text="Эквалайзер", 
            font=create_ctk_font("header"), 
            text_color=self.colors["text"]
        ).pack(pady=15)

        sliders_frame = ctk.CTkFrame(container, fg_color="transparent")
        sliders_frame.pack(fill="both", expand=True, padx=20)

        self.eq_sliders = {}
        bands = list(self.player.eq_settings.keys())
        
        for i, band in enumerate(bands):
            band_frame = ctk.CTkFrame(sliders_frame, fg_color="transparent")
            band_frame.pack(side="left", expand=True, fill="y", padx=5)
            
            slider = ctk.CTkSlider(
                band_frame, 
                from_=-12, 
                to=12, 
                orientation="vertical", 
                width=20,
                command=lambda v, b=band: self._update_eq_band(b, v)
            )
            slider.set(self.player.eq_settings[band])
            slider.pack(pady=(20, 10))
            
            ctk.CTkLabel(
                band_frame, 
                text=band, 
                font=create_ctk_font("micro"), 
                text_color=self.colors["text_secondary"]
            ).pack()
            
            self.eq_sliders[band] = slider

        def reset_eq():
            for band, slider in self.eq_sliders.items():
                slider.set(0)
                self._update_eq_band(band, 0)

        reset_btn = ctk.CTkButton(
            container,
            text="Сбросить настройки",
            command=reset_eq,
            **AppStyles.secondary_button(self.colors)
        )
        reset_btn.pack(pady=20)

    def _update_eq_band(self, band, value):
        self.player.eq_settings[band] = value
        # Pygame does not support real-time EQ, so we store state.
        # If we had a DSP library, we would apply the filter here.
        pass

    def _on_slider_release(self, event):
        duration = self.player.duration
        if duration > 0:
            position = (self.progress_slider.get() / 100) * duration
            self.player.seek(position)

    def _on_volume_change(self, event):
        volume = self.volume_slider.get() / 100
        self.player.set_volume(volume)
        if volume == 0:
            self.volume_label.configure(text="🔇")
        elif volume < 0.5:
            self.volume_label.configure(text="🔉")
        else:
            self.volume_label.configure(text="🔊")

    def _on_track_load(self, track_info):
        if track_info:
            self.track_label.configure(text=track_info.get("title", "Неизвестный трек"))
            self.artist_label.configure(text=track_info.get("artist", ""))
            self.time_total.configure(text=self.player.format_time(self.player.duration))
            self.progress_slider.set(0)
            self.time_current.configure(text="0:00")

    def _on_play(self):
        self.play_btn.configure(text="⏸")

    def _on_pause(self):
        self.play_btn.configure(text="▶")

    def _on_position_update(self, position):
        duration = self.player.duration
        if duration > 0:
            pct = (position / duration) * 100
            self.progress_slider.set(pct)
            self.time_current.configure(text=self.player.format_time(position))

    def _on_end(self):
        self.play_btn.configure(text="▶")
        self.progress_slider.set(0)
        self.time_current.configure(text="0:00")

    def _on_seek(self, position):
        self.time_current.configure(text=self.player.format_time(position))

    def show(self):
        self.frame.pack(fill="x", padx=20, pady=(10, 0))

    def hide(self):
        self.frame.pack_forget()

    def refresh_colors(self):
        from src.styles import AppColors, AppStyles
        from src.config import config
        self.colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        self.frame.configure(fg_color=self.colors["card"])
        if not hasattr(self, 'track_label'):
            return
        self.track_label.configure(text_color=self.colors["text"])
        self.artist_label.configure(text_color=self.colors["text_secondary"])
        self.time_current.configure(text_color=self.colors["text_secondary"])
        self.time_total.configure(text_color=self.colors["text_secondary"])
