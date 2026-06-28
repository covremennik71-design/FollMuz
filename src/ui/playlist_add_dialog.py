# src/ui/playlist_add_dialog.py
"""Диалог добавления плейлиста."""

import customtkinter as ctk
from src.styles import AppColors, AppStyles
from src.utils import create_ctk_font
from src.config import config


class PlaylistAddDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_tracks_added):
        super().__init__(parent)
        self.title("")
        self.geometry("500x400")
        self.resizable(False, False)
        self.grab_set()
        
        self.current_mode = "choice"
        self.on_tracks_added = on_tracks_added
        
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        self.configure(fg_color=colors["bg"])
        
        self._setup_choice_ui()
        
        self.transient(parent)
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 200
        self.geometry(f"500x400+{x}+{y}")

    def _setup_choice_ui(self):
        self.clear_ui()
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        
        title = ctk.CTkLabel(
            self,
            text="📥 Скачать из",
            font=create_ctk_font("header", weight="bold"),
            text_color=colors["text"]
        )
        title.pack(pady=(40, 30))
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        url_btn = ctk.CTkButton(
            btn_frame,
            text="🔗 Ссылка",
            width=150,
            height=60,
            corner_radius=15,
            font=create_ctk_font("body", weight="bold"),
            **AppStyles.primary_button(colors),
            command=self._switch_to_url
        )
        url_btn.pack(side="left", padx=15)
        
        file_btn = ctk.CTkButton(
            btn_frame,
            text="📁 Файл",
            width=150,
            height=60,
            corner_radius=15,
            font=create_ctk_font("body", weight="bold"),
            **AppStyles.secondary_button(colors),
            command=self._switch_to_file
        )
        file_btn.pack(side="left", padx=15)

    def _switch_to_url(self):
        self.clear_ui()
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        self.current_mode = "url"
        
        back_btn = ctk.CTkButton(
            self,
            text="← Назад к выбору",
            width=150,
            height=32,
            corner_radius=8,
            font=create_ctk_font("small"),
            **AppStyles.secondary_button(colors),
            command=self._setup_choice_ui
        )
        back_btn.pack(anchor="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            self,
            text="Вставьте ссылку на плейлист:",
            font=create_ctk_font("body"),
            text_color=colors["text_secondary"]
        ).pack(anchor="w", padx=20, pady=(20, 5))
        
        self.url_entry = ctk.CTkEntry(
            self,
            height=50,
            placeholder_text="https://open.spotify.com/playlist/...\nhttps://music.youtube.com/playlist/...",
            corner_radius=10,
            font=create_ctk_font("body"),
            **AppStyles.entry(colors)
        )
        self.url_entry.pack(fill="x", padx=20, pady=10)
        
        info_label = ctk.CTkLabel(
            self,
            text="Поддерживается: Spotify, YouTube Music, VK",
            font=create_ctk_font("small"),
            text_color=colors["text_secondary"]
        )
        info_label.pack(pady=5)
        
        parse_btn = ctk.CTkButton(
            self,
            text="🔍 Загрузить плейлист",
            height=50,
            corner_radius=12,
            font=create_ctk_font("body", weight="bold"),
            **AppStyles.primary_button(colors),
            command=self._parse_playlist_url
        )
        parse_btn.pack(pady=20, padx=20, fill="x")
        
        self.url_result_label = ctk.CTkLabel(
            self,
            text="",
            font=create_ctk_font("small"),
            text_color=colors["accent"]
        )
        self.url_result_label.pack(pady=5)

    def _switch_to_file(self):
        self.clear_ui()
        colors = AppColors.get_theme(config.get("theme", "dark") or "dark")
        self.current_mode = "file"
        
        back_btn = ctk.CTkButton(
            self,
            text="← Назад к выбору",
            width=150,
            height=32,
            corner_radius=8,
            font=create_ctk_font("small"),
            **AppStyles.secondary_button(colors),
            command=self._setup_choice_ui
        )
        back_btn.pack(anchor="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            self,
            text="📝 Формат файла:",
            font=create_ctk_font("body", weight="bold"),
            text_color=colors["text"]
        ).pack(anchor="w", padx=20, pady=(10, 5))
        
        info_box = ctk.CTkTextbox(
            self,
            height=100,
            font=("Consolas", 11),
            fg_color=colors["surface"],
            text_color=colors["text"],
            border_width=1,
            border_color=colors["border"]
        )
        info_box.pack(fill="x", padx=20, pady=5)
        info_box.insert("1.0", "Исполнитель|название\n---\nПример:\nMiyagi|Тамада\nMiyagi|Привычка\nAndy Lezard|Feel Good")
        info_box.configure(state="disabled")
        
        ctk.CTkButton(
            self,
            text="📂 Выбрать файл",
            height=50,
            corner_radius=12,
            font=create_ctk_font("body", weight="bold"),
            **AppStyles.primary_button(colors),
            command=self._choose_file
        ).pack(pady=20, padx=20, fill="x")

    def _parse_playlist_url(self):
        url = self.url_entry.get().strip()
        if not url:
            self.url_result_label.configure(text="⚠️ Введите ссылку")
            return
        
        self.url_result_label.configure(text="⏳ Загрузка...")
        
        def worker():
            tracks = []
            try:
                if 'spotify.com' in url or 'open.spotify.com' in url:
                    from src.api.spotify_client import SpotifyClient
                    client = SpotifyClient()
                    info = client.extract_playlist_info(url)
                    if info and info.get('tracks'):
                        tracks = info['tracks']
                elif 'vk.com' in url:
                    from src.playlist_parser import PlaylistParser
                    parser = PlaylistParser()
                    tracks = parser.parse(url) or []
                else:
                    from src.playlist_parser import PlaylistParser
                    parser = PlaylistParser()
                    tracks = parser.parse(url) or []
                
                from src.utils import normalize_query
                for track in tracks:
                    track['artist'] = normalize_query(track.get('artist', ''))
                    track['title'] = normalize_query(track.get('title', ''))
                
                self.after(0, lambda: self._on_tracks_loaded(tracks))
            except Exception as e:
                self.after(0, lambda: self.url_result_label.configure(text=f"❌ Ошибка: {e}"))
        
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _on_tracks_loaded(self, tracks):
        if tracks:
            self.url_result_label.configure(text=f"✅ Найдено {len(tracks)} треков")
            self.after(500, self.destroy)
            self.on_tracks_added(tracks)
        else:
            self.url_result_label.configure(text="❌ Плейлист не найден")

    def _choose_file(self):
        from tkinter import filedialog
        
        file = filedialog.askopenfilename(
            title="Выберите файл плейлиста",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file:
            return
        
        tracks = []
        try:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '|' in line:
                        parts = [part.strip() for part in line.split('|')]
                        if len(parts) >= 2:
                            artist = parts[0]
                            title = parts[1]
                            if artist and title:
                                tracks.append({"artist": artist, "title": title})
            
            self.destroy()
            self.on_tracks_added(tracks)
        except Exception as e:
            self.url_result_label.configure(text=f"❌ Ошибка чтения: {e}")

    def clear_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
