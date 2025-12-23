import inspect
import re
from dataclasses import dataclass
from typing import Optional


_FOR_TOKEN = "for"
_SELF_TOKEN = "self"
_ALL_TOKEN = "all"
_SELF_INDEX_RE = re.compile(r"^self\.\[(?P<index>\d+)\]$")
_MAIN_INDEX_RE = re.compile(r"^(?P<main>.+)\.\[(?P<index>\d+)\]$")


@dataclass(frozen=True)
class ParamInfo:
    name: str
    converter: callable
    has_default: bool
    default: object


@dataclass(frozen=True)
class CommandInfo:
    name: str
    name_tokens: list
    func: callable
    owner: str
    owner_name: Optional[str]
    explicit: bool
    params: list


@dataclass(frozen=True)
class TargetToken:
    kind: str
    raw: str
    main_id: Optional[str] = None
    index: Optional[int] = None


_COMMANDS = {}
_RELATION = None


def register_relation(
    main_class=None,
    sub_class=None,
    subattr=None,
    main_id_attr="id",
    sub_id_attr="id",
    all=None,
):
    global _RELATION
    if subattr is None:
        if sub_class is not None:
            raise ValueError("register_relation() requires subattr when sub_class is provided")
    elif not subattr:
        raise ValueError("register_relation() requires subattr")
    _RELATION = {
        "main_class": main_class,
        "sub_class": sub_class,
        "subattr": subattr,
        "main_id_attr": main_id_attr,
        "sub_id_attr": sub_id_attr,
        "all": all,
    }


def _get_owner_info(func):
    qual = func.__qualname__
    if "." in qual:
        return "method", qual.split(".")[0]
    return "engine", None


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

        param_infos = []
        for param in params:
            param_infos.append(
                ParamInfo(
                    name=param.name,
                    converter=_get_converter(param.annotation),
                    has_default=param.default is not inspect._empty,
                    default=param.default,
                )
            )

        name = func.__name__
        name_tokens = name.split("_")
        info = CommandInfo(
            name=name,
            name_tokens=name_tokens,
            func=func,
            owner=owner,
            owner_name=owner_name,
            explicit=explicit,
            params=param_infos,
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


def _as_list(items):
    if items is None:
        return None
    if isinstance(items, list):
        return items
    if isinstance(items, tuple):
        return list(items)
    return list(items)


def _resolve_relation(self_obj, all_override):
    if _RELATION is None:
        return None, "relation not registered (call register_relation())"
    relation = dict(_RELATION)
    if all_override is not None:
        relation["all"] = all_override
    all_list = _as_list(relation.get("all"))
    relation["all_list"] = all_list
    subattr = relation["subattr"]

    main_class = relation.get("main_class")
    sub_class = relation.get("sub_class")

    if main_class is None:
        if all_list:
            main_class = all_list[0].__class__
        elif self_obj is not None:
            if subattr is None or hasattr(self_obj, subattr):
                main_class = self_obj.__class__

    if subattr is None:
        relation["main_class"] = main_class
        relation["sub_class"] = sub_class
        return relation, None

    if sub_class is None:
        if all_list:
            subs = _as_list(getattr(all_list[0], subattr, None))
            if subs:
                sub_class = subs[0].__class__
        if sub_class is None and self_obj is not None:
            if main_class is not None and isinstance(self_obj, main_class):
                subs = _as_list(getattr(self_obj, subattr, None))
                if subs:
                    sub_class = subs[0].__class__
            elif main_class is None:
                sub_class = self_obj.__class__

    relation["main_class"] = main_class
    relation["sub_class"] = sub_class
    return relation, None


def _resolve_owner(info, relation):
    if info.owner == "engine":
        return "engine"
    if relation is None:
        return None
    cls = info.func.__globals__.get(info.owner_name)
    if not isinstance(cls, type):
        return None
    main_class = relation.get("main_class")
    sub_class = relation.get("sub_class")
    if main_class is not None and issubclass(cls, main_class):
        return "main"
    if sub_class is not None and issubclass(cls, sub_class):
        return "sub"
    return None


def _classify_self(self_obj, relation):
    if self_obj is None or relation is None:
        return None
    main_class = relation.get("main_class")
    sub_class = relation.get("sub_class")
    subattr = relation.get("subattr")
    if subattr is None:
        if main_class is None or isinstance(self_obj, main_class):
            return "main"
        return None
    if main_class is not None and isinstance(self_obj, main_class):
        return "main"
    if sub_class is not None and isinstance(self_obj, sub_class):
        return "sub"
    if main_class is None and subattr and hasattr(self_obj, subattr):
        return "main"
    if sub_class is None and subattr and not hasattr(self_obj, subattr):
        return "sub"
    return None


def _split_for(tokens, info):
    if _FOR_TOKEN in tokens:
        index = tokens.index(_FOR_TOKEN)
        return tokens[:index], tokens[index + 1:], True
    if not info.params and tokens:
        return [], tokens, False
    return tokens, [], False


def _parse_arguments(info, tokens):
    if not info.params:
        if tokens:
            return None, f"unexpected arguments {tokens!r}"
        return [], None

    param_map = {param.name: param for param in info.params}
    positional = []
    kwargs = {}
    seen_kw = False

    for token in tokens:
        if "=" in token:
            name, value = token.split("=", 1)
            if not name:
                return None, f"invalid keyword token {token!r}"
            if name not in param_map:
                return None, f"unknown parameter {name!r}"
            if name in kwargs:
                return None, f"duplicate parameter {name!r}"
            kwargs[name] = value
            seen_kw = True
        else:
            if seen_kw:
                return None, "positional arguments after keyword arguments"
            positional.append(token)

    if len(positional) > len(info.params):
        return None, "too many positional arguments"

    values = {}
    for index, raw in enumerate(positional):
        param = info.params[index]
        try:
            values[param.name] = param.converter(raw)
        except Exception:
            return None, f"invalid argument value {raw!r} for {param.name!r}"

    for name, raw in kwargs.items():
        if name in values:
            return None, f"duplicate parameter {name!r}"
        param = param_map[name]
        try:
            values[name] = param.converter(raw)
        except Exception:
            return None, f"invalid argument value {raw!r} for {name!r}"

    args = []
    for param in info.params:
        if param.name in values:
            args.append(values[param.name])
        elif param.has_default:
            args.append(param.default)
        else:
            return None, f"missing required parameter {param.name!r}"

    return args, None


def _parse_target_token(token):
    if token == _SELF_TOKEN:
        return TargetToken("self", token)
    if token == _ALL_TOKEN:
        return TargetToken("all", token)
    match = _SELF_INDEX_RE.match(token)
    if match:
        return TargetToken("self_sub", token, index=int(match.group("index")))
    match = _MAIN_INDEX_RE.match(token)
    if match:
        return TargetToken("main_sub", token, main_id=match.group("main"), index=int(match.group("index")))
    if "[" in token or "]" in token:
        return TargetToken("invalid", token)
    return TargetToken("id", token, main_id=token)


def _get_sub_items(main_obj, subattr):
    if subattr is None:
        return None
    items = getattr(main_obj, subattr, None)
    return _as_list(items)


def _find_main_by_id(all_list, main_id_attr, main_id):
    if not all_list:
        return None
    for item in all_list:
        if getattr(item, main_id_attr, None) == main_id:
            return item
    return None


def _find_sub_by_id(all_list, subattr, sub_id_attr, sub_id):
    if not all_list or subattr is None or not sub_id_attr:
        return None, None
    matches = []
    for main in all_list:
        subs = _get_sub_items(main, subattr) or []
        for sub in subs:
            if getattr(sub, sub_id_attr, None) == sub_id:
                matches.append(sub)
    if not matches:
        return None, None
    if len(matches) > 1:
        return None, f"ambiguous sub id {sub_id!r}"
    return matches[0], None


def _resolve_targets(owner, relation, target_tokens, self_obj):
    if owner == "engine":
        if target_tokens:
            return None, "engine commands do not accept targets"
        return [], None
    if relation is None:
        return None, "relation not registered (call register_relation())"

    all_list = relation.get("all_list")
    subattr = relation.get("subattr")
    main_id_attr = relation.get("main_id_attr")
    sub_id_attr = relation.get("sub_id_attr")
    self_kind = _classify_self(self_obj, relation)
    if owner == "sub" and subattr is None:
        return None, "sub targets are not supported"

    if not target_tokens:
        if self_obj is not None:
            target_tokens = [_SELF_TOKEN]
        elif all_list is not None:
            target_tokens = [_ALL_TOKEN]
        else:
            return None, "missing target (self/all)"

    main_targets = []
    sub_targets = []

    for raw in target_tokens:
        token = _parse_target_token(raw)
        if token.kind == "invalid":
            return None, f"invalid target token {token.raw!r}"
        if token.kind == "self":
            if self_obj is None:
                return None, "self target requires self"
            if owner == "main":
                if self_kind != "main":
                    return None, "self is not a main object"
                main_targets.append(self_obj)
            else:
                if self_kind == "sub":
                    sub_targets.append(self_obj)
                elif self_kind == "main":
                    sub_targets.extend(_get_sub_items(self_obj, subattr) or [])
                else:
                    return None, "self is not a sub object"
        elif token.kind == "all":
            if owner == "main":
                if all_list is None:
                    return None, "all target requires all"
                main_targets.extend(all_list)
            else:
                if self_kind == "main":
                    sub_targets.extend(_get_sub_items(self_obj, subattr) or [])
                else:
                    if all_list is None:
                        return None, "all target requires all"
                    for main in all_list:
                        sub_targets.extend(_get_sub_items(main, subattr) or [])
        elif token.kind == "self_sub":
            if subattr is None:
                return None, "sub targets are not supported"
            if owner == "main":
                return None, "target refers to sub but command is main"
            if self_kind != "main":
                return None, "self.[n] requires self to be main"
            subs = _get_sub_items(self_obj, subattr) or []
            if token.index >= len(subs) or token.index < 0:
                return None, f"sub index out of range {token.raw!r}"
            sub_targets.append(subs[token.index])
        elif token.kind == "main_sub":
            if subattr is None:
                return None, "sub targets are not supported"
            if owner == "main":
                return None, "target refers to sub but command is main"
            main = _find_main_by_id(all_list, main_id_attr, token.main_id)
            if main is None:
                return None, f"unknown main id {token.main_id!r}"
            subs = _get_sub_items(main, subattr) or []
            if token.index >= len(subs) or token.index < 0:
                return None, f"sub index out of range {token.raw!r}"
            sub_targets.append(subs[token.index])
        elif token.kind == "id":
            if owner == "main":
                main = _find_main_by_id(all_list, main_id_attr, token.main_id)
                if main is None:
                    return None, f"unknown main id {token.main_id!r}"
                main_targets.append(main)
            else:
                main = _find_main_by_id(all_list, main_id_attr, token.main_id)
                if main is not None:
                    sub_targets.extend(_get_sub_items(main, subattr) or [])
                    continue
                sub, error = _find_sub_by_id(all_list, subattr, sub_id_attr, token.main_id)
                if error:
                    return None, error
                if sub is None:
                    return None, f"unknown target id {token.main_id!r}"
                sub_targets.append(sub)

    if owner == "main":
        return main_targets, None
    return sub_targets, None


def _enforce_explicit(info, owner, targets):
    if not info.explicit:
        return None
    if owner == "engine":
        return None
    if len(targets) != 1:
        return f"explicit command requires exactly one target"
    return None


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


def _target_tokens_hint_sub(target_tokens):
    for token in target_tokens:
        if token == _SELF_TOKEN:
            continue
        if _SELF_INDEX_RE.match(token) or _MAIN_INDEX_RE.match(token):
            return True
    return False


def _build_call(info, tokens, self_obj, all_override):
    if info.owner == "engine":
        owner = "engine"
        arg_tokens, target_tokens, had_for = _split_for(tokens, info)
        if had_for and not target_tokens:
            return None, "missing targets after for"
        args, error = _parse_arguments(info, arg_tokens)
        if error:
            return None, error
        if target_tokens:
            return None, "engine commands do not accept targets"
        return (info, owner, args, [], None, target_tokens), None

    relation, relation_error = _resolve_relation(self_obj, all_override)
    owner = _resolve_owner(info, relation) if relation_error is None else None
    if owner is None:
        if relation_error is not None:
            return None, relation_error
        return None, "unknown command owner"

    arg_tokens, target_tokens, had_for = _split_for(tokens, info)
    if had_for and not target_tokens:
        return None, "missing targets after for"
    args, error = _parse_arguments(info, arg_tokens)
    if error:
        return None, error

    targets, error = _resolve_targets(owner, relation, target_tokens, self_obj)
    if error:
        return None, error

    error = _enforce_explicit(info, owner, targets)
    if error:
        return None, error

    self_kind = _classify_self(self_obj, relation)
    return (info, owner, args, targets, self_kind, target_tokens), None


def _select_call(calls):
    if not calls:
        return None
    if len(calls) == 1:
        return calls[0]

    for info, owner, args, targets, self_kind, target_tokens in calls:
        if owner == "engine":
            return info, owner, args, targets, self_kind, target_tokens

    for info, owner, args, targets, self_kind, target_tokens in calls:
        if owner == "sub" and _target_tokens_hint_sub(target_tokens):
            return info, owner, args, targets, self_kind, target_tokens

    for info, owner, args, targets, self_kind, target_tokens in calls:
        if owner == "sub" and self_kind == "sub":
            return info, owner, args, targets, self_kind, target_tokens

    for info, owner, args, targets, self_kind, target_tokens in calls:
        if owner == "main":
            return info, owner, args, targets, self_kind, target_tokens

    return calls[0]


def execute(*command, self=None, all=None):
    if not command:
        raise RuntimeError("scripting.execute() empty command")

    tokens = _tokenize(command[0]) if len(command) == 1 else _tokenize(command)
    if not tokens:
        raise RuntimeError("scripting.execute() empty command")

    infos, consumed, match_error = _match_command(tokens)
    if not infos:
        raise RuntimeError(f"scripting.execute() {match_error} in {' '.join(tokens)!r}")

    remaining = tokens[consumed:]
    calls = []
    errors = []
    for info in infos:
        call, error = _build_call(info, remaining, self, all)
        if call:
            calls.append(call)
        if error:
            errors.append(error)

    selected = _select_call(calls)
    if not selected:
        raise RuntimeError(_format_error(tokens, errors))

    info, owner, args, targets, self_kind, target_tokens = selected

    if owner == "engine":
        info.func(*args)
        return
    if owner == "main":
        for obj in targets:
            info.func(obj, *args)
        return
    if owner == "sub":
        for obj in targets:
            info.func(obj, *args)
        return
