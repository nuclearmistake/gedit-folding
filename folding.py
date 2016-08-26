# -*- coding: utf-8 -*-
from gi.repository import GObject, Gedit, Gio

actions = [
          ("fold", "<Alt>Z", "Fold/Unfold"),
          ("unfold_all", "<Shift><Alt>Z", "Un-Fold All"),
          ("fold_deepest", "<Control><Alt>X", "Fold Deepest"),
          ("fold_below", "<Alt>X", "Fold Below"),
          ("fold_all", "<Shift><Alt>X", "Fold All")
          ]

# the "folded" is the one line that remains visible
FOLDED = 'fld'
# the rest of the indent block is hidden (invisible)
HIDDEN = 'inv'


def getTagName( t ):
    return str(t.get_property('name'))

def isFoldTag( t ):
    return getTagName(t) == FOLDED

def getFoldTag( textIter ):
    '''
    get the shallowest fold tag.
    tags are ordered with most prominent (which should be the most recently added) at the end
    '''
    tags = textIter.get_tags()

    for tag in reversed(tags):
        if isFoldTag(tag):
            return tag

    return None

def getLineText( start ):
    start.set_line_offset(0)

    if start.ends_line():
        return ''

    end = start.copy()
    end.forward_to_line_end()
    text = start.get_text(end)

    return text


class FoldingPyPluginAppActivatable( GObject.Object, Gedit.AppActivatable ):

    app = GObject.property(type=Gedit.App)

    def __init__(self):
        self.menu_ext = None
        GObject.Object.__init__(self)

    def do_activate( self ):
        if hasattr(self, "extend_menu"):
            self.menu_ext = self.extend_menu("tools-section")
            for action_name, key, menu_name in actions:
                fullname = "win." + action_name
                self.app.add_accelerator(key, fullname, None)
                item = Gio.MenuItem.new(_(menu_name), fullname)
                self.menu_ext.append_menu_item(item)
        else:
            for action_name, key, menu_name in actions:
                fullname = "win." + action_name
                self.app.add_accelerator(key, fullname, None)

    def do_deactivate( self ):
        if self.menu_ext != None:
            for action_name, key, menu_name in actions:
                self.app.remove_accelerator("win." + action_name, None)
            self.menu_ext = None


class FoldingPyPlugin( GObject.Object, Gedit.WindowActivatable ):
    __gtype_name__ = 'FoldingPyPlugin'
    window = GObject.property(type=Gedit.Window)

    def __init__( self ):
        GObject.Object.__init__(self)

    def do_activate( self ):
        self.do_update_state()
        for action_name, key, menu_name in actions:
            action = Gio.SimpleAction(name=action_name)
            action.connect('activate', getattr(self, action_name))
            self.window.add_action(action)

    def do_update_state( self ):
        self.doc = self.window.get_active_document()
        if self.doc:
            self.view = self.window.get_active_view()
            self.tab_width = self.view.get_tab_width()
            self.tag_table = self.doc.get_tag_table()

            self.folded = self.tag_table.lookup(FOLDED) or self.makeFoldTag()
            self.hidden = self.tag_table.lookup(HIDDEN) or  self.makeHiddenTag()

    def getAllTags( self ):
        tags = []
        self.tag_table.foreach(tags.append)
        return tags

    def makeFoldTag( self ):
        tag = self.doc.create_tag(FOLDED, foreground="#333333", paragraph_background="#E0B9ED")
        return tag

    def makeHiddenTag( self ):
        tag = self.doc.create_tag(HIDDEN, invisible=True)
        return tag

    def count_whitespace( self, line ):
        stripped = line.lstrip()
        whitespace = line[:len(line)-len(stripped)]
        return whitespace.count(' ') + whitespace.count('\t') * self.tab_width

    def getLineIndent( self, start, backward=False ):
        text = getLineText(start)
        while not text.strip():
            prev_line = start.get_line()
            if backward:
                if not start.backward_visible_line():
                    break
            elif not start.forward_visible_line():
                break

            text = getLineText(start)

        return self.count_whitespace(text)

    def doFold( self, start, end, setFoldTag=True ):
        '''
        apply the folding (highlight the first line) and hiding (hide all the folded stuff) tags
        '''
        # get the front of the line
        start.set_line_offset(0)
        next = start.copy()
        next.forward_to_line_end()
        end.forward_line()

        # remove any previous hidden tags because they cause problems with not hiding everything correctly when nested
        self.doc.remove_tag(self.hidden, start, end)

        if setFoldTag:
            self.doc.apply_tag(self.folded, start, next)
        self.doc.apply_tag(self.hidden, next, end)

        return True

    def doUnfold( self, start, tag ):
        '''
        unfold tag at start
        '''
        start.set_line_offset(0)
        end = start.copy()
        end.forward_line()
        self.doc.remove_tag(tag, start, end)

        # move start & end forward to the bounds of the hidden tag
        start.forward_to_tag_toggle(self.hidden)
        end.forward_to_tag_toggle(self.hidden)
        self.doc.remove_tag(self.hidden, start, end)

        # there may be nested folds, so search through and refold as necessary.
        # actually nesting the hidden tags is problematic, so they need to be reapplied
        end_line = end.get_line()

        while start.get_line() <= end_line:
            folded = getFoldTag(start)
            if folded:
                # because we found the tag indicating that this was previously folded, we know
                # it is the true start, and we also know we will find an end
                end = self.findIndentBlockEnd(start)
                if end is not None:
                    self.doFold(start, end, setFoldTag=False)

            if not start.forward_visible_line():
                break

    def fold( self, action=None, start=None, end=None, foldFunction=None ):
        '''
        fold or unfold a selection.
        start & end are gtk.TextIter to specify range to fold/unfold
        action is the calling gtk widget, unused.
        '''
        if foldFunction is None:
            foldFunction = self.doFold

        if start is None:
            # if no start position specified, use the current cursor position
            start = self.doc.get_iter_at_mark(self.doc.get_insert())
            cursor_line = start.get_line()
        else:
            cursor_line = None

        # if we already are tagged, that means this block is folded, so unfold it
        start.set_line_offset(0)
        tag = getFoldTag(start)
        if tag:
            self.doUnfold(start, tag)
            return

        '''
        # i don't think folding an artibrary selection is that useful, and it doesn't nest, so let's not do it.
        if ((start and end) or len(selBounds) == 2):
            # if this is called with specific start and end or there is a selection

            # if no end provided, use the selection
            if end is None:
                start, end = selBounds

            # if the start and end are different, then fold the selection
            # if this is not the case (selection is on one line), then treat it
            # as a normal fold attempt
            if start.get_line() < end.get_line():
                self.doFold(start, end)
                return False
        '''

        # attempt to fold.
        # if the line after the current line is indented more, then the current line is the fold
        # start.
        # but if the next line is not indented more, then assume we're in the block we want to
        # fold, so look up until we find the undent to start from.

        start_line = start.get_line()
        # getLineIndent will search forward until we hit a line with something on it
        main_indent = self.getLineIndent(start)
        # get the next line to compare indents
        if not start.forward_line():
            # if we couldn't go forward, then set indents the same so we check backward
            next_indent = main_indent
        else:
            next_indent = self.getLineIndent(start)

        start.set_line(start_line)
        if next_indent == main_indent == 0:
            # print("Nothing to fold here!")
            return False

        elif next_indent <= main_indent:
            # look backward until we find the start of this block
            undent = self.getLineIndent(start, backward=True)
            while undent >= main_indent:
                if not start.backward_line():
                    break
                undent = self.getLineIndent(start, backward=True)

            if undent < main_indent:
                main_indent = undent
                start_line = start.get_line()
            else:
                # print("Couldn't find something to fold!")
                return False

        # else:
            # this was the start of a fold, so we're good to go
            # pass

        end = self.findIndentBlockEnd(start, main_indent)
        if end is None:
            return False

        # make sure we've found different lines
        if start_line < end.get_line():
            # move the cursor first because foldFunction may move start
            if cursor_line is not None and start_line < cursor_line:
                self.doc.place_cursor(start)

            return foldFunction(start=start, end=end)
        else:
            # print("Couldn't find something to fold!")
            pass

        return False

    def findIndentBlockEnd( self, start, main_indent=None ):
        # search forward until the indent returns to, or is shallower than, main_indent
        # this will be the block that we want to hide.
        if main_indent is None:
            main_indent = self.getLineIndent(start)

        end = start.copy()
        if not end.forward_line():
            # print("Can't fold last line")
            return None

        end_line = None
        next_indent = self.getLineIndent(end)
        while next_indent > main_indent:
            end_line = end.get_line()
            if not end.forward_line():
                break
            next_indent = self.getLineIndent(end)

        if end_line is None:
            return None

        # getLineIndent leaves the iter at the end of the line,
        # so if we've found the undent, set end position to the end of the previous line
        if next_indent <= main_indent:
            end.set_line(end_line)

        return end

    def fold_below( self, action=None, data=None ):
        while self.fold(foldFunction=self.fold_deepest):
            pass

    def fold_all( self, action=None, data=None ):
        while self.fold_deepest():
            pass

    def fold_deepest( self, action=None, data=None, reverse=True, start=None, end=None ):
        # keep track of all indent blocks
        # as we scan the doc, each time we step back out of a block, record it's depth
        # so we can sort them and then fold the deepest level
        blocks = []
        block_stack = []
        if start is None:
            start = self.doc.get_iter_at_line(0)
        indent = self.getLineIndent(start)
        last_line = start.get_line()

        if end is None:
            end_line = self.doc.get_line_count()
        else:
            end_line = end.get_line()

        while last_line <= end_line and start.forward_visible_line():
            this_indent = self.getLineIndent(start)
            this_line = start.get_line()

            if this_indent > indent:
                # update block start
                block_stack.append((last_line, indent))

            elif this_indent < indent and block_stack:
                block_start, block_indent = block_stack.pop()

                while block_stack and block_indent > this_indent:
                    if last_line - block_start > 1:
                        blocks.append((block_indent, block_start, last_line))
                    block_start, block_indent = block_stack.pop()

                if block_indent > this_indent:
                    # print('  Found undent without previous indent!?')
                    pass
                else:
                    if last_line - block_start > 1:
                        blocks.append((block_indent, block_start, last_line))

            indent = this_indent
            last_line = this_line

        # close any remaining blocks
        while block_stack:
            block_start, block_indent = block_stack.pop()
            if last_line - block_start > 1:
                blocks.append((block_indent, block_start, last_line))

        if not blocks:
            # print('Nothing to fold!')
            return False

        blocks = sorted(blocks, reverse=reverse)
        deepest_blocks = [ b for b in blocks if b[0] == blocks[0][0] ]

        end = start.copy()

        for each in deepest_blocks:
            start.set_line(each[1])
            end.set_line(each[2])
            self.doFold(start=start, end=end)

        return True

    def unfold_all( self, action=None, data=None ):
        start, end = self.doc.get_bounds()
        self.doc.remove_tag(self.folded, start, end)
        self.doc.remove_tag(self.hidden, start, end)

