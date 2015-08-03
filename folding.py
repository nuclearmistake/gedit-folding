# -*- coding: utf-8 -*-
from gi.repository import GObject, Gedit, Gio

actions = [
    ("fold", "<Alt>Z", "Fold/Unfold"),
    ("fold_deepest", "<Alt>X", "Fold Deepest"),
    ("unfold_all", "<Shift><Alt>X", "Un-Fold All")
]


class FoldingPyPluginAppActivatable(GObject.Object, Gedit.AppActivatable):

    app = GObject.property(type=Gedit.App)

    def do_activate(self):
        self.menu_ext = self.extend_menu("tools-section")
        for action_name, key, menu_name in actions:
            fullname = "win." + action_name
            self.app.add_accelerator(key, fullname, None)
            item = Gio.MenuItem.new(_(menu_name), fullname)
            self.menu_ext.append_menu_item(item)

    def do_deactivate(self):
        for action_name, key, menu_name in actions:
            self.app.remove_accelerator("win." + action_name, None)
        self.menu_ext = None


class FoldingPyPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = 'FoldingPyPlugin'
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.do_update_state()
        for action_name, key, menu_name in actions:
            action = Gio.SimpleAction(name=action_name)
            action.connect('activate', getattr(self, action_name))
            self.window.add_action(action)

    def do_update_state(self):
        self.doc = self.window.get_active_document()
        if self.doc:
            self.view = self.window.get_active_view()
            table = self.doc.get_tag_table()
            self.fld = table.lookup('fld')
            if self.fld is None:
                self.fld = self.doc.create_tag(
                    'fld',
                    foreground="#333333",
                    paragraph_background="#aadc5c"
                )
            self.inv = table.lookup('inv')
            if self.inv is None:
                self.inv = self.doc.create_tag('inv', invisible=True)

    def detect_sps(self, sps):
        sps_lstrip = sps.lstrip()
        i = sps.index(sps_lstrip)
        sps = sps[:i]
        return sps.count(' ') + sps.count('\t') * self.view.get_tab_width()

    def fold_deepest(self, action, data=None):
        deepest = 0
        lines = list()
        s = self.doc.get_iter_at_line(0)
        e = s.copy()
        sg = 0
        eg = 0
        while s.forward_visible_line():
            if s.get_char() == "\n":
                continue
            e.set_line(s.get_line())
            e.forward_to_line_end()
            text = s.get_text(e)
            if not text.strip():
                continue
            indent = self.detect_sps(text)
            if not indent:
                continue
            if indent > deepest:
                deepest = indent
                lines = list()
                sg = s.get_line()
                eg = s.get_line()
            elif indent < deepest and eg:
                lines.append((sg-1, eg))
                eg = 0
            elif indent == deepest:
                if not eg:
                    sg = s.get_line()
                eg = s.get_line()
        if eg:
            lines.append((sg-1, eg))
        for (sg, eg) in lines:
            s.set_line(sg)
            e.set_line(eg)
            self.fold(None, s, e)

    def unfold_all(self, action, data=None):
        s, e = self.doc.get_bounds()
        self.doc.remove_tag(self.fld, s, e)
        self.doc.remove_tag(self.inv, s, e)

    def fold(self, action, a=None, c=None):
        if a is None:
            a = self.doc.get_iter_at_mark(self.doc.get_insert())
        if a.has_tag(self.fld):
            try:
                a.set_line_offset(0)
                b = a.copy()
                b.forward_line()
                self.doc.remove_tag(self.fld, a, b)
                a.forward_to_tag_toggle(self.inv)
                b.forward_to_tag_toggle(self.inv)
                self.doc.remove_tag(self.inv, a, b)
            except:
                pass
        elif (
            a is not None
            and c is not None  # and is stronger than or
            or len(self.doc.get_selection_bounds()) == 2
        ):
            if c is None:
                a, c = self.doc.get_selection_bounds()
            if a.get_line() == c.get_line():
                return
            b = a.copy()
            a.set_line_offset(0)
            b.forward_line()
            c.forward_line()
            self.doc.apply_tag(self.fld, a, b)
            # TODO: Don't remove already folded tags
            # and keep track of nested tags
            self.doc.remove_tag(self.fld, b, c)
            self.doc.remove_tag(self.inv, b, c)
            self.doc.apply_tag(self.inv, b, c)
        else:
            a.set_line_offset(0)
            line = a.get_line()
            sfold = a.copy()
            sfold.forward_line()
            text = a.get_text(sfold)
            if text.strip():
                main_indent = self.detect_sps(text)
                fin = a.copy()
                e = a.copy()
                while 1 == 1:
                    if not e.forward_line():
                        fin.forward_to_end()
                        line = fin.get_line()
                        break
                    if e.get_char() == "\n":
                        continue
                    ne = e.copy()
                    ne.forward_to_line_end()
                    text = e.get_text(ne)
                    if text.strip() == "":
                        continue
                    child_indent = self.detect_sps(text)
                    if child_indent <= main_indent:
                        break
                    line = e.get_line()
                    fin.set_line(line)
                    fin.forward_line()

                if a.get_line() < line:
                    self.doc.apply_tag(self.fld, a, sfold)
                    # TODO: Don't remove already folded tags and
                    # keep track of nested tags
                    self.doc.remove_tag(self.fld, sfold, fin)
                    self.doc.remove_tag(self.inv, sfold, fin)
                    self.doc.apply_tag(self.inv, sfold, fin)

