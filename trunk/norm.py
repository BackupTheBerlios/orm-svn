#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -*- python -*-
#
#  File: norm.py
#  $Rev$
#  $Author$
#  $Date$
#
#*****************************************************************************
#
#  Copyright (c) 2006 Benjamin Sergeant (bsergean at gmail dot com)
#
#  progress bar code stolen from yum:
#  http://linux.duke.edu/projects/yum/
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License version 2, as
#  published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
#*****************************************************************************

#*****************************************************************************
# plug orm to a cplay-based curses interface
#*****************************************************************************

__version__ = "norm 0.0"

from types import *

import curses
import string
import tty
import sys
import re
import os
import time
import select
import signal

# ------------------------------------------
try: import locale; locale.setlocale(locale.LC_ALL, "")
except: pass

# ------------------------------------------
_locale_domain = "cplay"
_locale_dir = "/usr/local/share/locale"

try:
    import gettext  # python 2.0
    gettext.install(_locale_domain, _locale_dir)
except ImportError:
    try:
        import fintl
        fintl.bindtextdomain(_locale_domain, _locale_dir)
        fintl.textdomain(_locale_domain)
        _ = fintl.gettext
    except ImportError:
        def _(s): return s
except:
    def _(s): return s

# ------------------------------------------
XTERM = re.search("rxvt|xterm", os.environ["TERM"])

# ------------------------------------------
out = '/tmp/orm.log'
outfd = open(out, 'w')
def log(msg):
    outfd.write(msg + '\n')
    outfd.flush()

# ------------------------------------------
class Stack:
    def __init__(self):
        self.items = ()

    def push(self, item):
        self.items = (item,) + self.items

    def pop(self):
        self.items, item = self.items[1:], self.items[0]
        return item

# ------------------------------------------
class KeymapStack(Stack):
    def process(self, code):
        for keymap in self.items:
            if keymap and keymap.process(code):
                break

# ------------------------------------------
class Keymap:
    def __init__(self):
        self.methods = [None] * curses.KEY_MAX

    def bind(self, key, method, args=None):
        if type(key) in (TupleType, ListType):
            for i in key: self.bind(i, method, args)
            return
        if type(key) is StringType:
            key = ord(key)
        self.methods[key] = (method, args)

    def process(self, key):
        if self.methods[key] is None: return 0
        method, args = self.methods[key]
        if args is None:
            apply(method, (key,))
        else:
            apply(method, args)
        return 1

# ------------------------------------------
def cut(s, n, left=0):
    if left: return len(s) > n and "<%s" % s[-n+1:] or s
    else: return len(s) > n and "%s>" % s[:n-1] or s

# ------------------------------------------
class Timeout:
    def __init__(self):
        self.next = 0
        self.dict = {}

    def add(self, timeout, func, args=()):
        tid = self.next = self.next + 1
        self.dict[tid] = (func, args, time.time() + timeout)
        return tid

    def remove(self, tid):
        del self.dict[tid]

    def check(self, now):
        for tid, (func, args, timeout) in self.dict.items():
            if now >= timeout:
                self.remove(tid)
                apply(func, args)
        return len(self.dict) and 0.2 or None

class Window:
    chars = string.letters+string.digits+string.punctuation+string.whitespace

    t = ['?'] * 256
    for c in chars: t[ord(c)] = c
    translationTable = string.join(t, ""); del t

    def __init__(self, parent):
        self.parent = parent
        self.children = []
        self.name = None
        self.keymap = None
        self.visible = 1
        self.resize()
        if parent: parent.children.append(self)

    def insstr(self, s):
        if not s: return
        self.w.addstr(s[:-1])
        self.w.hline(ord(s[-1]), 1)  # insch() work-around

    def __getattr__(self, name):
        return getattr(self.w, name)

    def getmaxyx(self):
        y, x = self.w.getmaxyx()
        try: curses.version  # tested with 1.2 and 1.6
        except AttributeError:
            # pyncurses - emulate traditional (silly) behavior
            y, x = y+1, x+1
        return y, x

    def touchwin(self):
        try: self.w.touchwin()
        except AttributeError: self.touchln(0, self.getmaxyx()[0])

    def attron(self, attr):
        try: self.w.attron(attr)
        except AttributeError: self.w.attr_on(attr)

    def attroff(self, attr):
        try: self.w.attroff(attr)
        except AttributeError: self.w.attr_off(attr)

    def newwin(self):
        return curses.newwin(0, 0, 0, 0)

    def resize(self):
        self.w = self.newwin()
        self.ypos, self.xpos = self.getbegyx()
        self.rows, self.cols = self.getmaxyx()
        self.keypad(1)
        self.leaveok(0)
        self.scrollok(0)
        for child in self.children:
            child.resize()

    def update(self):
        self.clear()
        self.refresh()
        for child in self.children:
            child.update()

# ------------------------------------------
class ProgressWindow(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        self.value = 0

    def newwin(self):
        return curses.newwin(1, self.parent.cols, self.parent.rows-2, 0)

    def update(self):
        self.move(0, 0)
        self.hline(ord('-'), self.cols)
        if self.value > 0:
            self.move(0, 0)
            x = int(self.value * self.cols)  # 0 to cols-1
            x and self.hline(ord('='), x)
            self.move(0, x)
            self.insstr('|')
        self.touchwin()
        self.refresh()

    def progress(self, value):
        self.value = min(value, 0.99)
        self.update()

# ------------------------------------------
class StatusWindow(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        self.default_message = ''
        self.current_message = ''
        self.tid = None

    def newwin(self):
        return curses.newwin(1, self.parent.cols-12, self.parent.rows-1, 0)

    def update(self):
        msg = string.translate(self.current_message, Window.translationTable)
        self.move(0, 0)
        self.clrtoeol()
        self.insstr(cut(msg, self.cols))
        self.touchwin()
        self.refresh()

    def status(self, message, duration = 0):
        self.current_message = str(message)
        if self.tid: app.timeout.remove(self.tid)
        if duration: self.tid = app.timeout.add(duration, self.timeout)
        else: self.tid = None
        self.update()

    def timeout(self):
        self.tid = None
        self.restore_default_status()

    def set_default_status(self, message):
        if self.current_message == self.default_message: self.status(message)
        self.default_message = message
        XTERM and sys.stderr.write("\033]0;%s\a" % (message or "cplay"))

    def restore_default_status(self):
        self.status(self.default_message)

# ------------------------------------------
class ListWindow(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        self.buffer = []
        self.bufptr = self.scrptr = 0
        self.search_direction = 0
        self.last_search = ""
        self.hoffset = 0
        self.keymap = Keymap()
        self.keymap.bind(['k', curses.KEY_UP, 16], self.cursor_move, (-1,))
        self.keymap.bind(['j', curses.KEY_DOWN, 14], self.cursor_move, (1,))
        self.keymap.bind(['K', curses.KEY_PPAGE], self.cursor_ppage, ())
        self.keymap.bind(['J', curses.KEY_NPAGE], self.cursor_npage, ())
        self.keymap.bind(['g', curses.KEY_HOME], self.cursor_home, ())
        self.keymap.bind(['G', curses.KEY_END], self.cursor_end, ())
        self.keymap.bind(['>'], self.hscroll, (8,))
        self.keymap.bind(['<'], self.hscroll, (-8,))

    def newwin(self):
        return curses.newwin(self.parent.rows-2, self.parent.cols,
                             self.parent.ypos+2, self.parent.xpos)

    def update(self, force = 1):
        self.bufptr = max(0, min(self.bufptr, len(self.buffer) - 1))
        scrptr = (self.bufptr / self.rows) * self.rows
        if force or self.scrptr != scrptr:
            self.scrptr = scrptr
            self.move(0, 0)
            self.clrtobot()
            i = 0
            for entry in self.buffer[self.scrptr:]:
                self.move(i, 0)
                i = i + 1
                self.putstr(entry)
                if self.getyx()[0] == self.rows - 1: break
            if self.visible:
                self.refresh()
                self.parent.update_title()
        self.update_line(curses.A_REVERSE)

    def update_line(self, attr = None, refresh = 1):
        if not self.buffer: return
        ypos = self.bufptr - self.scrptr
        if attr: self.attron(attr)
        self.move(ypos, 0)
        self.hline(ord(' '), self.cols)
        self.putstr(self.current())
        if attr: self.attroff(attr)
        if self.visible and refresh: self.refresh()

    def get_title(self, data=""):
        pos = "%s-%s/%s" % (self.scrptr+min(1, len(self.buffer)),
                            min(self.scrptr+self.rows, len(self.buffer)),
                            len(self.buffer))
        width = self.cols-len(pos)-2
        data = cut(data, width-len(self.name), 1)
        return "%-*s  %s" % (width, cut(self.name+data, width), pos)

    def putstr(self, entry, *pos):
        s = string.translate(str(entry), Window.translationTable)
        pos and apply(self.move, pos)
        if self.hoffset: s = "<%s" % s[self.hoffset+1:]
        self.insstr(cut(s, self.cols))

    def current(self):
        if self.bufptr >= len(self.buffer): self.bufptr = len(self.buffer) - 1
        return self.buffer[self.bufptr]

    def cursor_move(self, ydiff):
        if app.input_mode: app.cancel_input()
        if not self.buffer: return
        self.update_line(refresh = 0)
        self.bufptr = (self.bufptr + ydiff) % len(self.buffer)
        self.update(force = 0)

    def cursor_ppage(self):
        tmp = self.bufptr % self.rows
        if tmp == self.bufptr:
            self.cursor_move(-(tmp+(len(self.buffer) % self.rows) or self.rows))
        else:
            self.cursor_move(-(tmp+self.rows))

    def cursor_npage(self):
        tmp = self.rows - self.bufptr % self.rows
        if self.bufptr + tmp > len(self.buffer):
            self.cursor_move(len(self.buffer) - self.bufptr)
        else:
            self.cursor_move(tmp)

    def cursor_home(self): self.cursor_move(-self.bufptr)

    def cursor_end(self): self.cursor_move(-self.bufptr - 1)

    def hscroll(self, value):
        self.hoffset = max(0, self.hoffset + value)
        self.update()

# ------------------------------------------
class DownloadListWindow(ListWindow):

    def __init__(self, parent):
        ListWindow.__init__(self, parent)
        self.keymap.bind('t', self.toto, ())
        self.keymap.bind('l', self.listPodCasts, ())
        self.keymap.bind(['\n', curses.KEY_ENTER],
                         self.toggleDownload, ())
        import orm
        self.settings = orm.settings()
        self.downloaders = []

        for f, url in self.settings.podcasts.iteritems():
            self.downloaders.append(orm.podcastHandler(self.settings.prefix,
                                                       f, url, verbose))
    # HERE
    def toggleDownload(self):

        self.buffer[self.bufptr] = "downloading ..."
        self.downloaders[self.bufptr].download()
        self.buffer[self.bufptr] = "downloaded !!"
        self.parent.update_title()
        self.update()

    def toto(): pass

    def get_title(self):
        self.name = _("DownloadListWindow: ")
        return self.name

    def listPodCasts(self):
        self.buffer = self.settings.podcasts.keys()
        self.bufptr = 0
        self.parent.update_title()
        self.update()

# ------------------------------------------
class HelpWindow(ListWindow):
    def __init__(self, parent):
        ListWindow.__init__(self, parent)
        self.name = _("Help")
        self.keymap.bind('q', self.parent.help, ())
        self.buffer = string.split(_("""\
  Global                               t, T  : tag current/regex
  ------                               u, U  : untag current/regex
  Up, Down, k, j, C-p, C-n,            Sp, i : invert current/all
  PgUp, PgDn, K, J,                    !     : shell ($@ = tagged or current)
  Home, End, g, G : movement
  Enter           : chdir or play      Filelist
  Tab             : filelist/playlist  --------
  n, p            : next/prev track    a     : add (tagged) to playlist
  z, x            : toggle pause/stop  s     : recursive search
                                       BS, o : goto parent/specified dir
  Left, Right,                         m, '  : set/get bookmark
  C-f, C-b    : seek forward/backward  
  C-a, C-e    : restart/end track      Playlist
  C-s, C-r, / : isearch                --------
  C-g, Esc    : cancel                 d, D  : delete (tagged) tracks/playlist
  1..9, +, -  : volume control         m, M  : move tagged tracks after/before
  c, v        : counter/volume mode    r, R  : toggle repeat/Random mode
  <, >        : horizontal scrolling   s, S  : shuffle/Sort playlist
  C-l, l      : refresh, list mode     w, @  : write playlist, jump to active
  h, q, Q     : help, quit?, Quit!     X     : stop playlist after each track
"""), "\n")

# ------------------------------------------
class TabWindow(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        self.active_child = 0

        self.win_podlist = self.add(DownloadListWindow)
        self.win_help    = self.add(HelpWindow)

        keymap = Keymap()
        keymap.bind('\t', self.change_window, ()) # tab
        keymap.bind('h', self.help, ())
        app.keymapstack.push(keymap)
        app.keymapstack.push(self.children[self.active_child].keymap)

    def newwin(self):
        return curses.newwin(self.parent.rows-2, self.parent.cols, 0, 0)

    def update(self):
        self.update_title()
        self.move(1, 0)
        self.hline(ord('-'), self.cols)
        self.move(2, 0)
        self.clrtobot()
        self.refresh()
        child = self.children[self.active_child]
        child.visible = 1
        child.update()

    def update_title(self, refresh = 1):
        child = self.children[self.active_child]
        self.move(0, 0)
        self.clrtoeol()
        self.attron(curses.A_BOLD)
        self.insstr(child.get_title())
        self.attroff(curses.A_BOLD)
        if refresh: self.refresh()

    def add(self, Class):
        win = Class(self)
        win.visible = 0
        return win

    def change_window(self, window = None):
        app.keymapstack.pop()
        self.children[self.active_child].visible = 0
        if window:
            self.active_child = self.children.index(window)
        else:
            # toggle windows 0 and 1
            self.active_child = not self.active_child
        app.keymapstack.push(self.children[self.active_child].keymap)
        self.update()

    def help(self):
        if self.children[self.active_child] == self.win_help:
            self.change_window(self.win_last)
        else:
            self.win_last = self.children[self.active_child]
            self.change_window(self.win_help)
            app.status(__version__, 2)

# ------------------------------------------
class RootWindow(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        keymap = Keymap()
        app.keymapstack.push(keymap)
        self.win_status = StatusWindow(self)
        self.win_progress = ProgressWindow(self)
        self.win_tab = TabWindow(self)

        keymap.bind('Q', app.quit, ())
        keymap.bind('q', self.command_quit, ())

    def command_quit(self):
        app.do_input_hook = self.do_quit
        app.start_input(_("Quit? (y/N)"))
        
    def do_quit(self, ch):
        if chr(ch) == 'y': app.quit()
        app.stop_input()



# ------------------------------------------
class Application:
    def __init__(self):
        self.keymapstack = KeymapStack()
        self.input_mode = 0
        self.input_mode = 0
        self.input_prompt = ""
        self.input_string = ""
        self.do_input_hook = None
        self.stop_input_hook = None
        self.complete_input_hook = None
        self.input_keymap = Keymap()
        
    def setup(self):
        if tty:
            self.tcattr = tty.tcgetattr(sys.stdin.fileno())
            tcattr = tty.tcgetattr(sys.stdin.fileno())
            tcattr[0] = tcattr[0] & ~(tty.IXON)
            tty.tcsetattr(sys.stdin.fileno(), tty.TCSANOW, tcattr)

        self.w = curses.initscr()
        curses.cbreak()
        curses.noecho()
        try: curses.meta(1)
        except: pass
        self.cursor(0)
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        signal.signal(signal.SIGHUP, self.handler_quit)
        signal.signal(signal.SIGINT, self.handler_quit)
        signal.signal(signal.SIGTERM, self.handler_quit)
        signal.signal(signal.SIGWINCH, self.handler_resize)
        
        self.win_root = RootWindow(None)
        self.win_root.update()

        self.win_status = self.win_root.win_status
        self.status = self.win_status.status
        self.win_podlist = self.win_root.win_tab.win_podlist

        self.timeout = Timeout()
        
    def cleanup(self):
        try: curses.endwin()
        except curses.error: return
        XTERM and sys.stderr.write("\033]0;%s\a" % "xterm")
        tty and tty.tcsetattr(sys.stdin.fileno(), tty.TCSADRAIN, self.tcattr)
        print

    def run(self):
        self.win_podlist.listPodCasts()                    
        while True:
            now = time.time()
            timeout = self.timeout.check(now)
            
            R = [sys.stdin]
            try: r, w, e = select.select(R, [], [], timeout)
            except select.error: continue
            
            # user
            if sys.stdin in r:
                c = self.win_root.getch()
                self.keymapstack.process(c)

    def show_input(self):
        n = len(self.input_prompt)+1
        s = cut(self.input_string, self.win_status.cols-n, left=1)
        app.status("%s%s " % (self.input_prompt, s))

    def start_input(self, prompt="", data="", colon=1):
        self.input_mode = 1
        self.cursor(1)
        app.keymapstack.push(self.input_keymap)
        self.input_prompt = prompt + (colon and ": " or "")
        self.input_string = data
        self.show_input()

    def do_input(self, *args):
        if self.do_input_hook:
            return apply(self.do_input_hook, args)
        ch = args and args[0] or None
        if ch in [8, 127]: # backspace
            self.input_string = self.input_string[:-1]
        elif ch == 9 and self.complete_input_hook:
            self.input_string = self.complete_input_hook(self.input_string)
        elif ch == 21: # C-u
            self.input_string = ""
        elif ch == 23: # C-w
            self.input_string = re.sub("((.* )?)\w.*", "\\1", self.input_string)
        elif ch:
            self.input_string = "%s%c" % (self.input_string, ch)
        self.show_input()

    def cursor(self, visibility):
        try: curses.curs_set(visibility)
        except: pass

    def quit(self):
        sys.exit(0)

    def handler_resize(self, sig, frame):
        # curses trickery
        while 1:
            try: curses.endwin(); break
            except: time.sleep(1)
        self.w.refresh()
        self.win_root.resize()
        self.win_root.update()

    def handler_quit(self, sig, frame):
        self.quit()

global app

if not sys.stdin.isatty():
    print 'not a tty .. which means ??'
    os.close(0)
    os.open("/dev/tty", 0)

try:
    app = Application()
    app.setup()
    app.run()
except SystemExit:
    app.cleanup() # fixme
except Exception:
    app.cleanup()
    import traceback
    traceback.print_exc()
else:
    app.cleanup()
