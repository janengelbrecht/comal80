import sys
import os
import re
import math
import time
import random
import tempfile
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Tuple, Callable

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QTreeWidget, QTreeWidgetItem,
    QToolBar, QStatusBar, QFileDialog, QMessageBox
)
from PySide6.QtGui import (
    QTextCursor, QFont, QColor, QPainter, QPen, QBrush, QPixmap,
    QAction, QKeySequence, QTextCharFormat
)
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF

COMAL80_VERSION = "1.1"


# ============================================================================
# DEL 1: TOKENS OG LEKSIKALSK ANALYSE (LEXER)
# ============================================================================

KEYWORDS = {
    'IF', 'THEN', 'ELIF', 'ELSE', 'ENDIF',
    'CASE', 'OF', 'WHEN', 'OTHERWISE', 'ENDCASE',
    'FOR', 'TO', 'STEP', 'DO', 'ENDFOR',
    'WHILE', 'ENDWHILE',
    'REPEAT', 'UNTIL',
    'LOOP', 'ENDLOOP', 'EXIT',
    'TRAP', 'ESC', 'HANDLER', 'ENDTRAP',
    'PROC', 'ENDPROC', 'EXEC',
    'FUNC', 'ENDFUNC', 'RETURN',
    'CLOSED', 'IMPORT', 'GLOBAL', 'REF', 'NAME',
    'DIM', 'DATA', 'READ', 'RESTORE', 'NULL',
    'PRINT', 'INPUT', 'USING', 'AT', 'CURSOR', 'ZONE', 'PAGE',
    'OPEN', 'CLOSE', 'FILE', 'WRITE', 'APPEND', 'RANDOM',
    'SELECT', 'OUTPUT',
    'AND', 'OR', 'EOR', 'XOR', 'NOT', 'MOD', 'DIV', 'IN',
    'GOTO', 'REM', 'END', 'STOP', 'CON',
    'DEL', 'DIR', 'CAT', 'PASS', 'RANDOMIZE',
    'TRACE', 'ON', 'OFF'
}


@dataclass
class Token:
    type: str
    value: Any
    line: int
    column: int
    raw_line: int = 1


class ComalError(Exception):
    def __init__(self, kind: str, message: str, line: Optional[int] = None,
                 column: Optional[int] = None, code: int = 1):
        self.kind = kind
        self.raw_message = message
        self.line = line
        self.column = column
        self.code = code
        loc = f" i linje {line}" if line is not None and line > 0 else ""
        col = f", kolonne {column}" if column is not None and column > 0 else ""
        super().__init__(f"{kind}{loc}{col}: {message}")


class LexerError(ComalError):
    def __init__(self, message: str, line: int, column: int):
        super().__init__("Leksikalsk fejl", message, line, column, code=10)


class ParserError(ComalError):
    def __init__(self, message: str, line: int, column: int):
        super().__init__("Syntaksfejl", message, line, column, code=20)


class InterpreterError(ComalError):
    def __init__(self, message: str, line: Optional[int] = None, code: int = 30):
        super().__init__("Kørselsfejl", message, line, None, code=code)


class Lexer:
    def __init__(self, text: str, line_map: Optional[Dict[int, int]] = None):
        self.text = text
        self.line_map = line_map or {}
        self.pos = 0
        self.raw_line = 1
        self.col_no = 1
        self.current_char = self.text[self.pos] if self.text else None
        self.prev_token: Optional[Token] = None

    @property
    def line_no(self) -> int:
        return self.line_map.get(self.raw_line, self.raw_line)

    def advance(self):
        if self.current_char == '\n':
            self.raw_line += 1
            self.col_no = 0
        self.pos += 1
        self.col_no += 1
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]

    def peek(self, offset: int = 1) -> Optional[str]:
        idx = self.pos + offset
        if 0 <= idx < len(self.text):
            return self.text[idx]
        return None

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char in ' \t\r':
            self.advance()

    def skip_comment(self):
        while self.current_char is not None and self.current_char != '\n':
            self.advance()

    def parse_string(self) -> Token:
        result = ''
        start_col = self.col_no
        line = self.line_no
        self.advance()
        while self.current_char is not None:
            if self.current_char == '"':
                if self.peek() == '"':
                    result += '"'
                    self.advance()
                    self.advance()
                    continue
                self.advance()
                return Token('STRING', result, line, start_col, self.raw_line)
            if self.current_char == '\n':
                raise LexerError("Uafsluttet tekststreng før linjeskift", line, start_col)
            result += self.current_char
            self.advance()
        raise LexerError("Uafsluttet tekststreng", line, start_col)

    def parse_number(self) -> Token:
        result = ''
        start_col = self.col_no
        line = self.line_no
        is_real = False

        if self.current_char == '$':
            self.advance()
            hex_digits = ''
            while self.current_char is not None and self.current_char in '0123456789abcdefABCDEF':
                hex_digits += self.current_char
                self.advance()
            if not hex_digits:
                raise LexerError("Ugyldigt hexadecimalt tal efter '$'", line, start_col)
            return Token('INTEGER', int(hex_digits, 16), line, start_col, self.raw_line)

        while self.current_char is not None and self.current_char.isdigit():
            result += self.current_char
            self.advance()

        if self.current_char == '.' and self.peek() != '.':
            is_real = True
            result += '.'
            self.advance()
            while self.current_char is not None and self.current_char.isdigit():
                result += self.current_char
                self.advance()

        if self.current_char in ('e', 'E'):
            nxt = self.peek()
            nxt2 = self.peek(2)
            if (nxt and nxt.isdigit()) or (nxt in ('+', '-') and nxt2 and nxt2.isdigit()):
                is_real = True
                result += self.current_char
                self.advance()
                if self.current_char in ('+', '-'):
                    result += self.current_char
                    self.advance()
                while self.current_char is not None and self.current_char.isdigit():
                    result += self.current_char
                    self.advance()

        if is_real:
            return Token('REAL', float(result), line, start_col, self.raw_line)
        return Token('INTEGER', int(result), line, start_col, self.raw_line)

    def parse_identifier(self) -> Token:
        result = ''
        start_col = self.col_no
        line = self.line_no
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_æøåÆØÅ")

        while self.current_char is not None and self.current_char in valid_chars:
            result += self.current_char
            self.advance()

        if self.current_char in ('%', '$'):
            result += self.current_char
            self.advance()

        result_upper = result.upper()
        if result_upper == 'XOR':
            result_upper = 'EOR'
        if result_upper in KEYWORDS:
            return Token(result_upper, result_upper, line, start_col, self.raw_line)

        return Token('ID', result, line, start_col, self.raw_line)

    def get_next_token(self) -> Token:
        while self.current_char is not None:
            if self.current_char in ' \t\r':
                self.skip_whitespace()
                continue

            if self.current_char == '\n':
                tok = Token('NEWLINE', '\n', self.line_no, self.col_no, self.raw_line)
                self.advance()
                return tok

            if (self.current_char == '/' and self.peek() == '/') or self.current_char == '!':
                self.skip_comment()
                continue

            if self.current_char == '"':
                return self.parse_string()

            if self.current_char.isdigit() or (self.current_char == '$' and self.peek() and self.peek() in '0123456789abcdefABCDEF'):
                return self.parse_number()

            if self.current_char.isalpha() or self.current_char in '_æøåÆØÅ':
                tok = self.parse_identifier()
                if tok.type == 'REM':
                    self.skip_comment()
                    continue
                return tok

            if self.current_char == ':':
                col = self.col_no
                line = self.line_no
                nxt = self.peek()
                if nxt == '=':
                    self.advance(); self.advance()
                    return Token('ASSIGN', ':=', line, col, self.raw_line)
                elif nxt == '+':
                    self.advance(); self.advance()
                    return Token('ASSIGN_ADD', ':+', line, col, self.raw_line)
                elif nxt == '-':
                    # ':-' er kun ASSIGN_SUB hvis forrige token er ID eller ')'
                    prev_type = self.prev_token.type if self.prev_token else None
                    if prev_type == 'ID' or (prev_type == 'OP' and self.prev_token.value == ')'):
                        self.advance(); self.advance()
                        return Token('ASSIGN_SUB', ':-', line, col, self.raw_line)
                    else:
                        self.advance()
                        return Token('OP', ':', line, col, self.raw_line)
                else:
                    self.advance()
                    return Token('OP', ':', line, col, self.raw_line)

            if self.current_char == '.' and self.peek() == '.':
                col = self.col_no
                line = self.line_no
                self.advance(); self.advance()
                return Token('OP', '..', line, col, self.raw_line)

            if self.current_char in '<>':
                char = self.current_char
                col = self.col_no
                line = self.line_no
                self.advance()
                if (char == '<' and self.current_char in ('=', '>')) or (char == '>' and self.current_char == '='):
                    char += self.current_char
                    self.advance()
                return Token('OP', char, line, col, self.raw_line)

            if self.current_char in '+-*/^()=,;#':
                tok = Token('OP', self.current_char, self.line_no, self.col_no, self.raw_line)
                self.advance()
                return tok

            raise LexerError(f"Ugyldigt tegn '{self.current_char}'", self.line_no, self.col_no)

        return Token('EOF', None, self.line_no, self.col_no, self.raw_line)

    def tokenize(self) -> List[Token]:
        tokens = []
        self.prev_token = None
        while True:
            tok = self.get_next_token()
            tokens.append(tok)
            if tok.type == 'EOF':
                break
            self.prev_token = tok
        return tokens


# ============================================================================
# DEL 2: AST-NODER
# ============================================================================

class AST:
    line: int = 0


class Num(AST):
    def __init__(self, token: Token):
        self.token = token
        self.value = token.value
        self.line = token.line


class StringVal(AST):
    def __init__(self, token: Token):
        self.token = token
        self.value = token.value
        self.line = token.line


class Var(AST):
    def __init__(self, token: Token):
        self.token = token
        self.name = token.value
        self.line = token.line


class IndexedOrCall(AST):
    def __init__(self, token: Token, args: List[AST], slice_range: Optional[Tuple[Optional[AST], Optional[AST]]] = None,
                 is_explicit_slice: bool = False):
        self.token = token
        self.name = token.value
        self.args = args
        self.slice_range = slice_range
        self.is_explicit_slice = is_explicit_slice
        self.line = token.line


class BinOp(AST):
    def __init__(self, left: AST, op_token: Token, right: AST):
        self.left = left
        self.op_token = op_token
        self.op = op_token.value
        self.right = right
        self.line = op_token.line


class UnaryOp(AST):
    def __init__(self, op_token: Token, expr: AST):
        self.op_token = op_token
        self.op = op_token.value
        self.expr = expr
        self.line = op_token.line


class Assign(AST):
    def __init__(self, target: AST, expr: AST, mode: str = ':='):
        self.target = target
        self.expr = expr
        self.mode = mode


class PrintItem:
    def __init__(self, expr: Optional[AST], sep: Optional[str] = None):
        self.expr = expr
        self.sep = sep


class Print(AST):
    def __init__(self, items: List[PrintItem], trailing_sep: Optional[str] = None,
                 using_expr: Optional[AST] = None, at_pos: Optional[Tuple[AST, AST]] = None,
                 file_no: Optional[AST] = None):
        self.items = items
        self.trailing_sep = trailing_sep
        self.using_expr = using_expr
        self.at_pos = at_pos
        self.file_no = file_no


class Input(AST):
    def __init__(self, prompt: str, targets: List[AST], at_pos: Optional[Tuple[AST, AST]] = None,
                 file_no: Optional[AST] = None):
        self.prompt = prompt
        self.targets = targets
        self.at_pos = at_pos
        self.file_no = file_no


@dataclass
class DimEntry:
    name: str
    bounds: List[Tuple[AST, AST]]
    str_len: Optional[AST] = None


class Dim(AST):
    def __init__(self, entries: List[DimEntry], is_global: bool = False):
        self.entries = entries
        self.is_global = is_global


class ImportStmt(AST):
    def __init__(self, names: List[str]):
        self.names = names


class Data(AST):
    def __init__(self, values: List[AST]):
        self.values = values


class Read(AST):
    def __init__(self, targets: List[AST], file_no: Optional[AST] = None):
        self.targets = targets
        self.file_no = file_no


class WriteStmt(AST):
    def __init__(self, file_no: AST, exprs: List[AST]):
        self.file_no = file_no
        self.exprs = exprs


class OpenFile(AST):
    def __init__(self, file_no: AST, filename: AST, mode: str, rec_len: Optional[AST] = None):
        self.file_no = file_no
        self.filename = filename
        self.mode = mode
        self.rec_len = rec_len


class CloseFile(AST):
    def __init__(self, file_nos: List[AST]):
        self.file_nos = file_nos


class Restore(AST):
    def __init__(self, label: Optional[str] = None):
        self.label = label


class Block(AST):
    def __init__(self, statements: List[AST]):
        self.statements = statements


class If(AST):
    def __init__(self, condition: AST, true_block: Block,
                 elifs: List[Tuple[AST, Block]], false_block: Optional[Block]):
        self.condition = condition
        self.true_block = true_block
        self.elifs = elifs
        self.false_block = false_block


@dataclass
class WhenMatcher:
    kind: str
    val1: AST
    val2: Optional[AST] = None
    op: Optional[str] = None


class CaseStmt(AST):
    def __init__(self, expr: AST, when_branches: List[Tuple[List[WhenMatcher], Block]],
                 otherwise_block: Optional[Block]):
        self.expr = expr
        self.when_branches = when_branches
        self.otherwise_block = otherwise_block


class For(AST):
    def __init__(self, var: Var, start_expr: AST, end_expr: AST, step_expr: AST, block: Block):
        self.var = var
        self.start_expr = start_expr
        self.end_expr = end_expr
        self.step_expr = step_expr
        self.block = block


class While(AST):
    def __init__(self, condition: AST, block: Block):
        self.condition = condition
        self.block = block


class Repeat(AST):
    def __init__(self, block: Block, condition: AST):
        self.block = block
        self.condition = condition


class LoopStmt(AST):
    def __init__(self, block: Block):
        self.block = block


class ExitStmt(AST):
    def __init__(self, condition: Optional[AST] = None):
        self.condition = condition


class TrapStmt(AST):
    def __init__(self, try_block: Block, handler_block: Optional[Block], esc_toggle: Optional[bool] = None):
        self.try_block = try_block
        self.handler_block = handler_block
        self.esc_toggle = esc_toggle


@dataclass
class ParamDecl:
    name: str
    is_ref: bool = False
    is_array: bool = False


class ProcDecl(AST):
    def __init__(self, name_token: Token, params: List[ParamDecl], is_closed: bool, block: Block):
        self.name_token = name_token
        self.name = name_token.value
        self.params = params
        self.is_closed = is_closed
        self.block = block
        self.line = name_token.line


class FuncDecl(AST):
    def __init__(self, name_token: Token, params: List[ParamDecl], is_closed: bool, block: Block):
        self.name_token = name_token
        self.name = name_token.value
        self.params = params
        self.is_closed = is_closed
        self.block = block
        self.line = name_token.line


class Exec(AST):
    def __init__(self, proc_token: Token, args: List[AST]):
        self.proc_token = proc_token
        self.name = proc_token.value
        self.args = args
        self.line = proc_token.line


class Return(AST):
    def __init__(self, expr: Optional[AST] = None):
        self.expr = expr


class LabelStmt(AST):
    def __init__(self, name: str, line: int):
        self.name = name
        self.line = line


class GotoStmt(AST):
    def __init__(self, target: str):
        self.target = target


class CursorStmt(AST):
    def __init__(self, row_expr: AST, col_expr: AST):
        self.row_expr = row_expr
        self.col_expr = col_expr


class ZoneStmt(AST):
    def __init__(self, width_expr: AST):
        self.width_expr = width_expr


class TraceStmt(AST):
    def __init__(self, enabled: bool):
        self.enabled = enabled


class DelFileStmt(AST):
    def __init__(self, filename_expr: AST):
        self.filename_expr = filename_expr


class RandomizeStmt(AST):
    def __init__(self, seed_expr: Optional[AST] = None):
        self.seed_expr = seed_expr


class NullStmt(AST): pass
class End(AST): pass
class Stop(AST): pass
class Page(AST): pass


# ============================================================================
# DEL 3: PARSER
# ============================================================================

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos] if self.tokens else Token('EOF', None, 0, 0)

    def peek_token(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if 0 <= idx < len(self.tokens):
            return self.tokens[idx]
        return Token('EOF', None, -1, -1)

    def error(self, message: str):
        line = self.current_token.line if self.current_token else 0
        col = self.current_token.column if self.current_token else 0
        raise ParserError(message, line, col)

    def eat(self, token_type: str):
        if self.current_token.type == token_type:
            self.pos += 1
            if self.pos < len(self.tokens):
                self.current_token = self.tokens[self.pos]
            else:
                self.current_token = Token('EOF', None, -1, -1)
        else:
            self.error(f"Forventede {token_type}, men fandt {self.current_token.type} ('{self.current_token.value}')")

    def match_op(self, val: str) -> bool:
        return self.current_token.type == 'OP' and self.current_token.value == val

    def eat_op(self, val: str):
        if self.match_op(val):
            self.eat('OP')
        else:
            self.error(f"Forventede '{val}', men fandt '{self.current_token.value}'")

    def skip_newlines(self):
        while self.current_token.type == 'NEWLINE' or self.match_op(';'):
            if self.current_token.type == 'NEWLINE':
                self.eat('NEWLINE')
            else:
                self.eat('OP')

    def is_stmt_terminator(self) -> bool:
        return self.current_token.type in (
            'NEWLINE', 'EOF', 'ELSE', 'ELIF', 'ENDIF', 'ENDFOR',
            'ENDWHILE', 'UNTIL', 'ENDLOOP', 'ENDPROC', 'ENDFUNC',
            'WHEN', 'OTHERWISE', 'ENDCASE', 'HANDLER', 'ENDTRAP'
        )

    def parse_id_or_indexed(self) -> AST:
        tok = self.current_token
        self.eat('ID')
        if not self.match_op('('):
            return Var(tok)

        self.eat_op('(')
        if self.match_op(':'):
            self.eat_op(':')
            end_expr = self.expr()
            self.eat_op(')')
            return IndexedOrCall(tok, [], slice_range=(Num(Token('INTEGER', 1, tok.line, tok.column)), end_expr),
                                 is_explicit_slice=True)

        args = []
        if not self.match_op(')'):
            first_expr = self.expr()
            if self.match_op(':'):
                self.eat_op(':')
                end_expr = None if self.match_op(')') else self.expr()
                self.eat_op(')')
                return IndexedOrCall(tok, [], slice_range=(first_expr, end_expr), is_explicit_slice=True)
            args.append(first_expr)
            while self.match_op(','):
                self.eat_op(',')
                args.append(self.expr())
        self.eat_op(')')

        slice_range = None
        is_explicit_slice = False
        if self.match_op('('):
            self.eat_op('(')
            start_e = Num(Token('INTEGER', 1, tok.line, tok.column)) if self.match_op(':') else self.expr()
            if self.match_op(':'):
                self.eat_op(':')
                end_e = None if self.match_op(')') else self.expr()
                slice_range = (start_e, end_e)
                is_explicit_slice = True
            else:
                slice_range = (start_e, start_e)
                is_explicit_slice = True
            self.eat_op(')')

        return IndexedOrCall(tok, args, slice_range=slice_range, is_explicit_slice=is_explicit_slice)

    def primary(self) -> AST:
        tok = self.current_token
        if tok.type in ('INTEGER', 'REAL'):
            self.eat(tok.type)
            return Num(tok)
        elif tok.type == 'STRING':
            self.eat('STRING')
            return StringVal(tok)
        elif self.match_op('('):
            self.eat_op('(')
            node = self.expr()
            self.eat_op(')')
            return node
        elif tok.type == 'ID':
            return self.parse_id_or_indexed()
        elif tok.type == 'EOF':
            self.eat('EOF')
            self.eat_op('(')
            arg = self.expr()
            self.eat_op(')')
            return IndexedOrCall(Token('ID', 'EOF', tok.line, tok.column), [arg])
        self.error(f"Uventet symbol i udtryk: {tok.type} ('{tok.value}')")

    def power(self) -> AST:
        node = self.primary()
        if self.match_op('^'):
            tok = self.current_token
            self.eat_op('^')
            node = BinOp(node, tok, self.unary())
        return node

    def unary(self) -> AST:
        tok = self.current_token
        if tok.type == 'OP' and tok.value in ('+', '-'):
            self.eat('OP')
            return UnaryOp(tok, self.unary())
        elif tok.type == 'NOT':
            self.eat('NOT')
            return UnaryOp(tok, self.unary())
        return self.power()

    def term(self) -> AST:
        node = self.unary()
        while (self.current_token.type == 'OP' and self.current_token.value in ('*', '/')) or \
              self.current_token.type in ('MOD', 'DIV'):
            tok = self.current_token
            self.eat(tok.type)
            node = BinOp(node, tok, self.unary())
        return node

    def arithmetic_expr(self) -> AST:
        node = self.term()
        while self.current_token.type == 'OP' and self.current_token.value in ('+', '-'):
            tok = self.current_token
            self.eat('OP')
            node = BinOp(node, tok, self.term())
        return node

    def relational_expr(self) -> AST:
        node = self.arithmetic_expr()
        while (self.current_token.type == 'OP' and self.current_token.value in ('=', '<', '>', '<=', '>=', '<>')) or \
              self.current_token.type == 'IN':
            tok = self.current_token
            self.eat(tok.type)
            node = BinOp(node, tok, self.arithmetic_expr())
        return node

    def expr(self) -> AST:
        node = self.relational_expr()
        while self.current_token.type in ('AND', 'OR', 'EOR'):
            tok = self.current_token
            self.eat(tok.type)
            node = BinOp(node, tok, self.relational_expr())
        return node

    def statement(self) -> Optional[AST]:
        self.skip_newlines()
        if self.current_token.type == 'EOF':
            return None
        line_no = self.current_token.line
        node = self._parse_statement()
        if node is not None:
            node.line = line_no
        return node

    def _parse_file_spec(self) -> AST:
        self.eat('FILE')
        if self.match_op('#'):
            self.eat_op('#')
        f_no = self.expr()
        if self.match_op(':') or self.match_op(','):
            self.eat('OP')
        return f_no

    def _parse_statement(self) -> AST:
        tok = self.current_token

        if tok.type == 'NULL':
            self.eat('NULL')
            return NullStmt()

        if tok.type == 'PRINT':
            self.eat('PRINT')
            file_no = None
            at_pos = None
            using_expr = None

            if self.current_token.type == 'FILE':
                file_no = self._parse_file_spec()

            if self.current_token.type == 'AT':
                self.eat('AT')
                r_expr = self.expr()
                self.eat_op(',')
                c_expr = self.expr()
                at_pos = (r_expr, c_expr)
                if self.match_op(':') or self.match_op(';') or self.match_op(','):
                    self.eat('OP')

            if self.current_token.type == 'USING':
                self.eat('USING')
                using_expr = self.expr()
                if self.match_op(':') or self.match_op(';') or self.match_op(','):
                    self.eat('OP')

            items: List[PrintItem] = []
            trailing_sep = None

            while not self.is_stmt_terminator():
                expr_node = self.expr()
                sep = None
                if self.current_token.type == 'OP' and self.current_token.value in (',', ';'):
                    sep = self.current_token.value
                    self.eat('OP')
                    if self.is_stmt_terminator():
                        trailing_sep = sep
                        items.append(PrintItem(expr_node, sep))
                        break
                items.append(PrintItem(expr_node, sep))
                if sep is None and not self.is_stmt_terminator():
                    break

            return Print(items, trailing_sep=trailing_sep, using_expr=using_expr, at_pos=at_pos, file_no=file_no)

        elif tok.type == 'CURSOR':
            self.eat('CURSOR')
            r_expr = self.expr()
            self.eat_op(',')
            c_expr = self.expr()
            return CursorStmt(r_expr, c_expr)

        elif tok.type == 'ZONE':
            self.eat('ZONE')
            return ZoneStmt(self.expr())

        elif tok.type == 'INPUT':
            self.eat('INPUT')
            file_no = None
            at_pos = None
            prompt = "? "

            if self.current_token.type == 'FILE':
                file_no = self._parse_file_spec()
                prompt = ""

            if self.current_token.type == 'AT':
                self.eat('AT')
                r_e = self.expr()
                self.eat_op(',')
                c_e = self.expr()
                at_pos = (r_e, c_e)
                if self.match_op(':') or self.match_op(';') or self.match_op(','):
                    self.eat('OP')

            if self.current_token.type == 'STRING':
                prompt = self.current_token.value
                self.eat('STRING')
                if self.current_token.type == 'OP' and self.current_token.value in (':', ';', ','):
                    sep_ch = self.current_token.value
                    self.eat('OP')
                    if sep_ch == ',':
                        prompt += "? "

            targets = [self.parse_id_or_indexed()]
            while self.match_op(','):
                self.eat_op(',')
                targets.append(self.parse_id_or_indexed())
            return Input(prompt, targets, at_pos=at_pos, file_no=file_no)

        elif tok.type in ('DIM', 'GLOBAL'):
            is_global = (tok.type == 'GLOBAL')
            self.eat(tok.type)
            entries: List[DimEntry] = []
            while True:
                id_tok = self.current_token
                self.eat('ID')
                bounds: List[Tuple[AST, AST]] = []
                str_len: Optional[AST] = None

                if self.match_op('('):
                    self.eat_op('(')
                    while True:
                        first_b = self.expr()
                        if self.match_op(':') or self.match_op('..'):
                            self.eat('OP')
                            second_b = self.expr()
                            bounds.append((first_b, second_b))
                        elif self.current_token.type == 'ASSIGN_SUB':
                            op_tok = self.current_token
                            self.eat('ASSIGN_SUB')
                            second_b = UnaryOp(Token('OP', '-', op_tok.line, op_tok.column), self.unary())
                            bounds.append((first_b, second_b))
                        else:
                            bounds.append((Num(Token('INTEGER', 1, id_tok.line, id_tok.column)), first_b))
                        if self.match_op(','):
                            self.eat_op(',')
                        else:
                            break
                    self.eat_op(')')

                if self.current_token.type == 'OF':
                    self.eat('OF')
                    str_len = self.expr()

                entries.append(DimEntry(id_tok.value, bounds, str_len))
                if self.match_op(','):
                    self.eat_op(',')
                else:
                    break
            return Dim(entries, is_global=is_global)

        elif tok.type == 'IMPORT':
            self.eat('IMPORT')
            names = []
            while True:
                if self.current_token.type == 'ARRAY':
                    self.eat('ARRAY')
                id_tok = self.current_token
                self.eat('ID')
                if self.match_op('('):
                    self.eat_op('(')
                    if not self.match_op(')'):
                        self.expr()
                    self.eat_op(')')
                names.append(id_tok.value)
                if self.match_op(','):
                    self.eat_op(',')
                else:
                    break
            return ImportStmt(names)

        elif tok.type == 'ID':
            if self.peek_token().type == 'OP' and self.peek_token().value == ':':
                label_name = tok.value
                self.eat('ID')
                self.eat_op(':')
                return LabelStmt(label_name, tok.line)

            target = self.parse_id_or_indexed()

            if self.current_token.type in ('ASSIGN', 'ASSIGN_ADD', 'ASSIGN_SUB') or self.match_op('='):
                mode = ':='
                if self.current_token.type == 'ASSIGN':
                    self.eat('ASSIGN')
                elif self.current_token.type == 'ASSIGN_ADD':
                    mode = ':+'
                    self.eat('ASSIGN_ADD')
                elif self.current_token.type == 'ASSIGN_SUB':
                    mode = ':-'
                    self.eat('ASSIGN_SUB')
                else:
                    self.eat_op('=')
                expr_node = self.expr()
                return Assign(target, expr_node, mode=mode)
            else:
                args = []
                if isinstance(target, IndexedOrCall):
                    args = target.args
                    proc_tok = target.token
                else:
                    proc_tok = target.token
                    if not self.is_stmt_terminator():
                        args.append(self.expr())
                        while self.match_op(','):
                            self.eat_op(',')
                            args.append(self.expr())
                return Exec(proc_tok, args)

        elif tok.type == 'EXEC':
            self.eat('EXEC')
            proc_tok = self.current_token
            self.eat('ID')
            args = []
            if self.match_op('('):
                self.eat_op('(')
                if not self.match_op(')'):
                    args.append(self.expr())
                    while self.match_op(','):
                        self.eat_op(',')
                        args.append(self.expr())
                self.eat_op(')')
            elif not self.is_stmt_terminator():
                args.append(self.expr())
                while self.match_op(','):
                    self.eat_op(',')
                    args.append(self.expr())
            return Exec(proc_tok, args)

        elif tok.type == 'IF':
            self.eat('IF')
            cond = self.expr()
            if self.current_token.type == 'THEN':
                self.eat('THEN')

            if self.current_token.type == 'NEWLINE':
                self.skip_newlines()
                true_block = self.block(['ELIF', 'ELSE', 'ENDIF'])
                elifs = []
                while self.current_token.type == 'ELIF':
                    self.eat('ELIF')
                    elif_cond = self.expr()
                    if self.current_token.type == 'THEN':
                        self.eat('THEN')
                    self.skip_newlines()
                    elif_block = self.block(['ELIF', 'ELSE', 'ENDIF'])
                    elifs.append((elif_cond, elif_block))

                false_block = None
                if self.current_token.type == 'ELSE':
                    self.eat('ELSE')
                    self.skip_newlines()
                    false_block = self.block(['ENDIF'])

                self.eat('ENDIF')
                return If(cond, true_block, elifs, false_block)
            else:
                single_true = self._parse_statement()
                single_true.line = tok.line
                false_block = None
                if self.current_token.type == 'ELSE':
                    self.eat('ELSE')
                    single_false = self._parse_statement()
                    single_false.line = tok.line
                    false_block = Block([single_false])
                if self.current_token.type == 'ENDIF':
                    self.eat('ENDIF')
                return If(cond, Block([single_true]), [], false_block)

        elif tok.type == 'CASE':
            self.eat('CASE')
            case_expr = self.expr()
            if self.current_token.type == 'OF':
                self.eat('OF')
            self.skip_newlines()

            when_branches: List[Tuple[List[WhenMatcher], Block]] = []
            while self.current_token.type == 'WHEN':
                self.eat('WHEN')
                matchers: List[WhenMatcher] = []
                while True:
                    if self.current_token.type == 'OP' and self.current_token.value in ('=', '<>', '<', '<=', '>', '>='):
                        rel_op = self.current_token.value
                        self.eat('OP')
                        val_e = self.expr()
                        matchers.append(WhenMatcher('REL', val_e, op=rel_op))
                    else:
                        v1 = self.expr()
                        if self.match_op('..') or self.match_op(':'):
                            self.eat('OP')
                            v2 = self.expr()
                            matchers.append(WhenMatcher('RANGE', v1, v2))
                        elif self.current_token.type == 'ASSIGN_SUB':
                            op_tok = self.current_token
                            self.eat('ASSIGN_SUB')
                            v2 = UnaryOp(Token('OP', '-', op_tok.line, op_tok.column), self.unary())
                            matchers.append(WhenMatcher('RANGE', v1, v2))
                        else:
                            matchers.append(WhenMatcher('EQ', v1))
                    if self.match_op(','):
                        self.eat_op(',')
                    else:
                        break
                self.skip_newlines()
                w_block = self.block(['WHEN', 'OTHERWISE', 'ENDCASE'])
                when_branches.append((matchers, w_block))

            otherwise_block = None
            if self.current_token.type == 'OTHERWISE':
                self.eat('OTHERWISE')
                if self.match_op(':'):
                    self.eat_op(':')
                self.skip_newlines()
                otherwise_block = self.block(['ENDCASE'])

            self.eat('ENDCASE')
            return CaseStmt(case_expr, when_branches, otherwise_block)

        elif tok.type == 'FOR':
            self.eat('FOR')
            var_tok = self.current_token
            self.eat('ID')
            if self.current_token.type == 'ASSIGN':
                self.eat('ASSIGN')
            else:
                self.eat_op('=')

            start_expr = self.expr()
            self.eat('TO')
            end_expr = self.expr()

            step_expr = Num(Token('INTEGER', 1, var_tok.line, 0))
            if self.current_token.type == 'STEP':
                self.eat('STEP')
                step_expr = self.expr()

            if self.current_token.type == 'DO':
                self.eat('DO')

            if self.current_token.type == 'NEWLINE':
                self.skip_newlines()
                body = self.block(['ENDFOR'])
                self.eat('ENDFOR')
                if self.current_token.type == 'ID':
                    self.eat('ID')
                return For(Var(var_tok), start_expr, end_expr, step_expr, body)
            else:
                single_stmt = self._parse_statement()
                single_stmt.line = tok.line
                if self.current_token.type == 'ENDFOR':
                    self.eat('ENDFOR')
                    if self.current_token.type == 'ID':
                        self.eat('ID')
                return For(Var(var_tok), start_expr, end_expr, step_expr, Block([single_stmt]))

        elif tok.type == 'WHILE':
            self.eat('WHILE')
            cond = self.expr()
            if self.current_token.type == 'DO':
                self.eat('DO')
            if self.current_token.type == 'NEWLINE':
                self.skip_newlines()
                body = self.block(['ENDWHILE'])
                self.eat('ENDWHILE')
                return While(cond, body)
            else:
                single_stmt = self._parse_statement()
                single_stmt.line = tok.line
                if self.current_token.type == 'ENDWHILE':
                    self.eat('ENDWHILE')
                return While(cond, Block([single_stmt]))

        elif tok.type == 'REPEAT':
            self.eat('REPEAT')
            self.skip_newlines()
            body = self.block(['UNTIL'])
            self.eat('UNTIL')
            cond = self.expr()
            return Repeat(body, cond)

        elif tok.type == 'LOOP':
            self.eat('LOOP')
            self.skip_newlines()
            body = self.block(['ENDLOOP'])
            self.eat('ENDLOOP')
            return LoopStmt(body)

        elif tok.type == 'EXIT':
            self.eat('EXIT')
            cond = None
            if self.current_token.type == 'WHEN':
                self.eat('WHEN')
                cond = self.expr()
            return ExitStmt(cond)

        elif tok.type == 'TRAP':
            self.eat('TRAP')
            if self.current_token.type == 'ESC':
                self.eat('ESC')
                toggle = True
                if self.match_op('+'):
                    self.eat_op('+')
                    toggle = True
                elif self.match_op('-'):
                    self.eat_op('-')
                    toggle = False
                return TrapStmt(Block([]), None, esc_toggle=toggle)

            self.skip_newlines()
            try_block = self.block(['HANDLER', 'ENDTRAP'])
            handler_block = None
            if self.current_token.type == 'HANDLER':
                self.eat('HANDLER')
                self.skip_newlines()
                handler_block = self.block(['ENDTRAP'])
            self.eat('ENDTRAP')
            return TrapStmt(try_block, handler_block)

        elif tok.type in ('PROC', 'FUNC'):
            is_func = (tok.type == 'FUNC')
            self.eat(tok.type)
            name_tok = self.current_token
            self.eat('ID')
            params = self._parse_param_list()
            is_closed = False
            if self.current_token.type == 'CLOSED':
                self.eat('CLOSED')
                is_closed = True

            self.skip_newlines()
            end_kw = 'ENDFUNC' if is_func else 'ENDPROC'
            body = self.block([end_kw])
            self.eat(end_kw)
            if self.current_token.type == 'ID':
                self.eat('ID')

            if is_func:
                return FuncDecl(name_tok, params, is_closed, body)
            return ProcDecl(name_tok, params, is_closed, body)

        elif tok.type == 'RETURN':
            self.eat('RETURN')
            expr = None
            if not self.is_stmt_terminator():
                expr = self.expr()
            return Return(expr)

        elif tok.type == 'DATA':
            self.eat('DATA')
            values = [self.expr()]
            while self.match_op(','):
                self.eat_op(',')
                values.append(self.expr())
            return Data(values)

        elif tok.type == 'READ':
            self.eat('READ')
            file_no = None
            if self.current_token.type == 'FILE':
                file_no = self._parse_file_spec()
            targets = [self.parse_id_or_indexed()]
            while self.match_op(','):
                self.eat_op(',')
                targets.append(self.parse_id_or_indexed())
            return Read(targets, file_no=file_no)

        elif tok.type == 'WRITE':
            self.eat('WRITE')
            file_no = self._parse_file_spec()
            exprs = [self.expr()]
            while self.match_op(','):
                self.eat_op(',')
                exprs.append(self.expr())
            return WriteStmt(file_no, exprs)

        elif tok.type == 'OPEN':
            self.eat('OPEN')
            if self.current_token.type == 'FILE':
                self.eat('FILE')
            if self.match_op('#'):
                self.eat_op('#')
            file_no = self.expr()
            self.eat_op(',')
            filename = self.expr()
            mode = 'READ'
            rec_len = None
            if self.match_op(','):
                self.eat_op(',')
                if self.current_token.type in ('READ', 'WRITE', 'APPEND', 'RANDOM', 'ID'):
                    mode = self.current_token.value.upper()
                    self.eat(self.current_token.type)
                    if mode == 'RANDOM' and not self.is_stmt_terminator():
                        if self.match_op(','):
                            self.eat_op(',')
                        rec_len = self.expr()
            return OpenFile(file_no, filename, mode, rec_len)

        elif tok.type == 'CLOSE':
            self.eat('CLOSE')
            if self.current_token.type == 'FILE':
                self.eat('FILE')
            file_nos = []
            if not self.is_stmt_terminator():
                if self.match_op('#'):
                    self.eat_op('#')
                file_nos.append(self.expr())
                while self.match_op(','):
                    self.eat_op(',')
                    file_nos.append(self.expr())
            return CloseFile(file_nos)

        elif tok.type == 'RESTORE':
            self.eat('RESTORE')
            label = None
            if self.current_token.type == 'ID':
                label = self.current_token.value
                self.eat('ID')
            elif self.current_token.type == 'INTEGER':
                label = str(self.current_token.value)
                self.eat('INTEGER')
            return Restore(label)

        elif tok.type == 'GOTO':
            self.eat('GOTO')
            if self.current_token.type in ('ID', 'INTEGER'):
                target = str(self.current_token.value)
                self.eat(self.current_token.type)
                return GotoStmt(target)
            self.error("Forventede label eller linjenummer efter GOTO")

        elif tok.type == 'RANDOMIZE':
            self.eat('RANDOMIZE')
            seed = None if self.is_stmt_terminator() else self.expr()
            return RandomizeStmt(seed)

        elif tok.type == 'TRACE':
            self.eat('TRACE')
            en = True
            if self.current_token.type in ('ON', 'OFF'):
                en = (self.current_token.type == 'ON')
                self.eat(self.current_token.type)
            return TraceStmt(en)

        elif tok.type == 'DEL':
            self.eat('DEL')
            return DelFileStmt(self.expr())

        elif tok.type == 'END':
            self.eat('END')
            return End()

        elif tok.type == 'STOP':
            self.eat('STOP')
            return Stop()

        elif tok.type == 'PAGE':
            self.eat('PAGE')
            return Page()

        else:
            self.error(f"Uventet kommando eller nøgleord: {tok.type} ('{tok.value}')")

    def _parse_param_list(self) -> List[ParamDecl]:
        params: List[ParamDecl] = []
        if not self.match_op('('):
            return params
        self.eat_op('(')
        if self.match_op(')'):
            self.eat_op(')')
            return params

        while True:
            is_ref = False
            if self.current_token.type in ('REF', 'NAME'):
                self.eat(self.current_token.type)
                is_ref = True
            p_tok = self.current_token
            self.eat('ID')
            is_arr = False
            if self.match_op('('):
                self.eat_op('(')
                while not self.match_op(')') and self.current_token.type != 'EOF':
                    self.eat(self.current_token.type)
                self.eat_op(')')
                is_arr = True
            params.append(ParamDecl(p_tok.value, is_ref=is_ref, is_array=is_arr))
            if self.match_op(','):
                self.eat_op(',')
            else:
                break
        self.eat_op(')')
        return params

    def block(self, end_tokens: List[str]) -> Block:
        statements = []
        self.skip_newlines()
        while self.current_token.type not in end_tokens and self.current_token.type != 'EOF':
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
            self.skip_newlines()
        return Block(statements)

    def parse(self) -> Block:
        statements = []
        self.skip_newlines()
        while self.current_token.type != 'EOF':
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
            self.skip_newlines()
        return Block(statements)


# ============================================================================
# DEL 4: RUNTIME-STRUKTURER OG FORTOLKER
# ============================================================================

class ReturnException(Exception):
    def __init__(self, value=None):
        self.value = value


class ExitLoopException(Exception): pass
class EndException(Exception): pass
class StopException(Exception): pass


class GotoException(Exception):
    def __init__(self, target: str):
        self.target = target


@dataclass
class RefBinding:
    getter: Callable[[], Any]
    setter: Callable[[Any], None]
    desc: str = "REF"


@dataclass
class ComalArray:
    name: str
    bounds: List[Tuple[int, int]]
    str_max_len: Optional[int] = None
    data: Dict[Tuple[int, ...], Any] = field(default_factory=dict)

    def default_value(self) -> Any:
        return "" if self.name.endswith('$') else 0

    def validate_indices(self, indices: Tuple[int, ...], line: Optional[int]):
        if len(indices) != len(self.bounds):
            raise InterpreterError(
                f"Tabel '{self.name}' har {len(self.bounds)} dimension(er), men blev tilgået med {len(indices)}",
                line, code=41
            )
        for dim_idx, (idx_val, (low, high)) in enumerate(zip(indices, self.bounds), start=1):
            if idx_val < low or idx_val > high:
                raise InterpreterError(
                    f"Indeks {idx_val} uden for grænserne ({low}:{high}) i dimension {dim_idx} for '{self.name}'",
                    line, code=42
                )

    def get(self, indices: Tuple[int, ...], line: Optional[int]) -> Any:
        self.validate_indices(indices, line)
        return self.data.get(indices, self.default_value())

    def set(self, indices: Tuple[int, ...], value: Any, line: Optional[int]):
        self.validate_indices(indices, line)
        if self.name.endswith('$'):
            value = str(value)
            if self.str_max_len is not None and len(value) > self.str_max_len:
                raise InterpreterError(
                    f"Strenglængde ({len(value)}) overstiger DIM OF {self.str_max_len} for '{self.name}'",
                    line, code=43
                )
        elif self.name.endswith('%'):
            value = int(float(value))
        else:
            value = float(value) if not isinstance(value, (int, float)) else value
        self.data[indices] = value


@dataclass
class CallFrame:
    name: str
    is_closed: bool
    call_line: int
    locals: Dict[str, Any] = field(default_factory=dict)
    arrays: Dict[str, ComalArray] = field(default_factory=dict)
    str_limits: Dict[str, int] = field(default_factory=dict)
    refs: Dict[str, RefBinding] = field(default_factory=dict)
    imports: set = field(default_factory=set)


class Interpreter:
    def __init__(self, ast_root: Block, ui_print: Callable, ui_input: Callable,
                 ui_cursor: Optional[Callable] = None, ui_clear: Optional[Callable] = None,
                 graphics_cb: Optional[Callable] = None, debug_hook: Optional[Callable] = None,
                 key_provider: Optional[Callable] = None,
                 base_dir: Optional[str] = None):
        self.ast = ast_root
        self.base_dir = base_dir
        self.ui_print = ui_print
        self.ui_input = ui_input
        self.ui_cursor = ui_cursor
        self.ui_clear = ui_clear
        self.graphics_cb = graphics_cb
        self.debug_hook = debug_hook
        self.key_provider = key_provider

        self.globals: Dict[str, Any] = {}
        self.global_arrays: Dict[str, ComalArray] = {}
        self.global_str_limits: Dict[str, int] = {}

        self.call_stack: List[CallFrame] = []
        self.procedures: Dict[str, ProcDecl] = {}
        self.functions: Dict[str, FuncDecl] = {}

        self.data_buffer: List[Any] = []
        self.data_labels: Dict[str, int] = {}
        self.data_ptr: int = 0

        self.files: Dict[int, Dict[str, Any]] = {}
        self.zone_width: int = 14
        self.print_col: int = 0

        self.current_line: int = 0
        self.last_err: int = 0
        self.last_errline: int = 0
        self.last_errtext: str = ""
        self.trap_esc_enabled: bool = True
        self.esc_requested: bool = False
        self.trace_enabled: bool = False
        self.start_time: float = time.time()

        self.line_counts: Dict[int, int] = {}
        self.stmt_counter: int = 0

        self.turtle_x: float = 0.0
        self.turtle_y: float = 0.0
        self.turtle_heading: float = 0.0
        self.turtle_pen: bool = True
        self.turtle_color: str = "#33ff33"

    def pre_scan(self, node: AST):
        if isinstance(node, Block):
            for stmt in node.statements:
                if isinstance(stmt, LabelStmt):
                    self.data_labels[stmt.name.upper()] = len(self.data_buffer)
                elif isinstance(stmt, Data):
                    if str(stmt.line) not in self.data_labels:
                        self.data_labels[str(stmt.line)] = len(self.data_buffer)
                    for val_node in stmt.values:
                        self.data_buffer.append(self._eval_static_data(val_node))
                elif isinstance(stmt, ProcDecl):
                    self.procedures[stmt.name.upper()] = stmt
                elif isinstance(stmt, FuncDecl):
                    self.functions[stmt.name.upper()] = stmt
                elif isinstance(stmt, If):
                    self.pre_scan(stmt.true_block)
                    for _, eb in stmt.elifs:
                        self.pre_scan(eb)
                    if stmt.false_block:
                        self.pre_scan(stmt.false_block)
                elif isinstance(stmt, (For, While, Repeat, LoopStmt)):
                    self.pre_scan(stmt.block)
                elif isinstance(stmt, CaseStmt):
                    for _, wb in stmt.when_branches:
                        self.pre_scan(wb)
                    if stmt.otherwise_block:
                        self.pre_scan(stmt.otherwise_block)
                elif isinstance(stmt, TrapStmt):
                    self.pre_scan(stmt.try_block)
                    if stmt.handler_block:
                        self.pre_scan(stmt.handler_block)

    def _eval_static_data(self, node: AST) -> Any:
        if isinstance(node, Num):
            return node.value
        if isinstance(node, StringVal):
            return node.value
        if isinstance(node, UnaryOp):
            v = self._eval_static_data(node.expr)
            return -v if node.op == '-' else +v
        return self.visit(node)

    def _active_closed_frame(self) -> Optional[CallFrame]:
        for frame in reversed(self.call_stack):
            if frame.is_closed:
                return frame
        return None

    def _coerce_type(self, name: str, value: Any, max_len: Optional[int] = None) -> Any:
        if name.endswith('$'):
            s = str(value)
            if max_len is not None and len(s) > max_len:
                raise InterpreterError(
                    f"Streng '{name}' på længde {len(s)} overskrider DIM OF {max_len}",
                    self.current_line, code=43
                )
            return s
        elif name.endswith('%'):
            try:
                return int(float(value))
            except Exception:
                raise InterpreterError(f"Kan ikke konvertere '{value}' til heltal for '{name}'", self.current_line)
        else:
            try:
                f = float(value)
                return int(f) if f.is_integer() else f
            except Exception:
                raise InterpreterError(f"Kan ikke konvertere '{value}' til tal for '{name}'", self.current_line)

    def get_var(self, name: str) -> Any:
        uname = name.upper()
        for frame in reversed(self.call_stack):
            if uname in frame.refs:
                return frame.refs[uname].getter()
            if uname in frame.locals:
                return frame.locals[uname]
            if frame.is_closed:
                if uname in frame.imports:
                    break
                default_val = "" if uname.endswith('$') else 0
                frame.locals[uname] = default_val
                return default_val

        if uname in self.globals:
            return self.globals[uname]
        default_val = "" if uname.endswith('$') else 0
        self.globals[uname] = default_val
        return default_val

    def set_var(self, name: str, value: Any):
        uname = name.upper()
        for frame in reversed(self.call_stack):
            if uname in frame.refs:
                frame.refs[uname].setter(self._coerce_type(uname, value))
                return
            if uname in frame.locals:
                limit = frame.str_limits.get(uname)
                frame.locals[uname] = self._coerce_type(uname, value, limit)
                return
            if frame.is_closed:
                if uname in frame.imports:
                    break
                limit = frame.str_limits.get(uname)
                frame.locals[uname] = self._coerce_type(uname, value, limit)
                return

        limit = self.global_str_limits.get(uname)
        self.globals[uname] = self._coerce_type(uname, value, limit)

    def get_array(self, name: str, auto_dim_len: int = 0) -> ComalArray:
        uname = name.upper()
        for frame in reversed(self.call_stack):
            if uname in frame.refs:
                ref_obj = frame.refs[uname].getter()
                if isinstance(ref_obj, ComalArray):
                    return ref_obj
            if uname in frame.arrays:
                return frame.arrays[uname]
            if frame.is_closed and uname not in frame.imports:
                if auto_dim_len > 0:
                    arr = ComalArray(uname, [(1, 10)] * auto_dim_len)
                    frame.arrays[uname] = arr
                    return arr
                raise InterpreterError(f"Tabellen '{uname}' er ikke dimensioneret i CLOSED procedure", self.current_line)

        if uname in self.global_arrays:
            return self.global_arrays[uname]
        if auto_dim_len > 0:
            arr = ComalArray(uname, [(1, 10)] * auto_dim_len)
            self.global_arrays[uname] = arr
            return arr
        raise InterpreterError(f"Tabellen '{uname}' er ikke dimensioneret (brug DIM)", self.current_line)

    def _apply_slice_read(self, text: str, slice_range: Tuple[Optional[AST], Optional[AST]]) -> str:
        start_node, end_node = slice_range
        n = len(text)
        start_idx = int(self.visit(start_node)) if start_node is not None else 1
        end_idx = int(self.visit(end_node)) if end_node is not None else n
        if start_idx < 1 or end_idx < start_idx or end_idx > n:
            raise InterpreterError(
                f"Strengindeks ({start_idx}:{end_idx}) uden for strengens længde ({n})",
                self.current_line, code=44
            )
        return text[start_idx - 1: end_idx]

    def _apply_slice_write(self, old_text: str, slice_range: Tuple[Optional[AST], Optional[AST]], new_part: str) -> str:
        start_node, end_node = slice_range
        n = len(old_text)
        start_idx = int(self.visit(start_node)) if start_node is not None else 1
        end_idx = int(self.visit(end_node)) if end_node is not None else n
        if start_idx < 1 or end_idx < start_idx or end_idx > n:
            raise InterpreterError(
                f"Strengindeks ({start_idx}:{end_idx}) uden for strengens længde ({n}) ved tildeling",
                self.current_line, code=44
            )
        span_len = end_idx - start_idx + 1
        formatted_part = str(new_part)[:span_len].ljust(span_len)
        return old_text[:start_idx - 1] + formatted_part + old_text[end_idx:]

    def visit(self, node: Optional[AST]) -> Any:
        if node is None:
            return None

        if hasattr(node, 'line') and node.line:
            self.current_line = node.line

        if self.esc_requested and self.trap_esc_enabled:
            self.esc_requested = False
            raise InterpreterError("Program afbrudt med ESC (STOP)", self.current_line, code=100)

        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        try:
            return visitor(node)
        except ComalError as ce:
            if ce.line is None or ce.line <= 0:
                ce.line = self.current_line
            raise

    def generic_visit(self, node: AST):
        raise InterpreterError(f"Manglende implementering for AST-node: {type(node).__name__}", self.current_line)

    def visit_Block(self, node: Block):
        idx = 0
        stmts = node.statements
        while idx < len(stmts):
            stmt = stmts[idx]
            if hasattr(stmt, 'line') and stmt.line:
                self.current_line = stmt.line
                self.line_counts[self.current_line] = self.line_counts.get(self.current_line, 0) + 1

            self.stmt_counter += 1
            if self.stmt_counter % 25 == 0:
                QApplication.processEvents()

            if self.trace_enabled and hasattr(stmt, 'line') and stmt.line and not isinstance(stmt, LabelStmt):
                self.ui_print(f"[{stmt.line:04d}] ", '')

            if self.debug_hook is not None and not isinstance(stmt, (LabelStmt, Data, ProcDecl, FuncDecl)):
                self.debug_hook(self, stmt)

            try:
                self.visit(stmt)
            except GotoException as ge:
                target_up = ge.target.upper()
                found_idx = None
                for i, candidate in enumerate(stmts):
                    if isinstance(candidate, LabelStmt) and candidate.name.upper() == target_up:
                        found_idx = i
                        break
                    if hasattr(candidate, 'line') and str(candidate.line) == target_up:
                        found_idx = i
                        break
                if found_idx is not None:
                    idx = found_idx
                    continue
                else:
                    raise
            idx += 1

    def visit_NullStmt(self, node: NullStmt): pass
    def visit_LabelStmt(self, node: LabelStmt): pass
    def visit_ProcDecl(self, node: ProcDecl): pass
    def visit_FuncDecl(self, node: FuncDecl): pass
    def visit_Data(self, node: Data): pass

    def visit_GotoStmt(self, node: GotoStmt):
        raise GotoException(node.target)

    def visit_Num(self, node: Num):
        return node.value

    def visit_StringVal(self, node: StringVal):
        return node.value

    def visit_Var(self, node: Var):
        uname = node.name.upper()
        if uname == 'PI':
            return math.pi
        elif uname == 'RND':
            return random.random()
        elif uname == 'EOD':
            return 1 if self.data_ptr >= len(self.data_buffer) else 0
        elif uname == 'ERR':
            return self.last_err
        elif uname == 'ERRLINE':
            return self.last_errline
        elif uname == 'ERRTEXT$':
            return self.last_errtext
        elif uname in ('TIME', 'TIMER'):
            return round(time.time() - self.start_time, 3)
        elif uname in ('KEY$', 'INKEY$'):
            return self.key_provider() if self.key_provider else ""
        elif uname in self.functions:
            return self._invoke_func(self.functions[uname], [])
        return self.get_var(uname)

    def visit_IndexedOrCall(self, node: IndexedOrCall):
        uname = node.name.upper()

        if uname in self.functions:
            val = self._invoke_func(self.functions[uname], node.args)
            if node.slice_range is not None:
                return self._apply_slice_read(str(val), node.slice_range)
            return val

        if self._is_builtin_func(uname):
            val = self._eval_builtin_func(uname, node.args)
            if node.slice_range is not None:
                return self._apply_slice_read(str(val), node.slice_range)
            return val

        is_array_var = self._is_known_array(uname)
        if uname.endswith('$') and not is_array_var:
            base_str = str(self.get_var(uname))
            if node.is_explicit_slice and node.slice_range is not None:
                return self._apply_slice_read(base_str, node.slice_range)
            elif len(node.args) == 1:
                pos_arg = node.args[0]
                return self._apply_slice_read(base_str, (pos_arg, pos_arg))
            elif len(node.args) == 2:
                return self._apply_slice_read(base_str, (node.args[0], node.args[1]))

        arr = self.get_array(uname, auto_dim_len=len(node.args))
        indices = tuple(int(round(self.visit(arg))) for arg in node.args)
        elem = arr.get(indices, self.current_line)
        if node.slice_range is not None:
            return self._apply_slice_read(str(elem), node.slice_range)
        return elem

    def _is_known_array(self, uname: str) -> bool:
        for frame in reversed(self.call_stack):
            if uname in frame.refs and isinstance(frame.refs[uname].getter(), ComalArray):
                return True
            if uname in frame.arrays:
                return True
            if frame.is_closed and uname not in frame.imports:
                return False
        return uname in self.global_arrays

    def _is_builtin_func(self, uname: str) -> bool:
        return uname in {
            'SIN', 'COS', 'TAN', 'ASN', 'ACS', 'ATN', 'RAD', 'DEG',
            'SQR', 'EXP', 'LN', 'LOG', 'ABS', 'INT', 'FRC', 'ROUND', 'SGN',
            'RND', 'LEN', 'CHR$', 'ORD', 'ASC', 'VAL', 'STR$', 'SPC$', 'TAB',
            'UPPER$', 'LOWER$', 'TRIM$', 'INSTR', 'EOF', 'NOT'
        }

    def _eval_builtin_func(self, uname: str, args: List[AST]) -> Any:
        vals = [self.visit(a) for a in args]
        try:
            if uname == 'SIN': return math.sin(float(vals[0]))
            if uname == 'COS': return math.cos(float(vals[0]))
            if uname == 'TAN': return math.tan(float(vals[0]))
            if uname == 'ASN': return math.asin(float(vals[0]))
            if uname == 'ACS': return math.acos(float(vals[0]))
            if uname == 'ATN': return math.atan(float(vals[0])) if len(vals) == 1 else math.atan2(float(vals[0]), float(vals[1]))
            if uname == 'RAD': return math.radians(float(vals[0]))
            if uname == 'DEG': return math.degrees(float(vals[0]))
            if uname == 'SQR':
                if float(vals[0]) < 0:
                    raise InterpreterError("Kvadratrod af negativt tal i SQR()", self.current_line)
                return math.sqrt(float(vals[0]))
            if uname == 'EXP': return math.exp(float(vals[0]))
            if uname == 'LN':
                if float(vals[0]) <= 0:
                    raise InterpreterError("Logaritme til ikke-positivt tal i LN()", self.current_line)
                return math.log(float(vals[0]))
            if uname == 'LOG':
                if float(vals[0]) <= 0:
                    raise InterpreterError("Logaritme til ikke-positivt tal i LOG()", self.current_line)
                return math.log10(float(vals[0]))
            if uname == 'ABS': return abs(vals[0])
            if uname == 'INT': return math.floor(float(vals[0]))
            if uname == 'FRC': return float(vals[0]) - math.floor(float(vals[0]))
            if uname == 'ROUND':
                decimals = int(vals[1]) if len(vals) > 1 else 0
                return round(float(vals[0]), decimals)
            if uname == 'SGN':
                v = float(vals[0])
                return 1 if v > 0 else (-1 if v < 0 else 0)
            if uname == 'RND':
                if not vals:
                    return random.random()
                if len(vals) == 1:
                    top = float(vals[0])
                    return random.uniform(0, top) if top <= 1.0 else random.randint(1, int(top))
                return random.randint(int(vals[0]), int(vals[1]))
            if uname == 'LEN': return len(str(vals[0]))
            if uname == 'CHR$': return chr(int(vals[0]))
            if uname in ('ORD', 'ASC'):
                s = str(vals[0])
                if not s:
                    raise InterpreterError("ORD() kaldt på tom streng", self.current_line)
                return ord(s[0])
            if uname == 'VAL':
                s = str(vals[0]).strip()
                try:
                    f = float(s)
                    return int(f) if f.is_integer() else f
                except ValueError:
                    raise InterpreterError(f"VAL() kunne ikke tolke '{s}' som et tal", self.current_line)
            if uname == 'STR$':
                v = vals[0]
                if isinstance(v, float) and v.is_integer():
                    v = int(v)
                return str(v)
            if uname == 'SPC$': return " " * max(0, int(vals[0]))
            if uname == 'TAB':
                target_col = max(1, int(vals[0]))
                spaces = max(0, target_col - 1 - self.print_col)
                return " " * spaces
            if uname == 'UPPER$': return str(vals[0]).upper()
            if uname == 'LOWER$': return str(vals[0]).lower()
            if uname == 'TRIM$': return str(vals[0]).strip()
            if uname == 'INSTR':
                hay, needle = str(vals[0]), str(vals[1])
                idx = hay.find(needle)
                return idx + 1 if idx >= 0 else 0
            if uname == 'EOF':
                fno = int(vals[0])
                if fno not in self.files:
                    raise InterpreterError(f"Fil {fno} er ikke åben", self.current_line)
                fobj = self.files[fno]['handle']
                cur = fobj.tell()
                fobj.seek(0, os.SEEK_END)
                end_pos = fobj.tell()
                fobj.seek(cur, os.SEEK_SET)
                return 1 if cur >= end_pos else 0
        except IndexError:
            raise InterpreterError(f"For få argumenter til funktionen {uname}", self.current_line)
        raise InterpreterError(f"Ukendt indbygget funktion: {uname}", self.current_line)

    def visit_UnaryOp(self, node: UnaryOp):
        val = self.visit(node.expr)
        if node.op == '-': return -val
        if node.op == '+': return +val
        if node.op == 'NOT': return 0 if val else 1
        return val

    def visit_BinOp(self, node: BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op

        if op == '+':
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if op == '-': return left - right
        if op == '*': return left * right
        if op == '/':
            if right == 0:
                raise InterpreterError("Division med nul", self.current_line, code=51)
            res = left / right
            return int(res) if isinstance(res, float) and res.is_integer() else res
        if op == '^': return left ** right
        if op == 'MOD':
            if right == 0:
                raise InterpreterError("Modulo med nul", self.current_line, code=51)
            return left % right
        if op == 'DIV':
            if right == 0:
                raise InterpreterError("Heltalsdivision (DIV) med nul", self.current_line, code=51)
            return int(left // right)

        if op == 'IN':
            sub_s, full_s = str(left), str(right)
            pos = full_s.find(sub_s)
            return (pos + 1) if pos != -1 else 0

        if op == '=': return 1 if left == right else 0
        if op == '<>': return 1 if left != right else 0
        if op == '<': return 1 if left < right else 0
        if op == '<=': return 1 if left <= right else 0
        if op == '>': return 1 if left > right else 0
        if op == '>=': return 1 if left >= right else 0

        if op == 'AND': return 1 if (bool(left) and bool(right)) else 0
        if op == 'OR': return 1 if (bool(left) or bool(right)) else 0
        if op == 'EOR': return 1 if (bool(left) ^ bool(right)) else 0

        raise InterpreterError(f"Ukendt operator: {op}", self.current_line)

    def _assign_to_target(self, target: AST, val: Any, mode: str = ':='):
        if isinstance(target, Var):
            if mode == ':+':
                val = self.get_var(target.name) + val
            elif mode == ':-':
                val = self.get_var(target.name) - val
            self.set_var(target.name, val)
            return

        if isinstance(target, IndexedOrCall):
            uname = target.name.upper()
            is_arr = self._is_known_array(uname)

            if uname.endswith('$') and not is_arr:
                old_s = str(self.get_var(uname))
                if target.is_explicit_slice and target.slice_range is not None:
                    s_range = target.slice_range
                elif len(target.args) == 1:
                    s_range = (target.args[0], target.args[0])
                elif len(target.args) == 2:
                    s_range = (target.args[0], target.args[1])
                else:
                    raise InterpreterError(f"Ugyldig streng-indeksering for '{uname}'", self.current_line)
                updated_s = self._apply_slice_write(old_s, s_range, str(val))
                self.set_var(uname, updated_s)
                return

            arr = self.get_array(uname, auto_dim_len=len(target.args))
            indices = tuple(int(round(self.visit(idx))) for idx in target.args)
            if target.slice_range is not None:
                old_elem = str(arr.get(indices, self.current_line))
                new_elem = self._apply_slice_write(old_elem, target.slice_range, str(val))
                arr.set(indices, new_elem, self.current_line)
            else:
                if mode == ':+':
                    val = arr.get(indices, self.current_line) + val
                elif mode == ':-':
                    val = arr.get(indices, self.current_line) - val
                arr.set(indices, val, self.current_line)
            return

        raise InterpreterError("Ugyldigt mål for tildeling", self.current_line)

    def visit_Assign(self, node: Assign):
        val = self.visit(node.expr)
        self._assign_to_target(node.target, val, mode=node.mode)

    def visit_Dim(self, node: Dim):
        closed_frame = None if node.is_global else self._active_closed_frame()
        for entry in node.entries:
            uname = entry.name.upper()
            str_max = int(self.visit(entry.str_len)) if entry.str_len is not None else None
            if entry.bounds:
                eval_bounds = []
                for low_e, high_e in entry.bounds:
                    low_v = int(round(self.visit(low_e)))
                    high_v = int(round(self.visit(high_e)))
                    if high_v < low_v:
                        raise InterpreterError(f"Øvre grænse ({high_v}) er mindre end nedre grænse ({low_v}) i DIM {uname}", self.current_line)
                    eval_bounds.append((low_v, high_v))
                arr = ComalArray(uname, eval_bounds, str_max_len=str_max)
                if closed_frame is not None:
                    closed_frame.arrays[uname] = arr
                else:
                    self.global_arrays[uname] = arr
            else:
                if closed_frame is not None:
                    if str_max is not None:
                        closed_frame.str_limits[uname] = str_max
                    closed_frame.locals.setdefault(uname, "" if uname.endswith('$') else 0)
                else:
                    if str_max is not None:
                        self.global_str_limits[uname] = str_max
                    self.globals.setdefault(uname, "" if uname.endswith('$') else 0)

    def visit_ImportStmt(self, node: ImportStmt):
        frame = self._active_closed_frame()
        if frame is not None:
            for name in node.names:
                frame.imports.add(name.upper())

    # --- PRINT USING: understøtter nu FLERE #-felter i samme format ---

    def _format_using(self, fmt: str, vals: List[Any]) -> str:
        """Erstatter ALLE #-felter i fmt med de tilsvarende værdier i vals.
        Hvis der er færre værdier end felter, efterlades resten som '#'.
        Hvis der er flere værdier end felter, ignoreres de overskydende."""
        if not isinstance(vals, list):
            vals = [vals]
        result = []
        val_idx = 0
        i = 0
        n = len(fmt)
        while i < n:
            ch = fmt[i]
            if ch in '#+' or (ch == '-' and i + 1 < n and fmt[i + 1] == '#'):
                # Start på et numerisk felt: [+|-]###[.###]
                j = i
                sign_prefix = ''
                if fmt[j] in '+-':
                    sign_prefix = fmt[j]
                    j += 1
                hash_start = j
                while j < n and fmt[j] == '#':
                    j += 1
                int_width = j - hash_start
                dec_width = 0
                if j < n and fmt[j] == '.':
                    dot_pos = j
                    j += 1
                    dec_start = j
                    while j < n and fmt[j] == '#':
                        j += 1
                    dec_width = j - dec_start
                    if dec_width == 0:
                        # '.' uden efterfølgende # -> behandl som literal
                        j = dot_pos
                        dec_width = 0
                total_width = int_width + dec_width + (1 if dec_width > 0 else 0) + len(sign_prefix)
                if val_idx < len(vals):
                    v = vals[val_idx]
                    val_idx += 1
                    if isinstance(v, (int, float)):
                        try:
                            formatted = f"{float(v):{sign_prefix}{total_width}.{dec_width}f}"
                        except Exception:
                            formatted = str(v)
                        if len(formatted) > total_width:
                            formatted = '*' * total_width
                        result.append(formatted)
                    else:
                        result.append(str(v))
                else:
                    result.append(fmt[i:j])
                i = j
            else:
                result.append(ch)
                i += 1
        return "".join(result)

    def visit_Print(self, node: Print):
        if node.at_pos is not None and self.ui_cursor is not None:
            r = int(self.visit(node.at_pos[0]))
            c = int(self.visit(node.at_pos[1]))
            self.ui_cursor(r, c)
            self.print_col = max(0, c - 1)

        # Hvis USING er angivet, indsæt ALLE print-værdier i formatet på én gang
        if node.using_expr is not None:
            fmt_str = str(self.visit(node.using_expr))
            all_vals = [self.visit(item.expr) for item in node.items]
            formatted_full = self._format_using(fmt_str, all_vals)
            out_chunks = [formatted_full]
            self.print_col += len(formatted_full)
        else:
            out_chunks = []
            for item in node.items:
                res = self.visit(item.expr)
                if isinstance(res, float):
                    text_piece = str(int(res)) if res.is_integer() else f"{res:.8g}"
                else:
                    text_piece = str(res)

                out_chunks.append(text_piece)
                self.print_col += len(text_piece)

                if item.sep == ',' and item is not node.items[-1]:
                    pad = self.zone_width - (self.print_col % self.zone_width)
                    out_chunks.append(" " * pad)
                    self.print_col += pad

        if node.trailing_sep == ',':
            pad = self.zone_width - (self.print_col % self.zone_width)
            out_chunks.append(" " * pad)
            self.print_col += pad
            end_char = ''
        elif node.trailing_sep == ';':
            end_char = ''
        else:
            end_char = '\n'
            self.print_col = 0

        final_str = "".join(out_chunks)
        if node.file_no is not None:
            fno = int(self.visit(node.file_no))
            if fno not in self.files:
                raise InterpreterError(f"Fil {fno} er ikke åben ved PRINT FILE", self.current_line)
            self.files[fno]['handle'].write(final_str + end_char)
            self.files[fno]['handle'].flush()
        else:
            self.ui_print(final_str, end_char)

    def visit_CursorStmt(self, node: CursorStmt):
        r = int(self.visit(node.row_expr))
        c = int(self.visit(node.col_expr))
        if self.ui_cursor:
            self.ui_cursor(r, c)
        self.print_col = max(0, c - 1)

    def visit_ZoneStmt(self, node: ZoneStmt):
        self.zone_width = max(1, int(self.visit(node.width_expr)))

    def visit_TraceStmt(self, node: TraceStmt):
        self.trace_enabled = node.enabled

    def visit_RandomizeStmt(self, node: RandomizeStmt):
        if node.seed_expr is not None:
            random.seed(self.visit(node.seed_expr))
        else:
            random.seed()

    def visit_Input(self, node: Input):
        if node.at_pos is not None and self.ui_cursor is not None:
            r = int(self.visit(node.at_pos[0]))
            c = int(self.visit(node.at_pos[1]))
            self.ui_cursor(r, c)

        if node.file_no is not None:
            fno = int(self.visit(node.file_no))
            if fno not in self.files:
                raise InterpreterError(f"Fil {fno} er ikke åben ved INPUT FILE", self.current_line)
            raw_line = self.files[fno]['handle'].readline()
            if raw_line == '':
                raise InterpreterError(f"Slut på fil (EOF) ved læsning fra fil {fno}", self.current_line, code=60)
            parts = [p.strip() for p in raw_line.rstrip('\r\n').split(',')]
            for idx, target in enumerate(node.targets):
                val = parts[idx] if idx < len(parts) else ""
                self._assign_to_target(target, val)
            return

        raw_input = self.ui_input(node.prompt)
        if len(node.targets) == 1:
            self._assign_to_target(node.targets[0], raw_input)
        else:
            parts = [p.strip() for p in raw_input.split(',')]
            for idx, target in enumerate(node.targets):
                val = parts[idx] if idx < len(parts) else ""
                self._assign_to_target(target, val)

    def visit_If(self, node: If):
        if self.visit(node.condition):
            self.visit(node.true_block)
            return
        for elif_cond, elif_block in node.elifs:
            if self.visit(elif_cond):
                self.visit(elif_block)
                return
        if node.false_block:
            self.visit(node.false_block)

    def visit_CaseStmt(self, node: CaseStmt):
        val = self.visit(node.expr)
        for matchers, block in node.when_branches:
            matched = False
            for m in matchers:
                if m.kind == 'EQ':
                    if val == self.visit(m.val1):
                        matched = True
                        break
                elif m.kind == 'RANGE':
                    low = self.visit(m.val1)
                    high = self.visit(m.val2)
                    if low <= val <= high:
                        matched = True
                        break
                elif m.kind == 'REL':
                    rhs = self.visit(m.val1)
                    if m.op == '=' and val == rhs: matched = True; break
                    if m.op == '<>' and val != rhs: matched = True; break
                    if m.op == '<' and val < rhs: matched = True; break
                    if m.op == '<=' and val <= rhs: matched = True; break
                    if m.op == '>' and val > rhs: matched = True; break
                    if m.op == '>=' and val >= rhs: matched = True; break
            if matched:
                self.visit(block)
                return
        if node.otherwise_block is not None:
            self.visit(node.otherwise_block)

    def visit_For(self, node: For):
        var_name = node.var.name
        start_val = self.visit(node.start_expr)
        end_val = self.visit(node.end_expr)
        step_val = self.visit(node.step_expr)
        if step_val == 0:
            raise InterpreterError("STEP i FOR-løkke må ikke være 0", self.current_line)

        self.set_var(var_name, start_val)
        while True:
            current = self.get_var(var_name)
            if step_val > 0 and current > end_val:
                break
            if step_val < 0 and current < end_val:
                break
            try:
                self.visit(node.block)
            except ExitLoopException:
                break
            current = self.get_var(var_name)
            self.set_var(var_name, current + step_val)

    def visit_While(self, node: While):
        while self.visit(node.condition):
            try:
                self.visit(node.block)
            except ExitLoopException:
                break

    def visit_Repeat(self, node: Repeat):
        while True:
            try:
                self.visit(node.block)
            except ExitLoopException:
                break
            if self.visit(node.condition):
                break

    def visit_LoopStmt(self, node: LoopStmt):
        while True:
            try:
                self.visit(node.block)
            except ExitLoopException:
                break

    def visit_ExitStmt(self, node: ExitStmt):
        if node.condition is None or self.visit(node.condition):
            raise ExitLoopException()

    def visit_TrapStmt(self, node: TrapStmt):
        if node.esc_toggle is not None:
            self.trap_esc_enabled = node.esc_toggle
            return
        try:
            self.visit(node.try_block)
        except ComalError as ce:
            self.last_err = ce.code
            self.last_errline = ce.line or self.current_line
            self.last_errtext = ce.raw_message
            if node.handler_block is not None:
                self.visit(node.handler_block)
            else:
                raise

    # --- REF-bindinger: fastfrys ejende frame/global ---

    def _find_owner_frame(self, uname: str) -> Optional[CallFrame]:
        for frame in reversed(self.call_stack):
            if uname in frame.locals or uname in frame.refs:
                return frame
            if frame.is_closed:
                if uname in frame.imports:
                    return None
                return None
        return None

    def _get_global_or_frame(self, uname: str) -> Any:
        if uname in self.globals:
            return self.globals[uname]
        return "" if uname.endswith('$') else 0

    def _set_global_or_frame(self, uname: str, value: Any):
        limit = self.global_str_limits.get(uname)
        self.globals[uname] = self._coerce_type(uname, value, limit)

    def _set_in_frame(self, frame: CallFrame, uname: str, value: Any):
        if uname in frame.refs:
            frame.refs[uname].setter(value)
        else:
            limit = frame.str_limits.get(uname)
            frame.locals[uname] = self._coerce_type(uname, value, limit)

    def _create_ref_binding(self, arg_node: AST) -> RefBinding:
        if isinstance(arg_node, Var):
            vname = arg_node.name
            uname = vname.upper()
            if self._is_known_array(uname):
                arr_ref = self.get_array(uname)
                return RefBinding(
                    getter=lambda a=arr_ref: a,
                    setter=lambda v, a=arr_ref: None,
                    desc=f"REF {vname}()"
                )
            owner = self._find_owner_frame(uname)
            if owner is None:
                return RefBinding(
                    getter=lambda v=uname: self._get_global_or_frame(v),
                    setter=lambda val, v=uname: self._set_global_or_frame(v, val),
                    desc=f"REF {vname}"
                )
            return RefBinding(
                getter=lambda f=owner, v=uname: (f.refs[v].getter() if v in f.refs else f.locals.get(v, "" if v.endswith('$') else 0)),
                setter=lambda val, f=owner, v=uname: self._set_in_frame(f, v, val),
                desc=f"REF {vname}"
            )
        elif isinstance(arg_node, IndexedOrCall):
            uname = arg_node.name.upper()
            arr = self.get_array(uname, auto_dim_len=len(arg_node.args))
            indices = tuple(int(round(self.visit(idx))) for idx in arg_node.args)
            line_snapshot = self.current_line
            return RefBinding(
                getter=lambda a=arr, i=indices, ln=line_snapshot: a.get(i, ln),
                setter=lambda val, a=arr, i=indices, ln=line_snapshot: a.set(i, val, ln),
                desc=f"REF {uname}{indices}"
            )
        raise InterpreterError("Argument til REF-parameter skal være en variabel eller et tabelelement", self.current_line)

    def _prepare_call_frame(self, name: str, params: List[ParamDecl], args: List[AST], is_closed: bool) -> CallFrame:
        if len(args) != len(params):
            raise InterpreterError(
                f"'{name}' forventer {len(params)} argument(er), men modtog {len(args)}",
                self.current_line
            )
        frame = CallFrame(name=name, is_closed=is_closed, call_line=self.current_line)
        for param, arg_node in zip(params, args):
            pname = param.name.upper()
            if param.is_ref or param.is_array:
                frame.refs[pname] = self._create_ref_binding(arg_node)
            else:
                val = self.visit(arg_node)
                frame.locals[pname] = self._coerce_type(pname, val)
        return frame

    def _invoke_func(self, func_decl: FuncDecl, args: List[AST]) -> Any:
        frame = self._prepare_call_frame(func_decl.name.upper(), func_decl.params, args, func_decl.is_closed)
        self.call_stack.append(frame)
        ret_val = "" if func_decl.name.endswith('$') else 0
        try:
            self.visit(func_decl.block)
        except ReturnException as re_exc:
            if re_exc.value is not None:
                ret_val = self._coerce_type(func_decl.name.upper(), re_exc.value)
        finally:
            self.call_stack.pop()
        return ret_val

    def visit_Exec(self, node: Exec):
        proc_name = node.name.upper()

        if self._try_builtin_proc(proc_name, node.args):
            return

        if proc_name not in self.procedures:
            raise InterpreterError(f"Proceduren '{proc_name}' er ikke defineret", self.current_line)

        proc = self.procedures[proc_name]
        frame = self._prepare_call_frame(proc_name, proc.params, node.args, proc.is_closed)
        self.call_stack.append(frame)
        try:
            self.visit(proc.block)
        except ReturnException:
            pass
        finally:
            self.call_stack.pop()

    def _try_builtin_proc(self, name: str, args: List[AST]) -> bool:
        if self.graphics_cb is None:
            return False

        vals = [self.visit(a) for a in args]
        if name in ('CLEAR', 'CLEARSCREEN', 'CS', 'CLS'):
            self.graphics_cb('CLEAR', ())
            return True
        if name == 'HOME':
            self.turtle_x, self.turtle_y, self.turtle_heading = 0.0, 0.0, 0.0
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name in ('PENUP', 'PU'):
            self.turtle_pen = False
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name in ('PENDOWN', 'PD'):
            self.turtle_pen = True
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name in ('FORWARD', 'FD') and len(vals) == 1:
            dist = float(vals[0])
            rad = math.radians(self.turtle_heading)
            nx = self.turtle_x + dist * math.cos(rad)
            ny = self.turtle_y + dist * math.sin(rad)
            if self.turtle_pen:
                self.graphics_cb('LINE', (self.turtle_x, self.turtle_y, nx, ny, self.turtle_color))
            self.turtle_x, self.turtle_y = nx, ny
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name in ('BACK', 'BK') and len(vals) == 1:
            dist = float(vals[0])
            rad = math.radians(self.turtle_heading)
            nx = self.turtle_x - dist * math.cos(rad)
            ny = self.turtle_y - dist * math.sin(rad)
            if self.turtle_pen:
                self.graphics_cb('LINE', (self.turtle_x, self.turtle_y, nx, ny, self.turtle_color))
            self.turtle_x, self.turtle_y = nx, ny
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name in ('LEFT', 'LT') and len(vals) == 1:
            self.turtle_heading = (self.turtle_heading + float(vals[0])) % 360.0
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name in ('RIGHT', 'RT') and len(vals) == 1:
            self.turtle_heading = (self.turtle_heading - float(vals[0])) % 360.0
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name in ('SETPOS', 'MOVETO') and len(vals) == 2:
            nx, ny = float(vals[0]), float(vals[1])
            if name == 'SETPOS' and self.turtle_pen:
                self.graphics_cb('LINE', (self.turtle_x, self.turtle_y, nx, ny, self.turtle_color))
            self.turtle_x, self.turtle_y = nx, ny
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name == 'LINETO' and len(vals) == 2:
            nx, ny = float(vals[0]), float(vals[1])
            self.graphics_cb('LINE', (self.turtle_x, self.turtle_y, nx, ny, self.turtle_color))
            self.turtle_x, self.turtle_y = nx, ny
            return True
        if name in ('SETHEADING', 'SETH') and len(vals) == 1:
            self.turtle_heading = float(vals[0]) % 360.0
            self.graphics_cb('TURTLE_STATE', (self.turtle_x, self.turtle_y, self.turtle_heading, self.turtle_pen))
            return True
        if name in ('PENCOLOR', 'PC', 'COLOR') and len(vals) >= 1:
            palette = {
                0: '#052005', 1: '#33ff33', 2: '#ffb000', 3: '#00ffff',
                4: '#ff4444', 5: '#ff55ff', 6: '#ffff55', 7: '#ffffff'
            }
            c_arg = vals[0]
            if isinstance(c_arg, (int, float)):
                self.turtle_color = palette.get(int(c_arg) % 8, '#33ff33')
            else:
                self.turtle_color = str(c_arg)
            return True
        if name == 'PLOT' and len(vals) >= 2:
            self.graphics_cb('PLOT', (float(vals[0]), float(vals[1]), self.turtle_color))
            return True
        if name == 'LINE' and len(vals) >= 4:
            self.graphics_cb('LINE', (float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3]), self.turtle_color))
            return True
        if name == 'CIRCLE' and len(vals) >= 3:
            fill = bool(vals[3]) if len(vals) >= 4 else False
            self.graphics_cb('CIRCLE', (float(vals[0]), float(vals[1]), float(vals[2]), self.turtle_color, fill))
            return True
        if name in ('RECT', 'BOX') and len(vals) >= 4:
            fill = bool(vals[4]) if len(vals) >= 5 else False
            self.graphics_cb('RECT', (float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3]), self.turtle_color, fill))
            return True
        if name == 'TEXT' and len(vals) >= 3:
            self.graphics_cb('TEXT', (float(vals[0]), float(vals[1]), str(vals[2]), self.turtle_color))
            return True
        return False

    def visit_Return(self, node: Return):
        val = self.visit(node.expr) if node.expr is not None else None
        raise ReturnException(val)

    def visit_Read(self, node: Read):
        if node.file_no is not None:
            fno = int(self.visit(node.file_no))
            if fno not in self.files:
                raise InterpreterError(f"Fil {fno} er ikke åben ved READ FILE", self.current_line)
            raw_line = self.files[fno]['handle'].readline()
            if raw_line == '':
                raise InterpreterError(f"Slut på fil (EOF) ved READ FILE {fno}", self.current_line, code=60)
            parts = [p.strip().strip('"') for p in raw_line.rstrip('\r\n').split(',')]
            for idx, target in enumerate(node.targets):
                val = parts[idx] if idx < len(parts) else ""
                self._assign_to_target(target, val)
            return

        for target in node.targets:
            if self.data_ptr >= len(self.data_buffer):
                raise InterpreterError("Løbet tør for DATA under READ (EOD)", self.current_line, code=61)
            val = self.data_buffer[self.data_ptr]
            self.data_ptr += 1
            self._assign_to_target(target, val)

    def visit_Restore(self, node: Restore):
        if node.label is None:
            self.data_ptr = 0
        else:
            lbl = node.label.upper()
            if lbl not in self.data_labels:
                raise InterpreterError(f"RESTORE-destination '{node.label}' blev ikke fundet", self.current_line)
            self.data_ptr = self.data_labels[lbl]

    def _file_candidates(self, fname: str) -> List[str]:
        """Absolutte kandidatstier for en data-fil.

        Relative filnavne løses mod arbejdsmappen, programmets eget bibliotek og
        til sidst temp-mappen. Findes filen allerede et sted, bruges den placering
        først (så en fil der er skrevet til temp også kan læses/slettes igen).
        """
        fname = os.path.expanduser(fname)
        if os.path.isabs(fname):
            return [fname]
        dirs: List[str] = []
        for d in (os.getcwd(), self.base_dir, tempfile.gettempdir(), os.path.expanduser('~')):
            if not d:
                continue
            d = os.path.abspath(os.path.expanduser(d))
            if d not in dirs:
                dirs.append(d)
        paths = [os.path.join(d, fname) for d in dirs]
        existing = [p for p in paths if os.path.exists(p)]
        return existing + [p for p in paths if p not in existing]

    def _open_data_file(self, fname: str, py_mode: str) -> Tuple[Any, str, bool]:
        """Åbner en data-fil og falder tilbage til et skrivbart bibliotek.

        Programmet kan være startet fra en app-bundle eller Finder, hvor
        arbejdsmappen er skrivebeskyttet (Errno 13). Derfor prøves flere
        kandidatstier, og tredje returværdi angiver at der blev flyttet væk
        fra arbejdsmappen pga. manglende skrivetilladelse.
        """
        cwd_path = None if os.path.isabs(os.path.expanduser(fname)) else os.path.join(os.getcwd(), os.path.expanduser(fname))
        denied = False
        last_err: Optional[Exception] = None
        tried: List[str] = []
        for path in self._file_candidates(fname):
            tried.append(path)
            try:
                if py_mode == 'r+' and not os.path.exists(path):
                    with open(path, 'w', encoding='utf-8'):
                        pass
                handle = open(path, py_mode, encoding='utf-8')
                return handle, path, (denied and path != cwd_path)
            except PermissionError as e:
                last_err = e
                if cwd_path is not None and path == cwd_path:
                    denied = True
            except OSError as e:
                last_err = e
        reason = str(last_err) if last_err is not None else 'ukendt fejl'
        raise OSError(f"{reason} (forsøgte: {', '.join(tried)})")

    def visit_OpenFile(self, node: OpenFile):
        fno = int(self.visit(node.file_no))
        fname = str(self.visit(node.filename))
        if fno in self.files:
            raise InterpreterError(f"Fil nummer {fno} er allerede åben", self.current_line)
        mode_map = {'READ': 'r', 'WRITE': 'w', 'APPEND': 'a', 'RANDOM': 'r+'}
        py_mode = mode_map.get(node.mode.upper(), 'r')
        try:
            fhandle, used_path, moved = self._open_data_file(fname, py_mode)
        except OSError as e:
            raise InterpreterError(f"Kunne ikke åbne fil '{fname}': {e}", self.current_line, code=62)
        if moved:
            self.ui_print(f"** Arbejdsmappen er ikke skrivbar - filen '{fname}' bruges som '{used_path}'\n", '\n')
        self.files[fno] = {'handle': fhandle, 'name': used_path, 'mode': node.mode.upper()}

    def visit_CloseFile(self, node: CloseFile):
        if not node.file_nos:
            for f in list(self.files.values()):
                try: f['handle'].close()
                except Exception: pass
            self.files.clear()
        else:
            for f_expr in node.file_nos:
                fno = int(self.visit(f_expr))
                if fno in self.files:
                    try: self.files[fno]['handle'].close()
                    except Exception: pass
                    del self.files[fno]

    def visit_WriteStmt(self, node: WriteStmt):
        fno = int(self.visit(node.file_no))
        if fno not in self.files:
            raise InterpreterError(f"Fil {fno} er ikke åben ved WRITE FILE", self.current_line)
        vals = []
        for e in node.exprs:
            v = self.visit(e)
            vals.append(f'"{v}"' if isinstance(v, str) else str(v))
        self.files[fno]['handle'].write(",".join(vals) + "\n")
        self.files[fno]['handle'].flush()

    def visit_DelFileStmt(self, node: DelFileStmt):
        fname = str(self.visit(node.filename_expr))
        for path in self._file_candidates(fname):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError as e:
                    raise InterpreterError(f"Kunne ikke slette filen '{fname}': {e}", self.current_line)
                return
        raise InterpreterError(f"Filen '{fname}' findes ikke", self.current_line)

    def visit_End(self, node: End):
        raise EndException()

    def visit_Stop(self, node: Stop):
        raise StopException()

    def visit_Page(self, node: Page):
        if self.ui_clear:
            self.ui_clear()
        else:
            self.ui_print("\n" * 25, '\n')
        self.print_col = 0

    def interpret(self):
        self.pre_scan(self.ast)
        try:
            self.visit(self.ast)
        finally:
            for f in list(self.files.values()):
                try: f['handle'].close()
                except Exception: pass
            self.files.clear()


# ============================================================================
# DEL 5: AUTOMATISK INDRYKNING OG STATISK KODEANALYSE
# ============================================================================

class ComalCodeTools:
    OPENERS = ('IF', 'FOR', 'WHILE', 'REPEAT', 'LOOP', 'PROC', 'FUNC', 'CASE', 'TRAP')
    CLOSERS = {
        'ENDIF': 'IF', 'ENDFOR': 'FOR', 'ENDWHILE': 'WHILE',
        'UNTIL': 'REPEAT', 'ENDLOOP': 'LOOP', 'ENDPROC': 'PROC',
        'ENDFUNC': 'FUNC', 'ENDCASE': 'CASE', 'ENDTRAP': 'TRAP'
    }
    MIDDLES = ('ELIF', 'ELSE', 'WHEN', 'OTHERWISE', 'HANDLER')

    @classmethod
    def format_program(cls, program_memory: Dict[int, str]) -> Dict[int, str]:
        formatted: Dict[int, str] = {}
        indent_level = 0

        for num in sorted(program_memory.keys()):
            raw = program_memory[num].strip()
            if not raw:
                formatted[num] = ""
                continue

            first_word = re.split(r'[\s(:=]', raw, maxsplit=1)[0].upper()
            is_single_line_if = (first_word == 'IF' and re.search(r'\bTHEN\b\s+\S+', raw, re.IGNORECASE))
            is_single_line_loop = (first_word in ('FOR', 'WHILE') and re.search(r'\bDO\b\s+\S+', raw, re.IGNORECASE))
            is_trap_esc = (first_word == 'TRAP' and re.match(r'^TRAP\s+ESC', raw, re.IGNORECASE))

            current_indent = indent_level
            if first_word in cls.CLOSERS or first_word in cls.MIDDLES:
                current_indent = max(0, indent_level - 1)

            formatted[num] = ("  " * current_indent) + raw

            if first_word in cls.CLOSERS:
                indent_level = max(0, indent_level - 1)
            elif first_word in cls.OPENERS and not (is_single_line_if or is_single_line_loop or is_trap_esc):
                indent_level += 1

        return formatted

    @classmethod
    def scan_program(cls, program_memory: Dict[int, str]) -> List[Tuple[int, str, str]]:
        diagnostics: List[Tuple[int, str, str]] = []
        stack: List[Tuple[str, int]] = []

        for num in sorted(program_memory.keys()):
            raw = program_memory[num].strip()
            if not raw:
                continue

            first_word = re.split(r'[\s(:=]', raw, maxsplit=1)[0].upper()
            is_single_line_if = (first_word == 'IF' and re.search(r'\bTHEN\b\s+\S+', raw, re.IGNORECASE))
            is_single_line_loop = (first_word in ('FOR', 'WHILE') and re.search(r'\bDO\b\s+\S+', raw, re.IGNORECASE))
            is_trap_esc = (first_word == 'TRAP' and re.match(r'^TRAP\s+ESC', raw, re.IGNORECASE))

            if first_word in cls.OPENERS and not (is_single_line_if or is_single_line_loop or is_trap_esc):
                stack.append((first_word, num))
            elif first_word in cls.CLOSERS:
                expected = cls.CLOSERS[first_word]
                if not stack:
                    diagnostics.append((num, "FEJL", f"'{first_word}' uden tilhørende '{expected}'"))
                else:
                    top_kw, top_line = stack.pop()
                    if top_kw != expected:
                        diagnostics.append((num, "FEJL", f"'{first_word}' matcher ikke '{top_kw}' fra linje {top_line:04d} (forventede slut på {top_kw})"))

        for kw, ln in stack:
            diagnostics.append((ln, "FEJL", f"Uafsluttet '{kw}'-blok startet i linje {ln:04d}"))

        if not diagnostics and program_memory:
            line_map = {}
            lines = []
            for idx, num in enumerate(sorted(program_memory.keys()), start=1):
                line_map[idx] = num
                lines.append(program_memory[num])
            try:
                lexer = Lexer("\n".join(lines), line_map=line_map)
                tokens = lexer.tokenize()
                parser = Parser(tokens)
                parser.parse()
            except ComalError as ce:
                diagnostics.append((ce.line or 0, "SYNTAKS", ce.raw_message))

        return diagnostics


# ============================================================================
# DEL 6: RC759 GRAFIKSKÆRM
# ============================================================================

class PiccolineGraphicsCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 320)
        self.commands: List[Tuple[str, Any]] = []
        self.turtle_state = (0.0, 0.0, 0.0, True)
        self.show_turtle = True

    def clear_canvas(self):
        self.commands.clear()
        self.turtle_state = (0.0, 0.0, 0.0, True)
        self.update()

    def handle_command(self, cmd: str, args: Any):
        if cmd == 'CLEAR':
            self.clear_canvas()
            return
        if cmd == 'TURTLE_STATE':
            self.turtle_state = args
            self.update()
            return
        self.commands.append((cmd, args))
        self.update()

    def _to_screen(self, x: float, y: float, cx: float, cy: float) -> QPointF:
        return QPointF(cx + x, cy - y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#041804"))

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        grid_pen = QPen(QColor("#0c350c"), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        painter.drawLine(0, int(cy), self.width(), int(cy))
        painter.drawLine(int(cx), 0, int(cx), self.height())

        for cmd, args in self.commands:
            if cmd == 'PLOT':
                x, y, col = args
                painter.setPen(QPen(QColor(col), 2))
                pt = self._to_screen(x, y, cx, cy)
                painter.drawPoint(pt)
            elif cmd == 'LINE':
                x1, y1, x2, y2, col = args
                painter.setPen(QPen(QColor(col), 1.6))
                painter.drawLine(self._to_screen(x1, y1, cx, cy), self._to_screen(x2, y2, cx, cy))
            elif cmd == 'CIRCLE':
                x, y, r, col, fill = args
                painter.setPen(QPen(QColor(col), 1.6))
                painter.setBrush(QBrush(QColor(col)) if fill else Qt.BrushStyle.NoBrush)
                pt = self._to_screen(x, y, cx, cy)
                painter.drawEllipse(pt, r, r)
            elif cmd == 'RECT':
                x1, y1, x2, y2, col, fill = args
                painter.setPen(QPen(QColor(col), 1.6))
                painter.setBrush(QBrush(QColor(col)) if fill else Qt.BrushStyle.NoBrush)
                p1 = self._to_screen(x1, y1, cx, cy)
                p2 = self._to_screen(x2, y2, cx, cy)
                painter.drawRect(QRectF(p1, p2).normalized())
            elif cmd == 'TEXT':
                x, y, txt, col = args
                painter.setPen(QPen(QColor(col), 1))
                painter.setFont(QFont("Consolas", 10))
                painter.drawText(self._to_screen(x, y, cx, cy), txt)

        if self.show_turtle:
            tx, ty, heading, pen_down = self.turtle_state
            pos = self._to_screen(tx, ty, cx, cy)
            rad = math.radians(heading)
            tip = QPointF(pos.x() + 10 * math.cos(rad), pos.y() - 10 * math.sin(rad))
            left_w = QPointF(pos.x() + 6 * math.cos(rad + 2.4), pos.y() - 6 * math.sin(rad + 2.4))
            right_w = QPointF(pos.x() + 6 * math.cos(rad - 2.4), pos.y() - 6 * math.sin(rad - 2.4))
            t_col = QColor("#ffb000") if pen_down else QColor("#66aa66")
            painter.setPen(QPen(t_col, 1.5))
            painter.drawLine(left_w, tip)
            painter.drawLine(right_w, tip)
            painter.drawLine(left_w, right_w)


# ============================================================================
# DEL 7: RC759 PICCOLINE TERMINAL & INTERAKTIVT MILJØ
# ============================================================================

DEMO_PROGRAM = {
    10: '// =====================================================',
    20: '// RC759 PICCOLINE - COMAL-80 KOMPLET DEMONSTRATION',
    30: '// =====================================================',
    40: 'PAGE',
    50: 'PRINT "=== RC759 COMAL-80 SYSTEMTEST ==="',
    60: 'DIM navn$(1:3) OF 20, tal(1:5)',
    70: 'FOR i:=1 TO 3 DO READ navn$(i)',
    80: 'DATA "Regnecentralen", "RC759 Piccoline", "COMAL-80 Rev 2.0"',
    90: 'tekst$ := "COMAL-75 ER GODT"',
    100: 'tekst$(7:8) := "80"',
    110: 'PRINT "Slicing-test: "; tekst$; " (del: "; tekst$(1:8); ")"',
    120: 'a := 12; b := 30',
    130: 'EXEC byt_og_add(a, b, sum)',
    140: 'PRINT USING "Efter REF-kald: a=##, b=##, sum=###": a, b, sum',
    150: 'PRINT "Fakultet(6) via rekursiv FUNC = "; fak(6)',
    160: 'END',
    170: 'PROC byt_og_add(REF x, REF y, REF resultat) CLOSED',
    180: '  temp := x',
    190: '  x := y',
    200: '  y := temp',
    210: '  resultat := x + y',
    220: 'ENDPROC byt_og_add',
    230: 'FUNC fak(n) CLOSED',
    240: '  IF n <= 1 THEN RETURN 1',
    250: '  RETURN n * fak(n - 1)',
    260: 'ENDFUNC fak',
}


class PiccolineTerminal(QPlainTextEdit):
    def __init__(self, main_window: 'ComalMainWindow'):
        super().__init__(main_window)
        self.main_win = main_window
        self.program_memory: Dict[int, str] = dict(DEMO_PROGRAM)

        self.auto_mode = False
        self.auto_current = 10
        self.auto_step = 10

        self.waiting_for_input = False
        self.input_buffer_result: Optional[str] = None
        self.input_start_pos: int = 0
        self.last_key_pressed: str = ""

        self.cmd_history: List[str] = []
        self.history_idx: int = -1

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #052005;
                color: #33ff33;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 15px;
                border: 2px solid #145214;
                selection-background-color: #33ff33;
                selection-color: #052005;
            }
        """)
        self.prompt = "> "
        self.print_banner()
        self.insert_prompt()

    def print_banner(self):
        self.insertPlainText(
            "================================================================\n"
            " Regnecentralen RC759 Piccoline - COMAL-80 (Rev. 2.02 Ultimate)\n"
            " Skriv HELP for kommandoer, LIST for kode eller RUN (F5).\n"
            "================================================================\n"
        )

    def insert_prompt(self):
        self.moveCursor(QTextCursor.MoveOperation.End)
        if self.auto_mode:
            while self.auto_current in self.program_memory:
                self.auto_current += self.auto_step
            self.insertPlainText(f"{self.auto_current:04d} ")
        else:
            self.insertPlainText(self.prompt)
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.input_start_pos = self.textCursor().position()

    def print_output(self, text: str, end_char: str = '\n'):
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(f"{text}{end_char}")
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.ensureCursorVisible()

    def set_cursor_rc(self, row: int, col: int):
        self.moveCursor(QTextCursor.MoveOperation.End)
        cur_col = self.textCursor().positionInBlock()
        if col - 1 > cur_col:
            self.insertPlainText(" " * (col - 1 - cur_col))

    def ask_inline_input(self, prompt_text: str) -> str:
        self.print_output(prompt_text, '')
        self.waiting_for_input = True
        self.input_buffer_result = None
        self.input_start_pos = self.textCursor().position()
        self.setFocus()

        while self.waiting_for_input:
            QApplication.processEvents()
            time.sleep(0.01)
            if self.main_win.active_interpreter and self.main_win.active_interpreter.esc_requested:
                self.waiting_for_input = False
                return ""

        return self.input_buffer_result or ""

    def poll_key(self) -> str:
        k = self.last_key_pressed
        self.last_key_pressed = ""
        return k

    def process_command(self, cmd_line: str):
        raw_line = cmd_line.rstrip()
        stripped = raw_line.strip()
        if not stripped:
            if self.auto_mode:
                self.auto_mode = False
            return

        if stripped and (not self.cmd_history or self.cmd_history[-1] != stripped):
            self.cmd_history.append(stripped)
        self.history_idx = len(self.cmd_history)

        match_line = re.match(r'^(\d+)\s*(.*)', stripped)
        if match_line:
            line_num = int(match_line.group(1))
            code = match_line.group(2).strip()
            if code:
                self.program_memory[line_num] = code
            else:
                self.program_memory.pop(line_num, None)
            if self.auto_mode:
                self.auto_current = line_num + self.auto_step
            self.main_win.refresh_code_view()
            return

        self.auto_mode = False
        cmd_upper = stripped.upper()

        if cmd_upper == "NEW":
            self.program_memory.clear()
            self.main_win.breakpoints.clear()
            self.main_win.graphics_canvas.clear_canvas()
            self.main_win.immediate_interp = None
            self.main_win.refresh_code_view()
            self.print_output("Programhukommelse nulstillet.")
            return

        elif cmd_upper.startswith("LIST"):
            self._handle_list(stripped)
            return

        elif cmd_upper == "RUN":
            self.main_win.start_execution(step_mode=False)
            return

        elif cmd_upper in ("CON", "CONTINUE"):
            self.main_win.continue_execution()
            return

        elif cmd_upper == "SCAN":
            self.main_win.run_static_scan(print_to_terminal=True)
            return

        elif cmd_upper == "VARS":
            self.main_win.print_vars_to_terminal()
            return

        elif cmd_upper.startswith("BREAK"):
            m = re.match(r'^BREAK\s+(\d+)', cmd_upper)
            if m:
                ln = int(m.group(1))
                self.main_win.toggle_breakpoint(ln, force_State=True)
                self.print_output(f"Breakpoint sat ved linje {ln:04d}")
            else:
                bps = sorted(self.main_win.breakpoints)
                self.print_output("Aktive breakpoints: " + (", ".join(f"{b:04d}" for b in bps) if bps else "Ingen"))
            return

        elif cmd_upper.startswith("UNBREAK"):
            m = re.match(r'^UNBREAK(?:\s+(\d+))?', cmd_upper)
            if m and m.group(1):
                ln = int(m.group(1))
                self.main_win.toggle_breakpoint(ln, force_State=False)
                self.print_output(f"Breakpoint fjernet ved linje {ln:04d}")
            else:
                self.main_win.breakpoints.clear()
                self.main_win.refresh_code_view()
                self.print_output("Alle breakpoints fjernet.")
            return

        elif cmd_upper.startswith("AUTO"):
            match_auto = re.match(r'^AUTO\s*(\d+)?\s*(?:,\s*(\d+))?', cmd_upper)
            if match_auto:
                self.auto_current = int(match_auto.group(1)) if match_auto.group(1) else 10
                self.auto_step = int(match_auto.group(2)) if match_auto.group(2) else 10
                self.auto_mode = True
            return

        elif cmd_upper.startswith("RENUM"):
            match_ren = re.match(r'^RENUM\s*(\d+)?\s*(?:,\s*(\d+))?', cmd_upper)
            start = int(match_ren.group(1)) if (match_ren and match_ren.group(1)) else 10
            step = int(match_ren.group(2)) if (match_ren and match_ren.group(2)) else 10
            self.renumber_program(start, step)
            return

        elif cmd_upper.startswith("DEL") and re.match(r'^DEL\s+\d+', cmd_upper):
            m_del = re.match(r'^DEL\s+(\d+)\s*(?:-\s*(\d+)?)?', cmd_upper)
            if m_del:
                s_ln = int(m_del.group(1))
                e_ln = int(m_del.group(2)) if m_del.group(2) else (max(self.program_memory.keys(), default=s_ln) if '-' in cmd_upper else s_ln)
                removed = [k for k in list(self.program_memory.keys()) if s_ln <= k <= e_ln]
                for k in removed:
                    del self.program_memory[k]
                self.main_win.refresh_code_view()
                self.print_output(f"Slettede {len(removed)} linje(r).")
            return

        elif cmd_upper.startswith("SAVE"):
            match_save = re.match(r'^SAVE\s+"([^"]+)"', stripped, re.IGNORECASE)
            if match_save:
                filename = match_save.group(1)
                if not filename.endswith('.cml'):
                    filename += '.cml'
                self.save_to_file(filename)
            else:
                self.print_output('SYNTAKSFEJL: SAVE "filnavn"')
            return

        elif cmd_upper.startswith("LOAD"):
            match_load = re.match(r'^LOAD\s+"([^"]+)"', stripped, re.IGNORECASE)
            if match_load:
                filename = match_load.group(1)
                if not filename.endswith('.cml'):
                    filename += '.cml'
                self.load_from_file(filename)
            else:
                self.print_output('SYNTAKSFEJL: LOAD "filnavn"')
            return

        elif cmd_upper == "HELP":
            self.print_output(
                "COMAL-80 SYSTEMKOMMANDOER:\n"
                "  LIST [fra][-til]  : Viser programmet med automatisk COMAL-indrykning\n"
                "  RUN (F5)          : Kører programmet i hukommelsen\n"
                "  SCAN              : Statisk struktur- og syntaksanalyse\n"
                "  AUTO [start,trin] : Automatisk linjenummerering\n"
                "  RENUM [start,trin]: Omnummererer programmet\n"
                "  DEL <fra>-<til>   : Sletter linjeinterval\n"
                "  BREAK / UNBREAK   : Sætter eller fjerner breakpoint\n"
                "  CON (F8)          : Fortsætter kørsel\n"
                "  VARS              : Udskriver alle aktive variabler\n"
                "  SAVE / LOAD \"fil\" : Gemmer eller henter .cml programfil\n"
                "  NEW / PAGE / DIR  : Nulstil hukommelse / Ryd skærm / Vis filer"
            )
            return

        self.main_win.execute_immediate(stripped)

    def _handle_list(self, cmd_str: str):
        formatted = ComalCodeTools.format_program(self.program_memory)
        m = re.match(r'^LIST\s*(?:(\d+)?\s*(-\s*(\d+)?)?)?', cmd_str.strip(), re.IGNORECASE)
        start_ln = int(m.group(1)) if (m and m.group(1)) else 0
        has_dash = bool(m and m.group(2))
        end_ln = int(m.group(3)) if (m and m.group(3)) else (999999 if has_dash or not start_ln else start_ln)

        for num in sorted(formatted.keys()):
            if start_ln <= num <= end_ln:
                bp_mark = "*" if num in self.main_win.breakpoints else " "
                self.print_output(f"{num:04d}{bp_mark} {formatted[num]}")

    def renumber_program(self, start: int = 10, step: int = 10):
        old_nums = sorted(self.program_memory.keys())
        mapping = {old_n: start + idx * step for idx, old_n in enumerate(old_nums)}
        new_mem: Dict[int, str] = {}
        new_bps = set()
        jump_ref = re.compile(r'\b(GOTO|RESTORE)\s+(\d+)\b', re.IGNORECASE)

        def _map_target(match: 're.Match') -> str:
            target = int(match.group(2))
            return f"{match.group(1)} {mapping.get(target, target)}"

        for old_n in old_nums:
            new_n = mapping[old_n]
            code = jump_ref.sub(_map_target, self.program_memory[old_n])
            new_mem[new_n] = code
            if old_n in self.main_win.breakpoints:
                new_bps.add(new_n)
        self.program_memory = new_mem
        self.main_win.breakpoints = new_bps
        self.main_win.refresh_code_view()
        self.print_output(f"Program omnummereret ({len(new_mem)} linjer).")

    def save_to_file(self, filename: str):
        try:
            formatted = ComalCodeTools.format_program(self.program_memory)
            with open(filename, 'w', encoding='utf-8') as f:
                for num in sorted(formatted.keys()):
                    f.write(f"{num:04d} {formatted[num]}\n")
            self.current_path = os.path.abspath(filename)
            self.print_output(f"Gemt som '{filename}'.")
        except Exception as e:
            self.print_output(f"FEJL VED GEM: {e}")

    def load_from_file(self, filename: str):
        if not os.path.exists(filename):
            self.print_output(f"FEJL: Filen '{filename}' findes ikke.")
            return
        try:
            self.program_memory.clear()
            auto_ln = 10
            with open(filename, 'r', encoding='utf-8') as f:
                for raw in f:
                    line = raw.strip()
                    if not line:
                        continue
                    match = re.match(r'^(\d+)\s+(.*)', line)
                    if match:
                        self.program_memory[int(match.group(1))] = match.group(2).strip()
                        auto_ln = int(match.group(1)) + 10
                    else:
                        self.program_memory[auto_ln] = line
                        auto_ln += 10
            self.current_path = os.path.abspath(filename)
            self.main_win.refresh_code_view()
            self.print_output(f"Hentet '{filename}' ({len(self.program_memory)} linjer).")
        except Exception as e:
            self.print_output(f"FEJL VED LOAD: {e}")

    def insertFromMimeData(self, source):
        text = source.text()
        if self.waiting_for_input:
            super().insertPlainText(text.replace('\n', ' '))
            return
        for line in text.splitlines():
            line_s = line.strip()
            if line_s:
                self.insertPlainText(line_s + '\n')
                self.process_command(line_s)
        self.insert_prompt()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.main_win.active_interpreter is not None:
                self.main_win.active_interpreter.esc_requested = True
            if self.waiting_for_input:
                self.waiting_for_input = False
            return

        if event.text():
            self.last_key_pressed = event.text()

        if self.waiting_for_input:
            cursor = self.textCursor()
            if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Left):
                if cursor.position() <= self.input_start_pos:
                    return
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.moveCursor(QTextCursor.MoveOperation.End)
                full_text = self.toPlainText()
                self.input_buffer_result = full_text[self.input_start_pos:]
                self.insertPlainText('\n')
                self.waiting_for_input = False
                return
            super().keyPressEvent(event)
            return

        cursor = self.textCursor()
        prompt_len = 5 if self.auto_mode else len(self.prompt)

        if event.key() == Qt.Key.Key_Up and self.cmd_history:
            self.history_idx = max(0, self.history_idx - 1)
            self._replace_current_line(self.cmd_history[self.history_idx], prompt_len)
            return
        elif event.key() == Qt.Key.Key_Down and self.cmd_history:
            self.history_idx = min(len(self.cmd_history), self.history_idx + 1)
            val = self.cmd_history[self.history_idx] if self.history_idx < len(self.cmd_history) else ""
            self._replace_current_line(val, prompt_len)
            return

        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Left):
            if cursor.positionInBlock() <= prompt_len:
                return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            self.setTextCursor(cursor)
            block_text = cursor.block().text()
            if len(block_text) >= prompt_len:
                cmd = block_text if self.auto_mode else block_text[prompt_len:]
                self.print_output("", '\n')
                self.process_command(cmd)
            if not self.main_win.is_paused:
                self.insert_prompt()
            return

        super().keyPressEvent(event)

    def _replace_current_line(self, new_cmd: str, prompt_len: int):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, prompt_len)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(new_cmd)
        self.setTextCursor(cursor)


# ============================================================================
# DEL 8: HOVEDVINDUE MED DEBUGGER
# ============================================================================

class ComalMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"RC759 Piccoline - COMAL-80 Fortolker v{COMAL80_VERSION} & Avanceret Fejlretter")
        self.resize(1360, 840)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0b190b;
                color: #b8ffb8;
                font-family: 'Segoe UI', 'Consolas', sans-serif;
            }
            QToolBar {
                background-color: #0f290f;
                border-bottom: 1px solid #226622;
                spacing: 6px;
                padding: 4px;
            }
            QPushButton {
                background-color: #143814;
                color: #55ff55;
                border: 1px solid #2d7a2d;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1f541f; }
            QPushButton:disabled { color: #3a663a; border-color: #1a3a1a; }
            QTableWidget, QTreeWidget {
                background-color: #061506;
                color: #33ff33;
                gridline-color: #144014;
                border: 1px solid #1e551e;
                font-family: 'Consolas', monospace;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #113011;
                color: #88ff88;
                border: 1px solid #1e551e;
                padding: 4px;
                font-weight: bold;
            }
            QTabWidget::pane { border: 1px solid #226622; }
            QTabBar::tab {
                background-color: #0f260f;
                color: #77cc77;
                padding: 6px 12px;
                border: 1px solid #226622;
            }
            QTabBar::tab:selected {
                background-color: #194419;
                color: #55ff55;
                font-weight: bold;
            }
        """)

        self.active_interpreter: Optional[Interpreter] = None
        self.immediate_interp: Optional[Interpreter] = None
        self.breakpoints: set = set()
        self.is_paused: bool = False
        self.step_mode: bool = False
        self.step_over_depth: Optional[int] = None
        self.current_debug_line: Optional[int] = None

        self._build_ui()
        self.refresh_code_view()

    def _build_ui(self):
        toolbar = QToolBar("COMAL-80 Kontrol")
        self.addToolBar(toolbar)

        self.btn_run = QPushButton("▶ Kør (F5)")
        self.btn_run.setShortcut(QKeySequence("F5"))
        self.btn_run.clicked.connect(lambda: self.start_execution(step_mode=False))
        toolbar.addWidget(self.btn_run)

        self.btn_step_into = QPushButton("⤵ Trin ind (F11)")
        self.btn_step_into.setShortcut(QKeySequence("F11"))
        self.btn_step_into.clicked.connect(self.step_into_action)
        toolbar.addWidget(self.btn_step_into)

        self.btn_step_over = QPushButton("↷ Trin over (F10)")
        self.btn_step_over.setShortcut(QKeySequence("F10"))
        self.btn_step_over.clicked.connect(self.step_over_action)
        toolbar.addWidget(self.btn_step_over)

        self.btn_continue = QPushButton("⏩ Fortsæt / CON (F8)")
        self.btn_continue.setShortcut(QKeySequence("F8"))
        self.btn_continue.clicked.connect(self.continue_execution)
        self.btn_continue.setEnabled(False)
        toolbar.addWidget(self.btn_continue)

        self.btn_pause = QPushButton("⏸ Pause (F6)")
        self.btn_pause.setShortcut(QKeySequence("F6"))
        self.btn_pause.clicked.connect(self.pause_execution)
        toolbar.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ Stop (Esc)")
        self.btn_stop.clicked.connect(self.stop_execution)
        toolbar.addWidget(self.btn_stop)

        toolbar.addSeparator()

        btn_scan = QPushButton("🔍 Scan struktur")
        btn_scan.clicked.connect(lambda: self.run_static_scan(print_to_terminal=True))
        toolbar.addWidget(btn_scan)

        btn_renum = QPushButton("🔢 Renum")
        btn_renum.clicked.connect(lambda: self.terminal.renumber_program(10, 10))
        toolbar.addWidget(btn_renum)

        btn_load = QPushButton("📂 Åbn .cml")
        btn_load.clicked.connect(self.open_file_dialog)
        toolbar.addWidget(btn_load)

        btn_save = QPushButton("💾 Gem .cml")
        btn_save.clicked.connect(self.save_file_dialog)
        toolbar.addWidget(btn_save)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.terminal = PiccolineTerminal(self)
        splitter.addWidget(self.terminal)

        right_panel = QSplitter(Qt.Orientation.Vertical)

        self.top_tabs = QTabWidget()

        code_widget = QWidget()
        code_layout = QVBoxLayout(code_widget)
        code_layout.setContentsMargins(4, 4, 4, 4)
        lbl_hint = QLabel("Klik på en linje for at tilføje/fjerne Breakpoint (●). Gul pil (▶) viser aktuel linje:")
        lbl_hint.setStyleSheet("color: #88dd88; font-size: 12px;")
        code_layout.addWidget(lbl_hint)

        self.code_table = QTableWidget(0, 4)
        self.code_table.setHorizontalHeaderLabels(["BP", "Linje", "Kald", "Indrykket COMAL-80-kildekode"])
        self.code_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.code_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.code_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.code_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.code_table.verticalHeader().setVisible(False)
        self.code_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.code_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.code_table.cellClicked.connect(self._on_code_Row_clicked)
        code_layout.addWidget(self.code_table)
        self.top_tabs.addTab(code_widget, "📜 Kildekode & Profilering")

        self.graphics_canvas = PiccolineGraphicsCanvas()
        self.top_tabs.addTab(self.graphics_canvas, "🐢 RC759 Grafikskærm")

        right_panel.addWidget(self.top_tabs)

        self.debug_tabs = QTabWidget()

        self.var_tree = QTreeWidget()
        self.var_tree.setHeaderLabels(["Navn / Indeks", "Værdi", "Type / Scope"])
        self.var_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.var_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.debug_tabs.addTab(self.var_tree, "🔎 Variabler & Tabeller")

        self.stack_table = QTableWidget(0, 4)
        self.stack_table.setHorizontalHeaderLabels(["Niveau", "PROC / FUNC", "Scope", "Kaldt fra linje"])
        self.stack_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stack_table.verticalHeader().setVisible(False)
        self.debug_tabs.addTab(self.stack_table, "📚 Kald-stak")

        self.data_table = QTableWidget(0, 3)
        self.data_table.setHorizontalHeaderLabels(["Peger", "Indeks", "DATA-værdi"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_table.verticalHeader().setVisible(False)
        self.debug_tabs.addTab(self.data_table, "📊 DATA-buffer")

        self.scan_table = QTableWidget(0, 3)
        self.scan_table.setHorizontalHeaderLabels(["Linje", "Type", "Beskrivelse"])
        self.scan_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.scan_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.scan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.scan_table.verticalHeader().setVisible(False)
        self.debug_tabs.addTab(self.scan_table, "🛠 Statisk Analyse")

        right_panel.addWidget(self.debug_tabs)
        right_panel.setSizes([450, 330])

        splitter.addWidget(right_panel)
        splitter.setSizes([640, 720])
        self.setCentralWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Klar - RC759 Piccoline COMAL-80 indlæst.")

    def _on_code_Row_clicked(self, row: int, col: int):
        item = self.code_table.item(row, 1)
        if item:
            ln = int(item.text())
            self.toggle_breakpoint(ln)

    def toggle_breakpoint(self, line_num: int, force_State: Optional[bool] = None):
        if force_State is True:
            self.breakpoints.add(line_num)
        elif force_State is False:
            self.breakpoints.discard(line_num)
        else:
            if line_num in self.breakpoints:
                self.breakpoints.discard(line_num)
            else:
                self.breakpoints.add(line_num)
        self.refresh_code_view()

    def refresh_code_view(self):
        formatted = ComalCodeTools.format_program(self.terminal.program_memory)
        nums = sorted(formatted.keys())
        self.code_table.setRowCount(len(nums))
        counts = self.active_interpreter.line_counts if self.active_interpreter else {}

        for row, num in enumerate(nums):
            is_bp = num in self.breakpoints
            is_cur = (num == self.current_debug_line)

            bp_text = "▶●" if (is_cur and is_bp) else ("▶" if is_cur else ("●" if is_bp else ""))
            bp_item = QTableWidgetItem(bp_text)
            bp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_cur:
                bp_item.setForeground(QColor("#ffff00"))
            elif is_bp:
                bp_item.setForeground(QColor("#ff4444"))

            ln_item = QTableWidgetItem(f"{num:04d}")
            cnt_val = counts.get(num, 0)
            cnt_item = QTableWidgetItem(str(cnt_val) if cnt_val > 0 else "")
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            code_item = QTableWidgetItem(formatted[num])

            if is_cur:
                bg = QColor("#3a4a00")
                for it in (bp_item, ln_item, cnt_item, code_item):
                    it.setBackground(bg)
            elif is_bp:
                bg = QColor("#331010")
                for it in (bp_item, ln_item, cnt_item, code_item):
                    it.setBackground(bg)

            self.code_table.setItem(row, 0, bp_item)
            self.code_table.setItem(row, 1, ln_item)
            self.code_table.setItem(row, 2, cnt_item)
            self.code_table.setItem(row, 3, code_item)

            if is_cur:
                self.code_table.scrollToItem(code_item)

        self.run_static_scan(print_to_terminal=False)

    def run_static_scan(self, print_to_terminal: bool = False):
        diags = ComalCodeTools.scan_program(self.terminal.program_memory)
        self.scan_table.setRowCount(len(diags))
        for r, (ln, kind, msg) in enumerate(diags):
            self.scan_table.setItem(r, 0, QTableWidgetItem(f"{ln:04d}" if ln else "-"))
            self.scan_table.setItem(r, 1, QTableWidgetItem(kind))
            self.scan_table.setItem(r, 2, QTableWidgetItem(msg))

        if print_to_terminal:
            if not diags:
                self.terminal.print_output("SCAN OK: Ingen struktur- eller syntaksfejl fundet.")
            else:
                for ln, kind, msg in diags:
                    self.terminal.print_output(f"SCAN [{kind}] Linje {ln:04d}: {msg}")

    def update_debugger_views(self):
        interp = self.active_interpreter
        if interp is None:
            return

        self.var_tree.clear()
        if interp.call_stack:
            top_frame = interp.call_stack[-1]
            loc_root = QTreeWidgetItem(self.var_tree, [f"Lokal ramme: {top_frame.name}", "", "CLOSED" if top_frame.is_closed else "ÅBEN"])
            for k, ref in sorted(top_frame.refs.items()):
                try: val_repr = repr(ref.getter())
                except Exception: val_repr = "<REF>"
                QTreeWidgetItem(loc_root, [k, val_repr, ref.desc])
            for k, v in sorted(top_frame.locals.items()):
                QTreeWidgetItem(loc_root, [k, repr(v), "Lokal variabel"])
            for k, arr in sorted(top_frame.arrays.items()):
                b_str = ", ".join(f"{l}:{h}" for l, h in arr.bounds)
                arr_node = QTreeWidgetItem(loc_root, [f"{k}({b_str})", f"{len(arr.data)} elementer", "Lokal tabel"])
                for idx_t, val in sorted(arr.data.items()):
                    QTreeWidgetItem(arr_node, [f"{k}{idx_t}", repr(val), "Element"])
            loc_root.setExpanded(True)

        glob_root = QTreeWidgetItem(self.var_tree, ["Globale variabler", "", "GLOBAL"])
        for k, v in sorted(interp.globals.items()):
            lim = interp.global_str_limits.get(k)
            t_info = f"STRING OF {lim}" if lim else ("STRING" if k.endswith('$') else ("INT" if k.endswith('%') else "REAL"))
            QTreeWidgetItem(glob_root, [k, repr(v), t_info])
        for k, arr in sorted(interp.global_arrays.items()):
            b_str = ", ".join(f"{l}:{h}" for l, h in arr.bounds)
            arr_node = QTreeWidgetItem(glob_root, [f"{k}({b_str})", f"{len(arr.data)} sat", "DIM Tabel"])
            for idx_t, val in sorted(arr.data.items()):
                QTreeWidgetItem(arr_node, [f"{k}{idx_t}", repr(val), "Element"])
        glob_root.setExpanded(True)

        self.stack_table.setRowCount(len(interp.call_stack))
        for idx, frame in enumerate(reversed(interp.call_stack)):
            self.stack_table.setItem(idx, 0, QTableWidgetItem(str(len(interp.call_stack) - idx)))
            self.stack_table.setItem(idx, 1, QTableWidgetItem(frame.name))
            self.stack_table.setItem(idx, 2, QTableWidgetItem("CLOSED" if frame.is_closed else "ÅBEN"))
            self.stack_table.setItem(idx, 3, QTableWidgetItem(f"{frame.call_line:04d}"))

        self.data_table.setRowCount(len(interp.data_buffer))
        for idx, d_val in enumerate(interp.data_buffer):
            ptr_mark = "▶ NÆSTE" if idx == interp.data_ptr else ""
            self.data_table.setItem(idx, 0, QTableWidgetItem(ptr_mark))
            self.data_table.setItem(idx, 1, QTableWidgetItem(str(idx + 1)))
            self.data_table.setItem(idx, 2, QTableWidgetItem(repr(d_val)))

    def print_vars_to_terminal(self):
        interp = self.active_interpreter
        if not interp:
            self.terminal.print_output("Ingen variabler (kør et program først).")
            return
        self.terminal.print_output("--- GLOBALE VARIABLER ---")
        for k, v in sorted(interp.globals.items()):
            self.terminal.print_output(f"  {k} = {repr(v)}")
        for k, arr in sorted(interp.global_arrays.items()):
            b_str = ", ".join(f"{l}:{h}" for l, h in arr.bounds)
            self.terminal.print_output(f"  DIM {k}({b_str}) -> {dict(sorted(arr.data.items()))}")

    def _debug_hook(self, interpreter: Interpreter, stmt: AST):
        line = getattr(stmt, 'line', 0)
        depth = len(interpreter.call_stack)

        should_pause = False
        if self.step_mode:
            if self.step_over_depth is None or depth <= self.step_over_depth:
                should_pause = True
        elif line in self.breakpoints:
            should_pause = True

        if should_pause:
            self.is_paused = True
            self.current_debug_line = line
            self.btn_continue.setEnabled(True)
            self.status_bar.showMessage(f"PAUSET ved linje {line:04d} — F11/F10/F8")
            self.refresh_code_view()
            self.update_debugger_views()

            while self.is_paused and not interpreter.esc_requested:
                QApplication.processEvents()
                time.sleep(0.015)

            self.current_debug_line = None
            self.btn_continue.setEnabled(False)

    def start_execution(self, step_mode: bool = False):
        if self.is_paused:
            self.step_mode = step_mode
            self.step_over_depth = None
            self.is_paused = False
            return

        if not self.terminal.program_memory:
            return

        self.step_mode = step_mode
        self.step_over_depth = None
        self.is_paused = False

        line_map: Dict[int, int] = {}
        source_lines: List[str] = []
        for idx, num in enumerate(sorted(self.terminal.program_memory.keys()), start=1):
            line_map[idx] = num
            source_lines.append(self.terminal.program_memory[num])

        source_code = "\n".join(source_lines)
        self._run_source(source_code, line_map, immediate=False)

    def execute_immediate(self, cmd_line: str):
        self.step_mode = False
        self._run_source(cmd_line, {1: 0}, immediate=True)

    def _run_source(self, source_code: str, line_map: Dict[int, int], immediate: bool = False):
        self.status_bar.showMessage("Kører COMAL-80-program...")
        try:
            lexer = Lexer(source_code, line_map=line_map)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast_root = parser.parse()

            cur_path = getattr(self.terminal, 'current_path', None)
            base_dir = os.path.dirname(os.path.abspath(cur_path)) if cur_path else None

            if immediate and self.immediate_interp is not None:
                interp = self.immediate_interp
                interp.ast = ast_root
                interp.current_line = 0
                interp.esc_requested = False
            else:
                interp = Interpreter(
                    ast_root,
                    ui_print=self.terminal.print_output,
                    ui_input=self.terminal.ask_inline_input,
                    ui_cursor=self.terminal.set_cursor_rc,
                    ui_clear=self.terminal.clear,
                    graphics_cb=self.graphics_canvas.handle_command,
                    debug_hook=self._debug_hook,
                    key_provider=self.terminal.poll_key,
                    base_dir=base_dir
                )
                if immediate:
                    self.immediate_interp = interp

            self.active_interpreter = interp
            interp.interpret()
            self.status_bar.showMessage("Kørsel fuldført.")
        except EndException:
            self.terminal.print_output("PROGRAM AFSLUTTET (END)")
            self.status_bar.showMessage("Program afsluttet normalt.")
        except StopException:
            self.terminal.print_output(f"PROGRAM STOPPET i linje {self.active_interpreter.current_line:04d}")
            self.status_bar.showMessage("Program stoppet.")
        except ComalError as ce:
            self.terminal.print_output(f"*** {ce}")
            self.status_bar.showMessage(str(ce))
        except Exception as e:
            self.terminal.print_output(f"*** INTERNT SYSTEMSTOP: {e}")
            self.status_bar.showMessage(f"Fejl: {e}")
        finally:
            self.is_paused = False
            self.current_debug_line = None
            self.btn_continue.setEnabled(False)
            self.refresh_code_view()
            self.update_debugger_views()

    def step_into_action(self):
        if not self.is_paused:
            self.start_execution(step_mode=True)
            return
        self.step_mode = True
        self.step_over_depth = None
        self.is_paused = False

    def step_over_action(self):
        if not self.is_paused:
            self.start_execution(step_mode=True)
            return
        self.step_mode = True
        self.step_over_depth = len(self.active_interpreter.call_stack) if self.active_interpreter else 0
        self.is_paused = False

    def continue_execution(self):
        if self.is_paused:
            self.step_mode = False
            self.step_over_depth = None
            self.is_paused = False
            self.status_bar.showMessage("Kører...")

    def pause_execution(self):
        if self.active_interpreter is not None and not self.is_paused:
            self.step_mode = True
            self.step_over_depth = None

    def stop_execution(self):
        if self.active_interpreter is not None:
            self.active_interpreter.esc_requested = True
        self.is_paused = False
        self.terminal.waiting_for_input = False
        self.status_bar.showMessage("Kørsel afbrudt af bruger (ESC).")

    def open_file_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Åbn COMAL-80-program", "", "COMAL-80 Filer (*.cml *.txt);;Alle filer (*)")
        if fname:
            self.terminal.load_from_file(fname)
            self.terminal.insert_prompt()

    def save_file_dialog(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Gem COMAL-80-program", "program.cml", "COMAL-80 Filer (*.cml);;Alle filer (*)")
        if fname:
            self.terminal.save_to_file(fname)
            self.terminal.insert_prompt()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ComalMainWindow()
    window.show()
    sys.exit(app.exec())