import importlib
import inspect
import re
from dataclasses import dataclass
from typing import Optional


ENGINE_MODULE_NAME = "engine"
_ENGINE_MODULE = None

_STRATEGY_ID_RE = re.compile(r"^(?P<robot>.+)\.\[(?P<index>\d+)\]$")


@dataclass(frozen=True)
class CommandInfo:
    name: str
    name_tokens: list
    func: callable
    owner: str
    owner_name: Optional[str]
    explicit: bool
    param_converters: list
    min_args: int
    max_args: int


@dataclass(frozen=True)
class IdToken:
    raw: str
    kind: str
    robot_id: str
    index: Optional[int] = None


_COMMANDS = {}


def set_engine(module_or_name):
    global ENGINE_MODULE_NAME, _ENGINE_MODULE
    if isinstance(module_or_name, str):
        ENGINE_MODULE_NAME = module_or_name
        _ENGINE_MODULE = None
    else:
        _ENGINE_MODULE = module_or_name
        ENGINE_MODULE_NAME = module_or_name.__name__


def _get_engine_module():
    if _ENGINE_MODULE is not None:
        return _ENGINE_MODULE
    return importlib.import_module(ENGINE_MODULE_NAME)


def _get_owner_info(func):
    qual = func.__qualname__
    if "." in qual:
        return "method", qual.split(".")[0]
    return "engine", None


def _resolve_owner(info):
    if info.owner != "method":
        return info.owner
    class_name = info.owner_name
    if not class_name:
        return None
    cls = info.func.__globals__.get(class_name)
    if not isinstance(cls, type):
        return None
    strategy_cls = info.func.__globals__.get("Strategy")
    robot_cls = info.func.__globals__.get("Robot")
    if isinstance(strategy_cls, type) and issubclass(cls, strategy_cls):
        return "strategy"
    if isinstance(robot_cls, type) and issubclass(cls, robot_cls):
        return "robot"
    return None


def _get_converter(annotation):
    if annotation is inspect._empty or annotation is str:
        return str
    if annotation is int:
        return int
    if annotation is float:
        return float
    if annotation is bool:
        def _to_bool(value):
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            if text in ("1", "true", "yes", "y", "t"):
                return True
            if text in ("0", "false", "no", "n", "f"):
                return False
            raise ValueError(f"invalid bool {value!r}")
        return _to_bool
    return str


def _check_name_conflict(new_info):
    for infos in _COMMANDS.values():
        for info in infos:
            if info.name == new_info.name:
                continue
            a = info.name_tokens
            b = new_info.name_tokens
            if len(a) <= len(b) and b[: len(a)] == a:
                raise TypeError(f"command name {info.name!r} conflicts {new_info.name!r}")
            if len(b) <= len(a) and a[: len(b)] == b:
                raise TypeError(f"command name {info.name!r} conflicts {new_info.name!r}")


def command(func=None, *, explicit=False):
    def decorator(func):
        owner, owner_name = _get_owner_info(func)
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if owner == "method":
            if not params:
                raise TypeError("missing self parameter")
            params = params[1:]

        for param in params:
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                raise TypeError("varargs are not supported")

        if not explicit:
            for param in params:
                if param.default is not inspect._empty:
                    raise TypeError("default parameters require explicit=True")

        converters = []
        min_args = 0
        for param in params:
            if param.default is inspect._empty:
                min_args += 1
            converters.append(_get_converter(param.annotation))

        name = func.__name__
        name_tokens = name.split("_")
        info = CommandInfo(
            name=name,
            name_tokens=name_tokens,
            func=func,
            owner=owner,
            owner_name=owner_name,
            explicit=explicit,
            param_converters=converters,
            min_args=min_args,
            max_args=len(converters),
        )
        _check_name_conflict(info)
        _COMMANDS.setdefault(name, []).append(info)
        return func

    if func is None:
        return decorator
    return decorator(func)


def _tokenize(command):
    if isinstance(command, (list, tuple)):
        tokens = []
        for item in command:
            if not isinstance(item, str):
                item = str(item)
            tokens.extend(item.split())
        return tokens
    if isinstance(command, str):
        return command.split()
    return [str(command)]


def _match_command(tokens):
    candidates = {}
    for name, infos in _COMMANDS.items():
        if tokens[0] == name:
            candidates[name] = max(candidates.get(name, 0), 1)
        name_tokens = infos[0].name_tokens
        if tokens[: len(name_tokens)] == name_tokens:
            candidates[name] = max(candidates.get(name, 0), len(name_tokens))

    if not candidates:
        return None, None, "unknown command"
    if len(candidates) > 1:
        return None, None, "ambiguous command name"

    name, consumed = next(iter(candidates.items()))
    return _COMMANDS[name], consumed, None


def _parse_id_token(token):
    match = _STRATEGY_ID_RE.match(token)
    if match:
        return IdToken(token, "strategy", match.group("robot"), int(match.group("index")))
    if "[" in token or "]" in token:
        return None
    return IdToken(token, "robot", token, None)


def _find_robot(engine_module, robot_id):
    for robot in engine_module.robots:
        if robot.id == robot_id:
            return robot
    return None


def _resolve_targets(owner, engine_module, info, ids):
    robots = engine_module.robots
    if owner == "engine":
        return [], None

    if owner == "robot":
        if not ids:
            return robots, None
        targets = []
        for item in ids:
            robot = _find_robot(engine_module, item.robot_id)
            if robot is None:
                return None, f"unknown robot id {item.robot_id!r}"
            targets.append(robot)
        return targets, None

    if owner == "strategy":
        targets = []
        if not ids:
            for robot in robots:
                targets.extend(robot.strategies)
            return targets, None

        for item in ids:
            robot = _find_robot(engine_module, item.robot_id)
            if robot is None:
                return None, f"unknown robot id {item.robot_id!r}"
            if item.kind == "robot":
                targets.extend(robot.strategies)
            else:
                if item.index >= len(robot.strategies) or item.index < 0:
                    return None, f"strategy index out of range {item.raw!r}"
                targets.append(robot.strategies[item.index])
        return targets, None

    return None, "unknown owner"


def _validate_ids(owner, info, ids):
    if owner == "engine":
        if ids:
            return "engine commands do not accept ids"
        return None

    if owner == "robot":
        if info.explicit:
            if len(ids) != 1:
                return "explicit robot command requires exactly one id"
        return None

    if owner == "strategy":
        if info.explicit:
            if len(ids) != 1 or ids[0].kind != "strategy":
                return "explicit strategy command requires exactly one strategy id"
        return None

    return "unknown owner"


def _try_build_call(engine_module, info, tokens):
    owner = _resolve_owner(info)
    if owner is None:
        return None, ["unknown command owner"]
    errors = []
    valid_calls = []
    if info.min_args == info.max_args:
        arg_counts = [info.max_args]
    else:
        arg_counts = list(range(info.min_args, info.max_args + 1))

    for arg_count in arg_counts:
        if len(tokens) < arg_count:
            errors.append("not enough arguments")
            continue
        ids_tokens = tokens[: len(tokens) - arg_count] if arg_count else tokens
        arg_tokens = tokens[len(tokens) - arg_count :] if arg_count else []

        args = []
        try:
            for index, raw in enumerate(arg_tokens):
                args.append(info.param_converters[index](raw))
        except Exception:
            if arg_tokens:
                errors.append(f"invalid argument value {arg_tokens[index]!r}")
            else:
                errors.append("invalid argument value")
            continue

        ids = []
        invalid_id = False
        for raw in ids_tokens:
            parsed = _parse_id_token(raw)
            if parsed is None:
                errors.append(f"invalid id token {raw!r}")
                invalid_id = True
                break
            ids.append(parsed)
        if invalid_id:
            continue

        error = _validate_ids(owner, info, ids)
        if error:
            errors.append(error)
            continue

        targets, error = _resolve_targets(owner, engine_module, info, ids)
        if error:
            errors.append(error)
            continue

        valid_calls.append((info, owner, ids, args, targets))

    if len(valid_calls) > 1:
        errors.append("ambiguous arguments")

    if len(valid_calls) != 1:
        if not errors:
            errors.append("cannot match arguments")
        return None, errors
    return valid_calls[0], []


def _format_error(tokens, errors):
    if not errors:
        return f"scripting.execute() cannot execute {' '.join(tokens)!r}"
    uniq = []
    seen = set()
    for err in errors:
        if err and err not in seen:
            uniq.append(err)
            seen.add(err)
    if len(uniq) == 1:
        return f"scripting.execute() {uniq[0]} in {' '.join(tokens)!r}"
    return f"scripting.execute() cannot execute ({'; '.join(uniq)}) in {' '.join(tokens)!r}"


def _select_call(calls):
    if not calls:
        return None

    if len(calls) == 1:
        return calls[0]

    # Prefer engine when no ids, then robot for robot ids, strategy for strategy ids.
    for info, owner, ids, args, targets in calls:
        if owner == "engine" and not ids:
            return info, owner, ids, args, targets

    has_strategy_ids = any(any(item.kind == "strategy" for item in ids) for _, _, ids, _, _ in calls)
    if has_strategy_ids:
        for info, owner, ids, args, targets in calls:
            if owner == "strategy":
                return info, owner, ids, args, targets
        for info, owner, ids, args, targets in calls:
            if owner == "robot":
                return info, owner, ids, args, targets

    has_robot_ids = any(any(item.kind == "robot" for item in ids) for _, _, ids, _, _ in calls)
    if has_robot_ids:
        for info, owner, ids, args, targets in calls:
            if owner == "robot":
                return info, owner, ids, args, targets
        for info, owner, ids, args, targets in calls:
            if owner == "strategy":
                return info, owner, ids, args, targets

    for info, owner, ids, args, targets in calls:
        if owner == "robot":
            return info, owner, ids, args, targets
    for info, owner, ids, args, targets in calls:
        if owner == "strategy":
            return info, owner, ids, args, targets

    return calls[0]


def execute(*command):
    if not command:
        raise RuntimeError("scripting.execute() empty command")

    tokens = _tokenize(command[0]) if len(command) == 1 else _tokenize(command)
    if not tokens:
        raise RuntimeError("scripting.execute() empty command")

    infos, consumed, match_error = _match_command(tokens)
    if not infos:
        raise RuntimeError(f"scripting.execute() {match_error} in {' '.join(tokens)!r}")

    remaining = tokens[consumed:]
    engine_module = _get_engine_module()

    calls = []
    errors = []
    for info in infos:
        call, call_errors = _try_build_call(engine_module, info, remaining)
        if call:
            calls.append(call)
        errors.extend(call_errors)

    selected = _select_call(calls)
    if not selected:
        raise RuntimeError(_format_error(tokens, errors))

    info, owner, ids, args, targets = selected

    if owner == "engine":
        getattr(engine_module, info.func.__name__)(*args)
        return

    if owner == "robot":
        for robot in targets:
            getattr(robot, info.func.__name__)(*args)
        return

    if owner == "strategy":
        for strategy in targets:
            getattr(strategy, info.func.__name__)(*args)
        return
