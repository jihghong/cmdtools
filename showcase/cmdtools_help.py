from cmdtools import command, execute, get_help, register_relation


@command
def version():
    print("version 1.0")


class Strategy:
    def __init__(self, robot, index):
        self.robot = robot
        self.index = index
        self.sid = f"{robot.id}.S{index}"

    @command
    def overview(self):
        print(f"strategy overview {self.robot.id}.[{self.index}]")

    @command
    def shift(self, value: float = 0.0):
        print(f"shift {self.robot.id}.[{self.index}] {value}")


class Robot:
    def __init__(self, id, n):
        self.id = id
        self.strategies = [Strategy(self, i) for i in range(n)]

    @command
    def overview(self):
        print(f"robot overview {self.id}")

    @command(explicit=True)
    def patch_record(self, price: float, size: int):
        print(f"patch record {self.id} {price} {size}")


robots = [Robot("robot1", 2), Robot("robot2", 1)]

print("---------------------------- Help before register_relation():\n")
print(get_help())
print()

register_relation(
    main_class=Robot,
    sub_class=Strategy,
    subattr="strategies",
    main_id_attr="id",
    sub_id_attr="sid",
    all=robots,
)

robot1 = robots[0]
strategy0 = robot1.strategies[0]

print("---------------------------- Help after register_relation():\n")
print(get_help())
print()

print("---------------------------- Help for self=robot1:\n")
print(get_help(self=robot1))
print()

print("---------------------------- Help for self=strategy0:\n")
print(get_help(self=strategy0))
print()

print("---------------------------- Help for command 'patch record':\n")
print(get_help("patch record"))
