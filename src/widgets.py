import tkinter as tk
import customtkinter as ctk
import os
import sys
from tkinter import messagebox
from src.styles import AppColors, AppDimensions, AppStyles, AppEffects, AnimatedWidget, GradientBackground
from src.utils import create_ctk_font
from src.translations import Translations
from src.config import config
from src.constants import TRACK_TYPES


# ========== SimpleProgressLabel ==========

class SimpleProgressLabel(ctk.CTkFrame):
    """Круговой прогресс-бар для отображения статуса скачивания."""

    def __init__(self, master, size=120, **kwargs):
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        super().__init__(
            master,
            corner_radius=60,
            fg_color=colors["bg"],
            **kwargs
        )

        self.size = size
        self.progress = 0
        self.status = "idle"
        self.colors = colors
        
        self.canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            bg=colors["bg"],
            highlightthickness=0
        )
        self.canvas.pack(pady=20)
        
        self.status_label = ctk.CTkLabel(
            self,
            text="Подготавливаю...",
            font=create_ctk_font("small"),
            text_color=colors["text_secondary"]
        )
        self.status_label.pack(pady=(0, 10))
        
        self._draw_circle(0, "loading")

    def _draw_circle(self, progress, status="loading"):
        self.canvas.delete("all")
        cx, cy = self.size // 2, self.size // 2
        radius = (self.size // 2) - 10
        
        if status == "success":
            self.canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                fill="#22C55E", outline=""
            )
            self.canvas.create_text(
                cx, cy, text="✓", font=("Arial", 40, "bold"),
                fill="white"
            )
            self.status_label.configure(text="Скачано", text_color="#22C55E")
            return
        
        if status == "error":
            self.canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                fill="#EF4444", outline=""
            )
            self.canvas.create_text(
                cx, cy, text="✗", font=("Arial", 40, "bold"),
                fill="white"
            )
            self.status_label.configure(text="Ошибка", text_color="#EF4444")
            return
        
        bg_color = self.colors.get("progress_track", "#374151")
        fill_color = self.colors.get("primary", "#3B82F6")
        
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=bg_color, outline=""
        )
        
        if progress > 0:
            angle = (progress / 100) * 360
            start_angle = 90
            
            self.canvas.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=start_angle, extent=-angle,
                style="arc", width=8,
                outline=fill_color
            )
        
        self.canvas.create_text(
            cx, cy, text=f"{int(progress)}%",
            font=create_ctk_font("title", weight="bold"),
            fill=self.colors.get("text", "white")
        )

    def set_progress(self, value):
        self.progress = min(100, max(0, value))
        self.status = "loading"
        self._draw_circle(self.progress, self.status)

    def set_status_text(self, text):
        self.status_label.configure(text=text)

    def start(self):
        self.progress = 0
        self.status = "loading"
        self._draw_circle(0, "loading")
        self.status_label.configure(text="Подготавливаю...", text_color=self.colors["text_secondary"])

    def stop(self):
        self.progress = 100
        self.status = "success"
        self._draw_circle(self.progress, self.status)

    def set_error(self):
        self.status = "error"
        self._draw_circle(self.progress, self.status)


class PlaylistProgressLabel(ctk.CTkFrame):
    """Круговой прогресс-бар для скачивания плейлиста."""

    def __init__(self, master, size=100, **kwargs):
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        super().__init__(
            master,
            corner_radius=50,
            fg_color=colors["bg"],
            **kwargs
        )

        self.size = size
        self.progress = 0
        self.total_tracks = 0
        self.completed_tracks = 0
        self.colors = colors
        
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        self.left_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.left_frame.pack(side="left")
        
        self.canvas = tk.Canvas(
            self.left_frame,
            width=size,
            height=size,
            bg=colors["bg"],
            highlightthickness=0
        )
        self.canvas.pack()
        
        self.right_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.right_frame.pack(side="left", fill="both", expand=True, padx=(15, 0))
        self.right_frame.grid_columnconfigure(0, weight=1)
        
        self.label = ctk.CTkLabel(
            self.right_frame,
            text="Плейлист: 0/0",
            font=create_ctk_font("body", weight="bold"),
            text_color=colors["text"],
            anchor="w"
        )
        self.label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.status_label = ctk.CTkLabel(
            self.right_frame,
            text="Подготавливаю...",
            font=create_ctk_font("small"),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        self.status_label.grid(row=1, column=0, sticky="w")
        
        self.current_track_label = ctk.CTkLabel(
            self.right_frame,
            text="",
            font=create_ctk_font("small"),
            text_color=colors["primary"],
            anchor="w"
        )
        self.current_track_label.grid(row=2, column=0, sticky="w", pady=(5, 0))
        
        self._draw_circle(0)

    def _draw_circle(self, progress):
        self.canvas.delete("all")
        cx, cy = self.size // 2, self.size // 2
        radius = (self.size // 2) - 8
        
        bg_color = self.colors.get("progress_track", "#374151")
        fill_color = self.colors.get("primary", "#3B82F6")
        
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=bg_color, outline=""
        )
        
        if progress > 0:
            angle = (progress / 100) * 360
            self.canvas.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=90, extent=-angle,
                style="arc", width=6,
                outline=fill_color
            )
        
        self.canvas.create_text(
            cx, cy, text=f"{int(progress)}%",
            font=create_ctk_font("body", weight="bold"),
            fill=self.colors.get("text", "white")
        )
        self.completed_tracks = 0

    def set_total(self, total):
        """Установить общее количество треков."""
        self.total_tracks = total
        self.completed_tracks = 0
        self.update_progress()

    def track_done(self, success=True):
        """Отметить трек как завершённый."""
        self.completed_tracks += 1
        self.update_progress()

    def update_progress(self):
        """Обновить прогресс."""
        if self.total_tracks > 0:
            self.progress = int((self.completed_tracks / self.total_tracks) * 100)
            self.label.configure(text=f"Плейлист: {self.completed_tracks}/{self.total_tracks}")
            self._draw_circle(self.progress)
        else:
            self.label.configure(text="Плейлист: ...")
            self._draw_circle(0)

    def set_current_track(self, artist, title):
        """Показать текущий трек."""
        self.current_track_label.configure(text=f"Скачиваю: {artist} - {title}")

    def set_status(self, text):
        """Установить текст статуса."""
        self.status_label.configure(text=text)

    def set_track_progress(self, pct, msg):
        """Обновить прогресс текущего трека."""
        self.status_label.configure(text=msg)

    def start(self):
        """Начать загрузку."""
        self.progress = 0
        self.completed_tracks = 0
        self.label.configure(text="Плейлист: 0%")
        self.status_label.configure(text="Подготавливаю загрузку...")
        self.current_track_label.configure(text="")
        self._draw_circle(0)

    def stop(self):
        """Завершить загрузку."""
        self.progress = 100
        self.label.configure(text=f"Плейлист: 100% ({self.total_tracks}/{self.total_tracks})")
        self.status_label.configure(text="Загрузка завершена")
        self._draw_circle(100)


# ========== TrackVariantSelector ==========

class TrackVariantSelector(ctk.CTkToplevel):
    """Окно выбора варианта трека."""

    def __init__(self, parent, artist, title, callback, lang="ru"):
        super().__init__(parent)

        #Атрибуты
        self.artist_name = artist
        self.track_title = title
        self.callback = callback
        self.lang = lang
        self.variant_data = []

        self.selected_var = tk.StringVar(value="0")

        print(f"DEBUG: Creating TrackVariantSelector for {artist} - {title}")

        self.title(Translations.get_string("select_variant", self.lang))
        self.geometry("600x500")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.apply_theme()
        self.setup_ui()

    def apply_theme(self):
        theme_name = config.get("theme", "dark") or "dark"
        ctk.set_appearance_mode("dark" if theme_name == "dark" else "light")
        self.configure(fg_color=AppColors.get_theme(theme_name)["bg"])

    def setup_ui(self):
        print("DEBUG: Setting up TrackVariantSelector UI")
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")

        # Заголовок
        title_frame = ctk.CTkFrame(
            self,
            corner_radius=20,
            **AppStyles.panel(colors, "card")
        )
        title_frame.pack(fill="x", padx=20, pady=(20,10))

        ctk.CTkLabel(
            title_frame,
            text=f"{self.artist_name} - {self.track_title}",
            font=create_ctk_font("header"),
            text_color=colors["text"]
        ).pack(anchor="w", padx=18, pady=(16,0))

        ctk.CTkLabel(
            title_frame,
            text=Translations.get_string("select_variant_desc", self.lang),
            font=create_ctk_font("small"),
            text_color=colors["text_secondary"]
        ).pack(anchor="w", padx=18, pady=(5,16))

        # Контейнер для вариантов
        variants_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=20,
            **AppStyles.scrollable_frame(colors)
        )
        variants_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Заголовки колонок
        headers_frame = ctk.CTkFrame(variants_frame, fg_color="transparent", height=30)
        headers_frame.pack(fill="x", pady=(0,5))
        headers_frame.pack_propagate(False)

        ctk.CTkLabel(headers_frame, text="", width=30).pack(side="left")
        ctk.CTkLabel(
            headers_frame,
            text=Translations.get_string("track_type", self.lang),
            font=create_ctk_font("small", weight="bold"),
            width=150
        ).pack(side="left", padx=2)
        ctk.CTkLabel(
            headers_frame,
            text=Translations.get_string("search_query", self.lang),
            font=create_ctk_font("small", weight="bold"),
            width=200
        ).pack(side="left", padx=2)

        # Добавляем варианты
        self.add_variants(variants_frame)

        # Кнопки
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=20)

        download_btn = ctk.CTkButton(
            button_frame,
            text=Translations.get_string("download", self.lang),
            command=self.on_select,
            height=40,
            width=120,
            font=create_ctk_font("body", weight="bold"),
            corner_radius=14,
            **AppStyles.primary_button(colors)
        )
        download_btn.pack(side="left", padx=5)
        AppEffects.bind_button(download_btn, colors, "primary")

        cancel_btn = ctk.CTkButton(
            button_frame,
            text=Translations.get_string("cancel", self.lang),
            command=self.destroy,
            height=40,
            width=120,
            corner_radius=14,
            font=create_ctk_font("body"),
            **AppStyles.secondary_button(colors)
        )
        cancel_btn.pack(side="left", padx=5)
        AppEffects.bind_button(cancel_btn, colors, "secondary")

        self.update()

    def add_variants(self, parent):
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")

        for i, track_type in enumerate(TRACK_TYPES):
            type_name = track_type.get(f"name_{self.lang}", track_type["name_en"])

            if track_type["search_term"]:
                search_query = f"{self.artist_name} {self.track_title} {track_type['search_term']}"
            else:
                search_query = f"{self.artist_name} {self.track_title} audio"

            row_frame = ctk.CTkFrame(
                parent,
                height=48,
                corner_radius=16,
                **AppStyles.panel(colors, "card_alt")
            )
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)
            AppEffects.bind_card(row_frame, colors)

            radio = ctk.CTkRadioButton(
                row_frame,
                text="",
                variable=self.selected_var,
                value=str(i),
                width=20,
                **AppStyles.radio(colors)
            )
            radio.pack(side="left", padx=(12,5))

            ctk.CTkLabel(
                row_frame,
                text=type_name,
                width=150,
                anchor="w",
                font=create_ctk_font("small"),
                text_color=colors["text"]
            ).pack(side="left", padx=2)

            display_query = search_query[:50] + "..." if len(search_query) > 50 else search_query
            ctk.CTkLabel(
                row_frame,
                text=display_query,
                width=200,
                anchor="w",
                font=create_ctk_font("small"),
                text_color=colors["text_secondary"]
            ).pack(side="left", padx=2)

            self.variant_data.append({
                "type": track_type["id"],
                "type_name": type_name,
                "search_query": search_query,
                "artist": self.artist_name,
                "title": self.track_title,
                "modification": track_type["search_term"],  # для передачи в search_and_download
                "full_title": f"{self.artist_name} - {self.track_title} ({type_name})"
            })

    def on_select(self):
        print(f"DEBUG: on_select called, selected={self.selected_var.get()}")
        print(f"DEBUG: variant_data length={len(self.variant_data)}")

        if self.selected_var.get():
            index=int(self.selected_var.get())
            if 0 <= index < len(self.variant_data):
                selected_data = self.variant_data[index]
                print(f'DEBUG: Selected index {index}: {selected_data}')
                self.callback(selected_data)
                self.destroy()
            else:
                print(f'DEBUG: Index {index} out of range')
        

# ========== SettingsWindow ==========

class SettingsWindow(ctk.CTkToplevel):
    """Отдельное окно настроек."""

    def __init__(self, parent, config, theme_callback, language_callback):
        super().__init__(parent)
        self.parent = parent
        self.cfg = config
        self.theme_callback = theme_callback
        self.language_callback = language_callback

        self.current_theme = config.get("theme", "dark")
        self.current_lang = config.get("language", "ru")

        self.title(Translations.get_string("settings_title", self.current_lang))
        self.geometry("680x600")
        self.resizable(False, False)
        self.minsize(600, 520)

        self.transient(parent)
        self.grab_set()

        self.apply_theme()
        self.setup_ui()

        self.after(100, self._animate_open)

    def apply_theme(self):
        theme_name = self.current_theme
        ctk.set_appearance_mode("dark" if theme_name == "dark" else "light")
        colors = AppColors.get_theme(theme_name)
        self.configure(fg_color=colors["bg"])

    def _animate_open(self):
        try:
            self.attributes("-alpha", 0.0)
            self._fade_in(0.0)
        except Exception:
            pass

    def _fade_in(self, current):
        if current >= 1.0:
            try:
                self.attributes("-alpha", 1.0)
            except Exception:
                pass
            return
        next_val = min(1.0, current + 0.12)
        try:
            self.attributes("-alpha", next_val)
        except Exception:
            pass
        self.after(16, lambda: self._fade_in(next_val))

    def _animate_close(self, callback):
        try:
            self.attributes("-alpha", 1.0)
            self._fade_out(1.0, callback)
        except Exception:
            callback()

    def _fade_out(self, current, callback):
        if current <= 0.0:
            callback()
            return
        next_val = max(0.0, current - 0.15)
        try:
            self.attributes("-alpha", next_val)
        except Exception:
            pass
        self.after(16, lambda: self._fade_out(next_val, callback))

    def setup_ui(self):
        lang = self.current_lang
        tr = Translations.get_string
        colors = AppColors.get_theme(self.current_theme)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        tabview = ctk.CTkTabview(
            self,
            corner_radius=20,
            **AppStyles.tabview(colors)
        )
        tabview.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 10))

        tab_general = tabview.add(tr("general_tab", lang) if tr("general_tab", lang) != "general_tab" else "Основные")
        tab_appearance = tabview.add(tr("appearance_tab", lang) if tr("appearance_tab", lang) != "appearance_tab" else "Внешний вид")
        tab_about = tabview.add(tr("about_tab", lang) if tr("about_tab", lang) != "about_tab" else "О приложении")

        tab_general.grid_columnconfigure(0, weight=1)
        tab_general.grid_rowconfigure(0, weight=1)

        tab_appearance.grid_columnconfigure(0, weight=1)
        tab_appearance.grid_rowconfigure(0, weight=1)

        tab_about.grid_columnconfigure(0, weight=1)
        tab_about.grid_rowconfigure(0, weight=1)

        self._build_general_tab(tab_general)
        self._build_appearance_tab(tab_appearance)
        self._build_about_tab(tab_about)

        self._build_bottom_bar(colors)

    def _section_title(self, parent, text):
        colors = AppColors.get_theme(self.current_theme)
        lbl = ctk.CTkLabel(
            parent,
            text=text,
            font=create_ctk_font("small", weight="bold"),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        return lbl

    def _card(self, parent):
        colors = AppColors.get_theme(self.current_theme)
        card = ctk.CTkFrame(
            parent,
            corner_radius=16,
            **AppStyles.panel(colors, "card")
        )
        return card

    def _build_general_tab(self, parent):
        lang = self.current_lang
        tr = Translations.get_string
        colors = AppColors.get_theme(self.current_theme)

        scroll = ctk.CTkScrollableFrame(
            parent,
            corner_radius=0,
            fg_color="transparent",
            scrollbar_button_color=colors["scrollbar"],
            scrollbar_button_hover_color=colors["scrollbar_hover"],
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        scroll.grid_columnconfigure(0, weight=1)

        row_idx = 0

        # MP3 Quality
        quality_card = self._card(scroll)
        quality_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 12))
        quality_card.grid_columnconfigure(0, weight=1)

        self._section_title(quality_card, tr("mp3_quality", lang)).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        self.quality_var = ctk.StringVar(value=self.cfg.get("mp3_quality", "192"))
        q_frame = ctk.CTkFrame(quality_card, fg_color="transparent")
        q_frame.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")
        for q in ["128", "192", "256", "320"]:
            ctk.CTkRadioButton(
                q_frame,
                text=f"{q} kbps",
                variable=self.quality_var,
                value=q,
                font=create_ctk_font("body"),
                **AppStyles.radio(colors)
            ).pack(side="left", padx=(0, 18))

        row_idx += 1

        # Audio Channels
        channels_card = self._card(scroll)
        channels_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 12))
        channels_card.grid_columnconfigure(0, weight=1)

        self._section_title(channels_card, tr("audio_channels", lang)).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        self.channels_var = ctk.StringVar(value=self.cfg.get("audio_channels", "stereo"))
        ch_frame = ctk.CTkFrame(channels_card, fg_color="transparent")
        ch_frame.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")
        channels = [
            ("stereo", tr("stereo", lang)),
            ("mono", tr("mono", lang)),
            ("joint_stereo", tr("joint_stereo", lang)),
            ("dual_mono", tr("dual_mono", lang))
        ]
        for val, text in channels:
            ctk.CTkRadioButton(
                ch_frame,
                text=text,
                variable=self.channels_var,
                value=val,
                font=create_ctk_font("body"),
                **AppStyles.radio(colors)
            ).pack(side="left", padx=(0, 18))

        row_idx += 1

        # Download Path (single)
        path_card = self._card(scroll)
        path_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 12))
        path_card.grid_columnconfigure(0, weight=1)

        self._section_title(path_card, tr("download_path", lang)).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        path_frame = ctk.CTkFrame(path_card, fg_color="transparent")
        path_frame.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)

        self.single_path_entry = ctk.CTkEntry(
            path_frame,
            height=38,
            corner_radius=12,
            font=create_ctk_font("small"),
            **AppStyles.entry(colors)
        )
        self.single_path_entry.insert(0, self.cfg.get_single_download_path())
        self.single_path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        single_browse_btn = ctk.CTkButton(
            path_frame,
            text="…",
            width=42,
            height=38,
            corner_radius=12,
            font=create_ctk_font("body", weight="bold"),
            command=self.choose_single_folder,
            **AppStyles.secondary_button(colors)
        )
        single_browse_btn.grid(row=0, column=1)
        AppEffects.bind_button(single_browse_btn, colors, "secondary")

        row_idx += 1

        # Download Path (playlist)
        pl_path_card = self._card(scroll)
        pl_path_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 12))
        pl_path_card.grid_columnconfigure(0, weight=1)

        self._section_title(pl_path_card, tr("playlist_download_path", lang)).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        pl_path_frame = ctk.CTkFrame(pl_path_card, fg_color="transparent")
        pl_path_frame.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="ew")
        pl_path_frame.grid_columnconfigure(0, weight=1)

        self.playlist_path_entry = ctk.CTkEntry(
            pl_path_frame,
            height=38,
            corner_radius=12,
            font=create_ctk_font("small"),
            **AppStyles.entry(colors)
        )
        self.playlist_path_entry.insert(0, self.cfg.get_playlist_download_path())
        self.playlist_path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        pl_browse_btn = ctk.CTkButton(
            pl_path_frame,
            text="…",
            width=42,
            height=38,
            corner_radius=12,
            font=create_ctk_font("body", weight="bold"),
            command=self.choose_playlist_folder,
            **AppStyles.secondary_button(colors)
        )
        pl_browse_btn.grid(row=0, column=1)
        AppEffects.bind_button(pl_browse_btn, colors, "secondary")

        row_idx += 1

        # Tag Options
        tags_card = self._card(scroll)
        tags_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 12))
        tags_card.grid_columnconfigure(0, weight=1)

        self._section_title(tags_card, tr("tag_options", lang) if tr("tag_options", lang) != "tag_options" else "Теги и обложки").grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        self.add_tags_var = ctk.BooleanVar(value=self.cfg.get("add_tags", True))
        ctk.CTkCheckBox(
            tags_card,
            text=tr("add_tags", lang),
            variable=self.add_tags_var,
            font=create_ctk_font("body"),
            **AppStyles.checkbox(colors)
        ).grid(row=1, column=0, padx=18, pady=(0, 6), sticky="w")

        self.download_cover_var = ctk.BooleanVar(value=self.cfg.get("download_cover", True))
        ctk.CTkCheckBox(
            tags_card,
            text=tr("download_cover", lang),
            variable=self.download_cover_var,
            font=create_ctk_font("body"),
            **AppStyles.checkbox(colors)
        ).grid(row=2, column=0, padx=18, pady=(0, 16), sticky="w")

        # Bypass
        self.bypass_var = ctk.BooleanVar(value=self.cfg.get("use_bypass", False))
        
        # Начальный цвет
        bypass_fg = colors["success"] if self.bypass_var.get() else colors["primary"]
        
        self.bypass_switch = ctk.CTkSwitch(
            tags_card,
            text="Использовать встроенный обход",
            variable=self.bypass_var,
            font=create_ctk_font("body"),
            fg_color=bypass_fg,
            button_color=colors["text"],
            button_hover_color=colors["text_secondary"],
            text_color=colors["text"],
            command=self._on_bypass_toggle
        )
        self.bypass_switch.grid(row=3, column=0, padx=18, pady=(10, 5), sticky="w")
        
        # Информационная сноска
        ctk.CTkLabel(
            tags_card,
            text="Помогает обходить ограничения провайдера для доступа к сервисам.",
            font=create_ctk_font("micro"),
            text_color=colors["text_secondary"],
            wraplength=350,
            justify="left"
        ).grid(row=4, column=0, padx=18, pady=(0, 16), sticky="w")

    def _on_bypass_toggle(self):
        from src.widgets import ToastNotification
        
        # Обновляем цвет в зависимости от состояния
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        new_state = self.bypass_var.get()
        
        if new_state:
            self.bypass_switch.configure(fg_color=colors["success"])
        else:
            self.bypass_switch.configure(fg_color=colors["primary"])
            
        # Запрос на перезагрузку
        if messagebox.askyesno("Перезагрузка", "Для применения изменений требуется перезагрузить приложение. Перезагрузить сейчас?"):
            self.cfg.set("use_bypass", new_state)
            
            # Перезапуск приложения
            python = sys.executable
            os.execl(python, python, *sys.argv)
        else:
            # Если отменили, возвращаем состояние переключателя в конфиге (если нужно),
            # но визуально оставляем как есть до следующего изменения
            pass

    def _build_appearance_tab(self, parent):
        lang = self.current_lang
        tr = Translations.get_string
        colors = AppColors.get_theme(self.current_theme)

        scroll = ctk.CTkScrollableFrame(
            parent,
            corner_radius=0,
            fg_color="transparent",
            scrollbar_button_color=colors["scrollbar"],
            scrollbar_button_hover_color=colors["scrollbar_hover"],
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        scroll.grid_columnconfigure(0, weight=1)

        row_idx = 0

        # Theme (Dark only - no switching)
        theme_card = self._card(scroll)
        theme_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 12))
        theme_card.grid_columnconfigure(0, weight=1)

        self._section_title(theme_card, tr("theme", lang)).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        theme_label = ctk.CTkLabel(
            theme_card,
            text="Тёмная",
            font=create_ctk_font("body"),
            text_color=colors["text_secondary"]
        )
        theme_label.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")

        row_idx += 1

        # Language
        lang_card = self._card(scroll)
        lang_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 12))
        lang_card.grid_columnconfigure(0, weight=1)

        self._section_title(lang_card, tr("language", lang)).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        self.lang_var = ctk.StringVar(value=self.current_lang)
        lang_frame = ctk.CTkFrame(lang_card, fg_color="transparent")
        lang_frame.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")
        languages = Translations.get_available_languages()
        for i, lang_info in enumerate(languages):
            ctk.CTkRadioButton(
                lang_frame,
                text=lang_info["name"],
                variable=self.lang_var,
                value=lang_info["code"],
                font=create_ctk_font("body"),
                **AppStyles.radio(colors)
            ).pack(side="left", padx=(0, 18))

        row_idx += 1

        # Minimize to tray
        tray_card = self._card(scroll)
        tray_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 12))
        tray_card.grid_columnconfigure(0, weight=1)

        self._section_title(tray_card, tr("minimize_to_tray", lang)).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        self.minimize_to_tray_var = ctk.BooleanVar(value=self.cfg.get("minimize_to_tray", False))
        ctk.CTkCheckBox(
            tray_card,
            text=tr("minimize_to_tray_toggle", lang) if tr("minimize_to_tray_toggle", lang) != "minimize_to_tray_toggle" else tr("minimize_to_tray", lang),
            variable=self.minimize_to_tray_var,
            font=create_ctk_font("body"),
            **AppStyles.checkbox(colors)
        ).grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")

    def _build_about_tab(self, parent):
        lang = self.current_lang
        tr = Translations.get_string
        colors = AppColors.get_theme(self.current_theme)

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        center = ctk.CTkFrame(frame, corner_radius=20, **AppStyles.panel(colors, "card"))
        center.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            center,
            text=tr("app_name", lang),
            font=create_ctk_font("title"),
            text_color=colors["text"]
        ).pack(pady=(36, 6))

        ctk.CTkLabel(
            center,
            text=tr("version", lang),
            font=create_ctk_font("body"),
            text_color=colors["text_secondary"]
        ).pack(pady=(0, 18))

        ctk.CTkLabel(
            center,
            text=tr("app_description", lang),
            font=create_ctk_font("body"),
            justify="center",
            text_color=colors["text"]
        ).pack(padx=30, pady=(0, 30))

        reset_btn = ctk.CTkButton(
            center,
            text="Сбросить настройки",
            command=self._reset_to_defaults,
            height=36,
            width=180,
            corner_radius=12,
            font=create_ctk_font("body"),
            fg_color=colors.get("danger", "#e74c3c"),
            hover_color=colors.get("danger_hover", "#c0392b"),
            text_color="white"
        )
        reset_btn.pack(pady=(0, 20))

    def _reset_to_defaults(self):
        from tkinter import messagebox
        if messagebox.askyesno("Сброс настроек", "Вы уверены, что хотите сбросить все настройки до значений по умолчанию?"):
            self.cfg.reset_to_defaults()
            messagebox.showinfo("Сброс", "Настройки сброшены. Перезапустите приложение.")

    def _build_bottom_bar(self, colors):
        lang = self.current_lang
        tr = Translations.get_string

        bar = ctk.CTkFrame(self, fg_color="transparent", height=60)
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        bar.grid_columnconfigure(0, weight=1)
        bar.pack_propagate(False)

        cancel_btn = ctk.CTkButton(
            bar,
            text=tr("cancel_btn", lang),
            command=self._on_cancel,
            height=42,
            width=120,
            corner_radius=14,
            font=create_ctk_font("body"),
            **AppStyles.secondary_button(colors)
        )
        cancel_btn.grid(row=0, column=0, sticky="w")
        AppEffects.bind_button(cancel_btn, colors, "secondary")

        save_btn = ctk.CTkButton(
            bar,
            text=tr("save_btn", lang),
            command=self._on_save,
            height=42,
            width=120,
            corner_radius=14,
            font=create_ctk_font("body", weight="bold"),
            **AppStyles.primary_button(colors)
        )
        save_btn.grid(row=0, column=1, sticky="e")
        AppEffects.bind_button(save_btn, colors, "primary")

    def choose_single_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(initialdir=self.single_path_entry.get())
        if folder:
            self.single_path_entry.delete(0, "end")
            self.single_path_entry.insert(0, folder)

    def choose_playlist_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(initialdir=self.playlist_path_entry.get())
        if folder:
            self.playlist_path_entry.delete(0, "end")
            self.playlist_path_entry.insert(0, folder)

    def _on_save(self):
        self.cfg.set("mp3_quality", self.quality_var.get())
        if self.single_path_entry.get():
            self.cfg.set_single_download_path(self.single_path_entry.get())
        if self.playlist_path_entry.get():
            self.cfg.set_playlist_download_path(self.playlist_path_entry.get())
        self.cfg.set("add_tags", self.add_tags_var.get())
        self.cfg.set("download_cover", self.download_cover_var.get())
        self.cfg.set("use_bypass", self.bypass_var.get())
        self.cfg.set("audio_channels", self.channels_var.get())
        self.cfg.set("minimize_to_tray", self.minimize_to_tray_var.get())

        lang_changed = self.lang_var.get() != self.current_lang

        if lang_changed:
            self.cfg.set("language", self.lang_var.get())

        def do_close():
            self.destroy()
            if lang_changed:
                self.language_callback(self.lang_var.get())

        self._animate_close(do_close)

    def _on_cancel(self):
        self._animate_close(self.destroy)


# ========== AnimatedButton ==========

class AnimatedButton(ctk.CTkButton):
    """Кнопка с плавной анимацией при наведении и нажатии."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._original_fg = self.cget("fg_color")
        self._original_hover = self.cget("hover_color")
        self._original_width = self.cget("width") or 120
        self._animating = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        self.configure(fg_color=self._original_hover)
        self._animate_scale(1.0, 1.03)

    def _on_leave(self, event):
        self.configure(fg_color=self._original_fg)
        self._animate_scale(1.03, 1.0)

    def _on_press(self, event):
        self._animate_scale(1.03, 0.97)

    def _on_release(self, event):
        self._animate_scale(0.97, 1.03)
        self.after(80, lambda: self._animate_scale(1.03, 1.0))

    def _animate_scale(self, start, end, steps=8):
        if self._animating:
            return
        self._animating = True

        def animate(step=0):
            if step <= steps:
                scale = start + (end - start) * (step / steps)
                new_w = max(20, int(self._original_width * scale))
                try:
                    self.configure(width=new_w)
                except tk.TclError:
                    pass
                self.after(10, animate, step + 1)
            else:
                self._animating = False

        animate()


# ========== AnimatedProgressBar ==========

class AnimatedProgressBar(ctk.CTkFrame):
    """Улучшенный анимированный прогресс-бар с градиентом и пульсацией."""

    def __init__(self, master, width=400, height=20, **kwargs):
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        super().__init__(master, width=width, height=height + 30, fg_color="transparent", **kwargs)
        self.pack_propagate(False)

        self.bar_width = width
        self.bar_height = height
        self.progress = 0
        self._pulse_animation = None
        self._pulse_direction = 1
        self._pulse_value = 0

        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=colors["progress_track"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(pady=(0, 5))

        self.canvas.create_rectangle(0, 0, width, height, fill=colors["progress_track"], outline="")

        c1 = AppColors.hex_to_rgb(colors["progress_start"])
        c2 = AppColors.hex_to_rgb(colors["progress_end"])
        mid_r = (c1[0] + c2[0]) // 2
        mid_g = (c1[1] + c2[1]) // 2
        mid_b = (c1[2] + c2[2]) // 2
        self.bar_color = AppColors.rgb_to_hex(mid_r, mid_g, mid_b)

        self.bar = self.canvas.create_rectangle(0, 0, 0, height, fill=self.bar_color, outline="")

        self.percent_label = ctk.CTkLabel(
            self,
            text="0%",
            font=create_ctk_font("small", weight="bold"),
            text_color=colors["text"],
        )
        self.percent_label.pack()

    def set_progress(self, value):
        target_width = int((value / 100) * self.bar_width)
        self._animate_width(target_width, value)

    def _animate_width(self, target_width, percent, step=0, steps=20):
        try:
            current_width = self.canvas.coords(self.bar)[2]
        except tk.TclError:
            return
        if step <= steps:
            new_width = current_width + (target_width - current_width) * (step / steps)
            self.canvas.coords(self.bar, 0, 0, new_width, self.bar_height)

            red = int(255 - (percent * 2.55))
            green = int(percent * 2.55)
            blue = 100
            color = f"#{max(0, min(255, red)):02x}{max(0, min(255, green)):02x}{max(0, min(255, blue)):02x}"
            self.canvas.itemconfig(self.bar, fill=color)

            self.after(10, self._animate_width, target_width, percent, step + 1, steps)
        else:
            self.canvas.coords(self.bar, 0, 0, target_width, self.bar_height)

        self.percent_label.configure(text=f"{percent:.1f}%")

    def start_pulse(self):
        self._pulse_direction = 1
        self._pulse_value = 0
        self._animate_pulse()

    def _animate_pulse(self):
        self._pulse_value += 0.05 * self._pulse_direction
        if self._pulse_value >= 1:
            self._pulse_value = 1
            self._pulse_direction = -1
        elif self._pulse_value <= 0:
            self._pulse_value = 0
            self._pulse_direction = 1

        alpha = 0.3 + self._pulse_value * 0.4
        try:
            self.canvas.itemconfig(self.bar, stipple="gray50")
        except tk.TclError:
            pass
        self._pulse_animation = self.after(50, self._animate_pulse)

    def stop_pulse(self):
        if self._pulse_animation:
            self.after_cancel(self._pulse_animation)
            self._pulse_animation = None
        try:
            self.canvas.itemconfig(self.bar, stipple="")
        except tk.TclError:
            pass


# ========== SkeletonLoader ==========

class SkeletonLoader(ctk.CTkFrame):
    """Эффект скелетона для загрузки."""

    def __init__(self, master, width=400, height=50, **kwargs):
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        super().__init__(master, width=width, height=height, fg_color=colors["card"], corner_radius=10, **kwargs)
        self.pack_propagate(False)
        self._animation_running = False
        self._animation_id = None

        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=colors["card"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

    def start_animation(self):
        self._animation_running = True
        self._animate(0)

    def _animate(self, offset):
        if not self._animation_running:
            return

        try:
            self.update_idletasks()
            width = self.winfo_width()
            height = self.winfo_height()
        except tk.TclError:
            return

        if width < 2 or height < 2:
            self._animation_id = self.after(50, self._animate, (offset + 10) % 40)
            return

        self.canvas.delete("gradient")
        base_color = AppColors.get_theme(config.get("theme", "dark") or "dark")["card"]
        hover_color = AppColors.get_theme(config.get("theme", "dark") or "dark")["surface_hover"]
        c1 = AppColors.hex_to_rgb(base_color)
        c2 = AppColors.hex_to_rgb(hover_color)

        for i in range(0, width, 20):
            x = i + offset
            if 0 <= x < width:
                alpha = 0.3 + (i / width) * 0.5
                r = int(c1[0] * (1 - alpha) + c2[0] * alpha)
                g = int(c1[1] * (1 - alpha) + c2[1] * alpha)
                b = int(c1[2] * (1 - alpha) + c2[2] * alpha)
                color = f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"
                self.canvas.create_rectangle(x, 0, x + 20, height, fill=color, tags="gradient")

        self._animation_id = self.after(50, self._animate, (offset + 10) % 40)

    def stop_animation(self):
        self._animation_running = False
        if self._animation_id:
            self.after_cancel(self._animation_id)
            self._animation_id = None
        self.canvas.delete("gradient")


# ========== ToastNotification ==========

class ToastNotification(ctk.CTkToplevel):
    """Всплывающее уведомление."""

    def __init__(self, parent, message, duration=3):
        super().__init__(parent)
        self.parent = parent
        self.duration = duration

        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")

        self.title("")
        self.overrideredirect(True)
        self.configure(fg_color=colors["card"])
        self.attributes("-alpha", 0)
        self.attributes("-topmost", True)

        self.label = ctk.CTkLabel(
            self,
            text=message,
            font=create_ctk_font("body"),
            text_color=colors["text"],
            padx=20,
            pady=12,
        )
        self.label.pack()

        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
            y = parent.winfo_y() + parent.winfo_height() - 80
            self.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

        self._fade_in()

    def _fade_in(self, alpha=0):
        if alpha <= 1:
            try:
                self.attributes("-alpha", alpha)
            except tk.TclError:
                return
            self.after(20, self._fade_in, alpha + 0.05)
        else:
            self.after(self.duration * 1000, self._fade_out)

    def _fade_out(self, alpha=1):
        if alpha >= 0:
            try:
                self.attributes("-alpha", alpha)
            except tk.TclError:
                self.destroy()
                return
            self.after(20, self._fade_out, alpha - 0.05)
        else:
            self.destroy()


# ========== CircularProgressWidget ==========

class CircularProgressWidget(ctk.CTkFrame):
    """Круговой прогресс-бар для отображения статуса скачивания."""

    def __init__(self, master, size=120, **kwargs):
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        super().__init__(
            master,
            corner_radius=60,
            fg_color=colors["bg"],
            **kwargs
        )

        self.size = size
        self.progress = 0
        self.status = "idle"
        self.animation_id = None
        self.colors = colors
        
        self.canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            bg=colors["bg"],
            highlightthickness=0
        )
        self.canvas.pack(pady=20)
        
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=create_ctk_font("body", weight="bold"),
            text_color=colors["text"]
        )
        self.status_label.pack(pady=(0, 10))

    def _draw_circle(self, progress, status="loading"):
        self.canvas.delete("all")
        cx, cy = self.size // 2, self.size // 2
        radius = (self.size // 2) - 10
        
        if status == "success":
            self.canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                fill="#22C55E", outline=""
            )
            self.canvas.create_text(
                cx, cy, text="✓", font=("Arial", 40, "bold"),
                fill="white"
            )
            self.status_label.configure(text="Скачано", text_color="#22C55E")
            return
        
        if status == "error":
            self.canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                fill="#EF4444", outline=""
            )
            self.canvas.create_text(
                cx, cy, text="✗", font=("Arial", 40, "bold"),
                fill="white"
            )
            self.status_label.configure(text="Ошибка", text_color="#EF4444")
            return
        
        if status == "loading":
            bg_color = self.colors.get("progress_track", "#374151")
            fill_color = self.colors.get("primary", "#3B82F6")
            
            self.canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                fill=bg_color, outline=""
            )
            
            if progress > 0:
                angle = (progress / 100) * 360
                start_angle = 90
                
                self.canvas.create_arc(
                    cx - radius, cy - radius, cx + radius, cy + radius,
                    start=start_angle, extent=-angle,
                    style="arc", width=8,
                    outline=fill_color
                )
            
            self.canvas.create_text(
                cx, cy, text=f"{int(progress)}%",
                font=create_ctk_font("title", weight="bold"),
                fill=self.colors.get("text", "white")
            )

    def set_progress(self, value):
        self.progress = min(100, max(0, value))
        self.status = "loading"
        self._draw_circle(self.progress, self.status)

    def set_success(self):
        self.progress = 100
        self.status = "success"
        self._draw_circle(self.progress, self.status)

    def set_error(self):
        self.status = "error"
        self._draw_circle(self.progress, self.status)

    def reset(self):
        self.progress = 0
        self.status = "idle"
        self._draw_circle(0, "loading")
        self.status_label.configure(text="")
