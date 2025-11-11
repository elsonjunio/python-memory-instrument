from ou.fn import other_func

def my_func():
    a = [1] * (10**6)
    b = [2] * (2 * 10**7)
    del b
    return a


if __name__ == '__main__':
    my_func()
    i = 0
    while True:
        i = i + 1
        other_func()
        if i > 5:
            break