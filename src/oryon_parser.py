from ast_nodes import *
from oryon_lexer import allowed_func_types, allowed_var_types

class ParserError(Exception):
    def __init__(self, message, token=None):
        if hasattr(token, "line") and hasattr(token, "col"):
            msg = f"{message} (Line {token.line}, Column {token.col})"
        else:
            msg = message
        super().__init__(msg)

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def peek(self, offset=0):
        pos = self.i + offset
        if 0 <= pos < len(self.tokens):
            return self.tokens[pos]
        return None

    def current(self):
        return self.peek(0)

    def advance(self):
        if self.i < len(self.tokens):
            self.i += 1

    def eat(self, type=None, value=None):
        tok = self.peek()
        if tok is None:
            raise ParserError("Unexpected end of input", tok)
        if type is not None and tok.type != type:
            raise ParserError(f"Expected {type}, got {tok.type}", tok)
        if value is not None and tok.value != value:
            raise ParserError(f"Expected token value {value}, got {tok.value}", tok)
        self.advance()
        return tok

    def skip_newlines(self):
        while True:
            p = self.peek()
            if p is None or p.type != "NEWLINE":
                break
            self.eat("NEWLINE")

    def parse(self):
        statements = []
        self.skip_newlines()
        while True:
            p = self.peek()
            if p is None or p.type == "EOF":
                break
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
            self.skip_newlines()
        return Program(statements)
    
    def is_expr_start(self, tok):
        if tok is None:
            return False
        return tok.type in ("ID", "INT", "FLOAT", "STRING", "TRUE", "FALSE", "NULL", "LPAREN", "LBRACKET", "LBRACE", "FUNC") or \
               (tok.type == "OP" and tok.value in ("+", "-", "!"))
    
    def is_assignable(self, node):
        if type(node).__name__ == "PropertyAccess":
            return True
        return isinstance(node, (Var, PropertyAccess, IndexAccess))

    def statement(self):
        self.skip_newlines()
        tok = self.peek()
        privacy = False
        if tok is None:
            return None
        
        if tok.type == "ASYNC" and self.peek(1) and self.peek(1).type == "FUNC":
            self.eat("ASYNC")
            return self.func_def(privacy=False, is_async=True)
        
        if tok.type in ("PUBLIC", "PRIVATE") and \
        self.peek(1) and self.peek(1).type == "ASYNC":
            privacy_tok = self.eat(tok.type)
            privacy = (privacy_tok.type == "PRIVATE")
            self.eat("ASYNC")
            return self.func_def(privacy=privacy, is_async=True)
        
        if tok.type == "ID" and tok.value == "import":
            return self.parse_import()
        
        if tok.type == "TRY":
            return self.parse_try_catch_finally()

        if tok.type == "THROW":
            return self.throw_stmt()
        
        if tok.type in ("PUBLIC", "PRIVATE") and self.peek(1) and self.peek(1).type == "CLASS":
            privacy_tok = self.eat(tok.type)
            privacy = (privacy_tok.type == "PRIVATE")
            return self.class_def(privacy=privacy)

        if tok.type == "CLASS":
            return self.class_def(privacy=False)

        if tok.type == "WHILE":
            return self.while_stmt()

        if tok.type == "FOR":
            return self.for_stmt()

        if tok.type == "SWITCH":
            return self.switch_stmt()

        if tok.type == "BREAK":
            self.eat("BREAK")
            return Break()

        if tok.type == "CONTINUE":
            self.eat("CONTINUE")
            return ContinueNode()

        if tok.type in ("END", "ELSE", "ELSEIF", "CATCHONLY", "CATCH", "FINALLY"):
            return None

        if tok.type == "RETURN":
            return self.return_stmt()
        
        if tok.type in ("PUBLIC", "PRIVATE") and self.peek(1) and self.peek(1).type == "FUNC":
            privacy_tok = self.eat(tok.type)
            privacy = (privacy_tok.type == "PRIVATE")
            return self.func_def(privacy=privacy)
        
        if tok.type in ("PUBLIC", "PRIVATE"):
            privacy_tok = self.eat(tok.type)
            privacy = (privacy_tok.type == "PRIVATE")

            next_tok = self.peek()
            if next_tok is None or next_tok.type not in ("INT", "STR", "BOOL", "FLOAT", "DOUBLE", "LONG", "LIST", "TUPLE", "MAP", "AUTO", "ID"):
                raise ParserError("Expected variable type after privacy modifier", next_tok)

            return self.var_decl(privacy=privacy)

        if tok.type in ("INT", "STR", "BOOL", "FLOAT", "DOUBLE", "LONG", "LIST", "TUPLE", "MAP", "AUTO"):
            return self.var_decl(privacy=False)

        if tok.type == "FUNC":
            return self.func_def(privacy=False)

        if tok.type == "IF":
            return self.if_block()

        if tok.type == "ID" and self._lookahead_is_op(("++", "--")):
            return self.inc_dec()
        
        if tok.type == "ID":
            next_tok = self.peek(1)
            if next_tok and next_tok.type == "ID":
                vtype = self.eat("ID").value
                name = self.eat("ID").value
                if self.peek() and self.peek().type == "OP" and self.peek().value == "=":
                    self.eat("OP")
                    value = self.expr()
                    return VarAssign(vtype, name, value, private=privacy)
                else:
                    return VarAssign(vtype, name, None, private=privacy)

        if tok.type in ("ID", "LPAREN", "LBRACKET", "FUNC", "THIS"):
            expr = self.expr()
            if self.peek() and self.peek().type == "OP" and self.peek().value in ("=", "+=", "-=", "*=", "/=", "%="):
                op = self.eat("OP").value
                value = self.expr()
                if not self.is_assignable(expr):
                    raise ParserError(f"Unsupported assignment target type {type(expr)}", tok)
                return VarSetExpr(expr, value, op)

            return ExprStmt(expr)

        if tok.type == "LPAREN":
            expr = self.expr()
            return ExprStmt(expr)
        
        if tok.type == "AWAIT":
            expr = self.expr()
            return ExprStmt(expr)

        raise ParserError(f"Unknown statement: {tok.value}", tok)

    def _lookahead_is_op(self, values):
        nxt = self.peek(1)
        return bool(nxt and nxt.type == "OP" and nxt.value in values)

    def return_stmt(self):
        self.eat("RETURN")
        value = None
        nxt = self.peek()
        if nxt and nxt.type not in ("NEWLINE", "END", "EOF"):
            value = self.expr()
        return ReturnNode(value)

    def var_decl(self, privacy=False):
        type_token = self.eat(self.peek().type)
        vtype = type_token.value

        if vtype.lower() in allowed_var_types:
            pass
        else:
            pass

        name = self.eat("ID").value

        if not (self.peek() and self.peek().type == "OP" and self.peek().value == "="):
            raise ParserError("Expected '=' after variable declaration", type_token)

        self.eat("OP")
        value = self.expr()

        return VarAssign(vtype, name, value, privacy)

    def var_set(self):
        name = self.eat("ID").value
        op = self.eat("OP").value
        value = self.expr()
        return VarSet(name, value, op)

    def func_def(self, privacy=False, is_async=False):
        self.eat("FUNC")
        name = self.eat("ID").value

        self.eat("LPAREN")
        params = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF in function parameter list", name)
            if p.type == "RPAREN":
                break
            params.append(self.eat("ID").value)
            if self.peek() and self.peek().type == "COMMA":
                self.eat("COMMA")
            else:
                break
        self.eat("RPAREN")

        self.eat("ARROW")

        if not self.peek():
            raise ParserError("Unexpected EOF after function arrow", name)

        if self.peek().type not in allowed_func_types:
            raise ParserError(f"Invalid return type '{self.peek().value}'", name)

        return_type = self.eat().value

        body = []
        self.skip_newlines()

        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF in function body", name)
            if p.type == "END":
                break

            stmt = self.statement()
            if stmt is None:
                self.skip_newlines()
                continue
            body.append(stmt)

        self.eat("END")
        return FuncDef(name, params, body, return_type, private=privacy, is_async=is_async)

    def if_block(self):
        tok = self.eat("IF")
        cond = self.expr()
        self.eat("ARROW")
        self.skip_newlines()

        body = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF in if block", tok)
            if p.type in ("ELSEIF", "ELSE", "END"):
                break
            stmt = self.statement()
            if stmt is not None:
                body.append(stmt)

        elseif_blocks = []
        while self.peek() and self.peek().type == "ELSEIF":
            elseiftok = self.eat("ELSEIF")
            cond2 = self.expr()
            self.eat("ARROW")
            self.skip_newlines()
            body2 = []
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF in elseif block", elseiftok)
                if p.type in ("ELSEIF", "ELSE", "END"):
                    break
                stmt = self.statement()
                if stmt is not None:
                    body2.append(stmt)
            elseif_blocks.append((cond2, body2))

        else_block = None
        if self.peek() and self.peek().type == "ELSE":
            elsetok = self.eat("ELSE")
            self.eat("ARROW")
            self.skip_newlines()
            else_body = []
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF in else block", elsetok)
                if p.type == "END":
                    break
                stmt = self.statement()
                if stmt is not None:
                    else_body.append(stmt)
            else_block = else_body

        self.eat("END")
        return IfBlock(cond, body, elseif_blocks, else_block)

    def func_call(self):
        tok = self.eat("ID")
        name = tok.value
        self.eat("LPAREN")
        args = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF in function call", tok)
            if p.type == "RPAREN":
                break
            args.append(self.expr())
            if self.peek() and self.peek().type == "COMMA":
                self.eat("COMMA")
                continue
            else:
                break
        self.eat("RPAREN")
        return FuncCall(name, args)

    def inc_dec(self):
        name = self.eat("ID").value
        op = self.eat("OP").value
        if op == "++":
            return VarSet(name, BinaryOp(Var(name), "+", Literal(1)), "=")
        else:
            return VarSet(name, BinaryOp(Var(name), "-", Literal(1)), "=")

    def expr(self):
        return self.logical_or()

    def logical_or(self):
        left = self.logical_and()
        while self.peek() and self.peek().type == "OP" and self.peek().value == "||":
            op = self.eat("OP").value
            right = self.logical_and()
            left = BinaryOp(left, op, right)
        return left

    def logical_and(self):
        left = self.membership()
        while self.peek() and self.peek().type == "OP" and self.peek().value == "&&":
            op = self.eat("OP").value
            right = self.membership()
            left = BinaryOp(left, op, right)
        return left

    def membership(self):
        left = self.equality()
        while self.peek() and self.peek().type == "IN":
            self.eat("IN")
            right = self.equality()
            left = BinaryOp(left, "in", right)
        return left

    def equality(self):
        left = self.comparison()
        while self.peek() and self.peek().type == "OP" and self.peek().value in ("==", "!=", "==="):
            op = self.eat("OP").value
            right = self.comparison()
            left = BinaryOp(left, op, right)
        return left

    def comparison(self):
        left = self.arith_expr()
        while self.peek() and self.peek().type == "OP" and self.peek().value in ("<", ">", "<=", ">="):
            op = self.eat("OP").value
            right = self.arith_expr()
            left = BinaryOp(left, op, right)
        return left

    def bit_ops(self):
        left = self.arith_term()
        while self.peek() and self.peek().type == "OP" and self.peek().value in ("&", "|", "^", "<<", ">>"):
            op = self.eat("OP").value
            right = self.arith_term()
            left = BinaryOp(left, op, right)
        return left

    def arith_expr(self):
        left = self.bit_ops()
        while self.peek() and self.peek().type == "OP" and self.peek().value in ("+", "-"):
            op = self.eat("OP").value
            right = self.bit_ops()
            left = BinaryOp(left, op, right)
        return left

    def arith_term(self):
        left = self.factor()
        while self.peek() and self.peek().type == "OP" and self.peek().value in ("*", "/", "//", "%"):
            op = self.eat("OP").value
            right = self.factor()
            left = BinaryOp(left, op, right)
        return left

    def factor(self):
        tok = self.peek()
        if tok and tok.type == "AWAIT":
            self.eat("AWAIT")
            expr = self.factor()
            return AwaitExpr(expr)

        if tok and tok.type == "OP" and tok.value in ("+", "-", "!"):
            op = self.eat("OP").value
            return UnaryOp(op, self.factor())

        node = self.atom()
        while self.peek() and self.peek().type == "OP" and self.peek().value == "**":
            op = self.eat("OP").value
            right = self.factor()
            node = BinaryOp(node, op, right)
        return node

    def atom(self):
        tok = self.peek()
        if tok is None:
            raise ParserError("Unexpected end of input in expression", tok)

        node = None

        if tok.type == "LBRACKET":
            self.eat("LBRACKET")
            items = []
            if not (self.peek() and self.peek().type == "RBRACKET"):
                while True:
                    items.append(self.expr())
                    if self.peek() and self.peek().type == "COMMA":
                        self.eat("COMMA")
                        continue
                    break
            self.eat("RBRACKET")
            node = ListLiteral(items)

        elif tok.type == "LBRACE":
            self.eat("LBRACE")
            pairs = []
            self.skip_newlines()
            if not (self.peek() and self.peek().type == "RBRACE"):
                while True:
                    self.skip_newlines()
                    key = self.expr()
                    self.eat("COLON")
                    self.skip_newlines()
                    val = self.expr()
                    pairs.append((key, val))
                    self.skip_newlines()
                    if self.peek() and self.peek().type == "COMMA":
                        self.eat("COMMA")
                        continue
                    break
            self.skip_newlines()
            self.eat("RBRACE")
            node = DictLiteral(pairs)

        elif tok.type == "INT":
            val = int(self.eat("INT").value)
            node = Literal(val)

        elif tok.type == "FLOAT":
            val = float(self.eat("FLOAT").value)
            node = Literal(val)

        elif tok.type == "STRING":
            val = self.eat("STRING").value
            node = Literal(val[1:-1])

        elif tok.type in ("TRUE", "FALSE"):
            val = (tok.type == "TRUE")
            self.eat(tok.type)
            node = Literal(val)

        elif tok.type == "NULL":
            self.eat("NULL")
            node = Literal(None)

        elif tok.type == "ID":
            next_tok = self.peek(1)
            if next_tok and next_tok.type == "LPAREN":
                node = self.func_call()
            else:
                node = Var(self.eat("ID").value)

        elif tok.type == "LPAREN":
            self.eat("LPAREN")
            if self.peek() and self.peek().type == "RPAREN":
                self.eat("RPAREN")
                node = TupleLiteral([])
            else:
                first = self.expr()
                if self.peek() and self.peek().type == "COMMA":
                    items = [first]
                    while self.peek() and self.peek().type == "COMMA":
                        self.eat("COMMA")
                        if self.peek() and self.peek().type == "RPAREN":
                            break
                        items.append(self.expr())
                    self.eat("RPAREN")
                    node = TupleLiteral(items)
                else:
                    self.eat("RPAREN")
                    node = first

        elif tok.type == "FUNC":
            self.eat("FUNC")
            self.eat("LPAREN")

            params = []
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF in lambda params", tok)
                if p.type == "RPAREN":
                    break
                params.append(self.eat("ID").value)
                if self.peek() and self.peek().type == "COMMA":
                    self.eat("COMMA")
                else:
                    break
                
            self.eat("RPAREN")
            self.eat("ARROW")
            self.skip_newlines()

            body = []
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF in lambda body", tok)
                if p.type == "END":
                    break
                stmt = self.statement()
                if stmt is None:
                    self.skip_newlines()
                    continue
                body.append(stmt)
            self.eat("END")

            return LambdaFunc(params, body)

        elif tok.type == "ASYNC":
            self.eat("ASYNC")
            if not (self.peek() and self.peek().type == "FUNC"):
                raise ParserError("Expected 'func' after 'async' in lambda expression", tok)

            self.eat("FUNC")
            self.eat("LPAREN")

            params = []
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF in async lambda params", tok)
                if p.type == "RPAREN":
                    break
                params.append(self.eat("ID").value)
                if self.peek() and self.peek().type == "COMMA":
                    self.eat("COMMA")
                else:
                    break
                
            self.eat("RPAREN")
            self.eat("ARROW")
            self.skip_newlines()

            body = []
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF in async lambda body", tok)
                if p.type == "END":
                    break
                stmt = self.statement()
                if stmt is None:
                    self.skip_newlines()
                    continue
                body.append(stmt)
            self.eat("END")

            lambda_func = LambdaFunc(params, body)
            lambda_func.is_async = True
            return lambda_func
        
        elif tok.type == "THIS":
            self.eat("THIS")
            node = Var("this")

        elif tok.type == "SUPER":
            self.eat("SUPER")
            node = Var("super")

        else:
            raise ParserError(f"Invalid expression starting with {tok.type}({tok.value})", tok)

        while True:
            p = self.peek()
            if p and p.type == "LBRACKET":
                self.eat("LBRACKET")
                index_expr = self.expr()
                self.eat("RBRACKET")
                node = IndexAccess(node, index_expr)
            elif p and p.type == "DOT":
                self.eat("DOT")
                attr_name_tok = self.peek()
                type_token_to_property = {
                    "INT": "Integer",
                    "FLOAT": "Float", 
                    "DOUBLE": "Double",
                    "LONG": "Long",
                    "STR": "String",
                    "BOOL": "Bool",
                    "LIST": "List",
                    "TUPLE": "Tuple",
                    "MAP": "Map",
                    "AUTO": "Auto"
                }
                if attr_name_tok.type == "ID":
                    attr_name = self.eat("ID").value
                elif attr_name_tok.type in type_token_to_property:
                    self.eat(attr_name_tok.type)
                    attr_name = type_token_to_property[attr_name_tok.type]
                else:
                    raise ParserError(f"Expected property name after '.', got {attr_name_tok.type}", attr_name_tok)
                
                if self.peek() and self.peek().type == "LPAREN":
                    self.eat("LPAREN")
                    args = []
                    if not (self.peek() and self.peek().type == "RPAREN"):
                        while True:
                            args.append(self.expr())
                            if self.peek() and self.peek().type == "COMMA":
                                self.eat("COMMA")
                                continue
                            break
                    self.eat("RPAREN")
                    node = MethodCall(node, attr_name, args)
                else:
                    node = PropertyAccess(node, attr_name)
            else:
                break

        return node

    def switch_stmt(self):
        self.eat("SWITCH")
        self.eat("LPAREN")
        switch_expr = self.expr()
        self.eat("RPAREN")
        self.eat("ARROW")
        self.skip_newlines()
        cases, default_block = self.switch_block()
        self.eat("END")
        return SwitchNode(switch_expr, cases, default_block)

    def switch_block(self):
        cases = []
        default_block = None
        while True:
            self.skip_newlines()
            tok = self.peek()
            if tok is None:
                break

            if tok.type == "CASE":
                self.eat("CASE")
                case_value = self.expr()
                self.eat("COLON")
                case_body = []
                while True:
                    nxt = self.peek()
                    if nxt is None or nxt.type in ("CASE", "DEF", "END"):
                        break
                    if nxt.type == "NEWLINE":
                        self.eat("NEWLINE")
                        continue
                    stmt = self.statement()
                    if stmt is not None:
                        case_body.append(stmt)
                cases.append((case_value, case_body))

            elif tok.type == "DEF":
                self.eat("DEF")
                self.eat("COLON")
                default_body = []
                while True:
                    nxt = self.peek()
                    if nxt is None or nxt.type == "END":
                        break
                    if nxt.type == "NEWLINE":
                        self.eat("NEWLINE")
                        continue
                    stmt = self.statement()
                    if stmt is not None:
                        default_body.append(stmt)
                default_block = default_body
                break

            elif tok.type == "END":
                break

            else:
                raise ParserError(f"Expected 'case' or 'def' inside switch but got {tok.type}", tok)

        return cases, default_block

    def while_stmt(self):
        tok = self.eat("WHILE")
        self.eat("LPAREN")
        condition = self.expr()
        self.eat("RPAREN")
        self.eat("ARROW")
        self.skip_newlines()

        body = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF in while body", tok)
            if p.type == "END":
                break
            stmt = self.statement()
            if stmt is not None:
                body.append(stmt)
        self.eat("END")
        return WhileNode(condition, body)

    def for_stmt(self):
        tok = self.eat("FOR")
        self.eat("LPAREN")
        try:
            peek_ahead = 0
            found_semicolon = False
            paren_depth = 0

            while self.pos + peek_ahead < len(self.tokens):
                peek_tok = self.tokens[self.pos + peek_ahead]
                if peek_tok.type == "LPAREN":
                    paren_depth += 1
                elif peek_tok.type == "RPAREN":
                    if paren_depth == 0:
                        break
                    paren_depth -= 1
                elif peek_tok.type == "SEMICOLON" and paren_depth == 0:
                    found_semicolon = True
                    break
                elif peek_tok.type == "IN" and paren_depth == 0:
                    found_semicolon = False
                    break
                peek_ahead += 1

            if found_semicolon:
                return self._parse_c_style_for(tok)
            else:
                return self._parse_iterator_for(tok)

        except Exception as e:
            try:
                return self._parse_iterator_for(tok)
            except:
                return self._parse_c_style_for(tok)

    def _parse_iterator_for(self, tok):
        var_name = self.eat("ID").value
        self.eat("IN")
        iterable = self.expr()
        self.eat("RPAREN")
        self.eat("ARROW")
        self.skip_newlines()

        body = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF in for body", tok)
            if p.type == "END":
                break
            stmt = self.statement()
            if stmt is not None:
                body.append(stmt)
        self.eat("END")
        return ForNode(var_name, iterable, body)

    def _parse_c_style_for(self, tok):
        init_stmt = None
        condition = None
        increment = None

        if self.peek() and self.peek().type not in ("SEMICOLON", "RPAREN"):
            if self.peek().type in ["INT", "FLOAT", "STR", "BOOL", "LONG", "DOUBLE", "AUTO", "LIST", "TUPLE", "MAP"]:
                init_stmt = self.var_decl(privacy=False)
            elif self.peek().type == "ID" and self.peek(1) and \
                 self.peek(1).type == "OP" and self.peek(1).value in ("++", "--"):
                init_stmt = self.inc_dec()
            else:
                init_stmt = ExprStmt(self.expr())

        if self.peek() and self.peek().type == "SEMICOLON":
            self.eat("SEMICOLON")
            if self.peek() and self.peek().type not in ("SEMICOLON", "RPAREN"):
                condition = self.expr()

        if self.peek() and self.peek().type == "SEMICOLON":
            self.eat("SEMICOLON")
            if self.peek() and self.peek().type != "RPAREN":
                if self.peek().type == "ID" and self.peek(1) and \
                   self.peek(1).type == "OP" and self.peek(1).value in ("++", "--"):
                    name = self.eat("ID").value
                    op = self.eat("OP").value
                    delta = 1 if op == "++" else -1
                    increment = VarSet(name, BinaryOp(Var(name), "+", Literal(delta)), "=")
                else:
                    increment = self.expr()

        self.eat("RPAREN")
        self.eat("ARROW")
        self.skip_newlines()

        body = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF in for body", tok)
            if p.type == "END":
                break
            stmt = self.statement()
            if stmt:
                body.append(stmt)

        self.eat("END")

        return CStyleForNode(init_stmt, condition, increment, body)
    
    def _looks_like_method(self):
        if not self.peek() or self.peek().type != "ID":
            return False
        if self.peek(1) and self.peek(1).type == "LPAREN":
            i = self.i + 2
            depth = 1
            while i < len(self.tokens):
                tok = self.tokens[i]
                if tok.type == "LPAREN":
                    depth += 1
                elif tok.type == "RPAREN":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            if depth != 0:
                return False
            return (i + 1 < len(self.tokens) and self.tokens[i + 1].type == "ARROW")
        elif self.peek(1) and self.peek(1).type == "ARROW":
            return True
        return False

    def method_def(self, privacy=False):
        name = self.eat("ID").value

        params = []
        if self.peek() and self.peek().type == "LPAREN":
            self.eat("LPAREN")
            while True:
                if self.peek().type == "RPAREN":
                    break
                param = self.eat("ID").value
                params.append(param)
                if self.peek().type == "COMMA":
                    self.eat("COMMA")
                    if self.peek().type == "RPAREN":
                        break
                else:
                    break
            self.eat("RPAREN")

        self.eat("ARROW")
        self.skip_newlines()

        body = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF in method body", name)
            if p.type == "END":
                break

            stmt = self.statement()
            if stmt is None:
                self.skip_newlines()
                continue
            body.append(stmt)

        self.eat("END")
        return FuncDef(name, params, body, return_type=None, private=privacy)

    def class_def(self, privacy=False):
        self.eat("CLASS")
        name = self.eat("ID").value
    
        superclass = None
    
        if self.peek() and self.peek().type == "INHERITS":
            self.eat("INHERITS")
            superclass = self.eat("ID").value
    
        self.eat("ARROW")
    
        self.skip_newlines()
    
        body = []
    
        while self.peek() and self.peek().type != "END":
            tok = self.peek()
    
            if tok.type in ("PUBLIC", "PRIVATE") and \
               self.peek(1) and self.peek(1).type == "ID" and \
               self.peek(2) and self.peek(2).type == "LPAREN":
    
                priv_tok = self.eat(tok.type)
                priv = (priv_tok.type == "PRIVATE")
    
                m = self.method_def(privacy=priv)
                m.is_class_method = True
                body.append(m)
                self.skip_newlines()
                continue
            
            if self._looks_like_method():
                m = self.method_def(privacy=False)
                m.is_class_method = True
                body.append(m)
                self.skip_newlines()
                continue
            
            if tok.type in ("PUBLIC", "PRIVATE") and \
               self.peek(1) and self.peek(1).type in (
                   "INT", "STR", "BOOL", "FLOAT", "DOUBLE", "LONG",
                   "LIST", "TUPLE", "MAP"
               ):
    
                priv_tok = self.eat(tok.type)
                priv = (priv_tok.type == "PRIVATE")
    
                field = self.var_decl(privacy=priv)
                field.is_class_field = True
                body.append(field)
                self.skip_newlines()
                continue
            
            if tok.type in (
                "INT", "STR", "BOOL", "FLOAT", "DOUBLE", "LONG",
                "LIST", "TUPLE", "MAP"
            ):
    
                field = self.var_decl(privacy=False)
                field.is_class_field = True
                body.append(field)
                self.skip_newlines()
                continue
            
            stmt = self.statement()
            if stmt:
                body.append(stmt)
                self.skip_newlines()
                continue
            
            self.advance()
    
        self.eat("END")
        return ClassDef(name, body, privacy, superclass)
    
    def parse_try_catch_finally(self):
        multistmt = False
        trytok = self.eat("TRY")
        self.eat("ARROW")
        self.skip_newlines()

        try_body = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF inside try block")
            if p.type in ("CATCHONLY", "CATCH", "FINALLY", "END"):
                break
            stmt = self.statement()
            if stmt is not None:
                try_body.append(stmt)

        catchonly = []

        while True:
            if self.peek().type == "CATCHONLY":
                self.eat("CATCHONLY")
                multistmt = True
                self.eat("LPAREN")
                catchonly_var = None
                catchonly_vartype = None
                catchonly_type = None
                catchonly_body = []
                if self.peek() and self.peek().type == "ID":
                    catchonly_var = self.eat("ID").value
                    if self.peek() and self.peek().type == "COMMA":
                        self.eat("COMMA")
                        catchonly_vartype = self.eat("ID").value
                self.eat("RPAREN")
                self.eat("ARROW")
                catchonly_type = self.expr()
                self.skip_newlines()
                while True:
                    p = self.peek()
                    if p is None:
                        raise ParserError("Unexpected EOF in catchonly block")
                    if p.type in ("CATCHONLY", "CATCH", "FINALLY", "END"):
                        break
                    stmt = self.statement()
                    if stmt:
                        catchonly_body.append(stmt)
                catchonly.append((catchonly_var, catchonly_vartype, catchonly_type, catchonly_body))
            else:
                break

        catch_var = None
        catch_type = None
        catch_body = []

        if self.peek().type == "CATCH":
            self.eat("CATCH")
            multistmt = True
            self.eat("LPAREN")
            if self.peek() and self.peek().type == "ID":
                catch_var = self.eat("ID").value
                if self.peek() and self.peek().type == "COMMA":
                    self.eat("COMMA")
                    catch_type = self.eat("ID").value
            self.eat("RPAREN")
            self.eat("ARROW")
            self.skip_newlines()
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF in catch block")
                if p.type in ("FINALLY", "END"):
                    break
                stmt = self.statement()
                if stmt:
                    catch_body.append(stmt)

        finally_body = []

        if self.peek().type == "FINALLY":
            self.eat("FINALLY")
            multistmt = True
            self.eat("ARROW")
            self.skip_newlines()
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF in finally block")
                if p.type == "END":
                    break
                stmt = self.statement()
                if stmt:
                    finally_body.append(stmt)

        self.eat("END")

        if not multistmt:
            raise ParserError("Empty statement body", trytok)

        return TryCatchNode(try_body, catch_var, catch_type, catch_body, finally_body, catchonly)
    
    def parse_import(self):
        import_tok = self.eat("ID")
        if not (self.peek() and self.peek().type == "OP" and self.peek().value == "<"):
            raise ParserError("Expected '<' after import", self.peek())
        self.eat("OP", "<")

        import_type = 0
        if self.peek() and self.peek().type == "OP" and self.peek().value == "#":
            import_type = 1
            self.eat("OP", "#")

        path_parts = []
        while True:
            p = self.peek()
            if p is None:
                raise ParserError("Unexpected EOF while parsing import path (missing '>')", p)
            if p.type == "OP" and p.value == ">":
                break
            if p.type == "NEWLINE":
                raise ParserError("Newline not allowed inside import path", p)
            path_parts.append(p.value)
            self.advance()
        self.eat("OP", ">")

        raw_path = ''.join(path_parts).strip()
        if raw_path == "":
            raise ParserError("Empty import path", import_tok)

        symbols = None
        self.skip_newlines()
        if self.peek() and self.peek().type == "OP" and self.peek().value == "<":
            self.eat("OP", "<")
            syms = []
            while True:
                p = self.peek()
                if p is None:
                    raise ParserError("Unexpected EOF while parsing import symbols (missing '>')", p)
                if p.type == "OP" and p.value == ">":
                    break
                if p.type == "NEWLINE":
                    raise ParserError("Newline not allowed inside selective import list", p)
                if p.type == "COMMA":
                    self.eat("COMMA")
                    continue
                if p.type == "ID":
                    syms.append(self.eat("ID").value)
                elif p.type == "OP" and p.value == "*":
                    self.eat("OP", "*")
                    syms.append("*")
                else:
                    raise ParserError("Expected identifier or '*' in selective import list", p)
            self.eat("OP", ">")
            symbols = syms

        return ImportNode(raw_path, symbols, import_type)

    def throw_stmt(self):
        self.eat("THROW")
        value = self.expr()
        error_type = "Exception"
        if self.peek() and self.peek().type == "ARROW":
            self.eat("ARROW")
            error_type = self.expr()
        return ThrowNode(value, error_type)