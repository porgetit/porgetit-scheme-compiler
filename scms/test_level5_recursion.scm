;;; NIVEL 5: Recursión
;;; Prueba la recursión simple y de árbol (manejo del stack).

(define (factorial n)
  (if (< n 2)
      1
      (* n (factorial (- n 1)))))

(factorial 5)
;; Result: 120.000000

(define (fib n)
  (if (< n 2)
      n
      (+ (fib (- n 1))
         (fib (- n 2)))))

(fib 10)
;; Result: 55.000000
