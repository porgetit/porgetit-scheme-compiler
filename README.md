# Compilador Scheme-a-Nativo

Un compilador de Scheme de calidad industrial que genera código máquina nativo vía LLVM IR, escrito en Python. Este compilador implementa un subconjunto de R5RS Scheme y emplea técnicas modernas de construcción de compiladores incluyendo parsing Earley, transformación AST, lambda lifting y generación de código basada en LLVM.

## Arquitectura

```
Código Fuente (R5RS Scheme)
    ↓
[Parser Lark - Algoritmo Earley]
    ↓
Árbol de Parseo
    ↓
[Transformador AST]
    ↓
Árbol de Sintaxis Abstracta
    ↓
[Lambda Lifter] (conversión de clausuras)
    ↓
AST Aplanado
    ↓
[Generador de Código LLVM]
    ↓
Representación Intermedia LLVM
    ↓
[llvmlite → Máquina Destino]
    ↓
Archivo Objeto (.o)
    ↓
[Enlazador GCC]
    ↓
Ejecutable Nativo (x86-64, ARM, etc.)
```

## Componentes Técnicos

### 1. Analizador Léxico y Sintáctico (`lisp.lark`)

- **Gramática**: Gramática EBNF compatible con R5RS
- **Algoritmo de Parseo**: Earley (maneja gramáticas ambiguas inherentes a Lisp)
- **Características**: Soporte completo para expresiones-s, cuasi-citación, literales numéricos, identificadores con caracteres especiales

### 2. Transformación AST (`ast_transformer.py`, `ast_nodes.py`)

- **Estrategia**: Patrón visitante sobre el árbol de parseo de Lark
- **Tipos de Nodos**: `Symbol`, `Number`, `String`, `Bool`, `LispList`, `Define`, `Lambda`, `If`, `Quote`
- **Desambiguación**: Maneja ambigüedades gramaticales detectando formas especiales (`define`, `if`) dentro de estructuras de lista genéricas

### 3. Lambda Lifting (`lambda_lifter.py`)

- **Propósito**: Convertir funciones anidadas (clausuras) en funciones de nivel superior
- **Algoritmo**: Análisis de variables libres + renombrado basado en ámbitos
- **Estado**: ⚠️ En desarrollo - actualmente soporta casos simples pero tiene problemas con ámbitos anidados complejos

### 4. Generación de Código (`codegen.py`)

- **Target**: LLVM IR (representación textual)
- **Sistema de Tipos**: Unitipado (todos los valores son doubles IEEE 754 para el MVP)
- **Primitivas**: Aritmética (`+`, `-`, `*`, `/`), comparaciones (`>`, `<`, `=`)
- **Flujo de Control**: Forma SSA apropiada con nodos phi para condicionales
- **FFI**: `printf` externo de libc para salida

### 5. Driver de Compilación (`main.py`)

- **Orquestación del Pipeline**: Parsear → Transformar → Elevar → Codegen → Ensamblar → Enlazar
- **Dependencias de Toolchain**: `llvmlite` (emisión IR), `gcc` (enlazado)

## Capacidades Actuales

✅ **Características Funcionando**:

- Definiciones de funciones recursivas
- Expresiones condicionales (`if`)
- Operaciones aritméticas y de comparación
- Llamadas a funciones (directas y recursivas)
- Retornos en posición de cola apropiados (LLVM optimiza tail calls con `-O2`)

✅ **Compila Exitosamente**:

```scheme
(define (fib n)
    (if (< n 2)
        n
        (+ (fib (- n 1)) (fib (- n 2)))))

(fib 10)  ; → 55.0
```

⚠️ **En Progreso**:

- Definiciones de funciones anidadas (clausuras)
- Ámbito de variables locales más allá de parámetros de función

## Instalación y Uso

### Prerrequisitos

```bash
# Debian/Ubuntu
sudo apt install build-essential python3 python3-venv

# Fedora
sudo dnf install gcc python3
```

### Configuración

```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Compilar y Ejecutar

```bash
# Compilar ejemplo
python main.py scheme_examples/factorial-naive.scm

# Ejecuta el pipeline de compilación y corre ./output
# Salida: Result: 120.000000 (para factorial de 5)
```

### Ejecución Manual

```bash
# Solo compilar (no ejecutar)
python main.py input.scm  # Produce ./output

# Inspeccionar LLVM IR
cat output.ll

# Ejecutar binario compilado
./output
```

## Diseño del Sistema de Tipos (MVP)

**Enfoque Actual**: Unitipado con doubles IEEE 754

- **Razón**: Simplifica gestión de memoria, evita necesidad de recolector de basura
- **Tradeoff**: Operaciones enteras se promueven a float, sin soporte para strings/símbolos en runtime
- **Futuro**: Plan de implementar tipos de unión etiquetada (boxing) similar al modelo Smi/HeapObject de Lua o V8

## Limitaciones Conocidas

1. **Clausuras**: `define` anidado con variables capturadas causa errores en runtime
2. **Tipos de Datos**: Solo valores numéricos soportados (sin listas, strings, booleanos en runtime)
3. **Biblioteca Estándar**: Primitivas mínimas (sin `cons`, `car`, `cdr`, etc.)
4. **Macros**: Sin expansión de macros (`define-syntax` parseado pero ignorado)
5. **Continuaciones**: Sin soporte para `call/cc`

## Notas de Implementación

### ¿Por qué Parser Earley?

La gramática R5RS Scheme es inherentemente ambigua para parsers LR. Por ejemplo, `(define x 1)` entra en conflicto con `(procedure-call define x 1)` en LALR(1). El parsing Earley resuelve esto explorando múltiples caminos de parseo.

### ¿Por qué LLVM?

- **Portabilidad**: Genera código para x86-64, ARM, RISC-V, WebAssembly sin codegen manual
- **Optimización**: Décadas de pases de LLVM (DCE, inlining, vectorización) aplicados automáticamente
- **Ecosistema**: Integración con depuradores (DWARF), profilers, sanitizers

### ¿Por qué No Transpilar a C?

Aunque la transpilación a C (como Chicken Scheme) es más simple, LLVM IR directo proporciona:

- Control preciso sobre convenciones de llamada
- Mejores oportunidades de optimización (LTO, PGO)
- Sin dependencia de peculiaridades del compilador C entre plataformas

## Dependencias

- **lark** (1.3.1+): Generador de parsers
- **llvmlite** (0.46.0+): Bindings de Python para LLVM
- **gcc/clang**: Enlazador del sistema (estándar en Unix, instalar MinGW en Windows)

## Contribuciones

Este es un proyecto educativo/experimental. Áreas clave para contribución:

1. **Corrección Lambda Lifting**: Depurar captura de variables en ámbitos anidados
2. **Sistema de Tipos**: Implementar uniones etiquetadas para datos heterogéneos
3. **Biblioteca Estándar**: Agregar primitivas de listas (`cons`, `car`, `cdr`)
4. **Recolección de Basura**: Integrar Boehm GC o implementar mark-sweep

## Licencia

Uso educativo/investigación. Ver guías institucionales para integridad académica si se usa para trabajos de curso.

---

**Autor**: Kevin  
**Estado**: Desarrollo Activo (Fase Lambda Lifting)  
**Última Actualización**: 2026-01-15
