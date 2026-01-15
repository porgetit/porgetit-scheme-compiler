;;; NIVEL 6: Avanzado (Closures & Lambdas)
;;; Estas pruebas requieren soporte para funciones de primera clase.

(define (aplicar-func f x) 
  (f x))
   
(define (inc z) 
  (+ z 1))

(aplicar-func inc 99)
;; Result: 100.000000
