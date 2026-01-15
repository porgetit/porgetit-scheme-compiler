;;; NIVEL 4: Funciones (Stack Frames)
;;; Prueba la definición de funciones, paso de argumentos y retorno.

(define (cuadrado n)
  (* n n))

(cuadrado 12)
;; Result: 144.000000

(define (suma3 a b c)
  (+ a (+ b c)))

(suma3 10 20 30)
;; Result: 60.000000
