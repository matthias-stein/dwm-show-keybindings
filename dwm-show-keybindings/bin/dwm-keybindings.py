#!/usr/bin/python3

import re

from collections import namedtuple
from configparser import ConfigParser, DuplicateSectionError
from dataclasses import dataclass, field
from math import ceil, floor
from pathlib import Path
from textwrap import fill
from tkinter import *
from tkinter.ttk import *
from pathlib import Path
from typing import Any, ClassVar, List

# Path to config file. Change here if your's lives someplace else.
CONF_PATH = Path().home() / '.config' / 'dwm' / 'dwm-keybindings'


@dataclass
class Fail:
    """Holds all error messages encountered.

    Provides classmethod to create a Label widget for each error.
    """
    fail: ClassVar[List] = []

    @classmethod
    def make(this, fram: Frame) -> list:
        rtrn = []
        for item in this.fail:
            rtrn.append(
                Label(
                    fram,
                    padding=5,
                    compound='top',
                    anchor='center',
                    text=f'[ERROR] {item}',
                    style='F.TLabel'
                )
            )
        return rtrn


@dataclass
class Conf:
    """This class reads the .ini file, and provides its content."""
    conf: ClassVar[Any] = field(init=False)

    wndw_clmn: int
    wndw_wghk: int
    wndw_wghd: int
    head_back: str
    head_fore: str
    body_back: str
    body_fore: str
    body_sect: str
    body_chrd: str
    dywm_logo: str
    dywm_srce: str

    @classmethod
    def read(this):
        """Returns conf from class variable ``conf``.

        ``conf`` initially is None, if it is requested and still None,
        the classmethod ``make()`` is called to poplate it with data.
        """
        try:
            return this.conf
        except AttributeError:
            this.make()
            return this.conf

    @classmethod
    def make(this) -> None:
        """Tries to make the content of the class variable ``conf``.

        The method tries to read the specified .ini file, and the
        relevant sections from it. It provides fallback values in
        case a section or key is missing to not break the program.
        """
        conf = ConfigParser()
        path = CONF_PATH / 'dwm-keybindings.ini'
        try:
            conf.read_file(open(path))
        except DuplicateSectionError as fail:
            Fail.fail.append(f'Duplicate Section Error\n{fail}')
            # provide empty sections to allow instanciation to
            # succeed
            conf['DWM'] = {}
            conf['STYLE'] = {}
            conf['WINDOW'] = {}
        this.conf = this(
            conf.getint('WINDOW', 'ColumnCount', fallback=2),
            conf.getint('WINDOW', 'KeyChordWidthWeight', fallback=2),
            conf.getint('WINDOW', 'DescriptionWidthWeight', fallback=5),
            conf.get('STYLE', 'BgHead', fallback='#bbbbbb'),
            conf.get('STYLE', 'FgHead', fallback='#005577'),
            conf.get('STYLE', 'BgBody', fallback='#eeeeee'),
            conf.get('STYLE', 'FgBody', fallback='#222222'),
            conf.get('STYLE', 'FgTitle', fallback='#005577'),
            conf.get('STYLE', 'FgKeyChords', fallback='#444444'),
            conf.get('STYLE', 'logo', fallback='dwm.png'),
            conf.get('DWM', 'conf', fallback=None)
        )


class Cfgh:
    """Handle config.h file."""

    def __init__(self) -> None:
        self.deck = ''  # will hold the content of onfig.h
        self.srce = None  # path to config file
        self.full = 0  # total number of lines
        self.keym = {}  # keybindings
        self.rgex = r"""
            # regex searching for keybing definitions including the
            # custom tags in comment
            \{\s*                 # {
            ([A-Za-z0\|]+)        # GROUP-1 :: MODKEY|ShiftMask etc or 0
            \s*,\s*               # ,
            ([A-Za-z0-9_]+)       # GROUP-2 :: XK_Return
            \s*,\s*               # ,
            ([A-Za-z_0-9]+)       # GROUP-3 :: spawn
            \s*,\s*               # ,
            \{\s*.+\s*\}          # {.v = termcmd }
            \s*/\*                # /*
            <g>([\w\-,\.:]+)</g>  # GROUP-4 :: <g>Spawner</g>
            \s*                   # /*
            <d>(.+)</d>           # GROUP-5 :: <d>Spawns a terminal.</d>
            \s*\*/                # */
            \s*\}\s*              # }
        """

    def find_conf(self) -> None:
        """Read .ini content for config.h path and find it in filesystem."""
        conf = Conf.read()  # get content of .ini file
        path = conf.dywm_srce  # path to config.h
        if path is None:
            Fail.fail.append(
                'ERROR - [DWM] > [conf] entry missing in .ini file.'
            )   
            return
        path = Path(path)
        if path.is_absolute():
            # if path is absolute, use it
            self.srce = path
            return
        else:
            # if path is relative, apply from home directory
            self.srce = Path().home() / path
            return

    def read_conf(self) -> None:
        """Read the file content of config.h."""
        if isinstance(self.srce, Path):
            try:
                assert self.srce.is_file()
            except AssertionError:
                Fail.fail.append(f'File not found: {self.srce}')
                return
            with open(self.srce, 'r') as hndl:
                self.deck = hndl.read()

    def prse_conf(self) -> None:
        """Apply regular expression to content of config.h."""
        for mtch in re.findall(self.rgex, self.deck, re.VERBOSE):
            cnf1 = mtch[0]
            dsp1 = cnf1.replace('MODKEY', 'Mod')
            dsp1 = dsp1.replace('|', '-')
            dsp1 = dsp1.replace('Mask', '')
            if dsp1 == '0':
                dsp1 = False

            cnf2 = mtch[1]
            dsp2 = cnf2.replace('XK_', '')

            cnf3 = mtch[2]

            if dsp1 is False:
                dkey = f'<{dsp2}>'
            else:
                dkey = f'<{dsp1}-{dsp2}>'

            gnam = mtch[3]  # group name
            desc = mtch[4]  # description

            if gnam not in self.keym:
                self.keym[gnam] = {}
                self.full += 1
            self.keym[gnam][dkey] = desc
            self.full += 1


class Wndw(Tk):
    """Handle the GUI window."""

    def make_look(self) -> None:
        """Define the widget styles."""
        conf = Conf.read()
        look = Style()
        look.configure(
            # left / right column
            'C.TFrame',
            background=conf.body_back,
            foreground=conf.body_fore,
        )
        look.configure(
            # header
            'L.TLabel',
            font=('Ubuntu Mono', 16, 'bold'),
            background=conf.head_back,
            foreground=conf.head_fore,
            wraplength=self.wdth,
            padding=(0, 0, 0, 10)
        )
        look.configure(
            # section name
            'H.TLabel',
            font=('Ubuntu Mono', 16, 'bold'),
            background=conf.body_back,
            foreground=conf.body_sect,
            wraplength=self.cwdh,
            padding=(0, 15, 0, 10)
        )
        look.configure(
            # key chord
            'K.TLabel',
            font=('Ubuntu Mono', 11, 'bold'),
            padding=3,
            background=conf.body_back,
            foreground=conf.body_chrd,
            anchor='e',
            wraplength=self.cwdk,
        )
        look.configure(
            # description
            'D.TLabel',
            font=('Ubuntu Mono', 11),
            padding=3,
            background=conf.body_back,
            foreground=conf.body_fore,
            anchor='w',
            wraplength=self.cwdd,
        )
        look.configure(
            # fail messages
            'F.TLabel',
            font=('Ubuntu Mono', 11),
            padding=3,
            background=conf.body_back,
            foreground=conf.body_fore,
            anchor='w',
            wraplength=self.wdth,
        )

    def make_dims(self, full: int) -> None:
        """Calculate dimensions based on screen size and .ini parameters."""
        conf = Conf.read()
        self.clen = floor(full / conf.wndw_clmn)  # number of rows per column
        self.wdth = ceil(self.winfo_screenwidth() * 0.8)
        self.dpth = ceil(self.winfo_screenheight() * 0.8)
        self.offx = ceil((self.winfo_screenwidth() - self.wdth) * 0.5)
        self.offy = ceil((self.winfo_screenheight() - self.dpth) * 0.5)
        self.cwgk = conf.wndw_wghk  # col weight key chord
        self.cwgd = conf.wndw_wghd  # col weight description
        wdth_wght = floor(  # width per weight
            self.wdth / (
                self.cwgk * conf.wndw_clmn +
                self.cwgd * conf.wndw_clmn
            )
        )  
        self.cwdk = self.cwgk * wdth_wght  # col width key chord
        self.cwdd = self.cwgd * wdth_wght  # col width description
        self.cwdh = self.cwdk + self.cwdd  # col width header

    def make_imgs(self) -> None:
        """Create tkinter image objects."""
        conf = Conf.read()
        path = CONF_PATH / 'logo' / conf.dywm_logo 
        self.logo = PhotoImage(file=path)

    def conf_wndw(self) -> None:
        """Initiate the main window."""
        conf = Conf.read()
        self.title('dwm keybindings')
        self.wm_title('dwm keybindings')
        self.iconphoto(False, self.logo)
        self.configure(bg=conf.body_back)
        self.geometry(f'{self.wdth}x{self.dpth}')
        self.geometry(f'+{self.offx}+{self.offy}')
        for coln in range(0, conf.wndw_clmn, 1):
            self.columnconfigure(coln, weight=1)

    def make_head(self, srce: Path) -> None:
        """Create header section of the GUI window.

        This displays the dwm logo, path to the config.h and any errors.
        """
        conf = Conf.read()
        grdy = -1

        fram = Frame(self, width=self.wdth, style='C.TFrame')
        fram.columnconfigure(0, weight=1)
        fram.grid(
            column=0,
            row=0,
            sticky=N+S+E+W,
            columnspan=conf.wndw_clmn
        )

        grdy += 1
        Label(
            fram,
            image=self.logo,
            padding=5,
            anchor='center',
            text=f'Current keybindings in {srce}.',
            compound='top',
            style='L.TLabel'
        ).grid(
            column=0,
            row=grdy,
            sticky=E+W
        )

        fail = Fail.make(fram)
        for item in fail:
            grdy += 1
            item.grid(
                column=0,
                row=grdy,
                sticky=N+W
            )
            

    def make_frms(self) -> None:
        """Create one frame per column specified in .ini."""
        conf = Conf.read()
        self.fram = [1, ]  # list[0] = index of active column
        for coln in range(0, conf.wndw_clmn, 1):
            fram = Frame(self, width=self.cwdh, style='C.TFrame')
            fram.columnconfigure(0, weight=self.cwgk)
            fram.columnconfigure(1, weight=self.cwgd)
            fram.grid(column=coln, row=1, sticky=N)
            self.fram.append(fram)

    def make_keym(self, cfgh: dict) -> None:
        """Output the keymap and distribuite over number of columns."""
        grdy = -1
        for sect in sorted(list(cfgh.keys())):
            grdy += 1
            keys = len(cfgh[sect].keys())
            grdy = self.test_cols(grdy, keys)
            fkey = self.fram[0]
            fram = self.fram[fkey]

            Label(
                fram, text=sect, style='H.TLabel'
            ).grid(
                column=0, row=grdy, columnspan=2
            )

            for card in sorted(list(cfgh[sect].keys())):
                grdy += 1

                Label(
                    fram, text=card, style='K.TLabel'
                ).grid(
                    column=0, row=grdy, sticky=N+E
                )

                Label(
                    fram, text=cfgh[sect][card], style='D.TLabel'
                ).grid(
                    column=1, row=grdy, sticky=N+W
                )

    def test_cols(self, grdy: int, keys: int) -> int:
        """Test if column switch is reached.

        A section is never broken into two columns,
        """
        if grdy > self.clen:
            grdy = 0
            self.fram[0] += 1
        elif (self.clen - grdy) < floor(keys / 2):
            grdy = 0
            self.fram[0] += 1
        return grdy


def ctrl() -> None:
    """Control program flow."""
    cfgh = Cfgh()
    cfgh.find_conf()
    cfgh.read_conf()
    cfgh.prse_conf()
    
    wndw = Wndw()
    wndw.make_dims(cfgh.full)
    wndw.make_look()
    wndw.make_imgs()
    wndw.conf_wndw()
    wndw.make_head(cfgh.srce)
    wndw.make_frms()
    wndw.make_keym(cfgh.keym)
    wndw.mainloop()
    

if __name__ == '__main__':
    ctrl()
