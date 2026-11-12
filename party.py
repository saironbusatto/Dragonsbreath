"""Grupo da mesa: os personagens vivem em world_state["party"]["members"].

world_state["player_character"] é só a visão do membro ativo, para o código existente
(prompt, rolagem, ressurreição) continuar funcionando: activate() copia a ficha do membro
para lá antes do turno e commit_active() devolve depois.
"party" é chave do motor: nunca vai para o Mestre nem para o Arquivista (without_engine_keys).
Todas as funções devolvem um estado novo; a entrada não é alterada.
"""
import copy

ENGINE_KEYS = ("party", "flags", "facts", "turn", "pending")  # só o motor escreve (gm_tags); o Mestre recebe por bloco próprio
FIRST_MEMBER_ID = "p1"


def without_engine_keys(state: dict) -> dict:
    return {k: v for k, v in state.items() if k not in ENGINE_KEYS}


def party_names(state: dict) -> list[str]:
    """Nomes dos personagens do grupo (para quem só vê o estado sem as chaves do motor)."""
    members = (state.get("party") or {}).get("members", [])
    return [m["character"].get("name", "") for m in members if m.get("character", {}).get("name")]


def _location(state: dict) -> str:
    return (state.get("world_state") or {}).get("current_location_key", "")


def ensure_party(state: dict) -> dict:
    """Converte um save solo (só player_character) em grupo de um membro. Idempotente."""
    if isinstance(state.get("party"), dict):
        return state
    pc = copy.deepcopy(state.get("player_character") or {})
    member = {
        "id": FIRST_MEMBER_ID,
        "nickname": pc.get("name", ""),
        "connected": True,
        "location_key": _location(state),
        "character": pc,
    }
    return {**state, "party": {"active_member_id": FIRST_MEMBER_ID, "members": [member]}}


def activate(state: dict, member_id: str) -> dict:
    """Coloca a ficha do membro em player_character e marca-o como ativo."""
    grp = state["party"]
    member = next(m for m in grp["members"] if m["id"] == member_id)
    return {
        **state,
        "player_character": copy.deepcopy(member["character"]),
        "party": {**grp, "active_member_id": member_id},
    }


def commit_active(state: dict) -> dict:
    """Devolve player_character e o local atual para o membro ativo."""
    grp = state["party"]
    active_id = grp["active_member_id"]
    members = [
        {**m, "character": copy.deepcopy(state.get("player_character") or {}), "location_key": _location(state)}
        if m["id"] == active_id else m
        for m in grp["members"]
    ]
    return {**state, "party": {**grp, "members": members}}
