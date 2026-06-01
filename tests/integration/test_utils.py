from contextlib import contextmanager


@contextmanager
def enable_profiling_for_library(library):
    library._arctic_lib._db.command("profile", 2)
    try:
        yield library._arctic_lib._db['system.profile']
    finally:
        library._arctic_lib._db.command("profile", 0, slowms=100)
