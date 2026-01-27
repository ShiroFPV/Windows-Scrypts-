#!/usr/bin/env python3
"""
FileSorter.py - Downloads Cleaner (only)

- Sorts files in your Downloads folder into a few category folders.
- Default: category folders are created inside Downloads.
- Sort root can be changed via folder picker (Explorer/Finder).

No external libs. UI is ANSI + minimal key reader.
"""

import os, sys, json, re, shutil, argparse, subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# ----------------------------
# App identity (auto-follows rename)
# ----------------------------
SCRIPT_PATH = Path(__file__).resolve()
APP_FILE = SCRIPT_PATH.name                # e.g. "FileSorter.py"
APP_BASENAME = SCRIPT_PATH.stem            # e.g. "FileSorter"
APP_TITLE = APP_BASENAME


# ----------------------------
# UI state
# ----------------------------
SESSION = {
    "status": "Ready.",
    "moves": [],
    "move_summary": [],
    "last_open_dir": None,
}


# ----------------------------
# Config paths
# ----------------------------
def _config_dir() -> Path:
    # Keep it consistent and easy to find
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / APP_BASENAME
    return Path.home() / ".config" / APP_BASENAME

def config_path() -> Path:
    return _config_dir() / "config.json"

def log_path() -> Path:
    # Log name follows your file name: FileSorter.log
    return _config_dir() / f"{APP_BASENAME}.log"

def ensure_dirs(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def expand_path(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p))).resolve()

def log(msg: str):
    ensure_dirs(_config_dir())
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    with open(log_path(), "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ----------------------------
# Folder picker + open folder
# ----------------------------
def pick_directory(title="Select folder", initial=None):
    """OS folder picker (tkinter, stdlib). Returns a path or None."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        out = filedialog.askdirectory(title=title, initialdir=initial or str(Path.home()))
        root.destroy()
        return out if out else None
    except Exception as e:
        log(f"[ui] folder picker unavailable: {e}")
        return None

def open_in_file_manager(path: str):
    p = str(expand_path(path))
    try:
        if os.name == "nt":
            os.startfile(p)
        elif sys.platform == "darwin":
            subprocess.run(["open", p], check=False)
        else:
            subprocess.run(["xdg-open", p], check=False)
        SESSION["last_open_dir"] = p
    except Exception as e:
        log(f"[ui] open folder failed: {e}")


# ----------------------------
# Clean artwork (no chaos)
# ----------------------------
def banner() -> str:
    w = 44
    top = "┌" + "─" * (w - 2) + "┐"
    mid = "│" + " " * (w - 2) + "│"
    name = f"{APP_TITLE}  •  Downloads Cleaner"
    name = name[: w - 6]  # keep it tidy
    line = "│  " + name.ljust(w - 6) + "  │"
    bottom = "└" + "─" * (w - 2) + "┘"
    return "\n".join([top, line, mid, bottom])


# ----------------------------
# Defaults + extension DB
# ----------------------------
def _exts_blob(blob: str) -> set[str]:
    parts = re.split(r"[\s,;]+", (blob or "").strip())
    out = set()
    for p in parts:
        if not p:
            continue
        p = p.strip().lower()
        if not p.startswith("."):
            p = "." + p
        out.add(p)
    return out

def build_builtin_categories() -> list[dict]:
    """
    Few folders, wide extension coverage.

    "1000+" is done without creating 1000 folders:
    - We add split archive parts .001.. .999 and multipart styles.
    """
    blobs = {
        "Images": """
            jpg jpeg jpe jfif png gif webp bmp dib tiff tif ico cur
            heic heif avif svg eps ai psd psb xcf kra ora clip csp
            dng raw cr2 cr3 nef arw sr2 raf orf rw2 pef 3fr erf mrw kdc mos rwl srw
            hdr exr dds tga icns jxr jp2 j2k jpf jpx jpm mj2
            pbm pgm ppm pam pnm wbmp
        """,
        "Videos": """
            mp4 m4v mkv mov avi webm wmv flv f4v mpg mpeg m2v 3gp 3g2
            ts mts m2ts vob ogv rm rmvb asf
        """,
        "Audio": """
            mp3 wav wave flac aac m4a m4b ogg oga opus wma alac aiff aif aifc
            mid midi kar
        """,
        "Documents": """
            pdf
            txt md rst tex rtf
            odt ott doc docx dot dotm dotx pages
            xps oxps djvu
            eml msg
            epub mobi azw azw3 kfx fb2 lit lrf
        """,
        "Spreadsheets": """
            xls xlsx xlsm xlsb xlt xltx xltm
            ods ots numbers
            csv tsv
        """,
        "Presentations": """
            ppt pptx pptm pps ppsx odp otp key
        """,
        "Archives": """
            zip 7z rar tar gz tgz bz2 tbz2 xz txz zst lz lz4 lzh lha cab
            jar war ear
            iso img nrg bin cue mdf mds
        """,
        "Installers": """
            exe msi msp msu
            appx appxbundle msix msixbundle
            dmg pkg mpkg
            deb rpm apk
            appimage
        """,
        "Code": """
            c h
            cc hh
            cpp hpp cxx hxx inl inc
            cs vb fs fsx
            java kt kts scala groovy gradle
            py pyw pyi ipynb
            js jsx mjs cjs ts tsx
            go rs swift m mm
            php phtml phar
            rb erb rake
            pl pm t
            lua
            sh bash zsh fish
            ps1 psm1 psd1
            sql
            html htm xhtml css scss sass less
            xml xsd xsl xslt
            json json5 yaml yml toml ini cfg conf properties env
            make mak cmake
        """,
        "3D_CAD": """
            stl obj fbx glb gltf dae 3ds blend
            step stp iges igs dwg dxf
            skp
        """,
        "Fonts": "ttf otf woff woff2 eot",
        "Keys_Certs": "pem crt cer der pfx p12 key pub gpg asc",
        "VM_Disk": "vdi vmdk vhd vhdx qcow qcow2 ova ovf",
        "Shortcuts": "url webloc lnk desktop",
        "Logs": "log out err trace dump dmp crash",
        "Data": "sqlite sqlite3 db mdb accdb dat parquet feather arrow",
    }

    cats = []
    for name, blob in blobs.items():
        cats.append({
            "name": name,
            "folder_default": name,
            "by_date": True if name == "Images" else False,
            "exts": _exts_blob(blob),
        })

    # Inflate extension DB massively (still one folder: Archives)
    archive = next(c for c in cats if c["name"] == "Archives")
    for i in range(1, 1000):
        archive["exts"].add(f".{i:03d}")     # .001 .. .999
    for i in range(0, 100):
        archive["exts"].add(f".r{i:02d}")    # .r00 .. .r99
    for i in range(1, 100):
        archive["exts"].add(f".z{i:02d}")    # .z01 .. .z99

    return cats

def default_config():
    return {
        "downloads": {
            "path": "~/Downloads",
            "sort_root": "",             # empty = inside Downloads
            "dry_run": False,
            "unknown_folder": "_Other",
            "ignore_hidden": True,
            "ignore_names": ["desktop.ini", "thumbs.db"],

            # You can rename the destination folders without touching extension lists.
            "folder_names": {
                "Images": "Images",
                "Videos": "Videos",
                "Audio": "Audio",
                "Documents": "Documents",
                "Spreadsheets": "Spreadsheets",
                "Presentations": "Presentations",
                "Archives": "Archives",
                "Installers": "Installers",
                "Code": "Code",
                "3D_CAD": "3D_CAD",
                "Fonts": "Fonts",
                "Keys_Certs": "Keys_Certs",
                "VM_Disk": "VM_Disk",
                "Shortcuts": "Shortcuts",
                "Logs": "Logs",
                "Data": "Data",
            },

            # Optional overrides (priority over builtin DB)
            # [{"ext":".hex","category":"Code"}]
            "custom_ext_map": []
        }
    }

def load_config():
    ensure_dirs(_config_dir())
    cp = config_path()
    if not cp.exists():
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(default_config(), f, indent=2)
        log("[init] created default config.json")
    with open(cp, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    ensure_dirs(_config_dir())
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    log("[cfg] saved")


# ----------------------------
# Sorting engine
# ----------------------------
def safe_mkdir(p: Path, dry=False):
    if not dry:
        p.mkdir(parents=True, exist_ok=True)

def unique_path(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    for i in range(1, 10000):
        cand = dest.with_name(f"{stem}__{i:03d}{suffix}")
        if not cand.exists():
            return cand
    raise RuntimeError(f"Too many collisions for {dest}")

def is_probably_incomplete(name: str) -> bool:
    low = name.lower()
    return low.endswith(".crdownload") or low.endswith(".part") or low.endswith(".tmp")

def build_ext_to_category(cfg) -> tuple[dict[str, str], dict[str, dict]]:
    dcfg = cfg["downloads"]
    folder_names = dcfg.get("folder_names", {}) or {}

    cats = build_builtin_categories()

    cat_meta: dict[str, dict] = {}
    ext_to_cat: dict[str, str] = {}

    for c in cats:
        cat = c["name"]
        folder = folder_names.get(cat) or c["folder_default"]
        cat_meta[cat] = {"folder": folder, "by_date": bool(c["by_date"])}
        for e in c["exts"]:
            ext_to_cat[e] = cat

    # user overrides
    for rule in dcfg.get("custom_ext_map", []):
        ext = (rule.get("ext") or "").strip().lower()
        cat = (rule.get("category") or "").strip()
        if not ext or not cat:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        if cat not in cat_meta:
            cat_meta[cat] = {"folder": folder_names.get(cat) or cat, "by_date": False}
        ext_to_cat[ext] = cat

    return ext_to_cat, cat_meta

def sort_downloads(cfg) -> dict:
    dcfg = cfg["downloads"]
    downloads = expand_path(dcfg["path"])
    sr = (dcfg.get("sort_root", "") or "").strip()
    sort_root = expand_path(sr) if sr else downloads

    dry_run = bool(dcfg.get("dry_run", False))
    unknown_folder = dcfg.get("unknown_folder", "_Other")
    ignore_hidden = bool(dcfg.get("ignore_hidden", True))
    ignore_names = set((n or "").lower() for n in dcfg.get("ignore_names", []))

    ext_to_cat, cat_meta = build_ext_to_category(cfg)

    moved, skipped = 0, 0
    moves = []
    counts = defaultdict(int)

    if not downloads.exists():
        raise FileNotFoundError(f"Downloads not found: {downloads}")

    # Safe mode: only root files, not subfolders.
    for p in downloads.iterdir():
        if p.is_dir():
            continue
        if ignore_hidden and p.name.startswith("."):
            continue
        if p.name.lower() in ignore_names:
            continue
        if is_probably_incomplete(p.name):
            continue

        ext = p.suffix.lower()
        cat = ext_to_cat.get(ext)

        if cat:
            folder = cat_meta.get(cat, {}).get("folder", cat)
            by_date = bool(cat_meta.get(cat, {}).get("by_date", False))
        else:
            folder = unknown_folder
            by_date = False

        dest_dir = sort_root / folder
        if by_date:
            dt = datetime.fromtimestamp(p.stat().st_mtime)
            dest_dir = dest_dir / f"{dt:%Y}" / f"{dt:%m}"

        dest = unique_path(dest_dir / p.name)

        try:
            safe_mkdir(dest_dir, dry=dry_run)
            if not dry_run:
                shutil.move(str(p), str(dest))
            moved += 1
            moves.append(f"{p.name} -> {dest}")
            counts[str(dest_dir)] += 1
        except Exception as e:
            skipped += 1
            log(f"[sort] skip {p.name}: {e}")

    summary = [f"{n} -> {k}" for k, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]
    log(f"[sort] moved={moved} skipped={skipped} sort_root={sort_root} ext_db={len(ext_to_cat)}")
    return {
        "moved": moved,
        "skipped": skipped,
        "moves": moves,
        "summary": summary,
        "sort_root": str(sort_root),
        "ext_db_size": len(ext_to_cat),
    }


# ----------------------------
# Terminal UI (no curses)
# ----------------------------
ANSI = {
    "clear": "\x1b[2J\x1b[H",
    "rev": "\x1b[7m",
    "norm": "\x1b[0m",
    "dim": "\x1b[2m",
    "bold": "\x1b[1m",
}

def ansi_enable_windows():
    if os.name == "nt":
        os.system("")

def term_get_key():
    # Returns: 'UP','DOWN','ENTER','ESC'
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            ch2 = msvcrt.getch()
            return {b"H": "UP", b"P": "DOWN"}.get(ch2, "ESC")
        if ch == b"\r":
            return "ENTER"
        if ch == b"\x1b":
            return "ESC"
        return "ESC"
    else:
        import termios, tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                nxt = sys.stdin.read(1)
                if nxt == "[":
                    code = sys.stdin.read(1)
                    return {"A": "UP", "B": "DOWN"}.get(code, "ESC")
                return "ESC"
            if ch in ("\r", "\n"):
                return "ENTER"
            return "ESC"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

def draw_menu(title, items, idx, ext_db_size=None):
    ansi_enable_windows()
    sys.stdout.write(ANSI["clear"])
    sys.stdout.write(banner() + "\n\n")

    sys.stdout.write(ANSI["bold"] + title + ANSI["norm"] + "\n")
    sys.stdout.write(ANSI["dim"] + ("─" * max(26, len(title))) + ANSI["norm"] + "\n")
    sys.stdout.write(ANSI["dim"] + f"Status: {SESSION.get('status','')}" + ANSI["norm"] + "\n")
    if ext_db_size is not None:
        sys.stdout.write(ANSI["dim"] + f"Extension DB: {ext_db_size} mapped extensions" + ANSI["norm"] + "\n")
    sys.stdout.write("\n")

    for i, it in enumerate(items):
        line = f"  {it}"
        if i == idx:
            sys.stdout.write(ANSI["rev"] + line + ANSI["norm"] + "\n")
        else:
            sys.stdout.write(line + "\n")

    sys.stdout.write("\n")

    if SESSION.get("move_summary"):
        sys.stdout.write(ANSI["dim"] + "Moved this run (summary):" + ANSI["norm"] + "\n")
        for line in SESSION["move_summary"][-8:]:
            sys.stdout.write(f"  {line}\n")
        sys.stdout.write("\n")

    if SESSION.get("moves"):
        sys.stdout.write(ANSI["dim"] + "Recent moves:" + ANSI["norm"] + "\n")
        for line in SESSION["moves"][-6:]:
            sys.stdout.write(f"  {line}\n")
        sys.stdout.write("\n")

    sys.stdout.write(ANSI["dim"] + "Keys: ↑/↓ select, Enter confirm, Esc back" + ANSI["norm"] + "\n")
    sys.stdout.flush()

def run_menu(title, items, ext_db_size=None):
    idx = 0
    while True:
        draw_menu(title, items, idx, ext_db_size=ext_db_size)
        k = term_get_key()
        if k == "UP":
            idx = (idx - 1) % len(items)
        elif k == "DOWN":
            idx = (idx + 1) % len(items)
        elif k == "ENTER":
            return idx
        elif k == "ESC":
            return len(items) - 1

def pause_screen(msg):
    ansi_enable_windows()
    sys.stdout.write(ANSI["clear"])
    sys.stdout.write(msg + "\n\nPress Enter...\n")
    sys.stdout.flush()
    input()

def prompt_input(label, current=None, allow_empty=False):
    ansi_enable_windows()
    sys.stdout.write(ANSI["clear"])
    sys.stdout.write(label + "\n")
    if current is not None:
        sys.stdout.write(ANSI["dim"] + f"Current: {current}" + ANSI["norm"] + "\n")
    sys.stdout.write("\n> ")
    sys.stdout.flush()
    s = input().strip()
    if s == "" and not allow_empty:
        return current
    return s

def prompt_path(label, current=None, allow_empty=False):
    while True:
        items = ["Browse… (folder picker)", "Type manually", "Back"]
        c = run_menu(label, items)
        if c == 0:
            picked = pick_directory(title=label, initial=current)
            if picked:
                return picked
        elif c == 1:
            return prompt_input(label, current=current, allow_empty=allow_empty)
        else:
            return current


# ----------------------------
# Config editor (simple)
# ----------------------------
def edit_config(cfg):
    d = cfg["downloads"]
    while True:
        sr = d.get("sort_root", "")
        eff_root = sr if sr else "(same as Downloads)"
        items = [
            f"Downloads path: {d.get('path','')}",
            f"Sort root: {eff_root}",
            "Set sort root = Downloads (keep inside Downloads)",
            f"Unknown folder: {d.get('unknown_folder','_Other')}",
            f"Dry-run: {d.get('dry_run', False)}",
            "Rename category folders",
            "Back"
        ]
        c = run_menu("Edit config", items)
        if c == 0:
            d["path"] = prompt_path("Downloads folder", d.get("path","~/Downloads"))
        elif c == 1:
            picked = prompt_path("Sort root (empty = Downloads)", d.get("sort_root",""), allow_empty=True)
            d["sort_root"] = picked or ""
        elif c == 2:
            d["sort_root"] = ""
        elif c == 3:
            d["unknown_folder"] = prompt_input("Folder for unknown extensions", d.get("unknown_folder","_Other"))
        elif c == 4:
            d["dry_run"] = (prompt_input("Dry-run? type y/n", "n") or "n").strip().lower().startswith(("y","j","1","t"))
        elif c == 5:
            edit_folder_names(d)
        else:
            break
        save_config(cfg)

def edit_folder_names(d):
    folder_names = d.setdefault("folder_names", {})
    keys = sorted(folder_names.keys())
    while True:
        items = [f"{k} -> {folder_names[k]}" for k in keys] + ["Back"]
        c = run_menu("Rename category folders", items)
        if c >= len(keys):
            break
        k = keys[c]
        folder_names[k] = prompt_input(f"Folder name for '{k}'", folder_names[k])


# ----------------------------
# Main UI
# ----------------------------
def ui_main():
    cfg = load_config()
    ext_to_cat, _ = build_ext_to_category(cfg)
    ext_db_size = len(ext_to_cat)

    while True:
        items = [
            "Run: Clean Downloads now",
            "Open sort root folder",
            "Edit config",
            "Show config + log paths",
            "Exit"
        ]
        c = run_menu("Main menu", items, ext_db_size=ext_db_size)

        if c == 0:
            try:
                SESSION["status"] = "Sorting…"
                SESSION["moves"] = []
                SESSION["move_summary"] = []
                res = sort_downloads(cfg)
                SESSION["moves"] = res["moves"][-30:]
                SESSION["move_summary"] = res["summary"][-30:]
                SESSION["status"] = f"Done: moved={res['moved']} skipped={res['skipped']}"
                SESSION["last_open_dir"] = res["sort_root"]
                ext_db_size = res.get("ext_db_size", ext_db_size)
            except Exception as e:
                SESSION["status"] = f"Error: {e}"

        elif c == 1:
            d = cfg["downloads"]
            downloads = expand_path(d.get("path","~/Downloads"))
            sr = (d.get("sort_root","") or "").strip()
            root = expand_path(sr) if sr else downloads
            open_in_file_manager(str(root))
            SESSION["status"] = f"Opened: {root}"

        elif c == 2:
            edit_config(cfg)
            cfg = load_config()
            ext_to_cat, _ = build_ext_to_category(cfg)
            ext_db_size = len(ext_to_cat)
            SESSION["status"] = "Config saved."

        elif c == 3:
            pause_screen(f"Config:\n{config_path()}\n\nLog:\n{log_path()}")
            SESSION["status"] = "Shown paths."
        else:
            break


# ----------------------------
# CLI
# ----------------------------
def main():
    ap = argparse.ArgumentParser(prog=APP_FILE)
    ap.add_argument("--sort", action="store_true", help="Sort Downloads and exit")
    args = ap.parse_args()

    cfg = load_config()

    if args.sort:
        res = sort_downloads(cfg)
        print(f"Moved {res['moved']} files, skipped {res['skipped']}, sort_root={res['sort_root']}, ext_db={res['ext_db_size']}")
        return

    ui_main()

if __name__ == "__main__":
    main()
