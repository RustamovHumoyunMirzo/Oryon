from ast_nodes import *
from native import native_env, native_loop
import os
import oryon_parser
import oryon_lexer
from standard_lib import StdModule
import async_runtime
import types

#std
from std import global_std
import std.std_math
import std.std_string
import std.std_system
import std.std_types
import std.std_memory
import std.std_ffi
import std.std_fs

class AsyncFrame:
    def __init__(self, interpreter, func_value, args):
        self.interpreter = interpreter
        self.func = func_value
        self.args = args
        self.pc = 0
        self.env = None
        self.finished = False

    def run(self, send_value=None):
        if self.env is None:
            self.env = native_env.Environment(parent=self.func.closure_env)

            for name, arg in zip(self.func.params, self.args):
                unwrapped_value = self.interpreter.unwrap(arg)
                if isinstance(arg, tuple) and len(arg) == 3:
                    arg_type = arg[1]
                else:
                    arg_type = self.interpreter.get_type_name(unwrapped_value)
                
                self.env.define(name, unwrapped_value, arg_type, False)

        prev_env = self.interpreter.env
        prev_rt = self.interpreter.current_return_type

        self.interpreter.env = self.env
        self.interpreter.current_return_type = self.func.return_type

        prev_async = self.interpreter.in_async
        self.interpreter.in_async = True

        try:
            while self.pc < len(self.func.body):
                stmt = self.func.body[self.pc]
                self.pc += 1
                result = self.interpreter.visit(stmt)

                if isinstance(result, async_runtime.Future):
                    return result

        except ReturnSignal as ret:
            self.finished = True
            raise StopIteration(self.interpreter.unwrap(ret.value))

        finally:
            self.interpreter.env = prev_env
            self.interpreter.current_return_type = prev_rt
            self.interpreter.in_async = prev_async

        self.finished = True
        raise StopIteration(None)

    def __iter__(self):
        return self

    def __next__(self):
        return self.run(None)

    def send(self, value):
        return self.run(value)

class ModuleNamespace:
    def __init__(self, env, module_name="unknown"):
        super().__setattr__("_env", env)
        self.module_i = module_name

    def is_entry(self, v):
        return isinstance(v, tuple) and len(v) == 3

    def unwrap(self, v, target=0):
        return v[target] if self.is_entry(v) else v

    def __getattr__(self, name):
        try:
            return self._env.get(name, self._env)
        except Exception as e:
            raise AttributeError(f"Module has no attribute '{name}': {e}")

    def __setattr__(self, name, value):
        if name == "_env":
            super().__setattr__(name, value)
        else:
            self._env.define(name, value, "module", False)

    def __repr__(self):
        mname = self.unwrap(self.module_i)
        return f"module '{mname}'"

class FunctionValue:
    def __init__(self, params, body, closure_env, return_type, is_async=False):
        self.params = params
        self.body = body
        self.closure_env = closure_env
        self.return_type = return_type
        self.is_async = is_async

    @property
    def args(self):
        return self.params

    def _get_type_name(self, value):
        if value is None:
            return "null"
        if isinstance(value, ClassValue):
            return f"class"
        if isinstance(value, ClassInstance):
            return f"instance"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "str"
        if isinstance(value, list):
            return "list"
        if isinstance(value, tuple):
            return "tuple"
        if isinstance(value, dict):
            return "map"
        if isinstance(value, FunctionValue):
            return "function"
        if isinstance(value, types.BuiltinFunctionType):
            return "function"
        if isinstance(value, types.FunctionType):
            return "function"
        if hasattr(value, "__class__") and value.__class__ is not type:
            return f"class"
        if hasattr(value, "__class__"):
            return f"class"
        if isinstance(value, type):
            return f"object"
        return f"unknown"
        
    def _is_entry(self, v):
        return isinstance(v, tuple) and len(v) == 3

    def _unwrap(self, v, target=0):
        return v[target] if self._is_entry(v) else v

    def call(self, interpreter, args):
        if self.is_async:
            frame = AsyncFrame(interpreter, self, args)
            return async_runtime.loop.create_task(frame)
        
        local_env = native_env.Environment(parent=self.closure_env)
        try:
            this_entry = self.closure_env.get("this", local_env)
            if isinstance(this_entry, tuple) and len(this_entry) == 3:
                this_obj = this_entry[0]
            else:
                this_obj = this_entry
            local_env.define("this", this_obj, "this", False)
        except Exception:
            pass

        for name, value in zip(self.params, args):
            if isinstance(value, FunctionValue):
                local_env.define(name, value, "function", False)
            else:
                local_env.define(name, self._unwrap(value), self._unwrap(value, 1) if isinstance(self._unwrap(value, 1), str) else self._get_type_name(value), False)

        prev_env = interpreter.env
        prev_return = interpreter.current_return_type

        interpreter.env = local_env
        interpreter.current_return_type = self.return_type
        try:
            for stmt in self.body:
                interpreter.visit(stmt)
        except ReturnSignal as ret:
            interpreter.env = prev_env
            interpreter.current_return_type = prev_return
            return self._unwrap(ret.value)

        interpreter.env = prev_env
        interpreter.current_return_type = prev_return

        return None
    
    def bind(self, instance, class_val=None):
        env = native_env.Environment(parent=self.closure_env)
        env.bind_this(instance)
        if class_val and getattr(class_val, "superclass", None):
            env.define(
                "super",
                SuperProxy(instance, class_val.superclass),
                "super",
                False
            )
        return FunctionValue(
            self.params,
            self.body,
            env,
            self.return_type
        )
    
    def __repr__(self):
        return f"function '{hex(id(self))}'"

class SuperProxy:
    def __init__(self, instance, superclass):
        self.instance = instance
        self.superclass = superclass

class ClassInstance:
    def __init__(self, class_def):
        self.class_def = class_def
        self.fields = {}

class Interpreter:
    def __init__(self):
        self.global_env = native_env.Environment()
        self.global_env.define("input", lambda *args: input(*args), "function", False)
        self.global_env.define("output", lambda *args: print(*args), "function", False)
        self.global_env.define("type", lambda x: self.get_type_name(x), "function", False)
        self.global_env.define("kindof", lambda v,t: self.instance_of(v,t), "function", False)
        for i in global_std.functions:
            self.global_env.define(i[0], i[1], i[2], i[3])
        self.env = self.global_env
        self.current_return_type = None
        self.classes = {}
        self.current_dir = ""
        self.imported_modules = {}
        self.currently_importing = set()
        self.in_async = False

    def is_entry(self, v):
        return isinstance(v, tuple) and len(v) == 3

    def unwrap(self, v, target=0):
        return v[target] if self.is_entry(v) else v

    def push_scope(self):
        self.env = native_env.Environment(parent=self.env)

    def instance_of(self, value, ttype):
        actual = self.get_type_name(value)
        
        if isinstance(actual, ModuleNamespace):
            return False
        
        if self.is_entry(ttype):
            ttype = self.unwrap(ttype)
        
        if hasattr(ttype, 'thistype'):
            ttype = ttype.thistype
        
        if isinstance(ttype, type) and hasattr(ttype, '__name__'):
            type_name = ttype.__name__
            if type_name == "StringType":
                ttype = "str"
            elif type_name == "IntegerType":
                ttype = "int"
            elif type_name == "LongType":
                ttype = "long"
            elif type_name == "FloatType":
                ttype = "float"
            elif type_name == "DoubleType":
                ttype = "double"
            elif type_name == "MapType":
                ttype = "map"
            elif type_name == "ListType":
                ttype = "list"
            elif type_name == "TupleType":
                ttype = "tuple"
            elif type_name == "BoolType":
                ttype = "bool"
        
        if not isinstance(actual, str):
            return False
        
        if not isinstance(ttype, str):
            if isinstance(value, ClassInstance):
                if isinstance(self.classes.get(value.class_def.name), type(ttype)):
                    if value.class_def.name == ttype.class_def.name or value.class_def.superclass == ttype.class_def.name:
                        return True
            return False

        if actual == ttype:
            return True
        
        if actual == self.get_type_name(ttype):
            return True
        
        if actual.startswith("instance '") and ttype.startswith("class '"):
            actual_name = actual[10:-1]
            target_name = ttype[7:-1]
            return actual_name == target_name
        
        if actual.startswith("class '") and ttype.startswith("class '"):
            actual_name = actual[7:-1]
            target_name = ttype[7:-1]
            return actual_name == target_name
        
        if actual.startswith("instance '"):
            actual_class_name = actual[10:-1]
            if actual_class_name in self.classes:
                class_val = self.classes[actual_class_name]
                current = class_val
                while current is not None:
                    if current.class_def.name == ttype:
                        return True
                    if f"class '{current.class_def.name}'" == ttype:
                        return True
                    if f"instance '{current.class_def.name}'" == ttype:
                        return True
                    current = getattr(current, 'superclass_val', None)
        
        primitive_aliases = {
            "int": ["long"],
            "long": ["int"],
            "float": ["double"],
            "double": ["float"],
            "bool": [],
            "str": [],
            "list": [],
            "tuple": [],
            "map": []
        }
        
        if ttype in primitive_aliases and actual in primitive_aliases[ttype]:
            return True
        
        if actual in primitive_aliases and ttype in primitive_aliases[actual]:
            return True
        
        return False

    def get_type_name(self, value):
        if isinstance(value, tuple) and len(value) == 3:
            _, declared_type, _ = value
            return declared_type
        if value is None:
            return "null"
        if isinstance(value, ModuleNamespace):
            return value
        if isinstance(value, ClassValue):
            return f"class '{value.class_def.name}'"
        if isinstance(value, ClassInstance):
            return f"instance '{value.class_def.name}'"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "str"
        if isinstance(value, list):
            return "list"
        if isinstance(value, tuple):
            return "tuple"
        if isinstance(value, dict):
            return "map"
        if isinstance(value, FunctionValue):
            return "function"
        if isinstance(value, types.BuiltinFunctionType):
            return "function"
        if isinstance(value, types.FunctionType):
            return "function"
        if hasattr(value, "__class__") and value.__class__ is not type:
            return f"class '{value.__class__.__name__}'"
        if hasattr(value, "__class__"):
            return f"class '{value.__name__}'"
        if isinstance(value, type):
            return f"object '{value.__name__}'"
        return f"unknown '{value.__name__}'"

    def pop_scope(self):
        if self.env.parent is None:
            raise Exception("Cannot pop global scope")
        self.env = self.env.parent

    def visit(self, node):
        method_name = 'visit_' + node.__class__.__name__
        method = getattr(self, method_name, self.no_visit_method)
        return method(node)

    def no_visit_method(self, node):
        raise Exception(f'No visit_{node.__class__.__name__} method')
    
    def _is_env_descendant(self, origin_env, declaring_env):
        cur = origin_env
        while cur and cur is not None:
            if cur is declaring_env:
                return True
            cur = getattr(cur, "parent", None)
        return False

    def visit_Program(self, node):
        for stmt in node.statements:
            if stmt is not None:
                self.visit(stmt)

    def _is_subclass_or_same(self, sub_class_val, super_class_val):
        current = sub_class_val
        while current is not None:
            if current.class_def.name == super_class_val.class_def.name:
                return True
            current = current.superclass
        return False

    def visit_VarAssign(self, node):
        val_entry = self.visit(node.value) if node.value else None
        val = self.unwrap(val_entry) if val_entry is not None else None
        vtype = node.vtype
        name = node.name

        if vtype == "auto":
            self.env.define(name, val, vtype, node.private)
            return

        if val is None:
            self.env.define(node.name, None, vtype, node.private)
            return

        if vtype in self.classes:
            if isinstance(val, ClassInstance):
                declared_class_val = self.classes[vtype]
                value_class_val = self.classes[val.class_def.name]
                if not self._is_subclass_or_same(value_class_val, declared_class_val):
                    raise Exception(
                        f"TypeError: Cannot assign instance of '{value_class_val.class_def.name}' "
                        f"to variable '{name}' of type '{declared_class_val.class_def.name}'"
                    )
                self.env.define(name, val, vtype, node.private)
                return
            else:
                raise Exception(f"Expected instance of class '{vtype}' for variable '{name}'")
        
        try:
            type_obj = self.env.get(vtype)
            if type_obj is not None:
                if isinstance(type_obj, tuple):
                    type_obj = type_obj[0]
                if isinstance(type_obj, type) and isinstance(val, type_obj):
                    self.env.define(name, val, vtype, node.private)
                    return
                elif isinstance(type_obj, type):
                    raise Exception(
                        f"TypeError: Expected instance of '{vtype}' for variable '{name}', "
                        f"got {type(val).__name__}"
                    )
        except:
            pass

        if node.vtype == "int":
            if isinstance(val, int):
                pass
            elif isinstance(val, float):
                if val.is_integer():
                    val = int(val)
                else:
                    raise Exception(f"TypeError: Cannot assign non-integer float {val} to int variable '{node.name}'")
            elif isinstance(val, str):
                try:
                    val = int(val)
                except ValueError:
                    raise Exception(f"TypeError: Cannot convert string '{val}' to int for variable '{node.name}'")
            else:
                raise Exception(f"TypeError: Cannot assign {type(val).__name__} to int variable '{node.name}'")

        elif node.vtype == "str":
            if isinstance(val, str):
                val = str(val)
            else:
                raise Exception(f"TypeError: Cannot assign {type(val).__name__} to str variable '{node.name}'")

        elif node.vtype == "float":
            if isinstance(val, (int, float)):
                val = float(val)
            elif isinstance(val, str):
                try:
                    val = float(val)
                except ValueError:
                    raise Exception(f"TypeError: Cannot convert string '{val}' to float for variable '{node.name}'")
            else:
                raise Exception(f"TypeError: Cannot assign {type(val).__name__} to float variable '{node.name}'")

        elif node.vtype == "long":
            if isinstance(val, int):
                pass
            elif isinstance(val, float) and val.is_integer():
                val = int(val)
            elif isinstance(val, str):
                try:
                    val = int(val)
                except ValueError:
                    raise Exception(f"TypeError: Cannot convert string '{val}' to long for variable '{node.name}'")
            else:
                raise Exception(f"TypeError: Cannot assign {type(val).__name__} to long variable '{node.name}'")

        elif node.vtype == "double":
            if isinstance(val, (int, float)):
                val = float(val)
            elif isinstance(val, str):
                try:
                    val = float(val)
                except ValueError:
                    raise Exception(f"TypeError: Cannot convert string '{val}' to double for variable '{node.name}'")
            else:
                raise Exception(f"TypeError: Cannot assign {type(val).__name__} to double variable '{node.name}'")

        elif node.vtype == "bool":
            if isinstance(val, bool):
                pass
            elif isinstance(val, str):
                val_lower = val.lower()
                if val_lower in ("true", "1"):
                    val = True
                elif val_lower in ("false", "0"):
                    val = False
                else:
                    raise Exception(f"TypeError: Cannot convert string '{val}' to bool for variable '{node.name}'")
            else:
                raise Exception(f"TypeError: Cannot assign {type(val).__name__} to bool variable '{node.name}'")

        elif node.vtype == "list":
            if not isinstance(val, list):
                raise Exception(f"TypeError: Expected list for variable '{node.name}', got {type(val).__name__}")

        elif node.vtype == "tuple":
            if not isinstance(val, tuple):
                raise Exception(f"TypeError: Expected tuple for variable '{node.name}', got {type(val).__name__}")

        elif node.vtype == "map":
            if not isinstance(val, dict):
                raise Exception(f"TypeError: Expected map/dict for variable '{node.name}', got {type(val).__name__}")
        else:
            raise Exception(f"TypeError: The type '{vtype}' could not be found")
        
        self.env.define(node.name, val, node.vtype, node.private)

    def visit_VarSet(self, node):
        val_entry = self.visit(node.value)
        val = self.unwrap(val_entry)
        name = node.name
        op = node.op

        try:
            if op == "=":
                self.env.assign(name, val)
            else:
                current_entry = self.env.get(name)
                current_val = self.unwrap(current_entry)
                if op == "+=":
                    self.env.assign(name, current_val + val)
                elif op == "-=":
                    self.env.assign(name, current_val - val)
                elif op == "*=":
                    self.env.assign(name, current_val * val)
                elif op == "/=":
                    self.env.assign(name, current_val / val)
                elif op == "%=":
                    self.env.assign(name, current_val % val)
                else:
                    raise Exception(f"Unknown assignment operator '{op}'")
        except Exception as e:
            raise e
    
    def visit_VarSetExpr(self, node):
        val_entry = self.visit(node.value)
        val = self.unwrap(val_entry)
        target_node = node.target_expr
        op = node.op

        if isinstance(target_node, Var):
            name = target_node.name
            try:
                if op == "=":
                    self.env.assign(name, val)
                else:
                    current_entry = self.env.get(name)
                    current_val = self.unwrap(current_entry)
                    if op == "+=":
                        self.env.assign(name, current_val + val)
                    elif op == "-=":
                        self.env.assign(name, current_val - val)
                    elif op == "*=":
                        self.env.assign(name, current_val * val)
                    elif op == "/=":
                        self.env.assign(name, current_val / val)
                    elif op == "%=":
                        self.env.assign(name, current_val % val)
                    else:
                        raise Exception(f"Unknown assignment operator '{op}'")
            except Exception as e:
                raise e
        elif isinstance(target_node, PropertyAccess):
            obj_entry = self.visit(target_node.obj)
            obj = self.unwrap(obj_entry)
            prop = target_node.property_name

            if not isinstance(obj, ClassInstance):
                raise Exception(f"Cannot assign property '{prop}' on non-class instance {obj}")

            if op == "=":
                existing = obj.fields.get(prop)
                if existing and isinstance(existing, tuple) and len(existing) >= 3:
                    _, is_priv, decl_env = existing
                    obj.fields[prop] = (val, is_priv, decl_env)
                else:
                    obj.fields[prop] = (val, False, self.env)
            else:
                current_entry = obj.fields.get(prop, None)
                if current_entry is None:
                    raise Exception(f"Property '{prop}' is not set on the object for compound assignment")
                if isinstance(current_entry, tuple) and len(current_entry) >= 3:
                    current_val, is_priv, decl_env = current_entry
                else:
                    current_val, is_priv, decl_env = current_entry, False, self.env

                if is_priv:
                    if not self._is_env_descendant(self.env, decl_env):
                        raise Exception(f"AccessError: Property '{prop}' is private")
                if op == "+=":
                    obj.fields[prop] = (current_val + val, is_priv, decl_env)
                elif op == "-=":
                    obj.fields[prop] = (current_val - val, is_priv, decl_env)
                elif op == "*=":
                    obj.fields[prop] = (current_val * val, is_priv, decl_env)
                elif op == "/=":
                    obj.fields[prop] = (current_val / val, is_priv, decl_env)
                elif op == "%=":
                    obj.fields[prop] = (current_val % val, is_priv, decl_env)
                else:
                    raise Exception(f"Unknown assignment operator '{op}'")
        elif isinstance(target_node, IndexAccess):
            container_entry = self.visit(target_node.collection)
            container = self.unwrap(container_entry)
            index_entry = self.visit(target_node.index)
            index = self.unwrap(index_entry)
            if not isinstance(container, list):
                raise Exception(
                    f"Type {type(container).__name__} does not support indexed assignment"
                )
            try:
                if op == "=":
                    container[index] = val
                else:
                    current_val = container[index]
                    if op == "+=":
                        container[index] = current_val + val
                    elif op == "-=":
                        container[index] = current_val - val
                    elif op == "*=":
                        container[index] = current_val * val
                    elif op == "/=":
                        container[index] = current_val / val
                    elif op == "%=":
                        container[index] = current_val % val
                    else:
                        raise Exception(f"Unknown assignment operator '{op}'")
            except IndexError:
                raise Exception("Index out of bounds")
        else:
            raise Exception(f"Unsupported assignment target type {type(target_node)}")

    def visit_Var(self, node):
        raw_val = None
        try:
            raw_val = self.env.get(node.name, self.env)
        except Exception:
            raise Exception(f"{node.name} not found")
        return raw_val

    def visit_Literal(self, node):
        return node.value

    def visit_BinaryOp(self, node):
        left_entry = self.visit(node.left)
        right_entry = self.visit(node.right)
        left = self.unwrap(left_entry)
        right = self.unwrap(right_entry)
        op = node.op
        if left is None or right is None:
            raise Exception(f"RuntimeError: Cannot perform '{op}' on null value")
        if op == '+':
            if isinstance(left, str) or isinstance(right, str):
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                else:
                    raise Exception(f"TypeError: Cannot add {type(left).__name__} and {type(right).__name__}")

            if isinstance(left, float) or isinstance(right, float):
                return float(left + right)
            return left + right
        if op == '-': return left - right
        if op == '*': return left * right
        if op == '/': return left / right
        if op == '==': return left == right
        if op == '!=': return left != right
        if op == '<': return left < right
        if op == '>': return left > right
        if op == '<=': return left <= right
        if op == '>=': return left >= right
        if op == '&&': return bool(left) and bool(right)
        if op == '||': return bool(left) or bool(right)
        if op == '**':
            return left ** right
        if op == '//':
            return left // right
        if op == '%':
            return left % right
        if op == '&':
            return left & right
        if op == '|':
            return left | right
        if op == '^':
            return left ^ right
        if op == '<<':
            return left << right
        if op == '>>':
            return left >> right
        if op == '===':
            return (left == right) and (type(left) == type(right))
        if op == "in":
            return left in right

        raise Exception(f"Unknown binary operator {op}")

    def visit_UnaryOp(self, node):
        expr_entry = self.visit(node.expr)
        expr = self.unwrap(expr_entry)
        if node.op == '-':
            return -expr
        elif node.op == '+':
            return +expr
        elif node.op == '!':
            return not expr
        raise Exception(f"Unknown unary operator {node.op}")

    def visit_IfBlock(self, node):
        if self.unwrap(self.visit(node.cond)):
            for stmt in node.body:
                if stmt is not None:
                    self.visit(stmt)
            return
        for cond, body in node.elseif_blocks:
            if self.unwrap(self.visit(cond)):
                for stmt in body:
                    if stmt is not None:
                        self.visit(stmt)
                return
        if node.else_block:
            for stmt in node.else_block:
                if stmt is not None:
                    self.visit(stmt)

    def visit_SwitchNode(self, node):
        switch_value = self.unwrap(self.visit(node.expr))
        try:
            for case_expr, body in node.cases:
                case_value = self.unwrap(self.visit(case_expr))
                if switch_value == case_value:
                    for stmt in body:
                        self.visit(stmt)
                    break
            else:
                if node.default_case:
                    for stmt in node.default_case:
                        self.visit(stmt)
        except BreakSignal:
            pass

    def visit_Break(self, node):
        raise BreakSignal()
    
    def visit_AwaitExpr(self, node):
        fut = self.visit(node.expr)
        if not isinstance(fut, async_runtime.Future):
            raise Exception("'await' can only be used on async values")
        if fut.done:
            return fut.result
        while not fut.done:
            async_runtime.loop.run()
        return fut.result

    def visit_FuncDef(self, node):
        valid_builtin_types = {"void", "int", "long", "float", "double", "str", "bool", "list", "tuple", "map", "any"}

        return_type = node.return_type
        if not return_type:
            return_type = "void"

        rt_lower = return_type.lower()

        if rt_lower not in valid_builtin_types:
            if return_type not in self.classes:
                try:
                    type_obj_entry = self.env.get(return_type)
                    type_obj = self.unwrap(type_obj_entry)
                    if type_obj is None:
                        raise Exception(f"TypeError: Unknown return type '{node.return_type}' in function definition '{node.name}'")
                except Exception as e:
                    raise Exception(e)

        func_val = FunctionValue(
            node.params,
            node.body,
            self.env,
            rt_lower if rt_lower in valid_builtin_types else return_type,
            is_async=node.is_async
        )
        self.env.define(node.name, func_val, "function", node.private)

    def visit_LambdaFunc(self, node):
        return FunctionValue(
            node.params, 
            node.body, 
            self.env, 
            "any",
            is_async=getattr(node, 'is_async', False)
        )

    def collect_fields(self, class_val, instance):
        if class_val.superclass:
            self.collect_fields(class_val.superclass, instance)

        class_vars = getattr(class_val.closure_env, "vars", {})
        for k, v in class_vars.items():
            if isinstance(v, tuple) and v[1] == "function":
                continue
            if k not in instance.fields:
                instance.fields[k] = (v[0], v[2], class_val.closure_env)

    def visit_FuncCall(self, node):
        if node.name in self.classes:
            class_val = self.classes[node.name]
            instance = ClassInstance(class_val.class_def)
            self.collect_fields(class_val, instance)

            try:
                class_vars = getattr(class_val.closure_env, "vars", None)
                if class_vars and isinstance(class_vars, dict):
                    for k, v in class_vars.items():
                        try:
                            if isinstance(v, tuple) and len(v) == 3:
                                value, vtype, is_priv = v
                                if vtype == "function":
                                    continue
                                instance.fields[k] = (value, bool(is_priv), class_val.closure_env)
                            else:
                                instance.fields[k] = (v, False, class_val.closure_env)
                        except Exception:
                            instance.fields[k] = (v, False, class_val.closure_env)
            except Exception:
                pass

            try:
                init_func_val = class_val.closure_env.get("init", class_val.closure_env)
            except Exception:
                init_func_val = None

            if init_func_val:
                if isinstance(init_func_val, tuple) and len(init_func_val) == 3 and init_func_val[1] == 'function':
                    func_value = init_func_val[0]
                else:
                    func_value = init_func_val

                if isinstance(func_value, FunctionValue):
                    bound_init = func_value.bind(instance)
                    args = [self.visit(arg) for arg in node.args]
                    bound_init.call(self, args)
                elif callable(func_value):
                    args = [self.visit(arg) for arg in node.args]
                    func_value(*args)

            return instance

        func_val = self.env.get(node.name, self.env)
        if isinstance(func_val, tuple):
            func = func_val[0]
        else:
            func = func_val

        args = [self.visit(arg) for arg in node.args]

        if isinstance(func, FunctionValue) and func.is_async:
            return func.call(self, args)

        unwrapped_args = [self.unwrap(arg) for arg in args]

        if callable(func) and not isinstance(func, FunctionValue):
            return func(*unwrapped_args)

        if isinstance(func, FunctionValue):
            return func.call(self, args)

        raise Exception(f"'{node.name}' is not a function")

    def visit_ReturnNode(self, node):
        type_map = {
            int: "int",
            str: "str",
            float: "float",
            bool: "bool",
            type(None): "null",
            list: "list",
            tuple: "tuple",
            dict: "map",
        }
        if node.value is None:
            val = None
            val_entry = (None, "null", False)
            vtype = "null"
        else:
            val_entry = self.visit(node.value)
            val = self.unwrap(val_entry)
            vtype = val_entry[1] if self.is_entry(val_entry) else type_map.get(type(val), "unknown")

        expected = self.current_return_type.lower() if self.current_return_type else "void"

        if expected == "any":
            raise ReturnSignal(val_entry)

        valid_types = {"void", "int", "float", "double", "long", "str", "bool", "null", "list", "tuple", "map"}

        if expected not in valid_types:
            if expected in self.classes:
                class_def = self.classes[expected]
                if not (hasattr(val, 'class_def') and val.class_def.name == expected and vtype == expected):
                    raise Exception(f"TypeError: Function expected to return instance of '{expected}' but returned {type(val).__name__} with type {vtype}")
                raise ReturnSignal(val_entry)
            else:
                type_obj_entry = self.env.get(self.current_return_type)
                type_obj = self.unwrap(type_obj_entry)
                if type_obj is not None:
                    raise ReturnSignal(val_entry)
                raise Exception(f"TypeError: Unknown return type '{expected}' in function")

        if expected == "void":
            if val is not None:
                raise Exception(f"TypeError: Function declared as void but returned a value")
            raise ReturnSignal(val_entry)

        def check_type(py_types, expected_name):
            if not isinstance(val, py_types) or vtype != expected_name:
                raise Exception(f"TypeError: Function expected to return {expected_name} but returned {type(val).__name__} with type {vtype}")
            
        def check_int_or_long(val, vtype, expected_name):
            if not isinstance(val, int) or vtype not in ("int", "long"):
                raise Exception(f"TypeError: Function expected to return {expected_name} but returned {type(val).__name__} with type {vtype}")

        if expected == "int":
            check_int_or_long(val, vtype, "int")
        elif expected == "long":
            check_int_or_long(val, vtype, "long")
        elif expected == "float":
            if not isinstance(val, (int, float)) or vtype not in ("float", "double"):
                raise Exception(f"TypeError: Function expected to return float but returned {type(val).__name__} with type {vtype}")
        elif expected == "double":
            if not isinstance(val, (int, float)) or vtype not in ("float", "double"):
                raise Exception(f"TypeError: Function expected to return double but returned {type(val).__name__} with type {vtype}")
        elif expected == "str":
            check_type(str, "str")
        elif expected == "bool":
            check_type(bool, "bool")
        elif expected == "list":
            check_type(list, "list")
        elif expected == "tuple":
            check_type(tuple, "tuple")
        elif expected == "map":
            check_type(dict, "map")

        raise ReturnSignal(val_entry)

    def visit_ListLiteral(self, node):
        return [self.unwrap(self.visit(item)) for item in node.items]

    def visit_TupleLiteral(self, node):
        return tuple(self.unwrap(self.visit(item)) for item in node.items)

    def visit_DictLiteral(self, node):
        return {self.unwrap(self.visit(k)): self.unwrap(self.visit(v)) for k, v in node.pairs}

    def visit_IndexAccess(self, node):
        collection = self.unwrap(self.visit(node.collection))
        index = self.unwrap(self.visit(node.index))

        try:
            return collection[index]
        except Exception as e:
            raise Exception(f"Indexing error: {e}")

    def visit_MethodCall(self, node):
        def unwrap_entry(entry):
            while isinstance(entry, tuple) and len(entry) == 3:
                entry = entry[0]
            return entry

        receiver = self.visit(node.receiver)
        if isinstance(receiver, tuple):
            receiver = receiver[0]

        method_name = node.method_name
        args = [self.unwrap(self.visit(arg)) for arg in node.args]

        if isinstance(receiver, ModuleNamespace):
            try:
                entry = getattr(receiver, method_name)
            except AttributeError:
                raise Exception(f"Module has no attribute '{method_name}'")

            value = unwrap_entry(entry)

            if isinstance(value, ClassValue):
                class_def = value.class_def
                instance = ClassInstance(class_def)

                init_entry = (
                    value.closure_env.get("init") or
                    value.closure_env.get("__init__")
                )

                if init_entry:
                    init_func = unwrap_entry(init_entry)
                    bound = init_func.bind(instance, value)
                    bound.call(self, args)

                return instance

            if isinstance(value, FunctionValue):
                return value.call(self, args)

            if callable(value):
                return value(*args)

            raise Exception(f"Attribute '{method_name}' of module is not callable")
        
        if isinstance(receiver, SuperProxy):
            (entry, _) = self.find_method(receiver.superclass, method_name)
            func = self.unwrap(entry)

            if not isinstance(func, FunctionValue):
                raise Exception(f"Super method '{method_name}' is not callable")

            bound = func.bind(receiver.instance, receiver.superclass)
            return bound.call(self, args)

        if isinstance(receiver, ClassValue):
            (entry, declaring_class) = self.find_method(receiver, method_name)
            func = unwrap_entry(entry)

            if isinstance(func, FunctionValue):
                this_entry = self.env.get("this", self.env)
                this_obj = this_entry[0] if isinstance(this_entry, tuple) else this_entry
                bound = func.bind(this_obj, declaring_class)
                return bound.call(self, args)

            raise Exception(f"Class method '{method_name}' is not callable")

        if isinstance(receiver, ClassInstance):
            class_val = self.classes[receiver.class_def.name]

            try:
                (entry, declaring_class) = self.find_method(class_val, method_name)
                func_obj = unwrap_entry(entry)
                is_private = self.unwrap(entry, 2)
            except Exception:
                raise Exception(
                    f"Method '{method_name}' not found in class {class_val.class_def.name}"
                )

            if is_private:
                call_env = self.env
                declaring_env = declaring_class.closure_env
                if not self._is_env_descendant(call_env, declaring_env):
                    raise Exception(f"AccessError: '{method_name}' is private")

            if isinstance(func_obj, FunctionValue):
                bound = func_obj.bind(receiver, declaring_class)
                return bound.call(self, args)

            if callable(func_obj):
                return func_obj(*args)

            raise Exception(
                f"Method '{method_name}' found but not callable in class {class_val.class_def.name}"
            )

        if isinstance(receiver, list):
            if method_name in ("add", "append"):
                receiver.append(args[0])
                return None

            if method_name == "insert":
                if len(args) != 2:
                    raise Exception("'insert' expects index and value")
                receiver.insert(args[0], args[1])
                return None

            if method_name == "remove":
                receiver.remove(args[0])
                return None

            if method_name == "pop":
                return receiver.pop(args[0]) if args else receiver.pop()

            if method_name in ("length", "len"):
                return len(receiver)

            if method_name == "get":
                return receiver[args[0]]

            if method_name == "set":
                receiver[args[0]] = args[1]
                return None

            if method_name == "clear":
                receiver.clear()
                return None

            if method_name == "contains":
                return args[0] in receiver

            if method_name == "indexOf":
                return receiver.index(args[0])

            if method_name == "copy":
                return receiver.copy()

            if method_name == "slice":
                start = args[0]
                end = args[1] if len(args) == 2 else None
                return receiver[start:end]

            if method_name == "reverse":
                receiver.reverse()
                return None

            if method_name == "sort":
                receiver.sort()
                return None

            raise Exception(f"List has no method '{method_name}'")

        if isinstance(receiver, dict):
            if method_name in ("add", "set"):
                receiver[args[0]] = args[1]
                return None

            if method_name == "remove":
                receiver.pop(args[0], None)
                return None

            if method_name == "get":
                return receiver.get(args[0])

            if method_name == "getOrDefault":
                return receiver.get(args[0], args[1])

            if method_name in ("contains", "has"):
                return args[0] in receiver

            if method_name == "keys":
                return list(receiver.keys())

            if method_name == "values":
                return list(receiver.values())

            if method_name == "items":
                return list(receiver.items())

            if method_name == "clear":
                receiver.clear()
                return None

            if method_name in ("length", "len"):
                return len(receiver)

            if method_name == "copy":
                return receiver.copy()

            if method_name == "join":
                receiver.update(args[0])
                return None
            raise Exception(f"Map has no method '{method_name}'")
        
        if hasattr(receiver, method_name):
            attr = getattr(receiver, method_name)
            if callable(attr):
                return attr(*args)
            else:
                return attr

        if isinstance(receiver, tuple):
            raise Exception("Tuples are immutable: no methods allowed")
        
        raise Exception(f"Type '{type(receiver).__name__}' has no methods")

    def visit_ExprStmt(self, node):
        return self.visit(node.expr)
    
    def visit_WhileNode(self, node):
        native_loop.native_while_loop(self, node.cond, node.body, BreakSignal, ContinueSignal, self.visit)
            
    def visit_ForNode(self, node):
        iterable_entry = self.visit(node.iterable_expr)
        iterable = self.unwrap(iterable_entry)

        if not hasattr(iterable, "__iter__"):
            raise Exception(f"TypeError: '{type(iterable).__name__}' object is not iterable")

        try:
            for item in iterable:
                self.env.define(node.var_name, item, self.get_type_name(item), False)

                try:
                    for stmt in node.body:
                        self.visit(stmt)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
        except BreakSignal:
            pass

    def visit_CStyleForNode(self, node):
        self.push_scope()

        try:
            if node.init_stmt is not None:
                self.visit(node.init_stmt)

            while True:
                if node.condition is not None:
                    cond_entry = self.visit(node.condition)
                    cond_value = self.unwrap(cond_entry)

                    if not cond_value:
                        break

                try:
                    for stmt in node.body:
                        self.visit(stmt)
                except ContinueSignal:
                    pass
                except BreakSignal:
                    break

                if node.increment is not None:
                    self.visit(node.increment)

        finally:
            self.pop_scope()

    def find_method(self, class_val, method_name):
        try:
            entry = class_val.closure_env.get(method_name)
            if entry is not None:
                return entry, class_val
        except Exception:
            pass

        if class_val.superclass_val:
            return self.find_method(class_val.superclass_val, method_name)

        raise Exception(f"Method '{method_name}' not found in class {class_val.class_def.name}")

    def visit_ClassDef(self, node):
        class_env = native_env.Environment(parent=self.global_env)

        prev_env = self.env
        self.env = class_env

        for member in node.body:
            self.visit(member)

        self.env = prev_env

        superclass_val = None
        if node.superclass:
            if node.superclass not in self.classes:
                raise Exception(f"Superclass '{node.superclass}' not found")
            superclass_val = self.classes[node.superclass]

        class_val = ClassValue(node, class_env, superclass_val)
        self.classes[node.name] = class_val
        self.env.define(node.name, class_val, "class", node.private)

    def visit_PropertyAccess(self, node):
        obj_entry = self.visit(node.obj)
        obj = self.unwrap(obj_entry)
        prop = node.property_name

        if isinstance(obj, ClassInstance):
            if prop in obj.fields:
                entry = obj.fields[prop]
                if isinstance(entry, tuple) and len(entry) >= 3:
                    val, is_priv, decl_env = entry[0], bool(entry[1]), entry[2]
                    if is_priv:
                        if not self._is_env_descendant(self.env, decl_env):
                            raise Exception(f"AccessError: '{prop}' is private")
                    return val
                else:
                    return entry
            raise Exception(f"Property '{prop}' not found on instance of class '{obj.class_def.name}'")
        elif isinstance(obj, dict):
            if prop in obj:
                return obj[prop]
            raise Exception(f"Map key '{prop}' not found in map {obj}")
        elif isinstance(obj, list):
            if prop.isdigit():
                idx = int(prop)
                if idx < len(obj):
                    return obj[idx]
                raise Exception(f"List index '{idx}' out of range")
            raise Exception(f"Lists do not support property '{prop}'")
        elif isinstance(obj, ModuleNamespace):
            try:
                return getattr(obj, prop)
            except AttributeError:
                raise Exception(f"Module has no attribute '{prop}'")
        else:
            try:
                val = getattr(obj, prop)
                return val
            except AttributeError:
                raise Exception(
                    f"Cannot access property '{prop}' on non-class instance '{obj}' (type: {type(obj).__name__})")

    def visit_ThrowNode(self, node):
        value = self.visit(node.expr)
        exception_type = node.exception_type
        if isinstance(exception_type, Literal) and hasattr(exception_type, 'value'):
            exception_type = self.visit(exception_type)
        raise ThrowSignal(value, exception_type)
    
    def visit_TryCatchNode(self, node):
        try:
            for stmt in node.try_block:
                self.visit(stmt)
        except ThrowSignal as err:
            isCaught = False

            if len(node.catchonly_block) > 0:
                for block in node.catchonly_block:
                    if block[2] is not None and not isCaught:
                        expected_type = self.visit(block[2])
                        actual_type = err.exception_type if err.exception_type else "Exception"

                        if expected_type == actual_type:
                            isCaught = True
                            self.push_scope()

                            if block[0] is not None:
                                if isinstance(err.value, str):
                                    error_msg = err.value
                                elif hasattr(err.value, 'value'):
                                    error_msg = err.value.value
                                else:
                                    error_msg = str(err.value)

                                self.env.define(block[0], error_msg, "str", False)

                            if block[1] is not None:
                                self.env.define(block[1], actual_type, "str", False)

                            try:
                                for stmt in block[3]:
                                    self.visit(stmt)
                            finally:
                                self.pop_scope()
                            break

            if len(node.catch_block) > 0 and not isCaught:
                isCaught = True
                self.push_scope()

                if node.catch_error is not None:
                    if isinstance(err.value, str):
                        error_msg = err.value
                    elif hasattr(err.value, 'value'):
                        error_msg = err.value.value
                    else:
                        error_msg = str(err.value)

                    self.env.define(node.catch_error, error_msg, "str", False)

                if node.catch_type is not None:
                    actual_type = err.exception_type if err.exception_type else "Exception"
                    if (isinstance(actual_type, Var)):
                        actual_type = self.unwrap(self.visit(actual_type))
                    self.env.define(node.catch_type, actual_type, "str", False)

                try:
                    for stmt in node.catch_block:
                        self.visit(stmt)
                finally:
                    self.pop_scope()

            if not isCaught:
                raise

        except Exception as err:
            isCaught = False

            if len(node.catchonly_block) > 0:
                for block in node.catchonly_block:
                    if block[2] is not None and not isCaught:
                        expected_type = self.visit(block[2])
                        actual_type = type(err).__name__

                        if expected_type == actual_type or expected_type == "Exception":
                            isCaught = True
                            self.push_scope()

                            if block[0] is not None:
                                error_msg = str(err)
                                self.env.define(block[0], error_msg, "str", False)

                            if block[1] is not None:
                                self.env.define(block[1], actual_type, "str", False)

                            try:
                                for stmt in block[3]:
                                    self.visit(stmt)
                            finally:
                                self.pop_scope()
                            break

            if len(node.catch_block) > 0 and not isCaught:
                isCaught = True
                self.push_scope()

                if node.catch_error is not None:
                    error_msg = str(err)
                    self.env.define(node.catch_error, error_msg, "str", False)

                if node.catch_type is not None:
                    actual_type = type(err).__name__
                    self.env.define(node.catch_type, actual_type, "str", False)

                try:
                    for stmt in node.catch_block:
                        self.visit(stmt)
                finally:
                    self.pop_scope()

            if not isCaught:
                raise

        finally:
            if node.finally_block:
                for stmt in node.finally_block:
                    self.visit(stmt)
    
    def visit_ContinueNode(self, _):
        raise ContinueSignal()

    def interpret_file(self, filepath):
        self.current_dir = os.path.dirname(os.path.abspath(filepath))
        source_code = self.read_file(filepath)

        lexer = oryon_lexer.Lexer(source_code)
        tokens = lexer.tokenize()
        parser = oryon_parser.Parser(tokens)
        ast = parser.parse()

        prev_env = self.env
        self.env = native_env.Environment(parent=self.global_env)

        try:
            self.visit(ast)
        except ContinueSignal:
            raise Exception("'continue' is only valid inside loop constructs")
        except BreakSignal:
            raise Exception("'break' is only valid inside loop constructs.")
        except ReturnSignal:
            raise Exception("Program ended by return statement")
        finally:
            self.env = prev_env

    def _import_local_module(self, node, current_dir):
        if current_dir is None:
            current_dir = self.current_dir or os.getcwd()

        module_path = self.resolve_module_path(node.path, current_dir)
        if not module_path:
            raise Exception(f"ImportError: Module '{node.path}' not found")

        if module_path in self.currently_importing:
            raise Exception(f"Circular import detected for module '{node.path}'")

        if module_path in self.imported_modules:
            module_env = self.imported_modules[module_path]
        else:
            self.currently_importing.add(module_path)
            try:
                source_code = self.read_file(module_path)
                lexer = oryon_lexer.Lexer(source_code)
                tokens = lexer.tokenize()
                parser = oryon_parser.Parser(tokens)
                ast = parser.parse()

                module_env = native_env.Environment(parent=self.global_env)
                prev_env = self.env
                self.env = module_env

                try:
                    self.visit(ast)
                except Exception as e:
                    self.env = prev_env
                    raise Exception(f"Error in imported module '{node.path}': {e}")

                self.env = prev_env
                self.imported_modules[module_path] = module_env

            finally:
                self.currently_importing.remove(module_path)

        return self._apply_import_symbols(node, module_env)
    
    def _apply_import_symbols(self, node, module_env):
        if node.symbols:
            if '*' in node.symbols:
                for sym in module_env.vars:
                    if self.env.has(sym):
                        raise Exception(f"ImportError: Symbol '{sym}' collides with existing declaration")

                    entry = module_env.get(sym)
                    value = self.unwrap(entry) if self.is_entry(entry) else entry
                    self.env.define(sym, value, "auto", False)
            else:
                for sym in node.symbols:
                    if not module_env.has(sym):
                        raise Exception(f"ImportError: Symbol '{sym}' not found in module '{node.path}'")
                    if self.env.has(sym):
                        raise Exception(f"ImportError: Symbol '{sym}' collides with existing declaration")

                    entry = module_env.get(sym)
                    value = self.unwrap(entry) if self.is_entry(entry) else entry
                    self.env.define(sym, value, "auto", False)
        else:
            module_name = node.path.split("/")[-1]
            if self.env.has(module_name):
                raise Exception(f"ImportError: Module name '{module_name}' collides with existing declaration")

            namespace = ModuleNamespace(module_env, module_name)
            self.env.define(module_name, namespace, "module", False)

        return None

    def visit_ImportNode(self, node, current_dir=None):
        if node.type == 1:
            module_name = node.path

            if module_name in self.imported_modules:
                module_env = self.imported_modules[module_name]
            else:
                try:
                    module_env = StdModule.load(module_name, self)
                except Exception as e:
                    raise Exception(f"ImportError: {e}")
                        
                self.imported_modules[module_name] = module_env

            return self._apply_import_symbols(node, module_env)

        return self._import_local_module(node, current_dir)

    def resolve_module_path(self, module_name, base_dir):
        possible_extensions = ['.or', '.oryon']

        candidate_path = os.path.normpath(os.path.join(base_dir, module_name))

        abs_candidate_path = os.path.abspath(candidate_path)

        for ext in possible_extensions:
            full_path = abs_candidate_path + ext
            if os.path.isfile(full_path):
                return full_path
        return None

    def read_file(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()