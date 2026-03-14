#!/usr/bin/python
# Copyright (C) 2013, One Laptop per Child
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

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics import style


HALF_LINE = int(style.LINE_WIDTH / 2)


class GridCreateWidget(Gtk.DrawingArea):

    __gsignals__ = {
        'create-table': (
            GObject.SignalFlags.RUN_FIRST, None, [int, int]), }

    def __init__(self):
        super(GridCreateWidget, self).__init__()
        self._cell_width = style.GRID_CELL_SIZE
        self._cell_height = int(self._cell_width / 2)
        self._rows = 0
        self._columns = 0
        self._min_rows = 3
        self._min_columns = 3

        # Padding to the sides are not added automatically
        self.props.margin_start = style.DEFAULT_SPACING
        self.props.margin_end = style.DEFAULT_SPACING

        self._update_size()
        self.set_draw_func(self.__draw_cb)

        click = Gtk.GestureClick()
        click.connect('pressed', self.__pressed_cb)
        click.connect('released', self.__released_cb)
        self.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.connect('motion', self.__motion_cb)
        self.add_controller(motion)

    def _update_cell_position(self, x, y):
        columns = int(x / self._cell_width) + 1
        rows = int(y / self._cell_height) + 1
        if self._columns != columns or self._rows != rows:
            self._columns = columns
            self._rows = rows
            self._update_size()

    def __pressed_cb(self, gesture, n_press, x, y):
        self._update_cell_position(x, y)

    def __released_cb(self, gesture, n_press, x, y):
        self.emit('create-table', self._rows, self._columns)

    def __motion_cb(self, controller, x, y):
        self._update_cell_position(x, y)

    def _update_size(self):
        self._min_col = max(self._columns + 1, self._min_columns)
        self._width = self._min_col * self._cell_width
        self._min_rows = max(self._rows + 1, self._min_rows)
        self._height = self._min_rows * self._cell_height
        # Add spacd for the line to show on the outsides
        self.set_size_request(self._width + style.LINE_WIDTH,
                              self._height + style.LINE_WIDTH)
        self.queue_draw()

    def __draw_cb(self, widget, cr, width, height):
        # background
        cr.set_source_rgba(*style.COLOR_BLACK.get_rgba())
        cr.rectangle(0, 0, self._width, self._height)
        cr.fill()
        # used area
        cr.set_source_rgba(*style.COLOR_HIGHLIGHT.get_rgba())
        width = self._columns * self._cell_width
        height = self._rows * self._cell_height
        cr.rectangle(0, 0, width, height)
        cr.fill()
        # draw grid
        cr.set_line_width(style.LINE_WIDTH)
        cr.set_source_rgba(*style.COLOR_HIGHLIGHT.get_rgba())
        self._draw_grid(cr, self._min_rows, self._min_col, self._width,
                        self._height)
        if self._rows > 0 or self._columns > 0:
            cr.set_source_rgba(*style.COLOR_TOOLBAR_GREY.get_rgba())
            self._draw_grid(cr, self._rows, self._columns, width, height)

    def _draw_grid(self, cr, rows, cols, width, height):
        for n in range(rows + 1):
            cr.move_to(0, n * self._cell_height + HALF_LINE)
            cr.line_to(width, n * self._cell_height + HALF_LINE)
        for n in range(cols + 1):
            cr.move_to(n * self._cell_width + HALF_LINE, 0)
            cr.line_to(n * self._cell_width + HALF_LINE, height)
        cr.stroke()

        # properly fill the line cap in the bottom right corner
        cr.rectangle(width, height, style.LINE_WIDTH * 2, style.LINE_WIDTH * 2)
        cr.fill()



