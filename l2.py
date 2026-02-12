"""
Второй уровень батареи L2 работает через сжатие строки, ловя повторения,
пропущенные уровнем L1.
"""

import zlib


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


test_data1 = "110" * 100  # цикличная строка на 3 символа
test_data2 = "11011100" * 100  # цикличная строка на 8 символов

print(l2(test_data1))
print(l2(test_data2))
