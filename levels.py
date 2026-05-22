import math
import zlib
import lzma
import os
import time
import subprocess
from scipy.special import erfc
import random
import hashlib


# функция compression_metrics вынесена для унифицированного подсчета
# энтропии на каждом уровне l2-l4: p-value, статистика T(x), описанная в главе 2,
# эффективность сжатия и итоговый вывод - признана ли последовательность случайной
# на данном уровне


def compression_metrics(n, compressed_length_bits, alpha):
    final_length = max(0.0, min(float(compressed_length_bits), float(n)))

    t_stat = n - final_length

    if t_stat <= 0:
        p_value = 1.0
    else:
        p_value = 2.0 ** (-t_stat)

    return p_value, t_stat, final_length / n, p_value >= alpha


# уровень l1 реализует частотный анализ, это соответствует
# частотному тесту из статистической батареи NIST
# метрики высчитываются отлично от уровней l2-l4 и вместо статистики T(x)
# рассчитывается z-критерий, также в соответствии с пакетом NIST


def l1(data: str, alpha):
    n = len(data)
    if n < 100: return 1.0, 0, 1.0, True  # недостаточная длина для анализа

    ones = data.count('1')
    zeros = n - ones

    z_stat = abs(ones - zeros) / math.sqrt(n)
    p_value = erfc(z_stat / math.sqrt(2))

    is_random = p_value >= alpha

    return p_value, z_stat, ones / n, is_random


# функция to_byte вынесена для корректного перевода битовой последовательности
# в массив байтов, необходимый для работы архиваторов


def to_byte(data: str):
    n = len(data)
    padded_str = data.ljust((n + 7) // 8 * 8, '0')
    byte_data = [int(padded_str[i:i + 8], 2) for i in range(0, len(padded_str), 8)]
    return bytes(byte_data)


# уровень l2 использует библиотека zlib для выявления простых структур
# и коротких повторов.


def l2(data: str, alpha):
    n = len(data)
    if n < 128: return 1.0, 0, 1.0, True

    b_data = to_byte(data)

    # сжатие пустой строки для вычисления размера заголовка
    overhead = len(zlib.compress(b""))
    # вычитание overhead для корректной оценки сжатия
    compressed_length = (len(zlib.compress(b_data, 9)) - overhead) * 8

    return compression_metrics(n, compressed_length, alpha)


# уровень l3 использует алгоритм lzma, обладающий большим размером словаря,
# что позволяет выявлять повторяющиеся структуры на больших дистанциях


def l3(data: str, alpha):
    n = len(data)
    if n < 512: return 1.0, 0, 1.0, True

    b_data = to_byte(data)

    overhead = len(lzma.compress(b""))
    compressed_length = (len(lzma.compress(b_data)) - overhead) * 8

    return compression_metrics(n, compressed_length, alpha)


# уровень l4 вызывает архиватор zpaq, реализующий
# контекстное моделирование вероятностей битов,
# с помощью ансамбля различных моделей


def l4(data: str, alpha):
    n = len(data)
    b_data = to_byte(data)

    # калибровка через temp_empty необходима для учета динамического
    # заголовка архиватора в режиме максимального сжатия
    ts = int(time.time() * 1000)
    temp_in, temp_empty, temp_zpaq = f"in_{ts}.bin", f"empty_{ts}.bin", f"out_{ts}.zpaq"

    # расчет системного оверхеда конкретной реализации zpaq
    try:
        with open(temp_empty, "wb") as f:
            subprocess.run(["zpaq", "add", temp_zpaq, temp_empty, "-m5"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            overhead = os.path.getsize(temp_zpaq)
            os.remove(temp_zpaq)

        with open(temp_in, "wb") as f:
            f.write(b_data)
            subprocess.run(["zpaq", "add", temp_zpaq, temp_in, "-m5"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        file_size = os.path.getsize(temp_zpaq)
        payload = max(0, (file_size - overhead) * 8)

        return compression_metrics(n, payload, alpha)

    except Exception as e:
        print(f"ZPAQ Error: {e}")
        return 1.0, 0.0, 1.0, True
    finally:
        # очистка временных файлов
        for f in [temp_in, temp_empty, temp_zpaq]:
            if os.path.exists(f): os.remove(f)


# функция test запускает непосредственное тестирование по уровням,
# последовательное прохождение уровней l1-l4 обеспечивает экономию
# ресурсов: анализ прекращается при первом же обнаружении неслучайности


def test(data, alpha=0.01):
    pipeline = [("L1", l1), ("L2", l2), ("L3", l3), ("L4", l4)]

    for name, func in pipeline:
        p, t, h, is_random = func(data, alpha)

        res = "PASSED" if is_random else "FAILED"
        print(f"{name:2}, p-value: {p:.2e}, t-test: {t:7.1f}, h: {h:.3f}, {res}")

        if not is_random:
            return f"Anomaly detected by {name}"

    return "Passed all tests"


# функция true_random генерирует эталонную последовательность с максимальной энтропией
# для этого используется вызов системного источника os.urandom
# и хеширование с помощью SHA-512 (процедура отбеливания),
# что позволяет устранить любые статистические смещения,
# проверяя систему на отсутствие ложных срабатываний.


def true_random():
    n = 100000

    raw_source = os.urandom(n // 8 + 64)

    bits = ""
    for i in range(0, len(raw_source), 64):
        chunk = raw_source[i:i + 64]
        digest = hashlib.sha512(chunk).digest()
        bits += "".join(bin(b)[2:].zfill(8) for b in digest)

    return bits[:n]


# функция l3_test_data моделирует системный сбой типа "дублирование буфера".
# структура с дальним зеркалированием (300 000 бит) специально подобрана
# для превышения окна уровня L2, что заставляет систему задействовать более
# высокий уровень


def l3_test_data():
    head = "".join(random.choice('01') for _ in range(8000))
    middle_noise = "".join(random.choice('01') for _ in range(300000))
    return head + middle_noise + head


# функция l4_test_data создает разреженную битовую зависимость, имитирующую
# математическую предсказуемость (линейную сложность),
# дополнительно выполняется частотная балансировка


def l4_test_data():
    n = 40000
    bits = [random.randint(0, 1) for _ in range(n)]

    # каждый 10-й бит с вероятностью 90% равен XOR-у предыдущих 20-ти битов
    for i in range(20, n, 10):
        if random.random() < 0.9:
            bits[i] = bits[i - 10] ^ bits[i - 20]

    ones = sum(bits)
    target = n // 2
    for i in range(n):
        if ones > target and bits[i] == 1:
            bits[i] = 0
            ones -= 1
        elif ones < target and bits[i] == 0:
            bits[i] = 1
            ones += 1
        if ones == target: break

    return "".join(map(str, bits))


def test_data(): # сборка итогового тест-стенда
    suite = {}

    # контрольный образец с высокой энтропией
    suite["1. True Random"] = true_random()

    # текстовая последовательность
    text = "Statistical randomness is a measure of the unpredictability of a sequence." * 100
    suite["2. Text Structure (L1 Target)"] = "".join(bin(ord(c))[2:].zfill(8) for c in text)

    # короткий цикл
    suite["3. Simple Repeat (L2 Target)"] = "11001100" * 4000

    # длинный цикл
    suite["4. Huge Distance Copy (L3 Target)"] = l3_test_data()

    # сложная нелинейная зависимость
    suite["5. Bitwise Context (L4 Target)"] = l4_test_data()
    return suite


demo = test_data()
for name, data in demo.items():
    print(f"\n>>>{name}")
    result = test(data)
    print(f"{result}")


