import time


def timer(func):
    def wrapper(*args, **kwargs):
        now = time.perf_counter()
        result = func(*args, **kwargs)
        delta = time.perf_counter() - now
        print(f"Выполнилась функция {func.__name__}. Время выполнения функции : {delta}")
        return result

    return wrapper
