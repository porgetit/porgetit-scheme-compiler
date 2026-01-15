from lark import Lark
import sys

def main():
    with open('lisp.lark', 'r') as f:
        grammar = f.read()

    parser = Lark(grammar, start='start', parser='lalr')

    # Example code or from CLI args
    code = "(defun fib (n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))"
    
    if len(sys.argv) > 1:
        # Check if file exists, otherwise treat as code
        if sys.argv[1].endswith('.lisp') or sys.argv[1].endswith('.scm'):
             with open(sys.argv[1], 'r') as f:
                 code = f.read()
        else:
            code = sys.argv[1]

    print(f"Parsing Code:\n{code}\n")
    try:
        tree = parser.parse(code)
        print("Parse Tree:")
        print(tree.pretty())
    except Exception as e:
        print(f"Error parsing: {e}")

if __name__ == "__main__":
    main()
