import os
import shutil
from gettext import gettext as _

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject, Gio

from sugar3.graphics.icon import Icon
from sugar3.graphics.palette import Palette, ToolInvoker
from sugar3.graphics.palettemenu import PaletteMenuBox, PaletteMenuItem
from sugar3.graphics import style
from sugar3 import env

DEFAULT_FONTS = ['Sans', 'Serif', 'Monospace']
USER_FONTS_FILE_PATH = env.get_profile_path('fonts')
GLOBAL_FONTS_FILE_PATH = '/etc/sugar_fonts'


class FontLabel(Gtk.Label):

    def __init__(self, default_font="Sans"):
        super().__init__()
        self._font = None
        self.set_font(default_font)

    def set_font(self, font):
        if self._font != font:
            self._font = font
            self.set_markup(f'<span font="{font}">{font}</span>')


class FontComboBox(Gtk.Box):

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._palette_invoker = ToolInvoker()

        self._font_label = FontLabel()
        self._font_name = "Sans"

        button = Gtk.Button()
        button.set_focusable(False)

        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        button.set_child(inner)

        icon = Icon(icon_name="font-text")
        inner.append(icon)
        inner.append(self._font_label)

        self.append(button)

        self._palette_invoker.attach_tool(self)
        self._palette_invoker.props.toggle_palette = True

        self.palette = Palette(_("Select font"))
        self.palette.set_invoker(self._palette_invoker)

        self._menu_box = PaletteMenuBox()
        self.palette.set_content(self._menu_box)

        self._init_font_list()

        context = self.get_pango_context()

        fonts = []
        for family in context.list_families():
            name = family.get_name()
            if name in self._font_white_list:
                fonts.append(name)

        for name in sorted(fonts):
            self._add_menu(name)

        self._font_label.set_font(self._font_name)

    def _init_font_list(self):
        self._font_white_list = []
        self._font_white_list.extend(DEFAULT_FONTS)

        if not os.path.exists(USER_FONTS_FILE_PATH):
            if os.path.exists(GLOBAL_FONTS_FILE_PATH):
                shutil.copy(GLOBAL_FONTS_FILE_PATH, USER_FONTS_FILE_PATH)

        if os.path.exists(USER_FONTS_FILE_PATH):
            with open(USER_FONTS_FILE_PATH) as f:
                for line in f:
                    self._font_white_list.append(line.strip())

            gio_fonts_file = Gio.File.new_for_path(USER_FONTS_FILE_PATH)

            self.monitor = gio_fonts_file.monitor_file(
                Gio.FileMonitorFlags.NONE,
                None
            )

            self.monitor.connect("changed", self._reload_fonts)

    def _reload_fonts(self, monitor, file, other_file, event):
        if event != Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            return

        self._font_white_list = []
        self._font_white_list.extend(DEFAULT_FONTS)

        with open(USER_FONTS_FILE_PATH) as f:
            for line in f:
                self._font_white_list.append(line.strip())

        child = self._menu_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._menu_box.remove(child)
            child = nxt

        context = self.get_pango_context()

        fonts = []
        for family in context.list_families():
            name = family.get_name()
            if name in self._font_white_list:
                fonts.append(name)

        for name in sorted(fonts):
            self._add_menu(name)

    def _add_menu(self, font_name):
        label = f'<span font="{font_name}">{font_name}</span>'

        item = PaletteMenuItem()
        item.set_label(label)

        item.connect(
            "activate",
            self.__font_selected_cb,
            font_name
        )

        self._menu_box.append_item(item)

    def __font_selected_cb(self, menu, font_name):
        self._font_name = font_name
        self._font_label.set_font(font_name)
        self.emit("changed")

    def set_font_name(self, font_name):
        self._font_label.set_font(font_name)

    def get_font_name(self):
        return self._font_name


class FontSize(Gtk.Box):

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):

        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self._font_sizes = [
            8, 9, 10, 11, 12, 14, 16, 20,
            22, 24, 26, 28, 36, 48, 72
        ]

        self._default_size = 12
        self._font_size = self._default_size

        self._size_down = Gtk.Button()
        icon = Icon(icon_name="resize-")
        self._size_down.set_child(icon)
        self._size_down.connect("clicked", self.__font_sizes_cb, False)

        self.append(self._size_down)

        self._size_label = Gtk.Label(str(self._font_size))
        self.append(self._size_label)

        self._size_up = Gtk.Button()
        icon = Icon(icon_name="resize+")
        self._size_up.set_child(icon)
        self._size_up.connect("clicked", self.__font_sizes_cb, True)

        self.append(self._size_up)

    def __font_sizes_cb(self, button, increase):

        if self._font_size in self._font_sizes:

            i = self._font_sizes.index(self._font_size)

            if increase:
                if i < len(self._font_sizes) - 1:
                    i += 1
            else:
                if i > 0:
                    i -= 1

        else:
            i = self._font_sizes.index(self._default_size)

        self._font_size = self._font_sizes[i]

        self._size_label.set_text(str(self._font_size))

        self._size_down.set_sensitive(i != 0)
        self._size_up.set_sensitive(i < len(self._font_sizes) - 1)

        self.emit("changed")

    def set_font_size(self, size):

        if size not in self._font_sizes:

            for s in self._font_sizes:
                if s > size:
                    size = s
                    break

            if size > self._font_sizes[-1]:
                size = self._font_sizes[-1]

        self._font_size = size

        self._size_label.set_text(str(self._font_size))

        i = self._font_sizes.index(self._font_size)

        self._size_down.set_sensitive(i != 0)
        self._size_up.set_sensitive(i < len(self._font_sizes) - 1)

        self.emit("changed")

    def get_font_size(self):
        return self._font_size
