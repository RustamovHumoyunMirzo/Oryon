import sys
import gc
import weakref
import tracemalloc
from standard_lib import StdModule
import os
import platform
import ctypes

@StdModule.register("memory")
def std_memory(interp):
    env = interp.env.new_child_env()

    def id_fn(obj):
        return id(obj)

    def sizeof_fn(obj):
        return sys.getsizeof(obj)

    def ref_count_fn(obj):
        return sys.getrefcount(obj) - 1

    def type_fn(obj):
        return type(obj)

    def repr_fn(obj):
        return repr(obj)

    def is_alive_fn(ref):
        try:
            return ref() is not None
        except Exception:
            return False

    def gc_collect_fn():
        return gc.collect()

    def gc_enable_fn():
        gc.enable()
        return True

    def gc_disable_fn():
        gc.disable()
        return True

    def gc_is_enabled_fn():
        return gc.isenabled()

    def gc_stats_fn():
        return {
            "counts": gc.get_count(),
            "thresholds": gc.get_threshold(),
            "garbage": len(gc.garbage),
        }

    def gc_objects_fn():
        return len(gc.get_objects())

    def weakref_fn(obj):
        return weakref.ref(obj)

    def memtrack_start_fn(n_frames=10):
        tracemalloc.start(n_frames)
        return True

    def memtrack_stop_fn():
        tracemalloc.stop()
        return True

    def memtrack_current_fn():
        current, peak = tracemalloc.get_traced_memory()
        return {
            "current": current,
            "peak": peak,
        }

    class NullPointerType:
        __slots__ = ()

        def __repr__(self):
            return "nullptr"

        def __str__(self):
            return "nullptr"

        def __bool__(self) -> bool:
            return False

        def __eq__(self, other):
            return isinstance(other, NullPointerType)

    NULLPTR = NullPointerType()

    env.define("id", id_fn)
    env.define("sizeof", sizeof_fn)
    env.define("refcount", ref_count_fn)
    env.define("type", type_fn)
    env.define("repr", repr_fn)

    env.define("gccollect", gc_collect_fn)
    env.define("gcenable", gc_enable_fn)
    env.define("gcdisable", gc_disable_fn)
    env.define("gcenabled", gc_is_enabled_fn)
    env.define("gcstats", gc_stats_fn)
    env.define("gcobjects", gc_objects_fn)

    env.define("weakref", weakref_fn)
    env.define("isalive", is_alive_fn)

    env.define("memtrack_start", memtrack_start_fn)
    env.define("memtrack_stop", memtrack_stop_fn)
    env.define("memtrack", memtrack_current_fn)

    env.define("NullPointer", NULLPTR)

    def process_memory_usage_fn():
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except Exception:
            pass

        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if platform.system() == "Darwin":
                return usage
            return usage * 1024
        except Exception:
            return 0

    def system_memory_total_fn():
        try:
            import psutil
            return psutil.virtual_memory().total
        except Exception:
            pass

        if hasattr(os, "sysconf"):
            try:
                pages = os.sysconf("SC_PHYS_PAGES")
                page_size = os.sysconf("SC_PAGE_SIZE")
                return pages * page_size
            except Exception:
                pass

        return 0

    def system_memory_free_fn():
        try:
            import psutil
            return psutil.virtual_memory().available
        except Exception:
            pass

        if os.path.exists("/proc/meminfo"):
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemAvailable:"):
                            return int(line.split()[1]) * 1024
            except Exception:
                pass

        return 0

    def process_memory_percent_fn():
        total = system_memory_total_fn()
        if total <= 0:
            return 0.0
        return (process_memory_usage_fn() / total) * 100.0

    env.define("usage", process_memory_usage_fn)
    env.define("free", system_memory_free_fn)
    env.define("total", system_memory_total_fn)
    env.define("percent", process_memory_percent_fn)

    class MemInfo(ctypes.Structure):
        _fields_ = [
            ("total_memory", ctypes.c_uint64),
            ("free_memory", ctypes.c_uint64),
            ("available_memory", ctypes.c_uint64),
            ("process_rss", ctypes.c_uint64),
            ("process_virtual", ctypes.c_uint64),
            ("process_percent", ctypes.c_double),
        ]
        def __repr__(self):
            return f"object '{hex(id(self))}'"

    lib = ctypes.CDLL("./src/libs/meminfo.dll")
    lib.get_meminfo.argtypes = [ctypes.POINTER(MemInfo)]
    lib.get_meminfo.restype = ctypes.c_int

    info = MemInfo()
    lib.get_meminfo(ctypes.byref(info))

    env.define("info", info)

    return env