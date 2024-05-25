from time import perf_counter

class Timer:
    def __init__(self, name=''):
        self.name = name
        self.time = None
      
    def __enter__(self):
        self.time = perf_counter()
        return self
    def __exit__(self, *exc):
        if exc[0]:
            raise
        else:
            print()
            print('CLOCK', self.name + ' performed in:', perf_counter() - self.time, 's')
            print()
    def __repr__(self):
        return f'\nCLOCK {self.name} RUNNING AT:   {perf_counter()-self.time} s\n'