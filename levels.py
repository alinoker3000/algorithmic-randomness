import math
from collections import Counter

import zlib

import lzma
import random


def l1(data: str):
    alpha = 0.05
    n = len(data)  # n < 2 нерепрезентативно, надо отдавать статус?

    # энтропия нулевого порядка - частотный тест
    p1 = data.count('1') / n
    h0 = 0 if p1 in [0, 1] else -(p1 * math.log2(p1) + (1 - p1) * math.log2(1 - p1))

    # энтропия S порядка - тест серий (пары)
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

    return p_value, t_stat, entropy, p_value >= alpha


def l2(data: str):
    alpha = 0.05
    n_bits = len(data)

    # zlib работает с байтами
    byte_data = data.encode('utf-8')

    compress_code_len = len(zlib.compress(byte_data, level=9)) * 8
    empty_code_len = len(zlib.compress(b"", level=9)) * 8

    code_len = max(0, compress_code_len - empty_code_len)

    t_stat = n_bits - code_len
    p_value = 2 ** (-max(0.0, t_stat))
    compression = code_len / n_bits

    return p_value, t_stat, compression, p_value >= alpha


def l3(data: str):
    alpha = 0.05
    n_bits = len(data)  # n < 100 нерепрезентативно

    byte_data = data.encode('utf-8')

    compress_code_len = len(lzma.compress(byte_data, preset=9)) * 8
    empty_code_len = len(lzma.compress(b"", preset=9)) * 8

    code_len = max(0, compress_code_len - empty_code_len)
    entropy = code_len / n_bits

    t_stat = n_bits - code_len
    p_value = 2 ** (-max(0.0, t_stat))

    return p_value, t_stat, entropy, p_value > alpha


test_data1 = "10" * 10  # цикличная строка на 2 символа
test_data2 = "0" * 10 + "1" * 10  # длинные серии

test_data3 = "1101001011100001" * 1000  # закономерность со сдвигом

bits = [random.randint(0, 1) for _ in range(5)]
n = 500
for i in range(5, n):
    last_5_sum = sum(bits[-5:])
    threshold = 0.8 if last_5_sum < 2 else 0.2
    bits.append(1 if random.random() < threshold else 0)
test_data4 = "".join(map(str, bits))  # markov with 5 characters drift


print(l1(test_data1), l2(test_data1), l3(test_data1))
print(l1(test_data2), l2(test_data2), l3(test_data2))
print(l1(test_data3), l2(test_data3), l3(test_data3))
print(l1(test_data4), l2(test_data4), l3(test_data4))
