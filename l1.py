import math
from collections import Counter


def l1(data: str):
    alpha = 0.05
    n = len(data)  # n < 2 нерепрезентативно, надо отдавать статус?

    # энтропия нулевого порядка - частотный тест
    p1 = data.count('1') / n
    h0 = 0 if p1 in [0, 1] else -(p1 * math.log2(p1) + (1 - p1) * math.log2(1 - p1))

    # энтропия первого порядка - тест серий (пары)
    pair_counts = Counter(data[i:i + 2] for i in range(n - 1))

    h1 = 0
    for count in pair_counts.values():
        p_b = count / (n - 1)
        h1 -= p_b * math.log2(p_b)

    # H(X_t | X_{t-1}) = H(X_t, X_{t-1}) - H(X_{t-1})
    h_cond = h1 - h0  # условная энтропия

    entropy = min(h0, h_cond)

    code_len = n * entropy
    t_stat = n - code_len
    p_value = 2 ** (-max(0, t_stat))

    return p_value, t_stat, entropy, p_value <= alpha


print(l1('1010101010'))
print(l1('1111110000'))
print(l1('1101001101'))
