Code Folding for Gedit
========================

A simple plugin that adds keyboard-based code folding to Gedit.

Installation
--------------

####Unix/Linux
* Simplest: Move `folding.plugin` and `folding.py` into `~/.local/share/gedit/plugins`
* More convenient:
```
cd ~/.local/share/gedit/plugins
git clone https://github.com/frank-hanner/gedit-folding
```
You can replace frank-hanner by other developer - pick active one: https://github.com/aeischeid/gedit-folding/network

Then

* In Gedit, go to Edit &rarr; Preferences &rarr; Plugins to enable the plugin.

####Windows

**Note**: As stated in IRC conversation at #gedit public channel, gedit3 is not ready for Windows (yet). Eventually this installation section will be updated when gedit3 supports Windows.

Usage
--------

* `Alt-Z` on an indented block's top line (or within the block) will collapse that block
* `Alt-Z` on a folded block will expand it
* `Shift-Alt-Z` will expand all collapsed blocks
* `Alt-X` will collapse all blocks within/deeper than the current one
* `Shift-Alt-X` will collapse everything
* `Ctrl-Alt-X` will collapse all blocks on the deepest indention column (you can keep pressing Alt-X until all indention levels are folded)
