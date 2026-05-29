# this file is fully vibecoded
from __future__ import annotations

import copy
import json
import platform
import shutil
import subprocess
from pathlib import Path
from tkinter import filedialog as fd
from tkinter.font import Font as _TkFont

import customtkinter as ctk
from PIL import Image

BASE_DIR      = Path(__file__).parent
RES_DIR       = BASE_DIR / "resources"
CONFIG_PATH   = BASE_DIR / "config.json"
LOGO_PATH     = RES_DIR / "logo.png"
ICONS_DIR     = RES_DIR / "icons"

_FONT_REGULAR = RES_DIR / "MTSCompact-Regular.ttf"
_FONT_BOLD    = RES_DIR / "MTSCompact-Bold.ttf"
_FONT_FAMILY  = "MTS Compact"

MTS_RED     = "#FF0032"
MTS_RED_HOV = "#CC0029"
WIN_H       = 740

CARD_BG     = ("gray88", "gray20")   # фон карточки (светлая / тёмная тема)


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


def _icon(name: str, size: tuple[int, int] = (18, 18)) -> ctk.CTkImage | None:
    path = ICONS_DIR / f"{name}.png"
    if not path.exists():
        return None
    img = Image.open(path)
    return ctk.CTkImage(light_image=img, dark_image=img, size=size)


_DEFAULT_CONFIG: dict = {
    "appearance_mode": "light",
    "apps": [
        {"name": "SimpleExcelCopypaster", "description": "Копирование данных между таблицами",   "path": "./ExcelCopypaster.exe"},
        {"name": "DocGenerator",          "description": "Генерация Word-документов из шаблонов", "path": "./DocGenerator.exe"},
        {"name": "Обработчик заявок",     "description": "Создание документов по заявкам МТС",   "path": ""},
    ],
}


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    cfg = copy.deepcopy(_DEFAULT_CONFIG)
    _save_config(cfg)
    return cfg


def _save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _rel(p: str) -> str:
    try:
        return str(Path(p).relative_to(BASE_DIR))
    except ValueError:
        return p


def _abs(p: str) -> Path:
    ap = Path(p)
    return ap if ap.is_absolute() else BASE_DIR / ap


# ── AppCard ───────────────────────────────────────────────────────────────────

class AppCard(ctk.CTkFrame):

    def __init__(self, parent, index: int, app_cfg: dict, on_save: callable,
                 icon_folder: ctk.CTkImage | None,
                 icon_pencil: ctk.CTkImage | None,
                 **kw):
        super().__init__(parent, **kw)
        self._index        = index
        self._cfg          = app_cfg
        self._on_save      = on_save
        self._icon_folder  = icon_folder
        self._icon_pencil  = icon_pencil
        self._proc: subprocess.Popen | None = None
        self._build()
        self._refresh_state()

    def _build(self):
        ctk.CTkFrame(self, fg_color=MTS_RED, width=5, corner_radius=0).pack(
            side="left", fill="y"
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(12, 14), pady=12)

        # header
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
            command=self._edit_name,
        ).pack(side="right", padx=(4, 0))

        # описание
        self._desc_lbl = ctk.CTkLabel(
            body,
            text=self._cfg.get("description", ""),
            font=(_F, 11),
            text_color="gray",
            anchor="w",
        )
        self._desc_lbl.pack(fill="x", pady=(0, 6))

        # путь + кнопка выбора
        path_row = ctk.CTkFrame(body, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 8))

        self._path_lbl = ctk.CTkLabel(
            path_row, text="",
            font=(_F, 10), text_color="gray", anchor="w",
        )
        self._path_lbl.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            path_row,
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
            self._path_lbl.configure(text="exe не выбран", text_color=MTS_RED)
            self._launch_btn.configure(**self._BTN_DISABLED)
        else:
            exists = _abs(path_str).exists()
            self._path_lbl.configure(
                text=_rel(path_str),
                text_color=("black", "white") if exists else "#e74c3c",
            )
            self._launch_btn.configure(**(self._BTN_ACTIVE if exists else self._BTN_DISABLED))

    def _pick_exe(self):
        p = fd.askopenfilename(
            title="Выберите исполняемый файл",
            filetypes=[("Исполняемый файл", "*.exe"), ("Все файлы", "*.*")],
        )
        if p:
            self._cfg["path"] = _rel(p)
            self._on_save()
            self._refresh_state()

    def _edit_name(self):
        dlg = ctk.CTkInputDialog(text="Новое название:", title="Переименовать")
        val = dlg.get_input()
        if val and val.strip():
            self._cfg["name"] = val.strip()
            self._name_lbl.configure(text=val.strip())
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
        self._path_lbl.configure(text=text, text_color="#e74c3c" if error else "#2ecc71")
        self.after(3000, self._refresh_state)


# ── App ───────────────────────────────────────────────────────────────────────

class LauncherApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self._cfg = _load_config()

        mode = self._cfg.get("appearance_mode", "light")
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("blue")

        self.title("MTS Launcher")
        self.geometry("273x{WIN_H}")
        self.resizable(False, False)

        self._init_icons()
        self._build_header()
        self._build_body()
        self._build_cards()
        self.after(50, self._fit_width)

    def _init_icons(self):
        self._icon_sun    = _icon("sun",    (20, 20))
        self._icon_moon   = _icon("moon",   (20, 20))
        self._icon_folder = _icon("folder", (16, 16))
        self._icon_pencil = _icon("pencil", (14, 14))

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=MTS_RED, corner_radius=0, height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # right side first — иначе tkinter pack не оставит место
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
        self._cards_frame.pack(fill="both", expand=True, padx=16, pady=16)
        self._cards_frame._parent_canvas.bind("<Configure>", self._update_scroll_visibility, add="+")
        self._cards_frame.bind("<Configure>",               self._update_scroll_visibility, add="+")

    def _build_cards(self):
        self._cards: list[AppCard] = []
        for i, app_cfg in enumerate(self._cfg.get("apps", [])):
            card = AppCard(
                self._cards_frame,
                index=i,
                app_cfg=app_cfg,
                on_save=self._save,
                icon_folder=self._icon_folder,
                icon_pencil=self._icon_pencil,
                fg_color=CARD_BG,
                corner_radius=8,
                border_width=1,
            )
            card.pack(fill="x", pady=(0, 10))
            self._cards.append(card)

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
            scrollbar.grid()         # восстановить с сохранёнными grid-настройками
        else:
            scrollbar.grid_remove()  # скрыть, grid-настройки сохраняются

    def _fit_width(self):
        """Ширина окна по содержимому карточек через font.measure (winfo_reqwidth не работает в CTkScrollableFrame)."""
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
            cfg = card._cfg
            name = cfg.get("name", "")
            desc = cfg.get("description", "")
            path = _rel(cfg["path"]) if cfg.get("path") else "exe не выбран"
            inner = max(
                f_bold.measure(name) + 26 + 4,  # имя + карандаш + зазор
                f_norm.measure(desc),
                f_tiny.measure(path) + 28,       # путь + кнопка папки
                140,                             # минимум CTkButton
            )
            max_card_w = max(max_card_w, inner + 26 + 5 + 2)  # padx тела + полоса + рамка

        # +24 — буфер: CTkLabel добавляет внутренние отступы, которые font.measure не учитывает
        w = max(273, max_card_w + 32 + 16 + 24)
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
        _save_config(self._cfg)


if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()
