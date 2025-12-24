from cmdtools import command, execute, register_relation


class Device:
    def __init__(self, name):
        self.name = name

    @command
    def overview(self):
        print(f"overview {self.name}")

    @command
    def tune(self, level: int = 1):
        print(f"tune {self.name} level={level}")

    @command(explicit=True)
    def reboot(self):
        print(f"reboot {self.name}")

@command
def shutdown(t=0):
    print(f"shutdown -t {t}")

devices = [Device("alpha"), Device("beta"), Device("gamma")]

register_relation(
    main_class=Device,
    subattr=None,
    main_id_attr="name",
    all=devices,
)


def execute_raised(command, **kwargs):
    try:
        execute(command, **kwargs)
    except Exception as e:
        print(repr(e))


execute("overview")
execute("overview", all=devices)
execute("overview all")
execute("overview alpha beta")
execute("overview for beta")
execute("overview", self=devices[0])
execute("overview for all", self=devices[0])

execute("tune", self=devices[0])
execute("tune 3", self=devices[0])
execute("tune level=2 for all")
execute("tune for beta")

execute("reboot gamma")
execute("shutdown t=3")
execute_raised("reboot alpha beta")
execute_raised("shutdown for alpha")
