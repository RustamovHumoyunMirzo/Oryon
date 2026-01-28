from standard_lib import StdModule
import os
import sys
import signal
import time
import subprocess
import tempfile
import platform

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

def getenv(key, default=None):
    return os.environ.get(key, default)

def setenv(key, value):
    os.environ[key] = value

def unsetenv(key):
    if key in os.environ:
        del os.environ[key]

def listenv():
    return dict(os.environ)

def exit(code=0):
    sys.exit(code)

def getargs():
    return sys.argv[1:]

def getpid():
    return os.getpid()

def getppid():
    return os.getppid()

def getuid():
    return os.getuid() if hasattr(os, 'getuid') else None

def getgid():
    return os.getgid() if hasattr(os, 'getgid') else None

def geteuid():
    return os.geteuid() if hasattr(os, 'geteuid') else None

def getegid():
    return os.getegid() if hasattr(os, 'getegid') else None

def umask(mask=None):
    if mask is None:
        current = os.umask(0)
        os.umask(current)
        return current
    return os.umask(mask)

def chdir(path):
    os.chdir(path)

def getcwd():
    return os.getcwd()

def gethostname():
    import socket
    return socket.gethostname()

def sysname():
    return os.uname().sysname if hasattr(os, 'uname') else sys.platform

def release():
    return os.uname().release if hasattr(os, 'uname') else ''

def version():
    return os.uname().version if hasattr(os, 'uname') else ''

def machine():
    return os.uname().machine if hasattr(os, 'uname') else ''

def pagesize():
    return os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096

def loadavg():
    return os.getloadavg() if hasattr(os, 'getloadavg') else None

def uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            return float(f.readline().split()[0])
    except:
        return None

def memusage():
    if HAS_RESOURCE:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            'maxrss': usage.ru_maxrss,
            'usertime': usage.ru_utime,
            'systemtime': usage.ru_stime,
            'pagefaults': usage.ru_majflt,
            'swaps': usage.ru_nswap
        }
    return None

def cpuusage():
    if HAS_RESOURCE:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            'user': usage.ru_utime,
            'system': usage.ru_stime
        }
    return None

def limits():
    if HAS_RESOURCE:
        return {
            'cpu': resource.getrlimit(resource.RLIMIT_CPU),
            'filesize': resource.getrlimit(resource.RLIMIT_FSIZE),
            'data': resource.getrlimit(resource.RLIMIT_DATA),
            'stack': resource.getrlimit(resource.RLIMIT_STACK),
            'core': resource.getrlimit(resource.RLIMIT_CORE),
            'nofile': resource.getrlimit(resource.RLIMIT_NOFILE),
            'memlock': resource.getrlimit(resource.RLIMIT_MEMLOCK) if hasattr(resource, 'RLIMIT_MEMLOCK') else None,
            'processes': resource.getrlimit(resource.RLIMIT_NPROC) if hasattr(resource, 'RLIMIT_NPROC') else None
        }
    return None

def setlimit(resource_type, soft, hard=None):
    if not HAS_RESOURCE:
        return False
    
    res_map = {
        'cpu': resource.RLIMIT_CPU,
        'filesize': resource.RLIMIT_FSIZE,
        'data': resource.RLIMIT_DATA,
        'stack': resource.RLIMIT_STACK,
        'core': resource.RLIMIT_CORE,
        'nofile': resource.RLIMIT_NOFILE
    }
    
    if resource_type in res_map:
        hard = hard if hard is not None else soft
        resource.setrlimit(res_map[resource_type], (soft, hard))
        return True
    return False

def pipe():
    r, w = os.pipe()
    return {'read': r, 'write': w}

def fork():
    if hasattr(os, 'fork'):
        return os.fork()
    raise OSError("fork not supported on this platform")

def wait():
    if hasattr(os, 'wait'):
        return os.wait()
    raise OSError("wait not supported on this platform")

def waitpid(pid, options=0):
    if hasattr(os, 'waitpid'):
        return os.waitpid(pid, options)
    raise OSError("waitpid not supported on this platform")

def execv(path, args):
    os.execv(path, args)

def execve(path, args, env):
    os.execve(path, args, env)

def spawn(command, args=None, shell=False):
    if args is None:
        args = []
    if shell:
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        proc = subprocess.Popen([command] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.pid

def tmpdir():
    return tempfile.gettempdir()

def tmpfile(mode='w+b', suffix='', prefix='tmp', dir=None):
    return tempfile.NamedTemporaryFile(mode=mode, suffix=suffix, prefix=prefix, dir=dir, delete=False)

class Stdin:
    @staticmethod
    def read(n=-1):
        return sys.stdin.read(n)
    
    @staticmethod
    def readline():
        return sys.stdin.readline()
    
    @staticmethod
    def readlines():
        return sys.stdin.readlines()
    
    @staticmethod
    def isatty():
        return sys.stdin.isatty()

class Stdout:
    @staticmethod
    def write(s):
        sys.stdout.write(str(s))
        sys.stdout.flush()
    
    @staticmethod
    def writeln(s=""):
        sys.stdout.write(str(s) + "\n")
        sys.stdout.flush()
    
    @staticmethod
    def flush():
        sys.stdout.flush()
    
    @staticmethod
    def isatty():
        return sys.stdout.isatty()

class Stderr:
    @staticmethod
    def write(s):
        sys.stderr.write(str(s))
        sys.stderr.flush()
    
    @staticmethod
    def writeln(s=""):
        sys.stderr.write(str(s) + "\n")
        sys.stderr.flush()
    
    @staticmethod
    def flush():
        sys.stderr.flush()
    
    @staticmethod
    def isatty():
        return sys.stderr.isatty()

def signalhandler(sig, handler):
    signal.signal(sig, handler)

def sendsignal(pid, sig):
    os.kill(pid, sig)

def alarm(seconds):
    if hasattr(signal, 'alarm'):
        signal.alarm(seconds)
    else:
        raise OSError("alarm not supported on this platform")

def monotonic():
    return time.monotonic()

def perfcounter():
    return time.perf_counter()

def cpucount():
    return os.cpu_count()

def getplatform():
    return sys.platform

def username():
    import getpass
    return getpass.getuser()

def sleep(seconds):
    time.sleep(seconds)

def sleepms(milliseconds):
    time.sleep(milliseconds / 1000.0)

def sleepus(microseconds):
    time.sleep(microseconds / 1000000.0)

@StdModule.register("system")
def std_sys(interp):
    env = interp.env.new_child_env()

    env.define("getenv", getenv)
    env.define("setenv", setenv)
    env.define("unsetenv", unsetenv)
    env.define("listenv", listenv)
    env.define("exit", exit)
    env.define("getargs", getargs)
    env.define("getpid", getpid)
    env.define("getppid", getppid)
    if hasattr(os, 'getuid'):
        env.define("getuid", getuid)
    if hasattr(os, 'getgid'):
        env.define("getgid", getgid)
    if hasattr(os, 'geteuid'):
        env.define("geteuid", geteuid)
    if hasattr(os, 'getegid'):
        env.define("getegid", getegid)
    if hasattr(os, 'fork'):
        env.define("fork", fork)
    if hasattr(os, 'wait'):
        env.define("wait", wait)
        env.define("waitpid", waitpid)
    env.define("execv", execv)
    env.define("execve", execve)
    env.define("spawn", spawn)
    env.define("pipe", pipe)
    env.define("umask", umask)
    env.define("chdir", chdir)
    env.define("getcwd", getcwd)
    env.define("tmpdir", tmpdir)
    env.define("tmpfile", tmpfile)
    env.define("stdin", Stdin)
    env.define("stdout", Stdout)
    env.define("stderr", Stderr)
    env.define("signalhandler", signalhandler)
    env.define("sendsignal", sendsignal)
    if hasattr(signal, 'alarm'):
        env.define("alarm", alarm)
    if hasattr(signal, 'SIGTERM'):
        env.define("sigterm", signal.SIGTERM)
    if hasattr(signal, 'SIGINT'):
        env.define("sigint", signal.SIGINT)
    if hasattr(signal, 'SIGKILL'):
        env.define("sigkill", signal.SIGKILL)
    if hasattr(signal, 'SIGHUP'):
        env.define("sighup", signal.SIGHUP)
    if hasattr(signal, 'SIGALRM'):
        env.define("sigalrm", signal.SIGALRM)
    if hasattr(signal, 'SIGCHLD'):
        env.define("sigchld", signal.SIGCHLD)
    if hasattr(signal, 'SIGPIPE'):
        env.define("sigpipe", signal.SIGPIPE)
    if hasattr(signal, 'SIGUSR1'):
        env.define("sigusr1", signal.SIGUSR1)
    if hasattr(signal, 'SIGUSR2'):
        env.define("sigusr2", signal.SIGUSR2)
    if hasattr(signal, 'SIGABRT'):
        env.define("sigabrt", signal.SIGABRT)
    if hasattr(signal, 'SIGBREAK'):
        env.define("sigbreak", signal.SIGBREAK)
    env.define("monotonic", monotonic)
    env.define("perfcounter", perfcounter)
    env.define("sleep", sleep)
    env.define("sleepms", sleepms)
    env.define("sleepus", sleepus)
    env.define("cpucount", cpucount)
    env.define("platform", getplatform)
    env.define("username", username)
    env.define("gethostname", gethostname)
    env.define("sysname", sysname)
    env.define("release", release)
    env.define("version", version)
    env.define("machine", machine)
    env.define("pagesize", pagesize)
    if hasattr(os, 'getloadavg'):
        env.define("loadavg", loadavg)
    env.define("uptime", uptime)
    env.define("arch", platform.architecture())
    if HAS_RESOURCE:
        env.define("memusage", memusage)
        env.define("cpuusage", cpuusage)
        env.define("limits", limits)
        env.define("setlimit", setlimit)

    return env