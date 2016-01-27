# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/overlay/move_scale/handle.py
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

from math import pi
import cairo
import numpy as np


class Handle:
    def __init__(self, overlay, x=0, y=0):
        self.overlay = overlay
        self.position = np.array([x, y])

        self.name = ""

        self.clicked = False
        self.hovered = False
        self.window_position = None
        self.translation = None
        self.position_window_cached = None
        self.click_position_compare = None
        self.click_position = None
        self.opposite_position = None
        self.opposite_to_handle = None
        self.cursor = None

        self.glow = 0.9
        self.reference_radius = 15
        self.radius = 15
        self.minimal_radius = 5

        self.update_window_position()

    def get_position_translated(self):
        return self.position + self.translation

    def get_position_window(self):
        return self.get_position_translated() * self.overlay.stack.window_size

    def get_position_source(self):
        """
        Calculate source translation when certain handles are used
        for top and left handles we need to translate
        the source to get a correct resize pivot
        """
        source_position = None
        if "T" in self.name or "L" in self.name:
            position_stream_size = self.position * self.overlay.project_size
            # only x source translation changes
            if self.name in ["BL", "L"]:
                position_stream_size[1] = 0
            # only y source translation changes
            elif self.name in ["TR", "T"]:
                position_stream_size[0] = 0
            source_position = position_stream_size + self.overlay.click_source_position

        return source_position

    def get_normalized_minimal_size(self):
        return 4 * self.minimal_radius / self.overlay.stack.window_size

    def set_position(self, position):
        self.position = position
        self.update_window_position()

    def set_translation(self, translation):
        self.translation = translation
        self.update_window_position()

    def set_x(self, x):
        # self.position[0] = x
        self.position = np.array([x, self.position[1]])
        self.update_window_position()

    def set_y(self, y):
        # self.position[1] = y
        self.position = np.array([self.position[0], y])
        self.update_window_position()

    def on_hover(self, cursor_pos):
        distance = np.linalg.norm(self.position_window_cached - cursor_pos)

        if distance < self.radius:
            self.hovered = True
            self.overlay.stack.set_cursor(self.cursor)
        else:
            self.hovered = False

    def on_click(self):
        self.click_position = self.position
        self.calculate_opposite()

    def on_drag(self, click_to_cursor):
        handle_to_cursor = click_to_cursor + self.click_position
        restricted_handle_to_cursor = self.restrict(handle_to_cursor)

        # Update box from motion event coordinates
        self.set_position(restricted_handle_to_cursor)
        self.update_neighbours()

    def on_release(self):
        self.opposite_position = None
        self.opposite_to_handle = None

    def restrict_to_minimal_size(self, cursor_position):
        minimal_size = self.get_minimal_box_size()
        handle_to_opposite_sign = np.sign(self.opposite_to_handle)
        minimal_size_handle_position = self.opposite_position + minimal_size * handle_to_opposite_sign
        cursor_position_compare = cursor_position >= minimal_size_handle_position
        handle_position_compare = handle_to_opposite_sign >= np.array([0, 0])

        if self.needs_size_restriction(handle_position_compare, cursor_position_compare):
            cursor_position = minimal_size_handle_position
        return cursor_position

    def restrict_radius_to_size(self, size):
        if size < self.reference_radius * 5:
            radius = size / 5
            if radius < self.minimal_radius:
                radius = self.minimal_radius
            self.radius = radius
        else:
            self.radius = self.reference_radius

    def update_window_position(self):
        if isinstance(self.translation, np.ndarray):
            self.position_window_cached = self.get_position_window()

    def reset_size(self):
        self.radius = self.reference_radius

    def calculate_opposite(self):
        self.opposite_to_handle = 2 * (self.position - self.overlay.get_center())
        self.opposite_position = self.position - self.opposite_to_handle

    def draw(self, cr):
        if self.clicked:
            outer_color = .2
            glow_radius = 1.08
        elif self.hovered:
            outer_color = .8
            glow_radius = 1.08
        else:
            outer_color = .5
            glow_radius = 1.01

        cr.set_source_rgba(self.glow, self.glow, self.glow, 0.9)
        cr.arc(*self.position_window_cached.tolist(), self.radius * glow_radius, 0, 2 * pi)
        cr.fill()

        from_point = (self.position_window_cached[0], self.position_window_cached[1] - self.radius)
        to_point = (self.position_window_cached[0], self.position_window_cached[1] + self.radius)
        linear = cairo.LinearGradient(*(from_point + to_point))
        linear.add_color_stop_rgba(0.00, outer_color, outer_color, outer_color, 1)
        linear.add_color_stop_rgba(0.55, .1, .1, .1, 1)
        linear.add_color_stop_rgba(0.65, .1, .1, .1, 1)
        linear.add_color_stop_rgba(1.00, outer_color, outer_color, outer_color, 1)

        cr.set_source(linear)

        cr.arc(*self.position_window_cached.tolist(), self.radius * .9, 0, 2 * pi)
        cr.fill()


class CornerHandle(Handle):
    def __init__(self, overlay, x=0, y=0):
        Handle.__init__(self, overlay, x, y)

    def get_minimal_box_size(self):
        # keep aspect when making a minimal box when corner is dragged
        minimal_size = self.get_normalized_minimal_size()
        if self.overlay.get_aspect_ratio() < 1.0:
            minimal_size[1] = minimal_size[0] / self.overlay.get_aspect_ratio()
        else:
            minimal_size[0] = minimal_size[1] * self.overlay.get_aspect_ratio()
        return minimal_size

    def needs_size_restriction(self, handle_position_compare, cursor_position_compare):
        if (handle_position_compare != cursor_position_compare).any():
            return True

    def update_neighbours(self):
        neighbours = []
        if self.name == "TL":
            neighbours = ["BL", "TR"]
        elif self.name == "BL":
            neighbours = ["TL", "BR"]
        elif self.name == "BR":
            neighbours = ["TR", "BL"]
        elif self.name == "TR":
            neighbours = ["BR", "TL"]
        self.move_neighbours(*neighbours, self.position)

    def restrict_to_aspect_ratio(self, cursor_position):
        opposite_to_cursor = cursor_position - self.opposite_position
        opposite_to_cursor_ratio = opposite_to_cursor[0] / opposite_to_cursor[1]
        opposite_to_handle_ratio = self.opposite_to_handle[0] / self.opposite_to_handle[1]
        restricted_cursor_position = cursor_position

        if abs(opposite_to_cursor_ratio) > abs(opposite_to_handle_ratio):
            # adjust width
            restricted_cursor_position[0] = self.opposite_position[0] + opposite_to_cursor[1] * opposite_to_handle_ratio
        else:
            # adjust height
            restricted_cursor_position[1] = self.opposite_position[1] + opposite_to_cursor[0] / opposite_to_handle_ratio
        return restricted_cursor_position

    def restrict(self, handle_to_cursor):
        return self.restrict_to_minimal_size(
            self.restrict_to_aspect_ratio(
                handle_to_cursor))

    def move_neighbours(self, a, b, position):
        self.overlay.handles[a].set_x(position[0])
        self.overlay.handles[b].set_y(position[1])


class EdgeHandle(Handle):
    def __init__(self, overlay, x=0, y=0):
        Handle.__init__(self, overlay, x, y)

    def get_minimal_box_size(self):
        # nullify x / y in minimal box for edge handles
        # required in minimal handle position calculation
        minimal_size = self.get_normalized_minimal_size()
        if self.opposite_to_handle[0] == 0:
            # top bottom
            minimal_size[0] = 0
        else:
            # left right
            minimal_size[1] = 0
        return minimal_size

    def needs_size_restriction(self, handle_position_compare, cursor_position_compare):
        if self.opposite_to_handle[0] == 0:
            # top bottom
            if handle_position_compare[1] != cursor_position_compare[1]:
                return True
        else:
            # left right
            if handle_position_compare[0] != cursor_position_compare[0]:
                return True

    def get_neighbour_corners(self):
        neighbours = []
        for key in self.overlay.corner_handles:
            if self.name in key:
                neighbours.append(key)
        return neighbours

    def restrict(self, handle_to_cursor):
        return self.restrict_to_minimal_size(handle_to_cursor)

    def update_neighbours(self):
        corners = self.get_neighbour_corners()
        if self.name == "L" or self.name == "R":
            self.move_neighbours_x(*corners, self.position)
        elif self.name == "T" or self.name == "B":
            self.move_neighbours_y(*corners, self.position)

    def move_neighbours_x(self, a, b, position):
        self.overlay.handles[a].set_x(position[0])
        self.overlay.handles[b].set_x(position[0])

    def move_neighbours_y(self, a, b, position):
        self.overlay.handles[a].set_y(position[1])
        self.overlay.handles[b].set_y(position[1])
