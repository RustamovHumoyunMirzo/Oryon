from standard_lib import StdModule
import re
import json

def upper(s):
    return s.upper()

def lower(s):
    return s.lower()

def capitalize(s):
    return s.capitalize()

def title(s):
    return s.title()

def strip(s, chars=None):
    return s.strip(chars)

def lstrip(s, chars=None):
    return s.lstrip(chars)

def rstrip(s, chars=None):
    return s.rstrip(chars)

def split(s, sep=None, maxsplit=-1):
    return s.split(sep, maxsplit)

def join(sep, iterable):
    return sep.join(str(x) for x in iterable)

def replace(s, old, new, count=-1):
    return s.replace(old, new, count)

def startswith(s, prefix, start=0, end=None):
    if end is None:
        return s.startswith(prefix, start)
    return s.startswith(prefix, start, end)

def endswith(s, suffix, start=0, end=None):
    if end is None:
        return s.endswith(suffix, start)
    return s.endswith(suffix, start, end)

def find(s, sub, start=0, end=None):
    if end is None:
        return s.find(sub, start)
    return s.find(sub, start, end)

def rfind(s, sub, start=0, end=None):
    if end is None:
        return s.rfind(sub, start)
    return s.rfind(sub, start, end)

def index(s, sub, start=0, end=None):
    if end is None:
        return s.index(sub, start)
    return s.index(sub, start, end)

def rindex(s, sub, start=0, end=None):
    if end is None:
        return s.rindex(sub, start)
    return s.rindex(sub, start, end)

def count(s, sub, start=0, end=None):
    if end is None:
        return s.count(sub, start)
    return s.count(sub, start, end)

def isalpha(s):
    return s.isalpha()

def isdigit(s):
    return s.isdigit()

def isalnum(s):
    return s.isalnum()

def isspace(s):
    return s.isspace()

def isupper(s):
    return s.isupper()

def islower(s):
    return s.islower()

def istitle(s):
    return s.istitle()

def reverse(s):
    return s[::-1]

def substr(s, start, length=None):
    if length is None:
        return s[start:]
    return s[start:start+length]

def pad_left(s, width, fillchar=' '):
    return s.rjust(width, fillchar)

def pad_right(s, width, fillchar=' '):
    return s.ljust(width, fillchar)

def pad_center(s, width, fillchar=' '):
    return s.center(width, fillchar)

def repeat(s, n):
    return s * n

def contains(s, sub):
    return sub in s

def char_at(s, index):
    if 0 <= index < len(s):
        return s[index]
    raise IndexError("string index out of range")

def concat(*args):
    return ''.join(str(x) for x in args)

def lines(s):
    return s.splitlines()

def words(s):
    return s.split()

def chars(s):
    return list(s)

def trim(s):
    return s.strip()

def trim_left(s):
    return s.lstrip()

def trim_right(s):
    return s.rstrip()

def swapcase(s):
    return s.swapcase()

def zfill(s, width):
    return s.zfill(width)

def expandtabs(s, tabsize=8):
    return s.expandtabs(tabsize)

def slice(s, start, end=None):
    if end is None:
        return s[start:]
    return s[start:end]

def insert(s, index, sub):
    return s[:index] + sub + s[index:]

def remove(s, sub):
    return s.replace(sub, '', 1)

def remove_all(s, sub):
    return s.replace(sub, '')

def match(s, pattern):
    return re.match(pattern, s) is not None

def search(s, pattern):
    return re.search(pattern, s) is not None

def findall(s, pattern):
    return re.findall(pattern, s)

def regex_replace(s, pattern, repl):
    return re.sub(pattern, repl, s)

def isempty(s):
    return len(s) == 0

def isblank(s):
    return len(s.strip()) == 0

def compare(s1, s2):
    if s1 < s2:
        return -1
    elif s1 > s2:
        return 1
    return 0

def compare_ignore_case(s1, s2):
    return compare(s1.lower(), s2.lower())

def equals(s1, s2):
    return s1 == s2

def equals_ignore_case(s1, s2):
    return s1.lower() == s2.lower()

def ord_at(s, index):
    return ord(s[index])

def from_char_code(code):
    return chr(code)

class FormatError(Exception):
    pass

class Formatter:
    def __init__(self):
        self.registry = {}
        self._register_defaults()

    def _register(self, spec, fn):
        self.registry[spec] = fn

    def _register_defaults(self):
        self._register('d', self._int)
        self._register('l', self._long)
        self._register('f', self._float)
        self._register('lf', self._double)
        self._register('e', self._scientific)
        self._register('s', self._string)
        self._register('b', self._bool)
        self._register('x', self._hex)
        self._register('o', self._oct)
        self._register('B', self._bin)
        self._register('m', self._map)
        self._register('a', self._list)
        self._register('t', self._tuple)

    def _int(self, v, p): self._req(v, int, '%d'); return str(v)
    def _long(self, v, p): self._req(v, int, '%l'); return str(v)

    def _float(self, v, p):
        self._req(v, (int, float), '%f')
        prec = p.precision if p.precision is not None else 6
        return self._num(float(v), prec)

    def _double(self, v, p): return self._float(v, p)

    def _scientific(self, v, p):
        self._req(v, (int, float), '%e')
        prec = p.precision if p.precision is not None else 6
        return f"{float(v):.{prec}e}"

    def _string(self, v, p):
        self._req(v, str, '%s')
        return v[:p.precision] if p.precision is not None else v

    def _bool(self, v, p):
        self._req(v, bool, '%b')
        return "true" if v else "false"

    def _hex(self, v, p):
        self._req(v, int, '%x')
        return ('0x' if p.alt else '') + hex(v)[2:]

    def _oct(self, v, p):
        self._req(v, int, '%o')
        return ('0o' if p.alt else '') + oct(v)[2:]

    def _bin(self, v, p):
        self._req(v, int, '%B')
        return ('0b' if p.alt else '') + bin(v)[2:]

    def _map(self, v, p):
        self._req(v, dict, '%m')
        return json.dumps(v)

    def _list(self, v, p):
        self._req(v, list, '%a')
        return json.dumps(v)

    def _tuple(self, v, p):
        self._req(v, tuple, '%t')
        return json.dumps(v)

    def _req(self, v, t, name):
        if not isinstance(v, t):
            raise TypeError(f"{name} expects {t}")

    def _num(self, v, prec):
        s = f"{v:.{prec}f}"
        return s

class Spec:
    def __init__(self):
        self.left = False
        self.zero = False
        self.plus = False
        self.space = False
        self.alt = False
        self.width = None
        self.precision = None
        self.name = None
        self.spec = None

def format_string(fmt, *args, **kwargs):
    out = []
    i = 0
    argi = 0
    F = Formatter()

    while i < len(fmt):
        if fmt[i] != '%':
            out.append(fmt[i])
            i += 1
            continue

        if fmt[i+1] == '%':
            out.append('%')
            i += 2
            continue

        i += 1
        p = Spec()

        if fmt[i] == '(':
            i += 1
            start = i
            while fmt[i] != ')': i += 1
            p.name = fmt[start:i]
            i += 1

        while fmt[i] in '-0+ #':
            setattr(p, {
                '-':'left','0':'zero','+':'plus',
                ' ':'space','#':'alt'
            }[fmt[i]], True)
            i += 1

        if fmt[i].isdigit():
            s = i
            while fmt[i].isdigit(): i += 1
            p.width = int(fmt[s:i])

        if fmt[i] == '.':
            i += 1
            s = i
            while fmt[i].isdigit(): i += 1
            p.precision = int(fmt[s:i])

        if fmt[i:i+2] == 'lf':
            p.spec = 'lf'
            i += 2
        else:
            p.spec = fmt[i]
            i += 1

        if p.spec not in F.registry:
            raise FormatError(f"Unknown spec %{p.spec}")

        val = kwargs[p.name] if p.name else args[argi]
        if not p.name: argi += 1

        txt = F.registry[p.spec](val, p)

        if txt[0] not in '-0123456789' and isinstance(val, (int,float)):
            if p.plus: txt = '+' + txt
            elif p.space: txt = ' ' + txt

        if p.width:
            pad = '0' if p.zero and not p.left else ' '
            txt = txt.ljust(p.width, pad) if p.left else txt.rjust(p.width, pad)

        out.append(txt)

    return ''.join(out)

@StdModule.register("string")
def std_string(interp):
    env = interp.env.new_child_env()

    env.define("toupper", upper)
    env.define("tolower", lower)
    env.define("capital", capitalize)
    env.define("totitle", title)
    env.define("swapcase", swapcase)
    env.define("trim", trim)
    env.define("trimleft", trim_left)
    env.define("trimright", trim_right)
    env.define("split", split)
    env.define("join", join)
    env.define("lines", lines)
    env.define("words", words)
    env.define("chars", chars)
    env.define("replace", replace)
    env.define("find", find)
    env.define("findlast", rfind)
    env.define("index", index)
    env.define("indexlast", rindex)
    env.define("count", count)
    env.define("contains", contains)
    env.define("startswith", startswith)
    env.define("endswith", endswith)
    env.define("isalpha", isalpha)
    env.define("isdigit", isdigit)
    env.define("isalnum", isalnum)
    env.define("isspace", isspace)
    env.define("isupper", isupper)
    env.define("islower", islower)
    env.define("istitle", istitle)
    env.define("empty", isempty)
    env.define("blank", isblank)
    env.define("reverse", reverse)
    env.define("slice", slice)
    env.define("charat", char_at)
    env.define("concat", concat)
    env.define("repeat", repeat)
    env.define("insert", insert)
    env.define("remove", remove)
    env.define("removeall", remove_all)
    env.define("padleft", pad_left)
    env.define("padright", pad_right)
    env.define("padcenter", pad_center)
    env.define("zfill", zfill)
    env.define("expandtabs", expandtabs)
    env.define("fstr", format_string)
    env.define("compare", compare)
    env.define("compareic", compare_ignore_case)
    env.define("equals", equals)
    env.define("equalsic", equals_ignore_case)
    env.define("match", match)
    env.define("search", search)
    env.define("findall", findall)
    env.define("regexreplace", regex_replace)
    env.define("charcode", ord_at)
    env.define("charfrom", from_char_code)

    return env