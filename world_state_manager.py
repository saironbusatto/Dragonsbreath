import json
import os
import random
import re
import unicodedata
from openai import OpenAI
from campaign_manager import (
    get_campaign_files,
    get_class_template,
    get_player_template,
    get_world_template,
    load_campaign_data,
)


_POSITIVE_ROLE_HINTS = (
    "aliad", "mentor", "protet", "comerc", "civil", "inform", "companheir", "curandeir"
)
_NEGATIVE_ROLE_HINTS = (
    "antagon", "cult", "vil", "ameac", "boss", "vampir", "inimig", "caos"
)
_AMBIGUOUS_ROLE_HINTS = (
    "oracul", "ambigu", "ocult", "duplo", "suspeit", "enig"
)

_NPC_LABEL_HINTS = (
    "guarda", "taverneiro", "mercador", "comerciante", "campon", "viajante",
    "figura", "vulto", "homem", "mulher", "senhor", "senhora", "lady", "madam",
    "criança", "crianca", "menino", "menina", "caçador", "cacador", "conde",
    "barão", "barao", "padre", "irmão", "irmao", "irmã", "irma", "caixeiro",
    "nobre", "aristocrata", "caçadora", "cacadora",
)


def _normalize_token(value: str) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s_]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _ensure_player_resurrection_fields(state: dict) -> dict:
    if not isinstance(state, dict):
        return state
    player = state.setdefault("player_character", {})
    if not isinstance(player, dict):
        player = {}
        state["player_character"] = player
    if not isinstance(player.get("death_count"), int):
        player["death_count"] = int(player.get("death_count", 0) or 0)
    if not isinstance(player.get("resurrection_flaws"), list):
        player["resurrection_flaws"] = []
    player.setdefault("alignment", "neutro")
    state["player_character"] = player
    return state


def _slugify(value: str) -> str:
    token = _normalize_token(value)
    return token.replace(" ", "_")


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _is_empty_value(value) -> bool:
    return value in (None, "", [], {})


def _infer_moral_tonality(tipo: str) -> str:
    role = _normalize_token(tipo)
    if any(hint in role for hint in _NEGATIVE_ROLE_HINTS):
        return "negativa"
    if any(hint in role for hint in _AMBIGUOUS_ROLE_HINTS):
        return "ambigua"
    if any(hint in role for hint in _POSITIVE_ROLE_HINTS):
        return "positiva"
    return "neutra"


def _infer_social_archetype(nome: str, tipo: str) -> str:
    joined = f"{_normalize_token(nome)} {_normalize_token(tipo)}"
    if any(token in joined for token in ("strahd", "conde", "lady", "aristocrata", "nobre")):
        return "vilao_de_elite"
    if any(token in joined for token in ("comerc", "taverneir", "mercador", "caixeiro")):
        return "mercador"
    if any(token in joined for token in ("oracul", "madam", "vidente")):
        return "oraculo"
    if any(token in joined for token in ("guarda", "caçador", "cacador", "soldado")):
        return "sentinela"
    if any(token in joined for token in ("campon", "civil", "aldeao")):
        return "sobrevivente"
    return "habitante"


def _default_body_language(archetype: str) -> str:
    if archetype == "vilao_de_elite":
        return "Mantém postura impecável, queixo elevado e dedos cruzados em torre ao avaliar cada resposta."
    if archetype == "mercador":
        return "Usa mãos abertas e acolhedoras, inclinando o tronco para convidar conversa e troca."
    if archetype == "oraculo":
        return "Move as mãos lentamente sobre símbolos e cartas, com olhar distante e silencioso."
    if archetype == "sentinela":
        return "Mantém o peso do corpo firme nas pernas, ombros quadrados e atenção constante ao entorno."
    if archetype == "sobrevivente":
        return "Carrega ombros caídos e gestos contidos, como quem mede cada risco antes de agir."
    return "Adota gestos contidos e observa o ambiente antes de falar."


def _default_voice_text(moral_tonality: str, archetype: str) -> str:
    if archetype == "vilao_de_elite":
        return (
            "Fala polida, aristocrática e controlada; sedutora sem elevar o tom, "
            "com pausas frias para dominar a conversa."
        )
    if moral_tonality == "positiva":
        return (
            "Fala suave e respirada, com cadência calorosa que transmite segurança, conforto e confiança."
        )
    if moral_tonality == "negativa":
        return (
            "Fala seca e sussurrada, com pouca variação de tom, transmitindo ameaça e controle."
        )
    if moral_tonality == "ambigua":
        return (
            "Fala fluida e enigmática, alternando gentileza e opacidade para manter intenções difíceis de ler."
        )
    return "Fala direta, moderada e cautelosa, sem exagero emocional."


def _default_motivation(nome: str, tipo: str, origem: str) -> str:
    role = _normalize_token(tipo)
    name = _normalize_token(nome)
    if origem == "improvisado":
        return "Sobreviver ao cenário atual mantendo alguma vantagem sobre quem cruza seu caminho."
    if "oracul" in role or "vidente" in name:
        return "Guiar destinos sem revelar tudo de uma vez, preservando mistério e influência."
    if any(hint in role for hint in _NEGATIVE_ROLE_HINTS):
        return "Consolidar poder e manter os heróis sob pressão psicológica e estratégica."
    if "comerc" in role or "taverneir" in role:
        return "Manter o negócio vivo e lucrativo sem perder o controle do ambiente."
    if any(hint in role for hint in _POSITIVE_ROLE_HINTS):
        return "Proteger os seus e buscar uma saída menos cruel para o conflito."
    return "Manter-se relevante no equilíbrio local de poder e sobrevivência."


def _default_interaction_intent(tipo: str, moral_tonality: str) -> str:
    role = _normalize_token(tipo)
    if "oracul" in role:
        return "Entregar pistas crípticas para testar discernimento e coragem do grupo."
    if moral_tonality == "negativa":
        return "Testar limites dos heróis, sem ceder controle emocional da cena."
    if "comerc" in role or "taverneir" in role:
        return "Negociar informação ou recursos em troca de vantagem prática imediata."
    if moral_tonality == "positiva":
        return "Ajudar sem se expor além do necessário, medindo confiança mútua."
    if moral_tonality == "ambigua":
        return "Oferecer meias-verdades para orientar e confundir ao mesmo tempo."
    return "Coletar informações sobre os heróis antes de assumir compromisso."


def _improvised_profile_from_name(npc_name: str) -> dict:
    token = _normalize_token(npc_name)
    if any(k in token for k in ("taverneir", "mercador", "comerciante", "vendedor")):
        return {
            "tipo": "improvisado_mercador",
            "moral_tonalidade": "positiva",
            "arquetipo_social": "mercador",
            "motivacao_principal": "Proteger seu negócio e manter clientes influentes por perto.",
            "intencao_na_interacao": "Descobrir o que os heróis querem e cobrar um preço justo (ou vantajoso).",
        }
    if any(k in token for k in ("figura", "vulto", "encapuz", "estranho", "sombrio")):
        return {
            "tipo": "improvisado_enigmatico",
            "moral_tonalidade": "ambigua",
            "arquetipo_social": "habitante",
            "motivacao_principal": "Ocultar a própria identidade até confirmar quem está no controle da cena.",
            "intencao_na_interacao": "Testar os heróis com respostas vagas e observar fraquezas.",
        }
    if any(k in token for k in ("guarda", "soldado", "sentinela", "vigia")):
        return {
            "tipo": "improvisado_sentinela",
            "moral_tonalidade": "neutra",
            "arquetipo_social": "sentinela",
            "motivacao_principal": "Cumprir ordens e manter a ordem local sem perder autoridade.",
            "intencao_na_interacao": "Controlar acesso e extrair explicações objetivas dos heróis.",
        }
    if any(k in token for k in ("crianca", "menino", "menina", "garoto", "garota")):
        return {
            "tipo": "improvisado_civil",
            "moral_tonalidade": "positiva",
            "arquetipo_social": "sobrevivente",
            "motivacao_principal": "Permanecer em segurança em meio ao caos ao redor.",
            "intencao_na_interacao": "Pedir ajuda ou fugir de ameaça imediata.",
        }
    return {
        "tipo": "improvisado_habitante",
        "moral_tonalidade": "neutra",
        "arquetipo_social": "habitante",
        "motivacao_principal": "Sobreviver ao dia e evitar chamar atenção das forças perigosas locais.",
        "intencao_na_interacao": "Medir intenções dos heróis antes de colaborar.",
    }


def _build_npc_signature(npc_id: str, npc_data: dict | None, origem: str) -> dict:
    npc_data = npc_data or {}
    signature_raw = npc_data.get("assinatura_narrativa", {})
    if not isinstance(signature_raw, dict):
        signature_raw = {}

    name = (
        signature_raw.get("nome")
        or npc_data.get("nome")
        or npc_id.replace("_", " ").strip().title()
    )

    if origem == "improvisado":
        improvised = _improvised_profile_from_name(name)
        default_tipo = improvised["tipo"]
        moral_tonality = signature_raw.get("moral_tonalidade", improvised["moral_tonalidade"])
        archetype = signature_raw.get("arquetipo_social", improvised["arquetipo_social"])
        motivation = signature_raw.get("motivacao_principal", improvised["motivacao_principal"])
        intent = signature_raw.get("intencao_na_interacao", improvised["intencao_na_interacao"])
    else:
        default_tipo = npc_data.get("tipo", "npc_preparado")
        moral_tonality = signature_raw.get("moral_tonalidade") or _infer_moral_tonality(default_tipo)
        archetype = signature_raw.get("arquetipo_social") or _infer_social_archetype(name, default_tipo)
        motivation = signature_raw.get("motivacao_principal") or _default_motivation(
            name, default_tipo, origem
        )
        intent = signature_raw.get("intencao_na_interacao") or _default_interaction_intent(
            default_tipo, moral_tonality
        )

    posture = signature_raw.get("linguagem_corporal") or _default_body_language(archetype)
    voice = signature_raw.get("voz_textual") or _default_voice_text(moral_tonality, archetype)

    rules = _as_list(signature_raw.get("regras_de_atuacao"))
    aliases = _as_list(signature_raw.get("aliases"))
    aliases.extend(_as_list(npc_data.get("aliases")))
    aliases.extend(_as_list(npc_data.get("apelidos")))

    # Alias utilitário para nomes alternativos com "/" no nome principal.
    if "/" in name:
        aliases.extend([part.strip() for part in name.split("/") if part.strip()])

    dedup_aliases = []
    seen_aliases = set()
    for alias in [name, npc_id.replace("_", " "), *aliases]:
        norm = _normalize_token(alias)
        if not norm or norm in seen_aliases:
            continue
        seen_aliases.add(norm)
        dedup_aliases.append(alias.strip())

    return {
        "id_origem": npc_id,
        "nome": name,
        "origem": origem,
        "tipo": signature_raw.get("tipo", default_tipo),
        "motivacao_principal": motivation,
        "intencao_na_interacao": intent,
        "linguagem_corporal": posture,
        "voz_textual": voice,
        "moral_tonalidade": moral_tonality,
        "arquetipo_social": archetype,
        "camada_externa": signature_raw.get("camada_externa", npc_data.get("aparencia_facil", "")),
        "camada_oculta": signature_raw.get("camada_oculta", npc_data.get("verdade_oculta", "")),
        "regras_de_atuacao": rules,
        "aliases": dedup_aliases,
    }


def _merge_signature(existing: dict, generated: dict) -> dict:
    existing = existing if isinstance(existing, dict) else {}
    merged = {}
    for key, generated_value in generated.items():
        existing_value = existing.get(key)
        if key in ("aliases", "regras_de_atuacao"):
            merged[key] = []
            for item in _as_list(existing_value) + _as_list(generated_value):
                if item not in merged[key]:
                    merged[key].append(item)
            continue
        if _is_empty_value(existing_value):
            merged[key] = generated_value
        else:
            merged[key] = existing_value

    # Preserva campos extras já gravados no save.
    for key, existing_value in existing.items():
        if key not in merged:
            merged[key] = existing_value
    return merged


def _extract_aliases(npc_id: str, signature: dict) -> list[str]:
    aliases = _as_list(signature.get("aliases"))
    aliases.extend(_as_list(signature.get("nome")))
    aliases.extend(_as_list(signature.get("id_origem")))
    aliases.extend(_as_list(npc_id))
    return aliases


def _looks_like_npc_label(label: str) -> bool:
    token = _normalize_token(label)
    return any(hint in token for hint in _NPC_LABEL_HINTS)


def _collect_scene_npc_names(world_state_section: dict) -> list[str]:
    names: list[str] = []

    important_npcs = world_state_section.get("important_npcs_in_scene", {})
    if isinstance(important_npcs, dict):
        names.extend([name for name in important_npcs.keys() if isinstance(name, str) and name.strip()])
    elif isinstance(important_npcs, list):
        names.extend([name for name in important_npcs if isinstance(name, str) and name.strip()])

    scene = world_state_section.get("interactable_elements_in_scene", {})
    if isinstance(scene, dict):
        names.extend([name for name in scene.get("npcs", []) if isinstance(name, str) and name.strip()])
    elif isinstance(scene, list):
        # Compatibilidade com saves antigos em formato de lista.
        names.extend([name for name in scene if isinstance(name, str) and _looks_like_npc_label(name)])

    deduped = []
    seen = set()
    for name in names:
        norm = _normalize_token(name)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(name.strip())
    return deduped


def _resolve_npc_id_by_name(scene_name: str, alias_map: dict[str, str]) -> str | None:
    normalized_name = _normalize_token(scene_name)
    if not normalized_name:
        return None
    if normalized_name in alias_map:
        return alias_map[normalized_name]

    # Fallback por similaridade simples (contém).
    for alias, npc_id in alias_map.items():
        if normalized_name in alias or alias in normalized_name:
            return npc_id
    return None


def _load_campaign_npcs() -> dict:
    files = get_campaign_files()
    npcs_path = files.get("npcs", "")
    if not npcs_path:
        return {}
    try:
        return load_campaign_data(npcs_path).get("npcs", {})
    except Exception:
        return {}


def ensure_npc_signature_memory(world_state: dict) -> dict:
    """
    Garante memória persistente de assinatura de NPCs.
    - Semeia NPCs preparados da campanha (npcs.json)
    - Cria raízes para NPCs improvisados detectados na cena
    - Mantém um recorte das assinaturas ativas da cena atual
    """
    if not isinstance(world_state, dict):
        return world_state
    world_state = _ensure_player_resurrection_fields(world_state)

    ws = world_state.setdefault("world_state", {})
    if not isinstance(ws, dict):
        return world_state

    registry = ws.get("npc_signatures", {})
    if not isinstance(registry, dict):
        registry = {}

    prepared_npcs = _load_campaign_npcs()
    for npc_id, npc_data in prepared_npcs.items():
        generated = _build_npc_signature(npc_id, npc_data, origem="preparado")
        registry[npc_id] = _merge_signature(registry.get(npc_id, {}), generated)

    alias_map: dict[str, str] = {}
    for npc_id, signature in registry.items():
        if not isinstance(signature, dict):
            continue
        for alias in _extract_aliases(npc_id, signature):
            norm = _normalize_token(alias)
            if norm and norm not in alias_map:
                alias_map[norm] = npc_id

    scene_names = _collect_scene_npc_names(ws)
    scene_signatures = {}
    important_npcs = ws.get("important_npcs_in_scene", {})

    for scene_name in scene_names:
        matched_id = _resolve_npc_id_by_name(scene_name, alias_map)

        if not matched_id:
            base_id = _slugify(scene_name) or "npc"
            matched_id = f"improvisado_{base_id}"
            suffix = 2
            while matched_id in registry:
                matched_id = f"improvisado_{base_id}_{suffix}"
                suffix += 1

            generated = _build_npc_signature(
                matched_id,
                {"nome": scene_name, "tipo": "npc_improvisado"},
                origem="improvisado",
            )
            registry[matched_id] = generated
            for alias in _extract_aliases(matched_id, generated):
                norm = _normalize_token(alias)
                if norm and norm not in alias_map:
                    alias_map[norm] = matched_id

        signature = registry.get(matched_id, {})
        if not isinstance(signature, dict):
            continue

        scene_entry = dict(signature)
        scene_entry["referencia_id"] = matched_id
        if scene_name != scene_entry.get("nome"):
            scene_entry["nome_em_cena"] = scene_name

        if isinstance(important_npcs, dict):
            descriptor = important_npcs.get(scene_name)
            if isinstance(descriptor, str) and descriptor.strip():
                scene_entry["intencao_na_interacao_atual"] = descriptor.strip()

        scene_signatures[scene_name] = scene_entry

    ws["npc_signatures"] = registry
    ws["scene_npc_signatures"] = scene_signatures
    ws["scene_npc_ids"] = [
        data["referencia_id"]
        for data in scene_signatures.values()
        if isinstance(data, dict) and "referencia_id" in data
    ]
    world_state["world_state"] = ws
    return world_state


def _preserve_runtime_state(old_state: dict, new_state: dict) -> dict:
    """
    Preserva campos de runtime que o Arquivista pode omitir no JSON de retorno.
    """
    if not isinstance(old_state, dict) or not isinstance(new_state, dict):
        return new_state

    old_ws = old_state.get("world_state", {})
    new_ws = new_state.setdefault("world_state", {})
    if not isinstance(new_ws, dict):
        new_ws = {}
        new_state["world_state"] = new_ws

    if isinstance(old_ws, dict):
        if "combat_state" in old_ws and "combat_state" not in new_ws:
            new_ws["combat_state"] = old_ws["combat_state"]

    for key in (
        "narration_mood",
        "recent_narrations",
        "hdywdtd_pending",
        "hdywdtd_prompt",
        "pause_beat_count",
        "pause_beat_segments",
        "resurrection_state",
        "tutorial_turn",
        "campaign_event_state",
        "tarokka_reading",
        "in_mists",
        "strahd_awareness",
        "time_of_day_counter",
        "npc_soul_cache",
        "travel_encounter_pending",
        "consecutive_movement_turns",
        "vistani_curse",
        "raven_enemy",
        "npc_pool",
        "gothic_loot_pending",
        "gothic_trinkets_used",
    ):
        if key in old_state and key not in new_state:
            new_state[key] = old_state[key]

    old_pc = old_state.get("player_character", {})
    new_pc = new_state.setdefault("player_character", {})
    if isinstance(old_pc, dict) and isinstance(new_pc, dict):
        for key in ("death_count", "resurrection_flaws", "alignment"):
            if key in old_pc and key not in new_pc:
                new_pc[key] = old_pc[key]
        new_state["player_character"] = new_pc

    if isinstance(old_ws, dict):
        if "emotional_pacing" in old_ws and "emotional_pacing" not in new_ws:
            new_ws["emotional_pacing"] = old_ws["emotional_pacing"]

    return new_state


# NPCs críticos: se o Arquivista os colocar fora do home_location sem gatilho, bloqueamos
_CRITICAL_NPCS = {
    "strahd":                  "castelo_ravenloft",
    "rose_ghost":              "area_20_quarto_criancas",
    "thorn_ghost":             "area_20_quarto_criancas",
    "shambling_mound_lorghoth": "area_38_camara_ritual",
}


def validate_location_transition(old_loc: str, new_loc: str, locais: dict) -> bool:
    """
    Verifica se a transição old_loc → new_loc é válida segundo o grafo de exits.
    Se old_loc não tem exits mapeados (legado ou mundo aberto), permite tudo.
    """
    if old_loc == new_loc:
        return True
    old_data = locais.get(old_loc, {})
    exits = old_data.get("exits")
    if not exits:
        return True  # local sem mapa MUD — sem restrição
    return new_loc in exits.values()


def _enforce_critical_npc_locations(novo_estado: dict) -> dict:
    """
    Valida NPCs críticos no novo estado.
    Se um NPC crítico aparecer em important_npcs_in_scene e o player NÃO estiver
    no home_location desse NPC, remove-o da cena e injeta nota de correção.
    """
    ws = novo_estado.get("world_state", {})
    if not isinstance(ws, dict):
        return novo_estado

    current_loc = ws.get("current_location_key", "")
    npcs_in_scene = ws.get("important_npcs_in_scene", {})
    if not isinstance(npcs_in_scene, dict):
        return novo_estado

    corrections = []
    for npc_id, home_loc in _CRITICAL_NPCS.items():
        if npc_id in npcs_in_scene and current_loc != home_loc:
            del npcs_in_scene[npc_id]
            corrections.append(npc_id)

    if corrections:
        existing = novo_estado.get("_npc_correction_pending", [])
        if isinstance(existing, list):
            existing.extend(corrections)
        else:
            existing = corrections
        novo_estado["_npc_correction_pending"] = existing

    return novo_estado


def update_world_state(old_state: dict, player_action: str, gm_response: str) -> dict:
    """
    Usa a IA Arquivista para atualizar o estado do mundo baseado nos eventos recentes.
    """
    # Atualização silenciosa do estado
    
    # SYSTEM: papel e instruções fixas do Arquivista
    archivista_system = """Você é o Arquivista — um sistema silencioso que mantém o estado de um RPG.
Sua única tarefa: receber um JSON de estado e eventos recentes, e retornar o JSON atualizado.
Retorne APENAS o JSON completo e válido. Nenhuma palavra, explicação ou markdown extra.

REGRAS DE ATUALIZAÇÃO:
1. Atualize 'immediate_scene_description' com a situação atual.
2. Atualize 'current_location_key' se o jogador mudou de local.
3. Adicione/remova NPCs em 'important_npcs_in_scene' conforme necessário.
4. Atualize 'active_quests' se missões foram iniciadas ou completadas.
5. Mantenha 'recent_events_summary' com os 3-4 eventos mais recentes.
6. Atualize inventário e status do personagem se necessário.
7. MAPA SEMÂNTICO DA CENA: Preencha 'interactable_elements_in_scene' dentro de 'world_state' como um dicionário com estas chaves exatas:
   - "objetos": lista de objetos standalone presentes (ex: ["vela", "balcão", "livro"])
   - "npcs": lista de personagens/criaturas presentes (ex: ["taverneiro", "figura encapuzada"])
   - "npc_itens": dicionário {nome_npc: [itens visíveis]} — SOMENTE se o Mestre mencionou explicitamente (ex: {"taverneiro": ["caneca", "chave"]})
   - "containers": dicionário {container: [conteúdo visível]} — SOMENTE se o Mestre mencionou conteúdo (ex: {"baú": ["moedas"]})
   - "saidas": lista de saídas e passagens (ex: ["porta norte", "escada", "beco lateral"])
   - "chao": itens abandonados ou caídos no chão (ex: ["moeda suja", "papel amassado"])
   REGRAS: Use [] para categorias sem elementos. Extraia APENAS o que foi explicitamente mencionado pelo Mestre neste turno. Ao mudar de local, limpe o mapa e recomece.
   NOMES: Use o termo mais curto e natural. Quando um elemento tiver variações óbvias, registre-as entre parênteses. Ex: "menino (garoto, criança)", "caixa (caixote)", "figura encapuzada (homem, vulto)".
8. CONTEXTO DE ROLAGEM: Adicione o campo "roll_context" no nível raiz do JSON com um destes valores:
   - "advantage" — se a situação atual favorece claramente a classe do personagem para a próxima ação de risco (ex: Bardo em negociação social, Inquisidor confrontando morto-vivo)
   - "disadvantage" — se a situação desfavorece (ex: Bardo em combate físico direto, Ocultista em tarefa de força bruta)
   - "normal" — padrão; nenhum fator contextual determinante
   Baseie-se na classe em player_character.class e no contexto atual da cena."""

    # USER: o estado atual + o que acabou de acontecer
    archivista_user = f"""JSON DO ESTADO ATUAL:
{json.dumps(old_state, indent=2, ensure_ascii=False)}

EVENTOS RECENTES:
- Ação do jogador: "{player_action}"
- Resposta do Mestre: "{gm_response}"

Retorne o JSON atualizado:"""

    try:
        response = get_openai_response_archivista(archivista_system, archivista_user)
        novo_estado = json.loads(response)
        if not novo_estado:
            return old_state
        novo_estado = _preserve_runtime_state(old_state, novo_estado)
        novo_estado = _enforce_critical_npc_locations(novo_estado)
        return ensure_npc_signature_memory(novo_estado)
    except json.JSONDecodeError:
        # JSON inválido - mantém estado anterior
        return old_state

def get_openai_response_archivista(system_content: str, user_content: str) -> str:
    """Arquivista via Groq Llama 3.3 70B — rápido e gratuito."""
    try:
        groq_key   = os.environ.get('GROQ_API_KEY')
        openai_key = os.environ.get('OPENAI_API_KEY')

        if groq_key:
            client     = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            model_name = os.environ.get('GROQ_MODEL_ARQUIVISTA', 'llama-3.3-70b-versatile')
        elif openai_key:
            client     = OpenAI(api_key=openai_key)
            model_name = os.environ.get('OPENAI_MODEL_ARQUIVISTA', 'gpt-4o-mini')
        else:
            return "{}"

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception:
        return "{}"

def create_initial_world_state(character_name: str, player_class: str | None = None) -> dict:
    """Cria o estado inicial do mundo para um novo jogo."""
    player_template = get_player_template()
    world_template = get_world_template()

    resolved_class = player_class or player_template.get("class", "Aventureiro")
    class_tpl = get_class_template(resolved_class) if player_class else None
    source = class_tpl if class_tpl else player_template

    state = {
        "player_character": {
            "name": character_name,
            "class": resolved_class,
            "current_act": 1,
            "status": {
                "hp": source.get("starting_hp", 20),
                "max_hp": source.get("starting_hp", 20)
            },
            "max_slots": source.get("max_slots", 10),
            "slots_iniciais": source.get("slots_iniciais", len(source.get("starting_inventory", []))),
            "inventory": source.get("starting_inventory", []),
            "desejo": world_template.get("initial_quest", "Explorar o mundo"),
            "death_count": 0,
            "resurrection_flaws": [],
            "alignment": "neutro",
        },
        "world_state": {
            "current_location_key": world_template.get("initial_location", "local_inicial"),
            "immediate_scene_description": world_template.get("initial_description", "Você inicia uma nova aventura."),
            "active_quests": {
                "main_quest": world_template.get("initial_quest", "Explorar o mundo")
            },
            "important_npcs_in_scene": {},
            "interactable_elements_in_scene": {
                "objetos": [], "npcs": [], "npc_itens": {},
                "containers": {}, "saidas": [], "chao": []
            },
            "recent_events_summary": [
                f"{character_name} iniciou sua jornada"
            ],
            "gatilhos_ativos": world_template.get("initial_triggers", {}),
            "gatilhos_usados": {loc: [] for loc in world_template.get("initial_triggers", {}).keys()}
        }
    }
    return ensure_npc_signature_memory(_ensure_player_resurrection_fields(state))

def load_world_state(filepath: str) -> dict:
    """Carrega o estado do mundo do arquivo JSON."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
            loaded = _ensure_player_resurrection_fields(loaded)
            return ensure_npc_signature_memory(loaded)
    except (json.JSONDecodeError, KeyError):
        # Arquivo corrompido - retorna None
        return None

def save_world_state(state: dict, filepath: str):
    """Salva o estado do mundo no arquivo JSON."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
