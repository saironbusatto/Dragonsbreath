"""Regras do Mestre na Death House — injetadas só enquanto o grupo está numa sala area_*.

Descoberto automaticamente por game._build_campaign_gm_block (todo .py da campanha
com build_gm_context_block). Sem dependências: o loader engole exceções de import.
"""

DEATH_HOUSE_PREFIX = "area_"

LOOT_RULES = (
    "Todo inimigo derrotado tem resolução de saque narrada — mesmo que seja 'trapos podres e nada mais'.",
    "Itens no chão e corpos persistem na sala até um evento narrativo justificar a mudança.",
    "Corpo de inimigo morto continua na sala se o grupo voltar (salvo tempo significativo ou evento que o remova).",
    "Se alguém declarar que vasculha algo, responda sempre com o que encontra — ou que não há nada.",
)

NAVIGATION_RULES = (
    "Ao voltar a uma sala já visitada, lembre o grupo do que aconteceu ali antes.",
    "No máximo 1 turno de deslocamento sem micro-evento (som, rastro, detalhe, presságio). Nunca 2+ turnos de 'andando...'.",
)


def build_gm_context_block(world_state: dict) -> str:
    location = (world_state.get("world_state") or {}).get("current_location_key", "")
    if not isinstance(location, str) or not location.startswith(DEATH_HOUSE_PREFIX):
        return ""
    lines = ["", "--- REGRAS DA DEATH HOUSE ---", "SAQUE:"]
    lines += [f"- {rule}" for rule in LOOT_RULES]
    lines.append("NAVEGAÇÃO:")
    lines += [f"- {rule}" for rule in NAVIGATION_RULES]
    return "\n".join(lines)
