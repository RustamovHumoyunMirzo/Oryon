import sys
import os
import argparse
from oryon_interpreter import Interpreter
from ast_nodes import ThrowSignal
import time

try:
    from llvm_compiler import LLVMCompiler
    LLVM_AVAILABLE = True
except ImportError as e:
    LLVM_AVAILABLE = False

_VERSION = "0.1.0-beta-2"
_ALLOWED_EXTENSIONS = ['.or', '.oryon']
_LANG_NAME = "Oryon"
_COPYRIGHT_YEAR = "2025-2026"
_COPYRIGHT_HOLDER = "Rustamov Humoyun Mirzo"

try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    license_path = os.path.join(script_dir, 'misc', 'LICENSE.txt')
    with open(license_path, 'r', encoding='utf-8') as l:
        _LICENSE = l.read()
except FileNotFoundError:
    _LICENSE = "License file not found"

def print_banner():
    print(f"{_LANG_NAME}, version {_VERSION}")
    print(f"Copyright (c) {_COPYRIGHT_YEAR} {_COPYRIGHT_HOLDER}. All rights reserved.")
    if LLVM_AVAILABLE:
        print("LLVM compiler support: ENABLED")
    else:
        print("LLVM compiler support: DISABLED (install llvmlite to enable)")
    print()
    print("Use 'h' or 'help' for more information.")
    print("Enter the command or type 'quit' to exit:")

    while True:
        cmd = input(">> ").strip()
        if cmd.lower() == 'quit':
            break
        elif cmd in ('h', 'help'):
            print_help()
        elif cmd in ('v', 'version'):
            print(f"Oryon {_VERSION}")
        elif cmd == 'license':
            print(_LICENSE)
        elif cmd.startswith("run "):
            raw = cmd[4:].strip()

            if not raw:
                print("Usage: run <file.or | file.oryon>")
                continue
            
            if (raw.startswith('"') and raw.endswith('"')) or \
               (raw.startswith("'") and raw.endswith("'")):
                filename = raw[1:-1]
            else:
                filename = raw

            if not filename:
                print("Usage: run <file.or | file.oryon>")
                continue
            
            run_file_repl(filename, compile_mode=False)
        elif cmd.startswith("compile "):
            if not LLVM_AVAILABLE:
                print("Error: LLVM compiler not available. Install llvmlite: pip install llvmlite")
                continue
            
            raw = cmd[8:].strip()
            if not raw:
                print("Usage: compile <file.or | file.oryon>")
                continue
            
            if (raw.startswith('"') and raw.endswith('"')) or \
               (raw.startswith("'") and raw.endswith("'")):
                filename = raw[1:-1]
            else:
                filename = raw

            if not filename:
                print("Usage: compile <file.or | file.oryon>")
                continue
            
            run_file_repl(filename, compile_mode=True, opt_level=3)
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'quit' to exit or 'h' for help.")

def print_help():
    print(f"Oryon Programming Language, version {_VERSION}")
    print("Usage: oryon [OPTIONS] <file.or | file.oryon>")
    print()
    print("Options:")
    print("  -h, --help              → Show this help message and exit")
    print("  -v, --version           → Show version information and exit")
    print("  --license               → Show license information and exit")
    print()
    if LLVM_AVAILABLE:
        print("Compilation options:")
        print("  --compile               → Use LLVM compiler instead of interpreter")
        print("  --opt LEVEL             → Optimization level 0-3 (default: 3)")
        print("  --no-optimize           → Disable optimizations (same as --opt 0)")
        print("  -o, --output PATH       → Output directory for compiled files")
        print("  --ll                    → Generate LLVM IR (.ll) file")
        print("  --obj                   → Generate object (.o) file")
        print("  --asm                   → Generate assembly (.s) file")
        print("  --execute               → Execute after compilation (JIT)")
        print()
        print("Examples:")
        print("  oryon program.or                           → Run with interpreter")
        print("  oryon --compile program.or                 → Compile and execute")
        print("  oryon --compile --ll program.or            → Generate LLVM IR")
        print("  oryon --compile --obj -o build/ program.or → Compile to object file")
        print("  oryon --compile --opt 0 program.or         → Compile without optimization")
        print()
    print("REPL commands:")
    print("  run <file>              → Execute an Oryon source file")
    if LLVM_AVAILABLE:
        print("  compile <file>          → Compile and execute an Oryon source file")
    print("  license                 → Show license text")
    print("  quit                    → Exit REPL")

def print_perf(stats):
    print("\n=== Performance Report ===")
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"{k:<15}: {v:.6f} s")
        else:
            print(f"{k:<15}: {v}")
    print("==========================")

def run_file(filename, compile_mode=False, opt_level=3, output_dir=None, 
             gen_ll=False, gen_obj=False, gen_asm=False, execute=True, perf=False):
    
    if not os.path.isfile(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(3)

    file_extension = os.path.splitext(filename)[1].lower()

    if file_extension not in _ALLOWED_EXTENSIONS:
        print(f"Error: Unsupported file extension '{file_extension}'. "
              f"Supported extensions are: {', '.join(_ALLOWED_EXTENSIONS)}.")
        sys.exit(2)
    
    if compile_mode:
        if not LLVM_AVAILABLE:
            print("Error: LLVM compiler not available. Install llvmlite: pip install llvmlite")
            print("Falling back to interpreter mode...")
            compile_mode = False
        else:
            compile_file(filename, opt_level, output_dir, gen_ll, gen_obj, gen_asm, execute, perf)
            return
    
    try:
        start_wall = time.perf_counter()
        start_cpu = time.process_time()

        interpreter = Interpreter()
        interpreter.interpret_file(filename)

        end_wall = time.perf_counter()
        end_cpu = time.process_time()

        if perf:
            print_perf({
                "Mode": "Interpreter",
                "Execution time": end_wall - start_wall,
                "CPU time": end_cpu - start_cpu
            })
    except Exception as e:
        print(f"Runtime error: {e}")
        sys.exit(5)

def compile_file(filename, opt_level=3, output_dir=None, gen_ll=False, 
                gen_obj=False, gen_asm=False, execute=True, perf=False):
    
    try:
        total_start = time.perf_counter()
        cpu_start = time.process_time()

        compiler = LLVMCompiler()
        
        print(f"Compiling {filename}...")
        compile_start = time.perf_counter()
        compiler.compile_file(filename)
        compile_end = time.perf_counter()
        
        if output_dir is None:
            output_dir = os.path.dirname(filename) or '.'
        
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        base_name = os.path.splitext(os.path.basename(filename))[0]
        
        if gen_ll:
            ll_path = os.path.join(output_dir, f"{base_name}.ll")
            compiler.save_to_file(ll_path)
            print(f"✓ LLVM IR saved to: {ll_path}")
        
        if gen_obj:
            obj_path = os.path.join(output_dir, f"{base_name}.o")
            compiler.save_to_object(obj_path)
            print(f"✓ Object file saved to: {obj_path}")
        
        if gen_asm:
            asm_path = os.path.join(output_dir, f"{base_name}.s")
            try:
                compiler.save_to_assembly(asm_path, opt_level)
                print(f"✓ Assembly saved to: {asm_path}")
            except AttributeError:
                print("Warning: Assembly generation not implemented yet")
        
        if execute:

            print(f"\nExecuting with JIT (optimization level {opt_level})...")
            exec_start = time.perf_counter()
            result = compiler.execute(optimize=(opt_level > 0), opt_level=opt_level)
            exec_end = time.perf_counter()
            print(f"\nProgram exited with code: {result}")
        
        if not (gen_ll or gen_obj or gen_asm or execute):
            print(f"Executing with JIT (optimization level {opt_level})...")
            exec_start = time.perf_counter()
            result = compiler.execute(optimize=(opt_level > 0), opt_level=opt_level)
            exec_end = time.perf_counter()
            print(f"Program exited with code: {result}")
        
        total_end = time.perf_counter()
        cpu_end = time.process_time()
        
        if perf:
            print_perf({
                "Mode": "LLVM JIT",
                "Optimization": f"O{opt_level}",
                "Compile time": compile_end - compile_start,
                "Execution time": exec_end - exec_start,
                "Total time": total_end - total_start,
                "CPU time": cpu_end - cpu_start
            })
    except Exception as e:
        print(f"Compilation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(4)

def run_file_repl(filename, compile_mode=False, opt_level=3):
    if not os.path.isfile(filename):
        print(f"Error: File '{filename}' not found.")
        return

    file_extension = os.path.splitext(filename)[1].lower()

    if file_extension not in _ALLOWED_EXTENSIONS:
        print(f"Error: Unsupported file extension '{file_extension}'. "
              f"Supported extensions: {', '.join(_ALLOWED_EXTENSIONS)}.")
        return
    
    if compile_mode:
        if not LLVM_AVAILABLE:
            print("Error: LLVM compiler not available.")
            return
        
        try:
            compiler = LLVMCompiler()
            compiler.compile_file(filename)
            result = compiler.execute(optimize=(opt_level > 0), opt_level=opt_level)
            print(f"Program exited with code: {result}")
        except Exception as e:
            print(f"Compilation error: {e}")
    else:
        try:
            interpreter = Interpreter()
            interpreter.interpret_file(filename)
        except Exception as e:
            print(f"Runtime error: {e}")

def main():
    parser = argparse.ArgumentParser(
        description=f"{_LANG_NAME} Programming Language v{_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  oryon program.or                           # Run with interpreter
  oryon --compile program.or                 # Compile and execute
  oryon --compile --ll program.or            # Generate LLVM IR
  oryon --compile --obj -o build/ program.or # Compile to object file
  oryon --compile --opt 0 program.or         # Compile without optimization
        """
    )
    
    parser.add_argument('file', nargs='?', help='Oryon source file to run/compile')
    parser.add_argument('-v', '--version', action='store_true', 
                       help='Show version information')
    parser.add_argument('--license', action='store_true',
                       help='Show license information')
    parser.add_argument('--perf', action='store_true',
                    help='Show performance statistics after execution')
    
    if LLVM_AVAILABLE:
        parser.add_argument('--compile', action='store_true',
                           help='Use LLVM compiler instead of interpreter')
        parser.add_argument('--opt', type=int, default=3, choices=[0, 1, 2, 3],
                           help='Optimization level (0-3, default: 3)')
        parser.add_argument('--no-optimize', action='store_true',
                           help='Disable optimizations (same as --opt 0)')
        parser.add_argument('-o', '--output', metavar='PATH',
                           help='Output directory for compiled files')
        parser.add_argument('--ll', action='store_true',
                           help='Generate LLVM IR (.ll) file')
        parser.add_argument('--obj', action='store_true',
                           help='Generate object (.o) file')
        parser.add_argument('--asm', action='store_true',
                           help='Generate assembly (.s) file')
        parser.add_argument('--no-execute', action='store_true',
                           help='Do not execute after compilation')
    
    args = parser.parse_args()
    
    if args.version:
        print(f"{_LANG_NAME} {_VERSION}")
        return 0
    
    if args.license:
        print(_LICENSE)
        return 0
    
    if not args.file:
        print_banner()
        return 0
    
    compile_mode = False
    opt_level = 3
    output_dir = None
    gen_ll = False
    gen_obj = False
    gen_asm = False
    execute = True
    perf = args.perf
    
    if LLVM_AVAILABLE and args.compile:
        compile_mode = True
        opt_level = 0 if args.no_optimize else args.opt
        output_dir = args.output
        gen_ll = args.ll
        gen_obj = args.obj
        gen_asm = args.asm
        execute = not args.no_execute
    
    try:
        run_file(args.file, compile_mode, opt_level, output_dir, 
                gen_ll, gen_obj, gen_asm, execute, perf)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
        return 130
    except SystemExit as e:
        return e.code
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())
