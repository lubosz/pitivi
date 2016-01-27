# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/overlay/viewer_overlay.py
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

from gi.repository import Gtk, GES
import numpy as np

from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import SELECT


class ViewerOverlay(Gtk.DrawingArea, Loggable):
    def __init__(self, stack, source):
        Gtk.DrawingArea.__init__(self)
        Loggable.__init__(self)
        self.stack = stack
        self.source = source
        self.connect("draw", self.on_draw)
        self.click_source_position = None
        project = stack.app.project_manager.current_project
        self.project_size = np.array([project.videowidth, project.videoheight])

    def is_hovered(self):
        return self.stack.hovered_overlay == self

    def is_selected(self):
        return self.stack.selected_overlay == self

    def select(self):
        self.stack.selected_overlay = self
        self.stack.app.gui.timeline_ui.timeline.selection.setSelection([self.source], SELECT)
        if isinstance(self.source, GES.TitleSource):
            page = 2
        elif isinstance(self.source, GES.VideoUriSource):
            page = 0
        else:
            self.warning("Unknown clip type: %s", self.source)
            return
        self.stack.app.gui.context_tabs.set_current_page(page)

    def deselect(self):
        self.stack.selected_overlay = None

    def hover(self):
        self.stack.hovered_overlay = self

    def unhover(self):
        self.stack.hovered_overlay = None
        self.queue_draw()

    def commit(self):
        self.stack.app.project_manager.current_project.pipeline.commit_timeline()
