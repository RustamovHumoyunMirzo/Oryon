class Program:
    def __init__(self, statements):
        self.statements = statements

class VarAssign:
    def __init__(self, vtype, name, value, private):
        self.vtype = vtype
        self.name = name
        self.value = value
        self.private = private

class VarSet:
    def __init__(self, name, value, op='='):
        self.name = name
        self.value = value
        self.op = op

class FuncDef:
    def __init__(self, name, params, body, return_type, private=False, is_async=False):
        self.name = name
        self.params = params
        self.body = body
        self.return_type = return_type
        self.private = private
        self.is_async = is_async

class IfBlock:
    def __init__(self, cond, body, elseif_blocks, else_block):
        self.cond = cond
        self.body = body
        self.elseif_blocks = elseif_blocks
        self.else_block = else_block

class FuncCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args

class BinaryOp:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class UnaryOp:
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

class Literal:
    def __init__(self, value):
        self.value = value

class Var:
    def __init__(self, name):
        self.name = name

class ExprStmt:
    def __init__(self, expr):
        self.expr = expr

class ReturnNode:
    def __init__(self, value):
        self.value = value

class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value

class SwitchNode:
    def __init__(self, expr, cases, default_case):
        self.expr = expr
        self.cases = cases
        self.default_case = default_case

class Break:
    pass

class BreakSignal(Exception):
    pass

class ListLiteral:
    def __init__(self, items):
        self.items = items

class TupleLiteral:
    def __init__(self, items):
        self.items = items

class DictLiteral:
    def __init__(self, pairs):
        self.pairs = pairs

class IndexAccess():
    def __init__(self, collection, index):
        self.collection = collection
        self.index = index

class MethodCall():
    def __init__(self, receiver, method_name, args):
        self.receiver = receiver
        self.method_name = method_name
        self.args = args

class VarSetExpr:
    def __init__(self, target_expr, value, op):
        self.target_expr = target_expr
        self.value = value
        self.op = op

class LambdaFunc():
    def __init__(self, params, body, return_type=None, is_async=False):
        self.params = params
        self.body = body
        self.return_type = return_type
        self.is_async = is_async

class WhileNode:
    def __init__(self, condition, body):
        self.cond = condition
        self.body = body

class ForNode:
    def __init__(self, var_name, iterable_expr, body):
        self.var_name = var_name
        self.iterable_expr = iterable_expr
        self.body = body

class CStyleForNode:
    def __init__(self, init_stmt, condition, increment, body):
        self.init_stmt = init_stmt
        self.condition = condition
        self.increment = increment
        self.body = body

class ClassDef:
    def __init__(self, name, body, private, superclass=None):
        self.name = name
        self.body = body
        self.private = private
        self.superclass = superclass

class PropertyAccess:
    def __init__(self, obj, property_name):
        self.obj = obj
        self.property_name = property_name

class Assign:
    def __init__(self, target, value):
        self.target = target
        self.value = value

class ClassValue:
    def __init__(self, class_def, closure_env, superclass_val=None):
        self.class_def = class_def
        self.closure_env = closure_env
        self.superclass = superclass_val

class TryCatchNode:
    def __init__(self, try_block, catch_error, catch_type, catch_block, finally_block, catchonly_block):
        self.try_block = try_block
        self.catch_error = catch_error
        self.catch_type = catch_type
        self.catch_block = catch_block
        self.finally_block = finally_block
        self.catchonly_block = catchonly_block

class ThrowNode:
    def __init__(self, expr, err_type):
        self.expr = expr
        self.exception_type = err_type

class ThrowSignal(Exception):
    def __init__(self, value, err_type):
        self.value = unwrap(value)
        self.exception_type = unwrap(err_type)
    
    def __str__(self):
        if isinstance(self.value, str):
            return self.value
        elif isinstance(self.value, (int, float, bool)):
            return str(self.value)
        elif hasattr(self.value, 'value'):
            return str(self.value.value)
        else:
            return str(self.value)

class ImportNode:
    def __init__(self, path, symbols=None, itype=0):
        self.path = path
        self.symbols = symbols or []
        self.type = itype
    def __repr__(self):
        return f"ImportNode(path={self.path!r}, symbols={self.symbols!r})"
    
class InterpolatedString:
    def __init__(self, parts):
        self.parts = parts
    def __repr__(self):
        return f"InterpolatedString({self.parts})"

class ContinueNode:
    pass

class ContinueSignal(Exception):
    pass

class AwaitExpr():
    def __init__(self, expr):
        self.expr = expr

def is_entry(v):
    return isinstance(v, tuple) and len(v) == 3

def unwrap(v, target=0):
    return v[target] if is_entry(v) else v