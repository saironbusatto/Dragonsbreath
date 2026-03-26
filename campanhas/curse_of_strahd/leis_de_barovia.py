"""
Leis de Baróvia — Fase 9
Mecânicas sistêmicas do Capítulo 2 de Curse of Strahd.

Interface pública consumida pelo motor via campaign_manager:
  INSPECTION_KEYWORDS      — padrões HUD
  build_gm_context_block   — regras injetadas no system prompt do GM a cada turno
  post_narrative_hook      — parse de tags na resposta do GM, atualiza world_state
  on_travel                — chamado quando jogador muda de local; rola encontros
  get_inspect_response     — resposta HUD para queries do jogador
"""

import random
import re

# ─── Padrões de inspeção HUD ──────────────────────────────────────────────────
INSPECTION_KEYWORDS = {
    "mists": [
        "névoa", "neblina", "sair de baróvia", "fugir da névoa",
        "escapar de baróvia", "atravessar a névoa",
        "posso sair", "tem saída", "saída de baróvia",
    ],
    "strahd_awareness": [
        "strahd me vê", "strahd sabe", "strahd está me vigiando",
        "espiões de strahd", "estou sendo vigiado", "nível de ameaça",
        "strahd_awareness", "quanto strahd sabe", "o que strahd sabe de mim",
    ],
    "barovian_rules": [
        "sol de baróvia", "luz solar aqui", "magia planar", "teleporte aqui",
        "posso usar teleporte", "plane shift", "almas de baróvia",
        "quantos têm alma", "barovianos sem alma",
    ],
}

# ─── Tabelas de encontros em viagem ──────────────────────────────────────────

_ENCONTROS_DIA = [
    "Uma matilha de dire wolves (3d4) emerge da névoa lateral da estrada, farejando sangue.",
    "Um cavaleiro esqueleto (Death's Head) bloqueia a estrada em silêncio absoluto.",
    "Druidas enlouquecidos de Yester Hill conduzem um bloco de Vine Blights pela trilha.",
    "Dois Vistani bêbados reconhecem o jogador e oferecem informação suspeita por ouro.",
    "Uma carroça abandonada com marcas de garras e uma tocha ainda acesa.",
    "Um mensageiro do Barão Vargas exige saber para onde o jogador está indo.",
    "Crianças barovianas sem alma caminham em fila silenciosa em direção contrária.",
    "Uma emboscada de bandidos (Barovian thugs) desesperados por comida e moedas.",
]

_ENCONTROS_NOITE = [
    "Três Vampire Spawn saltam das sombras, movendo-se com velocidade sobrenatural.",
    "Uma She-Wolf (Werewolf) rastreia o grupo há horas — e agora para à frente deles.",
    "Um enxame de morcegos mergulha em formação cerrada — claramente guiados por inteligência.",
    "Figuras encapuzadas (Will-o'-Wisps) acenam da linha das árvores sussurrando nomes.",
    "Uma Banshee grita a 30 metros — teste de CON DC 13 ou perder 1d6 de CON temporária.",
    "Um cavaleiro da Ordem do Dragão Prateado (Revenant) bloqueia a estrada e exige propósito.",
    "Lobos (5d6) circundam o grupo em formação de caça — aguardando o sinal para atacar.",
    "Uma figura solitária na estrada revela ser um Shadow quando a tocha a ilumina.",
]

# ─── Tempo de viagem entre locais (em horas simuladas) ───────────────────────

_TRAVEL_HOURS = {
    frozenset({"vila_barovia", "estrada_svalich"}): 1,
    frozenset({"estrada_svalich", "acampamento_tser_pool"}): 2,
    frozenset({"estrada_svalich", "vallaki"}): 4,
    frozenset({"vallaki", "acampamento_tser_pool"}): 2,
    frozenset({"vallaki", "moinho_dos_ossos"}): 3,
    frozenset({"vallaki", "krezk_abadia"}): 6,
    frozenset({"vallaki", "argynvostholt"}): 4,
    frozenset({"moinho_dos_ossos", "argynvostholt"}): 2,
    frozenset({"templo_de_ambar", "castelo_ravenloft"}): 8,
    frozenset({"castelo_ravenloft", "vila_barovia"}): 5,
}
_DEFAULT_TRAVEL_HOURS = 3

# ─── Tags emitidas pelo GM (parsadas por post_narrative_hook) ─────────────────

_TAG_MISTS        = re.compile(r"\[ENTERING_MISTS\]", re.IGNORECASE)
_TAG_NO_SOUL      = re.compile(r"\[NPC_NO_SOUL:([^\]]+)\]", re.IGNORECASE)
_TAG_AWARENESS    = re.compile(r"\[STRAHD_AWARENESS:\+(\d+)\]", re.IGNORECASE)

# ─── API pública ──────────────────────────────────────────────────────────────

def build_gm_context_block(world_state: dict) -> str:
    """Injeta todas as leis de Baróvia no system prompt do GM a cada turno."""
    lines = ["", "--- LEIS DE BARÓVIA (REGRAS DO SEMIPLANO) ---"]

    # Lei 1 — Névoas
    in_mists = world_state.get("in_mists", False)
    lines.append(
        "NÉVOAS: Se o jogador tentar deixar Baróvia ou navegar por área não mapeada, "
        "narre a névoa engolindo-o com [MOOD:tense]. "
        "Role mentalmente DC 18 CON: falha → inclua [STATUS_UPDATE] {\"hp_change\": -3}. "
        "Redirecione-o de volta ao último local conhecido. "
        "Inclua a tag [ENTERING_MISTS] no início da resposta se isso acontecer."
    )
    if in_mists:
        lines.append(
            "ATENÇÃO: O jogador está atualmente DENTRO DA NÉVOA. "
            "Continue narrando a desorientação até que ele aceite voltar. "
            "Cada turno dentro aplica novo DC 18 CON ([STATUS_UPDATE] {\"hp_change\": -3} se falhar). "
            "Remove [ENTERING_MISTS] da resposta quando ele retornar ao caminho."
        )

    # Lei 2 — Almas
    soul_cache = world_state.get("npc_soul_cache", {})
    lines.append(
        "ALMAS: 90% dos barovianos são cascas sem alma criadas pela consciência de Strahd. "
        "Para qualquer NPC anônimo não listado em npcs.json, role 1d10 mentalmente: "
        "1-9 = sem alma (voz monótona, roupas cinzas, indiferença total a humor e tragédia); "
        "10 = tem alma (reações emocionais normais). "
        "Bardo tem Desvantagem automática em persuasão/inspiração com NPCs sem alma. "
        "Strahd NUNCA se alimenta de cascas (sangue sem alma é insípido). "
        "Ao introduzir um NPC sem alma, inclua [NPC_NO_SOUL:nome_do_npc] no final da resposta. "
        "NPCs com alma já conhecidos: " +
        (", ".join(f"{k}=COM_ALMA" for k, v in soul_cache.items() if v) or "nenhum") + ". "
        "NPCs sem alma conhecidos: " +
        (", ".join(k for k, v in soul_cache.items() if not v) or "nenhum") + "."
    )

    # Lei 3 — Espiões de Strahd
    awareness = world_state.get("strahd_awareness", 0)
    counter   = world_state.get("time_of_day_counter", 0)
    is_dusk_dawn = (counter % 5 == 0 and counter > 0)
    awareness_label = (
        "CRÍTICO — retaliação direta iminente" if awareness >= 80 else
        "ALTO — Strahd pode aparecer pessoalmente" if awareness >= 50 else
        "MÉDIO — espiões ativos mas Strahd aguarda" if awareness >= 20 else
        "BAIXO — Strahd ignora o grupo por ora"
    )
    lines.append(
        f"ESPIÕES DE STRAHD (strahd_awareness={awareness}/100 — {awareness_label}): "
        "Strahd monitora via morcegos, lobos e Vistani. "
        "Se o jogador fizer: magia visível em espaço aberto (+20), matar servo de Strahd (+30), "
        "andar com tocha à noite fora de cidade (+10), ação heroica espalhafatosa em público (+15) — "
        "inclua [STRAHD_AWARENESS:+N] ao final da resposta com o valor exato. "
        + (
            f"AMANHECER/ANOITECER: Os espiões acabaram de reportar a Strahd. "
            + ("Narre uma retaliação imediata — um tenente de elite ou o próprio Strahd aparece." if awareness >= 80 else
               "Strahd observa de longe mas não age ainda." if awareness >= 50 else
               "Strahd recebe o relatório com indiferença.")
            if is_dusk_dawn else ""
        )
    )

    # Lei 4 — Viagem (encontro pendente)
    encounter = world_state.get("travel_encounter_pending")
    if encounter:
        lines.append(
            f"ENCONTRO EM VIAGEM PENDENTE: Durante a última viagem, o seguinte aconteceu e "
            f"ainda não foi resolvido: \"{encounter}\". "
            "Narre este encontro AGORA antes de descrever a chegada ao destino. "
            "Após narrado, o jogador deve lidar com a situação."
        )

    # Lei 5 — Magia e luz
    lines.append(
        "MAGIA E LUZ: "
        "(a) A luz do dia de Baróvia NÃO é luz solar real — vampiros não sofrem dano solar, "
        "apenas são fotossensíveis às nuvens e preferem ambientes fechados de dia. "
        "(b) Magias de escape planar (Teleport, Plane Shift, Dimension Door para fora de Baróvia) "
        "FALHAM automaticamente — a magia colide contra a barreira do semiplano e se dissolve. "
        "Não aplique [STATUS_UPDATE]; o feitiço simplesmente não funciona. "
        "(c) Magias de comunicação planar (Sending, Scrying para fora) chegam distorcidas ou "
        "são bloqueadas completamente."
    )

    return "\n".join(lines)


def post_narrative_hook(world_state: dict, gm_narrative: str) -> dict:
    """
    Chamado após cada resposta do GM.
    Parseia tags especiais e atualiza world_state com o novo estado das leis.
    """
    # ── [ENTERING_MISTS] ──────────────────────────────────────────────────────
    if _TAG_MISTS.search(gm_narrative):
        world_state["in_mists"] = True
    else:
        world_state["in_mists"] = False

    # ── [NPC_NO_SOUL:nome] ────────────────────────────────────────────────────
    soul_cache = world_state.get("npc_soul_cache", {})
    for match in _TAG_NO_SOUL.finditer(gm_narrative):
        npc_name = match.group(1).strip().lower()
        if npc_name not in soul_cache:
            soul_cache[npc_name] = False   # False = sem alma
    world_state["npc_soul_cache"] = soul_cache

    # ── [STRAHD_AWARENESS:+N] ─────────────────────────────────────────────────
    for match in _TAG_AWARENESS.finditer(gm_narrative):
        delta = int(match.group(1))
        current = world_state.get("strahd_awareness", 0)
        world_state["strahd_awareness"] = min(100, current + delta)

    # ── Avança contador de tempo (dawn/dusk a cada 5 turnos) ─────────────────
    counter = world_state.get("time_of_day_counter", 0) + 1
    world_state["time_of_day_counter"] = counter

    # ── Limpa encontro pendente se já está no destino ─────────────────────────
    if world_state.get("travel_encounter_pending") and not world_state.get("in_mists"):
        # O GM narrou o encontro (assumido após 1 turno com pending ativo)
        world_state["travel_encounter_pending"] = None

    return world_state


def on_travel(world_state: dict, old_loc: str, new_loc: str) -> dict:
    """
    Chamado quando current_location_key muda.
    Calcula encontros aleatórios baseados no tempo de viagem.
    """
    hours = _TRAVEL_HOURS.get(frozenset({old_loc, new_loc}), _DEFAULT_TRAVEL_HOURS)

    # Dia ou noite? (counter par = dia, ímpar = noite — simplificação)
    is_night = (world_state.get("time_of_day_counter", 0) % 2 == 1)
    pool = _ENCONTROS_NOITE if is_night else _ENCONTROS_DIA

    # Uma rolagem por hora de viagem; chance base 25%
    encounter = None
    for _ in range(hours):
        if random.random() < 0.25:
            encounter = random.choice(pool)
            break

    if encounter:
        world_state["travel_encounter_pending"] = encounter

    return world_state


def get_inspect_response(world_state: dict) -> str:
    """Resposta HUD quando o jogador perguntar sobre névoa, espiões ou regras mágicas."""
    awareness  = world_state.get("strahd_awareness", 0)
    in_mists   = world_state.get("in_mists", False)
    soul_cache = world_state.get("npc_soul_cache", {})

    parts = []

    if in_mists:
        parts.append(
            "Você está dentro da névoa de Ravenloft. "
            "Cada momento aqui corrói sua vitalidade — volte ao caminho."
        )

    awareness_desc = (
        "Strahd está apontando diretamente para você — retaliação é iminente." if awareness >= 80 else
        "Strahd está pessoalmente atento aos seus movimentos." if awareness >= 50 else
        "Os espiões de Strahd te monitoram mas ele não age ainda." if awareness >= 20 else
        "Strahd mal sabe que você existe por ora."
    )
    parts.append(f"Nível de consciência de Strahd: {awareness}/100. {awareness_desc}")

    sem_alma = [k for k, v in soul_cache.items() if not v]
    if sem_alma:
        parts.append(
            f"NPCs confirmados sem alma: {', '.join(sem_alma)}. "
            "Persuasão tem Desvantagem automática com eles."
        )

    parts.append(
        "Lembre-se: a luz solar aqui não fere vampiros. "
        "Magia de escape planar não funciona em Baróvia."
    )

    return " ".join(parts)
