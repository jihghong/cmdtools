from scripting import command

class Strategy:
    def __init__(self, robot, index):
        self.robot, self.index = robot, index

    @command
    def overview(self):
        print(f"overview {self.robot.id}.[{self.index}]")

    @command(explicit=True)
    def shift(self, value: float = 0.0):
        print(f"shift {self.robot.id}.[{self.index}] {type(value).__name__}({repr(value)})")

    try:
        @command
        def expand(self, value: float = 0.0):  # default value=0 will confuse 'expand robot1' with 'expand 4.0'
            print(f"shift {self.robot.id}.[{self.index}] {type(value).__name__}({repr(value)})")
    except TypeError as e:
        print('Strategy.expand()', repr(e))

    @command
    def abc(self, a: int, b: float, c: str):
        print(f"abc {self.robot.id}.[{self.index}] {type(a).__name__}({repr(a)}) {type(b).__name__}({repr(b)}) {type(c).__name__}({repr(c)})")

    try:
        @command
        def gain_align(self):  # conflict with Robot.gain(), and default value=0.0 will confuse 'gain align robot1 robot2 0.0' vs 'gain align robot1 robot2 robot3'
            print(f"gain align {self.robot.id}.[{self.index}]")
    except TypeError as e:
        print('Strategy.gain_align()', repr(e))

class Derived(Strategy):
    @command
    def abc(self, a: int, b: float, c: str):
        print(f"Derived abc {self.robot.id}.[{self.index}] {type(a).__name__}({repr(a)}) {type(b).__name__}({repr(b)}) {type(c).__name__}({repr(c)})")

class Robot:
    def __init__(self, id, n, derived=False):
        self.id = id
        if derived: self.strategies = [Derived(self, id) for id in range(n)]
        else: self.strategies = [Strategy(self, id) for id in range(n)]

    @command
    def overview(self):
        print(f"overview {self.id}")
        for strategy in self.strategies: strategy.overview()

    @command(explicit=True)
    def patch_record(self, price: float, size: int):
        print(f"patch record {self.id} {type(price).__name__}({price}) {type(size).__name__}({size})")

    try:
        @command
        def gain(self):  # conflict with Strategy.gain_align()
            print(f"gain {self.id}")
    except TypeError as e:
        print('Robot.gain()', repr(e))
