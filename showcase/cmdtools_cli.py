from cmdtools import CmdtoolsError, command, cli_entry, execute, register_relation


@command
def greet(name: str = "world"):
    print(f"greet {name!r}")


@command
def add(a: int, b: int = 0):
    print(f"add {a} {b} sum={a + b}")


@command
def echo(text: str = "ok"):
    print(f"echo {text!r}")


@command
def version():
    print("version")


class Strategy:
    def __init__(self, robot, index, sid):
        self.robot = robot
        self.index = index
        self.sid = sid

    @command
    def shift(self, value: float = 0.0):
        print(f"shift {self.robot.id}.[{self.index}] {value}")

    @command
    def ping(self):
        print(f"ping {self.robot.id}.[{self.index}]")


class Robot:
    def __init__(self, robot_id, n, duplicate_sid=False):
        self.id = robot_id
        self.strategies = []
        for i in range(n):
            if duplicate_sid:
                sid = "dup"
            else:
                sid = f"{robot_id}.S{i}"
            self.strategies.append(Strategy(self, i, sid=sid))

    @command
    def overview(self):
        print(f"overview {self.id}")

    @command(explicit=True)
    def reboot(self):
        print(f"reboot {self.id}")


ROBOTS = [
    Robot("robot1", 2, duplicate_sid=True),
    Robot("robot2", 1, duplicate_sid=True),
]

MAIN_CLASS = Robot
SUB_CLASS = Strategy
SUBATTR = "strategies"
MAIN_ID_ATTR = "id"
SUB_ID_ATTR = "sid"


def _reset_relation(all_list=ROBOTS, subattr=SUBATTR, sub_class=SUB_CLASS):
    register_relation(
        main_class=MAIN_CLASS,
        sub_class=sub_class,
        subattr=subattr,
        main_id_attr=MAIN_ID_ATTR,
        sub_id_attr=SUB_ID_ATTR,
        all=all_list,
    )


_reset_relation()


@command
def dry_check(command: str):
    command = command.replace(",", " ").replace("|", " ")
    execute(command, dry_run=True)
    print("dry_run ok")


@command
def simulate(case: str):
    if case == "empty_command":
        execute("", dry_run=True)
        return
    if case == "missing_target":
        _reset_relation(all_list=None)
        try:
            execute("overview")
        finally:
            _reset_relation()
        return
    if case == "all_requires_all":
        _reset_relation(all_list=None)
        try:
            execute("overview for all")
        finally:
            _reset_relation()
        return
    if case == "self_not_main":
        execute("overview for self", self=ROBOTS[0].strategies[0])
        return
    if case == "self_not_sub":
        execute("shift for self", self=object())
        return
    if case == "sub_targets_not_supported":
        import cmdtools as _cmdtools

        saved = _cmdtools._RELATION
        try:
            _cmdtools._RELATION = dict(saved)
            _cmdtools._RELATION["subattr"] = None
            _cmdtools._RELATION["sub_class"] = Strategy
            execute("shift for robot1.[0]")
        finally:
            _cmdtools._RELATION = saved
        return
    raise CmdtoolsError(f"unknown simulate case {case!r}")


cli_entry(__name__)
