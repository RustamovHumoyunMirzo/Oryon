import re
from oryon_token import Token

KEYWORDS = {
    'int', 'str', 'bool', 'float', 'double', 'long',
    'func', 'if', 'elseif', 'else', 'end', 'true', 'false', "null", 
    "void", "return", "switch", "def", "break", "case", "list", "tuple", "map",
    "for", "while", "in", "class", "this", "try", "catch", "finally", "private",
    "public", "throw", "continue", "inherits", "auto", "async", "await", "catchonly",
}

allowed_func_types = ("INT", "STR", "BOOL", "FLOAT", "DOUBLE", "LONG", "VOID", "ID", "LIST", "TUPLE", "MAP")
allowed_var_types = {"int", "str", "bool", "float", "double", "long", "list", "tuple", "map"}

TOKEN_SPEC = [
    ('SINGLELINE_COMMENT', r'//.*'),
    ('NUMBER',    r'\d+(\.\d*)?'),
    ('STRING',    r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\''),
    ('ARROW',     r'->'),
    ('DOT', r'\.'),
    ('OP', r'''
        === | == | != | <= | >= | \+\+ | -- | \+= | -= | \*= | /= | %= | \*\* | // | << | >> | && | \|\| | < | > | [+\-*/%=&|^!#]
    '''),
    ('ID',        r'[A-Za-z_][A-Za-z0-9_]*'),
    ('LPAREN',    r'\('),
    ('RPAREN',    r'\)'),
    ('COMMA',     r','),
    ('LBRACKET',  r'\['),
    ('RBRACKET',  r'\]'),
    ('LBRACE',    r'\{'),
    ('RBRACE',    r'\}'),
    ('COLON',     r':'),
    ('SEMICOLON', r';'),
    ('NEWLINE',   r'\n'),
    ('SKIP',      r'[ \t]+'),
    ('MISMATCH',  r'.'),
]

TOKEN_RE = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC),
    re.VERBOSE
)

class Lexer:
    def __init__(self, text):
        self.original_text = text
        self.text = self._remove_multiline_comments(text)
        self.tokens = []
        self.pos = 0
        self.line_starts = [0]
        for match in re.finditer(r'\n', self.text):
            self.line_starts.append(match.end())

    def _remove_multiline_comments(self, text):
        pattern = re.compile(r'/\*.*?\*/', re.DOTALL)
        cleaned = re.sub(pattern, '', text)

        if "/*" in cleaned and "*/" not in cleaned:
            raise Exception("Unterminated multi-line comment: missing closing '*/'")

        return cleaned
    
    def offset_to_line_col(self, offset):
        line_num = 0
        for i, start in enumerate(self.line_starts):
            if start > offset:
                break
            line_num = i
        col_num = offset - self.line_starts[line_num] + 1
        return line_num + 1, col_num
    
    def tokenize(self):
        for mo in TOKEN_RE.finditer(self.text):
            kind = mo.lastgroup
            value = mo.group()
            start = mo.start()

            if kind == 'SINGLELINE_COMMENT' or kind == 'SKIP':
                continue

            line, col = self.offset_to_line_col(start)

            if kind == 'NUMBER':
                if '.' in value:
                    tok = Token('FLOAT', float(value), line=line, col=col)
                else:
                    tok = Token('INT', int(value), line=line, col=col)
            elif kind == 'STRING':
                unescaped_str = bytes(value, "utf-8").decode("unicode_escape")
                tok = Token('STRING', unescaped_str, line=line, col=col)
            elif kind == 'ID':
                if value.lower() in KEYWORDS:
                    tok = Token(value.upper(), value.lower(), line=line, col=col)
                else:
                    tok = Token('ID', value, line=line, col=col)
            elif kind == 'OP':
                tok = Token('OP', value, line=line, col=col)
            elif kind == 'RBRACKET':
                tok = Token('RBRACKET', value, line=line, col=col)
            elif kind == 'LBRACKET':
                tok = Token('LBRACKET', value, line=line, col=col)
            elif kind == 'LBRACE':
                tok = Token('LBRACE', value, line=line, col=col)
            elif kind == 'RBRACE':
                tok = Token('RBRACE', value, line=line, col=col)
            elif kind == 'ARROW':
                tok = Token('ARROW', value, line=line, col=col)
            elif kind == 'LPAREN':
                tok = Token('LPAREN', value, line=line, col=col)
            elif kind == 'RPAREN':
                tok = Token('RPAREN', value, line=line, col=col)
            elif kind == 'COMMA':
                tok = Token('COMMA', value, line=line, col=col)
            elif kind == 'COLON':
                tok = Token('COLON', value, line=line, col=col)
            elif kind == 'SEMICOLON':
                tok = Token('SEMICOLON', value, line=line, col=col)
            elif kind == 'DOT':
                tok = Token('DOT', value, line=line, col=col)
            elif kind == 'NEWLINE':
                tok = Token('NEWLINE', value, line=line, col=col)
            elif kind == 'MISMATCH':
                raise Exception(f"Unexpected character {value!r} at line {line} column {col}")
            else:
                raise Exception(f"Unknown token kind {kind!r} at line {line} column {col}")

            self.tokens.append(tok)

        eof_line, eof_col = self.offset_to_line_col(len(self.text))
        self.tokens.append(Token('EOF', '', line=eof_line, col=eof_col))
        return self.tokens