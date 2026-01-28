from standard_lib import StdModule
from pathlib import Path

def write_file(
    filename,
    data,
    encoding="utf-8",
    newline=None,
    buffering=-1,
    errors="strict"
):

    with open(
        filename,
        mode="w",
        encoding=encoding,
        errors=errors,
        newline=newline,
        buffering=buffering
    ) as file:
        if isinstance(data, list):
            file.writelines(data)
        else:
            file.write(data)

def read_file(
    path,
    encoding="utf-8",
    newline=None,
    buffering=-1,
    errors="strict",
):

    path = Path(path)

    with path.open(
        mode="r",
        encoding=encoding,
        errors=errors,
        newline=newline,
        buffering=buffering
    ) as file:
        return file.read()

@StdModule.register("file")
def std_fs(interp):
    env = interp.env.new_child_env()

    env.define("write", write_file)
    env.define("read", read_file)

    return env