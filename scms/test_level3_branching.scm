;;; NIVEL 3: Control de Flujo (Branching)
;;; Prueba la generación de bloques básicos y saltos condicionales.

(if (< 10 20) 100 200)
;; Result: 100.000000

(if (> 10 20) 100 200)
;; Result: 200.000000

;;; If anidado (Prueba de unicidad de etiquetas/labels)
(if (< 5 10)
    (if (> 3 1) 1 0)
    0)
;; Result: 1.000000
