"""
Minigame do Tarokka — exclusivo da campanha Curse of Strahd.

Interface pública consumida genericamente por game.py via campaign_manager:
  INSPECTION_KEYWORDS  — dict de padrões para o HUD
  on_trigger(ws)       — chamado quando o gatilho cartas_tarokka dispara
  process_turn(ws, action) → dict  — máquina de estados da leitura
  get_inspect_response(ws) → str   — resposta do HUD para "profecias"
  build_gm_context_block(ws) → str — bloco injetado no system prompt do GM
"""

import json
import os
import random

# ─── Padrões de inspeção registrados no HUD ───────────────────────────────────
INSPECTION_KEYWORDS = {
    "prophecies": [
        "profecias", "profecia", "tarokka", "cartas do tarokka",
        "cartas de madam eva", "o que madam eva disse", "madam eva",
        "as profecias", "meu destino", "leitura das cartas",
        "quais são as profecias", "me diga as profecias",
        "repita as profecias", "o que as cartas disseram",
        "destino das cartas", "o que as cartas",
    ],
}

# ─── Dados internos ───────────────────────────────────────────────────────────
_DECK_PATH = os.path.join(os.path.dirname(__file__), "tarokka_deck.json")

_STAGE_MAP = {
    "carta_1": ("tomo_de_strahd",              "Tomo de Strahd",              "carta_2", "segunda"),
    "carta_2": ("simbolo_sagrado_de_ravenkind", "Símbolo Sagrado de Ravenkind","carta_3", "terceira"),
    "carta_3": ("espada_solar",                 "Espada Solar",                "carta_4", "quarta"),
    "carta_4": ("aliado",                       "Aliado",                      "carta_5", "quinta"),
    "carta_5": ("confronto",                    "Local do Confronto Final",    "concluido", None),
}

_ORDINALS = {
    "carta_1": "primeira", "carta_2": "segunda", "carta_3": "terceira",
    "carta_4": "quarta",   "carta_5": "quinta",
}

_PREAMBLES = {
    "tomo_de_strahd":              "Esta carta fala do Tomo de Strahd — o livro de sangue e segredos do Conde.",
    "simbolo_sagrado_de_ravenkind":"Esta carta fala do Símbolo Sagrado de Ravenkind — relíquia de luz perdida nas trevas.",
    "espada_solar":                "Esta carta fala da Espada Solar — a lâmina que pode ferir o Conde no coração.",
    "aliado":                      "Esta carta fala do seu aliado — aquele que o destino coloca ao seu lado nesta batalha.",
    "confronto":                   "Esta carta fala do local do confronto final — onde o destino desta terra será selado.",
}

_FLIP_PATTERNS = [
    "vire", "vira", "virar", "viro",
    "próxima", "proxima", "próximo", "proximo",
    "continue", "continuar", "seguir", "prosseguir",
    "sim", "pode", "ok", "pronto",
    "abra", "abrir", "abre",
    "mostre", "mostrar", "revele", "revelar",
    "segunda", "terceira", "quarta", "quinta",
]

_ITEM_SLOTS = [
    ("tomo_de_strahd",              "Tomo de Strahd"),
    ("simbolo_sagrado_de_ravenkind","Símbolo Sagrado de Ravenkind"),
    ("espada_solar",                "Espada Solar"),
]


# ─── Helpers privados ─────────────────────────────────────────────────────────

def _load_deck() -> dict:
    try:
        with open(_DECK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _is_flip_action(action: str) -> bool:
    lowered = (action or "").lower()
    return any(p in lowered for p in _FLIP_PATTERNS)


# ─── API pública ──────────────────────────────────────────────────────────────

def draw_cards(world_state: dict) -> dict:
    """Embaralha e sorteia 5 cartas. Idempotente — não redesorteia se já feito."""
    if world_state.get("tarokka_reading", {}).get("drawn"):
        return world_state

    deck = _load_deck()
    if not deck:
        return world_state

    deck_comum = list(deck.get("deck_comum", []))
    deck_alto  = list(deck.get("deck_alto",  []))
    random.shuffle(deck_comum)
    random.shuffle(deck_alto)

    drawn_comum = deck_comum[:3]
    drawn_alto  = deck_alto[:2]

    cards = {}
    item_locations = {}

    for i, (slot_key, item_label) in enumerate(_ITEM_SLOTS):
        card = drawn_comum[i]
        cards[slot_key] = {
            "nome":           card["nome"],
            "suite":          card.get("suite", ""),
            "numero":         card.get("numero", 0),
            "profecia":       card["profecia"],
            "alvo_semantico": card["alvo_semantico"],
            "alvo_descricao": card.get("alvo_descricao", ""),
        }
        item_locations[item_label] = card["alvo_semantico"]

    # Posição 4 — Aliado
    aliado_card = drawn_alto[0]
    cards["aliado"] = {
        "nome":           aliado_card["nome"],
        "numero":         aliado_card.get("numero", 0),
        "profecia":       aliado_card["profecia_aliado"],
        "alvo_semantico": aliado_card["alvo_aliado"],
        "alvo_descricao": aliado_card.get("aliado_descricao", ""),
    }

    # Posição 5 — Confronto
    confronto_card = drawn_alto[1]
    cards["confronto"] = {
        "nome":           confronto_card["nome"],
        "numero":         confronto_card.get("numero", 0),
        "profecia":       confronto_card["profecia_confronto"],
        "alvo_semantico": confronto_card["alvo_confronto"],
        "alvo_descricao": confronto_card.get("confronto_descricao", ""),
    }

    world_state["tarokka_reading"] = {
        "drawn":          True,
        "cards":          cards,
        "item_locations": item_locations,
    }
    return world_state


def on_trigger(world_state: dict) -> dict:
    """Chamado pelo motor quando o gatilho cartas_tarokka dispara."""
    world_state = draw_cards(world_state)
    if not world_state.get("campaign_event_state"):
        world_state["campaign_event_state"] = {
            "handler": "tarokka",
            "stage":   "intro",
        }
    return world_state


def process_turn(world_state: dict, player_action: str) -> dict:
    """
    Máquina de estados da leitura do Tarokka.
    Retorna {"narrative": str, "mood": str, "completed": bool}.
    """
    event_state = world_state.get("campaign_event_state", {})
    stage = event_state.get("stage", "intro")
    reading = world_state.get("tarokka_reading", {})
    cards   = reading.get("cards", {})

    # ── Intro: coloca as 5 cartas na mesa ─────────────────────────────────────
    if stage == "intro":
        narrative = (
            "Madam Eva fecha os olhos e move os dedos sobre o baralho como quem ouve sussurros invisíveis. "
            "Cinco cartas surgem uma a uma, colocadas viradas para baixo sobre a mesa de veludo vermelho. "
            "[PAUSE_BEAT] "
            "\"Os fios do destino estão sobre a mesa\", ela murmura. "
            "\"Diga-me para virar a primeira carta quando estiver pronto para ver a escuridão.\""
        )
        world_state["campaign_event_state"] = {"handler": "tarokka", "stage": "carta_1"}
        world_state["narration_mood"] = "dramatic"
        return {"narrative": narrative, "mood": "dramatic", "completed": False}

    # ── Aguarda comando para virar ─────────────────────────────────────────────
    if stage not in _STAGE_MAP:
        world_state.pop("campaign_event_state", None)
        return {"narrative": "", "mood": "normal", "completed": True}

    if not _is_flip_action(player_action):
        wait_text = (
            "Os dedos de Madam Eva repousam sobre a carta, aguardando. "
            "\"As sombras são pacientes\", ela murmura. "
            "\"Diga quando estiver pronto para virar.\""
        )
        return {"narrative": wait_text, "mood": "dramatic", "completed": False}

    # ── Revela a carta ─────────────────────────────────────────────────────────
    slot_key, slot_label, next_stage, next_ordinal = _STAGE_MAP[stage]
    card      = cards.get(slot_key, {})
    card_name = card.get("nome", "Carta Desconhecida")
    prophecy  = card.get("profecia", "O destino se recusa a falar.")
    preamble  = _PREAMBLES.get(slot_key, "")
    ordinal   = _ORDINALS[stage]

    if next_stage == "concluido":
        closing = (
            " [PAUSE_BEAT] "
            "Madam Eva afasta as cartas lentamente e olha para você com olhos que já viram muitas mortes. "
            "\"As cartas falaram. O destino está traçado. "
            "O que você faz com ele... isso, as cartas não podem dizer.\""
        )
        next_prompt = ""
    else:
        next_prompt = (
            f" [PAUSE_BEAT] "
            f"\"Diga quando estiver pronto para virar a {next_ordinal} carta.\""
        )
        closing = ""

    narrative = (
        f"Madam Eva vira a {ordinal} carta. "
        f"É {card_name}. [PAUSE_BEAT] "
        f"{preamble} {prophecy}{next_prompt}{closing}"
    )

    if next_stage == "concluido":
        world_state["campaign_event_state"] = {"handler": "tarokka", "stage": "concluido"}
    else:
        world_state["campaign_event_state"] = {"handler": "tarokka", "stage": next_stage}

    world_state["narration_mood"] = "dramatic"
    return {
        "narrative": narrative,
        "mood":      "dramatic",
        "completed": next_stage == "concluido",
    }


def get_inspect_response(world_state: dict) -> str:
    """Resposta do HUD quando o jogador perguntar sobre as profecias."""
    reading = world_state.get("tarokka_reading", {})
    if not reading.get("drawn"):
        return "As cartas do Tarokka ainda não foram lidas. Madam Eva aguarda no Acampamento Tser Pool."

    cards = reading.get("cards", {})
    label_map = [
        ("tomo_de_strahd",              "Tomo de Strahd"),
        ("simbolo_sagrado_de_ravenkind","Símbolo Sagrado de Ravenkind"),
        ("espada_solar",                "Espada Solar"),
        ("aliado",                      "Aliado"),
        ("confronto",                   "Local do Confronto Final"),
    ]

    parts = ["Madam Eva revelou cinco destinos."]
    for key, label in label_map:
        card = cards.get(key, {})
        if card:
            parts.append(
                f"Para o {label}, a carta foi {card.get('nome', '?')}: "
                f"{card.get('profecia', '?')}"
            )
    return " ".join(parts)


def build_gm_context_block(world_state: dict) -> str:
    """Bloco injetado no system prompt do GM com localizações reais dos itens."""
    reading = world_state.get("tarokka_reading", {})
    if not reading.get("drawn"):
        return ""

    item_locs = reading.get("item_locations", {})
    if not item_locs:
        return ""

    lines = [
        "",
        "--- DESTINOS DO TAROKKA (LOCALIZAÇÕES REAIS DOS ITENS SAGRADOS) ---",
        "Madam Eva sorteouy as cartas. Os itens sagrados estão ocultos nos locais abaixo.",
        "REGRA: O jogador SÓ encontra estes itens no local indicado.",
        "Se procurar em local errado, narre que não encontra nada.",
    ]
    for item, loc in item_locs.items():
        card = next(
            (v for k, v in reading.get("cards", {}).items()
             if v.get("alvo_semantico") == loc and
             k in ("tomo_de_strahd", "simbolo_sagrado_de_ravenkind", "espada_solar")),
            {}
        )
        desc = card.get("alvo_descricao", loc)
        lines.append(f"- {item}: escondido em '{loc}' ({desc})")

    return "\n".join(lines)
