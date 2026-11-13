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


def _owned(sheet: dict, item: str, scene: dict | None = None) -> str | None:
    """Item da ficha pelo nome; com catálogo, também pelo id ou apelido."""
    names = {_norm(item)}
    known = _scene_item(scene, item) if scene else None
    if known:
        names |= set(known[1]["names"])
    return next((i for i in sheet.get("inventory", []) if _norm(i) in names), None)


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


def _where(state: dict, sheet: dict) -> str:
    """Sala onde está o dono da ficha (o ativo usa a sala atual; os outros, a do membro)."""
    if sheet is state.get("player_character"):
        return (state.get("world_state") or {}).get("current_location_key", "")
    members = (state.get("party") or {}).get("members", [])
    return next((m.get("location_key", "") for m in members if m.get("character") is sheet), "")


def _scene_item(scene: dict, name: str) -> tuple[str, dict] | None:
    key = _norm(name)
    return next(((item_id, item) for item_id, item in scene["items"].items() if key in item["names"]), None)


def _catalog_item(scene: dict, name: str) -> tuple[str, dict]:
    found = _scene_item(scene, name)
    if found is None:
        raise _Rejected("item fora do catálogo")
    return found


def _stock_move(state: dict, source: str, item_id: str, delta: int) -> None:
    """Saldo do que saiu (-) ou foi deixado (+) em cada sala/NPC, sobre o que a campanha define."""
    stock = state.setdefault("stock", {}).setdefault(source, {})
    stock[item_id] = stock.get(item_id, 0) + delta


def _on_hand(state: dict, defined: dict, source: str, item_id: str) -> int:
    return defined.get(item_id, 0) + state.get("stock", {}).get(source, {}).get(item_id, 0)


def _scene_npc(scene: dict, name: str) -> dict:
    npc = next((n for n in scene["npcs"] if _norm(name) in n["names"]), None)
    if npc is None:
        raise _Rejected("alvo desconhecido")
    return npc


def _take_from_npc(state, scene, npc_name, receiver_name, item_name, events) -> None:
    npc, receiver = _scene_npc(scene, npc_name), _target(state, receiver_name)
    item_id, item = _catalog_item(scene, item_name)
    has = _on_hand(state, npc["items"], npc["key"], item_id) > 0
    if not has and not item["livre"]:
        raise _Rejected("npc não tem o item")
    _check_space(receiver)
    receiver.setdefault("inventory", []).append(item["nome"])
    if has:
        _stock_move(state, npc["key"], item_id, -1)
    events.append({"type": "item_add", "target": receiver.get("name"), "item": item["nome"]})


def _give_to_npc(state, scene, giver, npc_name, item_name, events) -> None:
    npc, owned = _scene_npc(scene, npc_name), _owned(giver, item_name, scene)
    if owned is None:
        raise _Rejected("não tem o item")
    giver["inventory"].remove(owned)
    known = _scene_item(scene, owned)
    if known:
        _stock_move(state, npc["key"], known[0], +1)
    events.append({"type": "item_remove", "target": giver.get("name"), "item": owned})


def _item(state, body, events, scene=None, **_):
    """Com `scene` (catálogo estrito) só entra o que está na sala ou com um NPC em cena."""
    transfer = re.fullmatch(r"\s*(.*?)\s*>\s*(.+?)\s*:\s*(.+?)\s*", body)
    if transfer:
        giver_name, receiver_name, item_name = transfer.groups()
        if scene and _find(state, giver_name) is None:
            return _take_from_npc(state, scene, giver_name, receiver_name, item_name, events)
        if scene and _find(state, receiver_name) is None:
            return _give_to_npc(state, scene, _target(state, giver_name), receiver_name, item_name, events)
        giver, receiver = _target(state, giver_name), _target(state, receiver_name)
        item = _owned(giver, item_name, scene)
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
    room = _where(state, sheet)
    if m.group(2) == "+":
        name = m.group(3)
        if scene:
            item_id, item = _catalog_item(scene, name)
            if _on_hand(state, scene["rooms"].get(room, {}), room, item_id) <= 0:
                raise _Rejected("item não está na cena")
            name = item["nome"]
        _check_space(sheet)
        if scene:
            _stock_move(state, room, item_id, -1)
        sheet.setdefault("inventory", []).append(name)
        events.append({"type": "item_add", "target": sheet.get("name"), "item": name})
        return
    item = _owned(sheet, m.group(3), scene)
    if item is None:
        raise _Rejected("não tem o item")
    sheet["inventory"].remove(item)
    known = _scene_item(scene, item) if scene else None
    if known and not known[1]["consumivel"]:
        _stock_move(state, room, known[0], +1)  # largado: fica no chão da sala; consumível é gasto
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


def _add_fact(state: dict, text: str, location: str, entities: list[str] | None = None) -> bool:
    """Grava um fato ativo; False se já existe (mesmo texto normalizado na mesma sala)."""
    text = " ".join(text.split())
    facts = state.setdefault("facts", [])
    if not text or any(f.get("active") and f.get("location_key") == location and _norm(f["text"]) == _norm(text)
                       for f in facts):
        return False
    facts.append({"text": text, "location_key": location, "active": True,
                  "entities": list(entities or []), "turn": state.get("turn", 0)})
    return True


def _fact(state, body, events, **_):
    location = (state.get("world_state") or {}).get("current_location_key", "")
    if not _add_fact(state, body, location):
        raise _Rejected("fato repetido")
    events.append({"type": "fact", "text": " ".join(body.split())})


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


RECENT_FACTS = 5
MAX_FACTS_IN_PROMPT = 15


def _scene_npc_names(ws: dict) -> list[str]:
    names = []
    for key in ("important_npcs_in_scene", "scene_npc_signatures"):
        for npc_id, data in (ws.get(key) or {}).items():
            names.append(npc_id.replace("_", " "))
            if isinstance(data, dict) and data.get("nome"):
                names.append(data["nome"])
    return [_norm(n) for n in names if n]


def _relevant_facts(state: dict) -> list[dict]:
    """Fatos ativos da sala atual, dos NPCs em cena e os mais recentes (o resto volta quando voltar a importar)."""
    ws = state.get("world_state") or {}
    here = ws.get("current_location_key", "")
    npcs = _scene_npc_names(ws)
    active = [f for f in state.get("facts", []) if f.get("active")]
    recent = {id(f) for f in active[-RECENT_FACTS:]}
    chosen = [f for f in active
              if id(f) in recent or f.get("location_key") == here or any(n in _norm(f["text"]) for n in npcs)]
    return chosen[-MAX_FACTS_IN_PROMPT:]


def build_world_memory_block(state: dict) -> str:
    """Bloco do prompt do Mestre com as flags da campanha e os fatos que importam agora."""
    flags = state.get("flags") or {}
    facts = _relevant_facts(state)
    if not any(flags.values()) and not facts:
        return ""
    # ponytail: todas as flags entram; filtrar por região quando a campanha tiver centenas
    lines = ["", "--- MEMÓRIA DO MUNDO (registrada pelo motor; é a verdade) ---"]
    if any(flags.values()):
        lines.append("FLAGS DA CAMPANHA:")
        lines += [f"- {name}: {'sim' if value else 'não'}" for group in flags.values() for name, value in group.items()]
    if facts:
        total = sum(1 for f in state.get("facts", []) if f.get("active"))
        lines.append(f"FATOS LEMBRADOS ({len(facts)} de {total}):")
        lines += [f"- [{f.get('location_key') or '?'}] {f['text']}" for f in facts]
    return "\n".join(lines) + "\n"


PENDING_KINDS = ("hp", "item", "cond")
MAX_REVIEW_ITEMS = 5   # por turno, de cada lista da conferência
MAX_REVIEW_TEXT = 200
MAX_NAME = 60
TRANSIENT_KEYS = ("_sheet_events", "_tags_rejected", "_pending_ignored", "_secret_leaks")


def pop_transient(state: dict) -> dict:
    """Retira do estado o que só vale para este turno (eventos, recusas, pendências ignoradas, vazamentos)."""
    return {key.lstrip("_"): state.pop(key, []) for key in TRANSIENT_KEYS}


def _dicts(value) -> list[dict]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _strs(value) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _cut(value, size: int = MAX_REVIEW_TEXT) -> str:
    return " ".join(str(value).split())[:size]


def _changed(events: list[dict]) -> set[tuple[str, str]]:
    """(tipo, personagem) de cada mudança de ficha aplicada: hp, item ou cond."""
    return {(e["type"].split("_")[0], _norm(str(e.get("target", "")))) for e in events}


def _sheet_name(state: dict, name: str) -> str:
    sheet = _find(state, name)
    return _norm(sheet.get("name", "") if sheet else name)


def apply_review(state: dict, review, location_key: str, applied_events: list[dict] | None = None) -> tuple[dict, list[dict]]:
    """Aplica a conferência do Arquivista (saída de modelo: validada e limitada em tamanho).

    Fatos do mundo entram direto; mudança de ficha sem tag vira pendência para o Mestre
    resolver no próximo turno (a ficha não muda aqui). O que o motor já aplicou neste turno
    (`applied_events`) nunca vira pendência: cobrar de novo aplicaria em dobro.
    Devolve (estado, segredos de NPC vazados).
    """
    new = copy.deepcopy(state)
    review = review if isinstance(review, dict) else {}
    for fact in _dicts(review.get("fatos_novos"))[:MAX_REVIEW_ITEMS]:
        if isinstance(fact.get("texto"), str):
            entities = [_cut(e, MAX_NAME) for e in _strs(fact.get("entidades"))[:MAX_REVIEW_ITEMS]]
            _add_fact(new, _cut(fact["texto"]), location_key, entities)
    undone = {_norm(t) for t in _strs(review.get("fatos_desfeitos"))}
    new["facts"] = [
        {**f, "active": False}
        if f.get("active") and f.get("location_key") == location_key and _norm(f["text"]) in undone else f
        for f in new.get("facts", [])
    ]
    already = _changed(applied_events or [])
    new["pending"] = [
        {"tipo": p["tipo"], "alvo": _cut(p["alvo"], MAX_NAME), "descricao": _cut(p.get("descricao", "")),
         "turn": new.get("turn", 0)}
        for p in _dicts(review.get("ficha_sem_tag"))
        if p.get("tipo") in PENDING_KINDS and isinstance(p.get("alvo"), str)
        and (p["tipo"], _sheet_name(new, p["alvo"])) not in already
    ][:MAX_REVIEW_ITEMS]
    leaks = [{"npc": _cut(s.get("npc", ""), MAX_NAME), "segredo": _cut(s.get("segredo", ""))}
             for s in _dicts(review.get("segredos_revelados"))[:MAX_REVIEW_ITEMS]]
    return new, leaks


def build_pending_block(state: dict) -> str:
    """Cobrança ao Mestre das mudanças de ficha que a narração anterior sugeriu sem tag."""
    pending = state.get("pending") or []
    if not pending:
        return ""
    lines = ["", "--- PENDÊNCIAS DO TURNO ANTERIOR (a narração sugeriu, mas faltou a tag) ---"]
    lines += [f"- {p['alvo']}: {p['descricao']} → escreva a tag [{p['tipo'].upper()}:...] agora ou corrija na narração"
              for p in pending]
    return "\n".join(lines) + "\n"


def settle_pending(state: dict, events: list[dict]) -> tuple[dict, list[dict]]:
    """A cobrança vale um turno: resolvida se houve evento do mesmo tipo no mesmo alvo; o resto é ignorado."""
    done = _changed(events)
    ignored = [p for p in state.get("pending", []) if (p["tipo"], _sheet_name(state, p["alvo"])) not in done]
    return {**state, "pending": []}, ignored


def apply(state: dict, tags: list[dict], roll_success: bool = False,
          scene: dict | None = None) -> tuple[dict, list[dict], list[dict]]:
    """Aplica as tags em ordem; uma tag recusada não altera nada. `scene` vem de item_catalog.scene()."""
    current = copy.deepcopy(state)
    events: list[dict] = []
    rejected: list[dict] = []
    for tag in tags:
        attempt, tag_events = copy.deepcopy(current), []
        try:
            HANDLERS[tag["kind"]](attempt, tag["body"], tag_events, roll_success=roll_success, scene=scene)
        except _Rejected as why:
            rejected.append({"tag": tag["raw"], "reason": str(why)})
            continue
        current, events = attempt, events + tag_events
    return current, events, rejected
