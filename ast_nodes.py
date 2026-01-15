from dataclasses import dataclass
from typing import List, Any, Optional

@dataclass
class Symbol:
    name: str
    def __repr__(self):
        return f"{self.name}"

@dataclass
class LispList:
    elements: List[Any]
    def __repr__(self):
        return f"({' '.join(map(str, self.elements))})"

@dataclass
class Number:
    value: float | int
    def __repr__(self):
        return str(self.value)

@dataclass
class String:
    value: str
    def __repr__(self):
        return f'"{self.value}"'

@dataclass
class Bool:
    value: bool
    def __repr__(self):
        return "#t" if self.value else "#f"

# Special forms mostly map to Lists in Lisp, but having specific nodes helps interpretation later
# However, to keep it "Lispy" typically everything is a list or atom.
# But for a compiler, specific nodes for 'define', 'if' are very useful.
# We will check if we want a "Pure Lisp AST" (just cons cells) or "Compiler AST" (DefineNode, etc.)
# Given the user wants a compiler, structural nodes are better.

@dataclass
class Program:
    expressions: List[Any]

@dataclass
class Define:
    target: Symbol
    value: Any

@dataclass
class If:
    test: Any
    consequent: Any
    alternate: Optional[Any] = None

@dataclass
class Lambda:
    params: List[Symbol]
    body: List[Any]

@dataclass
class Quote:
    datum: Any
