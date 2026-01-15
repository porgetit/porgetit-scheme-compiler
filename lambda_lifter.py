from ast_nodes import *

class LambdaLifter:
    def __init__(self):
        self.lifted_funcs = []
        self.counter = 0

    def lift(self, ast):
        # We assume input is a Program with a list of global expressions
        if not isinstance(ast, Program):
            return ast
        
        new_exprs = []
        
        # Analyze top-level expressions
        # Global scope defines don't capture anything usually in MVP, 
        # but their bodies might contain nested defines.
        
        global_env = {} # name -> (new_name, [captured_vars])
        
        for expr in ast.expressions:
            # We only really care about transforming top-level defines that are functions
            if isinstance(expr, Define) and isinstance(expr.value, Lambda):
                func_name = expr.target.name
                # Register global name
                global_env[func_name] = (func_name, [])
                
                # Transform body
                transformed_lambda = self._transform_lambda(expr.value, global_env)
                
                new_exprs.append(Define(expr.target, transformed_lambda))
            else:
                # Other top level exprs (e.g. calls)
                new_exprs.append(self._transform_expr(expr, global_env))
                
        # Prepend lifted functions to expressions
        # Lifted functions are Define nodes
        final_exprs = self.lifted_funcs + new_exprs
        return Program(expressions=final_exprs)

    def _transform_expr(self, node, env):
        if isinstance(node, LispList):
            # Check if it's a call to a function in env
            if not node.elements:
                return node
            
            op = node.elements[0]
            args = [self._transform_expr(a, env) for a in node.elements[1:]]
            
            if isinstance(op, Symbol) and op.name in env:
                # Compiling a call to a function we track
                lifted_name, captured_vars = env[op.name]
                
                # We need to pass consumed variables
                # The captured_vars are variable names (strs) that this function expects as extra args.
                # We simply pass them as Symbol references.
                extra_args = [Symbol(v) for v in captured_vars]
                
                # Update call
                new_elements = [Symbol(lifted_name)] + args + extra_args
                return LispList(new_elements)
            
            return LispList([self._transform_expr(e, env) for e in node.elements])

        elif isinstance(node, If):
            return If(self._transform_expr(node.test, env),
                      self._transform_expr(node.consequent, env),
                      self._transform_expr(node.alternate, env) if node.alternate else None)
        
        # Other atoms pass through
        return node

    def _transform_lambda(self, lam_node, env):
        # 1. Scan body for nested Definitions
        local_defines = []
        body_exprs = []
        
        for expr in lam_node.body:
            if isinstance(expr, Define) and isinstance(expr.value, Lambda):
                local_defines.append(expr)
            else:
                body_exprs.append(expr)
        
        # 2. Lift each nested definition
        current_scope_params = {p.name for p in lam_node.params}
        
        # We need a new env for this lambda's body
        # It inherits from parent env, but local defines shadow or add entries.
        local_env = env.copy()
        
        for def_node in local_defines:
            name = def_node.target.name
            nested_lam = def_node.value
            
            # Identify free variables in this nested lambda
            # Free vars = vars used in body - vars defined in args - vars defined locally
            free_vars = self._get_free_vars(nested_lam)
            
            # Important: The free variables must be captured from CURRENT scope.
            # However, if 'iter' uses 'n', 'n' is a param of 'factorial'.
            # 'n' is free in 'iter', but bound in 'factorial'.
            # We must pass 'n' to 'iter'.
            
            # Sort for deterministic order
            captured = sorted(list(free_vars))
            
            # Generate new global name
            self.counter += 1
            lifted_name = f"{name}_lifted_{self.counter}"
            
            # Update env for body processing: calls to 'name' -> call 'lifted_name' with 'captured'
            local_env[name] = (lifted_name, captured)
            
            # Recurse: The nested lambda might itself have nested lambdas.
            # But wait, we need to transform the nested lambda BEFORE lifting it?
            # Or while lifting.
            # The nested lambda's body needs to know about `local_env` + its own params.
            # Actually, the nested lambda becomes a top-level function.
            # It needs to handle calls to ITSELF (recursion).
            
            # When we lift `iter`, we transform its body.
            # Inside `iter` body, a call to `iter` should map to `lifted_iter` with `captured`.
            
            # So we perform transformation on the nested lambda using an env that includes itself.
            nested_env = local_env.copy() # includes 'iter' mapping
            
            # Transform the nested lambda
            # Note: The nested lambda now needs extra params corresponding to captured vars
            transformed_nested = self._transform_lambda(nested_lam, nested_env)
            
            # Add captured vars to params of the lifted function
            extra_params = [Symbol(v) for v in captured]
            transformed_nested.params.extend(extra_params)
            
            # Create global definition
            lifted_def = Define(Symbol(lifted_name), transformed_nested)
            self.lifted_funcs.append(lifted_def)
            
        # 3. Transform body expressions of current lambda using `local_env`
        new_body = [self._transform_expr(e, local_env) for e in body_exprs]
        
        return Lambda(lam_node.params, new_body)

    def _get_free_vars(self, lam_node):
        """
        Returns set of strings (variable names) that are free in the lambda.
        Free = Used but not defined in params or local definitions.
        """
        used = set()
        defined = set(p.name for p in lam_node.params)
        
        # We need a visitor to collect usage
        def visit(node):
            if isinstance(node, Symbol):
                used.add(node.name)
            elif isinstance(node, LispList):
                for e in node.elements:
                    visit(e)
            elif isinstance(node, If):
                visit(node.test)
                visit(node.consequent)
                if node.alternate: visit(node.alternate)
            elif isinstance(node, Define):
                # If we encounter a nested define (before lifting), 
                # the target is defined in this scope.
                # The value (Lambda) creates a new scope, handled separately?
                # No, we are just scanning usage.
                defined.add(node.target.name)
                # But we don't descend into the Lambda body looking for *this* scope's free usage?
                # Actually, vars used inside a nested lambda are used by *it*, but if they are bound *here*, they are used here too conceptually?
                # Wait. For lifting `iter`, we need to know what `iter` needs from `factorial`.
                # If `iter` uses `n` (param of factorial), `n` is free in `iter`.
                pass # We handle nested Define.value (Lambda) separately below
                
                # Careful: We are implementing get_free_vars for `lam_node`.
                # If `lam_node` has a nested Define `iter`, 
                # `iter`'s body usage counts as usage for `lam_node` only if it's NOT bound by `iter`.
                if isinstance(node.value, Lambda):
                    # Recursive check
                    child_free = self._get_free_vars(node.value)
                    used.update(child_free)
            # What if Define value is simple expr?
            elif isinstance(node, Define):
                 visit(node.value)

        for expr in lam_node.body:
            visit(expr)
            
        # Global symbols (standard library) should not be captured potentially?
        # Typically we capture everything not bound. 
        # But we shouldn't capture '+' or 'if' or 'cons'.
        # We need a heuristic or ignore list.
        ignored = {'+', '-', '*', '/', '>', '<', '=', 'if', 'define', 'lambda'}
        
        # Filter
        free = used - defined - ignored
        
        # Also remove any symbols that are actually global function names?
        # For strictness, yes. But MVP: if it's not local, we try to capture. 
        # If it turns out to be global, capturing it is harmless (pass global ptr), 
        # or weird (shadowing).
        # Let's hope users don't shadow globals for now.
        
        return free
