from llvmlite import ir
import llvmlite.binding as llvm
from ast_nodes import *

class CodeGen:
    def __init__(self):
        self.module = ir.Module(name="scheme_module")
        self.module.triple = llvm.get_default_triple()
        self.builder = None
        self.func_symtab = {}
        
        # We use purely doubles for this MVP
        self.double_type = ir.DoubleType()
        self.bool_type = ir.IntType(1)

        # Setup external functions (printf)
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

        # Setup main function (entry point)
        self.main_func = None

    def _codegen(self, node, symtab=None):
        if symtab is None:
            symtab = {}

        if isinstance(node, Number):
            return ir.Constant(self.double_type, float(node.value))

        elif isinstance(node, Symbol):
            # Look up variable
            if node.name in symtab:
                return symtab[node.name]
            else:
                raise Exception(f"Undefined variable: {node.name}")

        elif isinstance(node, If):
             # IF is an expression in Scheme, so it must return a value (Phi node)
             cond = self._codegen(node.test, symtab)
             
             # Convert condition to bool (i1) if strictly needed, 
             # but Scheme treats almost anything as true. For MVP, assume cond is boolean logic result (i1) OR double.
             # If it's double (0.0 vs others), let's compare != 0
             if cond.type == self.double_type:
                 cond = self.builder.fcmp_ordered('!=', cond, ir.Constant(self.double_type, 0.0))

             then_block = self.builder.append_basic_block('then')
             else_block = self.builder.append_basic_block('else')
             merge_block = self.builder.append_basic_block('merge')

             self.builder.cbranch(cond, then_block, else_block)

             # THEN
             self.builder.position_at_end(then_block)
             then_val = self._codegen(node.consequent, symtab)
             self.builder.branch(merge_block)
             # Capture updated block (codegen might have added more blocks inside)
             then_bb = self.builder.block

             # ELSE
             self.builder.position_at_end(else_block)
             if node.alternate:
                 else_val = self._codegen(node.alternate, symtab)
             else:
                 else_val = ir.Constant(self.double_type, 0.0) # Void value
             self.builder.branch(merge_block)
             else_bb = self.builder.block

             # MERGE
             self.builder.position_at_end(merge_block)
             phi = self.builder.phi(self.double_type, 'if_result')
             phi.add_incoming(then_val, then_bb)
             phi.add_incoming(else_val, else_bb)
             return phi

        elif isinstance(node, LispList): 
            # Function Call: (op arg1 arg2 ...)
            if not node.elements:
                return ir.Constant(self.double_type, 0.0)
            
            op = node.elements[0]
            args = [self._codegen(a, symtab) for a in node.elements[1:]]

            if isinstance(op, Symbol):
                # Builtins
                if op.name == '+': 
                    return self.builder.fadd(args[0], args[1]) # Simplify unary/multi arity later
                elif op.name == '-':
                    if len(args) == 1: # Unary negation
                        return self.builder.fsub(ir.Constant(self.double_type, 0.0), args[0])
                    return self.builder.fsub(args[0], args[1])
                elif op.name == '*':
                    return self.builder.fmul(args[0], args[1])
                elif op.name == '/':
                    return self.builder.fdiv(args[0], args[1])
                elif op.name in ['>', '<', '=']:
                    # Compare
                    cmp_op = op.name if op.name != '=' else '==' # '==' not '=' in LLVM
                    # For doubles, use fcmp_ordered
                    if op.name == '=': pred = 'oeq'
                    elif op.name == '>': pred = 'ogt'
                    elif op.name == '<': pred = 'olt'
                    
                    # fcmp returns i1 (bool). We must cast back to double for our untyped world?
                    # Or keep as i1 and let IF handle it. 
                    # For MVP consistency, let's keep boolean logic internal or cast to double 1.0/0.0?
                    # Scheme standard: #t/#f.
                    # Let's return numbers 1.0/0.0 so they can be passed around easily in our double-only world.
                    res_i1 = self.builder.fcmp_ordered(pred, args[0], args[1])
                    return self.builder.uitofp(res_i1, self.double_type)

                # Custom Function Calls
                elif op.name in self.func_symtab:
                    func = self.func_symtab[op.name]
                    return self.builder.call(func, args)
                else:
                    # Recursive call to self (if compilation inside main logic before registration)
                    # or forward ref.
                     # Actually, we should check self.module.globals too?
                    func = self.module.get_global(op.name)
                    if func:
                         return self.builder.call(func, args)
                    raise Exception(f"Unknown function call: {op.name}")
            
            raise Exception("Function position must be a symbol")
            
        return ir.Constant(self.double_type, 0.0)

    def generate(self, ast):
        # Initialize
        # LLVM 15+ handles initialize automatically usually
        # llvm.initialize() # Deprecated
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        
        # Create main entry point
        main_ty = ir.FunctionType(ir.IntType(32), [], var_arg=False)
        self.main_func = ir.Function(self.module, main_ty, name="main")
        block = self.main_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        # Process top-level expressions
        # Separate Definitions from Expressions
        # In this simplistic compiler, we'll scan for Definitions first to declare functions,
        # then codegen their bodies.
        
        if isinstance(ast, Program):
            expressions = ast.expressions
        else:
            expressions = [ast]

        # 1. Register Functions
        for expr in expressions:
            if isinstance(expr, Define) and isinstance(expr.value, Lambda):
                # Function Definition
                func_name = expr.target.name
                params = expr.value.params
                
                # Assume all params are doubles
                param_types = [self.double_type] * len(params)
                func_ty = ir.FunctionType(self.double_type, param_types)
                func = ir.Function(self.module, func_ty, name=func_name)
                
                self.func_symtab[func_name] = func

        # 2. Implement Functions
        # We need to save the main builder
        main_builder = self.builder
        
        for expr in expressions:
            if isinstance(expr, Define) and isinstance(expr.value, Lambda):
                func_name = expr.target.name
                func = self.func_symtab[func_name]
                
                # Create blocks
                bb = func.append_basic_block(name="entry")
                self.builder = ir.IRBuilder(bb)
                
                # Create local symtab for args
                local_symtab = {}
                for i, arg in enumerate(func.args):
                    arg.name = expr.value.params[i].name
                    local_symtab[arg.name] = arg
                
                # Codegen Body (Evaluate all, return last)
                ret_val = None
                for body_expr in expr.value.body:
                     ret_val = self._codegen(body_expr, local_symtab)
                
                self.builder.ret(ret_val)
        
        # 3. Compile Main Body (Top-level expressions)
        self.builder = main_builder
        
        # Setup format string for printf
        # "Result: %f\n"
        fmt = "Result: %f\n\0"
        c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
        global_fmt = ir.GlobalVariable(self.module, c_fmt.type, name="fstr")
        global_fmt.linkage = 'internal'
        global_fmt.global_constant = True
        global_fmt.initializer = c_fmt

        for expr in expressions:
            # Skip calls to define, they are handled (unless define variable)
            if isinstance(expr, Define) and isinstance(expr.value, Lambda):
                continue
            
            # TODO: Handle (define x 10) globals
            
            # Exec statement
            val = self._codegen(expr)
            
            # Print result
            # call printf
            voidptr_fmt = self.builder.bitcast(global_fmt, ir.IntType(8).as_pointer())
            self.builder.call(self.printf, [voidptr_fmt, val])

        # Return 0
        self.builder.ret(ir.Constant(ir.IntType(32), 0))

        return str(self.module)
