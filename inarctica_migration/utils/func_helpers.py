import time


def timer(func):
    def wrapper(*args, **kwargs):
        now = time.perf_counter()
        result = func(*args, **kwargs)
        delta = time.perf_counter() - now
        print(f"����������� ������� {func.__name__}. ����� ���������� ������� : {delta}")
        return result

    return wrapper