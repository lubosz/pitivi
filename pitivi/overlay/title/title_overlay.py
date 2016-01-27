# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/overlay/title/title_overlay.py
#
# Copyright (c) 2016, Lubosz Sarnecki <lubosz.sarnecki@collabora.co.uk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import cairo
import numpy as np
from pitivi.overlay.viewer_overlay import ViewerOverlay


class TitleOverlay(ViewerOverlay):
    def __init__(self, stack, source):
        ViewerOverlay.__init__(self, stack, source)
        self.update_from_source()
        self.corners = []
        self.position = None
        self.size = None
        self.click_window_position = None

    def draw_rectangle(self, cr):
        for corner in self.corners:
            cr.line_to(*corner.tolist())
        cr.line_to(*self.position.tolist())

    def on_draw(self, widget, cr):
        if not self.is_selected() and not self.is_hovered():
            return

        cr.save()
        # clear background
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        cr.paint()

        if self.is_hovered():
            brightness = 0.65
        else:
            brightness = 0.3

        # clip away outer mask
        self.draw_rectangle(cr)
        cr.clip()
        cr.set_source_rgba(brightness, brightness, brightness, 0.6)
        self.draw_rectangle(cr)

        cr.set_line_width(16)
        cr.stroke()
        cr.restore()

    def get_source_position(self):
        res_x, x = self.source.get_child_property("xpos")
        res_y, y = self.source.get_child_property("ypos")
        assert res_x
        assert res_y
        return np.array([x, y])

    def set_source_position(self, position):
        if not isinstance(position, np.ndarray):
            return
        self.source.set_child_property("xpos", float(position[0]))
        self.source.set_child_property("ypos", float(position[1]))

    def update_corners(self):
        self.corners = [
            self.position,
            self.position + np.array([self.size[0], 0]),
            self.position + self.size,
            self.position + np.array([0, self.size[1]])
        ]

    def update_from_source(self):
        x = self.source.get_text_x()
        y = self.source.get_text_y()
        w = self.source.get_text_width()
        h = self.source.get_text_height()

        self.position = np.array([x, y]) * self.stack.window_size / self.project_size
        self.size = np.array([w, h]) * self.stack.window_size / self.project_size
        self.update_corners()

    def update_from_motion(self, title_position):
        self.position = title_position
        self.update_corners()

    def on_hover(self, cursor_position):
        if (self.position < cursor_position).all() and (cursor_position < self.position + self.size).all():
            if self.is_selected():
                self.stack.set_cursor("grab")
            self.hover()
        else:
            self.unhover()
        self.queue_draw()
        return self.is_hovered()

    def on_button_press(self, cursor_position):
        self.click_source_position = self.get_source_position()
        self.click_window_position = self.position
        if self.is_hovered():
            self.select()
            self.stack.set_cursor("grabbing")
            self.stack.selected_overlay = self
        elif self.is_selected():
            self.deselect()

    def on_button_release(self, cursor_position):
        self.click_source_position = None
        self.on_hover(cursor_position)
        if self.is_hovered():
            self.stack.set_cursor("grab")
        self.queue_draw()

    def on_leave(self):
        pass

    def on_motion_notify(self, cursor_position):
        if not isinstance(self.stack.click_position, np.ndarray):
                return
        title_position = self.click_source_position + self.stack.get_normalized_drag_distance(cursor_position)
        self.update_from_motion(self.click_window_position + self.stack.get_drag_distance(cursor_position))
        self.queue_draw()
        self.set_source_position(title_position)
        self.commit()
