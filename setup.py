from distutils.core import setup
from distutils.extension import Extension
from distutils import sysconfig

sysconfig.get_config_vars()['CC'] = 'gcc'

setup(
    ext_modules=[
        Extension("native_loop", ["native/native_loop.c"]),
        Extension("native_env", ["native/native_env.c"])
    ]
)
