import sys
import re
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple

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
    ("CLASS",    r"class\b"),
    ("IF",       r"if\b"),
    ("WHILE",    r"while\b"),
    ("FOR",      r"for\b"),
    ("RETURN",   r"return\b"),
    ("BREAK",    r"break\b"),
    ("PRINT",    r"print\b"),
    ("IMPORT",   r"import\b"),
    ("USE",      r"use\b"),
    ("TYPE",     r"\b(?:i8|i16|i32|i64|i128|i256|f4|f8|f16|f32|f64|f128|f256|str|bool|list|index|dict)\b"),
    ("IDENT",    r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("OP",       r"==|!=|<=|>=|->|=|\+|-|\*|/|<|>"),
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("LBRACE",   r"\{"),
    ("RBRACE",   r"\}"),
    ("LBRACKET", r"\["),
    ("RBRACKET", r"\]"),
    ("COMMA",    r","),
    ("DOT",      r"\."),
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
class ImportStmt(ASTNode):
    module: Token; line: int

@dataclass
class VarDecl(ASTNode):
    name: Token; is_mut: bool; v_type: Optional[Token]; expr: Optional[ASTNode]; line: int

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
class FunctionCall(ASTNode):
    name: Token; args: List[ASTNode]; line: int

@dataclass
class ExprStmt(ASTNode):
    expr: ASTNode; line: int

@dataclass
class ReturnStmt(ASTNode):
    expr: Optional[ASTNode]; line: int

@dataclass
class BreakStmt(ASTNode):
    line: int

@dataclass
class ControlBlock(ASTNode):
    body: List[ASTNode]; line: int

@dataclass
class FunctionDef(ASTNode):
    name: Token; params: List[Tuple[str, str]]; body: List[ASTNode]; line: int; complexity: int

@dataclass
class ClassDef(ASTNode):
    name: Token; line: int

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
        if tok.kind in ('IMPORT', 'USE'): return self.parse_import()
        if tok.kind == 'LET': return self.parse_let()
        if tok.kind == 'FN': return self.parse_fn()
        if tok.kind == 'CLASS': return self.parse_class()
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
                elif nxt.kind in ('LPAREN', 'LBRACKET'):
                    return ExprStmt(self.parse_expression(), tok.line)
        
        self.consume()
        return None

    def parse_import(self):
        line = self.consume().line # IMPORT or USE
        module = self.consume('IDENT')
        return ImportStmt(module, line)

    def parse_class(self):
        line = self.consume('CLASS').line
        name = self.consume('IDENT')
        while self.current().kind not in ('LBRACE', 'EOF'): self.consume()
        self.consume('LBRACE')
        while self.current().kind not in ('RBRACE', 'EOF'): self.consume() # Skip body analysis for now
        if self.current().kind == 'RBRACE': self.consume('RBRACE')
        return ClassDef(name, line)

    def parse_fn(self):
        line = self.consume('FN').line
        name = self.consume('IDENT')
        params = []
        
        # FEATURE 1: Function Signature Parsing
        if self.current().kind == 'LPAREN':
            self.consume('LPAREN')
            while self.current().kind not in ('RPAREN', 'EOF'):
                if self.current().kind == 'IDENT':
                    p_name = self.consume('IDENT').value
                    self.consume('COLON') if self.current().kind == 'COLON' else None
                    p_type = self.consume('TYPE').value if self.current().kind == 'TYPE' else "Unknown"
                    params.append((p_name, p_type))
                if self.current().kind == 'COMMA': self.consume('COMMA')
            self.consume('RPAREN')
            
        while self.current().kind not in ('LBRACE', 'EOF'): self.consume()
        self.consume('LBRACE')
        
        body = []
        complexity = 1
        while self.current().kind not in ('RBRACE', 'EOF'):
            if self.current().kind in ('IF', 'WHILE', 'FOR'): complexity += 1
            stmt = self.parse_statement()
            if stmt: body.append(stmt)
        if self.current().kind == 'RBRACE': self.consume('RBRACE')
        
        return FunctionDef(name, params, body, line, complexity)

    def parse_control_block(self):
        line = self.consume().line 
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
        
        expr = None
        # FEATURE 3: Definite Initialization - Allow variables without assignment
        if self.current().kind == 'OP' and self.current().value == '=':
            self.consume('OP')
            expr = self.parse_expression()
            
        return VarDecl(name, is_mut, v_type, expr, line)

    def parse_assign(self):
        name = self.consume('IDENT')
        line = name.line
        self.consume('OP')
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
        if tok.kind == 'IDENT':
            if self.current().kind in ('LPAREN', 'LBRACKET'):
                close_char = 'RPAREN' if self.current().kind == 'LPAREN' else 'RBRACKET'
                self.consume()
                args = []
                while self.current().kind not in (close_char, 'EOF'):
                    args.append(self.parse_expression())
                    if self.current().kind == 'COMMA': self.consume('COMMA')
                self.consume(close_char)
                return FunctionCall(tok, args, tok.line)
            return Identifier(tok)
        return Literal(tok, None)

# ==========================================
# 4. ADVANCED LINTER & STATIC ANALYZER
# ==========================================
class VarMetadata:
    def __init__(self, is_mut: bool, declared_line: int, type_cat: str, is_initialized: bool):
        self.is_mut = is_mut
        self.declared_line = declared_line
        self.last_used_line = declared_line
        self.type_cat = type_cat
        self.is_initialized = is_initialized
        self.is_dropped = False
        self.is_reassigned = False 
        self.is_read = False       

class StaticAnalyzer:
    def __init__(self, filepath, source_lines):
        self.env: Dict[str, VarMetadata] = {}
        self.global_functions: Dict[str, FunctionDef] = {}
        self.visited_files = set() # FEATURE 2: Track imports
        
        self.errors = 0
        self.warnings = 0
        self.filepath = filepath
        self.source_lines = source_lines
        self.unreachable = False
        self.unreachable_reported = set()

    def report_error(self, code, msg, line, file=None):
        f = file or self.filepath
        print(f"\033[1;31merror[{code}]\033[0m: {msg}")
        print(f" \033[1;36m-->\033[0m {f}:{line}")
        if f == self.filepath:
            print(f" \033[1;36m{line:3} |\033[0m {self.source_lines[line-1].strip()}")
            print(f"     \033[1;36m|\033[0m \033[1;31m^^^\033[0m\n")
        self.errors += 1
        
    def report_warning(self, code, msg, line, hint):
        print(f"\033[1;33mwarning[{code}]\033[0m: {msg}")
        print(f" \033[1;36m-->\033[0m {self.filepath}:{line}")
        print(f" \033[1;36m{line:3} |\033[0m {self.source_lines[line-1].strip()}")
        print(f"     \033[1;36m|\033[0m \033[1;33m--- \033[0m\033[3m{hint}\033[0m\n")
        self.warnings += 1

    def get_type_category(self, type_str):
        if not type_str: return "Unknown"
        if type_str.startswith('i'): return "Int"
        if type_str.startswith('f'): return "Float"
        if type_str == 'str': return "String"
        if type_str == 'bool': return "Bool"
        if type_str in ('list', 'dict', 'index'): return "Collection"
        return "Unknown"

    def infer_type(self, expr):
        if isinstance(expr, Literal):
            if expr.token.kind == 'NUMBER': return "Float" if '.' in expr.token.value else "Int"
            if expr.token.kind == 'STRING': return "String"
            if expr.token.kind == 'BOOL': return "Bool"
        elif isinstance(expr, Identifier):
            meta = self.env.get(expr.token.value)
            if meta: return meta.type_cat
        elif isinstance(expr, FunctionCall):
            # Collections in Rubidium return Unknown without a deep generic system, but we recognize them
            meta = self.env.get(expr.name.value)
            if meta and meta.type_cat == "Collection": return "Unknown" 
        return "Unknown"

    def check_panics(self, tokens: List[Token]):
        # FEATURE 5: Constant Panic Detection (Math Safety)
        for i, tok in enumerate(tokens):
            if tok.kind == 'OP' and tok.value == '/':
                if i + 1 < len(tokens) and tokens[i+1].kind == 'NUMBER':
                    val = float(tokens[i+1].value) if '.' in tokens[i+1].value else int(tokens[i+1].value)
                    if val == 0:
                        self.report_error("E050", "Attempt to divide by zero. This will panic at runtime.", tok.line)

    def run(self, ast_nodes, tokens):
        self.check_panics(tokens)
        
        # Pre-load functions for signature checking
        for node in ast_nodes:
            if isinstance(node, FunctionDef):
                self.global_functions[node.name.value] = node
                
        for node in ast_nodes: self.visit(node)
        
        for var_name, meta in self.env.items():
            if not meta.is_read and not var_name.startswith('_'):
                self.report_warning("W012", f"Unused variable `{var_name}`.", meta.declared_line, hint="Prefix with an underscore if intentional.")
            else:
                if meta.is_mut and not meta.is_reassigned and meta.is_initialized:
                    self.report_warning("W011", f"Variable `{var_name}` does not need to be mutable.", meta.declared_line, hint=f"Change to `let {var_name}`.")
                if not meta.is_dropped and meta.type_cat in ("Collection", "String"):
                    self.report_warning("W010", f"Heap variable `{var_name}` is never dropped.", meta.declared_line, hint=f"Add `{var_name}.drop()` after line {meta.last_used_line}.")
        return self.errors == 0

    def visit(self, node):
        line = getattr(node, 'line', None)
        
        if self.unreachable and line and line not in self.unreachable_reported:
            self.report_warning("W013", "Unreachable code detected.", line, hint="This sits after a `return` or `break`.")
            self.unreachable_reported.add(line); return 
            
        if isinstance(node, ImportStmt):
            # FEATURE 2: Cross-File Resolution
            target_file = f"{node.module.value}.rub"
            if target_file not in self.visited_files:
                self.visited_files.add(target_file)
                if os.path.exists(target_file):
                    with open(target_file, 'r') as f:
                        sub_tokens = tokenize(f.read())
                        sub_ast = Parser(sub_tokens).parse()
                        # Extract functions from imported file to global scope
                        for sub_node in sub_ast:
                            if isinstance(sub_node, FunctionDef):
                                self.global_functions[sub_node.name.value] = sub_node
                else:
                    self.report_error("E060", f"Cannot resolve import `{node.module.value}`. File not found.", node.line)

        elif isinstance(node, FunctionDef):
            # FEATURE 4: Style & Complexity Linting
            if not re.match(r"^[a-z_][a-z0-9_]*$", node.name.value):
                self.report_warning("W021", f"Function `{node.name.value}` should be snake_case.", node.line, hint="Rename using lowercase and underscores.")
            if node.complexity >= 5:
                self.report_warning("W020", f"Function `{node.name.value}` has a cyclomatic complexity of {node.complexity}.", node.line, hint="Consider breaking this into smaller functions.")
                
            prev_unreachable = self.unreachable
            self.unreachable = False 
            for stmt in node.body: self.visit(stmt)
            self.unreachable = prev_unreachable 
            
        elif isinstance(node, ClassDef):
            if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name.value):
                self.report_warning("W022", f"Class `{node.name.value}` should be PascalCase.", node.line, hint="Capitalize the first letter.")

        elif isinstance(node, ControlBlock):
            prev_unreachable = self.unreachable
            self.unreachable = False 
            for stmt in node.body: self.visit(stmt)
            self.unreachable = prev_unreachable 

        elif isinstance(node, (ReturnStmt, BreakStmt)):
            if isinstance(node, ReturnStmt) and node.expr: self.check_expr(node.expr, node.line)
            self.unreachable = True 

        elif isinstance(node, ExprStmt):
            self.check_expr(node.expr, node.line)

        elif isinstance(node, VarDecl):
            # FEATURE 4: Style Linting
            if not re.match(r"^[a-z_][a-z0-9_]*$", node.name.value):
                self.report_warning("W021", f"Variable `{node.name.value}` should be snake_case.", node.line, hint="Rename using lowercase and underscores.")
                
            if node.name.value in self.env:
                self.report_error("E022", f"Duplicate declaration of `{node.name.value}`", node.line)
            else:
                is_initialized = node.expr is not None
                inferred_cat = self.infer_type(node.expr) if is_initialized else "Unknown"
                final_cat = inferred_cat
                
                if node.v_type:
                    declared_cat = self.get_type_category(node.v_type.value)
                    if is_initialized and declared_cat != "Unknown" and inferred_cat != "Unknown" and declared_cat != inferred_cat:
                        self.report_error("E030", f"Type mismatch: expected `{declared_cat}`, found `{inferred_cat}`", node.line)
                    final_cat = declared_cat
                    
                meta = VarMetadata(node.is_mut, node.line, final_cat, is_initialized)
                self.env[node.name.value] = meta
                if is_initialized: self.check_expr(node.expr, node.line)
                
        elif isinstance(node, Assign):
            meta = self.env.get(node.name.value)
            if not meta:
                self.report_error("E002", f"Cannot find value `{node.name.value}` in scope", node.line)
            else:
                if not meta.is_mut and meta.is_initialized: 
                    self.report_error("E001", f"Cannot assign twice to immutable variable `{node.name.value}`", node.line)
                elif meta.is_dropped: 
                    self.report_error("E041", f"Use of dropped variable `{node.name.value}`", node.line)
                
                inferred_cat = self.infer_type(node.expr)
                if meta.type_cat != "Unknown" and inferred_cat != "Unknown" and meta.type_cat != inferred_cat:
                    self.report_error("E031", f"Type mismatch: cannot assign `{inferred_cat}` to `{meta.type_cat}` variable", node.line)
                
                meta.last_used_line = node.line
                meta.is_reassigned = True 
                meta.is_initialized = True # Mark as initialized
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
            if not meta: 
                self.report_error("E002", f"Cannot find value `{expr.token.value}` in scope", expr.token.line)
            else:
                # FEATURE 3: Definite Initialization validation
                if not meta.is_initialized:
                    self.report_error("E032", f"Use of possibly uninitialized variable `{expr.token.value}`", current_line)
                meta.last_used_line = current_line
                meta.is_read = True 
                
        elif isinstance(expr, FunctionCall):
            target_name = expr.name.value
            
            # FEATURE 5: Constant Panic Detection (Zero Indexing on collections)
            meta = self.env.get(target_name)
            if meta and meta.type_cat == "Collection":
                if len(expr.args) > 0 and isinstance(expr.args[0], Literal) and expr.args[0].value == 0:
                    self.report_error("E051", f"Rubidium collections are 1-indexed. Attempted to access index 0 on `{target_name}`.", expr.line)
                meta.last_used_line = current_line
                meta.is_read = True
            else:
                # FEATURE 1: Function Signature Validation
                if target_name in self.global_functions:
                    func_def = self.global_functions[target_name]
                    if len(expr.args) != len(func_def.params):
                        self.report_error("E070", f"Function `{target_name}` expects {len(func_def.params)} arguments, but {len(expr.args)} were provided.", expr.line)
                    else:
                        for i, arg_expr in enumerate(expr.args):
                            arg_inferred = self.infer_type(arg_expr)
                            expected_type = self.get_type_category(func_def.params[i][1])
                            if expected_type != "Unknown" and arg_inferred != "Unknown" and expected_type != arg_inferred:
                                self.report_error("E071", f"Argument {i+1} for `{target_name}` should be `{expected_type}`, but found `{arg_inferred}`.", expr.line)
            
            for arg in expr.args: self.check_expr(arg, current_line)

# ==========================================
# 5. CLI EXECUTION
# ==========================================
def main():
    if os.name == 'nt': os.system('color')
    
    args = sys.argv[1:]
    filepaths = [arg for arg in args if not arg.startswith("--")]
    if not filepaths:
        print("\033[1;31merror\033[0m: No file provided to xeon debug.")
        print("Usage: python debug.py <file.rub>")
        sys.exit(1)

    filepath = filepaths[0]
    if not os.path.exists(filepath):
        print(f"\033[1;31merror\033[0m: File '{filepath}' not found.")
        sys.exit(1)

    with open(filepath, 'r') as f:
        code = f.read()
        source_lines = code.split("\n")

    start_time = time.time()
    
    # Lex & Parse current file
    tokens = tokenize(code)
    parser = Parser(tokens)
    ast = parser.parse()

    if parser.errors > 0:
        print(f"\n\033[1;31merror\033[0m: aborting due to {parser.errors} syntax error(s)")
        sys.exit(1)

    # Analyze AST
    analyzer = StaticAnalyzer(os.path.basename(filepath), source_lines)
    success = analyzer.run(ast, tokens)
    duration = (time.time() - start_time) * 1000
    
    if success:
        if analyzer.warnings > 0: 
            print(f"\033[1;33m✔ Checked\033[0m {os.path.basename(filepath)} with {analyzer.warnings} warning(s) in {duration:.2f}ms")
        else: 
            print(f"\033[1;32m✔ Checked\033[0m {os.path.basename(filepath)} successfully in {duration:.2f}ms")
        sys.exit(0)
    else:
        print(f"\n\033[1;31merror\033[0m: could not compile due to {analyzer.errors} error(s)")
        sys.exit(1)

if __name__ == "__main__": 
    main()
