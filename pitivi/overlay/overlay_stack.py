# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/overlay/overlay_stack.py
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

from gi.repository import Gtk, Gdk, GES
import numpy as np

from pitivi.overlay.move_scale.move_scale_overlay import MoveScaleOverlay
from pitivi.overlay.title.title_overlay import TitleOverlay


class OverlayStack(Gtk.Overlay):
    def __init__(self, app, sink_widget):
        Gtk.Overlay.__init__(self)
        self.overlays = {}
        self.visible_overlays = []
        self.app = app
        self.sink_widget = sink_widget
        self.add(sink_widget)
        self.window_size = np.array([1, 1])
        self.click_position = None
        self.hovered_overlay = None
        self.selected_overlay = None
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.SCROLL_MASK |
                        Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK |
                        Gdk.EventMask.ALL_EVENTS_MASK)
        self.connect("size-allocate", self.on_size_allocate)

    def on_size_allocate(self, widget, rectangle):
        self.window_size = np.array([rectangle.width,
                                     rectangle.height])
        for overlay in self.overlays.values():
            overlay.update_from_source()

    def do_event(self, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            cursor_position = np.array([event.x, event.y])
            self.click_position = None
            if self.selected_overlay:
                self.selected_overlay.on_button_release(cursor_position)
        elif event.type == Gdk.EventType.LEAVE_NOTIFY and event.mode == Gdk.CrossingMode.NORMAL:
            if isinstance(self.click_position, np.ndarray):
                return
            for overlay in self.overlays.values():
                overlay.unhover()
            self.reset_cursor()
        elif event.type == Gdk.EventType.BUTTON_PRESS:
            cursor_position = np.array([event.x, event.y])
            self.click_position = cursor_position
            if self.hovered_overlay:
                self.hovered_overlay.on_button_press(cursor_position)
            elif self.selected_overlay:
                self.selected_overlay.on_button_press(cursor_position)
        elif event.type == Gdk.EventType.MOTION_NOTIFY:
            cursor_position = np.array([event.x, event.y])

            if isinstance(self.click_position, np.ndarray):
                if self.selected_overlay:
                    self.selected_overlay.on_motion_notify(cursor_position)
            else:

                # Prioritize Handles
                if isinstance(self.selected_overlay, MoveScaleOverlay):
                    if self.selected_overlay.on_hover(cursor_position):
                        if self.selected_overlay.hovered_handle:
                            self.hovered_overlay = self.selected_overlay
                            return

                for overlay in self.visible_overlays:
                    if overlay.on_hover(cursor_position):
                        self.hovered_overlay = overlay
                        break
                if not self.hovered_overlay:
                    self.reset_cursor()
        elif event.type == Gdk.EventType.SCROLL:
            # TODO: Viewer zoom
            pass
        return True

    def add_overlay_for_source(self, source):
        if type(source) == GES.TitleSource:
            overlay = TitleOverlay(self, source)
        else:
            overlay = MoveScaleOverlay(self, source)
        self.add_overlay(overlay)
        self.overlays[source] = overlay

    def set_current_sources(self, sources):
        self.visible_overlays = []
        # check if source has instanced overlay
        for source in sources:
            if source not in self.overlays.keys():
                self.add_overlay_for_source(source)
            self.visible_overlays.append(self.overlays[source])
        # check if overlay should be visible
        for source in self.overlays.keys():
            if source in sources:
                self.overlays[source].show()
            else:
                self.overlays[source].hide()

    def update(self, source):
        self.overlays[source].update_from_source()

    def select(self, source):
        if source not in self.overlays.keys():
            self.add_overlay_for_source(source)
        self.selected_overlay = self.overlays[source]
        self.selected_overlay.queue_draw()

    def set_cursor(self, type):
        display = Gdk.Display.get_default()
        if isinstance(type, Gdk.CursorType):
            cursor = Gdk.Cursor.new_for_display(display, type)
        else:
            cursor = Gdk.Cursor.new_from_name(display, type)
        self.app.gui.get_window().set_cursor(cursor)

    def reset_cursor(self):
        self.app.gui.get_window().set_cursor(None)

    def get_drag_distance(self, cursor_position):
        return cursor_position - self.click_position

    def get_normalized_drag_distance(self, cursor_position):
        return self.get_drag_distance(cursor_position) / self.window_size

    def get_normalized_cursor_position(self, cursor_position):
        return cursor_position / self.window_size
