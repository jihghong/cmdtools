# Cmdtools

Cmdtools is a lightweight command-dispatch utility that maps command strings to Python callables. It supports explicit targets, defaults, keyword arguments, and a general "A has many B" relation so you can apply the same syntax to different domains.

## Features

- Command strings like `shift 3 for robot1.[0]` or `overview all`
- Target tokens: `self`, `all`, `self.[n]`, `id`, `id.[n]`
- Keyword arguments: `shift value=3 for self.[0]`
- Subclass-aware dispatch (commands defined on subclasses still work)
- Optional single-level (no subitems) mode
- Command name tokens: `gain_align` can be invoked as `gain align`
- Built-in help output via `get_help()`

## Quick Start

```python
from cmdtools import command, execute, register_relation

class Strategy:
    def __init__(self, robot, index):
        self.robot = robot
        self.index = index
        self.sid = f"{robot.id}.S{index}"

    @command
    def shift(self, value: float = 0.0):
        print(f"shift {self.robot.id}.[{self.index}] {value}")

class Robot:
    def __init__(self, id, n):
        self.id = id
        self.strategies = [Strategy(self, i) for i in range(n)]

    @command
    def overview(self):
        print(f"overview {self.id}")

robots = [Robot("robot1", 2), Robot("robot2", 1)]

register_relation(
    main_class=Robot,
    sub_class=Strategy,
    subattr="strategies",
    main_id_attr="id",
    sub_id_attr="sid",
    all=robots,
)

execute("overview all")
execute("shift 3 for robot1.[0]")
execute("shift value=2 for self.[1]", self=robots[0])
```

## Installation

```bash
pip install git+https://github.com/jihghong/cmdtools
```

## Command Grammar

- Format: `<command> <args/kwargs...> [for <targets...>]`
- Only the first `for` splits arguments and targets.
- If a command has **no parameters**, you can omit `for`:
  - `overview all` is shorthand for `overview for all`
  - `overview robot1 robot2` is shorthand for `overview for robot1 robot2`

### Targets

- `self`: the object passed via `execute(..., self=...)`
- `all`: all main objects registered via `register_relation(..., all=...)`
- `self.[n]`: the nth subitem of `self`
- `id`: a main id
- `id.[n]`: the nth subitem of a main object by id

If no targets are provided:
- If `self` is given, it behaves as `for self`.
- Else if `all` is configured, it behaves as `for all`.
- Otherwise, an error is raised (except for module-level commands).

## API

### `@command`
Register a function or method as a command.

- Underscore names can be called with spaces: `gain_align` -> `gain align`
- Ambiguous name prefixes raise at definition time.

### `register_relation(...)`
Define the A has many B relation.

```python
register_relation(
    main_class=Robot,
    sub_class=Strategy,
    subattr="strategies",
    main_id_attr="id",
    sub_id_attr="sid",
    all=robots,
)
```

Notes:
- `main_id_attr` and `sub_id_attr` can differ.
- To support **single-level** (no subitems), use `subattr=None`.

### `execute(command, *, self=None, all=None)`
Execute a command string or a list/tuple of tokens.

- `self` defines the `self` target.
- `all` overrides the default list from `register_relation` for this call.
- Errors raise `RuntimeError` with a specific reason.

### `get_help(command=None, *, self=None)`
Return a formatted help string for all commands or a specific command.

- Groups by class (main/sub) and global commands.
- Uses `*` for normal commands and `!` for `explicit=True`.
- If `self` is provided, help reflects that context.
- If no relation is registered, the header is `Commands`.

Example output:

```
Strategy commands (for all | id | id.[n] | self | self.[n])
    * overview
    * shift [value=0.0]

Robot commands (for all | id | self)
    * overview
    ! patch record <price: float> <size: int>

Global commands
    * version
```

## Single-Level Relation Example

```python
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

devices = [Device("alpha"), Device("beta")]

register_relation(
    main_class=Device,
    subattr=None,
    main_id_attr="name",
    all=devices,
)

execute("overview all")
execute("tune 3 for beta")
```

## Tips

- Use `explicit=True` on a command to require exactly one target.
- If a sub id is used across multiple main objects, it must be unique or execution will error due to ambiguity.
- See `showcase/cmdtools_robots.py`, `showcase/cmdtools_library.py`, `showcase/cmdtools_flat.py`, and `showcase/cmdtools_help.py` for runnable demos.
