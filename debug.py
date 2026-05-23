import sys
import re
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

# ==========================================
# 1. THE OFFICIAL RUBIDIUM LEXER
# ==========================================
TOKEN_SPEC = [
    ("NUMBER",   r"\d+\.\d+|\d+"),
    ("STRING",   r'"[^"]*"'),
    ("BOOL",     r"True|False|None"),
    ("LET",      r"let\b"),
    ("MUT",      r"mut\b"),
    ("FN",       r"fn\b"),
    ("IF",       r"if\b"),
    ("WHILE",    r"while\b"),
    ("FOR",      r"for\b"),
    ("RETURN",   r"return\b"),
    ("BREAK",    r"break\b"),
    ("PRINT",    r"print\b"),
    ("TYPE",     r"\b(?:i8|i16|i32|i64|i128|i256|f4|f8|f16|f32|f64|f128|f256|str|bool|list|index|dict)\b"),
    ("IDENT",    r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("OP",       r"==|!=|<=|>=|->|=|\+|-|\*|/|<|>"),
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("LBRACE",   r"\{"),
    ("RBRACE",   r"\}"),
    ("COMMENT",  r"#[^\n]*"),
    ("SKIP",     r"[ \t]+"),
    ("NEWLINE",  r"\n"),
    ("MISMATCH", r"."),
]

token_regex = "|".join(f"(?P<{n}>{r})" for n, r in TOKEN_SPEC)

@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int = 0

def tokenize(code) -> List[Token]:
    tokens = []
    line_no = 1
    line_start = 0
    for m in re.finditer(token_regex, code):
        kind = m.lastgroup
        value = m.group()
        col = m.start() - line_start

        if kind == "NEWLINE":
            line_no += 1
            line_start = m.end()
            continue
        if kind in ("SKIP", "COMMENT"): continue
        if kind == "MISMATCH":
            print(f"\033[1;31merror[L001]\033[0m: Unexpected character '{value}' at line {line_no}")
            continue

        tokens.append(Token(kind, value, line_no, col))
    
    tokens.append(Token("EOF", "", line_no, 0))
    return tokens

# ==========================================
# 2. ABSTRACT SYNTAX TREE (AST)
# ==========================================
class ASTNode: pass

@dataclass
class VarDecl(ASTNode):
    name: Token; is_mut: bool; v_type: Optional[Token]; expr: ASTNode; line: int

@dataclass
class Assign(ASTNode):
    name: Token; expr: ASTNode; line: int

@dataclass
class PrintStmt(ASTNode):
    expr: ASTNode; line: int

@dataclass
class DropStmt(ASTNode):
    name: Token; line: int

@dataclass
class ReturnStmt(ASTNode):
    expr: Optional[ASTNode]; line: int

@dataclass
class BreakStmt(ASTNode):
    line: int

@dataclass
class ControlBlock(ASTNode):
    # Represents IF, WHILE, FOR bodies
    body: List[ASTNode]; line: int

@dataclass
class FunctionDef(ASTNode):
    name: Token; body: List[ASTNode]; line: int

@dataclass
class Literal(ASTNode):
    token: Token; value: Any

@dataclass
class Identifier(ASTNode):
    token: Token

# ==========================================
# 3. THE PARSER
# ==========================================
class ParseError(Exception): pass

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors = 0

    def current(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]

    def consume(self, expected_kind=None) -> Token:
        tok = self.current()
        if expected_kind and tok.kind != expected_kind:
            print(f"\033[1;31merror[P001]\033[0m: Expected `{expected_kind}`, got `{tok.kind}` at line {tok.line}")
            self.errors += 1
            raise ParseError()
        self.pos += 1
        return tok

    def parse(self):
        statements = []
        while self.current().kind != 'EOF':
            try:
                stmt = self.parse_statement()
                if stmt: statements.append(stmt)
            except ParseError:
                self.pos += 1 
        return statements

    def parse_statement(self):
        tok = self.current()
        if tok.kind == 'LET': return self.parse_let()
        if tok.kind == 'FN': return self.parse_fn()
        if tok.kind in ('IF', 'WHILE', 'FOR'): return self.parse_control_block()
        if tok.kind == 'RETURN': return self.parse_return()
        if tok.kind == 'BREAK': return self.parse_break()
        if tok.kind == 'PRINT': return self.parse_print()
        
        if tok.kind == 'IDENT':
            if self.pos + 1 < len(self.tokens):
                nxt = self.tokens[self.pos + 1]
                if nxt.kind == 'OP' and nxt.value == '=': return self.parse_assign()
                elif nxt.kind == 'DOT' and self.pos + 2 < len(self.tokens) and self.tokens[self.pos + 2].value == 'drop':
                    return self.parse_drop()
        
        self.consume()
        return None

    def parse_fn(self):
        line = self.consume('FN').line
        name = self.consume('IDENT')
        # Skip arguments and return types until we hit the opening bracket {
        while self.current().kind not in ('LBRACE', 'EOF'): self.consume()
        self.consume('LBRACE')
        body = []
        while self.current().kind not in ('RBRACE', 'EOF'):
            stmt = self.parse_statement()
            if stmt: body.append(stmt)
        if self.current().kind == 'RBRACE': self.consume('RBRACE')
        return FunctionDef(name, body, line)

    def parse_control_block(self):
        line = self.consume().line # Consume IF/WHILE/FOR
        while self.current().kind not in ('LBRACE', 'EOF'): self.consume()
        self.consume('LBRACE')
        body = []
        while self.current().kind not in ('RBRACE', 'EOF'):
            stmt = self.parse_statement()
            if stmt: body.append(stmt)
        if self.current().kind == 'RBRACE': self.consume('RBRACE')
        return ControlBlock(body, line)

    def parse_let(self):
        line = self.consume('LET').line
        is_mut = False
        if self.current().kind == 'MUT':
            is_mut = True; self.consume('MUT')
        name = self.consume('IDENT')
        v_type = self.consume('TYPE') if self.current().kind == 'TYPE' else None
        self.consume('OP') # '='
        expr = self.parse_expression()
        return VarDecl(name, is_mut, v_type, expr, line)

    def parse_assign(self):
        name = self.consume('IDENT')
        line = name.line
        self.consume('OP') # '='
        expr = self.parse_expression()
        return Assign(name, expr, line)

    def parse_print(self):
        line = self.consume('PRINT').line
        self.consume('LPAREN')
        expr = self.parse_expression()
        self.consume('RPAREN')
        return PrintStmt(expr, line)
        
    def parse_drop(self):
        name = self.consume('IDENT'); line = name.line
        self.consume('DOT'); self.consume('IDENT'); self.consume('LPAREN'); self.consume('RPAREN')
        return DropStmt(name, line)

    def parse_return(self):
        line = self.consume('RETURN').line
        expr = self.parse_expression() if self.current().kind not in ('NEWLINE', 'EOF', 'RBRACE') else None
        return ReturnStmt(expr, line)

    def parse_break(self):
        return BreakStmt(self.consume('BREAK').line)

    def parse_expression(self):
        tok = self.consume()
        if tok.kind == 'NUMBER': return Literal(tok, float(tok.value) if '.' in tok.value else int(tok.value))
        if tok.kind == 'STRING': return Literal(tok, tok.value.strip('"'))
        if tok.kind == 'BOOL': return Literal(tok, tok.value == 'True')
        if tok.kind == 'IDENT': return Identifier(tok)
        return Literal(tok, None)

# ==========================================
# 4. RUST-STYLE STATIC ANALYZER 
# ==========================================
class VarMetadata:
    def __init__(self, is_mut: bool, declared_line: int):
        self.is_mut = is_mut
        self.declared_line = declared_line
        self.last_used_line = declared_line
        self.is_dropped = False
        self.is_reassigned = False # Tracks if a mutable variable actually changed
        self.is_read = False       # Tracks if a variable is ever used

class StaticAnalyzer:
    def __init__(self, filepath, source_lines):
        self.env: Dict[str, VarMetadata] = {}
        self.errors = 0
        self.warnings = 0
        self.filepath = filepath
        self.source_lines = source_lines
        
        # State tracking
        self.unreachable = False
        self.unreachable_reported = set() # Prevent spamming W013 per line

    def report_error(self, code, msg, line):
        print(f"\033[1;31merror[{code}]\033[0m: {msg}")
        print(f" \033[1;36m-->\033[0m {self.filepath}:{line}")
        print(f" \033[1;36m{line:3} |\033[0m {self.source_lines[line-1].strip()}")
        print(f"     \033[1;36m|\033[0m \033[1;31m^^^\033[0m\n")
        self.errors += 1
        
    def report_warning(self, code, msg, line, hint):
        print(f"\033[1;33mwarning[{code}]\033[0m: {msg}")
        print(f" \033[1;36m-->\033[0m {self.filepath}:{line}")
        print(f" \033[1;36m{line:3} |\033[0m {self.source_lines[line-1].strip()}")
        print(f"     \033[1;36m|\033[0m \033[1;33m--- \033[0m\033[3m{hint}\033[0m\n")
        self.warnings += 1

    def run(self, ast_nodes):
        for node in ast_nodes:
            self.visit(node)
            
        # Post-scan Liveness Analysis (Check for memory leaks, unused, and unnecessary mutability)
        for var_name, meta in self.env.items():
            if not meta.is_read:
                self.report_warning("W012", f"Unused variable `{var_name}`.", meta.declared_line, hint=f"If this is intentional, prefix the name with an underscore `_{var_name}`.")
            else:
                if meta.is_mut and not meta.is_reassigned:
                    self.report_warning("W011", f"Variable `{var_name}` does not need to be mutable.", meta.declared_line, hint=f"Change `let mut {var_name}` to `let {var_name}`.")
                if not meta.is_dropped:
                    self.report_warning("W010", f"Variable `{var_name}` is never dropped. Memory leak detected.", meta.declared_line, hint=f"Add `{var_name}.drop()` right after line {meta.last_used_line}.")
                
        return self.errors == 0

    def visit(self, node):
        line = getattr(node, 'line', None)
        
        # W013: Unreachable Code Check
        if self.unreachable and line and line not in self.unreachable_reported:
            self.report_warning("W013", "Unreachable code detected.", line, hint="This statement sits after a `return` or `break` and will never execute.")
            self.unreachable_reported.add(line)
            return # Skip executing logic for dead code
            
        if isinstance(node, FunctionDef) or isinstance(node, ControlBlock):
            prev_unreachable = self.unreachable
            self.unreachable = False # Enter new block scope
            for stmt in node.body: self.visit(stmt)
            self.unreachable = prev_unreachable # Exit block scope

        elif isinstance(node, ReturnStmt) or isinstance(node, BreakStmt):
            if isinstance(node, ReturnStmt) and node.expr: self.check_expr(node.expr, node.line)
            self.unreachable = True # Next statements in this scope are dead code

        elif isinstance(node, VarDecl):
            if node.name.value in self.env:
                self.report_error("E022", f"Duplicate declaration of `{node.name.value}`", node.line)
            else:
                meta = VarMetadata(node.is_mut, node.line)
                if node.name.value.startswith('_'): meta.is_read = True # Ignore intentionally unused vars
                self.env[node.name.value] = meta
                self.check_expr(node.expr, node.line)
                
        elif isinstance(node, Assign):
            meta = self.env.get(node.name.value)
            if not meta:
                self.report_error("E002", f"Cannot find value `{node.name.value}` in scope", node.line)
            else:
                if not meta.is_mut: self.report_error("E001", f"Cannot assign twice to immutable variable `{node.name.value}`", node.line)
                elif meta.is_dropped: self.report_error("E041", f"Use of dropped variable `{node.name.value}`", node.line)
                
                meta.last_used_line = node.line
                meta.is_reassigned = True # Validates the 'mut' keyword wasn't a waste
            self.check_expr(node.expr, node.line)
            
        elif isinstance(node, PrintStmt):
            self.check_expr(node.expr, node.line)
            
        elif isinstance(node, DropStmt):
            meta = self.env.get(node.name.value)
            if meta: 
                meta.is_dropped = True
                meta.last_used_line = node.line

    def check_expr(self, expr, current_line):
        if isinstance(expr, Identifier):
            meta = self.env.get(expr.token.value)
            if not meta: self.report_error("E002", f"Cannot find value `{expr.token.value}` in scope", expr.token.line)
            else:
                meta.last_used_line = current_line
                meta.is_read = True # Validates the variable was actually used

# ==========================================
# 5. INTERACTIVE RUNTIME DEBUGGER
# ==========================================
class RuntimeDebugger:
    def __init__(self, ast, source_lines):
        self.ast = ast; self.source_lines = source_lines; self.env = {} 
        self.breakpoints = set(); self.stepping = True; self.running = True

    def run(self):
        print("\n" + "="*55)
        print(" \033[1;35m🛠️  RUBIDIUM INTERACTIVE DEBUGGER 🛠️\033[0m")
        print("="*55)
        print(" \033[3mType 'help' for commands. Starting execution...\033[0m\n")
        try:
            for node in self.ast:
                if not self.running: break
                if getattr(node, 'line', None) in self.breakpoints or self.stepping: self.interactive_loop(node)
                self.execute(node)
        except Exception as e:
            self.post_mortem(e, getattr(node, 'line', 0))

    def evaluate(self, expr):
        if isinstance(expr, Literal): return expr.value
        elif isinstance(expr, Identifier):
            if expr.token.value in self.env: return self.env[expr.token.value]
            raise NameError(f"Variable '{expr.token.value}' not found.")

    def execute(self, node):
        if isinstance(node, FunctionDef) or isinstance(node, ControlBlock):
            for stmt in node.body: self.execute(stmt)
        elif isinstance(node, VarDecl) or isinstance(node, Assign):
            self.env[node.name.value] = self.evaluate(node.expr)
        elif isinstance(node, PrintStmt):
            print(f" \033[1;32m➔ Output:\033[0m {self.evaluate(node.expr)}")
        elif isinstance(node, DropStmt):
            if node.name.value in self.env:
                del self.env[node.name.value]
                print(f" \033[1;31m➔ Dropped:\033[0m {node.name.value} freed")

    def interactive_loop(self, node):
        line = getattr(node, 'line', 0)
        print(f"\n\033[1;30m{'-'*55}\033[0m")
        print(f" \033[1;36m▶ Line {line:02d} |\033[0m \033[1;37m{self.source_lines[line - 1].strip()}\033[0m")
        print(f"\033[1;30m{'-'*55}\033[0m")
        while True:
            cmd = input("\033[1;35m(rub-dbg) > \033[0m").strip().split(" ")
            if cmd[0] in ("s", "step", ""): self.stepping = True; break
            elif cmd[0] in ("c", "continue"): self.stepping = False; break
            elif cmd[0] == "q": self.running = False; break
            elif cmd[0] == "env":
                for k, v in self.env.items(): print(f"    \033[1;33m{k:<15}\033[0m = \033[1;37m{str(v):<15}\033[0m")
            else: print("  Type 's' to step or 'c' to continue.")

    def post_mortem(self, exception, line_num):
        print(f"\n\033[1;41m FATAL CRASH \033[0m \033[1;31mLine {line_num}: {exception}\033[0m")
        @dataclass
        class CrashNode: line: int
        self.interactive_loop(CrashNode(line_num))

# ==========================================
# 6. CLI EXECUTION
# ==========================================
def main():
    if os.name == 'nt': os.system('color')
    
    args = sys.argv[1:]
    is_live = "--live" in args
    filepaths = [arg for arg in args if not arg.startswith("--")]
    if not filepaths: sys.exit(1)

    filepath = filepaths[0]
    with open(filepath, 'r') as f:
        code = f.read()
        source_lines = code.split("\n")

    start_time = time.time()
    tokens = tokenize(code)
    parser = Parser(tokens)
    ast = parser.parse()

    if is_live:
        RuntimeDebugger(ast, source_lines).run()
    else:
        analyzer = StaticAnalyzer(os.path.basename(filepath), source_lines)
        success = analyzer.run(ast)
        duration = (time.time() - start_time) * 1000
        if success:
            if analyzer.warnings > 0: print(f"\033[1;33m✔ Checked\033[0m {os.path.basename(filepath)} with {analyzer.warnings} warning(s) in {duration:.2f}ms")
            else: print(f"\033[1;32m✔ Checked\033[0m {os.path.basename(filepath)} successfully in {duration:.2f}ms")
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__": main()
