"""
Leis de Baróvia — Fase 9.5
Mecânicas sistêmicas do Capítulo 2 de Curse of Strahd.

Interface pública (campaign_manager hooks):
  INSPECTION_KEYWORDS    — padrões HUD
  build_gm_context_block — injetado no system prompt do GM a cada turno
  post_narrative_hook    — parseia tags da resposta do GM, atualiza world_state
  on_travel              — chamado quando current_location_key muda
  get_inspect_response   — resposta HUD para queries do jogador
"""

import json
import os
import random
import re

# ═══════════════════════════════════════════════════════════════════════════════
# LISTAS OFICIAIS DE NOMES BAROVIANOS (CoS Apêndice p.28)
# ═══════════════════════════════════════════════════════════════════════════════

_NAMES_M = [
    "Alek", "Andrej", "Anton", "Balthazar", "Bogan", "Boris", "Dargos",
    "Darzin", "Dragomir", "Emeric", "Falkon", "Frederich", "Franz", "Gargosh",
    "Gorek", "Grygori", "Hans", "Harkus", "Ivan", "Jirko", "Kobal", "Korga",
    "Krystofor", "Lazlo", "Livius", "Marek", "Miroslav", "Nikolaj", "Nimir",
    "Oleg", "Radovan", "Radu", "Seraz", "Sergei", "Stefan", "Tural",
    "Valentin", "Vasily", "Vladislav", "Waltar", "Yesper", "Zsolt",
]

_NAMES_F = [
    "Alana", "Clavdia", "Danya", "Dezdrelda", "Diavola", "Dorina", "Drasha",
    "Drilvia", "Elisabeta", "Fatima", "Grilsha", "Isabella", "Ivana",
    "Jarzinka", "Kala", "Katerina", "Kereza", "Korina", "Lavinia", "Magda",
    "Marta", "Mathilda", "Minodora", "Mirabel", "Miruna", "Nimira", "Nyanka",
    "Olivenka", "Ruxandra", "Serina", "Tereska", "Valentina", "Vasha",
    "Victoria", "Wensencia", "Zondra",
]

# Sobrenomes: (forma masculina, forma feminina)
_SURNAMES: list = [
    ("Alastroi",         "Alastroi"),
    ("Antonovich",       "Antonova"),
    ("Barthos",          "Barthos"),
    ("Belasco",          "Belasco"),
    ("Cantemir",         "Cantemir"),
    ("Dargovich",        "Dargova"),
    ("Diavolov",         "Diavolov"),
    ("Diminski",         "Diminski"),
    ("Dilisnya",         "Dilisnya"),
    ("Drazkoi",          "Drazkoi"),
    ("Garvinski",        "Garvinski"),
    ("Grejenko",         "Grejenko"),
    ("Groza",            "Groza"),
    ("Grygorovich",      "Grygorova"),
    ("Ivanovich",        "Ivanova"),
    ("Janek",            "Janek"),
    ("Karushkin",        "Karushkin"),
    ("Konstantinovich",  "Konstantinova"),
    ("Krezkov",          "Krezkova"),
    ("Krykski",          "Krykski"),
    ("Lansten",          "Lansten"),
    ("Lazarescu",        "Lazarescu"),
    ("Lukresh",          "Lukresh"),
    ("Lipsiege",         "Lipsiege"),
    ("Martikov",         "Martikova"),
    ("Mironovich",       "Mironovna"),
    ("Moldovar",         "Moldovar"),
    ("Nikolovich",       "Nikolova"),
    ("Nimirovich",       "Nimirova"),
    ("Oronovich",        "Oronova"),
    ("Petrovich",        "Petrovna"),
    ("Polensky",         "Polensky"),
    ("Radovich",         "Radova"),
    ("Rilsky",           "Rilsky"),
    ("Stefanovich",      "Stefanova"),
    ("Strazni",          "Strazni"),
    ("Swilovich",        "Swilova"),
    ("Taltos",           "Taltos"),
    ("Targolov",         "Targolova"),
    ("Tyminski",         "Tyminski"),
    ("Ulbrek",           "Ulbrek"),
    ("Ulrich",           "Ulrich"),
    ("Vadu",             "Vadu"),
    ("Voltanescu",       "Voltanescu"),
    ("Zalenski",         "Zalenski"),
    ("Zalken",           "Zalken"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

_NPC_POOL_SIZE   = 3
_MIDNIGHT_CYCLE  = 20   # meia-noite a cada 20 turnos
_DUSK_DAWN_CYCLE = 5    # amanhecer/anoitecer a cada 5 turnos

_OUTDOOR_LOCATIONS = {
    "estrada_svalich", "acampamento_tser_pool", "yester_hill",
    "cemiterio_barovia", "lago_baratok", "floresta_svalich",
    "vila_barovia",     # ruas contam como exterior
    "argynvostholt",    # mansão em ruínas, exterior conta
}

# ─── Tabelas de encontros em viagem ──────────────────────────────────────────

_ENCONTROS_DIA = [
    "Uma matilha de dire wolves (3d4) emerge da névoa lateral da estrada, farejando sangue.",
    "Um cavaleiro esqueleto (Death's Head) bloqueia a estrada em silêncio absoluto.",
    "Druidas enlouquecidos de Yester Hill conduzem Vine Blights pela trilha.",
    "Dois Vistani bêbados reconhecem o jogador e oferecem informação suspeita por ouro.",
    "Uma carroça abandonada com marcas de garras e uma tocha ainda acesa.",
    "Um mensageiro do Barão Vargas exige saber para onde o jogador está indo.",
    "Crianças barovianas sem alma caminham em fila silenciosa em direção contrária.",
    "Uma emboscada de bandidos desesperados por comida e moedas.",
]

_ENCONTROS_NOITE = [
    "Três Vampire Spawn saltam das sombras com velocidade sobrenatural.",
    "Uma She-Wolf rastreia o grupo há horas — e agora para à frente deles.",
    "Um enxame de morcegos mergulha em formação cerrada, claramente guiado.",
    "Will-o'-Wisps acenam da linha das árvores sussurrando nomes do jogador.",
    "Uma Banshee grita a 30 metros — DC 13 CON ou 1d6 CON temporária.",
    "Um Revenant cavaleiro bloqueia a estrada e exige propósito da visita.",
    "Lobos (5d6) circundam em formação de caça — aguardando o sinal.",
    "Uma figura solitária revela ser um Shadow quando iluminada pela tocha.",
]

# ─── Tempo de viagem entre locais (horas simuladas) ───────────────────────────

_TRAVEL_HOURS = {
    frozenset({"vila_barovia",   "estrada_svalich"}):        1,
    frozenset({"estrada_svalich","acampamento_tser_pool"}):   2,
    frozenset({"estrada_svalich","vallaki"}):                 4,
    frozenset({"vallaki",        "acampamento_tser_pool"}):   2,
    frozenset({"vallaki",        "moinho_dos_ossos"}):        3,
    frozenset({"vallaki",        "krezk_abadia"}):            6,
    frozenset({"vallaki",        "argynvostholt"}):           4,
    frozenset({"moinho_dos_ossos","argynvostholt"}):          2,
    frozenset({"templo_de_ambar","castelo_ravenloft"}):       8,
    frozenset({"castelo_ravenloft","vila_barovia"}):          5,
}
_DEFAULT_TRAVEL_HOURS = 3

# ─── Tags emitidas pelo GM ────────────────────────────────────────────────────

_TAG_MISTS         = re.compile(r"\[ENTERING_MISTS\]",           re.IGNORECASE)
_TAG_NO_SOUL       = re.compile(r"\[NPC_NO_SOUL:([^\]]+)\]",     re.IGNORECASE)
_TAG_AWARENESS     = re.compile(r"\[STRAHD_AWARENESS:\+(\d+)\]", re.IGNORECASE)
_TAG_VISTANI_CURSE = re.compile(r"\[VISTANI_CURSE:([^\]]+)\]",   re.IGNORECASE)
_TAG_RAVEN         = re.compile(r"\[RAVEN_ATTACKED\]",           re.IGNORECASE)
_TAG_NPC_USED      = re.compile(r"\[NPC_USED:([^\]]+)\]",        re.IGNORECASE)
_TAG_GOTHIC_LOOT   = re.compile(r"\[GOTHIC_LOOT_REQUESTED\]",    re.IGNORECASE)

_TRINKETS_PATH     = os.path.join(os.path.dirname(__file__), "gothic_trinkets.json")
_MAX_INVENTORY_SLOTS = 10

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS PRIVADOS
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_npc_profile(gender: str = None) -> dict:
    """Gera um perfil NPC baroviano com nome oficial, gênero e status de alma."""
    if gender not in ("m", "f"):
        gender = random.choice(("m", "f"))
    name = random.choice(_NAMES_M if gender == "m" else _NAMES_F)
    surname_m, surname_f = random.choice(_SURNAMES)
    surname  = surname_m if gender == "m" else surname_f
    has_soul = random.randint(1, 10) == 10   # 10% de chance
    return {
        "full_name": f"{name} {surname}",
        "gender":    gender,
        "has_soul":  has_soul,
    }


def _replenish_pool(world_state: dict) -> None:
    """Garante que npc_pool tenha sempre _NPC_POOL_SIZE perfis prontos."""
    pool = world_state.setdefault("npc_pool", [])
    while len(pool) < _NPC_POOL_SIZE:
        pool.append(_generate_npc_profile())


def _gender_pt(gender: str) -> str:
    return "ele" if gender == "m" else "ela"


def _load_trinkets() -> list:
    try:
        with open(_TRINKETS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# INSPECTION KEYWORDS
# ═══════════════════════════════════════════════════════════════════════════════

INSPECTION_KEYWORDS = {
    "mists": [
        "névoa", "neblina", "sair de baróvia", "fugir da névoa",
        "escapar de baróvia", "atravessar a névoa",
        "posso sair", "tem saída", "saída de baróvia",
    ],
    "strahd_awareness": [
        "strahd me vê", "strahd sabe", "strahd me vigia",
        "espiões de strahd", "estou sendo vigiado",
        "quanto strahd sabe", "o que strahd sabe de mim",
    ],
    "barovian_rules": [
        "sol de baróvia", "luz solar aqui", "magia planar",
        "teleporte aqui", "plane shift", "almas de baróvia",
        "quantos têm alma", "barovianos sem alma",
    ],
    "vistani_curse": [
        "maldição vistani", "mau-olhado", "estou amaldiçoado",
        "a maldição", "efeito da maldição", "maldição ativa",
    ],
    "raven_rule": [
        "corvos guardiões", "keepers of the feather",
        "inimigo dos corvos", "posso atacar corvos",
    ],
    "gothic_trinkets": [
        "bugiganga", "treco", "item estranho", "objeto macabro",
        "o que encontrei", "meus itens", "inventário gótico",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════════
# API PÚBLICA
# ═══════════════════════════════════════════════════════════════════════════════

def build_gm_context_block(world_state: dict) -> str:
    """Injeta todas as leis de Baróvia no system prompt do GM a cada turno."""
    _replenish_pool(world_state)

    counter     = world_state.get("time_of_day_counter", 0)
    location    = world_state.get("world_state", {}).get("current_location_key", "")
    in_mists    = world_state.get("in_mists", False)
    awareness   = world_state.get("strahd_awareness", 0)
    raven_enemy = world_state.get("raven_enemy", False)
    curse       = world_state.get("vistani_curse")
    soul_cache  = world_state.get("npc_soul_cache", {})
    pool        = world_state.get("npc_pool", [])

    is_dusk_dawn = (counter > 0 and counter % _DUSK_DAWN_CYCLE == 0)
    is_midnight  = (counter > 0 and counter % _MIDNIGHT_CYCLE == 0)
    is_outdoor   = location in _OUTDOOR_LOCATIONS

    lines = ["", "--- LEIS DE BARÓVIA ---"]

    # ── 1. Névoas ─────────────────────────────────────────────────────────────
    lines.append(
        "NÉVOAS: Se o jogador tentar deixar Baróvia ou navegar em área não mapeada, "
        "narre a névoa com [MOOD:tense], role DC 18 CON mentalmente "
        "(falha → [STATUS_UPDATE] {\"hp_change\": -3}), redirecione ao último local. "
        "Inclua [ENTERING_MISTS] no início da resposta se isso ocorrer."
    )
    if in_mists:
        lines.append(
            "⚠ JOGADOR NA NÉVOA: Continue a desorientação. "
            "Cada turno aplica DC 18 CON ([STATUS_UPDATE] {\"hp_change\": -3} se falhar). "
            "Retire [ENTERING_MISTS] somente ao retornar ao caminho."
        )

    # ── 2. Gerador de NPCs Barovianos ─────────────────────────────────────────
    if pool:
        npc = pool[0]
        pronoun = _gender_pt(npc["gender"])
        soul_line = (
            f"{pronoun.capitalize()} TEM ALMA — reações emocionais normais."
            if npc["has_soul"] else
            f"{pronoun.capitalize()} NÃO TEM ALMA — voz monótona, roupas cinzas, indiferença "
            "total. Bardo tem Desvantagem automática em persuasão/inspiração com esse NPC."
        )
        gender_pt = "masculino" if npc["gender"] == "m" else "feminino"
        lines.append(
            f"PRÓXIMO NPC ANÔNIMO: Use obrigatoriamente '{npc['full_name']}' ({gender_pt}). "
            f"{soul_line} "
            f"Ao introduzi-lo(a) na cena, inclua [NPC_USED:{npc['full_name']}] ao final."
        )

    # Contexto de almas já conhecidas
    soulless = [k for k, v in soul_cache.items() if not v]
    soulful  = [k for k, v in soul_cache.items() if v]
    soul_ctx = (
        "ALMAS: 90% dos barovianos anônimos não têm alma. Strahd nunca se alimenta de cascas."
        + (f" Sem alma: {', '.join(soulless)}." if soulless else "")
        + (f" Com alma: {', '.join(soulful)}." if soulful else "")
    )
    lines.append(soul_ctx)

    # ── 3. Espiões de Strahd ──────────────────────────────────────────────────
    awareness_label = (
        "CRÍTICO — retaliação direta iminente" if awareness >= 80 else
        "ALTO — Strahd pode aparecer pessoalmente"  if awareness >= 50 else
        "MÉDIO — espiões ativos, Strahd aguarda"    if awareness >= 20 else
        "BAIXO — Strahd ignora o grupo por ora"
    )
    dusk_note = ""
    if is_dusk_dawn:
        if awareness >= 80:
            dusk_note = " | AMANHECER/ANOITECER — RETALIAÇÃO: narre tenente de elite ou Strahd."
        elif awareness >= 50:
            dusk_note = " | AMANHECER/ANOITECER — Strahd observa, não age ainda."
        else:
            dusk_note = " | AMANHECER/ANOITECER — Strahd recebe relatório com indiferença."
    lines.append(
        f"ESPIÕES (awareness={awareness}/100 — {awareness_label}){dusk_note}: "
        "Ações que aumentam: magia visível exterior (+20), matar servo de Strahd (+30), "
        "tocha à noite fora de cidade (+10), ação heroica pública (+15). "
        "Se ocorrer → inclua [STRAHD_AWARENESS:+N]."
    )

    # ── 4. Vistani — Mau-Olhado ───────────────────────────────────────────────
    lines.append(
        "VISTANI — MAU-OLHADO: Ação hostil contra Vistana → NÃO é combate físico. "
        "Force teste de Vontade (Sabedoria) DC 15. "
        "Falha → maldição severa (cegueira, vulnerabilidade ou perda de item), [MOOD:dramatic], "
        "inclua [VISTANI_CURSE:descrição_breve]. "
        "Sucesso → Vistana recua com ameaça velada."
    )
    if curse:
        lines.append(
            f"⚠ MALDIÇÃO VISTANI ATIVA: '{curse}'. "
            "Aplique narrativamente em toda cena relevante. "
            "Quebra apenas com ritual, favor a Madam Eva ou sacrifício significativo."
        )

    # ── 5. Meia-Noite — Marcha dos Mortos ────────────────────────────────────
    if is_midnight:
        if is_outdoor:
            lines.append(
                "⚠ MEIA-NOITE — MARCHA DOS MORTOS: Narre AGORA com [MOOD:dramatic]: "
                "fantasmas de aventureiros passados marcham em procissão de luz verde espectral "
                "da Vila de Baróvia rumo ao Castelo Ravenloft. "
                "Os fantasmas IGNORAM o jogador — não interagem, não podem ser feridos. "
                "Um parágrafo dramático, depois retorne ao fluxo normal."
            )
        else:
            lines.append(
                "MEIA-NOITE (local fechado): Narre apenas sons etéreos distantes — "
                "passos cadenciados, sussurros — sem interromper a cena atual."
            )

    # ── 6. Regra dos Corvos ───────────────────────────────────────────────────
    lines.append(
        "CORVOS SAGRADOS: Corvos são espiões dos Keepers of the Feather (wereravens). "
        "Ataque declarado a corvo → desencoraje narrativamente com força. "
        "Se o ataque de fato ocorrer → inclua [RAVEN_ATTACKED]."
    )
    if raven_enemy:
        lines.append(
            "⚠ INIMIGO DOS CORVOS (permanente): "
            "(a) Todos os encontros de viagem usam tabela NOTURNA (mais letal), mesmo de dia. "
            "(b) Martikovs e toda facção Keepers of the Feather são permanentemente hostis — "
            "recusam abrigo, informação e qualquer ajuda. Narre hostilidade se encontrados."
        )

    # ── 7. Bugigangas Góticas ─────────────────────────────────────────────────
    lines.append(
        "BUGIGANGAS GÓTICAS: Se o jogador buscar/investigar/vasculhar (verbos de exploração) "
        "e rolar >= DC 12 (sucesso Shadowdark), e o local não tiver item de missão específico, "
        "inclua [GOTHIC_LOOT_REQUESTED] ao final da resposta para sortear uma bugiganga macabra. "
        "Não nomeie o item — o sistema fará isso na próxima resposta."
    )

    # ── 8. Viagem — encontro pendente ─────────────────────────────────────────
    encounter = world_state.get("travel_encounter_pending")
    if encounter:
        lines.append(
            f"⚠ ENCONTRO EM VIAGEM: '{encounter}'. "
            "Narre AGORA antes de descrever a chegada. O jogador resolve antes de prosseguir."
        )

    # ── 8. Gothic Loot pendente ───────────────────────────────────────────────
    gothic_pending = world_state.get("gothic_loot_pending")
    if gothic_pending:
        item = gothic_pending.get("item", "")
        lines.append(
            f"⚠ GOTHIC LOOT PRIORITÁRIO: O jogador encontrou um item macabro. "
            f"Narre a descoberta de '{item}' com dois parágrafos de atmosfera gótica sombria. "
            f"Inclua obrigatoriamente: [INVENTORY_UPDATE] {{\"add\": [\"{item}\"]}} "
            f"e [MOOD:tense] na sua resposta."
        )

    # ── 9. Magia e Luz ────────────────────────────────────────────────────────
    lines.append(
        "MAGIA E LUZ: Luz do dia não é solar real — vampiros não sofrem dano solar. "
        "Escape planar (Teleport, Plane Shift para fora) FALHA — sem [STATUS_UPDATE]. "
        "Comunicação planar para fora chega distorcida ou bloqueada."
    )

    return "\n".join(lines)


def post_narrative_hook(world_state: dict, gm_narrative: str) -> dict:
    """Parseia tags da resposta do GM e atualiza world_state."""

    # ── Névoas ────────────────────────────────────────────────────────────────
    world_state["in_mists"] = bool(_TAG_MISTS.search(gm_narrative))

    # ── NPC do pool usado ─────────────────────────────────────────────────────
    pool       = world_state.setdefault("npc_pool", [])
    soul_cache = world_state.setdefault("npc_soul_cache", {})

    for match in _TAG_NPC_USED.finditer(gm_narrative):
        used_name = match.group(1).strip()
        # Registra soul status vindo do perfil gerado pelo backend (fonte confiável)
        for profile in pool:
            if profile["full_name"] == used_name:
                soul_cache[used_name.lower()] = profile["has_soul"]
                break
        world_state["npc_pool"] = [p for p in pool if p["full_name"] != used_name]
        pool = world_state["npc_pool"]

    # ── NPC sem alma (fallback para NPCs fora do pool) ────────────────────────
    for match in _TAG_NO_SOUL.finditer(gm_narrative):
        name_key = match.group(1).strip().lower()
        if name_key not in soul_cache:   # não sobrescreve perfil do pool
            soul_cache[name_key] = False

    # ── Consciência de Strahd ─────────────────────────────────────────────────
    for match in _TAG_AWARENESS.finditer(gm_narrative):
        delta = int(match.group(1))
        world_state["strahd_awareness"] = min(100, world_state.get("strahd_awareness", 0) + delta)

    # ── Maldição Vistani ──────────────────────────────────────────────────────
    curse_match = _TAG_VISTANI_CURSE.search(gm_narrative)
    if curse_match:
        world_state["vistani_curse"] = curse_match.group(1).strip()

    # ── Corvo atacado ─────────────────────────────────────────────────────────
    if _TAG_RAVEN.search(gm_narrative):
        world_state["raven_enemy"] = True

    # ── Gothic Loot ───────────────────────────────────────────────────────────
    # Limpa pending após 1 turno (GM já narrou na resposta anterior)
    if world_state.get("gothic_loot_pending"):
        world_state["gothic_loot_pending"] = None

    if _TAG_GOTHIC_LOOT.search(gm_narrative):
        inventory = world_state.get("player_character", {}).get("inventory", [])
        slots_used = len(inventory) if isinstance(inventory, list) else 0
        if slots_used < _MAX_INVENTORY_SLOTS:
            used_trinkets = world_state.get("gothic_trinkets_used", [])
            all_trinkets  = _load_trinkets()
            available     = [t for t in all_trinkets if t not in used_trinkets]
            if not available:
                # pool esgotado — reutiliza tudo
                available = all_trinkets
                world_state["gothic_trinkets_used"] = []
            if available:
                chosen = random.choice(available)
                world_state.setdefault("gothic_trinkets_used", []).append(chosen)
                world_state["gothic_loot_pending"] = {"item": chosen}

    # ── Limpa encontro pendente após 1 turno de resolução ────────────────────
    if world_state.get("travel_encounter_pending") and not world_state.get("in_mists"):
        world_state["travel_encounter_pending"] = None

    # ── Avança contador de tempo ──────────────────────────────────────────────
    world_state["time_of_day_counter"] = world_state.get("time_of_day_counter", 0) + 1

    return world_state


def on_travel(world_state: dict, old_loc: str, new_loc: str) -> dict:
    """Calcula encontros aleatórios na viagem entre locais."""
    hours = _TRAVEL_HOURS.get(frozenset({old_loc, new_loc}), _DEFAULT_TRAVEL_HOURS)
    is_night    = (world_state.get("time_of_day_counter", 0) % 2 == 1)
    raven_enemy = world_state.get("raven_enemy", False)

    # Inimigos dos corvos sempre usam tabela noturna (mais letal)
    pool = _ENCONTROS_NOITE if (is_night or raven_enemy) else _ENCONTROS_DIA

    for _ in range(hours):
        if random.random() < 0.25:
            world_state["travel_encounter_pending"] = random.choice(pool)
            break

    return world_state


def get_inspect_response(world_state: dict) -> str:
    """Resposta HUD para queries sobre leis de Baróvia."""
    parts = []

    if world_state.get("in_mists"):
        parts.append(
            "Você está dentro da névoa de Ravenloft. "
            "Volte ao caminho — cada momento corrói sua vitalidade."
        )

    awareness = world_state.get("strahd_awareness", 0)
    label = (
        "Strahd aponta diretamente para você — retaliação iminente." if awareness >= 80 else
        "Strahd está pessoalmente atento aos seus movimentos."        if awareness >= 50 else
        "Os espiões monitoram mas Strahd não age ainda."              if awareness >= 20 else
        "Strahd mal sabe que você existe por ora."
    )
    parts.append(f"Consciência de Strahd: {awareness}/100. {label}")

    curse = world_state.get("vistani_curse")
    if curse:
        parts.append(
            f"Maldição Vistani ativa: {curse}. "
            "Quebre com ritual, favor a Madam Eva ou sacrifício significativo."
        )

    if world_state.get("raven_enemy"):
        parts.append(
            "Você é inimigo dos corvos. "
            "Keepers of the Feather são permanentemente hostis. "
            "Seus encontros em viagem são sempre os mais perigosos."
        )

    soulless = [k for k, v in world_state.get("npc_soul_cache", {}).items() if not v]
    if soulless:
        parts.append(
            f"NPCs sem alma confirmados: {', '.join(soulless)}. "
            "Persuasão com Desvantagem automática."
        )

    parts.append(
        "Magia de escape planar falha em Baróvia. "
        "A luz do dia aqui não fere vampiros."
    )

    return " | ".join(parts)
