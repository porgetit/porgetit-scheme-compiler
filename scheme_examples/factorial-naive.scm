(define (factorial-naive n)
    (if (= n 0)
        1
        (* n (factorial-naive (- n 1)))
    )
)

(factorial-naive 5)