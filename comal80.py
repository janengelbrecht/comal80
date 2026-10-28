import re
from dataclasses import dataclass
from typing import Any

# ==========================================
# DEL 1: TOKENS OG LEXER
# ==========================================

# COMAL-80 specifikke nøgleord
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
    'GOTO', 'OPEN', 'CLOSE', 'FILE', 'WRITE'
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
        # COMAL-80 kommentarer starter typisk med // eller er in-line
        while self.current_char is not None and self.current_char != '\n':
            self.advance()

    def parse_string(self):
        result = ''
        start_col = self.col_no
        self.advance() # Skip start-gåseøjne
        
        while self.current_char is not None and self.current_char != '"':
            result += self.current_char
            self.advance()
            
        if self.current_char is None:
            raise LexerError("Uafsluttet tekststreng", self.line_no, start_col)
            
        self.advance() # Skip slut-gåseøjne
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
            
        # Tjek for COMAL-80 typesuffiks (% for heltal, $ for strenge)
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
                return self.parse_identifier()
                
            # Operators and punctuation
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
# DEL 2: AST NODER (Abstrakt Syntakstræ)
# ==========================================

class AST:
    """Basisklasse for alle noder i syntakstræet."""
    pass

# --- 1. PRIMITIVE VÆRDIER OG VARIABLER ---
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
        self.indices = indices  # Liste af udtryk (f.eks. tabel(i% + 1))

# --- 2. UDTRYK (EXPRESSIONS) ---
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

# --- 3. ALMINDELIGE STATEMENTS ---
class Assign(AST):
    def __init__(self, target, expr):
        self.target = target  # Kan være en Var eller en ArrayAccess
        self.expr = expr

class Print(AST):
    def __init__(self, exprs, end_char='\n'):
        self.exprs = exprs
        self.end_char = end_char  # Håndterer PRINT "A", (tab) vs PRINT "A"; (ingen newline)

class Input(AST):
    def __init__(self, prompt, target):
        self.prompt = prompt
        self.target = target

class Dim(AST):
    def __init__(self, declarations):
        # Liste af tupeler: (Var_token, [størrelser...]) eller (Var_token, max_string_length)
        self.declarations = declarations

class Data(AST):
    def __init__(self, values):
        self.values = values  # Liste af konstante tokens (Num eller StringVal)

class Read(AST):
    def __init__(self, targets):
        self.targets = targets  # Liste af variabler, der modtager data

class Restore(AST):
    def __init__(self, line_number_expr=None):
        self.line_number_expr = line_number_expr

# --- 4. KONTROLSTRUKTURER ---
class Block(AST):
    def __init__(self, statements):
        self.statements = statements

class If(AST):
    def __init__(self, condition, true_block, elifs, false_block):
        self.condition = condition
        self.true_block = true_block
        self.elifs = elifs        # Liste af (condition, block) tuples
        self.false_block = false_block  # Kan være None

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

# --- 5. PROCEDURER OG FUNKTIONER ---
class ProcDecl(AST):
    def __init__(self, name_token, params, block):
        self.name_token = name_token
        self.name = name_token.value
        self.params = params  # Liste af Var noder
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
# ==========================================
# DEL 3: PARSER (Recursive Descent)
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

    # --- UDTRYK (EXPRESSIONS) ---
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
            # Tjek om det er et array-opslag, et funktionskald eller en variabel
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
                
                # Hvis vi ved det er et array vs funktion (typisk klares det i interpreteren, 
                # men vi lader AST'en skelne mellem generiske ID-kald her. Vi bruger FuncCall 
                # for nu; ArrayAccess håndteres også derhjemme under evaluering).
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
        # Håndter AND / OR på øverste niveau
        node = self.relational_expr()
        while self.current_token.type in ('AND', 'OR'):
            tok = self.current_token
            self.eat(tok.type)
            node = BinOp(node, tok, self.relational_expr())
        return node

    # --- STATEMENTS OG KONTROLSTRUKTURER ---
    def statement(self):
        self.skip_newlines()
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
            
            # Håndter array input f.eks. INPUT A(1)
            if self.current_token.type == 'OP' and self.current_token.value == '(':
                self.eat('OP')
                indices = [self.expr()]
                while self.current_token.type == 'OP' and self.current_token.value == ',':
                    self.eat('OP')
                    indices.append(self.expr())
                self.eat('OP') # Forventer ')'
                target = ArrayAccess(target_tok, indices)
            else:
                target = Var(target_tok)
            return Input(prompt, target)
            
        elif tok.type == 'ID':
            var_tok = self.current_token
            self.eat('ID')
            
            target = Var(var_tok)
            # Tjek for Array tildeling: tabel(i) := 5
            if self.current_token.type == 'OP' and self.current_token.value == '(':
                self.eat('OP')
                indices = [self.expr()]
                while self.current_token.type == 'OP' and self.current_token.value == ',':
                    self.eat('OP')
                    indices.append(self.expr())
                if self.current_token.value == ')':
                    self.eat('OP')
                target = ArrayAccess(var_tok, indices)
            
            self.eat('ASSIGN')
            expr_node = self.expr()
            return Assign(target, expr_node)

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
                self.eat('OP') # Forvent ')'
            return Exec(proc_tok, args)
            
        elif tok.type == 'IF':
            self.eat('IF')
            cond = self.expr()
            self.eat('THEN')
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

        elif tok.type == 'FOR':
            self.eat('FOR')
            var_tok = self.current_token
            self.eat('ID')
            self.eat('ASSIGN')
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
                if not (self.current_token.type == 'OP' and self.current_token.value == ')'):
                    params.append(Var(self.current_token))
                    self.eat('ID')
                    while self.current_token.type == 'OP' and self.current_token.value == ',':
                        self.eat('OP')
                        params.append(Var(self.current_token))
                        self.eat('ID')
                self.eat('OP')
            self.skip_newlines()
            body = self.block(['ENDPROC'])
            self.eat('ENDPROC')
            # Optionel name matching ved ENDPROC kan tilføjes her for striks syntaks
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
            return Restore() # Simpel RESTORE uden linjenummer pt.

        else:
            self.error(f"Uventet statement start: {tok.type} ('{tok.value}')")

    def block(self, end_tokens):
        statements = []
        self.skip_newlines()
        while self.current_token.type not in end_tokens and self.current_token.type != 'EOF':
            statements.append(self.statement())
            self.skip_newlines()
        return Block(statements)

    def parse(self):
        statements = []
        self.skip_newlines()
        while self.current_token.type != 'EOF':
            statements.append(self.statement())
            self.skip_newlines()
        return Block(statements)
# ==========================================
# DEL 4: INTERPRETER (Evaluator)
# ==========================================

class ReturnException(Exception):
    """Bruges til at hoppe ud af en PROC/FUNC med en returværdi."""
    def __init__(self, value=None):
        self.value = value

class InterpreterError(Exception):
    def __init__(self, message):
        super().__init__(f"Kørselsfejl: {message}")

class Interpreter:
    def __init__(self, ast_root, ui_print, ui_input):
        self.ast = ast_root
        self.ui_print = ui_print
        self.ui_input = ui_input
        
        self.globals = {}
        self.call_stack = []      # Liste af lokale scopes (dictionaries)
        self.procedures = {}      # Registrerede procedurer
        
        self.data_buffer = []     # Til DATA / READ
        self.data_ptr = 0

    def pre_scan(self, node):
        """Kører før selve eksekveringen for at opsamle PROC's og DATA."""
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
        # Kig først i lokalt scope, hvis vi er i en PROC
        if self.call_stack and name in self.call_stack[-1]:
            return self.call_stack[-1][name]
        # Ellers kig globalt
        if name in self.globals:
            return self.globals[name]
            
        # Implicit deklaration hvis den ikke findes
        default_val = "" if name.endswith('$') else 0
        self.set_var(name, default_val)
        return default_val

    def set_var(self, name, value):
        name = name.upper()
        # COMAL-80 Typehåndtering
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
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise InterpreterError(f"Mangler implementering for node: {type(node).__name__}")

    # --- PRIMITIVE NODER ---
    def visit_Block(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_Num(self, node): return node.value
    def visit_StringVal(self, node): return node.value
    def visit_Var(self, node): return self.get_var(node.name)

    def visit_ArrayAccess(self, node):
        # Simpel implementering af 1D/2D arrays lagret i dictionary
        name = node.name.upper()
        indices = tuple(int(self.visit(idx)) for idx in node.indices)
        array_key = f"{name}{indices}"
        return self.get_var(array_key)

    # --- UDTRYK (EXPRESSIONS) ---
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

        # Matematiske operatorer
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

        # Logiske og relationelle operatorer (Returnerer 1 for Sand, 0 for Falsk i standard COMAL-80 stil)
        if op == '=': return 1 if left == right else 0
        if op == '<>': return 1 if left != right else 0
        if op == '<': return 1 if left < right else 0
        if op == '<=': return 1 if left <= right else 0
        if op == '>': return 1 if left > right else 0
        if op == '>=': return 1 if left >= right else 0
        
        if op == 'AND': return 1 if (left and right) else 0
        if op == 'OR': return 1 if (left or right) else 0

        raise InterpreterError(f"Ukendt operator: {op}")

    # --- STATEMENTS ---
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
            # Simuler COMAL formatering: Heltal udskrives uden decimaler
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

    # --- KONTROLSTRUKTURER ---
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
            
            # Opdater variablen
            current = self.get_var(var_name)
            self.set_var(var_name, current + step_val)

    def visit_While(self, node):
        while self.visit(node.condition):
            self.visit(node.block)

    def visit_Repeat(self, node):
        while True:
            self.visit(node.block)
            if self.visit(node.condition):  # REPEAT ... UNTIL condition er opfyldt
                break

    # --- PROCEDURER / DATA ---
    def visit_ProcDecl(self, node):
        pass # Opsamles i pre_scan

    def visit_Exec(self, node):
        proc_name = node.name.upper()
        if proc_name not in self.procedures:
            raise InterpreterError(f"Proceduren {proc_name} er ikke defineret.")
            
        proc = self.procedures[proc_name]
        
        # Evaluer argumenter i nuværende scope
        arg_values = [self.visit(arg) for arg in node.args]
        
        # Opret nyt lokalt scope
        local_scope = {}
        for param, val in zip(proc.params, arg_values):
            local_scope[param.name.upper()] = val
            
        self.call_stack.append(local_scope)
        
        try:
            self.visit(proc.block)
        except ReturnException:
            pass # PROC kan returnere tidligt
        finally:
            self.call_stack.pop() # Fjern lokalt scope uanset hvad

    def visit_Data(self, node):
        pass # Opsamles i pre_scan

    def visit_Read(self, node):
        for target in node.targets:
            if self.data_ptr >= len(self.data_buffer):
                raise InterpreterError("Løbet tør for DATA under READ")
            val = self.data_buffer[self.data_ptr]
            self.set_var(target.name, val)
            self.data_ptr += 1

    def visit_Restore(self, node):
        self.data_ptr = 0

    # --- KØRSEL ---
    def interpret(self):
        self.pre_scan(self.ast)
        self.visit(self.ast)
import sys
import re
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget, QInputDialog
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt

# ==========================================
# DEL 5: MILJØ & PYSIDE6 GUI (RC759 Piccoline)
# ==========================================

class PiccolineTerminal(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.program_memory = {}  # Hukommelse for linjenumre: { 10: "PRINT 1" }
        
        # AUTO-mode tilstand
        self.auto_mode = False
        self.auto_current = 10
        self.auto_step = 10
        
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
            # En tom linje afslutter AUTO mode i standard COMAL
            if self.auto_mode:
                self.auto_mode = False
            return

        # 1. Er det indtastning af kildekode? (Starter med et tal)
        match_line = re.match(r'^(\d+)\s*(.*)', cmd_line)
        if match_line:
            line_num = int(match_line.group(1))
            code = match_line.group(2).strip()
            
            if code:
                # RC's editor tjekker typisk syntaks ved indtastning. 
                # For at gøre det, kunne vi køre Lexer/Parser på den enkelte linje her,
                # men for at tillade ufærdige blokke (IF uden ENDIF) gemmer vi den bare råt:
                self.program_memory[line_num] = code
            else:
                # Slet linje hvis koden er tom
                self.program_memory.pop(line_num, None)
                
            if self.auto_mode:
                self.auto_current += self.auto_step
            return

        # Hvis vi er i AUTO-mode og brugeren taster en kommando, afbrydes AUTO
        self.auto_mode = False

        # 2. Miljø-kommandoer
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

        # 3. Direct mode (Eksekver som en enkelt linje kode)
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
        except Exception as e:
            self.print_output(f"FATAL FEJL: {str(e)}", '\n')
    def insertFromMimeData(self, source):
        """Håndterer Copy/Paste ved at indlæse én linje ad gangen."""
        text = source.text()
        for line in text.split('\n'):
            line = line.strip()
            if line:
                # Simuler at brugeren taster linjen og trykker Enter
                self.insertPlainText(line + '\n')
                self.process_command(line)
        self.insert_prompt()
    def keyPressEvent(self, event):
        cursor = self.textCursor()
        
        # Sikr at brugeren ikke kan slette prompten eller rykke venstre for den
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
                # Hvis vi er i auto_mode, består prompten af "0010 ", som også er en del af koden
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