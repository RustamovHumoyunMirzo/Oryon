from standard_lib import StdModule
import ctypes
import sys

_IS_WINDOWS = sys.platform.startswith("win")

def _dlopen(path, flags):
    if _IS_WINDOWS:
        return ctypes.WinDLL(path)
    return ctypes.CDLL(path, flags)

class CType:
    void    = None
    bool    = ctypes.c_bool
    char    = ctypes.c_char
    uchar   = ctypes.c_ubyte
    short   = ctypes.c_short
    ushort  = ctypes.c_ushort
    int     = ctypes.c_int
    uint    = ctypes.c_uint
    long    = ctypes.c_long
    ulong   = ctypes.c_ulong
    float   = ctypes.c_float
    double  = ctypes.c_double

    char_p  = ctypes.c_char_p
    void_p  = ctypes.c_void_p

    def ptr(self, ctype):
        return ctypes.POINTER(ctype)

    def array(self, ctype, size):
        return ctype * size

    def sizeof(self, ctype):
        return ctypes.sizeof(ctype)

class Memory:
    def alloc(self, size):
        return ctypes.create_string_buffer(size)

    def sizeof(self, ctype):
        return ctypes.sizeof(ctype)

    def address(self, value):
        return ctypes.addressof(value)
    
class Struct:
    def define(self, name, *fields):
        return type(
            name,
            (ctypes.Structure,),
            {"_fields_": fields}
        )

class CFunction:
    def __init__(self, fn):
        self._fn = fn

    def argtypes(self, *types):
        self._fn.argtypes = types
        return self

    def restype(self, type_):
        self._fn.restype = type_
        return self

    def variadic(self):
        self._fn.argtypes = None
        return self

    def __call__(self, *args):
        return self._fn(*args)

    def __repr__(self):
        return f"cfunc '{hex(id(self))}'"
    
class Callback:
    def __init__(self, restype, *argtypes):
        self._ctype = ctypes.CFUNCTYPE(restype, *argtypes)

    def wrap(self, fn):
        return self._ctype(fn)

class Library:
    def __init__(self, path, flags):
        self._lib = _dlopen(path, flags)

    def __getattr__(self, name):
        return CFunction(getattr(self._lib, name))

    def __repr__(self):
        return f"clib '{hex(id(self))}'"

class FFI:
    CType = CType()
    Memory = Memory()
    Struct = Struct()
    Callback = Callback

    RTLD_LOCAL  = getattr(ctypes, "RTLD_LOCAL", 0)
    RTLD_GLOBAL = getattr(ctypes, "RTLD_GLOBAL", 0)

    @staticmethod
    def load(path, flags=0):
        return Library(path, flags)
    
    def __repr__(self):
        return f"class '{hex(id(self))}'"

@StdModule.register("ffi")
def std_ffi(interp):
    env = interp.env.new_child_env()
    
    env.define("C", FFI())

    return env