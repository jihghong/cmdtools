from scripting import command, execute, register_relation


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
        print(f"shift {self.robot.id}.[{self.index}] {type(value).__name__}({repr(value)})")

    @command
    def echo(self, text: str = "ok"):
        print(f"echo {self.robot.id}.[{self.index}] {text!r}")


class DerivedStrategy(Strategy):
    @command
    def ping(self):
        print(f"ping {self.robot.id}.[{self.index}]")


class Robot:
    def __init__(self, id, n, derived=False):
        self.id = id
        if derived:
            self.strategies = [DerivedStrategy(self, i) for i in range(n)]
        else:
            self.strategies = [Strategy(self, i) for i in range(n)]

    @command
    def overview(self):
        print(f"robot overview {self.id}")

    @command(explicit=True)
    def patch_record(self, price: float, size: int):
        print(f"patch record {self.id} {type(price).__name__}({price}) {type(size).__name__}({size})")


robots = [
    Robot("robot1", 3),
    Robot("robot2", 1, derived=True),
    Robot("robot3", 2),
]

register_relation(
    main_class=Robot,
    sub_class=Strategy,
    subattr="strategies",
    main_id_attr="id",
    sub_id_attr="sid",
    all=robots,
)


def execute_raised(command, **kwargs):
    try:
        execute(command, **kwargs)
    except Exception as e:
        print(repr(e))


robot1 = robots[0]
robot2 = robots[1]
strategy0 = robot1.strategies[0]

execute("overview")
execute("overview", self=robot1, all=robots)
execute("overview", self=robot1)
execute("overview all")
execute("overview robot1 robot2")
execute("overview for robot2", self=robot1)
execute("overview", self=strategy0)

execute("shift 3", self=robot1)
execute("shift 3", self=robot1, all=robots)
execute("shift value=1.5 for self.[1]", self=robot1)
execute("shift for self.[2]", self=robot1)
execute("shift 2 for all", self=robot1)
execute("shift 2 for all")
execute("shift 2 for robot2", self=robot1)
execute("shift 2 for robot2.[0]")
execute(f"shift for {robot2.strategies[0].sid}")
execute("shift 1.25", self=strategy0, all=robots)
execute("shift 1.25", self=strategy0)

execute("echo text=hello for robot1.[0]")
execute("ping for robot2.[0]")

execute("patch_record 28.5 3", self=robot1)
execute_raised("patch_record 28.5 3 for robot1 robot2")
