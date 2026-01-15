(define (factorial-tco n)
    (define (iter producto contador)
        (if (> contador n)
            producto
            (iter (* contador producto) (+ contador 1))))
    (iter 1 1)
)

(factorial-tco 5000)