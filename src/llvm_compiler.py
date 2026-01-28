import os
import sys
from llvmlite import ir, binding
from ast_nodes import *
import oryon_lexer
import oryon_parser

class CompilerError(Exception):
    pass

class LLVMCompiler:
    def __init__(self):
        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()
        
        self.module = ir.Module(name="oryon_module")
        self.builder = None
        
        # Symbol tables
        self.variables = {}  # {name: (ptr, type)}
        self.functions = {}  # {name: ir.Function}
        self.classes = {}    # {name: ClassInfo}
        self.current_function = None
        self.current_class = None
        
        # Type mappings
        self.type_map = {
            'int': ir.IntType(32),
            'long': ir.IntType(64),
            'float': ir.FloatType(),
            'double': ir.DoubleType(),
            'bool': ir.IntType(1),
            'str': ir.IntType(8).as_pointer(),
            'auto': ir.IntType(32),
            'list': ir.IntType(8).as_pointer(),  # Generic pointer
            'tuple': ir.IntType(8).as_pointer(),
            'map': ir.IntType(8).as_pointer(),
        }
        
        # Runtime support functions
        self._declare_runtime_functions()
        
        # Control flow
        self.loop_exit_blocks = []
        self.loop_continue_blocks = []
        
        # Exception handling
        self.exception_handlers = []
        self.current_exception_block = None
        
        # String literals cache
        self.string_literals = {}
        
    def _declare_runtime_functions(self):
        """Declare runtime support functions"""
        # printf for I/O
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")
        
        # malloc/free for dynamic allocation
        size_t = ir.IntType(64)
        malloc_ty = ir.FunctionType(voidptr_ty, [size_t])
        self.malloc = ir.Function(self.module, malloc_ty, name="malloc")
        
        free_ty = ir.FunctionType(ir.VoidType(), [voidptr_ty])
        self.free = ir.Function(self.module, free_ty, name="free")
        
        # memcpy for copying data
        memcpy_ty = ir.FunctionType(voidptr_ty, [voidptr_ty, voidptr_ty, size_t])
        self.memcpy = ir.Function(self.module, memcpy_ty, name="memcpy")
        
        # String operations
        strlen_ty = ir.FunctionType(size_t, [voidptr_ty])
        self.strlen = ir.Function(self.module, strlen_ty, name="strlen")
        
        strcmp_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty, voidptr_ty])
        self.strcmp = ir.Function(self.module, strcmp_ty, name="strcmp")
        
        strcat_ty = ir.FunctionType(voidptr_ty, [voidptr_ty, voidptr_ty])
        self.strcat = ir.Function(self.module, strcat_ty, name="strcat")
        
        # Exception handling helpers
        setjmp_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty])
        self.setjmp = ir.Function(self.module, setjmp_ty, name="setjmp")
        
        longjmp_ty = ir.FunctionType(ir.VoidType(), [voidptr_ty, ir.IntType(32)])
        self.longjmp = ir.Function(self.module, longjmp_ty, name="longjmp")
        
    def get_llvm_type(self, type_str):
        """Convert Oryon type to LLVM type"""
        if isinstance(type_str, str):
            type_lower = type_str.lower()
            return self.type_map.get(type_lower, ir.IntType(32))
        return type_str
    
    def create_string_literal(self, value):
        """Create a global string literal"""
        if value in self.string_literals:
            return self.string_literals[value]
        
        # Create global string
        string_val = value + '\0'
        string_const = ir.Constant(ir.ArrayType(ir.IntType(8), len(string_val)),
                                   bytearray(string_val.encode('utf-8')))
        
        global_str = ir.GlobalVariable(self.module, string_const.type, 
                                       name=f".str.{len(self.string_literals)}")
        global_str.linkage = 'internal'
        global_str.global_constant = True
        global_str.initializer = string_const
        
        # Get pointer to first element
        zero = ir.Constant(ir.IntType(32), 0)
        str_ptr = self.builder.gep(global_str, [zero, zero])
        
        self.string_literals[value] = str_ptr
        return str_ptr
    
    def compile_file(self, filepath):
        """Main entry point - compile a file"""
        self.current_dir = os.path.dirname(os.path.abspath(filepath))
        source_code = self.read_file(filepath)
        
        lexer = oryon_lexer.Lexer(source_code)
        tokens = lexer.tokenize()
        parser = oryon_parser.Parser(tokens)
        ast = parser.parse()
        
        self.visit(ast)
        
        return self.module
    
    def read_file(self, filepath):
        """Read source file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def visit(self, node):
        """Dispatch to appropriate visitor method"""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        raise CompilerError(f'No visit method for {type(node).__name__}')
    
    def visit_Program(self, node):
        """Compile program - create main function"""
        # First pass: declare all functions and classes
        for stmt in node.statements:
            if isinstance(stmt, FuncDef):
                self._predeclare_function(stmt)
            elif isinstance(stmt, ClassDef):
                self._predeclare_class(stmt)
        
        # Create main function
        main_ty = ir.FunctionType(ir.IntType(32), [])
        main_func = ir.Function(self.module, main_ty, name="main")
        block = main_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.current_function = main_func
        
        # Visit all statements
        for stmt in node.statements:
            self.visit(stmt)
        
        # Return 0 from main
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(ir.IntType(32), 0))
    
    def _predeclare_function(self, node):
        """Predeclare function for forward references"""
        if node.name in self.functions:
            return
        
        if node.return_type:
            ret_type = self.get_llvm_type(node.return_type)
        else:
            ret_type = ir.IntType(32)  # Default return type
        
        param_types = [ir.IntType(32) for _ in node.params]
        func_ty = ir.FunctionType(ret_type, param_types)
        func = ir.Function(self.module, func_ty, name=node.name)
        self.functions[node.name] = func
    
    def _predeclare_class(self, node):
        """Predeclare class structure"""
        # Create opaque struct for class
        class_type = ir.global_context.get_identified_type(f"class.{node.name}")
        self.classes[node.name] = {
            'type': class_type,
            'fields': {},
            'methods': {},
            'superclass': node.superclass
        }
    
    def visit_VarAssign(self, node):
        """Variable declaration and assignment"""
        llvm_type = self.get_llvm_type(node.vtype)
        
        ptr = self.builder.alloca(llvm_type, name=node.name)
        self.variables[node.name] = (ptr, llvm_type)
        
        if node.value is not None:
            value = self.visit(node.value)
            value = self._cast_if_needed(value, llvm_type)
            self.builder.store(value, ptr)
        
        return ptr
    
    def _cast_if_needed(self, value, target_type):
        """Cast value to target type if needed"""
        if value.type == target_type:
            return value
        
        # Integer to integer
        if isinstance(target_type, ir.IntType) and isinstance(value.type, ir.IntType):
            if target_type.width > value.type.width:
                return self.builder.sext(value, target_type)
            else:
                return self.builder.trunc(value, target_type)
        
        # Integer to float
        elif isinstance(target_type, (ir.FloatType, ir.DoubleType)) and isinstance(value.type, ir.IntType):
            return self.builder.sitofp(value, target_type)
        
        # Float to integer
        elif isinstance(target_type, ir.IntType) and isinstance(value.type, (ir.FloatType, ir.DoubleType)):
            return self.builder.fptosi(value, target_type)
        
        # Float to float
        elif isinstance(target_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
            return self.builder.fpext(value, target_type)
        elif isinstance(target_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
            return self.builder.fptrunc(value, target_type)
        
        # Pointer casts
        elif isinstance(target_type, ir.PointerType) and isinstance(value.type, ir.PointerType):
            return self.builder.bitcast(value, target_type)
        
        return value
    
    def visit_VarSet(self, node):
        """Variable assignment"""
        if node.name not in self.variables:
            raise CompilerError(f"Undefined variable: {node.name}")
        
        ptr, var_type = self.variables[node.name]
        new_value = self.visit(node.value)
        
        if node.op != '=':
            old_value = self.builder.load(ptr)
            
            # Check if float operations
            is_float = isinstance(old_value.type, (ir.FloatType, ir.DoubleType))
            
            if node.op == '+=':
                new_value = self.builder.fadd(old_value, new_value) if is_float else self.builder.add(old_value, new_value)
            elif node.op == '-=':
                new_value = self.builder.fsub(old_value, new_value) if is_float else self.builder.sub(old_value, new_value)
            elif node.op == '*=':
                new_value = self.builder.fmul(old_value, new_value) if is_float else self.builder.mul(old_value, new_value)
            elif node.op == '/=':
                new_value = self.builder.fdiv(old_value, new_value) if is_float else self.builder.sdiv(old_value, new_value)
            elif node.op == '%=':
                new_value = self.builder.frem(old_value, new_value) if is_float else self.builder.srem(old_value, new_value)
        
        new_value = self._cast_if_needed(new_value, var_type)
        self.builder.store(new_value, ptr)
        return new_value
    
    def visit_VarSetExpr(self, node):
        """Handle complex assignment (property, index access)"""
        if isinstance(node.target_expr, Var):
            return self.visit(VarSet(node.target_expr.name, node.value, node.op))
        elif isinstance(node.target_expr, IndexAccess):
            # Handle array/list assignment
            collection = self.visit(node.target_expr.collection)
            index = self.visit(node.target_expr.index)
            value = self.visit(node.value)
            
            # Get element pointer and store
            elem_ptr = self.builder.gep(collection, [index])
            self.builder.store(value, elem_ptr)
            return value
        elif isinstance(node.target_expr, PropertyAccess):
            # Handle property assignment
            obj = self.visit(node.target_expr.obj)
            value = self.visit(node.value)
            
            # Store in object field
            # This is simplified - real implementation would need struct access
            return value
        
        raise CompilerError(f"Unsupported assignment target")
    
    def visit_FuncDef(self, node):
        """Function definition"""
        if node.name not in self.functions:
            self._predeclare_function(node)
        
        func = self.functions[node.name]
        
        # Save current state
        prev_builder = self.builder
        prev_function = self.current_function
        prev_vars = self.variables.copy()
        
        # Create function body
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.current_function = func
        
        # Add parameters to symbol table
        for param, arg in zip(node.params, func.args):
            arg.name = param
            ptr = self.builder.alloca(arg.type, name=param)
            self.builder.store(arg, ptr)
            self.variables[param] = (ptr, arg.type)
        
        # Visit function body
        returned = False
        for stmt in node.body:
            if isinstance(stmt, ReturnNode):
                returned = True
            self.visit(stmt)
            if self.builder.block.is_terminated:
                break
        
        # Add default return if needed
        if not self.builder.block.is_terminated:
            ret_type = func.return_value.type
            if isinstance(ret_type, ir.VoidType):
                self.builder.ret_void()
            else:
                self.builder.ret(ir.Constant(ret_type, 0))
        
        # Restore state
        self.builder = prev_builder
        self.current_function = prev_function
        self.variables = prev_vars
        
        return func
    
    def visit_FuncCall(self, node):
        """Function call"""
        if node.name not in self.functions:
            raise CompilerError(f"Undefined function: {node.name}")
        
        func = self.functions[node.name]
        args = []
        
        for i, arg_expr in enumerate(node.args):
            arg_val = self.visit(arg_expr)
            # Cast to expected parameter type if needed
            if i < len(func.args):
                expected_type = func.args[i].type
                arg_val = self._cast_if_needed(arg_val, expected_type)
            args.append(arg_val)
        
        return self.builder.call(func, args)
    
    def visit_ReturnNode(self, node):
        """Return statement"""
        if node.value is None:
            self.builder.ret_void()
        else:
            value = self.visit(node.value)
            ret_type = self.current_function.return_value.type
            value = self._cast_if_needed(value, ret_type)
            self.builder.ret(value)
    
    def visit_IfBlock(self, node):
        """If/else statement"""
        cond_value = self.visit(node.cond)
        cond_value = self._to_bool(cond_value)
        
        then_block = self.current_function.append_basic_block(name="if.then")
        else_block = self.current_function.append_basic_block(name="if.else")
        merge_block = self.current_function.append_basic_block(name="if.merge")
        
        self.builder.cbranch(cond_value, then_block, else_block)
        
        # Then block
        self.builder.position_at_end(then_block)
        for stmt in node.body:
            self.visit(stmt)
            if self.builder.block.is_terminated:
                break
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)
        
        # Else/elseif block
        self.builder.position_at_end(else_block)
        if node.elseif_blocks:
            for i, (elseif_cond, elseif_body) in enumerate(node.elseif_blocks):
                remaining_elseifs = node.elseif_blocks[i+1:] if i+1 < len(node.elseif_blocks) else []
                elseif_node = IfBlock(elseif_cond, elseif_body, remaining_elseifs, node.else_block)
                self.visit(elseif_node)
                break
        elif node.else_block:
            for stmt in node.else_block:
                self.visit(stmt)
                if self.builder.block.is_terminated:
                    break
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)
        
        # Merge block
        self.builder.position_at_end(merge_block)
    
    def _to_bool(self, value):
        """Convert value to boolean (i1)"""
        if isinstance(value.type, ir.IntType) and value.type.width == 1:
            return value
        elif isinstance(value.type, ir.IntType):
            return self.builder.icmp_signed('!=', value, ir.Constant(value.type, 0))
        elif isinstance(value.type, (ir.FloatType, ir.DoubleType)):
            return self.builder.fcmp_ordered('!=', value, ir.Constant(value.type, 0.0))
        return value
    
    def visit_WhileNode(self, node):
        """While loop"""
        cond_block = self.current_function.append_basic_block(name="while.cond")
        body_block = self.current_function.append_basic_block(name="while.body")
        exit_block = self.current_function.append_basic_block(name="while.exit")
        
        self.loop_exit_blocks.append(exit_block)
        self.loop_continue_blocks.append(cond_block)
        
        self.builder.branch(cond_block)
        
        # Condition block
        self.builder.position_at_end(cond_block)
        cond_value = self.visit(node.cond)
        cond_value = self._to_bool(cond_value)
        self.builder.cbranch(cond_value, body_block, exit_block)
        
        # Body block
        self.builder.position_at_end(body_block)
        for stmt in node.body:
            self.visit(stmt)
            if self.builder.block.is_terminated:
                break
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)
        
        # Exit block
        self.builder.position_at_end(exit_block)
        
        self.loop_exit_blocks.pop()
        self.loop_continue_blocks.pop()
    
    def visit_ForNode(self, node):
        """For-in loop (iterator style)"""
        # Evaluate iterable
        iterable_val = self.visit(node.iterable_expr)
        
        # For integers, treat as range(0, n)
        if isinstance(iterable_val.type, ir.IntType):
            end_val = iterable_val
        else:
            # For other types, would need runtime support
            end_val = ir.Constant(ir.IntType(32), 10)
        
        # Create loop variable
        loop_var = self.builder.alloca(ir.IntType(32), name=node.var_name)
        self.variables[node.var_name] = (loop_var, ir.IntType(32))
        self.builder.store(ir.Constant(ir.IntType(32), 0), loop_var)
        
        # Create blocks
        cond_block = self.current_function.append_basic_block(name="for.cond")
        body_block = self.current_function.append_basic_block(name="for.body")
        inc_block = self.current_function.append_basic_block(name="for.inc")
        exit_block = self.current_function.append_basic_block(name="for.exit")
        
        self.loop_exit_blocks.append(exit_block)
        self.loop_continue_blocks.append(inc_block)
        
        self.builder.branch(cond_block)
        
        # Condition
        self.builder.position_at_end(cond_block)
        current = self.builder.load(loop_var)
        cond = self.builder.icmp_signed('<', current, end_val)
        self.builder.cbranch(cond, body_block, exit_block)
        
        # Body
        self.builder.position_at_end(body_block)
        for stmt in node.body:
            self.visit(stmt)
            if self.builder.block.is_terminated:
                break
        if not self.builder.block.is_terminated:
            self.builder.branch(inc_block)
        
        # Increment
        self.builder.position_at_end(inc_block)
        current = self.builder.load(loop_var)
        next_val = self.builder.add(current, ir.Constant(ir.IntType(32), 1))
        self.builder.store(next_val, loop_var)
        self.builder.branch(cond_block)
        
        # Exit
        self.builder.position_at_end(exit_block)
        
        self.loop_exit_blocks.pop()
        self.loop_continue_blocks.pop()
    
    def visit_CStyleForNode(self, node):
        """C-style for loop"""
        # Initialize
        if node.init_stmt:
            self.visit(node.init_stmt)
        
        # Create blocks
        cond_block = self.current_function.append_basic_block(name="for.cond")
        body_block = self.current_function.append_basic_block(name="for.body")
        inc_block = self.current_function.append_basic_block(name="for.inc")
        exit_block = self.current_function.append_basic_block(name="for.exit")
        
        self.loop_exit_blocks.append(exit_block)
        self.loop_continue_blocks.append(inc_block)
        
        self.builder.branch(cond_block)
        
        # Condition
        self.builder.position_at_end(cond_block)
        if node.condition:
            cond = self.visit(node.condition)
            cond = self._to_bool(cond)
            self.builder.cbranch(cond, body_block, exit_block)
        else:
            self.builder.branch(body_block)
        
        # Body
        self.builder.position_at_end(body_block)
        for stmt in node.body:
            self.visit(stmt)
            if self.builder.block.is_terminated:
                break
        if not self.builder.block.is_terminated:
            self.builder.branch(inc_block)
        
        # Increment
        self.builder.position_at_end(inc_block)
        if node.increment:
            self.visit(node.increment)
        self.builder.branch(cond_block)
        
        # Exit
        self.builder.position_at_end(exit_block)
        
        self.loop_exit_blocks.pop()
        self.loop_continue_blocks.pop()
    
    def visit_SwitchNode(self, node):
        """Switch statement"""
        switch_val = self.visit(node.expr)
        
        # Create blocks
        case_blocks = []
        default_block = self.current_function.append_basic_block(name="switch.default")
        exit_block = self.current_function.append_basic_block(name="switch.exit")
        
        self.loop_exit_blocks.append(exit_block)  # For break
        
        # Create case blocks
        for i, (case_val, _) in enumerate(node.cases):
            case_blocks.append(self.current_function.append_basic_block(name=f"switch.case.{i}"))
        
        # Create switch instruction
        switch = self.builder.switch(switch_val, default_block)
        
        # Add cases
        for i, (case_val_node, case_body) in enumerate(node.cases):
            case_const = self.visit(case_val_node)
            switch.add_case(case_const, case_blocks[i])
            
            # Generate case body
            self.builder.position_at_end(case_blocks[i])
            for stmt in case_body:
                self.visit(stmt)
                if self.builder.block.is_terminated:
                    break
            if not self.builder.block.is_terminated:
                self.builder.branch(exit_block)
        
        # Default case
        self.builder.position_at_end(default_block)
        if node.default_case:
            for stmt in node.default_case:
                self.visit(stmt)
                if self.builder.block.is_terminated:
                    break
        if not self.builder.block.is_terminated:
            self.builder.branch(exit_block)
        
        # Exit
        self.builder.position_at_end(exit_block)
        self.loop_exit_blocks.pop()
    
    def visit_Break(self, node):
        """Break statement"""
        if not self.loop_exit_blocks:
            raise CompilerError("break outside of loop")
        self.builder.branch(self.loop_exit_blocks[-1])
    
    def visit_ContinueNode(self, node):
        """Continue statement"""
        if not self.loop_continue_blocks:
            raise CompilerError("continue outside of loop")
        self.builder.branch(self.loop_continue_blocks[-1])
    
    def visit_BinaryOp(self, node):
        """Binary operation"""
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        # Determine if float operation
        is_float = isinstance(left.type, (ir.FloatType, ir.DoubleType)) or \
                   isinstance(right.type, (ir.FloatType, ir.DoubleType))
        
        # Cast to common type if needed
        if is_float:
            if not isinstance(left.type, (ir.FloatType, ir.DoubleType)):
                left = self.builder.sitofp(left, ir.DoubleType())
            if not isinstance(right.type, (ir.FloatType, ir.DoubleType)):
                right = self.builder.sitofp(right, ir.DoubleType())
        
        # Arithmetic operations
        if node.op == '+':
            return self.builder.fadd(left, right) if is_float else self.builder.add(left, right)
        elif node.op == '-':
            return self.builder.fsub(left, right) if is_float else self.builder.sub(left, right)
        elif node.op == '*':
            return self.builder.fmul(left, right) if is_float else self.builder.mul(left, right)
        elif node.op == '/':
            return self.builder.fdiv(left, right) if is_float else self.builder.sdiv(left, right)
        elif node.op == '//':
            # Floor division
            if is_float:
                div = self.builder.fdiv(left, right)
                # Would need to call floor() intrinsic
                return div
            return self.builder.sdiv(left, right)
        elif node.op == '%':
            return self.builder.frem(left, right) if is_float else self.builder.srem(left, right)
        elif node.op == '**':
            # Power - would need pow intrinsic
            # Simplified: just multiply for now
            return self.builder.fmul(left, right) if is_float else self.builder.mul(left, right)
        
        # Comparison operations
        elif node.op == '==' or node.op == '===':
            return self.builder.fcmp_ordered('==', left, right) if is_float else \
                   self.builder.icmp_signed('==', left, right)
        elif node.op == '!=':
            return self.builder.fcmp_ordered('!=', left, right) if is_float else \
                   self.builder.icmp_signed('!=', left, right)
        elif node.op == '<':
            return self.builder.fcmp_ordered('<', left, right) if is_float else \
                   self.builder.icmp_signed('<', left, right)
        elif node.op == '>':
            return self.builder.fcmp_ordered('>', left, right) if is_float else \
                   self.builder.icmp_signed('>', left, right)
        elif node.op == '<=':
            return self.builder.fcmp_ordered('<=', left, right) if is_float else \
                   self.builder.icmp_signed('<=', left, right)
        elif node.op == '>=':
            return self.builder.fcmp_ordered('>=', left, right) if is_float else \
                   self.builder.icmp_signed('>=', left, right)
        
        # Logical operations
        elif node.op == '&&':
            left_bool = self._to_bool(left)
            right_bool = self._to_bool(right)
            return self.builder.and_(left_bool, right_bool)
        elif node.op == '||':
            left_bool = self._to_bool(left)
            right_bool = self._to_bool(right)
            return self.builder.or_(left_bool, right_bool)
        
        # Bitwise operations (only for integers)
        elif node.op == '&':
            return self.builder.and_(left, right)
        elif node.op == '|':
            return self.builder.or_(left, right)
        elif node.op == '^':
            return self.builder.xor(left, right)
        elif node.op == '<<':
            return self.builder.shl(left, right)
        elif node.op == '>>':
            return self.builder.ashr(left, right)
        elif node.op == 'in':
            # Membership check - simplified
            # Would need runtime support for real implementation
            return ir.Constant(ir.IntType(1), 0)
        
        else:
            raise CompilerError(f"Unknown binary operator: {node.op}")
    
    def visit_UnaryOp(self, node):
        """Unary operation"""
        expr = self.visit(node.expr)
        
        if node.op == '-':
            if isinstance(expr.type, (ir.FloatType, ir.DoubleType)):
                return self.builder.fneg(expr)
            return self.builder.neg(expr)
        elif node.op == '+':
            return expr
        elif node.op == '!':
            bool_val = self._to_bool(expr)
            return self.builder.not_(bool_val)
        else:
            raise CompilerError(f"Unknown unary operator: {node.op}")
    
    def visit_Literal(self, node):
        """Literal value"""
        if isinstance(node.value, bool):
            return ir.Constant(ir.IntType(1), int(node.value))
        elif isinstance(node.value, int):
            return ir.Constant(ir.IntType(32), node.value)
        elif isinstance(node.value, float):
            return ir.Constant(ir.DoubleType(), node.value)
        elif isinstance(node.value, str):
            return self.create_string_literal(node.value)
        elif node.value is None:
            return ir.Constant(ir.IntType(8).as_pointer(), None)
        else:
            return ir.Constant(ir.IntType(32), 0)
    
    def visit_Var(self, node):
        """Variable reference"""
        if node.name not in self.variables:
            raise CompilerError(f"Undefined variable: {node.name}")
        
        ptr, var_type = self.variables[node.name]
        return self.builder.load(ptr)
    
    def visit_ExprStmt(self, node):
        """Expression statement"""
        return self.visit(node.expr)
    
    def visit_ListLiteral(self, node):
        """List literal - allocate array"""
        if not node.items:
            # Empty list
            null_ptr = ir.Constant(ir.IntType(8).as_pointer(), None)
            return null_ptr
        
        # Determine element type
        elem_type = ir.IntType(32)
        if node.items:
            first_val = self.visit(node.items[0])
            elem_type = first_val.type
        
        # Allocate array
        array_size = len(node.items)
        array_type = ir.ArrayType(elem_type, array_size)
        array_ptr = self.builder.alloca(array_type, name="list")
        
        # Store elements
        for i, item in enumerate(node.items):
            val = self.visit(item)
            val = self._cast_if_needed(val, elem_type)
            
            idx = ir.Constant(ir.IntType(32), i)
            elem_ptr = self.builder.gep(array_ptr, [ir.Constant(ir.IntType(32), 0), idx])
            self.builder.store(val, elem_ptr)
        
        # Return pointer to first element
        zero = ir.Constant(ir.IntType(32), 0)
        return self.builder.gep(array_ptr, [zero, zero])
    
    def visit_TupleLiteral(self, node):
        """Tuple literal - similar to list but immutable"""
        # For LLVM, treat same as list (immutability is semantic)
        return self.visit(ListLiteral(node.items))
    
    def visit_DictLiteral(self, node):
        """Dictionary literal - allocate hash table structure"""
        # Simplified: allocate struct with keys and values arrays
        # Real implementation would need hash table runtime
        
        if not node.pairs:
            null_ptr = ir.Constant(ir.IntType(8).as_pointer(), None)
            return null_ptr
        
        # For now, just return a pointer
        # Full implementation would need runtime hash table support
        ptr_type = ir.IntType(8).as_pointer()
        size = ir.Constant(ir.IntType(64), 64)
        dict_ptr = self.builder.call(self.malloc, [size])
        
        return dict_ptr
    
    def visit_IndexAccess(self, node):
        """Array/list index access"""
        collection = self.visit(node.collection)
        index = self.visit(node.index)
        
        # Get element pointer
        elem_ptr = self.builder.gep(collection, [index])
        return self.builder.load(elem_ptr)
    
    def visit_PropertyAccess(self, node):
        """Property access (object.property)"""
        obj = self.visit(node.obj)
        
        # For classes, access struct field
        # Simplified implementation
        if isinstance(obj.type, ir.PointerType):
            # Would need to look up field index in class definition
            field_idx = 0  # Simplified
            field_ptr = self.builder.gep(obj, [ir.Constant(ir.IntType(32), 0), 
                                                ir.Constant(ir.IntType(32), field_idx)])
            return self.builder.load(field_ptr)
        
        raise CompilerError("Property access not fully supported yet")
    
    def visit_MethodCall(self, node):
        """Method call (object.method())"""
        receiver = self.visit(node.receiver)
        
        # Look up method in class
        # For now, treat as regular function call
        if node.method_name in self.functions:
            func = self.functions[node.method_name]
            args = [receiver]  # Add receiver as first argument
            
            for arg_expr in node.args:
                args.append(self.visit(arg_expr))
            
            return self.builder.call(func, args)
        
        raise CompilerError(f"Unknown method: {node.method_name}")
    
    def visit_LambdaFunc(self, node):
        """Lambda function - create anonymous function"""
        # Generate unique name
        lambda_name = f"lambda_{id(node)}"
        
        # Create function type
        ret_type = ir.IntType(32)  # Default
        param_types = [ir.IntType(32) for _ in node.params]
        
        func_ty = ir.FunctionType(ret_type, param_types)
        func = ir.Function(self.module, func_ty, name=lambda_name)
        
        # Save state
        prev_builder = self.builder
        prev_function = self.current_function
        prev_vars = self.variables.copy()
        
        # Build lambda body
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.current_function = func
        
        # Add parameters
        for param, arg in zip(node.params, func.args):
            arg.name = param
            ptr = self.builder.alloca(arg.type, name=param)
            self.builder.store(arg, ptr)
            self.variables[param] = (ptr, arg.type)
        
        # Visit body
        for stmt in node.body:
            self.visit(stmt)
            if self.builder.block.is_terminated:
                break
        
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(ret_type, 0))
        
        # Restore state
        self.builder = prev_builder
        self.current_function = prev_function
        self.variables = prev_vars
        
        # Return function pointer
        return func
    
    def visit_ClassDef(self, node):
        """Class definition"""
        if node.name not in self.classes:
            self._predeclare_class(node)
        
        class_info = self.classes[node.name]
        
        # Collect fields and methods
        fields = []
        methods = []
        
        for item in node.body:
            if isinstance(item, VarAssign):
                fields.append((item.name, self.get_llvm_type(item.vtype)))
            elif isinstance(item, FuncDef):
                methods.append(item)
        
        # Define struct type
        if fields:
            field_types = [ftype for _, ftype in fields]
            class_info['type'].set_body(*field_types)
        else:
            class_info['type'].set_body(ir.IntType(8))  # Dummy field
        
        # Store field info
        for i, (fname, ftype) in enumerate(fields):
            class_info['fields'][fname] = (i, ftype)
        
        # Define methods
        for method in methods:
            # Add 'this' parameter
            method_name = f"{node.name}_{method.name}"
            
            ret_type = self.get_llvm_type(method.return_type) if method.return_type else ir.IntType(32)
            param_types = [class_info['type'].as_pointer()] + [ir.IntType(32) for _ in method.params]
            
            func_ty = ir.FunctionType(ret_type, param_types)
            func = ir.Function(self.module, func_ty, name=method_name)
            
            class_info['methods'][method.name] = func
            
            # Build method
            prev_builder = self.builder
            prev_function = self.current_function
            prev_vars = self.variables.copy()
            
            block = func.append_basic_block(name="entry")
            self.builder = ir.IRBuilder(block)
            self.current_function = func
            
            # Store 'this' pointer
            this_ptr = self.builder.alloca(func.args[0].type, name="this")
            self.builder.store(func.args[0], this_ptr)
            self.variables['this'] = (this_ptr, func.args[0].type)
            
            # Store other parameters
            for param, arg in zip(method.params, func.args[1:]):
                arg.name = param
                ptr = self.builder.alloca(arg.type, name=param)
                self.builder.store(arg, ptr)
                self.variables[param] = (ptr, arg.type)
            
            # Visit method body
            for stmt in method.body:
                self.visit(stmt)
                if self.builder.block.is_terminated:
                    break
            
            if not self.builder.block.is_terminated:
                if isinstance(ret_type, ir.VoidType):
                    self.builder.ret_void()
                else:
                    self.builder.ret(ir.Constant(ret_type, 0))
            
            self.builder = prev_builder
            self.current_function = prev_function
            self.variables = prev_vars
    
    def visit_TryCatchNode(self, node):
        """Try-catch-finally statement"""
        # Simplified exception handling
        # Real implementation would use setjmp/longjmp or LLVM invoke/landingpad
        
        try_block = self.current_function.append_basic_block(name="try")
        catch_block = self.current_function.append_basic_block(name="catch")
        finally_block = self.current_function.append_basic_block(name="finally")
        exit_block = self.current_function.append_basic_block(name="try.exit")
        
        # Try block
        self.builder.branch(try_block)
        self.builder.position_at_end(try_block)
        
        for stmt in node.try_block:
            self.visit(stmt)
            if self.builder.block.is_terminated:
                break
        
        if not self.builder.block.is_terminated:
            self.builder.branch(finally_block)
        
        # Catch block (simplified - always skip)
        self.builder.position_at_end(catch_block)
        if node.catch_block:
            for stmt in node.catch_block:
                self.visit(stmt)
                if self.builder.block.is_terminated:
                    break
        if not self.builder.block.is_terminated:
            self.builder.branch(finally_block)
        
        # Finally block
        self.builder.position_at_end(finally_block)
        if node.finally_block:
            for stmt in node.finally_block:
                self.visit(stmt)
                if self.builder.block.is_terminated:
                    break
        if not self.builder.block.is_terminated:
            self.builder.branch(exit_block)
        
        # Exit
        self.builder.position_at_end(exit_block)
    
    def visit_ThrowNode(self, node):
        """Throw statement"""
        # Simplified: just branch to exception handler
        # Real implementation would use longjmp or LLVM exception handling
        
        value = self.visit(node.expr)
        
        # For now, just return error code
        if self.exception_handlers:
            self.builder.branch(self.exception_handlers[-1])
        else:
            # No handler, return error
            self.builder.ret(ir.Constant(ir.IntType(32), -1))
    
    def visit_ImportNode(self, node):
        """Import statement"""
        # Simplified: would need to compile and link other modules
        # For now, just declare external functions
        
        # Could look up symbols and declare them as external
        pass
    
    def visit_AwaitExpr(self, node):
        """Await expression - for async support"""
        # Simplified: just evaluate expression
        # Real async would need coroutine support
        return self.visit(node.expr)
    
    def execute(self, optimize=True, opt_level=3):
        """Execute the compiled module using JIT"""
        target = binding.Target.from_default_triple()
        target_machine = target.create_target_machine(opt=opt_level)
        
        llvm_ir = str(self.module)
        mod = binding.parse_assembly(llvm_ir)
        mod.verify()
        
        if optimize:
            pmb = binding.PassManagerBuilder()
            pmb.opt_level = opt_level
            pmb.size_level = 0
            pmb.inlining_threshold = 225
            
            pm = binding.ModulePassManager()
            pmb.populate(pm)
            pm.run(mod)
        
        engine = binding.create_mcjit_compiler(mod, target_machine)
        engine.finalize_object()
        
        func_ptr = engine.get_function_address("main")
        
        from ctypes import CFUNCTYPE, c_int
        cfunc = CFUNCTYPE(c_int)(func_ptr)
        result = cfunc()
        
        return result
    
    def save_to_file(self, output_path):
        with open(output_path, 'w') as f:
            f.write(str(self.module))
    
    def save_to_object(self, output_path):
        target = binding.Target.from_default_triple()
        target_machine = target.create_target_machine()
        
        llvm_ir = str(self.module)
        mod = binding.parse_assembly(llvm_ir)
        mod.verify()
        
        obj = target_machine.emit_object(mod)
        
        with open(output_path, 'wb') as f:
            f.write(obj)

    def save_to_assembly(self, output_path, opt_level=3):
        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()

        target = binding.Target.from_default_triple()
        target_machine = target.create_target_machine(opt=opt_level)

        llvm_ir = str(self.module)
        mod = binding.parse_assembly(llvm_ir)
        mod.verify()

        asm = target_machine.emit_assembly(mod)

        with open(output_path, "w") as f:
            f.write(asm)