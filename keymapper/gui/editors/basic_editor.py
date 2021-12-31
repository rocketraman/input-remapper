#!/usr/bin/python3
# -*- coding: utf-8 -*-
# key-mapper - GUI for device specific keyboard mappings
# Copyright (C) 2021 sezanzeb <proxima@sezanzeb.de>
#
# This file is part of key-mapper.
#
# key-mapper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# key-mapper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with key-mapper.  If not, see <https://www.gnu.org/licenses/>.


"""The basic editor with one row per mapping."""


from gi.repository import Gtk, GLib

from keymapper.gui.custom_mapping import custom_mapping
from keymapper.key import Key
from keymapper.gui.editors.base import SingleEditableMapping, store
from keymapper.logger import logger


class _KeycodeRecordingToggle(Gtk.ToggleButton):
    """Displays instructions and the current key of a single mapping."""

    __gtype_name__ = "ToggleButton"

    def __init__(self, key):
        """

        Parameters
        ----------
        key : Key
        """
        super().__init__()

        self.key = key

        self.set_size_request(140, -1)

        # make the togglebutton go back to its normal state when doing
        # something else in the UI
        self.connect("focus-in-event", self.on_focus)
        self.connect("focus-out-event", self.on_unfocus)

        if key is not None:
            self.set_label(key.beautify())
        else:
            self.show_click_here()

    def on_focus(self, *_):
        """Refresh useful usage information."""
        self.show_press_key()

    def on_unfocus(self, *_):
        """Refresh useful usage information and set some state stuff."""
        self.show_click_here()

    def show_click_here(self):
        """Show 'click here' on the keycode input button."""
        if self.key is not None:
            return

        self.set_label("Click here")
        self.set_opacity(0.3)

    def show_press_key(self):
        """Show 'press key' on the keycode input button."""
        if self.key is not None:
            return

        self.set_label("Press key")
        self.set_opacity(1)

    def set_key(self, key):
        """Set the key and display it."""
        self.key = key
        self.set_label(key.beautify())

    def set_label(self, label):
        """Set the label of the keycode input."""
        super().set_label(label)
        # Make the child label widget break lines, important for
        # long combinations
        label = self.get_child()
        label.set_line_wrap(True)
        label.set_line_wrap_mode(2)
        label.set_max_width_chars(13)
        label.set_justify(Gtk.Justification.CENTER)
        self.set_opacity(1)


class Row(Gtk.ListBoxRow, SingleEditableMapping):
    """A single configurable key mapping of the basic editor.

    Configures an entry in custom_mapping.
    """

    __gtype_name__ = "ListBoxRow"

    def __init__(self, *args, delete_callback, key=None, symbol=None, **kwargs):
        """

        Parameters
        ----------
        key : Key
            The key this row is going to display by default
        symbol : str
            The symbol/macro this row is going to display by default
        """
        Gtk.ListBoxRow.__init__(self)

        # create all child GTK widgets and connect their signals
        delete_button = Gtk.EventBox()
        close_image = Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.BUTTON)
        delete_button.add(close_image)
        delete_button.connect("button-press-event", self.on_delete_button_clicked)
        delete_button.set_size_request(50, -1)

        key_recording_toggle = _KeycodeRecordingToggle(key)
        self.key_recording_toggle = key_recording_toggle
        self.key_recording_toggle.key = key

        text_input = Gtk.Entry()
        self.text_input = text_input
        text_input.set_alignment(0.5)
        text_input.set_width_chars(4)
        text_input.set_has_frame(False)
        completion = Gtk.EntryCompletion()
        completion.set_model(store)
        completion.set_text_column(0)
        completion.set_match_func(self.match)
        text_input.set_completion(completion)

        if symbol is not None:
            text_input.set_text(symbol)

        self.text_input.connect("changed", self.on_text_input_change)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_homogeneous(False)
        box.set_spacing(0)
        box.pack_start(key_recording_toggle, expand=False, fill=True, padding=0)
        box.pack_start(text_input, expand=True, fill=True, padding=0)
        box.pack_start(delete_button, expand=False, fill=True, padding=0)
        box.show_all()
        box.get_style_context().add_class("row-box")

        self.delete_callback = delete_callback

        self.add(box)
        self.show_all()

        SingleEditableMapping.__init__(self, *args, **kwargs)

    def get_recording_toggle(self):
        return self.key_recording_toggle

    def get_text_input(self):
        return self.text_input

    def get_key(self):
        """Get the Key object from the left column.

        Or None if no code is mapped on this row.
        """
        return self.key_recording_toggle.key

    def get_symbol(self):
        """Get the assigned symbol from the middle column."""
        symbol = self.text_input.get_text()
        return symbol if symbol else None

    def set_symbol(self, symbol):
        """Set the assigned symbol from the middle column."""
        self.text_input.set_text(symbol)

    def display_key(self, key):
        """Show what the user is currently pressing in ther user interface."""
        self.key_recording_toggle.set_key(key)

    def on_delete_button_clicked(self, *_):
        """Destroy the row and remove it from the config."""
        super().on_delete_button_clicked()
        self.key_recording_toggle.set_label("")
        self.key_recording_toggle.key = None
        self.delete_callback(self)


class BasicEditor:
    """Maintains the widgets of the simple editor."""

    def __init__(self, user_interface):
        self.user_interface = user_interface
        self.window = self.get("window")
        self.timeout = GLib.timeout_add(100, self.check_add_row)
        mapping_list = self.get("mapping_list")
        mapping_list.connect("destroy", self.__del__)

    def get(self, name):
        """Get a widget from the window"""
        return self.user_interface.builder.get_object(name)

    def __del__(self, *_):
        """Clear up all timeouts and resources.

        This is especially important for tests.
        """
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None

    def load_custom_mapping(self):
        """Display the custom mapping."""
        mapping_list = self.get("mapping_list")
        mapping_list.forall(mapping_list.remove)

        for key, output in custom_mapping:
            row = Row(
                user_interface=self.user_interface,
                delete_callback=self.on_row_removed,
                key=key,
                symbol=output,
            )
            toggle = row.key_recording_toggle
            toggle.connect("focus-in-event", self.user_interface.can_modify_mapping)
            toggle.connect("focus-out-event", self.user_interface.save_preset)
            mapping_list.insert(row, -1)

        self.check_add_row()

    def get_focused_row(self):
        """Get the Row and its child that is currently in focus."""
        focused = self.window.get_focus()
        if focused is None:
            return None, None

        box = focused.get_parent()
        if box is None:
            return None, None

        row = box.get_parent()
        if not isinstance(row, Row):
            return None, None

        return row, focused

    def check_add_row(self):
        """Ensure that one empty row is available at all times."""
        mapping_list = self.get("mapping_list")
        rows = mapping_list.get_children()

        # verify that all mappings are displayed.
        # One of them is possibly the empty row
        num_rows = len(rows)
        num_maps = len(custom_mapping)
        if num_rows < num_maps or num_rows > num_maps + 1:
            # good for finding bugs early on during development.
            # If you get these logs during tests, then maybe some earlier test
            # has still a glib timeout running.
            logger.error(
                "custom_mapping contains %d rows, but %d are displayed",
                len(custom_mapping),
                num_rows,
            )
            logger.spam("Mapping %s", list(custom_mapping))
            logger.spam(
                "Rows    %s", [(row.get_key(), row.get_symbol()) for row in rows]
            )

        # iterating over that 10 times per second is a bit wasteful,
        # but the old approach which involved just counting the number of
        # mappings and rows didn't seem very robust.
        for row in rows:
            if row.get_key() is None or row.get_symbol() is None:
                # unfinished row found
                break
        else:
            self.add_empty()

        return True

    def consume_newest_keycode(self, key):
        """To capture events from keyboards, mice and gamepads.

        Parameters
        ----------
        key : Key or None
            If None will unfocus the input widget
        """
        # inform the currently selected row about the new keycode
        row, focused = self.get_focused_row()
        if row:
            row.consume_newest_keycode(key)

    def clear_mapping_table(self):
        """Remove all rows from the mappings table."""
        mapping_list = self.get("mapping_list")
        mapping_list.forall(mapping_list.remove)
        custom_mapping.empty()

    def add_empty(self):
        """Add one empty row for a single mapped key."""
        logger.spam("Adding a new empty row")
        empty = Row(
            user_interface=self.user_interface, delete_callback=self.on_row_removed
        )
        mapping_list = self.get("mapping_list")
        mapping_list.insert(empty, -1)

    def on_row_removed(self, row):
        """Stuff to do when a row was removed

        Parameters
        ----------
        row : Row
        """
        mapping_list = self.get("mapping_list")
        # https://stackoverflow.com/a/30329591/4417769
        mapping_list.remove(row)