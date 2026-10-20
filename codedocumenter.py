#!/usr/bin/env python3
"""
Code Documenter - Professional UI Edition
------------------------------------------
Single-file GUI tool that turns a project folder into a full textual
documentation (folder tree + contents of every source file + metadata
for images / binary files).

All original functionality preserved. Frontend redesigned with:
  - Refined color palette and typography
  - Animated button hover transitions (smooth color interpolation)
  - Indeterminate progress bar during scanning
  - Pulsing drop-zone feedback while dragging
  - Status indicator with colored accent bar
  - Success animation on Copy
  - Card-based layout with clean separation

Optional dependencies:
  pip install tkinterdnd2 pillow
"""

import os
import time
import threading
import hashlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# ----- optional drag-and-drop ------------------------------------------------
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

# ----- optional image library ------------------------------------------------
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


# ----- constants -------------------------------------------------------------
IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".ico", ".tif", ".tiff", ".svg", ".heic", ".avif",
}

SKIP_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".idea", ".vscode", "dist", "build", "target", "bin", "obj",
    ".pytest_cache", ".mypy_cache", ".tox", ".gradle", ".next", ".nuxt",
    ".cache", ".sass-cache", "bower_components", "vendor",
}


# =============================================================================
#  Color palette (refined light theme with a deep-navy header)
# =============================================================================
COLOR_BG                = "#eef2f7"
COLOR_CARD              = "#ffffff"
COLOR_CARD_ALT          = "#f8fafc"
COLOR_BORDER            = "#e2e8f0"
COLOR_BORDER_STRONG     = "#cbd5e1"

COLOR_TEXT              = "#1e293b"
COLOR_TEXT_STRONG       = "#0f172a"
COLOR_TEXT_MUTED        = "#64748b"
COLOR_TEXT_FAINT        = "#94a3b8"

COLOR_PRIMARY           = "#1e40af"
COLOR_PRIMARY_HOVER     = "#2563eb"
COLOR_PRIMARY_PRESS     = "#1e3a8a"

COLOR_HEADER_BG         = "#0f172a"
COLOR_HEADER_ACCENT     = "#3b82f6"
COLOR_HEADER_TEXT       = "#ffffff"
COLOR_HEADER_SUB        = "#94a3b8"

COLOR_DROP_IDLE         = "#f8fafc"
COLOR_DROP_HOVER        = "#eff6ff"
COLOR_DROP_BORDER       = "#cbd5e1"
COLOR_DROP_BORDER_HOVER = "#3b82f6"
COLOR_DROP_TEXT         = "#64748b"

COLOR_SUCCESS           = "#10b981"
COLOR_SUCCESS_DARK      = "#059669"
COLOR_WARNING           = "#f59e0b"
COLOR_ERROR             = "#ef4444"
COLOR_INFO              = "#3b82f6"

COLOR_BTN_BG            = "#ffffff"
COLOR_BTN_HOVER         = "#f1f5f9"
COLOR_BTN_BORDER        = "#d8e0ea"
COLOR_BTN_TEXT          = "#334155"


# =============================================================================
#  Color helpers (for smooth animations)
# =============================================================================

def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(rgb[0]))),
        max(0, min(255, int(rgb[1]))),
        max(0, min(255, int(rgb[2]))),
    )


def _lerp_color(c1, c2, t):
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex((r1 + (r2 - r1) * t,
                        g1 + (g2 - g1) * t,
                        b1 + (b2 - b1) * t))


def _normalize_color(widget, color):
    """Convert a Tk color (name or hex) to a #rrggbb string."""
    if isinstance(color, str) and color.startswith("#") and len(color) in (4, 7):
        return color
    try:
        r, g, b = widget.winfo_rgb(color)
        return _rgb_to_hex((r // 256, g // 256, b // 256))
    except Exception:
        return "#ffffff"


# =============================================================================
#  Utilities (unchanged from original)
# =============================================================================

def format_size(n):
    try:
        n = float(n)
    except Exception:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            if unit == "B":
                return "%d %s" % (int(n), unit)
            return "%.2f %s" % (n, unit)
        n /= 1024.0
    return "%.2f PB" % n


def list_entries(path, skip_dirs=True, include_hidden=False):
    try:
        entries = sorted(os.listdir(path))
    except OSError:
        return [], []
    dirs, files = [], []
    for e in entries:
        if not include_hidden and e.startswith("."):
            continue
        full = os.path.join(path, e)
        try:
            is_dir = os.path.isdir(full)
        except OSError:
            continue
        if is_dir:
            if skip_dirs and e in SKIP_DIRS:
                continue
            dirs.append(e)
        elif os.path.isfile(full):
            files.append(e)
    return dirs, files


def iter_files(folder, skip_dirs=True, include_hidden=False):
    for root, dirs, files in os.walk(folder):
        if skip_dirs:
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]
        dirs.sort()
        files.sort()
        for f in files:
            yield os.path.join(root, f)


def render_tree(folder, skip_dirs=True, include_hidden=False):
    lines = [os.path.basename(os.path.abspath(folder)) + "/"]

    def walk(path, prefix):
        dirs, files = list_entries(path, skip_dirs, include_hidden)
        items = [(d, True) for d in dirs] + [(f, False) for f in files]
        for i, (name, is_dir) in enumerate(items):
            last = (i == len(items) - 1)
            connector = "└── " if last else "├── "
            lines.append(prefix + connector + name + ("/" if is_dir else ""))
            if is_dir:
                walk(os.path.join(path, name), prefix + ("    " if last else "│   "))

    walk(folder, "")
    return "\n".join(lines)


def compute_signature(folder, skip_dirs=True, include_hidden=False):
    h = hashlib.md5()
    for path in iter_files(folder, skip_dirs, include_hidden):
        try:
            st = os.stat(path)
        except OSError:
            continue
        h.update(path.encode("utf-8", "surrogateescape"))
        h.update(b"|")
        h.update(str(st.st_mtime_ns).encode("ascii"))
        h.update(b"|")
        h.update(str(st.st_size).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def is_binary_file(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
    except OSError:
        return True
    if not chunk:
        return False
    return b"\x00" in chunk


def read_text(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("latin-1")
        except Exception:
            return None


def get_image_dimensions(path):
    ext = os.path.splitext(path)[1].lower()
    if PIL_AVAILABLE:
        try:
            with Image.open(path) as img:
                return img.size
        except Exception:
            pass
    try:
        with open(path, "rb") as f:
            head = f.read(32)
    except OSError:
        return None
    try:
        if ext == ".png" and len(head) >= 24:
            return (int.from_bytes(head[16:20], "big"),
                    int.from_bytes(head[20:24], "big"))
        if ext == ".gif" and len(head) >= 10:
            return (int.from_bytes(head[6:8], "little"),
                    int.from_bytes(head[8:10], "little"))
        if ext == ".bmp" and len(head) >= 26:
            return (int.from_bytes(head[18:22], "little"),
                    int.from_bytes(head[22:26], "little"))
    except Exception:
        pass
    return None


# =============================================================================
#  Document builder (unchanged)
# =============================================================================

def build_document(folder, skip_dirs=True, include_hidden=False, max_mb=5):
    sep_eq = "=" * 80
    sep_dash = "-" * 80
    parts = []

    parts.append(sep_eq)
    parts.append("PROJECT DOCUMENTATION")
    parts.append("Root folder: " + os.path.abspath(folder))
    parts.append("Generated: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    parts.append(sep_eq)
    parts.append("")
    parts.append("FOLDER TREE")
    parts.append(sep_dash)
    parts.append(render_tree(folder, skip_dirs, include_hidden))
    parts.append("")
    parts.append("FILES")
    parts.append(sep_eq)
    parts.append("")

    for path in iter_files(folder, skip_dirs, include_hidden):
        rel = os.path.relpath(path, folder).replace(os.sep, "/")
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        size_str = format_size(size)
        ext = os.path.splitext(path)[1].lower()

        parts.append(sep_dash)

        if ext in IMAGE_EXTS:
            line = rel + ": " + ext + " | size: " + size_str
            dims = get_image_dimensions(path)
            if dims:
                line += " | dims: " + str(dims[0]) + "x" + str(dims[1])
            parts.append(line)
            parts.append(sep_dash)
            parts.append("[image file - content not included]")
            parts.append("")
            continue

        if is_binary_file(path):
            parts.append(rel + ": " + size_str + " | binary")
            parts.append(sep_dash)
            parts.append("[binary file - content not included]")
            parts.append("")
            continue

        if max_mb > 0 and size > max_mb * 1024 * 1024:
            parts.append(rel + ": " + size_str + " | skipped (too large)")
            parts.append(sep_dash)
            parts.append("[file too large - content not included, limit: "
                         + str(max_mb) + " MB]")
            parts.append("")
            continue

        content = read_text(path)
        if content is None:
            parts.append(rel + ": " + size_str + " | unreadable")
            parts.append(sep_dash)
            parts.append("[file could not be read]")
            parts.append("")
            continue

        if content and content.endswith("\n"):
            n_lines = content.count("\n")
        else:
            n_lines = content.count("\n") + (1 if content else 0)

        parts.append(rel + ": " + size_str + " lines: " + str(n_lines))
        parts.append(sep_dash)
        parts.append(content.rstrip("\n"))
        parts.append("")

    parts.append(sep_eq)
    parts.append("END OF DOCUMENTATION")
    parts.append(sep_eq)
    return "\n".join(parts)


# =============================================================================
#  AnimatedButton - flat button with smooth hover transition
# =============================================================================

class AnimatedButton(tk.Frame):
    """A flat button with an animated background/foreground hover transition."""

    def __init__(self, parent, text, command=None,
                 bg=COLOR_BTN_BG, fg=COLOR_BTN_TEXT,
                 hover_bg=COLOR_BTN_HOVER, hover_fg=None,
                 border=COLOR_BTN_BORDER,
                 font=("Segoe UI", 10), padx=20, pady=10,
                 width=None, bold=False, **kwargs):
        super().__init__(parent, bg=border, **kwargs)

        if hover_fg is None:
            hover_fg = fg
        if bold:
            try:
                font = (font[0], font[1], "bold")
            except Exception:
                pass

        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg
        self._hover_fg = hover_fg
        self._anim_job = None
        self._enabled = True

        self.inner = tk.Button(
            self, text=text, command=command,
            bg=bg, fg=fg,
            activebackground=hover_bg, activeforeground=hover_fg,
            relief="flat", bd=0, cursor="hand2",
            font=font, padx=padx, pady=pady,
            highlightthickness=0, takefocus=0,
        )
        if width:
            self.inner.config(width=width)
        self.inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.inner.bind("<Enter>", self._on_enter)
        self.inner.bind("<Leave>", self._on_leave)

    # ----- animation ---------------------------------------------------------
    def _animate_to(self, target_bg, target_fg, steps=7, delay=12):
        if self._anim_job:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None

        try:
            start_bg = _normalize_color(self.inner, self.inner.cget("bg"))
            start_fg = _normalize_color(self.inner, self.inner.cget("fg"))
        except Exception:
            return

        def step(i):
            t = i / steps
            t = 1 - (1 - t) ** 2  # ease-out quadratic
            try:
                self.inner.config(
                    bg=_lerp_color(start_bg, target_bg, t),
                    fg=_lerp_color(start_fg, target_fg, t),
                )
            except Exception:
                pass
            if i < steps:
                self._anim_job = self.after(delay, step, i + 1)
            else:
                self._anim_job = None

        step(1)

    def _on_enter(self, _e):
        if not self._enabled:
            return
        self._animate_to(self._hover_bg, self._hover_fg)

    def _on_leave(self, _e):
        if not self._enabled:
            return
        self._animate_to(self._bg, self._fg)

    # ----- public API --------------------------------------------------------
    def set_text(self, text):
        self.inner.config(text=text)

    def flash_colors(self, bg, fg, hover_bg, hover_fg, hold_ms=1500, reset_to=None):
        """Temporarily override the button colors (e.g. success feedback)."""
        old_bg = self._bg
        old_fg = self._fg
        old_hover_bg = self._hover_bg
        old_hover_fg = self._hover_fg

        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg
        self._hover_fg = hover_fg
        self.inner.config(bg=bg, fg=fg,
                          activebackground=hover_bg, activeforeground=hover_fg)

        def _restore():
            if reset_to:
                self._bg = reset_to[0]
                self._fg = reset_to[1]
                self._hover_bg = reset_to[2]
                self._hover_fg = reset_to[3]
            else:
                self._bg = old_bg
                self._fg = old_fg
                self._hover_bg = old_hover_bg
                self._hover_fg = old_hover_fg
            self.inner.config(bg=self._bg, fg=self._fg,
                              activebackground=self._hover_bg,
                              activeforeground=self._hover_fg)

        self.after(hold_ms, _restore)


# =============================================================================
#  GUI - CodeDocumenter
# =============================================================================

class CodeDocumenter:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Documenter")
        self.root.geometry("1180x840")
        self.root.minsize(860, 560)
        self.root.configure(bg=COLOR_BG)

        self.folder = None
        self.scanning = False
        self.last_signature = None
        self.refresh_job = None
        self._copy_reset_job = None
        self._pulse_job = None
        self._drop_anim_job = None

        self.interval_var = tk.IntVar(value=5)
        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.skip_dirs_var = tk.BooleanVar(value=True)
        self.include_hidden_var = tk.BooleanVar(value=False)
        self.max_mb_var = tk.IntVar(value=5)

        self._build_styles()
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.interval_var.trace_add("write", self._on_interval_change)
        self.schedule_check()

    # =========================================================================
    #  ttk styles
    # =========================================================================
    def _build_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Frames
        style.configure("TFrame", background=COLOR_BG)
        style.configure("Card.TFrame", background=COLOR_CARD)
        style.configure("Header.TFrame", background=COLOR_HEADER_BG)

        # Labels
        style.configure("Card.TLabel",
                        background=COLOR_CARD,
                        foreground=COLOR_TEXT,
                        font=("Segoe UI", 10))
        style.configure("CardMuted.TLabel",
                        background=COLOR_CARD,
                        foreground=COLOR_TEXT_MUTED,
                        font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel",
                        background=COLOR_CARD,
                        foreground=COLOR_TEXT_STRONG,
                        font=("Segoe UI", 11, "bold"))
        style.configure("HeaderTitle.TLabel",
                        background=COLOR_HEADER_BG,
                        foreground=COLOR_HEADER_TEXT,
                        font=("Segoe UI", 17, "bold"))
        style.configure("HeaderSubtitle.TLabel",
                        background=COLOR_HEADER_BG,
                        foreground=COLOR_HEADER_SUB,
                        font=("Segoe UI", 9))

        # Spinbox
        style.configure("TSpinbox",
                        font=("Segoe UI", 10),
                        padding=5,
                        fieldbackground=COLOR_CARD,
                        background=COLOR_CARD,
                        foreground=COLOR_TEXT,
                        arrowcolor=COLOR_TEXT,
                        bordercolor=COLOR_BORDER_STRONG,
                        lightcolor=COLOR_BORDER_STRONG,
                        darkcolor=COLOR_BORDER_STRONG)
        style.map("TSpinbox",
                  fieldbackground=[("!disabled", COLOR_CARD)],
                  foreground=[("!disabled", COLOR_TEXT)],
                  bordercolor=[("focus", COLOR_PRIMARY)],
                  lightcolor=[("focus", COLOR_PRIMARY)],
                  darkcolor=[("focus", COLOR_PRIMARY)])

        # Checkbutton (ttk) - styled for a card background
        style.configure("Card.TCheckbutton",
                        background=COLOR_CARD,
                        foreground=COLOR_TEXT,
                        font=("Segoe UI", 10))
        style.map("Card.TCheckbutton",
                  background=[("active", COLOR_CARD)],
                  foreground=[("active", COLOR_TEXT)])

        # Progress bar (thin, blends with background when idle)
        style.configure("Scan.Horizontal.TProgressbar",
                        troughcolor=COLOR_BG,
                        background=COLOR_HEADER_ACCENT,
                        lightcolor=COLOR_HEADER_ACCENT,
                        darkcolor=COLOR_HEADER_ACCENT,
                        bordercolor=COLOR_BG,
                        borderwidth=0,
                        thickness=4)

    # =========================================================================
    #  UI construction
    # =========================================================================
    def build_ui(self):
        # ---- Header bar --------------------------------------------------
        header = tk.Frame(self.root, bg=COLOR_HEADER_BG, height=78)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        header_inner = tk.Frame(header, bg=COLOR_HEADER_BG)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=28, pady=14)

        title_box = tk.Frame(header_inner, bg=COLOR_HEADER_BG)
        title_box.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(title_box, text="Code Documenter",
                 bg=COLOR_HEADER_BG, fg=COLOR_HEADER_TEXT,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(title_box,
                 text="Professional project documentation generator",
                 bg=COLOR_HEADER_BG, fg=COLOR_HEADER_SUB,
                 font=("Segoe UI", 9)).pack(anchor="w")

        # Thin accent line under the header
        tk.Frame(self.root, bg=COLOR_HEADER_ACCENT, height=3).pack(fill=tk.X)

        # ---- Main content area -------------------------------------------
        main = tk.Frame(self.root, bg=COLOR_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=18)

        # ---- Drop zone ----------------------------------------------------
        self.drop_zone_wrap = tk.Frame(main, bg=COLOR_DROP_BORDER)
        self.drop_zone_wrap.pack(fill=tk.X, pady=(0, 14))

        self.drop_zone = tk.Label(
            self.drop_zone_wrap,
            text="Drop a project folder here\nor use the Select Folder button below",
            bg=COLOR_DROP_IDLE, fg=COLOR_DROP_TEXT,
            font=("Segoe UI", 12), height=5, cursor="hand2",
            justify=tk.CENTER, bd=0, highlightthickness=0,
        )
        self.drop_zone.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        if DND_AVAILABLE:
            try:
                self.drop_zone.drop_target_register(DND_FILES)
                self.drop_zone.dnd_bind("<<Drop>>", self.on_drop)
                self.drop_zone.dnd_bind("<<DropEnter>>", self.on_drop_enter)
                self.drop_zone.dnd_bind("<<DropLeave>>", self.on_drop_leave)
            except Exception:
                pass

        # ---- Action buttons ----------------------------------------------
        btn_row = tk.Frame(main, bg=COLOR_BG)
        btn_row.pack(fill=tk.X, pady=(0, 16))

        self.select_btn = AnimatedButton(
            btn_row, "Select Folder", command=self.select_folder,
            bg=COLOR_PRIMARY, fg="#ffffff",
            hover_bg=COLOR_PRIMARY_HOVER, hover_fg="#ffffff",
            border=COLOR_PRIMARY, width=16, bold=True,
        )
        self.select_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.refresh_btn = AnimatedButton(
            btn_row, "Refresh Now", command=self.force_refresh,
            bg=COLOR_BTN_BG, fg=COLOR_BTN_TEXT,
            hover_bg=COLOR_BTN_HOVER, hover_fg=COLOR_TEXT_STRONG,
            border=COLOR_BTN_BORDER, width=16,
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=8)

        self.copy_btn = AnimatedButton(
            btn_row, "Copy", command=self.copy_output,
            bg=COLOR_BTN_BG, fg=COLOR_BTN_TEXT,
            hover_bg=COLOR_BTN_HOVER, hover_fg=COLOR_TEXT_STRONG,
            border=COLOR_BTN_BORDER, width=16,
        )
        self.copy_btn.pack(side=tk.LEFT, padx=8)

        self.save_btn = AnimatedButton(
            btn_row, "Save Output", command=self.save_output,
            bg=COLOR_BTN_BG, fg=COLOR_BTN_TEXT,
            hover_bg=COLOR_BTN_HOVER, hover_fg=COLOR_TEXT_STRONG,
            border=COLOR_BTN_BORDER, width=16,
        )
        self.save_btn.pack(side=tk.LEFT, padx=8)

        self.clear_btn = AnimatedButton(
            btn_row, "Clear", command=self.clear_output,
            bg=COLOR_BTN_BG, fg=COLOR_BTN_TEXT,
            hover_bg=COLOR_BTN_HOVER, hover_fg=COLOR_TEXT_STRONG,
            border=COLOR_BTN_BORDER, width=16,
        )
        self.clear_btn.pack(side=tk.LEFT, padx=8)

        # ---- Settings card ------------------------------------------------
        settings_card = tk.Frame(main, bg=COLOR_CARD,
                                 highlightbackground=COLOR_BORDER,
                                 highlightthickness=1)
        settings_card.pack(fill=tk.X, pady=(0, 12))

        settings_inner = tk.Frame(settings_card, bg=COLOR_CARD)
        settings_inner.pack(fill=tk.X, padx=18, pady=14)

        tk.Label(settings_inner, text="SETTINGS",
                 bg=COLOR_CARD, fg=COLOR_TEXT_MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 10))

        settings = tk.Frame(settings_inner, bg=COLOR_CARD)
        settings.pack(fill=tk.X)

        # Refresh interval
        col_interval = tk.Frame(settings, bg=COLOR_CARD)
        col_interval.grid(row=0, column=0, sticky="w", padx=(0, 28))
        tk.Label(col_interval, text="REFRESH INTERVAL (SEC)",
                 bg=COLOR_CARD, fg=COLOR_TEXT_FAINT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Spinbox(col_interval, from_=1, to=3600,
                    textvariable=self.interval_var, width=10).pack(
            anchor="w", pady=(4, 0))

        # Checkbuttons
        ttk.Checkbutton(settings, text="Auto refresh",
                        variable=self.auto_refresh_var,
                        style="Card.TCheckbutton").grid(
            row=0, column=1, sticky="sw", padx=(0, 22), pady=(16, 0))
        ttk.Checkbutton(settings, text="Skip build dirs",
                        variable=self.skip_dirs_var,
                        style="Card.TCheckbutton").grid(
            row=0, column=2, sticky="sw", padx=(0, 22), pady=(16, 0))
        ttk.Checkbutton(settings, text="Include hidden",
                        variable=self.include_hidden_var,
                        style="Card.TCheckbutton").grid(
            row=0, column=3, sticky="sw", padx=(0, 22), pady=(16, 0))

        # Max file size
        col_max = tk.Frame(settings, bg=COLOR_CARD)
        col_max.grid(row=0, column=4, sticky="w")
        tk.Label(col_max, text="MAX FILE SIZE (MB)",
                 bg=COLOR_CARD, fg=COLOR_TEXT_FAINT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Spinbox(col_max, from_=0, to=1000,
                    textvariable=self.max_mb_var, width=10).pack(
            anchor="w", pady=(4, 0))

        # ---- Progress strip (thin, invisible when idle) -------------------
        self.progress_wrap = tk.Frame(main, bg=COLOR_BG, height=4)
        self.progress_wrap.pack(fill=tk.X, pady=(0, 10))
        self.progress_wrap.pack_propagate(False)

        self.progress = ttk.Progressbar(
            self.progress_wrap,
            style="Scan.Horizontal.TProgressbar",
            mode="indeterminate",
        )
        self.progress.pack(fill=tk.BOTH, expand=True)

        # ---- Status card --------------------------------------------------
        status_card = tk.Frame(main, bg=COLOR_CARD,
                               highlightbackground=COLOR_BORDER,
                               highlightthickness=1)
        status_card.pack(fill=tk.X, pady=(0, 12))

        self.status_accent = tk.Frame(status_card, bg=COLOR_INFO, width=4)
        self.status_accent.pack(side=tk.LEFT, fill=tk.Y)
        self.status_accent.pack_propagate(False)

        status_inner = tk.Frame(status_card, bg=COLOR_CARD)
        status_inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                         padx=14, pady=10)

        self.status_var = tk.StringVar(
            value=("Ready. Select or drop a folder to begin."
                   if DND_AVAILABLE
                   else "Ready. Drag-and-drop module not installed; use 'Select Folder'."))

        tk.Label(status_inner, textvariable=self.status_var,
                 bg=COLOR_CARD, fg=COLOR_TEXT,
                 font=("Segoe UI", 9), anchor="w").pack(fill=tk.X)

        # ---- Output area --------------------------------------------------
        text_card = tk.Frame(main, bg=COLOR_CARD,
                             highlightbackground=COLOR_BORDER,
                             highlightthickness=1)
        text_card.pack(fill=tk.BOTH, expand=True)

        text_header = tk.Frame(text_card, bg=COLOR_CARD_ALT, height=34)
        text_header.pack(fill=tk.X)
        text_header.pack_propagate(False)

        tk.Label(text_header, text="OUTPUT",
                 bg=COLOR_CARD_ALT, fg=COLOR_TEXT_MUTED,
                 font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=16, pady=9)

        tk.Frame(text_card, bg=COLOR_BORDER, height=1).pack(fill=tk.X)

        self.text = scrolledtext.ScrolledText(
            text_card, wrap=tk.NONE, font=("Consolas", 10), undo=False,
            bg=COLOR_CARD, fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            selectbackground="#bfdbfe", selectforeground=COLOR_TEXT_STRONG,
            relief=tk.FLAT, borderwidth=0,
            padx=14, pady=12,
        )
        self.text.pack(fill=tk.BOTH, expand=True)

    # =========================================================================
    #  Status helpers (also drive the colored accent bar)
    # =========================================================================
    def _set_status(self, text, color=None):
        self.status_var.set(text)
        if color:
            self.status_accent.config(bg=color)

    # =========================================================================
    #  Drop zone animations
    # =========================================================================
    def _animate_drop_colors(self, target_border, target_bg, target_fg,
                             steps=6, delay=12):
        if self._drop_anim_job:
            try:
                self.root.after_cancel(self._drop_anim_job)
            except Exception:
                pass
            self._drop_anim_job = None

        try:
            start_border = _normalize_color(
                self.drop_zone_wrap, self.drop_zone_wrap.cget("bg"))
            start_bg = _normalize_color(self.drop_zone, self.drop_zone.cget("bg"))
            start_fg = _normalize_color(self.drop_zone, self.drop_zone.cget("fg"))
        except Exception:
            return

        def step(i):
            t = i / steps
            t = 1 - (1 - t) ** 2
            try:
                self.drop_zone_wrap.config(
                    bg=_lerp_color(start_border, target_border, t))
                self.drop_zone.config(
                    bg=_lerp_color(start_bg, target_bg, t),
                    fg=_lerp_color(start_fg, target_fg, t))
            except Exception:
                pass
            if i < steps:
                self._drop_anim_job = self.root.after(delay, step, i + 1)
            else:
                self._drop_anim_job = None

        step(1)

    def _set_drop_hover(self, hovering):
        if hovering:
            self._animate_drop_colors(COLOR_DROP_BORDER_HOVER,
                                      COLOR_DROP_HOVER,
                                      COLOR_PRIMARY)
        else:
            self._animate_drop_colors(COLOR_DROP_BORDER,
                                      COLOR_DROP_IDLE,
                                      COLOR_DROP_TEXT)

    # =========================================================================
    #  Drag & drop callbacks
    # =========================================================================
    def on_drop_enter(self, event):
        self._set_drop_hover(True)
        return getattr(event, "action", None)

    def on_drop_leave(self, event):
        self._set_drop_hover(False)

    def on_drop(self, event):
        self._set_drop_hover(False)
        try:
            paths = self.root.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        if not paths:
            return
        path = paths[0]
        if isinstance(path, str):
            path = path.strip("{}")
        if not path:
            return
        if os.path.isdir(path):
            self.set_folder(path)
        elif os.path.isfile(path):
            self.set_folder(os.path.dirname(path))
        else:
            messagebox.showerror("Invalid drop",
                                 "Not a valid folder:\n" + path)

    # =========================================================================
    #  Folder selection
    # =========================================================================
    def select_folder(self):
        path = filedialog.askdirectory(title="Select project folder")
        if path:
            self.set_folder(path)

    def set_folder(self, path):
        path = os.path.abspath(path)
        self.folder = path
        display = path
        if len(display) > 100:
            display = "..." + display[-97:]
        self.drop_zone.config(text="Current folder:\n" + display)
        self.last_signature = None
        self.force_refresh()

    # =========================================================================
    #  Scan control
    # =========================================================================
    def _read_int(self, var, default):
        try:
            return int(var.get())
        except Exception:
            try:
                var.set(default)
            except Exception:
                pass
            return default

    def force_refresh(self):
        if not self.folder:
            messagebox.showinfo("Info", "Select or drop a folder first.")
            return
        self.start_scan(force=True)

    def _start_scan_visuals(self):
        try:
            self.progress.start(14)
        except Exception:
            pass

    def _stop_scan_visuals(self):
        try:
            self.progress.stop()
        except Exception:
            pass

    def start_scan(self, force=False):
        if self.scanning or not self.folder:
            return
        self.scanning = True
        self._set_status("Scanning project files...", COLOR_WARNING)
        self._start_scan_visuals()

        folder = self.folder
        skip_dirs = bool(self.skip_dirs_var.get())
        include_hidden = bool(self.include_hidden_var.get())
        max_mb = self._read_int(self.max_mb_var, 5)
        last_sig = self.last_signature

        def worker():
            try:
                sig = compute_signature(folder, skip_dirs, include_hidden)
                if not force and sig == last_sig:
                    self.root.after(0, self.on_scan_unchanged)
                    return
                doc = build_document(folder, skip_dirs, include_hidden, max_mb)
                self.root.after(0, self.on_scan_done, doc, sig)
            except Exception as e:
                self.root.after(0, self.on_scan_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def on_scan_unchanged(self):
        self.scanning = False
        self._stop_scan_visuals()
        self._set_status("No changes detected at "
                         + time.strftime("%H:%M:%S") + ".", COLOR_INFO)

    def on_scan_done(self, doc, sig):
        self.scanning = False
        self._stop_scan_visuals()
        self.last_signature = sig
        try:
            ypos = self.text.yview()[0]
        except Exception:
            ypos = 0.0
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", doc)
        try:
            self.text.yview_moveto(ypos)
        except Exception:
            pass
        lines = doc.count("\n") + 1
        size_str = format_size(len(doc.encode("utf-8", "ignore")))
        self._set_status(
            "Updated at " + time.strftime("%H:%M:%S")
            + "  |  " + str(lines) + " lines"
            + "  |  " + size_str + " of text",
            COLOR_SUCCESS,
        )

    def on_scan_error(self, msg):
        self.scanning = False
        self._stop_scan_visuals()
        self._set_status("Error: " + msg, COLOR_ERROR)

    # =========================================================================
    #  Scheduler
    # =========================================================================
    def _on_interval_change(self, *args):
        try:
            v = int(self.interval_var.get())
        except Exception:
            return
        if v >= 1:
            self.schedule_check()

    def schedule_check(self):
        if self.refresh_job:
            try:
                self.root.after_cancel(self.refresh_job)
            except Exception:
                pass
            self.refresh_job = None
        interval = max(1, self._read_int(self.interval_var, 5))
        self.refresh_job = self.root.after(interval * 1000, self.auto_tick)

    def auto_tick(self):
        try:
            if (self.auto_refresh_var.get()
                    and self.folder
                    and not self.scanning):
                self.start_scan(force=False)
        finally:
            self.schedule_check()

    # =========================================================================
    #  Actions
    # =========================================================================
    def copy_output(self):
        content = self.text.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showinfo("Info", "Output is empty, nothing to copy.")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.root.update_idletasks()
        except Exception as e:
            messagebox.showerror("Error", "Could not copy to clipboard: " + str(e))
            return

        # Visual feedback: flash the button green, then restore
        self.copy_btn.set_text("Copied!")
        self.copy_btn.flash_colors(
            bg=COLOR_SUCCESS, fg="#ffffff",
            hover_bg=COLOR_SUCCESS_DARK, hover_fg="#ffffff",
            hold_ms=1500,
            reset_to=(COLOR_BTN_BG, COLOR_BTN_TEXT,
                      COLOR_BTN_HOVER, COLOR_TEXT_STRONG),
        )
        self.copy_btn.after(1500, lambda: self.copy_btn.set_text("Copy"))

        if self._copy_reset_job:
            try:
                self.root.after_cancel(self._copy_reset_job)
            except Exception:
                pass
            self._copy_reset_job = None

        size_str = format_size(len(content.encode("utf-8", "ignore")))
        self._set_status(
            "Copied to clipboard at " + time.strftime("%H:%M:%S")
            + "  |  " + size_str + " of text",
            COLOR_SUCCESS,
        )

    def save_output(self):
        content = self.text.get("1.0", tk.END)
        if not content.strip():
            messagebox.showinfo("Info", "Output is empty.")
            return
        base = "documentation.txt"
        if self.folder:
            base = os.path.basename(os.path.normpath(self.folder)) + "_doc.txt"
        path = filedialog.asksaveasfilename(
            title="Save documentation",
            defaultextension=".txt",
            initialfile=base,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Saved", "Saved to:\n" + path)
        except OSError as e:
            messagebox.showerror("Error", "Could not save: " + str(e))

    def clear_output(self):
        self.text.delete("1.0", tk.END)
        self._set_status("Output cleared.", COLOR_INFO)

    # =========================================================================
    #  Close handler
    # =========================================================================
    def on_close(self):
        for job_attr in ("refresh_job", "_copy_reset_job",
                         "_pulse_job", "_drop_anim_job"):
            job = getattr(self, job_attr, None)
            if job:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
                setattr(self, job_attr, None)
        try:
            self.progress.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


# =============================================================================
#  Entry point
# =============================================================================

def main():
    root = None
    if DND_AVAILABLE:
        try:
            root = TkinterDnD.Tk()
        except Exception:
            root = None
    if root is None:
        root = tk.Tk()
    CodeDocumenter(root)
    root.mainloop()


if __name__ == "__main__":
    main()