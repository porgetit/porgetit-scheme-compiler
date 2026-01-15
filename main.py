from lark import Lark
import sys
import subprocess
import llvmlite.binding as llvm
from ast_transformer import LispTransformer
from codegen import CodeGen
from lambda_lifter import LambdaLifter

def main():
    # ... (Keep existing grammar loading) ...
    with open('lisp.lark', 'r') as f:
        grammar = f.read()

    parser = Lark(grammar, start='start', parser='earley')

    # Example code or from CLI args
    code = "(define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2))))) (fib 10)"
    
    if len(sys.argv) > 1:
        # Check if file exists
        if sys.argv[1].endswith('.lisp') or sys.argv[1].endswith('.scm'):
             with open(sys.argv[1], 'r') as f:
                 code = f.read()
        else:
            code = sys.argv[1]

    print(f"Parsing Code...")
    try:
        tree = parser.parse(code)
        ast = LispTransformer().transform(tree)
        # print("AST:", ast)
        
        print("Lambda Lifting...")
        lifter = LambdaLifter()
        ast = lifter.lift(ast)
        
        # print("Lifted AST:", ast)
        
        print("Generating LLVM IR...")
        codegen = CodeGen()
        llvm_ir = codegen.generate(ast)
        # print(llvm_ir)
        
        # Save IR for debug
        with open("output.ll", "w") as f:
            f.write(llvm_ir)
            
        print("Compiling to Native Object...")
        # Initialize LLVM targets
        # llvm.initialize() 
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        
        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()
        
        # Compile IR to Module
        mod = llvm.parse_assembly(llvm_ir)
        mod.verify()
        
        # Emit Object Code
        obj_code = target_machine.emit_object(mod)
        
        with open("output.o", "wb") as f:
            f.write(obj_code)
            
        print("Linking with GCC...")
        # Link -> create executable 'output'
        # gcc output.o -o output -lm
        subprocess.run(["gcc", "output.o", "-o", "output", "-lm"], check=True)
        
        print("Compilation Success! Run ./output")
        print("--- Execution Output ---")
        subprocess.run(["./output"], check=False)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
