# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/viewer/sinks.py
#
# Copyright (c) 2014, Lubosz Sarnecki <lubosz@gmail.com>
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

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gst, GstGL, Graphene

from pitivi.viewer.scene import *


class GstOverlaySink(Gtk.DrawingArea):
    def __init__(self, name, w, h):
        Gtk.DrawingArea.__init__(self)
        from gi.repository import GdkX11, GstVideo

        self.sink = Gst.ElementFactory.make(name, None)
        self.set_size_request(w, h)
        self.set_double_buffered(True)

    def xid(self):
        return self.get_window().get_xid()

    def set_handle(self):
        self.sink.set_window_handle(self.xid())


class CairoGLSink(GstOverlaySink):
    def __init__(self, w, h):
        GstOverlaySink.__init__(self, "glimagesink", w, h)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.add_events(Gdk.EventMask.ALL_EVENTS_MASK)

        self.gl_init = False

        self.scene = TransformScene()

        self.sink.connect("client-draw", self.scene.draw)
        self.sink.connect("client-reshape", self.scene.reshape)

        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.scene.on_release)
        self.connect("motion-notify-event", self.scene.on_motion)
        self.connect("scroll-event", self.scene.on_scroll)

        self.sink.handle_events(False)

        self.canvas_width, self.canvas_height = w, h
        self.aspect = w / h

        self.transformation_element = None
        self.pipeline = None
        self.pipeline_position = 0

    def set_transformation_element(self, element):
        self.transformation_element = element

    def set_pipeline(self, pipeline):
        self.pipeline = pipeline

    def set_pipeline_position(self, position):
        self.pipeline_position = position

    def flush_seek(self):
        self.pipeline.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH,
            self.pipeline_position)
        return True

    def on_button_press(self, sink, event):
        self.scene.on_press(event)

        if self.pipeline.get_state(Gst.CLOCK_TIME_NONE)[1] == Gst.State.PAUSED:
            GLib.timeout_add(90, self.flush_seek)
