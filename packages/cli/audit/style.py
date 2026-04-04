"""
style.py — shared terminal styling for NSU Audit Engine
Automatically uses Unicode box-drawing + ANSI color when the terminal
supports it, and falls back to plain ASCII otherwise.
"""
import re
import sys

# ── Force UTF-8 output on Windows ─────────────────────────────────────────────
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Detect capabilities ────────────────────────────────────────────────────────
_TTY  = sys.stdout.isatty()
_ENC  = (getattr(sys.stdout, 'encoding', '') or '').lower().replace('-', '')
_UTF8 = _ENC in ('utf8', 'utf8bom', 'utf16', 'utf16le', 'utf16be') or _ENC.startswith('utf')

# ── ANSI colors (blank when not a TTY) ───────────────────────────────────────
def _a(code): return code if _TTY else ''
GR = _a('\033[92m')   # green
RD = _a('\033[91m')   # red
YL = _a('\033[93m')   # yellow
CY = _a('\033[96m')   # cyan
BL = _a('\033[1m')    # bold
DM = _a('\033[2m')    # dim
RS = _a('\033[0m')    # reset

# ── Box-drawing characters ─────────────────────────────────────────────────────
if _UTF8:
    H   = '─';  V   = '│'
    TL  = '┌';  TR  = '┐';  BL2 = '└';  BR  = '┘'
    ML  = '├';  MR  = '┤';  MC  = '┼';  TM  = '┬';  BM  = '┴'
    DH  = '═';  DV  = '║'
    DTL = '╔';  DTR = '╗';  DBL = '╚';  DBR = '╝'
    DML = '╠';  DMR = '╣'
    CHK  = '✓';  XMK = '✗';  WRN = '⚠';  BULL = '•'
    ARW  = '↩';  SLP = '⊘'
else:
    H   = '-';  V   = '|'
    TL  = '+';  TR  = '+';  BL2 = '+';  BR  = '+'
    ML  = '+';  MR  = '+';  MC  = '+';  TM  = '+';  BM  = '+'
    DH  = '=';  DV  = '|'
    DTL = '+';  DTR = '+';  DBL = '+';  DBR = '+'
    DML = '+';  DMR = '+'
    CHK  = '+';  XMK = 'x';  WRN = '!';  BULL = '-'
    ARW  = '<';  SLP = 'o'

def hline_single(w, left=TL, mid=H, right=TR):
    return f'{left}{mid * w}{right}'

def hline_double(w, left=DTL, mid=DH, right=DTR):
    return f'{left}{mid * w}{right}'

def banner(title, subtitle=None, w=64):
    lines = [hline_double(w, DTL, DH, DTR)]
    lines.append(f'{DV}  {BL}{CY}{title}{RS}{" " * max(0, w - len(title) - 2)}{DV}')
    if subtitle:
        lines.append(f'{DV}  {DM}{subtitle}{RS}{" " * max(0, w - len(subtitle) - 2)}{DV}')
    lines.append(hline_double(w, DML, DH, DMR))
    return '\n'.join(lines)

_ANSI_RE = re.compile(r'\033\[[0-9;]*m')

def visible_len(s):
    return len(_ANSI_RE.sub('', s))

def pad_row(content, w, left='', right=''):
    vl = visible_len(content)
    return f'{left}{content}{" " * max(0, w - vl)}{right}'
