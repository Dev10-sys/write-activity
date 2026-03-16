# Copyright (C) 2006, Martin Sevior
# Copyright (C) 2006-2007, Marc Maurer <uwog@uwog.net>
# Copyright (C) 2007, One Laptop Per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gettext import gettext as _
import logging

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk, GObject, GdkPixbuf

import os
import tempfile

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.colorbutton import ColorToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics import style
from sugar3.activity.widgets import CopyButton
from sugar3.activity.widgets import PasteButton
from sugar3.activity.widgets import UndoButton
from sugar3.activity.widgets import RedoButton

from widgets import AbiButton
from widgets import AbiMenuItem
from fontcombobox import FontComboBox
from fontcombobox import FontSize
from gridcreate import GridCreateWidget

logger = logging.getLogger('write-activity')


class EditToolbar(Gtk.Box):

    def __init__(self, pc, toolbar_box):

        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._abiword_canvas = pc.abiword_canvas

        copy = CopyButton()
        copy.props.accelerator = '<Ctrl>C'
        copy.connect('clicked', lambda button: pc.abiword_canvas.copy())
        self.append(copy)

        paste = PasteButton()
        paste.props.accelerator = '<Ctrl>V'
        paste.connect('clicked', self.__paste_button_cb)
        self.append(paste)

        menu_box = PaletteMenuBox()
        palette = paste.get_palette()
        palette.set_content(menu_box)
        menu_item = PaletteMenuItem()
        menu_item.set_label(_('Paste unformatted'))
        menu_item.connect('activate', self.__paste_special_button_cb)
        menu_box.append_item(menu_item)

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(separator)

        undo = UndoButton(sensitive=True)
        undo.connect('clicked', lambda button: pc.abiword_canvas.undo())
        pc.abiword_canvas.connect("can-undo", lambda abi, can_undo:
                                  undo.set_sensitive(can_undo))
        self.append(undo)

        redo = RedoButton(sensitive=True)
        redo.connect('clicked', lambda button: pc.abiword_canvas.redo())
        pc.abiword_canvas.connect("can-redo", lambda abi, can_redo:
                                  redo.set_sensitive(can_redo))
        self.append(redo)

        pc.abiword_canvas.connect('text-selected', lambda abi, b:
                                  copy.set_sensitive(True))
        pc.abiword_canvas.connect('image-selected', lambda abi, b:
                                  copy.set_sensitive(True))
        pc.abiword_canvas.connect('selection-cleared', lambda abi, b:
                                  copy.set_sensitive(False))

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(separator)

        search_label = Gtk.Label(label=_("Search:"))
        self.append(search_label)

        # setup the search options
        self._search_entry = Gtk.Entry()
        self._search_entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.PRIMARY,
            "system-search"
        )
        self._search_entry.connect('activate', self._search_entry_activated_cb)
        self._search_entry.connect('changed', self._search_entry_changed_cb)
        self._add_widget(self._search_entry, expand=True)

        self._findprev = ToolButton('go-previous-paired')
        self._findprev.set_tooltip(_('Find previous'))
        self.append(self._findprev)
        self._findprev.connect('clicked', self._findprev_cb)

        self._findnext = ToolButton('go-next-paired')
        self._findnext.set_tooltip(_('Find next'))
        self.append(self._findnext)
        self._findnext.connect('clicked', self._findnext_cb)

        # set the initial state of the search controls
        # note: we won't simple call self._search_entry_changed_cb
        # here, as that will call into the abiword_canvas, which
        # is not mapped on screen here, causing the set_find_string
        # call to fail
        self._findprev.set_sensitive(False)
        self._findnext.set_sensitive(False)

    def __paste_button_cb(self, button):
        display = Gdk.Display.get_default()

        if display is None:
            self._abiword_canvas.paste()
            return

        clipboard = display.get_clipboard()

        texture = clipboard.read_texture()

        if not texture:
            self._abiword_canvas.paste()
            return

        pixbuf = GdkPixbuf.Pixbuf.new_from_texture(texture)

        activity = self._abiword_canvas.get_toplevel()
        temp_path = os.path.join(activity.get_activity_root(), "instance")

        os.makedirs(temp_path, exist_ok=True)

        fd, file_path = tempfile.mkstemp(dir=temp_path, suffix=".png")
        os.close(fd)

        pixbuf.savev(file_path, "png", [], [])

        self._abiword_canvas.insert_image(file_path, False)

    def __paste_special_button_cb(self, button):
        self._abiword_canvas.paste_special()

    def _search_entry_activated_cb(self, entry):
        logger.debug('_search_entry_activated_cb')
        if not self._search_entry.props.text:
            return

        # find the next entry
        self._abiword_canvas.find_next(False)

    def _search_entry_changed_cb(self, entry):
        logger.debug('_search_entry_changed_cb search for \'%s\'',
                     self._search_entry.props.text)

        if not self._search_entry.props.text:
            self._search_entry.activate()
            # set the button contexts
            self._findprev.set_sensitive(False)
            self._findnext.set_sensitive(False)
            return

        self._abiword_canvas.set_find_string(self._search_entry.props.text)

        # set the button contexts
        self._findprev.set_sensitive(True)
        self._findnext.set_sensitive(True)

        # immediately start seaching
        self._abiword_canvas.find_next(True)

    def _findprev_cb(self, button):
        logger.debug('_findprev_cb')
        if self._search_entry.props.text:
            self._abiword_canvas.find_prev()
        else:
            logger.debug('nothing to search for!')

    def _findnext_cb(self, button):
        logger.debug('_findnext_cb')
        if self._search_entry.props.text:
            self._abiword_canvas.find_next(False)
        else:
            logger.debug('nothing to search for!')

    # bad foddex! this function was copied from sugar's activity.py
    def _add_widget(self, widget, expand=False):
        box = Gtk.Box()

        if expand:
            box.set_hexpand(True)

        box.append(widget)

        self.append(box)


class InsertToolbar(Gtk.Box):

    def __init__(self, abiword_canvas):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._abiword_canvas = abiword_canvas

        self._table_btn = ToolButton('create-table')
        self._table_btn.set_tooltip(_('Create table'))
        self._grid_create = GridCreateWidget()
        self._grid_create.connect('create-table', self._create_table_cb)
        palette = self._table_btn.get_palette()
        palette.set_content(self._grid_create)
        self._table_btn.connect('clicked', self._table_btn_clicked_cb)
        self.append(self._table_btn)

        self._table_rows_after = ToolButton('row-insert')
        self._table_rows_after.set_tooltip(_('Insert Row'))
        self._table_rows_after_id = self._table_rows_after.connect(
            'clicked', self._table_rows_after_cb)
        self.append(self._table_rows_after)

        self._table_delete_rows = ToolButton('row-remove')
        self._table_delete_rows.set_tooltip(_('Delete Row'))
        self._table_delete_rows_id = self._table_delete_rows.connect(
            'clicked', self._table_delete_rows_cb)
        self.append(self._table_delete_rows)

        self._table_cols_after = ToolButton('column-insert')
        self._table_cols_after.set_tooltip(_('Insert Column'))
        self._table_cols_after_id = self._table_cols_after.connect(
            'clicked', self._table_cols_after_cb)
        self.append(self._table_cols_after)

        self._table_delete_cols = ToolButton('column-remove')
        self._table_delete_cols.set_tooltip(_('Delete Column'))
        self._table_delete_cols_id = self._table_delete_cols.connect(
            'clicked', self._table_delete_cols_cb)
        self.append(self._table_delete_cols)

        self._merge_cells = ToolButton('format-columns-single')
        self._merge_cells.set_tooltip(_('Merge Cells'))
        self._merge_cells_id = self._merge_cells.connect(
            'clicked', self._merge_cells_cb)
        self.append(self._merge_cells)

        self._split_cells = ToolButton('format-columns-double')
        self._split_cells.set_tooltip(_('Split Cells'))
        self._split_cells_id = self._split_cells.connect(
            'clicked', self._split_cells_cb)
        self.append(self._split_cells)

        self._abiword_canvas.connect('table-state', self._isTable_cb)
        # self._abiword_canvas.connect('image-selected',
        #       self._image_selected_cb)

    def _table_btn_clicked_cb(self, button):
        button.get_palette().popup(True)

    def _create_table_cb(self, abi, rows, cols):
        self._abiword_canvas.insert_table(rows, cols)

    def _table_rows_after_cb(self, button):
        self._abiword_canvas.invoke_ex('insertRowsAfter', '', 0, 0)

    def _table_delete_rows_cb(self, button):
        self._abiword_canvas.invoke_ex('deleteRows', '', 0, 0)

    def _table_cols_after_cb(self, button):
        self._abiword_canvas.invoke_ex('insertColsAfter', '', 0, 0)

    def _table_delete_cols_cb(self, button):
        self._abiword_canvas.invoke_ex('deleteColumns', '', 0, 0)

    def _merge_cells_cb(self, button):
        self._abiword_canvas.invoke('mergeCells')

    def _split_cells_cb(self, button):
        self._abiword_canvas.invoke('splitCells')

    def _isTable_cb(self, abi, b):
        self._table_rows_after.set_sensitive(b)
        self._table_delete_rows.set_sensitive(b)
        self._table_cols_after.set_sensitive(b)
        self._table_delete_cols.set_sensitive(b)
        self._merge_cells.set_sensitive(b)
        self._split_cells.set_sensitive(b)


class ViewToolbar(Gtk.Box):

    def __init__(self, abiword_canvas):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._abiword_canvas = abiword_canvas
        self._zoom_percentage = 0

        self._zoom_out = ToolButton('zoom-out')
        self._zoom_out.set_tooltip(_('Zoom Out'))
        self._zoom_out_id = self._zoom_out.connect(
            'clicked', self._zoom_out_cb)
        self.append(self._zoom_out)

        self._zoom_in = ToolButton('zoom-in')
        self._zoom_in.set_tooltip(_('Zoom In'))
        self._zoom_in_id = self._zoom_in.connect('clicked',
                                                 self._zoom_in_cb)
        self.append(self._zoom_in)

        self._zoom_to_width = ToolButton('zoom-best-fit')
        self._zoom_to_width.set_tooltip(_('Zoom to width'))
        self._zoom_to_width.connect('clicked', self._zoom_to_width_cb)
        self.append(self._zoom_to_width)

        # TODO: fix the initial value
        self._zoom_spin_adj = Gtk.Adjustment(0, 25, 400, 25, 50, 0)
        self._zoom_spin = Gtk.SpinButton.new(self._zoom_spin_adj, 0, 0)
        self._zoom_spin_id = self._zoom_spin.connect('value-changed',
                                                     self._zoom_spin_cb)
        self._zoom_spin.set_numeric(True)
        box = Gtk.Box()
        box.append(self._zoom_spin)
        self.append(box)

        zoom_perc_label = Gtk.Label(label=_("%"))
        box = Gtk.Box()
        box.append(zoom_perc_label)
        self.append(box)

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(separator)

        page_label = Gtk.Label(_("Page: "))
        box = Gtk.Box()
        box.append(page_label)
        self.append(box)

        self._page_spin_adj = Gtk.Adjustment(0, 1, 0, 1, 1, 0)
        self._page_spin = Gtk.SpinButton.new(self._page_spin_adj, 0, 0)
        self._page_spin_id = self._page_spin.connect('value-changed',
                                                     self._page_spin_cb)
        self._page_spin.set_numeric(True)
        box = Gtk.Box()
        box.append(self._page_spin)
        self.append(box)

        self._total_page_label = Gtk.Label(label=" / 0")
        box = Gtk.Box()
        box.append(self._total_page_label)
        self.append(box)

        self._abiword_canvas.connect("page-count", self._page_count_cb)
        self._abiword_canvas.connect("current-page", self._current_page_cb)
        self._abiword_canvas.connect("zoom", self._zoom_cb)

    def set_zoom_percentage(self, zoom):
        self._zoom_percentage = zoom
        self._abiword_canvas.set_zoom_percentage(self._zoom_percentage)

    def _zoom_cb(self, canvas, zoom):
        self._zoom_spin.handler_block(self._zoom_spin_id)
        try:
            self._zoom_spin.set_value(zoom)
        finally:
            self._zoom_spin.handler_unblock(self._zoom_spin_id)

    def _zoom_out_cb(self, button):
        if self._zoom_percentage == 0:
            self._zoom_percentage = self._abiword_canvas.get_zoom_percentage()
        if self._zoom_percentage >= 50:
            self.set_zoom_percentage(self._zoom_percentage - 25)

    def _zoom_in_cb(self, button):
        if self._zoom_percentage == 0:
            self._zoom_percentage = self._abiword_canvas.get_zoom_percentage()
        if self._zoom_percentage <= 375:
            self.set_zoom_percentage(self._zoom_percentage + 25)

    def _zoom_to_width_cb(self, button):
        self._abiword_canvas.zoom_width()
        self._zoom_percentage = self._abiword_canvas.get_zoom_percentage()

    def _zoom_spin_cb(self, button):
        self._zoom_percentage = self._zoom_spin.get_value_as_int()
        self._abiword_canvas.set_zoom_percentage(self._zoom_percentage)

    def _page_spin_cb(self, button):
        page_num = self._page_spin.get_value_as_int()
        self._abiword_canvas.set_current_page(page_num)

    def _page_count_cb(self, canvas, count):
        current_page = canvas.get_current_page_num()
        self._page_spin_adj.configure(current_page, 1, count, 1, 10, 0)
        self._total_page_label.set_label(" / " + str(count))

    def _current_page_cb(self, canvas, num):
        self._page_spin.handler_block(self._page_spin_id)
        try:
            self._page_spin.set_value(num)
        finally:
            self._page_spin.handler_unblock(self._page_spin_id)


class TextToolbar(Gtk.Box):

    def __init__(self, abiword_canvas):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.font_name_combo = FontComboBox()
        self.font_name_combo.set_font_name('Sans')
        self._fonts_changed_id = self.font_name_combo.connect(
            'changed', self._font_changed_cb, abiword_canvas)
        self._abi_handler = abiword_canvas.connect('font-family',
                                                   self._font_family_cb)
        self.append(self.font_name_combo)

        self.font_size = FontSize()
        self._abi_handler = abiword_canvas.connect('font-size',
                                                   self._font_size_cb)
        self._font_size_changed_id = self.font_size.connect(
            'changed', self._font_size_changed_cb, abiword_canvas)
        self.append(self.font_size)

        bold = ToggleToolButton('format-text-bold')
        bold.set_tooltip(_('Bold'))
        bold.props.accelerator = '<Ctrl>B'
        bold_id = bold.connect('clicked', lambda sender:
                               abiword_canvas.toggle_bold())
        abiword_canvas.connect('bold', lambda abi, b:
                               self._setToggleButtonState(bold, b, bold_id))
        self.append(bold)

        italic = ToggleToolButton('format-text-italic')
        italic.set_tooltip(_('Italic'))
        italic.props.accelerator = '<Ctrl>I'
        italic_id = italic.connect('clicked', lambda sender:
                                   abiword_canvas.toggle_italic())
        abiword_canvas.connect('italic', lambda abi, b:
                               self._setToggleButtonState(italic, b,
                                                          italic_id))
        self.append(italic)

        underline = ToggleToolButton('format-text-underline')
        underline.set_tooltip(_('Underline'))
        underline.props.accelerator = '<Ctrl>U'
        underline_id = underline.connect('clicked', lambda sender:
                                         abiword_canvas.toggle_underline())
        abiword_canvas.connect('underline', lambda abi, b:
                               self._setToggleButtonState(underline, b,
                                                          underline_id))
        self.append(underline)

        super_btn = ToggleToolButton('format-text-super')
        super_btn.set_tooltip(_('Superscript'))
        super_btn.props.accelerator = '<Ctrl>asciicircum'
        super_id = super_btn.connect('clicked', lambda sender:
                                     abiword_canvas.toggle_super())
        abiword_canvas.connect('superscript', lambda abi, b:
                               self._setToggleButtonState(super_btn, b,
                                                          super_id))
        self.append(super_btn)

        sub = ToggleToolButton('format-text-sub')
        sub.set_tooltip(_('Subscript'))
        sub.props.accelerator = '<Ctrl>underscore'
        sub_id = sub.connect('clicked', lambda sender:
                             abiword_canvas.toggle_sub())
        abiword_canvas.connect('subscript', lambda abi, b:
                               self._setToggleButtonState(sub, b, sub_id))
        self.append(sub)

        color = ColorToolButton()
        color.connect('notify::color', self._text_color_cb,
                      abiword_canvas)
        box = Gtk.Box()
        box.append(color)
        self.append(box)
        abiword_canvas.connect(
            'color', lambda abi, r, g, b: self._set_text_color(color, r, g, b))

        # MAGIC NUMBER WARNING: Secondary toolbars are not a standard height?
        self.set_size_request(-1, style.GRID_CELL_SIZE)

        def append_align(icon_name, tooltip, do_abi_cb, style_name, button,
                         menu_box):
            menu_item = AbiMenuItem(abiword_canvas, style_name, do_abi_cb,
                                    icon_name, tooltip, button)
            menu_box.append_item(menu_item)

        self._aligment_btn = ToolButton(icon_name='format-justify-left')
        self._aligment_btn.props.tooltip = _('Choose alignment')
        self._aligment_btn.props.hide_tooltip_on_click = False
        self._aligment_btn.palette_invoker.props.toggle_palette = True

        menu_box = PaletteMenuBox()
        self._aligment_btn.props.palette.set_content(menu_box)
        append_align('format-justify-left', _('Left justify'),
                     abiword_canvas.align_left, 'left-align',
                     self._aligment_btn, menu_box)

        append_align('format-justify-center', _('Center justify'),
                     abiword_canvas.align_center, 'center-align',
                     self._aligment_btn, menu_box)

        append_align('format-justify-right', _('Right justify'),
                     abiword_canvas.align_right, 'right-align',
                     self._aligment_btn, menu_box)

        append_align('format-justify-fill', _('Fill justify'),
                     abiword_canvas.align_justify, 'justify-align',
                     self._aligment_btn, menu_box)

        self.append(self._aligment_btn)

    def _font_changed_cb(self, combobox, abi):
        logger.debug('Setting font: %s', combobox.get_font_name())
        try:
            abi.handler_block(self._abi_handler)
            abi.set_font_name(combobox.get_font_name())
        finally:
            abi.handler_unblock(self._abi_handler)

    def _font_family_cb(self, abi, font_family):
        logging.debug('Abiword font changed to %s', font_family)
        self.font_name_combo.set_font_name(font_family)

    def _font_size_changed_cb(self, widget, abi):
        abi.handler_block(self._abi_handler)
        try:
            abi.set_font_size(str(widget.get_font_size()))
        finally:
            abi.handler_unblock(self._abi_handler)

    def _font_size_cb(self, abi, size):
        logging.debug('Abiword font size changed to %s', size)
        self.font_size.handler_block(self._font_size_changed_id)
        self.font_size.set_font_size(int(size))
        self.font_size.handler_unblock(self._font_size_changed_id)

    def _setToggleButtonState(self, button, b, id):
        button.handler_block(id)
        button.set_active(b)
        button.handler_unblock(id)

    def _text_color_cb(self, button, pspec, abiword_canvas):
        newcolor = button.get_color()
        abiword_canvas.set_text_color(newcolor.red,
                                      newcolor.green,
                                      newcolor.blue)

    def _set_text_color(self, color, r, g, b):
        rgba = Gdk.RGBA()
        rgba.red = r
        rgba.green = g
        rgba.blue = b
        rgba.alpha = 1.0
        color.set_color(rgba)


class ParagraphToolbar(Gtk.Box):

    def __init__(self, abi):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        def append_style(icon_name, tooltip, do_abi_cb, on_abi_cb):
            button = AbiButton(abi, 'style-name', do_abi_cb, on_abi_cb)
            button.props.icon_name = icon_name
            button.props.group = group
            button.props.tooltip = tooltip
            self.append(button)
            return button

        group = None

        group = append_style(
            'list-none', _('Normal'),
            lambda: abi.set_style('Normal'),
            lambda abi, style: style not in [
                'Heading 1', 'Heading 2', 'Heading 3', 'Heading 4',
                'Block Text', 'Plain Text'])

        append_style('paragraph-h1', _('Heading 1'),
                     lambda: abi.set_style('Heading 1'),
                     lambda abi, style: style == 'Heading 1')

        append_style('paragraph-h2', _('Heading 2'),
                     lambda: abi.set_style('Heading 2'),
                     lambda abi, style: style == 'Heading 2')

        append_style('paragraph-h3', _('Heading 3'),
                     lambda: abi.set_style('Heading 3'),
                     lambda abi, style: style == 'Heading 3')

        append_style('paragraph-h4', _('Heading 4'),
                     lambda: abi.set_style('Heading 4'),
                     lambda abi, style: style == 'Heading 4')

        append_style('paragraph-blocktext', _('Block Text'),
                     lambda: abi.set_style('Block Text'),
                     lambda abi, style: style == 'Block Text')

        append_style('paragraph-plaintext', _('Plain Text'),
                     lambda: abi.set_style('Plain Text'),
                     lambda abi, style: style == 'Plain Text')

        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        def append_list(icon_name, tooltip, do_abi_cb, on_abi_cb, button,
                        menu_box, button_icon=None):
            menu_item = AbiMenuItem(
                abi, 'style-name', do_abi_cb,
                icon_name, tooltip, button, on_abi_cb, button_icon)
            menu_box.append_item(menu_item)

        list_btn = ToolButton(icon_name='toolbar-bulletlist')
        list_btn.props.tooltip = _('Select list')
        list_btn.props.hide_tooltip_on_click = False
        list_btn.palette_invoker.props.toggle_palette = True

        menu_box = PaletteMenuBox()
        list_btn.props.palette.set_content(menu_box)
        append_list('list-none', _('Normal'),
                    lambda: abi.set_style('Normal'),
                    lambda abi, style:
                    style not in ['Bullet List',
                                  'Dashed List',
                                  'Numbered List',
                                  'Lower Case List',
                                  'Upper Case List'],
                    list_btn, menu_box, 'toolbar-bulletlist')

        append_list('list-bullet', _('Bullet List'),
                    lambda: abi.set_style('Bullet List'),
                    lambda abi, style: style == 'Bullet List', list_btn,
                    menu_box)

        append_list('list-dashed', _('Dashed List'),
                    lambda: abi.set_style('Dashed List'),
                    lambda abi, style: style == 'Dashed List', list_btn,
                    menu_box)

        append_list('list-numbered', _('Numbered List'),
                    lambda: abi.set_style('Numbered List'),
                    lambda abi, style: style == 'Numbered List', list_btn,
                    menu_box)

        append_list('list-lower-case', _('Lower Case List'),
                    lambda: abi.set_style('Lower Case List'),
                    lambda abi, style: style == 'Lower Case List', list_btn,
                    menu_box)

        append_list('list-upper-case', _('Upper Case List'),
                    lambda: abi.set_style('Upper Case List'),
                    lambda abi, style: style == 'Upper Case List', list_btn,
                    menu_box)

        self.append(list_btn)
