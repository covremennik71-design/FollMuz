# src/ui/sidebar.py
"""Боковая навигационная панель для приложения FollMuz."""

import customtkinter as ctk
from src.styles import AppColors, AppStyles
from src.utils import create_ctk_font
from src.config import config


class Sidebar(ctk.CTkFrame):
    """Боковая панель навигации."""

    def __init__(self, master, on_item_selected, current_theme="dark", is_frameless=False, window=None, **kwargs):
        super().__init__(
            master,
            width=200,
            corner_radius=15,
            **kwargs
        )
        self.on_item_selected = on_item_selected
        self.current_theme = current_theme
        self.active_item = "single"
        self.buttons = {}
        self.is_frameless = is_frameless
        self.window = window
        
        self.pack(side="left", fill="y", padx=(0, 10), pady=0)
        self.pack_propagate(False)

        self._setup_ui()

    def _setup_ui(self):
        """Настройка интерфейса панели."""
        colors = AppColors.get_theme(self.current_theme)

        logo_frame = ctk.CTkFrame(self, fg_color="transparent", height=80)
        logo_frame.pack(fill="x", padx=15, pady=(20, 10))
        logo_frame.pack_propagate(False)

        logo_label = ctk.CTkLabel(
            logo_frame,
            text="🎵 FollMuz",
            font=create_ctk_font("header", weight="bold"),
            text_color=colors["primary"],
            cursor="fleur"
        )
        logo_label.pack(anchor="w")
        
        if self.is_frameless and self.window:
            logo_label.bind("<Button-1>", self._start_drag)
            logo_label.bind("<B1-Motion>", self._on_drag)

        separator = ctk.CTkFrame(self, height=1, fg_color=colors["border"])
        separator.pack(fill="x", padx=15, pady=(5, 15))

        self._create_menu_items(colors)
        self._create_settings_button(colors)
        
        if self.is_frameless and self.window:
            self._create_window_controls(colors)
        
        self._highlight_button("single")

    def _highlight_button(self, item_key):
        """Highlight a button without triggering callback."""
        colors = AppColors.get_theme(self.current_theme)
        for key, btn in self.buttons.items():
            if key == item_key:
                btn.configure(fg_color=colors["primary"], text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color=colors["text"])

    def _create_menu_items(self, colors):
        """Создание пунктов меню."""
        menu_items = [
            ("single", "🎵 Один трек", "single"),
            ("playlist", "📋 Плейлист", "playlist"),
            ("player", "🎧 Аудио плеер", "player"),
        ]

        for item_key, text, icon_text in menu_items:
            btn = ctk.CTkButton(
                self,
                text=text,
                command=lambda k=item_key: self._select_item(k),
                anchor="w",
                height=48,
                corner_radius=10,
                font=create_ctk_font("body"),
                fg_color="transparent",
                text_color=colors["text"],
                hover_color=colors["surface_hover"],
                hover=True,
            )
            btn.pack(fill="x", padx=10, pady=3)
            self.buttons[item_key] = btn

            btn.bind("<Enter>", lambda e, b=btn: self._on_enter(b))
            btn.bind("<Leave>", lambda e, b=btn, k=item_key: self._on_leave(b, k))

    def _create_settings_button(self, colors):
        """Создание кнопки настроек."""
        separator = ctk.CTkFrame(self, height=1, fg_color=colors["border"])
        separator.pack(fill="x", padx=15, pady=(10, 10))

        self.settings_btn = ctk.CTkButton(
            self,
            text="⚙️ Настройки",
            command=self._open_settings,
            anchor="w",
            height=48,
            corner_radius=10,
            font=create_ctk_font("body"),
            fg_color="transparent",
            text_color=colors["text"],
            hover_color=colors["surface_hover"],
            hover=True,
        )
        self.settings_btn.pack(fill="x", padx=10, pady=10, side="bottom")

        self.settings_btn.bind("<Enter>", lambda e: self._on_enter(self.settings_btn))
        self.settings_btn.bind("<Leave>", lambda e: self._on_leave(self.settings_btn, "settings"))

    def _on_enter(self, btn):
        """Анимация при наведении."""
        try:
            colors = AppColors.get_theme(self.current_theme)
            if btn == self.settings_btn or self.buttons.get(self.active_item) == btn:
                return
            btn.configure(fg_color=colors["surface_press"])
        except Exception:
            pass

    def _on_leave(self, btn, item_key=None):
        """Анимация при уходе мыши."""
        try:
            colors = AppColors.get_theme(self.current_theme)
            if item_key == self.active_item or (item_key == "settings" and btn == self.settings_btn):
                return
            btn.configure(fg_color="transparent")
        except Exception:
            pass

    def _select_item(self, item_key):
        """Выбор пункта меню."""
        colors = AppColors.get_theme(self.current_theme)
        self.active_item = item_key

        for key, btn in self.buttons.items():
            if key == item_key:
                btn.configure(
                    fg_color=colors["primary"],
                    text_color="#ffffff"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=colors["text"]
                )

        if self.on_item_selected:
            self.on_item_selected(item_key)

    def _open_settings(self):
        """Открытие окна настроек."""
        from src.widgets import SettingsWindow
        from src.config import config
        try:
            settings_window = SettingsWindow(
                self.winfo_toplevel(),
                config,
                theme_callback=self._on_theme_changed,
                language_callback=None
            )
        except Exception as e:
            print(f"Ошибка открытия настроек: {e}")

    def _on_theme_changed(self, new_theme):
        """Обработчик смены темы."""
        self.current_theme = new_theme
        colors = AppColors.get_theme(new_theme)

        self.configure(fg_color=colors.get("sidebar_bg", colors["surface"]))

        for key, btn in self.buttons.items():
            if key == self.active_item:
                btn.configure(
                    fg_color=colors.get("sidebar_active", colors["primary"]),
                    text_color=colors.get("sidebar_text", "#ffffff")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=colors["text"]
                )

        self.settings_btn.configure(
            fg_color="transparent",
            text_color=colors["text"]
        )

    def set_active(self, item_key):
        """Установить активный пункт извне."""
        self._select_item(item_key)

    def _create_window_controls(self, colors):
        """Создание кнопок управления окном для frameless режима."""
        controls_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        controls_frame.pack(fill="x", padx=10, pady=(10, 0), side="bottom")
        controls_frame.pack_propagate(False)

        minimize_btn = ctk.CTkButton(
            controls_frame,
            text="─",
            width=30,
            height=30,
            corner_radius=6,
            font=("Segoe UI", 14, "bold"),
            fg_color=colors["surface_hover"],
            text_color=colors["text"],
            hover_color=colors["surface_press"],
            command=self._minimize_window
        )
        minimize_btn.pack(side="left", padx=2)

        close_btn = ctk.CTkButton(
            controls_frame,
            text="✕",
            width=30,
            height=30,
            corner_radius=6,
            font=("Segoe UI", 12, "bold"),
            fg_color="#e81123",
            text_color="white",
            hover_color="#f1707a",
            command=self._close_window
        )
        close_btn.pack(side="right", padx=2)

    def _minimize_window(self):
        """Минимизировать окно."""
        if self.window:
            self.window.overrideredirect(False)
            self.window.iconify()
            self.window.after(100, lambda: self.window.overrideredirect(True) if self.is_frameless else None)

    def _close_window(self):
        """Закрыть окно."""
        if self.window:
            self.window.event_generate("<<CloseWindow>>")

    def _start_drag(self, event):
        """Начать перетаскивание окна."""
        if self.window:
            self.drag_x = event.x
            self.drag_y = event.y

    def _on_drag(self, event):
        """Перетаскивание окна."""
        if self.window and hasattr(self, 'drag_x') and hasattr(self, 'drag_y'):
            delta_x = event.x - self.drag_x
            delta_y = event.y - self.drag_y
            x = self.window.winfo_x() + delta_x
            y = self.window.winfo_y() + delta_y
            self.window.geometry(f"+{x}+{y}")
