# this file is fully vibecoded
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from tkinter import filedialog as fd
from tkinter.font import Font as _TkFont

import customtkinter as ctk
from PIL import Image, ImageTk

# ── Пути ──────────────────────────────────────────────────────────────────────

if getattr(sys, "frozen", False):
    _MEIPASS     = Path(sys._MEIPASS)
    RES_DIR      = _MEIPASS / "resources"
    _BUNDLED_CFG = _MEIPASS / "config.json"
    BASE_DIR     = Path(sys.executable).parent   # папка рядом с .exe
else:
    _MEIPASS     = None
    BASE_DIR     = Path(__file__).parent
    RES_DIR      = BASE_DIR / "resources"
    _BUNDLED_CFG = BASE_DIR / "config.json"

LOGO_PATH  = RES_DIR / "logo.png"
ICONS_DIR  = RES_DIR / "icons"

_FONT_REGULAR = RES_DIR / "MTSCompact-Regular.ttf"
_FONT_BOLD    = RES_DIR / "MTSCompact-Bold.ttf"
_FONT_FAMILY  = "MTS Compact"


def _get_config_path() -> Path:
    """AppData / Application Support на всех платформах, независимо от режима запуска."""
    sys_name = platform.system()
    if sys_name == "Windows":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys_name == "Darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "MTSLauncher" / "config.json"


CONFIG_PATH = _get_config_path()

# ── Константы ─────────────────────────────────────────────────────────────────

MTS_RED     = "#FF0032"
MTS_RED_HOV = "#CC0029"
WIN_W       = 273
WIN_H       = 740
MIN_W       = 240
MIN_H       = 450

CARD_BG = ("gray88", "gray20")


# ── Шрифты ────────────────────────────────────────────────────────────────────

def _install_fonts() -> str:
    if not _FONT_REGULAR.exists() or not _FONT_BOLD.exists():
        return "Arial"
    if platform.system() == "Darwin":
        dest = Path.home() / "Library" / "Fonts"
    elif platform.system() == "Windows":
        dest = Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"
    else:
        dest = Path.home() / ".local" / "share" / "fonts"
    try:
        dest.mkdir(parents=True, exist_ok=True)
        for src in (_FONT_REGULAR, _FONT_BOLD):
            dst = dest / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
    except Exception:
        return "Arial"
    return _FONT_FAMILY


_F = _install_fonts()


# ── Иконки ────────────────────────────────────────────────────────────────────

def _icon(name: str, size: tuple[int, int] = (18, 18)) -> ctk.CTkImage | None:
    path = ICONS_DIR / f"{name}.png"
    if not path.exists():
        return None
    img = Image.open(path)
    return ctk.CTkImage(light_image=img, dark_image=img, size=size)


# ── Конфиг ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        if _BUNDLED_CFG and _BUNDLED_CFG.exists():
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_BUNDLED_CFG, CONFIG_PATH)
        else:
            raise FileNotFoundError(f"config.json не найден:\n  {CONFIG_PATH}")
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise FileNotFoundError(f"Ошибка чтения config.json:\n  {CONFIG_PATH}\n  {e}")


def _save_config(cfg: dict) -> bool:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


def _abs(p: str) -> Path:
    ap = Path(p)
    return ap if ap.is_absolute() else BASE_DIR / ap


# ── Диалог редактирования карточки ────────────────────────────────────────────

class _EditDialog(ctk.CTkToplevel):

    def __init__(self, parent, name: str, desc: str):
        super().__init__(parent)
        self.title("Редактировать")
        self.resizable(False, False)
        self.grab_set()
        self._result: tuple[str, str] | None = None

        ctk.CTkLabel(self, text="Название:", font=(_F, 12)).pack(
            padx=20, pady=(16, 2), anchor="w"
        )
        self._name_e = ctk.CTkEntry(self, width=260, font=(_F, 12))
        self._name_e.insert(0, name)
        self._name_e.pack(padx=20, pady=(0, 10))

        ctk.CTkLabel(self, text="Описание:", font=(_F, 12)).pack(
            padx=20, pady=(0, 2), anchor="w"
        )
        self._desc_e = ctk.CTkEntry(self, width=260, font=(_F, 12))
        self._desc_e.insert(0, desc)
        self._desc_e.pack(padx=20, pady=(0, 16))

        ctk.CTkButton(
            self, text="Сохранить",
            font=(_F, 12, "bold"),
            fg_color=MTS_RED, hover_color=MTS_RED_HOV,
            command=self._save,
        ).pack(padx=20, pady=(0, 16), fill="x")

        self.bind("<Return>", lambda _: self._save())
        self._name_e.focus()
        self.after(50, self._center)
        self.wait_window()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _save(self):
        self._result = (self._name_e.get().strip(), self._desc_e.get().strip())
        self.destroy()

    @property
    def result(self) -> tuple[str, str] | None:
        return self._result


# ── AppCard ───────────────────────────────────────────────────────────────────

class AppCard(ctk.CTkFrame):

    def __init__(self, parent, index: int, app_cfg: dict, on_save: callable,
                 on_delete: callable,
                 icon_folder: ctk.CTkImage | None,
                 icon_pencil: ctk.CTkImage | None,
                 **kw):
        super().__init__(parent, **kw)
        self._index       = index
        self._cfg         = app_cfg
        self._on_save     = on_save
        self._on_delete   = on_delete
        self._icon_folder = icon_folder
        self._icon_pencil = icon_pencil
        self._proc: subprocess.Popen | None = None
        self._hide_id: str | None = None
        self._build()
        self._refresh_state()
        self._setup_hover()

    def _build(self):
        ctk.CTkFrame(self, fg_color=MTS_RED, width=5, height=1, corner_radius=0).pack(
            side="left", fill="y"
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True, padx=(12, 14), pady=(12, 8))

        # header: название + карандаш
        hdr = ctk.CTkFrame(body, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 2))

        self._name_lbl = ctk.CTkLabel(
            hdr,
            text=self._cfg.get("name", f"Приложение {self._index + 1}"),
            font=(_F, 13, "bold"),
            anchor="w",
        )
        self._name_lbl.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            hdr,
            text="" if self._icon_pencil else "✏",
            image=self._icon_pencil,
            width=26, height=26,
            fg_color=("gray72", "gray30"), hover_color=("gray62", "gray40"),
            command=self._edit_card,
        ).pack(side="right", padx=(4, 0))

        # описание + крестик удаления (справа, появляется при наведении)
        desc_row = ctk.CTkFrame(body, fg_color="transparent")
        desc_row.pack(fill="x", pady=(0, 4))

        self._desc_lbl = ctk.CTkLabel(
            desc_row,
            text=self._cfg.get("description", ""),
            font=(_F, 11),
            text_color="gray",
            anchor="w",
        )
        self._desc_lbl.pack(side="left", fill="x", expand=True)

        _icon_x = _icon("x", (14, 14))
        self._del_btn = ctk.CTkButton(
            desc_row,
            text="" if _icon_x else "✕",
            image=_icon_x,
            width=26, height=26,
            fg_color=("gray72", "gray30"), hover_color=("#c0392b", "#922b21"),
            command=lambda: self._on_delete(self),
        )
        # не пакуем — появится при наведении

        # имя файла + кнопка выбора
        file_row = ctk.CTkFrame(body, fg_color="transparent")
        file_row.pack(fill="x", pady=(0, 6))

        self._file_lbl = ctk.CTkLabel(
            file_row, text="",
            font=(_F, 10), text_color="gray", anchor="w",
        )
        self._file_lbl.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            file_row,
            text="" if self._icon_folder else "📁",
            image=self._icon_folder,
            width=28, height=26,
            fg_color=("gray72", "gray30"), hover_color=("gray62", "gray40"),
            command=self._pick_exe,
        ).pack(side="right")

        # кнопка запуска
        self._launch_btn = ctk.CTkButton(
            body,
            text="▶ Запустить",
            height=38,
            font=(_F, 12, "bold"),
            fg_color=MTS_RED, hover_color=MTS_RED_HOV,
            corner_radius=6,
            command=self._launch,
        )
        self._launch_btn.pack(fill="x")

    _BTN_DISABLED = dict(
        state="disabled",
        fg_color="transparent", hover_color=CARD_BG,
        border_width=2, border_color=("gray60", "gray50"),
        text_color=("gray50", "gray50"),
    )
    _BTN_ACTIVE = dict(
        state="normal",
        fg_color=MTS_RED, hover_color=MTS_RED_HOV,
        border_width=0, text_color=("white", "white"),
    )

    def _refresh_state(self):
        path_str = self._cfg.get("path", "")
        if not path_str:
            self._file_lbl.configure(text="exe не выбран", text_color=MTS_RED)
            self._launch_btn.configure(**self._BTN_DISABLED)
        else:
            fname = Path(path_str).name
            exists = _abs(path_str).exists()
            self._file_lbl.configure(
                text=fname,
                text_color=("black", "white") if exists else "#e74c3c",
            )
            self._launch_btn.configure(**(self._BTN_ACTIVE if exists else self._BTN_DISABLED))

    def _pick_exe(self):
        p = fd.askopenfilename(
            title="Выберите исполняемый файл",
            filetypes=[("Исполняемый файл", "*.exe"), ("Все файлы", "*.*")],
        )
        if p:
            self._cfg["path"] = p   # абсолютный путь — надёжнее при конфиге в AppData
            self._on_save()
            self._refresh_state()

    def _edit_card(self):
        dlg = _EditDialog(
            self.winfo_toplevel(),
            name=self._cfg.get("name", ""),
            desc=self._cfg.get("description", ""),
        )
        res = dlg.result
        if res is None:
            return
        name, desc = res
        if name:
            self._cfg["name"] = name
            self._name_lbl.configure(text=name)
        self._cfg["description"] = desc
        self._desc_lbl.configure(text=desc)
        self._on_save()

    def _launch(self):
        path = _abs(self._cfg.get("path", ""))
        if not path.exists():
            self._flash("Файл не найден!", error=True)
            return
        if self._proc is not None and self._proc.poll() is None:
            self._flash("Уже запущен")
            return
        try:
            self._proc = subprocess.Popen([str(path)], cwd=str(path.parent))
            self._launch_btn.configure(text="✓  Запущен", fg_color="#27ae60", hover_color="#2ecc71")
            self.after(2500, self._reset_btn)
        except Exception as e:
            self._flash(f"Ошибка: {e}", error=True)

    def _reset_btn(self):
        self._launch_btn.configure(
            text="▶  Запустить", fg_color=MTS_RED, hover_color=MTS_RED_HOV,
            border_width=0, text_color=("white", "white"),
        )

    def _flash(self, text: str, error: bool = False):
        self._file_lbl.configure(text=text, text_color="#e74c3c" if error else "#2ecc71")
        self.after(3000, self._refresh_state)

    def _setup_hover(self):
        self._bind_tree("<Enter>", self._on_hover_enter)
        self._bind_tree("<Leave>", self._on_hover_leave)

    def _bind_tree(self, event: str, handler):
        self.bind(event, handler, add="+")
        def recurse(w):
            for child in w.winfo_children():
                child.bind(event, handler, add="+")
                recurse(child)
        recurse(self)

    def _on_hover_enter(self, _=None):
        if self._hide_id:
            self.after_cancel(self._hide_id)
            self._hide_id = None
        self._del_btn.pack(side="right", padx=(2, 0))

    def _on_hover_leave(self, _=None):
        if self._hide_id:
            self.after_cancel(self._hide_id)
        self._hide_id = self.after(80, self._check_hover)

    def _check_hover(self):
        self._hide_id = None
        x, y = self.winfo_pointerx(), self.winfo_pointery()
        rx, ry = self.winfo_rootx(), self.winfo_rooty()
        if not (rx <= x < rx + self.winfo_width() and ry <= y < ry + self.winfo_height()):
            self._del_btn.pack_forget()


# ── App ───────────────────────────────────────────────────────────────────────

class LauncherApp(ctk.CTk):

    def __init__(self):
        try:
            self._cfg = _load_config()
        except FileNotFoundError as e:
            import tkinter as _tk
            import tkinter.messagebox as _mb
            _r = _tk.Tk(); _r.withdraw()
            _mb.showerror("Ошибка конфигурации", str(e))
            _r.destroy(); sys.exit(1)
        super().__init__()

        mode = self._cfg.get("appearance_mode", "light")
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("blue")

        self.title("MTS Launcher")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(MIN_W, MIN_H)

        self._set_window_icon()
        self._init_icons()
        self._build_header()
        self._build_body()
        self._build_cards()
        self._build_add_btn()
        self.after(50, self._fit_width)

    def _set_window_icon(self):
        ico = RES_DIR / "logo.ico"
        if not ico.exists():
            return
        try:
            img = Image.open(ico).resize((32, 32), Image.LANCZOS)
            self._tk_icon = ImageTk.PhotoImage(img)
            self.iconphoto(True, self._tk_icon)
        except Exception:
            pass

    def _init_icons(self):
        self._icon_sun    = _icon("sun",    (20, 20))
        self._icon_moon   = _icon("moon",   (20, 20))
        self._icon_folder = _icon("folder", (16, 16))
        self._icon_pencil = _icon("pencil", (14, 14))

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=MTS_RED, corner_radius=0, height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        self._theme_btn = ctk.CTkButton(
            hdr,
            text="" if self._icon_sun else ("☀" if is_dark else "🌙"),
            image=self._icon_sun if is_dark else self._icon_moon,
            width=36, height=36,
            fg_color="transparent",
            hover_color=MTS_RED_HOV,
            text_color="white",
            border_width=0,
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right", padx=9, pady=9)

        if LOGO_PATH.exists():
            img = Image.open(LOGO_PATH)
            self._logo_img = ctk.CTkImage(img, size=(38, 38))
            ctk.CTkLabel(hdr, image=self._logo_img, text="").pack(
                side="left", padx=(14, 10), pady=10
            )

        ctk.CTkLabel(
            hdr,
            text="Лаунчер приложений",
            font=(_F, 15, "bold"),
            text_color="white",
        ).pack(side="left", pady=10)

    def _build_body(self):
        self._cards_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._cards_frame.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        self._cards_frame._parent_canvas.bind("<Configure>", self._update_scroll_visibility, add="+")
        self._cards_frame.bind("<Configure>",               self._update_scroll_visibility, add="+")

    def _build_cards(self):
        self._cards: list[AppCard] = []
        for i, app_cfg in enumerate(self._cfg.get("apps", [])):
            self._append_card(i, app_cfg)

    def _build_add_btn(self):
        ctk.CTkButton(
            self,
            text="＋  Добавить приложение",
            height=36,
            font=(_F, 12),
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("gray20", "gray90"),
            corner_radius=6,
            command=self._add_card,
        ).pack(fill="x", padx=16, pady=(0, 14))

    def _append_card(self, index: int, app_cfg: dict) -> AppCard:
        card = AppCard(
            self._cards_frame,
            index=index,
            app_cfg=app_cfg,
            on_save=self._save,
            on_delete=self._delete_card,
            icon_folder=self._icon_folder,
            icon_pencil=self._icon_pencil,
            fg_color=CARD_BG,
            corner_radius=8,
            border_width=1,
        )
        card.pack(fill="x", pady=(0, 10))
        self._cards.append(card)
        return card

    def _delete_card(self, card: AppCard):
        idx = self._cards.index(card)
        self._cfg["apps"].pop(idx)
        self._cards.pop(idx)
        card.destroy()
        for i, c in enumerate(self._cards):
            c._index = i
        self._save()
        self.after(50, self._update_scroll_visibility)

    def _add_card(self):
        new_cfg: dict = {"name": f"Приложение {len(self._cards) + 1}", "description": "", "path": ""}
        self._cfg.setdefault("apps", []).append(new_cfg)
        self._append_card(len(self._cards), new_cfg)
        self._save()
        self.after(50, self._update_scroll_visibility)

    def _update_scroll_visibility(self, _=None):
        canvas    = self._cards_frame._parent_canvas
        scrollbar = self._cards_frame._scrollbar
        if canvas.winfo_height() <= 1:
            return
        needs = self._cards_frame.winfo_reqheight() > canvas.winfo_height()
        shown = scrollbar.winfo_ismapped()
        if needs == shown:
            return
        if needs:
            scrollbar.grid()
        else:
            scrollbar.grid_remove()

    def _fit_width(self):
        """Начальная ширина окна по содержимому карточек (font.measure, т.к. winfo_reqwidth не работает в CTkScrollableFrame)."""
        try:
            f_bold = _TkFont(family=_F, size=13, weight="bold")
            f_norm = _TkFont(family=_F, size=11)
            f_tiny = _TkFont(family=_F, size=10)
        except Exception:
            f_bold = _TkFont(size=13, weight="bold")
            f_norm = _TkFont(size=11)
            f_tiny = _TkFont(size=10)

        max_card_w = 0
        for card in self._cards:
            cfg  = card._cfg
            name = cfg.get("name", "")
            desc = cfg.get("description", "")
            fname = Path(cfg["path"]).name if cfg.get("path") else "exe не выбран"
            inner = max(
                f_bold.measure(name) + 26 + 4,
                f_norm.measure(desc),
                f_tiny.measure(fname) + 28,
                140,
            )
            max_card_w = max(max_card_w, inner + 26 + 5 + 2)

        w = max(WIN_W, max_card_w + 32 + 16 + 24)
        self.geometry(f"{w}x{WIN_H}")

    def _toggle_theme(self):
        new = "light" if ctk.get_appearance_mode() == "Dark" else "dark"
        ctk.set_appearance_mode(new)
        is_dark = new == "dark"
        self._theme_btn.configure(
            image=self._icon_sun if is_dark else self._icon_moon,
            text="" if self._icon_sun else ("☀" if is_dark else "🌙"),
        )
        self._cfg["appearance_mode"] = new
        self._save()

    def _save(self):
        ok = _save_config(self._cfg)
        self.title("MTS Launcher" if ok else f"⚠ Не удалось сохранить {CONFIG_PATH}")


if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()
