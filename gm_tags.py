"""Tags que o Mestre escreve na narração e o motor confere antes de aplicar.

  [HP:Mira=-6]            [ITEM:Mira+Adaga de prata]  [ITEM:Mira-Corda]  [ITEM:Mira>Aldric:Corda]
  [COND:Aldric+envenenado] [FATO:a cortina do quarto 5 queimou]  [FLAG:portcullis_37_raised=true]
  [MODO:turnos]           (lido e retirado do texto; o motor aplica no passo dos modos)
Tags antigas [STATUS_UPDATE]{...} e [INVENTORY_UPDATE]{...} viram as mesmas tags do personagem ativo.

A ficha só muda por aqui. Cada mudança aplicada vira um evento (para a tela de todos);
cada tag recusada vai para `rejected` com o motivo. Nada muta a entrada.
"""
import copy
import json
import re
import unicodedata

TAG_RE = re.compile(r"\[(HP|ITEM|COND|FATO|FLAG|MODO):([^\]]+)\]", re.IGNORECASE)
LEGACY_RE = re.compile(r"\[(STATUS_UPDATE|INVENTORY_UPDATE)\]\s*(\{.*?\})", re.DOTALL)
DEFAULT_SLOTS = 10
DEFAULT_STATUS = {"hp": 20, "max_hp": 20}


def _norm(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(plain.casefold().split())


def _legacy_tags(kind: str, body: str) -> list[dict]:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return [{"kind": "INVALID", "body": body, "raw": body}]
    if kind == "STATUS_UPDATE":
        change = data.get("hp_change")
        return [{"kind": "HP", "body": f"={int(change):+d}", "raw": body}] if change is not None else []
    tags = [{"kind": "ITEM", "body": f"+{item}", "raw": body} for item in data.get("add", [])]
    return tags + [{"kind": "ITEM", "body": f"-{item}", "raw": body} for item in data.get("remove", [])]


def extract(text: str) -> tuple[str, list[dict]]:
    """Separa as tags do texto. Alvo vazio (tags antigas) = personagem ativo."""
    found = [(m.start(), [{"kind": m.group(1).upper(), "body": m.group(2), "raw": m.group(0)}])
             for m in TAG_RE.finditer(text)]
    found += [(m.start(), _legacy_tags(m.group(1), m.group(2))) for m in LEGACY_RE.finditer(text)]
    if not found:
        return text, []
    clean = LEGACY_RE.sub("", TAG_RE.sub("", text))
    clean = re.sub(r"[ \t]{2,}", " ", clean)
    clean = re.sub(r"[ \t]+\n", "\n", clean).strip()
    return clean, [tag for _, tags in sorted(found, key=lambda f: f[0]) for tag in tags]


def ensure_flags(state: dict, initial_flags: dict) -> dict:
    """Semeia flags da campanha que o save ainda não tem (campanha cresce, save antigo acompanha)."""
    flags = copy.deepcopy(state.get("flags") or {})
    for group, values in (initial_flags or {}).items():
        flags[group] = {**values, **flags.get(group, {})}
    return {**state, "flags": flags, "facts": state.get("facts", [])}


def _sheets(state: dict) -> list[dict]:
    """Fichas editáveis: player_character é o membro ativo; os outros vivem no party."""
    sheets = [state["player_character"]] if isinstance(state.get("player_character"), dict) else []
    grp = state.get("party") or {}
    for m in grp.get("members", []):
        if m["id"] != grp.get("active_member_id"):
            sheets.append(m["character"])
    return sheets


def _find(state: dict, name: str) -> dict | None:
    if not name.strip():
        return state.get("player_character")
    key = _norm(name)
    for sheet in _sheets(state):
        if _norm(sheet.get("name", "")) == key:
            return sheet
    grp = state.get("party") or {}
    for m in grp.get("members", []):
        if _norm(m.get("nickname", "")) == key:
            return state["player_character"] if m["id"] == grp.get("active_member_id") else m["character"]
    return None


class _Rejected(Exception):
    pass


def _target(state: dict, name: str) -> dict:
    sheet = _find(state, name)
    if sheet is None:
        raise _Rejected("alvo desconhecido")
    return sheet


def _owned(sheet: dict, item: str) -> str | None:
    return next((i for i in sheet.get("inventory", []) if _norm(i) == _norm(item)), None)


def _check_space(sheet: dict) -> None:
    if len(sheet.get("inventory", [])) >= sheet.get("max_slots", DEFAULT_SLOTS):
        raise _Rejected("sem espaço")


def _hp(state, body, events, **_):
    m = re.fullmatch(r"\s*(.*?)\s*=\s*([+-]?\d+)\s*", body)
    if not m:
        raise _Rejected("formato inválido")
    sheet = _target(state, m.group(1))
    status = sheet.setdefault("status", dict(DEFAULT_STATUS))
    before = status.get("hp", DEFAULT_STATUS["hp"])
    status["hp"] = max(0, min(before + int(m.group(2)), status.get("max_hp", DEFAULT_STATUS["max_hp"])))
    events.append({"type": "hp", "target": sheet.get("name"), "before": before, "after": status["hp"]})


def _item(state, body, events, **_):
    transfer = re.fullmatch(r"\s*(.*?)\s*>\s*(.+?)\s*:\s*(.+?)\s*", body)
    if transfer:
        giver, receiver = _target(state, transfer.group(1)), _target(state, transfer.group(2))
        item = _owned(giver, transfer.group(3))
        if item is None:
            raise _Rejected("não tem o item")
        _check_space(receiver)
        giver["inventory"].remove(item)
        receiver.setdefault("inventory", []).append(item)
        events.append({"type": "item_remove", "target": giver.get("name"), "item": item})
        events.append({"type": "item_add", "target": receiver.get("name"), "item": item})
        return
    m = re.fullmatch(r"\s*(.*?)\s*([+-])\s*(.+?)\s*", body)
    if not m:
        raise _Rejected("formato inválido")
    sheet = _target(state, m.group(1))
    if m.group(2) == "+":
        _check_space(sheet)
        sheet.setdefault("inventory", []).append(m.group(3))
        events.append({"type": "item_add", "target": sheet.get("name"), "item": m.group(3)})
        return
    item = _owned(sheet, m.group(3))
    if item is None:
        raise _Rejected("não tem o item")
    sheet["inventory"].remove(item)
    events.append({"type": "item_remove", "target": sheet.get("name"), "item": item})


def _cond(state, body, events, **_):
    m = re.fullmatch(r"\s*(.*?)\s*([+-])\s*(.+?)\s*", body)
    if not m:
        raise _Rejected("formato inválido")
    sheet = _target(state, m.group(1))
    conds = sheet.setdefault("conditions", [])
    current = next((c for c in conds if _norm(c) == _norm(m.group(3))), None)
    if m.group(2) == "+":
        if current is not None:
            raise _Rejected("condição repetida")
        conds.append(m.group(3))
        events.append({"type": "cond_add", "target": sheet.get("name"), "condition": m.group(3)})
        return
    if current is None:
        raise _Rejected("não tem a condição")
    conds.remove(current)
    events.append({"type": "cond_remove", "target": sheet.get("name"), "condition": current})


def _fact(state, body, events, **_):
    text = " ".join(body.split())
    location = (state.get("world_state") or {}).get("current_location_key", "")
    facts = state.setdefault("facts", [])
    if any(f.get("active") and f.get("location_key") == location and _norm(f["text"]) == _norm(text) for f in facts):
        raise _Rejected("fato repetido")
    facts.append({"text": text, "location_key": location, "active": True})
    events.append({"type": "fact", "text": text})


def _flag(state, body, events, roll_success=False, **_):
    m = re.fullmatch(r"\s*(\w+)\s*=\s*(true|false)\s*", body, re.IGNORECASE)
    if not m:
        raise _Rejected("formato inválido")
    name, value = m.group(1), m.group(2).lower() == "true"
    group = next((g for g in (state.get("flags") or {}).values() if name in g), None)
    if group is None:
        raise _Rejected("flag não existe na campanha")
    if not roll_success:
        raise _Rejected("sem rolagem bem-sucedida")
    if group[name] != value:
        events.append({"type": "flag", "target": name, "before": group[name], "after": value})
        group[name] = value


def _mode(*_, **__):
    raise _Rejected("modo ainda não aplicado pelo motor")  # ponytail: o passo dos modos (5) aplica


def _invalid(*_, **__):
    raise _Rejected("formato inválido")


HANDLERS = {"HP": _hp, "ITEM": _item, "COND": _cond, "FATO": _fact, "FLAG": _flag, "MODO": _mode, "INVALID": _invalid}


def apply(state: dict, tags: list[dict], roll_success: bool = False) -> tuple[dict, list[dict], list[dict]]:
    """Aplica as tags em ordem; uma tag recusada não altera nada."""
    current = copy.deepcopy(state)
    events: list[dict] = []
    rejected: list[dict] = []
    for tag in tags:
        attempt, tag_events = copy.deepcopy(current), []
        try:
            HANDLERS[tag["kind"]](attempt, tag["body"], tag_events, roll_success=roll_success)
        except _Rejected as why:
            rejected.append({"tag": tag["raw"], "reason": str(why)})
            continue
        current, events = attempt, events + tag_events
    return current, events, rejected
