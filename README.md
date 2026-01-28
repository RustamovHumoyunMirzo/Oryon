# Oryon
Oryon is a modern programming language with **Dual-Mode Execution**, enabling the same source code to run either through a fast AST-walking interpreter or a native compiler—all from a single, unified toolchain.

This design allows rapid prototyping and debugging in interpreter mode, while still offering high-performance native binaries when compiled.

## Requirements
All dependencies must be installed in the same Python environment.
- Python 3.9.x
- pyinstaller
- llvmlite

## Build Instructions
First, compile the native extensions.
Make sure the generated output is placed inside `src/native`.
```bash
python setup.py build_ext --inplace
```

Once native extensions are built, package the language using **PyInstaller**:
```bash
pyinstaller --clean config.spec
```
The final executable will be generated in the `dist/` directory.

## Notes
- Interpreter and compiler share the same frontend and semantics.
- No source code changes are required to switch between execution modes.

**🚧 The language is not yet stable**
