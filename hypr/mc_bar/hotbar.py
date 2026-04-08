#!/usr/bin/env python3
import gi
import os
import subprocess
from gi.repository import Gtk, GdkPixbuf, Gdk, GLib

# ================== CONFIG ==================
CONFIG_DIR = os.path.expanduser("~/.config/hypr/mc_hotbar")
HOTBAR_PNG = os.path.join(CONFIG_DIR, "hotbar.png")

WIDTH  = 560
HEIGHT = 80

BOTTOM_MARGIN = 15   # distance from bottom of screen
# ============================================

class MinecraftHotbar(Gtk.Window):
    def __init__(self):
        super().__init__(title="MC Hotbar")
        
        self.set_default_size(WIDTH, HEIGHT)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        
        # Make it behave like a real panel/bar
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_accept_focus(False)        # Can't be focused/selected easily
        self.set_focus_on_map(False)

        # Background
        if os.path.exists(HOTBAR_PNG):
            pb = GdkPixbuf.Pixbuf.new_from_file(HOTBAR_PNG)
            scaled = pb.scale_simple(WIDTH, HEIGHT, GdkPixbuf.InterpType.NEAREST)
            bg = Gtk.Image.new_from_pixbuf(scaled)
            overlay = Gtk.Overlay()
            overlay.add(bg)
            self.add(overlay)
            self.fixed = Gtk.Fixed()
            overlay.add_overlay(self.fixed)
        else:
            print("[MC Hotbar] hotbar.png not found!")
            self.fixed = Gtk.Fixed()
            self.add(self.fixed)

        self.create_slots()

        # Very hard to close accidentally
        self.connect("delete-event", lambda *_: True)   # Block close button
        self.connect("key-press-event", self.on_key)

    def create_slots(self):
        slot_size = 52
        start_x = 28      # ← Change these if icons are not aligned
        y_pos   = 14

        apps = self.get_apps()[:9]

        for i in range(9):
            x = start_x + i * 60
            btn = Gtk.Button()
            btn.set_size_request(slot_size, slot_size)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_can_focus(False)          # Makes slots less "clickable" visually

            if i < len(apps):
                app = apps[i]
                icon = self.get_icon(app["icon"], int(slot_size * 0.72))
                if icon:
                    btn.set_image(Gtk.Image.new_from_pixbuf(icon))
                btn.set_tooltip_text(app["name"])
                btn.connect("clicked", lambda _, cmd=app["cmd"]: self.launch(cmd))

            self.fixed.put(btn, x, y_pos)

    def get_apps(self):
        import glob, configparser
        apps = []
        seen = set()
        dirs = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]
        
        for d in dirs:
            for f in glob.glob(os.path.join(d, "*.desktop")):
                try:
                    cfg = configparser.ConfigParser(interpolation=None)
                    cfg.read(f, encoding="utf-8")
                    entry = cfg["Desktop Entry"]
                    if entry.get("NoDisplay", "false").lower() == "true":
                        continue
                    name = entry.get("Name", "").strip()
                    cmd = entry.get("Exec", "").split()[0].strip()
                    icon = entry.get("Icon", "").strip()
                    if name and cmd and cmd not in seen:
                        seen.add(cmd)
                        apps.append({"name": name, "cmd": cmd, "icon": icon})
                except:
                    continue
        apps.sort(key=lambda x: x["name"].lower())
        return apps

    def get_icon(self, icon_name, size):
        if not icon_name: return None
        try:
            theme = Gtk.IconTheme.get_default()
            pb = theme.load_icon(os.path.splitext(icon_name)[0], size, 0)
            return pb.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
        except:
            return None

    def launch(self, cmd):
        try:
            subprocess.Popen([cmd], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            return True  # Block escape from closing it
        return False

    def move_to_position(self):
        screen = self.get_screen()
        x = (screen.get_width() - WIDTH) // 2
        y = screen.get_height() - HEIGHT - BOTTOM_MARGIN
        self.move(x, y)


if __name__ == "__main__":
    lock = "/tmp/mc_hotbar.lock"
    if os.path.exists(lock):
        try:
            with open(lock) as f:
                os.kill(int(f.read().strip()), 15)
        except:
            pass

    with open(lock, "w") as f:
        f.write(str(os.getpid()))

    win = MinecraftHotbar()
    win.show_all()
    win.move_to_position()

    # Make it very persistent
    GLib.timeout_add(2000, lambda: (win.move_to_position(), True))

    Gtk.main()
    
    try: os.remove(lock)
    except: pass
