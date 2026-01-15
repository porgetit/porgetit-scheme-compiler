from lark import Transformer, v_args
from ast_nodes import *

class LispTransformer(Transformer):
    def start(self, items):
        return items[0]

    def program(self, items):
        return Program(items)

    def definition(self, items):
        # definition: "(" "define" variable expression ")"
        #           | "(" "define" "(" variable def_formals ")" body ")"
        # grammar rules have different structures, we need to handle them.
        # But 'items' will be a list of children.
        # Let's inspect the first child to disambiguate or rely on token names if visible.
        # Actually in Lark, we can name the alternatives in grammar or check types.
        # For simplicity, if items[1] is a list/formals, it's a function def.
        
        # NOTE: In our grammar, "define" is a token in the rule, but might be filtered out or present as Token.
        # Lark passes children. "define" is a generic string match in grammar unless it's a terminal.
        # In lisp.lark: definition: "(" "define" variable expression ")"
        # "define" is anon terminal, so it likely won't be in items if filter is on, OR it will be a Token.
        # Let's assume standard behavior:
        # Case 1: (define var expr) -> items = [var, expr]
        # Case 2: (define (var args) body) -> items = [var(inside formals?), (args), body]
        # Wait, the grammar rule is:
        # definition: "(" "define" variable expression ")"
        #           | "(" "define" "(" variable def_formals ")" body ")"
        
        # We need to look at what 'items' contains.
        
        # A robust way is to check the type of items[0].
        # If it's a Symbol (variable), it's Case 1.
        # But wait, Case 2 structure: "(" "define" "(" variable def_formals ")" body ")"
        # This part `"(" variable def_formals ")"` is not a dedicated rule in our grammar above, it's inline.
        # So we might get the variable and def_formals separate?
        # Actually, let's look at `lisp.lark`.
        # definition: "(" "define" variable expression ")"
        #           | "(" "define" "(" variable def_formals ")" body ")"
        
        # Case 1 items: [variable, expression]
        # Case 2 items: [variable, def_formals, body]  <-- The parens around var+formals match nothing specific that returns a value except matching tokens.
        
        if len(items) == 2:
            return Define(items[0], items[1])
        elif len(items) == 3:
            # (define func (args) body) -> Define(func, Lambda(args, body))
            target_func = items[0]
            formals = items[1] # This comes from def_formals rule
            body = items[2]
            
            # Formals rule returns a list of symbols
            return Define(target_func, Lambda(formals, body))
        return items

    def def_formals(self, items):
        # variable* or variable* . variable
        # We return a list of symbols. Dotted lists not supported in simple Lambda node yet.
        return items

    def body(self, items):
        # definition* sequence
        # Flatten
        return items 

    def sequence(self, items):
        # command* expression
        # Flatten
        return items

    def expression(self, items):
        # Pass-through rule
        if len(items) == 1:
            return items[0]
        return items

    def variable(self, items):
        return items[0]

    def identifier(self, items):
        return Symbol(str(items[0]))
    
    def symbol(self, items):
        return items[0]

    # --- Literals ---
    def number(self, items):
        return Number(float(items[0]) if '.' in items[0] else int(items[0]))

    def string(self, items):
        # Remove quotes
        return String(items[0][1:-1])

    def boolean(self, items):
        return Bool(items[0] == "#t")

    def procedure_call(self, items):
        # (operator operand*)
        # items[0] is operator, items[1:] are operands
        op = items[0]
        
        # Handle define if it parsed as a procedure call (due to ambiguity)
        if isinstance(op, Symbol) and op.name == "define":
            # Case 1: (define var expr)
            # Case 2: (define (f args) body)
            
            if len(items) >= 2:
                first_arg = items[1]
                
                # Case 2: (define (f x) body)
                if isinstance(first_arg, LispList):
                    # (f x) is the first arg list
                    # target is f, params are x
                    if len(first_arg.elements) > 0:
                        target_func = first_arg.elements[0]
                        params = first_arg.elements[1:]
                        body = items[2:] # Rest are body
                        
                        # Create Lambda for the body
                        # Note: body in typical define can be multiple exprs (implicit begin)
                        return Define(target_func, Lambda(params, body))
                
                # Case 1: (define var expr)
                else:
                    target = first_arg
                    value = items[2] if len(items) > 2 else None
                    return Define(target, value)

        # Handle if
        if isinstance(op, Symbol) and op.name == "if":
             # (if test consequent alternate?)
             if len(items) >= 3:
                 test = items[1]
                 consequent = items[2]
                 alternate = items[3] if len(items) > 3 else None
                 return If(test, consequent, alternate)

        return LispList(items)

    def lambda_expression(self, items):
        # (lambda formals body)
        return Lambda(items[0], items[1])
    
    def formals(self, items):
        # "(" variable* ")" ...
        # items is list of vars
        return items

    # --- Literals & Wrappers ---
    def literal(self, items):
        return items[0]

    def self_evaluating(self, items):
        return items[0]
        
    def datum(self, items):
        return items[0]

    def simple_datum(self, items):
        return items[0]

    def compound_datum(self, items):
        return items[0]
        
    # --- Lists ---
    def list(self, items):
        return LispList(items)
        
    def quote(self, items):
        return Quote(items[0])

    def quotation(self, items):
        return Quote(items[0])

    # Handling 'if' explicitly if desired, but in `expression` it falls through to generic rules often?
    # In `lisp.lark` conditional is a rule.
    def conditional(self, items):
        # (if test consequent alternate?)
        if len(items) == 2:
             return If(items[0], items[1])
        return If(items[0], items[1], items[2])

