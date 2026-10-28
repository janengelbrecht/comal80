import sys
import re
import os
from dataclasses import dataclass
from typing import Any
from PySide6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget, QInputDialog
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt

# ==========================================
# DEL 1: TOKENS OG LEXER
# ==========================================

KEYWORDS = {
    'IF', 'THEN', 'ELIF', 'ELSE', 'ENDIF',
    'FOR', 'TO', 'STEP', 'DO', 'ENDFOR',
    'WHILE', 'ENDWHILE',
    'REPEAT', 'UNTIL',
    'PROC', 'ENDPROC', 'EXEC',
    'FUNC', 'ENDFUNC', 'RETURN',
    'DIM', 'OF',
    'DATA', 'READ', 'RESTORE',
    'PRINT', 'INPUT',
    'AND', 'OR', 'NOT', 'MOD', 'DIV',
    'GOTO', 'OPEN', 'CLOSE', 'FILE', 'WRITE',
    'REM', 'END', 'STOP', 'PAGE'
}

@dataclass
class Token:
    type: str
    value: Any
    line: int
    column: int

class LexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"Leksikalsk fejl i linje {line}, kolonne {column}: {message}")
        self.line = line
        self.column = column

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line_no = 1
        self.col_no = 1
        self.current_char = self.text[self.pos] if self.text else None

    def advance(self):
        if self.current_char == '\n':
            self.line_no += 1
            self.col_no = 0
        
        self.pos += 1
        self.col_no += 1
        
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char in ' \t\r':
            self.advance()

    def skip_comment(self):
        while self.current_char is not None and self.current_char != '\n':
            self.advance()

    def parse_string(self):
        result = ''
        start_col = self.col_no
        self.advance() 
        
        while self.current_char is not None and self.current_char != '"':
            result += self.current_char
            self.advance()
            
        if self.current_char is None:
            raise LexerError("Uafsluttet tekststreng", self.line_no, start_col)
            
        self.advance() 
        return Token('STRING', result, self.line_no, start_col)

    def parse_number(self):
        result = ''
        start_col = self.col_no
        
        while self.current_char is not None and self.current_char.isdigit():
            result += self.current_char
            self.advance()
            
        if self.current_char == '.':
            result += '.'
            self.advance()
            while self.current_char is not None and self.current_char.isdigit():
                result += self.current_char
                self.advance()
            return Token('REAL', float(result), self.line_no, start_col)
            
        return Token('INTEGER', int(result), self.line_no, start_col)

    def parse_identifier(self):
        result = ''
        start_col = self.col_no
        
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
            
        if self.current_char in ('%', '$'):
            result += self.current_char
            self.advance()
            
        result_upper = result.upper()
        if result_upper in KEYWORDS:
            return Token(result_upper, result_upper, self.line_no, start_col)
            
        return Token('ID', result, self.line_no, start_col)

    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char in ' \t\r':
                self.skip_whitespace()
                continue
                
            if self.current_char == '\n':
                tok = Token('NEWLINE', '\n', self.line_no, self.col_no)
                self.advance()
                return tok
                
            if self.current_char == '/' and self.pos + 1 < len(self.text) and self.text[self.pos+1] == '/':
                self.skip_comment()
                continue
                
            if self.current_char == '"':
                return self.parse_string()
                
            if self.current_char.isdigit():
                return self.parse_number()
                
            if self.current_char.isalpha():
                tok = self.parse_identifier()
                if tok.type == 'REM':
                    self.skip_comment()
                    continue
                return tok
                
            if self.current_char == ':' and self.pos + 1 < len(self.text) and self.text[self.pos+1] == '=':
                tok = Token('ASSIGN', ':=', self.line_no, self.col_no)
                self.advance(); self.advance()
                return tok
                
            if self.current_char in '<>':
                char = self.current_char
                col = self.col_no
                self.advance()
                if self.current_char in '=>':
                    char += self.current_char
                    self.advance()
                return Token('OP', char, self.line_no, col)
                
            if self.current_char in '+-*/^()=,;:':
                tok = Token('OP', self.current_char, self.line_no, self.col_no)
                self.advance()
                return tok
                
            raise LexerError(f"Ugyldigt tegn '{self.current_char}'", self.line_no, self.col_no)
            
        return Token('EOF', None, self.line_no, self.col_no)

    def tokenize(self):
        tokens = []
        while True:
            tok = self.get_next_token()
            tokens.append(tok)
            if tok.type == 'EOF':
                break
        return tokens

# ==========================================
# DEL 2: AST NODER
# ==========================================

class AST: pass

class Num(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value

class StringVal(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value

class Var(AST):
    def __init__(self, token):
        self.token = token
        self.name = token.value

class ArrayAccess(AST):
    def __init__(self, var_token, indices):
        self.token = var_token
        self.name = var_token.value
        self.indices = indices

class BinOp(AST):
    def __init__(self, left, op_token, right):
        self.left = left
        self.op_token = op_token
        self.op = op_token.value
        self.right = right

class UnaryOp(AST):
    def __init__(self, op_token, expr):
        self.op_token = op_token
        self.op = op_token.value
        self.expr = expr

class FuncCall(AST):
    def __init__(self, func_token, args):
        self.func_token = func_token
        self.name = func_token.value
        self.args = args

class Assign(AST):
    def __init__(self, target, expr):
        self.target = target
        self.expr = expr

class Print(AST):
    def __init__(self, exprs, end_char='\n'):
        self.exprs = exprs
        self.end_char = end_char

class Input(AST):
    def __init__(self, prompt, target):
        self.prompt = prompt
        self.target = target

class Dim(AST):
    def __init__(self, declarations):
        self.declarations = declarations

class Data(AST):
    def __init__(self, values):
        self.values = values

class Read(AST):
    def __init__(self, targets):
        self.targets = targets

class Restore(AST):
    def __init__(self, line_number_expr=None):
        self.line_number_expr = line_number_expr

class Block(AST):
    def __init__(self, statements):
        self.statements = statements

class If(AST):
    def __init__(self, condition, true_block, elifs, false_block):
        self.condition = condition
        self.true_block = true_block
        self.elifs = elifs
        self.false_block = false_block

class For(AST):
    def __init__(self, var, start_expr, end_expr, step_expr, block):
        self.var = var
        self.start_expr = start_expr
        self.end_expr = end_expr
        self.step_expr = step_expr
        self.block = block

class While(AST):
    def __init__(self, condition, block):
        self.condition = condition
        self.block = block

class Repeat(AST):
    def __init__(self, block, condition):
        self.block = block
        self.condition = condition

class ProcDecl(AST):
    def __init__(self, name_token, params, block):
        self.name_token = name_token
        self.name = name_token.value
        self.params = params
        self.block = block

class FuncDecl(AST):
    def __init__(self, name_token, params, block):
        self.name_token = name_token
        self.name = name_token.value
        self.params = params
        self.block = block

class Exec(AST):
    def __init__(self, proc_token, args):
        self.proc_token = proc_token
        self.name = proc_token.value
        self.args = args

class Return(AST):
    def __init__(self, expr=None):
        self.expr = expr

class End(AST): pass
class Stop(AST): pass
class Page(AST): pass

# ==========================================
# DEL 3: PARSER
# ==========================================

class ParserError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"Syntaksfejl i linje {line}, kolonne {column}: {message}")

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos] if self.tokens else None

    def error(self, message):
        line = self.current_token.line if self.current_token else "EOF"
        col = self.current_token.column if self.current_token else "EOF"
        raise ParserError(message, line, col)

    def eat(self, token_type):
        if self.current_token.type == token_type:
            self.pos += 1
            if self.pos < len(self.tokens):
                self.current_token = self.tokens[self.pos]
            else:
                self.current_token = Token('EOF', None, -1, -1)
        else:
            self.error(f"Forventede {token_type}, men fandt {self.current_token.type} ('{self.current_token.value}')")

    def skip_newlines(self):
        while self.current_token.type == 'NEWLINE':
            self.eat('NEWLINE')

    def factor(self):
        tok = self.current_token
        if tok.type == 'OP' and tok.value in ('+', '-'):
            self.eat('OP')
            return UnaryOp(tok, self.factor())
        elif tok.type == 'NOT':
            self.eat('NOT')
            return UnaryOp(tok, self.factor())
        elif tok.type in ('INTEGER', 'REAL'):
            self.eat(tok.type)
            return Num(tok)
        elif tok.type == 'STRING':
            self.eat('STRING')
            return StringVal(tok)
        elif tok.type == 'OP' and tok.value == '(':
            self.eat('OP')
            node = self.expr()
            if self.current_token.type == 'OP' and self.current_token.value == ')':
                self.eat('OP')
            else:
                self.error("Forventede lukket parentes ')'")
            return node
        elif tok.type == 'ID':
            self.eat('ID')
            if self.current_token.type == 'OP' and self.current_token.value == '(':
                self.eat('OP')
                args = []
                if not (self.current_token.type == 'OP' and self.current_token.value == ')'):
                    args.append(self.expr())
                    while self.current_token.type == 'OP' and self.current_token.value == ',':
                        self.eat('OP')
                        args.append(self.expr())
                if self.current_token.type == 'OP' and self.current_token.value == ')':
                    self.eat('OP')
                else:
                    self.error("Forventede ')' efter argumenter/indeks")
                return FuncCall(tok, args)
            else:
                return Var(tok)
        self.error(f"Uventet token i udtryk: {tok.type} '{tok.value}'")

    def term(self):
        node = self.factor()
        while self.current_token.type == 'OP' and self.current_token.value in ('*', '/', '^', 'MOD', 'DIV'):
            tok = self.current_token
            if tok.value in ('MOD', 'DIV'):
                self.eat(tok.type)
            else:
                self.eat('OP')
            node = BinOp(node, tok, self.factor())
        return node

    def arithmetic_expr(self):
        node = self.term()
        while self.current_token.type == 'OP' and self.current_token.value in ('+', '-'):
            tok = self.current_token
            self.eat('OP')
            node = BinOp(node, tok, self.term())
        return node

    def relational_expr(self):
        node = self.arithmetic_expr()
        while self.current_token.type == 'OP' and self.current_token.value in ('=', '<', '>', '<=', '>=', '<>'):
            tok = self.current_token
            self.eat('OP')
            node = BinOp(node, tok, self.arithmetic_expr())
        return node

    def expr(self):
        node = self.relational_expr()
        while self.current_token.type in ('AND', 'OR'):
            tok = self.current_token
            self.eat(tok.type)
            node = BinOp(node, tok, self.relational_expr())
        return node

    def statement(self):
        self.skip_newlines()
        if self.current_token.type == 'EOF':
            return None
            
        # Fang linjenummeret INDEN vi parser selve udtrykket
        line_no = self.current_token.line 
        
        node = self._parse_statement()
        
        # Injicér linjenummeret dynamisk i den færdige node
        if node is not None:
            node.line = line_no
            
        return node

    def _parse_statement(self):
        tok = self.current_token
        
        if tok.type == 'PRINT':
            self.eat('PRINT')
            exprs = []
            end_char = '\n'
            if self.current_token.type != 'NEWLINE' and self.current_token.type != 'EOF':
                exprs.append(self.expr())
                while self.current_token.type == 'OP' and self.current_token.value in (',', ';'):
                    sep = self.current_token.value
                    self.eat('OP')
                    if self.current_token.type in ('NEWLINE', 'EOF'):
                        end_char = '' if sep == ';' else '\t'
                        break
                    exprs.append(self.expr())
            return Print(exprs, end_char)
            
        elif tok.type == 'INPUT':
            self.eat('INPUT')
            prompt = ""
            if self.current_token.type == 'STRING':
                prompt = self.current_token.value
                self.eat('STRING')
                if self.current_token.type == 'OP' and self.current_token.value in (':', ';', ','):
                    self.eat('OP')
            target_tok = self.current_token
            self.eat('ID')
            
            if self.current_token.type == 'OP' and self.current_token.value == '(':
                self.eat('OP')
                indices = [self.expr()]
                while self.current_token.type == 'OP' and self.current_token.value == ',':
                    self.eat('OP')
                    indices.append(self.expr())
                self.eat('OP')
                target = ArrayAccess(target_tok, indices)
            else:
                target = Var(target_tok)
            return Input(prompt, target)
            
        elif tok.type == 'ID':
            var_tok = self.current_token
            self.eat('ID')
            
            args = []
            has_parens = False
            if self.current_token.type == 'OP' and self.current_token.value == '(':
                has_parens = True
                self.eat('OP')
                if not (self.current_token.type == 'OP' and self.current_token.value == ')'):
                    args.append(self.expr())
                    while self.current_token.type == 'OP' and self.current_token.value == ',':
                        self.eat('OP')
                        args.append(self.expr())
                if self.current_token.type == 'OP' and self.current_token.value == ')':
                    self.eat('OP')
                else:
                    self.error("Forventede ')'")
                    
            if self.current_token.type == 'ASSIGN' or (self.current_token.type == 'OP' and self.current_token.value == '='):
                if self.current_token.type == 'ASSIGN':
                    self.eat('ASSIGN')
                else:
                    self.eat('OP')
                
                target = ArrayAccess(var_tok, args) if has_parens else Var(var_tok)
                expr_node = self.expr()
                return Assign(target, expr_node)
            else:
                return Exec(var_tok, args)

        elif tok.type == 'EXEC':
            self.eat('EXEC')
            proc_tok = self.current_token
            self.eat('ID')
            args = []
            if self.current_token.type == 'OP' and self.current_token.value == '(':
                self.eat('OP')
                if not (self.current_token.type == 'OP' and self.current_token.value == ')'):
                    args.append(self.expr())
                    while self.current_token.type == 'OP' and self.current_token.value == ',':
                        self.eat('OP')
                        args.append(self.expr())
                self.eat('OP') 
            return Exec(proc_tok, args)
            
        elif tok.type == 'IF':
            self.eat('IF')
            cond = self.expr()
            self.eat('THEN')
            
            if self.current_token.type == 'NEWLINE':
                self.eat('NEWLINE')
                self.skip_newlines()
                true_block = self.block(['ELIF', 'ELSE', 'ENDIF'])
                
                elifs = []
                while self.current_token.type == 'ELIF':
                    self.eat('ELIF')
                    elif_cond = self.expr()
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
                single_stmt = self.statement()
                return If(cond, Block([single_stmt]), [], None)

        elif tok.type == 'FOR':
            self.eat('FOR')
            var_tok = self.current_token
            self.eat('ID')
            if self.current_token.type == 'ASSIGN':
                self.eat('ASSIGN')
            else:
                self.eat('OP') 
                
            start_expr = self.expr()
            self.eat('TO')
            end_expr = self.expr()
            
            step_expr = Num(Token('INTEGER', 1, var_tok.line, 0))
            if self.current_token.type == 'STEP':
                self.eat('STEP')
                step_expr = self.expr()
                
            self.eat('DO')
            self.skip_newlines()
            body = self.block(['ENDFOR'])
            self.eat('ENDFOR')
            return For(Var(var_tok), start_expr, end_expr, step_expr, body)

        elif tok.type == 'WHILE':
            self.eat('WHILE')
            cond = self.expr()
            self.eat('DO')
            self.skip_newlines()
            body = self.block(['ENDWHILE'])
            self.eat('ENDWHILE')
            return While(cond, body)

        elif tok.type == 'REPEAT':
            self.eat('REPEAT')
            self.skip_newlines()
            body = self.block(['UNTIL'])
            self.eat('UNTIL')
            cond = self.expr()
            return Repeat(body, cond)
            
        elif tok.type == 'PROC':
            self.eat('PROC')
            name_tok = self.current_token
            self.eat('ID')
            params = []
            
            if self.current_token.type == 'OP' and self.current_token.value == '(':
                self.eat('OP') 
                if self.current_token.type == 'OP' and self.current_token.value == ')':
                    self.eat('OP') 
                else:
                    params.append(Var(self.current_token))
                    self.eat('ID')
                    while self.current_token.type == 'OP' and self.current_token.value == ',':
                        self.eat('OP')
                        params.append(Var(self.current_token))
                        self.eat('ID')
                    if self.current_token.type == 'OP' and self.current_token.value == ')':
                        self.eat('OP')
                    else:
                        self.error("Forventede ')'")
            
            self.skip_newlines()
            body = self.block(['ENDPROC'])
            self.eat('ENDPROC')
            if self.current_token.type == 'ID':
                self.eat('ID')
            return ProcDecl(name_tok, params, body)
            
        elif tok.type == 'RETURN':
            self.eat('RETURN')
            expr = None
            if self.current_token.type != 'NEWLINE':
                expr = self.expr()
            return Return(expr)

        elif tok.type == 'DATA':
            self.eat('DATA')
            values = []
            tok = self.current_token
            if tok.type in ('INTEGER', 'REAL', 'STRING'):
                if tok.type in ('INTEGER', 'REAL'):
                    values.append(Num(tok))
                else:
                    values.append(StringVal(tok))
                self.eat(tok.type)
                while self.current_token.type == 'OP' and self.current_token.value == ',':
                    self.eat('OP')
                    tok = self.current_token
                    if tok.type in ('INTEGER', 'REAL'):
                        values.append(Num(tok))
                    else:
                        values.append(StringVal(tok))
                    self.eat(tok.type)
            return Data(values)

        elif tok.type == 'READ':
            self.eat('READ')
            targets = []
            targets.append(Var(self.current_token))
            self.eat('ID')
            while self.current_token.type == 'OP' and self.current_token.value == ',':
                self.eat('OP')
                targets.append(Var(self.current_token))
                self.eat('ID')
            return Read(targets)
            
        elif tok.type == 'RESTORE':
            self.eat('RESTORE')
            return Restore() 

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
            self.error(f"Uventet statement start: {tok.type} ('{tok.value}')")

    def block(self, end_tokens):
        statements = []
        self.skip_newlines()
        while self.current_token.type not in end_tokens and self.current_token.type != 'EOF':
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
            self.skip_newlines()
        return Block(statements)

    def parse(self):
        statements = []
        self.skip_newlines()
        while self.current_token.type != 'EOF':
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
            self.skip_newlines()
        return Block(statements)

# ==========================================
# DEL 4: INTERPRETER
# ==========================================

class ReturnException(Exception):
    def __init__(self, value=None):
        self.value = value

class InterpreterError(Exception):
    def __init__(self, message, line=None):
        self.raw_message = message
        self.line = line
        if line is not None:
            super().__init__(f"Kørselsfejl i linje {line}: {message}")
        else:
            super().__init__(f"Kørselsfejl: {message}")

class EndException(Exception): pass
class StopException(Exception): pass

class Interpreter:
    def __init__(self, ast_root, ui_print, ui_input):
        self.ast = ast_root
        self.ui_print = ui_print
        self.ui_input = ui_input
        
        self.globals = {}
        self.call_stack = []      
        self.procedures = {}      
        
        self.data_buffer = []     
        self.data_ptr = 0
        
        # Holder styr på det aktive linjenummer under evaluering
        self.current_line = None

    def pre_scan(self, node):
        if isinstance(node, Block):
            for stmt in node.statements:
                self.pre_scan(stmt)
        elif isinstance(node, ProcDecl) or type(node).__name__ == 'FuncDecl':
            self.procedures[node.name.upper()] = node
        elif isinstance(node, Data):
            for val_node in node.values:
                self.data_buffer.append(val_node.value)

    def get_var(self, name):
        name = name.upper()
        if self.call_stack and name in self.call_stack[-1]:
            return self.call_stack[-1][name]
        if name in self.globals:
            return self.globals[name]
            
        default_val = "" if name.endswith('$') else 0
        self.set_var(name, default_val)
        return default_val

    def set_var(self, name, value):
        name = name.upper()
        if name.endswith('%'):
            try: value = int(float(value))
            except: value = 0
        elif name.endswith('$'):
            value = str(value)
        else:
            try: value = float(value)
            except: value = 0.0

        if self.call_stack:
            self.call_stack[-1][name] = value
        else:
            self.globals[name] = value

    def visit(self, node):
        if node is None:
            return None
            
        # Opdater linjenummer, hvis vi bevæger os til en node med linjedata
        if hasattr(node, 'line'):
            self.current_line = node.line
        elif hasattr(node, 'token') and hasattr(node.token, 'line'):
            self.current_line = node.token.line
            
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        
        try:
            return visitor(node)
        except InterpreterError as ie:
            # Hvis fejlen ikke kender sit linjenummer, griber vi den, tilføjer det, og smider den igen
            if ie.line is None:
                raise InterpreterError(ie.raw_message, self.current_line)
            raise

    def generic_visit(self, node):
        raise InterpreterError(f"Mangler implementering for node: {type(node).__name__}")

    def visit_Block(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_Num(self, node): return node.value
    def visit_StringVal(self, node): return node.value
    def visit_Var(self, node): return self.get_var(node.name)

    def visit_ArrayAccess(self, node):
        name = node.name.upper()
        indices = tuple(int(self.visit(idx)) for idx in node.indices)
        array_key = f"{name}{indices}"
        return self.get_var(array_key)

    def visit_UnaryOp(self, node):
        val = self.visit(node.expr)
        if node.op == '-': return -val
        if node.op == '+': return +val
        if node.op == 'NOT':
            return 0 if val else 1
        return val

    def visit_BinOp(self, node):
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
            if right == 0: raise InterpreterError("Division med nul")
            return left / right
        if op == '^': return left ** right
        if op == 'MOD': return left % right
        if op == 'DIV': 
            if right == 0: raise InterpreterError("Division med nul")
            return left // right

        if op == '=': return 1 if left == right else 0
        if op == '<>': return 1 if left != right else 0
        if op == '<': return 1 if left < right else 0
        if op == '<=': return 1 if left <= right else 0
        if op == '>': return 1 if left > right else 0
        if op == '>=': return 1 if left >= right else 0
        
        if op == 'AND': return 1 if (left and right) else 0
        if op == 'OR': return 1 if (left or right) else 0

        raise InterpreterError(f"Ukendt operator: {op}")

    def visit_Assign(self, node):
        val = self.visit(node.expr)
        if type(node.target).__name__ == 'ArrayAccess':
            name = node.target.name.upper()
            indices = tuple(int(self.visit(idx)) for idx in node.target.indices)
            array_key = f"{name}{indices}"
            self.set_var(array_key, val)
        else:
            self.set_var(node.target.name, val)

    def visit_Print(self, node):
        out_str = ""
        for expr in node.exprs:
            res = self.visit(expr)
            if isinstance(res, float) and res.is_integer():
                res = int(res)
            out_str += str(res) + " "
        self.ui_print(out_str, node.end_char)

    def visit_Input(self, node):
        prompt = node.prompt
        val = self.ui_input(prompt)
        
        if type(node.target).__name__ == 'ArrayAccess':
            name = node.target.name.upper()
            indices = tuple(int(self.visit(idx)) for idx in node.target.indices)
            array_key = f"{name}{indices}"
            self.set_var(array_key, val)
        else:
            self.set_var(node.target.name, val)

    def visit_If(self, node):
        if self.visit(node.condition):
            self.visit(node.true_block)
            return

        for elif_cond, elif_block in node.elifs:
            if self.visit(elif_cond):
                self.visit(elif_block)
                return

        if node.false_block:
            self.visit(node.false_block)

    def visit_For(self, node):
        var_name = node.var.name
        start_val = self.visit(node.start_expr)
        end_val = self.visit(node.end_expr)
        step_val = self.visit(node.step_expr)
        
        self.set_var(var_name, start_val)
        
        while True:
            current = self.get_var(var_name)
            if step_val > 0 and current > end_val: break
            if step_val < 0 and current < end_val: break
            
            self.visit(node.block)
            
            current = self.get_var(var_name)
            self.set_var(var_name, current + step_val)

    def visit_While(self, node):
        while self.visit(node.condition):
            self.visit(node.block)

    def visit_Repeat(self, node):
        while True:
            self.visit(node.block)
            if self.visit(node.condition): 
                break

    def visit_ProcDecl(self, node):
        pass 

    def visit_Exec(self, node):
        proc_name = node.name.upper()
        if proc_name not in self.procedures:
            raise InterpreterError(f"Proceduren {proc_name} er ikke defineret.")
            
        proc = self.procedures[proc_name]
        
        arg_values = [self.visit(arg) for arg in node.args]
        
        local_scope = {}
        for param, val in zip(proc.params, arg_values):
            local_scope[param.name.upper()] = val
            
        self.call_stack.append(local_scope)
        
        try:
            self.visit(proc.block)
        except ReturnException:
            pass 
        finally:
            self.call_stack.pop() 

    def visit_Data(self, node):
        pass

    def visit_Read(self, node):
        for target in node.targets:
            if self.data_ptr >= len(self.data_buffer):
                raise InterpreterError("Løbet tør for DATA under READ")
            val = self.data_buffer[self.data_ptr]
            self.set_var(target.name, val)
            self.data_ptr += 1

    def visit_Restore(self, node):
        self.data_ptr = 0

    def visit_End(self, node): raise EndException()
    def visit_Stop(self, node): raise StopException()
    def visit_Page(self, node): self.ui_print("\n" * 29, '\n')

    def interpret(self):
        self.pre_scan(self.ast)
        self.visit(self.ast)

# ==========================================
# DEL 5: MILJØ & PYSIDE6 GUI (RC759 Piccoline)
# ==========================================

class PiccolineTerminal(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.program_memory = {} 
        
        self.auto_mode = False
        self.auto_current = 10
        self.auto_step = 10
        
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #052005;
                color: #33ff33;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 16px;
                border: none;
            }
        """)
        self.prompt = "> "
        self.insertPlainText("Regnecentralen COMAL-80 (Rev. 2.00)\nRC759 Piccoline Emulering\n")
        self.insertPlainText("Klar.\n")
        self.insert_prompt()

    def insert_prompt(self):
        if self.auto_mode:
            self.insertPlainText(f"{self.auto_current:04d} ")
        else:
            self.insertPlainText(self.prompt)
        self.moveCursor(QTextCursor.End)

    def print_output(self, text, end_char='\n'):
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(f"{text}{end_char}")
        self.moveCursor(QTextCursor.End)

    def ask_input(self, prompt_text):
        val, ok = QInputDialog.getText(self, "COMAL-80 INPUT", prompt_text)
        return val if ok else ""

    def process_command(self, cmd_line):
        cmd_line = cmd_line.strip()
        if not cmd_line:
            if self.auto_mode:
                self.auto_mode = False
            return

        match_line = re.match(r'^(\d+)\s*(.*)', cmd_line)
        if match_line:
            line_num = int(match_line.group(1))
            code = match_line.group(2).strip()
            
            if code:
                self.program_memory[line_num] = code
            else:
                self.program_memory.pop(line_num, None)
                
            if self.auto_mode:
                self.auto_current += self.auto_step
            return

        self.auto_mode = False
        cmd_upper = cmd_line.upper()
        
        if cmd_upper == "NEW":
            self.program_memory.clear()
            return
            
        elif cmd_upper == "LIST":
            for num in sorted(self.program_memory.keys()):
                self.print_output(f"{num:04d} {self.program_memory[num]}", '\n')
            return
            
        elif cmd_upper == "RUN":
            self.run_program()
            return
            
        elif cmd_upper.startswith("AUTO"):
            match_auto = re.match(r'^AUTO\s*(\d+)?\s*,?\s*(\d+)?', cmd_upper)
            if match_auto:
                start = int(match_auto.group(1)) if match_auto.group(1) else 10
                step = int(match_auto.group(2)) if match_auto.group(2) else 10
                self.auto_mode = True
                self.auto_current = start
                self.auto_step = step
            return

        elif cmd_upper.startswith("SAVE"):
            match_save = re.match(r'^SAVE\s+"([^"]+)"', cmd_line, re.IGNORECASE)
            if match_save:
                filename = match_save.group(1)
                if not filename.endswith('.cml'): filename += '.cml'
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        for num in sorted(self.program_memory.keys()):
                            f.write(f"{num:04d} {self.program_memory[num]}\n")
                    self.print_output(f"Gemt som {filename}", '\n')
                except Exception as e:
                    self.print_output(f"FEJL VED GEM: {e}", '\n')
            else:
                self.print_output("SYNKTAKSFEJL: SAVE \"filnavn\"", '\n')
            return

        elif cmd_upper.startswith("LOAD"):
            match_load = re.match(r'^LOAD\s+"([^"]+)"', cmd_line, re.IGNORECASE)
            if match_load:
                filename = match_load.group(1)
                if not filename.endswith('.cml'): filename += '.cml'
                if os.path.exists(filename):
                    self.program_memory.clear()
                    try:
                        with open(filename, 'r', encoding='utf-8') as f:
                            for line in f:
                                match = re.match(r'^(\d+)\s+(.*)', line.strip())
                                if match:
                                    self.program_memory[int(match.group(1))] = match.group(2)
                        self.print_output(f"Hentet {filename}", '\n')
                    except Exception as e:
                        self.print_output(f"FEJL VED LOAD: {e}", '\n')
                else:
                    self.print_output("FEJL: Filen findes ikke.", '\n')
            else:
                self.print_output("SYNKTAKSFEJL: LOAD \"filnavn\"", '\n')
            return

        self.execute_source(cmd_line)

    def run_program(self):
        source_lines = [self.program_memory[num] for num in sorted(self.program_memory.keys())]
        source_code = "\n".join(source_lines)
        if not source_code.strip():
            return
        self.execute_source(source_code)

    def execute_source(self, source_code):
        try:
            lexer = Lexer(source_code)
            tokens = lexer.tokenize()
            
            parser = Parser(tokens)
            ast_root = parser.parse()
            
            interpreter = Interpreter(ast_root, self.print_output, self.ask_input)
            interpreter.interpret()
            
        except LexerError as le:
            self.print_output(str(le), '\n')
        except ParserError as pe:
            self.print_output(str(pe), '\n')
        except InterpreterError as ie:
            self.print_output(str(ie), '\n')
        except EndException:
            self.print_output("PROGRAM AFSLUTTET", '\n')
        except StopException:
            self.print_output("PROGRAM STOPPET", '\n')
        except Exception as e:
            self.print_output(f"FATAL FEJL: {str(e)}", '\n')

    def insertFromMimeData(self, source):
        text = source.text()
        for line in text.split('\n'):
            line = line.strip()
            if line:
                self.insertPlainText(line + '\n')
                self.process_command(line)
        self.insert_prompt()

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        
        if event.key() in (Qt.Key_Backspace, Qt.Key_Left):
            cursor.movePosition(QTextCursor.StartOfBlock)
            current_col = self.textCursor().positionInBlock()
            prompt_len = 5 if self.auto_mode else len(self.prompt)
            if current_col <= prompt_len:
                return
                
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            cursor.movePosition(QTextCursor.EndOfBlock)
            self.setTextCursor(cursor)
            
            block_text = cursor.block().text()
            prompt_len = 5 if self.auto_mode else len(self.prompt)
            
            if len(block_text) >= prompt_len:
                if self.auto_mode:
                    cmd = block_text
                else:
                    cmd = block_text[prompt_len:]
                    
                self.print_output("", '\n') 
                self.process_command(cmd)
                
            self.insert_prompt()
            return
            
        super().keyPressEvent(event)

class ComalMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RC759 Piccoline - COMAL-80 (Fuldt system)")
        self.resize(1024, 768)
        
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.terminal = PiccolineTerminal()
        layout.addWidget(self.terminal)
        self.setCentralWidget(central_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ComalMainWindow()
    window.show()
    sys.exit(app.exec())