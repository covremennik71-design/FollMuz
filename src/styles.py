"""Модуль для стилей, цветов, эффектов и шрифтов приложения."""

import tkinter as tk
from PIL import Image, ImageDraw, ImageTk


class AnimatedWidget:
    """Базовый класс для анимированных виджетов."""

    @staticmethod
    def fade_in(widget, duration=0.3, steps=20):
        step_time = max(1, int(duration * 1000 / steps))

        def animate(step=0):
            if step <= steps:
                alpha = step / steps
                try:
                    widget.attributes("-alpha", alpha)
                except tk.TclError:
                    return
                widget.after(step_time, animate, step + 1)

        try:
            widget.attributes("-alpha", 0)
        except tk.TclError:
            return
        animate()

    @staticmethod
    def fade_out(widget, duration=0.3, steps=20, callback=None):
        step_time = max(1, int(duration * 1000 / steps))

        def animate(step=0):
            if step <= steps:
                alpha = 1 - (step / steps)
                try:
                    widget.attributes("-alpha", alpha)
                except tk.TclError:
                    return
                widget.after(step_time, animate, step + 1)
            else:
                if callback:
                    callback()

        animate()

    @staticmethod
    def slide_in(widget, direction="right", duration=0.3, steps=20):
        try:
            widget.update_idletasks()
            w = widget.winfo_width()
            y = widget.winfo_y()
        except tk.TclError:
            return

        if direction == "right":
            start_x = -w
        elif direction == "left":
            start_x = w
        else:
            start_x = -w

        step_time = max(1, int(duration * 1000 / steps))

        def animate(step=0):
            if step <= steps:
                progress = step / steps
                x = int(start_x * (1 - progress))
                try:
                    widget.place(x=x, y=y)
                except tk.TclError:
                    return
                widget.after(step_time, animate, step + 1)

        animate()


class AppColors:
    """Цветовые схемы приложения."""

    THEMES = {
        "dark": {
            "bg": "#03060c", "fg": "#060b14", "window": "#060b14", "surface": "#0a1220",
            "card": "#101a2b", "card_alt": "#14223a", "surface_hover": "#172741", "surface_press": "#1b2e4a",
            "input_bg": "#09101d", "input_border": "#263853", "placeholder": "#6e819f",
            "primary": "#2173e0", "primary_hover": "#3a8af0", "primary_press": "#1a5fc0",
            "text": "#f0f0f0", "text_secondary": "#9bb0cc", "text_muted": "#6b7280",
            "accent": "#58b7ff", "accent_hover": "#86cbff",
            "success": "#22c55e", "error": "#ef4444", "warning": "#f59e0b", "info": "#4ea3ff",
            "border": "#1c2b43", "border_strong": "#31517d",
            "button_secondary": "#132139", "button_secondary_hover": "#1b3152", "button_secondary_press": "#223b61",
            "button_ghost_hover": "#132238", "button_ghost_press": "#1a2d48",
            "tab_fg": "#08111d", "tab_unselected": "#132139", "tab_unselected_hover": "#1a2e4a",
            "tab_selected": "#2173e0", "tab_selected_hover": "#3a8af0",
            "log_bg": "#07101c", "scrollbar": "#2a4161", "scrollbar_hover": "#3d5e89",
            "progress_track": "#162539", "progress_start": "#2173e0", "progress_end": "#58b7ff",
            "gradient_start": "#0a1628", "gradient_end": "#060b14",
            "shadow": "#000000", "glass_bg": "#101a2b", "glass_border": "#1c2b43",
            "sidebar_bg": "#0a0a0a",
            "sidebar_hover": "#1e3a5f",
            "sidebar_active": "#2173e0",
            "sidebar_text": "#f0f0f0",
        },
        "light": {
            "bg": "#eef4ff", "fg": "#ffffff", "window": "#ffffff", "surface": "#f7faff",
            "card": "#ffffff", "card_alt": "#f3f7ff", "surface_hover": "#edf4ff", "surface_press": "#e4eeff",
            "input_bg": "#ffffff", "input_border": "#bfd0ef", "placeholder": "#8190a8",
            "primary": "#2563eb", "primary_hover": "#1d4ed8", "primary_press": "#1e40af",
            "text": "#000000", "text_secondary": "#333333", "text_muted": "#666666",
            "accent": "#7c3aed", "accent_hover": "#6d28d9",
            "success": "#16a34a", "error": "#dc2626", "warning": "#d97706", "info": "#0284c7",
            "border": "#d8e3f8", "border_strong": "#bfd0ef",
            "button_secondary": "#eff5ff", "button_secondary_hover": "#e6f0ff", "button_secondary_press": "#dce9ff",
            "button_ghost_hover": "#f5f8ff", "button_ghost_press": "#eaf1ff",
            "tab_fg": "#eaf1ff", "tab_unselected": "#f2f6ff", "tab_unselected_hover": "#e8efff",
            "tab_selected": "#2563eb", "tab_selected_hover": "#1d4ed8",
            "log_bg": "#f8fbff", "scrollbar": "#bfd0ef", "scrollbar_hover": "#9db7e8",
            "progress_track": "#d9e6ff", "progress_start": "#2563eb", "progress_end": "#7c3aed",
            "gradient_start": "#f7faff", "gradient_end": "#eef4ff",
            "shadow": "#000000", "glass_bg": "#ffffff", "glass_border": "#d8e3f8",
            "sidebar_bg": "#f5f5f5",
            "sidebar_hover": "#e0e0e0",
            "sidebar_active": "#a0a0a0",
            "sidebar_text": "#333333",
        },
        "gray": {
            "bg": "#8a8a8a", "fg": "#7a7a7a", "window": "#7a7a7a", "surface": "#848484",
            "card": "#949494", "card_alt": "#909090", "surface_hover": "#989898", "surface_press": "#8c8c8c",
            "input_bg": "#a0a0a0", "input_border": "#707070", "placeholder": "#505050",
            "primary": "#5a6a7a", "primary_hover": "#6a7a8a", "primary_press": "#4a5a6a",
            "text": "#1a1a1a", "text_secondary": "#444444", "text_muted": "#333333",
            "accent": "#7a8a9a", "accent_hover": "#8a9aaa",
            "success": "#4a7a4a", "error": "#a04040", "warning": "#b08030", "info": "#5080a0",
            "border": "#707070", "border_strong": "#606060",
            "button_secondary": "#808080", "button_secondary_hover": "#888888", "button_secondary_press": "#787878",
            "button_ghost_hover": "#858585", "button_ghost_press": "#7a7a7a",
            "tab_fg": "#757575", "tab_unselected": "#707070", "tab_unselected_hover": "#787878",
            "tab_selected": "#5a6a7a", "tab_selected_hover": "#6a7a8a",
            "log_bg": "#828282", "scrollbar": "#606060", "scrollbar_hover": "#505050",
            "progress_track": "#606060", "progress_start": "#5a6a7a", "progress_end": "#7a8a9a",
            "gradient_start": "#909090", "gradient_end": "#8a8a8a",
            "shadow": "#000000", "glass_bg": "#949494", "glass_border": "#707070",
        },
        "black-blue": {
            "bg": "#0a0a0a", "fg": "#0d1117", "window": "#0d1117", "surface": "#0c1017",
            "card": "#0e1219", "card_alt": "#101622", "surface_hover": "#121826", "surface_press": "#0f1520",
            "input_bg": "#111820", "input_border": "#1a2240", "placeholder": "#506080",
            "primary": "#4a9eff", "primary_hover": "#6ab0ff", "primary_press": "#3a8eef",
            "text": "#e8e8e8", "text_secondary": "#888888", "text_muted": "#606060",
            "accent": "#58b7ff", "accent_hover": "#78c7ff",
            "success": "#3d8b4f", "error": "#e74c3c", "warning": "#d4a017", "info": "#58b7ff",
            "border": "#1a2240", "border_strong": "#2a3250",
            "button_secondary": "#0e1420", "button_secondary_hover": "#141a28", "button_secondary_press": "#0a1020",
            "button_ghost_hover": "#0c1520", "button_ghost_press": "#0a1220",
            "tab_fg": "#0b0f14", "tab_unselected": "#0d1218", "tab_unselected_hover": "#111420",
            "tab_selected": "#4a9eff", "tab_selected_hover": "#6ab0ff",
            "log_bg": "#0a0e14", "scrollbar": "#1a2240", "scrollbar_hover": "#2a3250",
            "progress_track": "#162030", "progress_start": "#4a9eff", "progress_end": "#58b7ff",
            "gradient_start": "#0c1017", "gradient_end": "#0a0a0a",
            "shadow": "#000000", "glass_bg": "#0e1219", "glass_border": "#1a2240",
        },
        "black-red": {
            "bg": "#0a0a0a", "fg": "#170d0d", "window": "#170d0d", "surface": "#100c0c",
            "card": "#190e0e", "card_alt": "#1c1010", "surface_hover": "#201212", "surface_press": "#1a0e0e",
            "input_bg": "#201111", "input_border": "#2e1a1a", "placeholder": "#805060",
            "primary": "#ff4757", "primary_hover": "#ff6977", "primary_press": "#ef3545",
            "text": "#e8e8e8", "text_secondary": "#888888", "text_muted": "#606060",
            "accent": "#ff6b7a", "accent_hover": "#ff8b9a",
            "success": "#2ed573", "error": "#ff3838", "warning": "#ffa502", "info": "#ff6b7a",
            "border": "#2e1a1a", "border_strong": "#3e2a2a",
            "button_secondary": "#1a0e0e", "button_secondary_hover": "#201212", "button_secondary_press": "#160c0c",
            "button_ghost_hover": "#1c1010", "button_ghost_press": "#140e0e",
            "tab_fg": "#140b0b", "tab_unselected": "#160d0d", "tab_unselected_hover": "#1a0f0f",
            "tab_selected": "#ff4757", "tab_selected_hover": "#ff6977",
            "log_bg": "#0e0a0a", "scrollbar": "#2e1a1a", "scrollbar_hover": "#3e2a2a",
            "progress_track": "#301a1a", "progress_start": "#ff4757", "progress_end": "#ff6b7a",
            "gradient_start": "#100c0c", "gradient_end": "#0a0a0a",
            "shadow": "#000000", "glass_bg": "#190e0e", "glass_border": "#2e1a1a",
        },
        "black-green": {
            "bg": "#0a0a0a", "fg": "#0d170d", "window": "#0d170d", "surface": "#0c100c",
            "card": "#0e190e", "card_alt": "#111c11", "surface_hover": "#151f15", "surface_press": "#111a11",
            "input_bg": "#112011", "input_border": "#1a2e1a", "placeholder": "#508060",
            "primary": "#2ed573", "primary_hover": "#4ed793", "primary_press": "#1ec563",
            "text": "#e8e8e8", "text_secondary": "#888888", "text_muted": "#606060",
            "accent": "#4ee883", "accent_hover": "#6ef8a3",
            "success": "#2ed573", "error": "#ff4757", "warning": "#ffa502", "info": "#4ee883",
            "border": "#1a2e1a", "border_strong": "#2a3e2a",
            "button_secondary": "#0e1a0e", "button_secondary_hover": "#121f12", "button_secondary_press": "#0a160a",
            "button_ghost_hover": "#0c1a0c", "button_ghost_press": "#0a160a",
            "tab_fg": "#0b140b", "tab_unselected": "#0d170d", "tab_unselected_hover": "#111c11",
            "tab_selected": "#2ed573", "tab_selected_hover": "#4ed793",
            "log_bg": "#0a0e0a", "scrollbar": "#1a2e1a", "scrollbar_hover": "#2a3e2a",
            "progress_track": "#1a301a", "progress_start": "#2ed573", "progress_end": "#4ee883",
            "gradient_start": "#0c100c", "gradient_end": "#0a0a0a",
            "shadow": "#000000", "glass_bg": "#0e190e", "glass_border": "#1a2e1a",
        },
        "light-gray": {
            "bg": "#f3f4f6", "fg": "#e5e7eb", "window": "#e5e7eb", "surface": "#f9fafb",
            "card": "#f8f9fa", "card_alt": "#f5f7fa", "surface_hover": "#edf1f5", "surface_press": "#e8ecf0",
            "input_bg": "#ffffff", "input_border": "#d1d5db", "placeholder": "#9ca3af",
            "primary": "#6b7280", "primary_hover": "#7b8290", "primary_press": "#5b6270",
            "text": "#000000", "text_secondary": "#333333", "text_muted": "#555555",
            "accent": "#8b929a", "accent_hover": "#9ba2aa",
            "success": "#4a9a6a", "error": "#b06060", "warning": "#c0a060", "info": "#6b7280",
            "border": "#d1d5db", "border_strong": "#c1c5cb",
            "button_secondary": "#f0f2f4", "button_secondary_hover": "#e8eaec", "button_secondary_press": "#e0e2e4",
            "button_ghost_hover": "#f5f7fa", "button_ghost_press": "#eff1f3",
            "tab_fg": "#d1d5db", "tab_unselected": "#e5e7eb", "tab_unselected_hover": "#dde1e5",
            "tab_selected": "#6b7280", "tab_selected_hover": "#7b8290",
            "log_bg": "#fafbfc", "scrollbar": "#d1d5db", "scrollbar_hover": "#c1c5cb",
            "progress_track": "#e5e7eb", "progress_start": "#6b7280", "progress_end": "#8b929a",
            "gradient_start": "#f8f9fa", "gradient_end": "#f3f4f6",
            "shadow": "#000000", "glass_bg": "#f8f9fa", "glass_border": "#d1d5db",
        },
        "light-blue": {
            "bg": "#f0f7ff", "fg": "#dbeafe", "window": "#dbeafe", "surface": "#f8fafc",
            "card": "#f8fafc", "card_alt": "#f5f9ff", "surface_hover": "#edf5ff", "surface_press": "#e8f0ff",
            "input_bg": "#ffffff", "input_border": "#bfdbfe", "placeholder": "#94a3b8",
            "primary": "#3b82f6", "primary_hover": "#4b92f6", "primary_press": "#2b72e6",
            "text": "#000000", "text_secondary": "#333333", "text_muted": "#555555",
            "accent": "#60a5fa", "accent_hover": "#70b5ff",
            "success": "#10b981", "error": "#ef4444", "warning": "#f59e0b", "info": "#3b82f6",
            "border": "#bfdbfe", "border_strong": "#afcbfe",
            "button_secondary": "#eff6ff", "button_secondary_hover": "#e6f2ff", "button_secondary_press": "#deefff",
            "button_ghost_hover": "#f5f9ff", "button_ghost_press": "#eef5ff",
            "tab_fg": "#bfdbfe", "tab_unselected": "#dbeafe", "tab_unselected_hover": "#cbeafe",
            "tab_selected": "#3b82f6", "tab_selected_hover": "#4b92f6",
            "log_bg": "#f8fbff", "scrollbar": "#bfdbfe", "scrollbar_hover": "#afcbfe",
            "progress_track": "#dbeafe", "progress_start": "#3b82f6", "progress_end": "#60a5fa",
            "gradient_start": "#f8fafc", "gradient_end": "#f0f7ff",
            "shadow": "#000000", "glass_bg": "#f8fafc", "glass_border": "#bfdbfe",
        },
        "light-beige": {
            "bg": "#faf6f1", "fg": "#f5e6d3", "window": "#f5e6d3", "surface": "#fdf8f3",
            "card": "#fdfbf8", "card_alt": "#faf7f3", "surface_hover": "#f5ede5", "surface_press": "#f0e8de",
            "input_bg": "#ffffff", "input_border": "#e8d5c4", "placeholder": "#a09080",
            "primary": "#b4885a", "primary_hover": "#c4986a", "primary_press": "#a4784a",
            "text": "#000000", "text_secondary": "#333333", "text_muted": "#555555",
            "accent": "#d4a574", "accent_hover": "#e4b584",
            "success": "#6a9a6a", "error": "#b06060", "warning": "#c0a060", "info": "#b4885a",
            "border": "#e8d5c4", "border_strong": "#d8c5b4",
            "button_secondary": "#faf6f0", "button_secondary_hover": "#f5efe8", "button_secondary_press": "#f0e8e0",
            "button_ghost_hover": "#faf7f3", "button_ghost_press": "#f5f0eb",
            "tab_fg": "#e8d5c4", "tab_unselected": "#f5e6d3", "tab_unselected_hover": "#ead9c4",
            "tab_selected": "#b4885a", "tab_selected_hover": "#c4986a",
            "log_bg": "#fdfaf5", "scrollbar": "#e8d5c4", "scrollbar_hover": "#d8c5b4",
            "progress_track": "#e8d5c4", "progress_start": "#b4885a", "progress_end": "#d4a574",
            "gradient_start": "#fdf8f3", "gradient_end": "#faf6f1",
            "shadow": "#000000", "glass_bg": "#fdfbf8", "glass_border": "#e8d5c4",
        },
        "light-yellow": {
            "bg": "#fffdf5", "fg": "#fef3c7", "window": "#fef3c7", "surface": "#fefdf5",
            "card": "#fefdf5", "card_alt": "#fefaed", "surface_hover": "#fdf5e5", "surface_press": "#fdf0dd",
            "input_bg": "#ffffff", "input_border": "#fde68a", "placeholder": "#a0a080",
            "primary": "#d4a017", "primary_hover": "#e4b027", "primary_press": "#c49007",
            "text": "#000000", "text_secondary": "#333333", "text_muted": "#555555",
            "accent": "#e8b828", "accent_hover": "#f8c838",
            "success": "#4a9a6a", "error": "#b06060", "warning": "#c0a060", "info": "#d4a017",
            "border": "#fde68a", "border_strong": "#edd67a",
            "button_secondary": "#fffbf0", "button_secondary_hover": "#fef5e0", "button_secondary_press": "#fef0d8",
            "button_ghost_hover": "#fefcf5", "button_ghost_press": "#fef8ed",
            "tab_fg": "#fde68a", "tab_unselected": "#fef3c7", "tab_unselected_hover": "#fdebb7",
            "tab_selected": "#d4a017", "tab_selected_hover": "#e4b027",
            "log_bg": "#fefdf8", "scrollbar": "#fde68a", "scrollbar_hover": "#edd67a",
            "progress_track": "#fde68a", "progress_start": "#d4a017", "progress_end": "#e8b828",
            "gradient_start": "#fefdf5", "gradient_end": "#fffdf5",
            "shadow": "#000000", "glass_bg": "#fefdf5", "glass_border": "#fde68a",
        },
    }

    DARK = THEMES["dark"]
    LIGHT = THEMES["light"]

    @classmethod
    def get_theme(cls, theme_name="dark"):
        return cls.THEMES.get(theme_name, cls.DARK)

    @classmethod
    def get_available_themes(cls):
        return list(cls.THEMES.keys())

    @staticmethod
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(r, g, b):
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


class GradientBackground:
    """Создание градиентного фона."""

    @staticmethod
    def create_gradient(width, height, color1, color2, vertical=True):
        width = max(1, int(width))
        height = max(1, int(height))
        image = Image.new("RGB", (width, height), color1)
        draw = ImageDraw.Draw(image)

        c1 = AppColors.hex_to_rgb(color1)
        c2 = AppColors.hex_to_rgb(color2)

        if vertical:
            denom = max(1, height - 1)
            for i in range(height):
                ratio = i / denom
                r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
                g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
                b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
                draw.line([(0, i), (width, i)], fill=(r, g, b))
        else:
            denom = max(1, width - 1)
            for i in range(width):
                ratio = i / denom
                r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
                g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
                b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
                draw.line([(i, 0), (i, height)], fill=(r, g, b))

        return ImageTk.PhotoImage(image)

    @staticmethod
    def apply_to_frame(frame, color1, color2, vertical=True):
        frame.update_idletasks()
        try:
            width = frame.winfo_width()
            height = frame.winfo_height()
        except tk.TclError:
            return

        if width > 1 and height > 1:
            if hasattr(frame, "_bg_label") and frame._bg_label.winfo_exists():
                frame._bg_label.destroy()

            bg_image = GradientBackground.create_gradient(width, height, color1, color2, vertical)
            bg_label = tk.Label(frame, image=bg_image, borderwidth=0, highlightthickness=0)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            bg_label.lower()
            frame._bg_image = bg_image
            frame._bg_label = bg_label


class AppStyles:
    """Готовые пресеты стилей для customtkinter."""

    CORNER_RADIUS_SMALL = 8
    CORNER_RADIUS_MEDIUM = 12
    CORNER_RADIUS_LARGE = 20

    PADDING_SMALL = 5
    PADDING_MEDIUM = 10
    PADDING_LARGE = 20

    ANIMATION_DURATION_FAST = 0.15
    ANIMATION_DURATION_NORMAL = 0.3
    ANIMATION_DURATION_SLOW = 0.5

    @staticmethod
    def add_shadow(widget, radius=5):
        widget.configure(
            border_width=1,
            border_color="#333333"
        )

    @staticmethod
    def apply_glass_morphism(widget, colors=None):
        if colors:
            widget.configure(
                fg_color=colors.get("glass_bg", "#101a2b"),
                border_width=1,
                border_color=colors.get("glass_border", "#1c2b43"),
            )
        else:
            widget.configure(
                fg_color="#101a2b",
                border_width=1,
                border_color="#1c2b43",
            )

    @staticmethod
    def panel(colors, variant="surface"):
        fg_map = {
            "surface": colors["surface"],
            "card": colors["card"],
            "card_alt": colors["card_alt"],
            "log": colors["log_bg"],
        }
        return {
            "fg_color": fg_map.get(variant, colors["surface"]),
            "border_width": 1,
            "border_color": colors.get("border", "#1c2b43"),
        }