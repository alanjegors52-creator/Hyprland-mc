#!/usr/bin/env python3
import gi, os, glob, configparser, subprocess, json, hashlib
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, Gdk, GLib
from PIL import Image
import numpy as np

# ---------------- CONFIG ----------------
CONFIG_DIR = os.path.expanduser("~/.config/hypr/mc_menu")
BACKGROUND_IMG = os.path.join(CONFIG_DIR, "inventory.png")
CACHE_FILE     = os.path.join(CONFIG_DIR, "cache.json")

WINDOW_WIDTH  = 600
WINDOW_HEIGHT = 600

# Slot detection tuning
# The slot interior in default Minecraft textures is roughly this grey.
# Widen TOLERANCE if your texture pack uses a different shade.
SLOT_COLOR    = (139, 139, 139)   # #8b8b8b – classic MC slot face
TOLERANCE     = 18                # ± per channel
MIN_SLOT_PX   = 100               # minimum pixel cluster size to count as a slot

# Tooltip style (Minecraft pixel font look)
TOOLTIP_CSS = b"""
tooltip {
    background-color: #100010;
    border: 2px solid #5000a0;
    color: #ffffff;
    font-family: monospace;
    font-size: 13px;
    padding: 4px 8px;
}
tooltip * { color: #ffffff; }
"""
# ----------------------------------------

def detect_slots(img_path: str, win_w: int, win_h: int):
    """
    Scan the background PNG for Minecraft inventory slot regions.

    Strategy:
      1. Scale image to the final window size.
      2. Build a boolean mask of pixels that match the slot interior colour.
      3. Label connected components – each blob is one slot face.
      4. Filter by minimum area, then return slot centres sorted top→bottom, left→right.

    Returns a list of (x, y, size) tuples giving the top-left corner and
    side-length (in pixels) for each detected slot, scaled to win_w × win_h.
    Falls back to an empty list if detection fails.
    """
    try:
        img = Image.open(img_path).convert("RGB").resize(
            (win_w, win_h), Image.NEAREST
        )
        arr = np.array(img, dtype=np.int16)

        r, g, b = SLOT_COLOR
        mask = (
            (np.abs(arr[:, :, 0] - r) <= TOLERANCE) &
            (np.abs(arr[:, :, 1] - g) <= TOLERANCE) &
            (np.abs(arr[:, :, 2] - b) <= TOLERANCE)
        )

        # Simple flood-fill labelling (scipy not required)
        from collections import deque
        h, w = mask.shape
        labels = np.zeros((h, w), dtype=np.int32)
        current_label = 0

        for sy in range(h):
            for sx in range(w):
                if mask[sy, sx] and labels[sy, sx] == 0:
                    current_label += 1
                    queue = deque([(sy, sx)])
                    labels[sy, sx] = current_label
                    while queue:
                        cy, cx = queue.popleft()
                        for ny, nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and labels[ny, nx] == 0:
                                labels[ny, nx] = current_label
                                queue.append((ny, nx))

        raw_slots = []
        for lbl in range(1, current_label + 1):
            ys, xs = np.where(labels == lbl)
            if len(ys) < MIN_SLOT_PX:
                continue
            x0, y0 = int(xs.min()), int(ys.min())
            x1, y1 = int(xs.max()), int(ys.max())
            slot_w  = x1 - x0 + 1
            slot_h  = y1 - y0 + 1
            if slot_w == 0 or slot_h == 0:
                continue
            ratio = slot_w / slot_h
            if not (0.5 < ratio < 2.0):
                continue
            size = max(slot_w, slot_h)
            raw_slots.append((x0, y0, size))

        if not raw_slots:
            return []

        from collections import Counter, defaultdict

        # --- Group slots by Y row (round to nearest 20px) ---
        row_groups = defaultdict(list)
        for s in raw_slots:
            row_key = round(s[1] / 20) * 20
            row_groups[row_key].append(s)

        # Keep only rows that have exactly 9 slots (inventory/hotbar rows).
        # Armor rows have 1 slot, crafting rows have 2-3 — none have 9.
        valid_rows = [
            sorted(members, key=lambda s: s[0])  # sort by X within row
            for members in row_groups.values()
            if len(members) == 9
        ]

        if not valid_rows:
            print("[mc_menu] WARNING: No 9-wide rows found. Check TOLERANCE or MIN_SLOT_PX.")
            return []

        # Sort rows top to bottom
        valid_rows.sort(key=lambda row: row[0][1])

        # Flatten: inventory rows first (all but last), then hotbar (last row)
        grid_slots = [slot for row in valid_rows for slot in row]
        grid_slots = grid_slots[:36]

        # Use the median slot size so icon sizing is accurate
        median_size = sorted(grid_slots, key=lambda s: s[2])[len(grid_slots)//2][2]
        print(f"[mc_menu] Detected {len(grid_slots)} slots across {len(valid_rows)} rows (size ~{median_size}px)")
        return grid_slots

    except Exception as e:
        print(f"[mc_menu] Slot detection failed: {e}")
        return []



def desktop_mtime():
    """Return a hash of the newest mtime across all .desktop dirs + the bg image."""
    dirs = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]
    mtimes = []
    for d in dirs:
        if os.path.exists(d):
            mtimes.append(str(os.path.getmtime(d)))
    if os.path.exists(BACKGROUND_IMG):
        mtimes.append(str(os.path.getmtime(BACKGROUND_IMG)))
    return hashlib.md5("".join(mtimes).encode()).hexdigest()

def load_cache():
    """Return (apps, slots) from cache if still valid, else rescan and save."""
    current_hash = desktop_mtime()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
            if data.get("hash") == current_hash:
                print("[mc_menu] Using cache")
                return data["apps"], [tuple(s) for s in data["slots"]]
        except Exception:
            pass

    print("[mc_menu] Rescanning apps and slots...")
    apps  = get_gui_apps()
    slots = detect_slots(BACKGROUND_IMG, WINDOW_WIDTH, WINDOW_HEIGHT)
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump({"hash": current_hash, "apps": apps, "slots": slots}, f)
    except Exception as e:
        print(f"[mc_menu] Could not write cache: {e}")
    return apps, slots


def load_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(TOOLTIP_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

def get_gui_apps():
    """Scan .desktop files and return sorted list of GUI apps."""
    apps = []
    seen = set()
    dirs = [
        "/usr/share/applications",
        os.path.expanduser("~/.local/share/applications"),
    ]
    for d in dirs:
        for fpath in glob.glob(os.path.join(d, "*.desktop")):
            cfg = configparser.ConfigParser(interpolation=None)
            try:
                cfg.read(fpath, encoding="utf-8")
            except Exception:
                continue
            if "Desktop Entry" not in cfg:
                continue
            entry = cfg["Desktop Entry"]
            if entry.get("NoDisplay", "false").lower() == "true":
                continue
            if entry.get("Type", "") not in ("", "Application"):
                continue
            name     = entry.get("Name", "").strip()
            exec_cmd = entry.get("Exec", raw=True, fallback="").strip()
            icon     = entry.get("Icon", "").strip()
            if not name or not exec_cmd:
                continue
            # Strip field codes and take only the binary
            exec_bin = exec_cmd.split()[0]
            for code in ("%U", "%u", "%F", "%f", "%i", "%c", "%k"):
                exec_bin = exec_bin.replace(code, "")
            exec_bin = exec_bin.strip()
            if exec_bin in seen:
                continue
            seen.add(exec_bin)
            apps.append({"name": name, "cmd": exec_bin, "icon": icon})

    apps.sort(key=lambda a: a["name"].lower())
    return apps


def resolve_icon(icon_name: str, size: int):
    """Return a scaled GdkPixbuf for the given icon name/path, or None."""
    if not icon_name:
        return None
    try:
        if os.path.isabs(icon_name) and os.path.exists(icon_name):
            pb = GdkPixbuf.Pixbuf.new_from_file(icon_name)
        else:
            theme = Gtk.IconTheme.get_default()
            # Try exact name, then strip extension
            name = icon_name
            if not theme.has_icon(name):
                name = os.path.splitext(icon_name)[0]
            if not theme.has_icon(name):
                return None
            pb = theme.load_icon(name, size, Gtk.IconLookupFlags.FORCE_SIZE)
        return pb.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
    except Exception:
        return None


def make_slot_button(app: dict | None, slot_size: int = 54, on_close=None) -> Gtk.Button:
    """Create a single inventory slot button."""
    btn = Gtk.Button()
    btn.set_size_request(slot_size, slot_size)
    btn.set_relief(Gtk.ReliefStyle.NONE)
    btn.get_style_context().add_class("slot-btn")

    if app:
        pb = resolve_icon(app["icon"], int(slot_size * 0.65))
        if pb:
            btn.set_image(Gtk.Image.new_from_pixbuf(pb))
        btn.set_tooltip_text(app["name"])
        btn.connect("clicked", lambda _w, cmd=app["cmd"]: (on_close() if on_close else None, launch(cmd)))

    return btn


def launch(cmd: str):
    """Launch application detached from this process."""
    try:
        subprocess.Popen(
            [cmd],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"Failed to launch {cmd!r}: {e}")


LOCK_FILE = "/tmp/mc_menu.lock"

def already_running():
    """Return True if another instance is running; also clean up stale locks."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)   # signal 0 = just check if process exists
            return True       # process is alive -> another instance is open
        except (ProcessLookupError, ValueError):
            os.remove(LOCK_FILE)  # stale lock, clean up
    return False

def write_lock():
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def remove_lock():
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass


class MinecraftMenu(Gtk.Window):
    def __init__(self):
        super().__init__(title="Minecraft Inventory Menu")
        self.set_wmclass("mc_menu", "mc_menu")
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.set_resizable(False)
        self.set_decorated(False)
        # Prevent the window manager from letting the user move it
        self.set_type_hint(Gdk.WindowTypeHint.SPLASHSCREEN)

        self.fixed = Gtk.Fixed()
        self.add(self.fixed)

        # Background
        if os.path.exists(BACKGROUND_IMG):
            pb = GdkPixbuf.Pixbuf.new_from_file(BACKGROUND_IMG)
            scaled = pb.scale_simple(WINDOW_WIDTH, WINDOW_HEIGHT, GdkPixbuf.InterpType.BILINEAR)
            self.fixed.put(Gtk.Image.new_from_pixbuf(scaled), 0, 0)

        # Load apps and slots from cache if possible
        apps, slots = load_cache()

        if not slots:
            print("[mc_menu] WARNING: No slots detected – check SLOT_COLOR / TOLERANCE in config.")

        for idx, (sx, sy, ssize) in enumerate(slots):
            if idx >= len(apps):
                break
            btn = make_slot_button(apps[idx], ssize, on_close=self._close)
            self.fixed.put(btn, sx, sy)

        # Close on Escape or clicking outside
        self.connect("key-press-event", self._on_key)
        self.connect("destroy", self._on_destroy)

    def _on_key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self._close()

    def setup_click_outside(self):
        """Close when focus is lost, but with a delay to avoid firing
        during the open animation."""
        GLib.timeout_add(500, self._arm_focus_out)

    def _arm_focus_out(self):
        self.connect("focus-out-event", self._on_focus_out)
        return False  # don't repeat

    def _on_focus_out(self, _widget, _event):
        self._close()

    def _on_destroy(self, _widget):
        remove_lock()
        Gtk.main_quit()

    def _close(self):
        remove_lock()
        Gtk.main_quit()


if __name__ == "__main__":
    # If already open, kill the existing instance (toggle behaviour)
    if already_running():
        with open(LOCK_FILE) as f:
            pid = int(f.read().strip())
        import signal
        os.kill(pid, signal.SIGTERM)
        raise SystemExit(0)

    write_lock()
    load_css()
    win = MinecraftMenu()
    win.show_all()
    win.present()
    win.grab_focus()
    GLib.timeout_add(100, lambda: win.get_window().focus(Gdk.CURRENT_TIME) or False)
    win.setup_click_outside()
    Gtk.main()
