# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/overlay/move_scale/move_scale_overlay.py
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
from collections import OrderedDict

import cairo
import numpy as np
from gi.repository import Gdk

from pitivi.overlay.move_scale.handle import CornerHandle, EdgeHandle
from pitivi.overlay.viewer_overlay import ViewerOverlay


class MoveScaleOverlay(ViewerOverlay):
    def __init__(self, stack, source):
        ViewerOverlay.__init__(self, stack, source)
        stream_info = source.get_asset().get_stream_info()
        self.stream_size = np.array([stream_info.get_width(), stream_info.get_height()])

        self.clicked_handle = None
        self.hovered_handle = None
        self.box_hovered = False
        self.click_diagonal_sign = None

        # Corner handles need to be ordered for drawing.
        self.corner_handles = OrderedDict([
            ("TL", CornerHandle(self, 0, 0)),
            ("BL", CornerHandle(self, 0, 1)),
            ("BR", CornerHandle(self, 1, 1)),
            ("TR", CornerHandle(self, 1, 0))])

        self.edge_handles = {
            "T": EdgeHandle(self, 0.5, 0),
            "B": EdgeHandle(self, 0.5, 1),
            "L": EdgeHandle(self, 0, 0.5),
            "R": EdgeHandle(self, 1, 0.5)
        }
        self.handles = {**self.corner_handles, **self.edge_handles}

        cursors = {
            "BR": Gdk.CursorType.BOTTOM_RIGHT_CORNER,
            "BL": Gdk.CursorType.BOTTOM_LEFT_CORNER,
            "TL": Gdk.CursorType.TOP_LEFT_CORNER,
            "TR": Gdk.CursorType.TOP_RIGHT_CORNER,
            "B": Gdk.CursorType.BOTTOM_SIDE,
            "L": Gdk.CursorType.LEFT_SIDE,
            "T": Gdk.CursorType.TOP_SIDE,
            "R": Gdk.CursorType.RIGHT_SIDE
        }

        for key in self.handles:
            self.handles[key].name = key
            self.handles[key].cursor = cursors[key]

        self.update_from_source()

    def get_source_position(self):
        if self.source:
            res_x, x = self.source.get_child_property("posx")
            res_y, y = self.source.get_child_property("posy")
            assert res_x
            assert res_y
            return np.array([x, y])

    def get_source_size(self):
        if self.source:
            res_x, x = self.source.get_child_property("width")
            res_y, y = self.source.get_child_property("height")
            assert res_x
            assert res_y
            return np.array([x, y])

    def get_normalized_source_position(self):
        return self.get_source_position() / self.project_size

    def set_source_position(self, position):
        if not isinstance(position, np.ndarray):
            return
        self.source.set_child_property("posx", int(position[0]))
        self.source.set_child_property("posy", int(position[1]))

    def set_source_size(self, size):
        self.source.set_child_property("width", int(size[0]))
        self.source.set_child_property("height", int(size[1]))

    def get_center(self):
        diagonal = self.handles["BR"].position - self.handles["TL"].position
        return self.handles["TL"].position + (diagonal / 2)

    def get_size(self):
        return np.array([self.get_width(), self.get_height()])

    def get_size_stream(self):
        return self.get_size() * self.project_size

    def get_height(self):
        return self.handles["BL"].position[1] - self.handles["TL"].position[1]

    def get_width(self):
        return self.handles["BR"].position[0] - self.handles["BL"].position[0]

    def get_aspect_ratio(self):
        size = self.get_size()
        return size[0] / size[1]

    def set_size_from_source(self, size):
        if not isinstance(size, np.ndarray):
            return
        relative_size = size / self.project_size
        self.handles["TL"].position = np.array([0, 0])
        self.handles["BL"].position = np.array([0, relative_size[1]])
        self.handles["BR"].position = np.array([relative_size[0], relative_size[1]])
        self.handles["TR"].position = np.array([relative_size[0], 0])
        self.update_egdes_from_corners()

    def set_position_from_source(self, stream_position):
        for handle in self.handles.values():
            handle.set_translation(stream_position / self.project_size)

    def on_button_press(self, cursor_position):
        self.click_source_position = self.get_source_position()
        self.clicked_handle = None

        if self.hovered_handle:
            self.hovered_handle.on_click()
            self.clicked_handle = self.hovered_handle
        elif self.box_hovered:
            self.select()
            self.stack.set_cursor("grabbing")
            self.stack.selected_overlay = self
        elif self.is_selected():
            self.deselect()
            self.hovered_handle = None

    def on_button_release(self, cursor_position):
        self.click_source_position = None
        self.update_from_source()
        self.on_hover(cursor_position)

        if self.clicked_handle:
            if not self.clicked_handle.hovered:
                self.stack.reset_cursor()
            self.clicked_handle.on_release()
            self.clicked_handle = None
        elif self.is_hovered():
            self.stack.set_cursor("grab")

        self.queue_draw()

    def on_motion_notify(self, cursor_pos):
        # Move Clicked
        click_to_cursor = self.stack.get_normalized_drag_distance(cursor_pos)
        if self.clicked_handle:
            self.clicked_handle.on_drag(click_to_cursor)
            self.update_egdes_from_corners()
            self.set_source_position(self.clicked_handle.get_position_source())
            self.set_source_size(self.get_size_stream())
            self.update_handle_sizes()
        else:
            stream_position = self.click_source_position + click_to_cursor * self.project_size
            self.set_position_from_source(stream_position)
            self.set_source_position(stream_position)
        self.queue_draw()
        self.commit()

    def on_hover(self, cursor_pos):
        # handles hover check
        self.hovered_handle = None
        if self.is_selected():
            for handle in self.handles.values():
                handle.on_hover(cursor_pos)
                if handle.hovered:
                    self.hovered_handle = handle
            if self.hovered_handle:
                self.hover()
                self.queue_draw()
                return True

        # box hover check
        source = self.get_normalized_source_position()
        cursor = self.stack.get_normalized_cursor_position(cursor_pos)

        self.box_hovered = False
        if (source < cursor).all() and (cursor < source + self.get_size()).all():
            self.box_hovered = True
            self.stack.set_cursor("grab")
            self.hover()
        else:
            self.box_hovered = False
            self.unhover()

        self.queue_draw()
        return self.box_hovered

    def reset_handle_sizes(self):
        for handle in self.handles.values():
            handle.reset_size()
        self.update_handle_sizes()

    def update_handle_sizes(self):
        size = self.get_size() * self.stack.window_size
        smaller_size = np.amin(size)

        for handle in self.handles.values():
            handle.restrict_radius_to_size(smaller_size)

    def update_egdes_from_corners(self):
        half_w = np.array([self.get_width() * 0.5, 0])
        half_h = np.array([0, self.get_height() * 0.5])

        self.handles["L"].set_position(self.handles["TL"].position + half_h)
        self.handles["R"].set_position(self.handles["TR"].position + half_h)
        self.handles["B"].set_position(self.handles["BL"].position + half_w)
        self.handles["T"].set_position(self.handles["TR"].position - half_w)

    def update_from_source(self):
        self.set_size_from_source(self.get_source_size())
        self.set_position_from_source(self.get_source_position())
        self.reset_handle_sizes()
        self.queue_draw()

    def draw_rectangle(self, cr):
        for handle in self.corner_handles.values():
            cr.line_to(*handle.position_window_cached.tolist())
        cr.line_to(*self.handles["TL"].position_window_cached.tolist())

    def on_draw(self, widget, cr):
        if not self.is_selected() and not self.is_hovered():
            return

        cr.save()
        # clear background
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        cr.paint()

        if self.box_hovered:
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

        if self.is_selected():
            for handle in self.handles.values():
                handle.draw(cr)
