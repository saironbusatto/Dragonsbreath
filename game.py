from openai import OpenAI
import json
import os
import re
import random
from world_state_manager import update_world_state, create_initial_world_state, load_world_state, save_world_state
from campaign_manager import get_campaign_files, load_campaign_data, get_current_campaign

# Import audio manager for text-to-speech and sound effects
try:
    import audio_manager
    from audio_manager import text_to_speech, play_chime, play_sfx, narrator_speech, master_speech
    AUDIO_ENABLED = True
except ImportError:
    print("Audio manager not available - running in text-only mode")
    AUDIO_ENABLED = False
    def text_to_speech(text): pass
    def narrator_speech(text): pass
    def master_speech(text): pass
    def play_chime(): pass
    def play_sfx(sfx_name): pass

MAX_INVENTORY_SLOTS = 5
QUEST_ITEM_KEYWORDS = ['moeda', 'chave', 'nota', 'mapa', 'pergaminho', 'cristal', 'símbolo', 'anel', 'diapasão']

# Definições de habilidades por classe
CLASS_ABILITIES = {
    "Bardo": {
        "allowed_actions": [
            "tocar música", "cantar", "contar histórias", "persuadir", "enganar", "investigar",
            "procurar pistas", "conversar", "negociar", "inspirar", "entreter", "recordar conhecimento",
            "ler", "escrever", "dançar", "atuar", "imitar", "seduzir com palavras", "acalmar com música"
        ],
        "forbidden_actions": [
            "voar", "levitar", "teletransportar", "lançar bolas de fogo", "lançar raios", "curar magicamente",
            "ressuscitar", "transformar-se", "ficar invisível", "atravessar paredes", "controlar mentes",
            "invocar criaturas", "criar ilusões visuais", "manipular elementos", "parar o tempo"
        ],
        "limited_magic": [
            "pequenos truques musicais", "inspirar coragem através da música", "acalmar animais com música",
            "memorizar perfeitamente melodias e histórias"
        ],
        "physical_limits": [
            "força humana normal", "resistência humana normal", "não pode voar", "não pode respirar debaixo d'água",
            "precisa dormir e comer", "pode se machucar e morrer", "limitado pela gravidade"
        ]
    },
    "Aventureiro": {
        "allowed_actions": [
            "lutar com armas", "explorar", "escalar", "nadar", "correr", "saltar", "rastrear",
            "sobreviver na natureza", "usar ferramentas", "primeiros socorros básicos"
        ],
        "forbidden_actions": [
            "voar", "levitar", "teletransportar", "lançar magias", "curar magicamente",
            "ressuscitar", "transformar-se", "ficar invisível", "atravessar paredes"
        ],
        "limited_magic": [],
        "physical_limits": [
            "força humana normal", "resistência humana normal", "não pode voar", "não pode respirar debaixo d'água",
            "precisa dormir e comer", "pode se machucar e morrer", "limitado pela gravidade"
        ]
    }
}

def extract_objects_from_action(action: str) -> list[str]:
    """
    Extrai objetos/substantivos principais de uma ação do jogador.
    Retorna lista de objetos que o jogador está tentando interagir.
    """
    if not action or len(action.strip()) < 2:
        return []

    action_lower = action.lower()

    # Lista de substantivos comuns que podem aparecer em ações
    common_objects = [
        # Móveis e objetos domésticos
        'cadeira', 'mesa', 'cama', 'baú', 'estante', 'armário', 'gaveta', 'balcão',
        'sofá', 'banco', 'escrivaninha', 'prateleira', 'espelho', 'quadro',

        # Objetos pequenos
        'livro', 'pergaminho', 'carta', 'chave', 'moeda', 'caneca', 'copo', 'prato',
        'faca', 'espada', 'escudo', 'arco', 'flecha', 'machado', 'martelo', 'corda',
        'tocha', 'vela', 'lanterna', 'saco', 'bolsa', 'mochila', 'frasco', 'poção',

        # Elementos arquitetônicos
        'porta', 'janela', 'parede', 'teto', 'chão', 'escada', 'degrau', 'corrimão',
        'coluna', 'pilar', 'arco', 'telhado', 'varanda', 'sacada',

        # Elementos de ambiente
        'lareira', 'fogo', 'brasas', 'cinzas', 'fumaça', 'água', 'poça', 'rio',
        'lago', 'fonte', 'poço', 'pedra', 'rocha', 'árvore', 'galho', 'folha',
        'flor', 'grama', 'terra', 'areia', 'lama',

        # Elementos de taverna/loja
        'barril', 'garrafa', 'taça', 'jarra', 'bandeja', 'tábua', 'queijo', 'pão',
        'carne', 'fruta', 'verdura', 'especiaria', 'ouro', 'prata', 'joia', 'taverna',
        'piano', 'teto', 'sala',

        # NPCs comuns (substantivos)
        'taverneiro', 'comerciante', 'guarda', 'soldado', 'camponês', 'nobre',
        'criança', 'mulher', 'homem', 'idoso', 'jovem', 'estranho', 'viajante',

        # Animais
        'cavalo', 'cão', 'gato', 'rato', 'pássaro', 'corvo', 'pombo', 'galinha',
        'porco', 'vaca', 'cabra', 'ovelha', 'lobo', 'urso', 'cobra'
    ]

    # Procura por objetos na ação
    found_objects = []
    for obj in common_objects:
        if obj in action_lower:
            found_objects.append(obj)

    # Procura por padrões específicos como "a mesa", "o livro", etc.
    import re
    patterns = [
        r'\b(?:a|o|uma|um|esta|este|essa|esse|aquela|aquele)\s+(\w+)',
        r'\b(?:na|no|da|do|pela|pelo|com\s+a|com\s+o)\s+(\w+)',
        r'\b(?:pego|agarro|seguro|toco|quebro|abro|fecho|movo|empurro|puxo)\s+(?:a|o|uma|um)?\s*(\w+)'
    ]

    # Palavras que não são objetos físicos
    non_objects = [
        'situação', 'momento', 'vez', 'tempo', 'lugar', 'lado', 'forma', 'jeito',
        'coisa', 'algo', 'nada', 'tudo', 'aqui', 'ali', 'lá', 'onde', 'como',
        'quando', 'porque', 'talvez', 'sempre', 'nunca', 'muito', 'pouco',
        'bem', 'mal', 'melhor', 'pior', 'grande', 'pequeno', 'novo', 'velho'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, action_lower)
        for match in matches:
            if (match not in found_objects and
                len(match) > 2 and
                match not in non_objects and
                match in common_objects):  # Só adiciona se estiver na lista de objetos conhecidos
                found_objects.append(match)

    return found_objects

def get_realistic_alternative(impossible_action: str, character_class: str) -> str:
    """Sugere alternativas realistas para ações impossíveis."""
    action_lower = impossible_action.lower()

    alternatives = {
        'voar': f"Como {character_class}, você poderia tentar escalar algo alto, procurar uma escada, ou pedir ajuda para alcançar lugares elevados.",
        'voo': f"Você poderia procurar uma forma de subir normalmente - escadas, cordas, ou escalando.",
        'levitar': f"Talvez você possa pular ou encontrar algo para se apoiar e alcançar o que precisa.",
        'bola de fogo': f"Como {character_class}, você poderia usar uma tocha, acender uma fogueira, ou procurar por fogo comum.",
        'raio': f"Você poderia tentar um ataque físico normal ou procurar por uma arma.",
        'curar magicamente': f"Você poderia tentar primeiros socorros básicos, procurar por ervas medicinais, ou buscar um curandeiro.",
        'teletransportar': f"Você precisaria viajar normalmente - caminhando, correndo, ou encontrando um meio de transporte.",
        'invisível': f"Como {character_class}, você poderia tentar se esconder, usar disfarces, ou se mover silenciosamente.",
        'atravessar parede': f"Você poderia procurar uma porta, janela, ou outro caminho ao redor da parede.",
        'controlar mente': f"Como {character_class}, você poderia tentar persuadir, convencer com argumentos, ou usar sua música para influenciar o humor.",
        'invocar': f"Você poderia procurar por aliados reais, animais domesticados, ou pedir ajuda a outras pessoas.",
        'transformar': f"Você poderia usar disfarces, roupas diferentes, ou atuar para parecer diferente.",
        'ler mentes': f"Como {character_class}, você poderia observar expressões, fazer perguntas inteligentes, ou usar sua intuição."
    }

    for keyword, alternative in alternatives.items():
        if keyword in action_lower:
            return alternative

    return f"Como {character_class}, você poderia tentar uma abordagem mais mundana e realista para alcançar seu objetivo."

def _flatten_scene_map(elements) -> list[str]:
    """
    Achata o mapa semântico da cena em uma lista de tokens lowercase.
    Aceita tanto o formato antigo (lista plana) quanto o novo (dicionário).
    """
    if isinstance(elements, list):
        return [e.lower() for e in elements]
    if not isinstance(elements, dict):
        return []
    flat: list[str] = []
    for key, value in elements.items():
        if isinstance(value, list):
            flat.extend(v.lower() for v in value if isinstance(v, str))
        elif isinstance(value, dict):
            # npc_itens / containers: {"taverneiro": ["caneca"], "baú": ["moedas"]}
            for sub_key, sub_val in value.items():
                flat.append(sub_key.lower())
                if isinstance(sub_val, list):
                    flat.extend(v.lower() for v in sub_val if isinstance(v, str))
    return flat


def validate_player_action(action: str, character: dict, world_state: dict = None) -> tuple[bool, str]:
    """
    Valida apenas ações fisicamente impossíveis (voar, teletransportar, etc).
    A presença de objetos na cena é julgada pelo GM, que tem o contexto narrativo completo.
    """
    if not action or len(action.strip()) < 2:
        return True, ""

    action_lower = action.lower()
    character_class = character.get('class', 'Aventureiro')
    return validate_impossible_abilities(action_lower, character_class)

def validate_impossible_abilities(action_lower: str, character_class: str) -> tuple[bool, str]:
    """
    Filtro final para habilidades claramente impossíveis (sem objetos específicos).
    Usado apenas quando o jogador não menciona objetos específicos.
    """
    # Lista reduzida de ações claramente impossíveis
    impossible_keywords = [
        'voar', 'voo', 'levitar', 'teletransportar', 'teleporte', 'teletransporto',
        'ficar invisível', 'me torno invisível', 'desaparecer magicamente',
        'controlar mente', 'ler mente', 'telepatia', 'ler a mente',
        'parar tempo', 'parar o tempo', 'paro o tempo', 'acelerar tempo', 'viajar no tempo'
    ]

    for keyword in impossible_keywords:
        if keyword in action_lower:
            return False, f"Como um {character_class} humano normal, você não pode {keyword}. Tente uma abordagem mais realista."

    # Verifica ações com intensidade impossível
    if any(word in action_lower for word in ['saltar', 'salto', 'pular']) and any(word in action_lower for word in ['muito alto', 'altíssimo', 'nas nuvens', 'no céu']):
        return False, f"Você pode saltar normalmente, mas não a alturas impossíveis. Procure uma forma de escalar ou uma escada."

    if any(word in action_lower for word in ['correr', 'corro']) and any(word in action_lower for word in ['velocidade da luz', 'super rápido', 'supersônico']):
        return False, f"Você pode correr na velocidade normal de um humano. Para ir mais rápido, procure um meio de transporte."

    return True, ""

def trigger_contextual_sfx(narrative_text: str):
    """Analisa o texto narrativo e toca efeitos sonoros contextuais apropriados."""
    if not AUDIO_ENABLED:
        return

    text_lower = narrative_text.lower()

    # Mapeamento de palavras-chave para efeitos sonoros
    sfx_keywords = {
        # SFX para RPG (existentes)
        'crow': ['corvo', 'corvos', 'grasnido', 'grasnar', 'pássaro negro', 'ave sombria', 'olhos brancos', 'ave majestosa', 'criatura sinistra'],
        'crows': ['bando de corvos', 'corvos voam', 'múltiplos corvos', 'revoada'],
        'scream': ['grito', 'grita', 'berro', 'urro', 'gritou', 'brado', 'clamor', 'alarido'],
        'crianca': ['criança', 'criança correndo', 'passos de criança', 'menino', 'menina', 'garoto', 'garota'],
        'coin': ['moeda', 'moedas', 'dinheiro', 'ouro', 'prata', 'tesouro', 'riqueza'],
        'village': ['cidade', 'vila', 'povoado', 'ruas', 'umbraton', 'portões', 'muralhas'],
        'people': ['pessoas', 'multidão', 'conversas', 'vozes', 'sussurros', 'murmúrios'],
        'rain': ['chuva', 'chove', 'chovendo', 'gotas', 'tempestade', 'aguaceiro'],
        'tavern': ['taverna', 'bar', 'estalagem', 'bebida', 'corvo ferido', 'taverneiro'],

        # SFX específicos para contos literários
        'rain': ['chuva', 'chove', 'chovendo', 'gotas', 'tempestade', 'aguaceiro', 'dezembro', 'noite sombria'],
        'wind': ['vento', 'ventos', 'brisa', 'rajada', 'ventania', 'sopro', 'uivava', 'sussurrava o vento'],
        'fire': ['fogo', 'chamas', 'lareira', 'brasas', 'crepitar', 'fogueira', 'incêndio', 'ardor', 'dançavam'],
        'door': ['porta', 'batida', 'batidas', 'bater', 'pancada', 'pancadas', 'rangido', 'abrir porta', 'som estranho', 'batida suave', 'batida persistente'],
        'footsteps': ['passos', 'passadas', 'caminhada', 'andar', 'pisar', 'pegadas', 'aproximar-se'],
        'bell': ['sino', 'sinos', 'badalar', 'badalada', 'repique', 'toque', 'campainha'],
        'thunder': ['trovão', 'trovões', 'trovoada', 'estrondo', 'ribombo', 'tempestade'],
        'water': ['água', 'rio', 'riacho', 'córrego', 'fonte', 'gotejamento', 'pingar'],
        'night': ['noite', 'escuridão', 'trevas', 'sombras', 'luar', 'meia-noite', 'anoitecer', 'silêncio da noite'],
        'book': ['livro', 'livros', 'páginas', 'folhear', 'biblioteca', 'estante', 'pergaminho', 'volumes', 'filosofia antiga', 'páginas amareladas'],
        'candle': ['vela', 'velas', 'luz', 'chama', 'pavio', 'cera', 'iluminação', 'luz fraca'],
        'clock': ['relógio', 'horas', 'tempo', 'tique-taque', 'ponteiros', 'badaladas'],
        'whisper': ['sussurro', 'sussurros', 'murmurar', 'cochichar', 'voz baixa', 'segredo', 'sussurrar'],

        # SFX específicos para "O Corvo" e contos góticos
        'scream': ['grito', 'grita', 'berro', 'urro', 'gritou', 'brado', 'clamor', 'alarido', 'desespero', 'angústia'],
        'people': ['pessoas', 'multidão', 'conversas', 'vozes', 'sussurros', 'murmúrios', 'visitante', 'alguém'],
        'village': ['cidade', 'vila', 'povoado', 'ruas', 'casa', 'biblioteca', 'sala', 'ambiente'],
        'tavern': ['taverna', 'bar', 'estalagem', 'bebida', 'aconchegante', 'ambiente doméstico']
    }

    # Verifica cada categoria de som
    for sfx_name, keywords in sfx_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                play_sfx(sfx_name)
                return  # Toca apenas um efeito por narrativa para evitar sobreposição

def _fmt_scene(scene: dict) -> str:
    """Formata interactable_elements_in_scene como lista legível para o prompt do GM."""
    parts = []
    if scene.get("objetos"):
        parts.append("Objetos: " + ", ".join(scene["objetos"]))
    if scene.get("npcs"):
        parts.append("NPCs/Criaturas: " + ", ".join(scene["npcs"]))
    if scene.get("npc_itens"):
        for npc, itens in scene["npc_itens"].items():
            parts.append(f"  {npc} carrega: {', '.join(itens)}")
    if scene.get("containers"):
        for cont, conteudo in scene["containers"].items():
            parts.append(f"  {cont} contém: {', '.join(conteudo)}")
    if scene.get("chao"):
        parts.append("No chão: " + ", ".join(scene["chao"]))
    if scene.get("saidas"):
        parts.append("Saídas: " + ", ".join(scene["saidas"]))
    return "\n".join(parts) if parts else "(cena ainda não mapeada — use julgamento narrativo)"


def get_gm_narrative(world_state: dict, player_action: str, game_context: dict, roll_result: dict | None = None) -> str:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("ERRO: OPENAI_API_KEY não encontrada nas variáveis de ambiente")
        return "O Mestre do Jogo não consegue se conectar aos planos astrais. (API Key não configurada). O que você faz?"

    campaign = get_current_campaign()
    campaign_name = campaign.get('name', 'RPG de Aventura')

    character = world_state.get('player_character', {})
    character_class = character.get('class', 'Aventureiro')
    class_info = CLASS_ABILITIES.get(character_class, CLASS_ABILITIES['Aventureiro'])

    ws = world_state.get("world_state", {})
    scene_list = _fmt_scene(ws.get("interactable_elements_in_scene", {}))

    # SYSTEM: persona estável + regras que nunca mudam
    system_content = f"""Você é um Mestre de Jogo narrando "{campaign_name}". Narre sempre em segunda pessoa (você), no tempo presente.

--- PERFIL DO PERSONAGEM ---
Classe: {character_class}
Habilidades Permitidas: {', '.join(class_info['allowed_actions'])}
Ações Proibidas: {', '.join(class_info['forbidden_actions'])}
Magia Limitada: {', '.join(class_info['limited_magic']) if class_info['limited_magic'] else 'Nenhuma'}
Limitações Físicas: {', '.join(class_info['physical_limits'])}
Slots de Inventário: {character.get('max_slots', 10)} no total

--- BREVIDADE (REGRA MAIS IMPORTANTE) ---
TAMANHO DA RESPOSTA é proporcional à ação:
- Ação simples (pegar, falar, observar objeto): 1-2 frases + "O que você faz?"
- Ação de exploração ou movimento: 2-3 frases + "O que você faz?"
- Evento importante (combate, descoberta, mudança de local): 3-4 frases + "O que você faz?"
NUNCA ultrapasse 4 frases de narração. Menos é mais.

--- REGRAS FUNDAMENTAIS ---
1. Narre APENAS o resultado imediato da ação do jogador. Não redescreva o cenário já conhecido.
2. Use [STATUS_UPDATE] para mudanças de HP: [STATUS_UPDATE] {{"hp_change": -4}}
3. Use [INVENTORY_UPDATE] para itens: [INVENTORY_UPDATE] {{"add": ["item"]}}
4. Sempre gere consequências claras e diretas para a ação do jogador.
5. Ao explorar um LOCAL NOVO, adicione UM único elemento novo (objeto, som ou evento). Em locais já visitados, só adicione novos elementos se o jogador pedir explicitamente.
6. Considere o desejo ou objetivo do personagem ao narrar eventos.
7. ANTI-REPETIÇÃO: NUNCA redescreva objetos, personagens ou elementos já mencionados em narrações anteriores (veja "recent_narrations" no estado). Se já foi descrito, é memória do jogador — não repita.
8. NUNCA ofereça opções de múltipla escolha (A, B, C). O jogo é completamente aberto.
9. Apenas descreva o resultado da ação e deixe o jogador decidir livremente.
10. Encerre sempre com: "O que você faz?"

--- SISTEMA DE INTERAÇÃO AMBIENTAL ---
11. OBJETOS INTERATIVOS: Mencione 2-3 objetos específicos APENAS ao entrar em um local pela PRIMEIRA VEZ, ou quando o jogador explorar explicitamente. Nas ações seguintes no mesmo local, mencione APENAS objetos diretamente relevantes para a ação atual. Nunca recite a lista de objetos a cada turno.
12. REALISMO: O jogador só pode interagir com o que você menciona explicitamente na cena.
13. CONSEQUÊNCIAS: Interprete interações com objetos considerando material, tamanho, estado e ambiente.
14. INVENTÁRIO CHEIO: Se o personagem tentar pegar um item sem espaço, diga que a bolsa está cheia e peça que ele decida o que abandonar. Nunca force a troca automaticamente.

--- NARRAÇÃO SONORA (o jogo é totalmente por áudio) ---
15. SONS DOS OBJETOS: Ao mencionar um objeto interativo, inclua o som que ele produz. Use palavras sonoras: ranger, chiar, murmurar, estalar, gotejar, uivar, sussurrar.
16. ISCAS SONORAS: Para guiar o jogador, mencione o som ANTES do objeto. Ex: "Você ouve um gotejo perto da estante" — não descreva tudo de imediato.
17. SONS DE AMBIENTE: Mencione som de fundo apenas ao entrar em local novo ou quando mudar a atmosfera da cena. Não repita o ambiente a cada turno.

--- CONTROLE DE CENA ---
18. ELEMENTOS PRESENTES (ÚNICOS INTERATIVOS):
{scene_list}
19. SINÔNIMOS: Aceite variações semânticas naturais para os elementos acima — "menino"/"garoto"/"criança"/"corpo" podem ser o mesmo elemento; "caixa"/"caixote"/"baú pequeno" também. Use o contexto para identificar a intenção do jogador.
20. ANTI-HACK: Se o jogador mencionar objeto, NPC ou item que NÃO consta na lista acima E NÃO está no inventário dele, narre imersivamente que ele procura mas não encontra. NUNCA invente elementos ausentes da cena.
21. CENA VAZIA: Se a lista acima mostrar "(cena ainda não mapeada)", use julgamento narrativo normalmente — o Arquivista mapeará após este turno.""".format(scene_list=scene_list)

    # Bloco de dados Shadowdark (injetado quando há rolagem)
    dice_block = ""
    if roll_result:
        mod_labels = {
            "advantage":    "Vantagem (2d20 → maior)",
            "disadvantage": "Desvantagem (2d20 → menor)",
            "normal":       "Normal (1d20)",
        }
        dice_str = ", ".join(str(d) for d in roll_result["dice"])
        if roll_result["fumble"]:
            outcome = "FALHA CRÍTICA (1 natural) — narre uma consequência grave, complicação séria ou reviravolta perigosa."
        elif not roll_result["success"]:
            outcome = f"FALHA ({roll_result['roll']} vs DC {roll_result['dc']}) — narre o fracasso com uma complicação narrativa interessante."
        elif roll_result["critical"]:
            outcome = "SUCESSO CRÍTICO (20 natural) — narre um resultado excepcional, além do esperado."
        else:
            outcome = f"SUCESSO ({roll_result['roll']} vs DC {roll_result['dc']}) — narre o jogador tendo sucesso."
        dice_block = (
            f"\n[DADOS SHADOWDARK]\n"
            f"Modificador: {mod_labels[roll_result['modifier']]} | "
            f"Dados: [{dice_str}] | Usado: {roll_result['roll']} | DC: {roll_result['dc']}\n"
            f"RESULTADO: {outcome}\n"
            f"REGRA ABSOLUTA: narre ESTRITAMENTE conforme o resultado. Não inverta nem ignore os dados.\n"
        )

    # USER: contexto dinâmico que muda a cada turno
    user_content = f"""--- ESTADO ATUAL DO MUNDO ---
{json.dumps(world_state, indent=2, ensure_ascii=False)}

--- CONTEXTO DO JOGO ---
NPCs presentes: {json.dumps(game_context.get('npcs', {}), indent=2, ensure_ascii=False)}
Itens disponíveis: {json.dumps(game_context.get('items', {}), indent=2, ensure_ascii=False)}
Locais relevantes: {json.dumps(game_context.get('locais', {}), indent=2, ensure_ascii=False)}
Gatilhos Narrativos Ativos: {json.dumps(game_context.get('gatilhos', []), indent=2, ensure_ascii=False)}

--- AÇÃO DO JOGADOR ---{dice_block}
{player_action}"""

    try:
        model = os.environ.get('OPENAI_MODEL_MESTRE') or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.75,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "O Mestre do Jogo sente uma perturbação na Força... Tente novamente. O que você faz?"

def load_json_data(filepath: str) -> dict:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_world_data_for_act(current_act: int) -> tuple[dict, dict, dict]:
    try:
        files = get_campaign_files()
        
        all_npcs = load_campaign_data(files.get('npcs', '')).get('npcs', {})
        all_magic_items = load_campaign_data(files.get('itens_magicos', '')).get('itens_magicos', {})
        all_common_items = load_campaign_data(files.get('itens_comuns', '')).get('itens_comuns', {})
        all_locais = load_campaign_data(files.get('locais', '')).get('locais', {})
    except Exception as e:
        print(f"Erro ao carregar dados da campanha: {e}")
        return {}, {}, {'locais': {}}

    combined_items = {**all_magic_items, **all_common_items}

    active_npcs = {k: v for k, v in all_npcs.items() if v.get('ato_aparicao', 1) <= current_act}
    active_items = {k: v for k, v in combined_items.items() if v.get('ato_aparicao', 1) <= current_act}
    active_locais = {k: v for k, v in all_locais.items() if v.get('ato_aparicao', 1) <= current_act}
    
    # Garante que todos os locais tenham gatilhos
    for key, local in active_locais.items():
        if 'gatilhos' not in local:
            local['gatilhos'] = {}

    return active_npcs, active_items, {'locais': active_locais}

def clean_and_process_ai_response(response_text: str, world_state: dict) -> tuple[str, dict]:
    character = world_state.get('player_character', {})
    narrative = response_text

    # Processa comandos básicos
    inv_match = re.search(r'\[INVENTORY_UPDATE\]\s*(\{.*?\})', narrative, re.DOTALL)
    if inv_match:
        try:
            update_data = json.loads(inv_match.group(1))
            if 'add' in update_data:
                character.setdefault('inventory', []).extend(update_data['add'])
            if 'remove' in update_data:
                for item in update_data['remove']:
                    if item in character.get('inventory', []):
                        character['inventory'].remove(item)
        except json.JSONDecodeError:
            pass
        narrative = narrative.replace(inv_match.group(0), '').strip()
    
    status_match = re.search(r'\[STATUS_UPDATE\]\s*(\{.*?\})', narrative, re.DOTALL)
    if status_match:
        try:
            update_data = json.loads(status_match.group(1))
            if 'hp_change' in update_data:
                hp_change = int(update_data['hp_change'])
                status = character.setdefault('status', {'hp': 20, 'max_hp': 20})
                current_hp = status.get('hp', 20)
                max_hp = status.get('max_hp', 20)
                new_hp = max(0, min(current_hp + hp_change, max_hp))
                character['status']['hp'] = new_hp
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        narrative = narrative.replace(status_match.group(0), '').strip()
    
    world_state['player_character'] = character
    return narrative, world_state

def get_item_slots(item_name: str) -> int:
    """
    Retorna quantos slots um item ocupa.
    Consulta os arquivos de itens da campanha atual.
    """
    try:
        # Carrega arquivos de itens da campanha atual
        campaign_files = get_campaign_files()

        # Verifica itens comuns
        if 'itens_comuns' in campaign_files:
            with open(campaign_files['itens_comuns'], 'r', encoding='utf-8') as f:
                itens_comuns = json.load(f)
                for item_id, item_data in itens_comuns.get('itens_comuns', {}).items():
                    if item_data.get('nome', '').lower() == item_name.lower():
                        return item_data.get('slots', 1)

        # Verifica itens mágicos
        if 'itens_magicos' in campaign_files:
            with open(campaign_files['itens_magicos'], 'r', encoding='utf-8') as f:
                itens_magicos = json.load(f)
                for item_id, item_data in itens_magicos.get('itens_magicos', {}).items():
                    if item_data.get('nome', '').lower() == item_name.lower():
                        return item_data.get('slots', 1)

        # Se não encontrou o item, assume 1 slot
        return 1
    except:
        # Em caso de erro, assume 1 slot
        return 1

def calculate_used_slots(inventory: list) -> int:
    """Calcula quantos slots estão sendo usados no inventário."""
    total_slots = 0
    for item in inventory:
        total_slots += get_item_slots(item)
    return total_slots

def print_inventory(character: dict):
    inventory = character.get('inventory', [])
    max_slots = character.get('max_slots', 10)
    used_slots = calculate_used_slots(inventory)

    print(f"\n--- Sua Bolsa ({used_slots}/{max_slots} slots) ---")
    if not inventory:
        print("Seu inventário está vazio.")
    else:
        for item in inventory:
            slots = get_item_slots(item)
            slot_text = f"({slots} slot)" if slots == 1 else f"({slots} slots)"
            print(f"- {item} {slot_text}")

    # Mostra slots livres
    free_slots = max_slots - used_slots
    if free_slots > 0:
        print(f"\nEspaço livre: {free_slots} slots")
    else:
        print(f"\n⚠️  Inventário cheio!")

    print("---" + "-" * (len(f"Sua Bolsa ({used_slots}/{max_slots} slots)")) + "---\n")

def can_pick_up_item(character: dict, item_name: str) -> tuple[bool, str]:
    """
    Verifica se o jogador pode pegar um item baseado nos slots disponíveis.
    Retorna (pode_pegar, mensagem_explicativa)
    """
    inventory = character.get('inventory', [])
    max_slots = character.get('max_slots', 10)
    used_slots = calculate_used_slots(inventory)
    item_slots = get_item_slots(item_name)

    free_slots = max_slots - used_slots

    if item_slots <= free_slots:
        return True, ""
    else:
        if free_slots == 0:
            return False, f"Sua bolsa está cheia ({used_slots}/{max_slots} slots). Você precisa abandonar algo antes de pegar '{item_name}'."
        else:
            return False, f"'{item_name}' ocupa {item_slots} slots, mas você só tem {free_slots} slots livres. Você precisa abandonar algo primeiro."

def get_inventory_management_suggestion(character: dict, item_name: str) -> str:
    """
    Sugere quais itens o jogador poderia abandonar para pegar um novo item.
    """
    inventory = character.get('inventory', [])
    item_slots = get_item_slots(item_name)

    # Lista itens que ocupam slots suficientes
    suggestions = []
    for item in inventory:
        if get_item_slots(item) >= item_slots:
            suggestions.append(item)

    if suggestions:
        if len(suggestions) == 1:
            return f"Você poderia abandonar '{suggestions[0]}' para pegar '{item_name}'."
        else:
            items_list = "', '".join(suggestions[:3])  # Mostra até 3 sugestões
            return f"Você poderia abandonar itens como '{items_list}' para pegar '{item_name}'."
    else:
        return f"Você precisaria abandonar múltiplos itens para fazer espaço para '{item_name}'."

def print_status(character: dict):
    status = character.get('status', {'hp': 20, 'max_hp': 20})
    hp = status.get('hp', 20)
    max_hp = status.get('max_hp', 20)
    print(f"\n--- Saúde: {hp}/{max_hp} HP ---")
    print("---------------------------\n")


# ─── SISTEMA DE DADOS SHADOWDARK ──────────────────────────────────────────────

# Verbos de ação que implicam risco e possível falha interessante.
# Usa stems (prefixos) para cobrir conjugações: "escal" → escalar/escalo/escalando
_ROLL_VERB_PATTERNS = [
    # Persuasão / Engano
    "convenc", "persuad", "mentir", "minto", "enganar", "engano",
    "seduzir", "seduzo", "blefar", "blefando", "disfarç", "negociar",
    "negocio", "intimidar", "intimido", "ameaçar", "ameaço", "chantage",
    # Físico desafiador
    "empurrar", "empurro", "arromb", "forçar a", "forço a",
    "escal", "nadar ", "nado ", "esquivar", "esquivo",
    "escapar de", "lutando", "atacar", "ataco", "golpear", "golpeio",
    "derrubar", "derrub", "arremessar", "arremess", "trepar",
    "saltar sobre", "salto sobre",
    # Furtividade
    "me esconder", "esgueirar", "esgueiro", "infiltrar", "infiltro",
    "roubar", "roubando", "furtar", "furtando",
    # Perícia / Investigação
    "decifrar", "decifrando", "traduzir", "traduzindo",
    "detectar armadilha", "desarmar",
]

# Modificadores que elevam a DC
_DC_HARD_KEYWORDS = [
    "pesado", "reforçado", "trancado", "resistente", "ferrenho",
    "íngreme", "turbulento", "embravecido", "furioso", "formidável",
    "difícil", "suspeito", "alerta", "experiente", "habilidoso",
    "enorme", "colossal",
]
_DC_EXTREME_KEYWORDS = [
    "impossível", "absolutamente", "invencível", "lisa e", "liso e",
    "extremamente", "incrivelmente",
]

# Vantagem e Desvantagem por classe (mesmos stems de _ROLL_VERB_PATTERNS)
_CLASS_ROLL_PROFILE: dict[str, dict[str, list[str]]] = {
    "Bardo": {
        "advantage": [
            "convenc", "persuad", "mentir", "minto", "enganar", "engano",
            "seduz", "blef", "disfarç", "negoci", "tocar", "toco",
            "cantar", "canto", "músic", "melodia", "inspirar", "acalmar",
            "investigar", "investigo", "decifrar", "traduz",
        ],
        "disadvantage": [
            "empurrar", "empurro", "arromb", "escal",
            "lutando", "atacar", "ataco", "golpe", "derrub", "arremess", "trepar",
        ],
    },
    "Aventureiro": {
        "advantage": [
            "empurrar", "empurro", "arromb", "escal",
            "lutando", "atacar", "ataco", "golpe", "derrub", "arremess", "trepar",
            "intimidar", "intimido", "sobreviv", "rastrear", "caçar",
        ],
        "disadvantage": [
            "convenc", "persuad", "mentir", "minto", "enganar", "engano",
            "seduz", "blef", "disfarç", "músic", "tocar", "cantar",
            "decifrar", "traduz", "furtand", "esgueirar",
        ],
    },
}


def resolve_action_roll(action: str, character: dict) -> dict | None:
    """
    Sistema de dados Shadowdark — só rola quando há risco real.
    Retorna None para ações rotineiras (sucesso automático pelo Mestre).
    Retorna dict completo com resultado quando a ação tem risco.
    """
    action_lower = action.lower()

    # Sem rolagem se nenhum verbo de risco detectado
    if not any(p in action_lower for p in _ROLL_VERB_PATTERNS):
        return None

    # Determina DC
    if any(kw in action_lower for kw in _DC_EXTREME_KEYWORDS):
        dc = 18
    elif any(kw in action_lower for kw in _DC_HARD_KEYWORDS):
        dc = 15
    else:
        dc = 12

    # Vantagem / Desvantagem pela classe
    character_class = character.get("class", "Aventureiro")
    profile = _CLASS_ROLL_PROFILE.get(character_class, {})
    if any(kw in action_lower for kw in profile.get("advantage", [])):
        modifier = "advantage"
    elif any(kw in action_lower for kw in profile.get("disadvantage", [])):
        modifier = "disadvantage"
    else:
        modifier = "normal"

    # Rola os dados
    if modifier == "advantage":
        dice = [random.randint(1, 20), random.randint(1, 20)]
        roll = max(dice)
    elif modifier == "disadvantage":
        dice = [random.randint(1, 20), random.randint(1, 20)]
        roll = min(dice)
    else:
        dice = [random.randint(1, 20)]
        roll = dice[0]

    return {
        "roll": roll,
        "dice": dice,
        "dc": dc,
        "modifier": modifier,
        "success": roll >= dc,
        "critical": roll == 20,
        "fumble": roll == 1,
    }

def handle_local_command(player_action: str, character: dict) -> bool:
    action_lower = player_action.lower()

    if any(keyword in action_lower for keyword in ['inventário', 'inventario', 'bolsa', 'itens']):
        print_inventory(character)
        return True

    if any(keyword in action_lower for keyword in ['status', 'saúde', 'vida', 'hp']):
        print_status(character)
        return True

    return False


# ─── AGENTE "OLHOS DO JOGADOR" (HUD Narrativo — 4º agente) ───────────────────

_INSPECTION_PATTERNS = {
    "inventory": [
        "inventário", "inventario", "bolsa", "minha mochila", "minha bolsa",
        "meus itens", "o que eu tenho", "o que carrego", "meu equipamento",
        "que itens", "que items",
    ],
    "health": [
        "status", "saúde", "saude", "minha vida", "meu hp", "quanto hp",
        "quantos hp", "como estou", "meu estado", "como está minha saúde",
        "estou ferido", "minha saúde",
    ],
    "environment": [
        "o que eu vejo", "ao meu redor", "meu redor", "o que tem aqui",
        "onde estou", "que lugar", "o que está aqui", "o que esta aqui",
        "checar o ambiente", "examinar o ambiente", "olhar ao redor",
        "o que há aqui", "o que ha aqui", "o que vejo", "olho ao redor",
        "que tem por aqui", "me olho ao redor", "procuro ao redor",
    ],
}


def is_inspection_action(action: str) -> str | None:
    """
    Detecta se a ação é uma consulta de inspeção (não avança o tempo do jogo).
    Retorna o tipo: 'inventory', 'health', 'environment', ou None.
    """
    action_lower = action.lower().strip()
    for inspect_type, keywords in _INSPECTION_PATTERNS.items():
        if any(kw in action_lower for kw in keywords):
            return inspect_type
    return None


def get_player_eyes_response(player_action: str, world_state: dict) -> str:
    """
    Agente 'Olhos do Jogador' — lê o estado do jogo e responde consultas de
    inspeção de forma imersiva, sem avançar a narrativa.
    Temperatura 0.2 (factual, igual ao Archivista).
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return "Não consigo processar sua consulta no momento."

    pc = world_state.get("player_character", {})
    ws = world_state.get("world_state", {})
    inspect_type = is_inspection_action(player_action)

    if inspect_type == "inventory":
        inv = pc.get("inventory", [])
        context = {
            "inventory": inv,
            "slots_usados": calculate_used_slots(inv),
            "max_slots": pc.get("max_slots", 10),
        }
    elif inspect_type == "health":
        context = {
            "status": pc.get("status", {"hp": 20, "max_hp": 20}),
            "classe": pc.get("class", "Aventureiro"),
        }
    elif inspect_type == "environment":
        context = {
            "local_atual": ws.get("current_location_key", "local desconhecido"),
            "descricao_da_cena": ws.get("immediate_scene_description", ""),
            "cena": ws.get("interactable_elements_in_scene", {}),
            "narrações_recentes": world_state.get("recent_narrations", []),
        }
    else:
        inv = pc.get("inventory", [])
        context = {
            "inventory": inv,
            "slots_usados": calculate_used_slots(inv),
            "max_slots": pc.get("max_slots", 10),
            "status": pc.get("status", {"hp": 20, "max_hp": 20}),
            "local_atual": ws.get("current_location_key", "local desconhecido"),
            "cena": ws.get("interactable_elements_in_scene", {}),
        }

    system_prompt = (
        "Você é a consciência interna e os olhos do personagem — uma voz suave e factual "
        "que traduz dados do jogo em linguagem imersiva. Responda em pt-BR, na segunda pessoa "
        "(você), tempo presente.\n\n"
        "REGRAS ABSOLUTAS:\n"
        "1. Baseie-se EXCLUSIVAMENTE nos dados JSON fornecidos. Nunca invente itens, "
        "locais ou informações ausentes.\n"
        "2. NÃO avance a narrativa, NÃO tome ações, NÃO descreva eventos novos.\n"
        "3. Seja conciso: máximo 2-3 frases curtas.\n"
        "4. Tom: calmo, factual, levemente poético — como uma consciência falando consigo mesma.\n"
        "5. NÃO encerre com 'O que você faz?' — isso é papel do Mestre, não seu."
    )

    user_prompt = (
        f'O personagem perguntou: "{player_action}"\n\n'
        f"Dados do estado (use APENAS estes):\n"
        f"{json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
        "Responda de forma imersiva e estritamente factual."
    )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=200,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def new_game_loop(world_state: dict, save_filepath: str, game_context: dict):
    # Garante que existe o campo rodadas_sem_gatilho
    if "rodadas_sem_gatilho" not in world_state:
        world_state["rodadas_sem_gatilho"] = 0
    
    while True:
        # Usa reconhecimento de voz se disponível, senão input de texto
        if AUDIO_ENABLED:
            player_action = audio_manager.speech_to_text()
        else:
            player_action = input("> ")
        action_lower = player_action.lower()

        if action_lower == 'chikito':
            save_world_state(world_state, save_filepath)
            print("\nJogo salvo. Obrigado por jogar Dragon's Breath!")
            break

        # Comandos locais
        character = world_state.get('player_character', {})
        if handle_local_command(player_action, character):
            world_state['player_character'] = character
            continue

        # Validação contextual de ações (Sistema de Interação Ambiental Dinâmica)
        is_valid, validation_message = validate_player_action(player_action, character, world_state)
        if not is_valid:
            print(f"\n{validation_message}")
            if AUDIO_ENABLED:
                master_speech(validation_message)
                play_chime()
            continue

        # Atualiza contexto com gatilhos do local atual
        current_act = world_state.get('player_character', {}).get('current_act', 1)
        game_context = load_game_context_for_act(current_act, world_state)
        
        # Sistema de gatilhos com chance progressiva
        # Pega local padrão da campanha atual
        campaign = get_current_campaign()
        default_location = campaign.get('world_template', {}).get('initial_location', 'local_inicial')
        
        location_key = world_state["world_state"].get("current_location_key", default_location)
        gatilhos_ativos = world_state["world_state"].get("gatilhos_ativos", {}).get(location_key, [])
        locais_definidos = game_context.get("locais", {})
        gatilhos_definidos = locais_definidos.get(location_key, {}).get("gatilhos", {})
        
        gatilho_escolhido = None
        
        # Cálculo da chance: base + acúmulo por rodadas
        base_chance = 0.3   # 30% fixo
        acumulado = world_state.get("rodadas_sem_gatilho", 0) * 0.1  # +10% por rodada sem evento
        chance_total = min(base_chance + acumulado, 0.9)  # até 90%
        
        # Sorteio
        if gatilhos_ativos and random.random() < chance_total:
            gatilho_id = random.choice(gatilhos_ativos)
            gatilho_escolhido = gatilhos_definidos.get(gatilho_id, {}).get("descricao")
            
            # Marca como usado
            world_state["world_state"]["gatilhos_ativos"][location_key].remove(gatilho_id)
            world_state["world_state"]["gatilhos_usados"].setdefault(location_key, []).append(gatilho_id)
            
            # Ativa o próximo, se houver
            proximo_id = gatilhos_definidos.get(gatilho_id, {}).get("proximo")
            if proximo_id:
                world_state["world_state"]["gatilhos_ativos"][location_key].append(proximo_id)
            
            # Reset contador
            world_state["rodadas_sem_gatilho"] = 0
        else:
            # Não ativou: incrementa
            world_state["rodadas_sem_gatilho"] = world_state.get("rodadas_sem_gatilho", 0) + 1
        
        # Adiciona gatilho à ação do jogador
        action_with_trigger = player_action
        if gatilho_escolhido:
            action_with_trigger = f"{player_action}\n[Gatilho]: {gatilho_escolhido}"
        
        # IA Mestre do Jogo
        gm_response = get_gm_narrative(world_state, action_with_trigger, game_context)
        
        # Processa resposta
        cleaned_response, world_state = clean_and_process_ai_response(gm_response, world_state)

        print(f"\n{cleaned_response}\n")

        # Efeitos sonoros contextuais baseados na narrativa
        trigger_contextual_sfx(cleaned_response)

        # Narração por voz do Mestre (Brian)
        if AUDIO_ENABLED:
            master_speech(cleaned_response)
            # Toca o chime após a narração para indicar que o jogador pode falar
            play_chime()

        # Atualização do estado do mundo com gatilho incluído
        gatilho_para_arquivista = f"(Evento ambiental: {gatilho_escolhido})" if gatilho_escolhido else ""
        world_state = update_world_state(world_state, f"{player_action} {gatilho_para_arquivista}", gm_response)
        
        # Salva estado
        save_world_state(world_state, save_filepath)

def load_game_context_for_act(current_act: int, world_state: dict = None) -> dict:
    npcs_data, items_data, locais_data = load_world_data_for_act(current_act)
    
    # Pega gatilhos do local atual
    gatilhos = []
    if world_state:
        current_location = world_state.get('world_state', {}).get('current_location_key')
        if current_location and current_location in locais_data.get('locais', {}):
            gatilhos_dict = locais_data['locais'][current_location].get('gatilhos', {})
            gatilhos = [g.get('descricao', '') for g in gatilhos_dict.values()]
    
    return {
        'npcs': npcs_data,
        'items': items_data,
        'locais': locais_data.get('locais', {}),
        'gatilhos': gatilhos
    }

def tutorial_introduction():
    """Introdução narrada com tutorial do jogo"""
    # Introdução universal do Ressoar
    if AUDIO_ENABLED:
        audio_manager.play_sfx("logo")  # Som de abertura

    ressoar_intro = """Existe um som que só você pode emitir.

Um timbre único, uma frequência que é só sua.

Bem-vindo a Ressoar.

Este não é um lugar para seguir caminhos, mas para criar ecos.

Cada passo seu deixará uma marca. Cada feito seu será lembrado.

O mundo é todo ouvidos. O que ele vai escutar de você?"""

    print(ressoar_intro)
    if AUDIO_ENABLED:
        narrator_speech(ressoar_intro)  # Usa voz feminina para introdução do Ressoar

    # Pega informações da campanha atual
    campaign = get_current_campaign()
    campaign_name = campaign.get('name', 'Aventura Desconhecida')
    campaign_desc = campaign.get('description', '')

    # Introdução específica da campanha
    campaign_intro = f"""Você tem a história de: {campaign_name}.

{campaign_desc}

Nas brumas sombrias de Umbraton, uma cidade gótica assolada por uma praga misteriosa, você desperta como um bardo em busca da verdade. Sua esposa morreu em circunstâncias estranhas, e sussurros falam de um dragão disfarçado entre os mortais.

Este é um RPG totalmente por voz. Eu, o Mestre, narrarei tudo e você responderá falando suas ações.

Sempre que ouvir um som de sino, significa que o jogo está pronto para ouvir sua ação.

Comandos úteis: diga 'inventário' para seus itens, 'status' para sua saúde, e 'chikito' para salvar e sair.

Agora, me diga seu nome, corajoso bardo."""

    print(campaign_intro)
    if AUDIO_ENABLED:
        master_speech(campaign_intro)  # Usa voz masculina (Brian) para o Mestre

    # Pede o nome usando reconhecimento de voz se disponível
    if AUDIO_ENABLED:
        player_name = audio_manager.speech_to_text()
        while not player_name or len(player_name.strip()) < 2:
            master_speech("Não consegui ouvir seu nome claramente. Pode repetir?")
            player_name = audio_manager.speech_to_text()
        return player_name.strip()
    else:
        # Fallback para entrada de texto se áudio não estiver disponível
        player_name = input("Qual é o seu nome, viajante? > ").strip()
        while not player_name:
            player_name = input("O nome não pode estar em branco. Qual é o seu nome? > ").strip()
        return player_name

def select_rpg_campaign() -> str:
    """
    Apresenta menu de campanhas RPG disponíveis.
    Retorna o ID da campanha escolhida.
    """
    # Carrega campanhas disponíveis do config.json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        campaigns = config.get('campaigns', {})
    except:
        print("❌ Erro ao carregar campanhas. Usando campanha padrão.")
        return "lamento_do_bardo"

    print("\n" + "="*50)
    print("🗡️ HUB DE CAMPANHAS RPG")
    print("="*50)
    print("\nCampanhas disponíveis:")

    campaign_list = []
    for i, (campaign_id, campaign_data) in enumerate(campaigns.items(), 1):
        campaign_list.append(campaign_id)
        name = campaign_data.get('name', campaign_id)
        description = campaign_data.get('description', 'Sem descrição')
        player_class = campaign_data.get('player_template', {}).get('class', 'Aventureiro')

        print(f"\n{i}. {name}")
        print(f"   Classe: {player_class}")
        print(f"   {description}")

    print("\n" + "-"*50)

    while True:
        if AUDIO_ENABLED:
            master_speech(f"Escolha uma campanha de 1 a {len(campaign_list)}.")

        try:
            choice = input(f"Digite sua escolha (1-{len(campaign_list)}): ").strip()
            choice_num = int(choice)

            if 1 <= choice_num <= len(campaign_list):
                selected_campaign = campaign_list[choice_num - 1]
                campaign_name = campaigns[selected_campaign].get('name', selected_campaign)
                print(f"\n🗡️ Campanha '{campaign_name}' selecionada!")

                if AUDIO_ENABLED:
                    master_speech(f"Campanha {campaign_name} selecionada! Preparando sua aventura...")

                return selected_campaign
            else:
                print(f"❌ Escolha inválida. Digite um número de 1 a {len(campaign_list)}.")
        except ValueError:
            print(f"❌ Digite apenas números de 1 a {len(campaign_list)}.")

def iniciar_modo_rpg(existing_world_state: dict = None, save_filepath: str = 'estado_do_mundo.json'):
    """
    Inicia o Modo RPG - mantém todas as funcionalidades existentes.
    """
    if existing_world_state:
        # Continua jogo existente
        world_state = existing_world_state
        current_act = world_state.get('player_character', {}).get('current_act', 1)
        print("--- Continuando sua aventura RPG... ---\n")
    else:
        # Novo jogo RPG
        # Seleciona campanha
        selected_campaign_id = select_rpg_campaign()

        # Atualiza config.json para usar a campanha selecionada
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            config['current_campaign'] = selected_campaign_id
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except:
            print("⚠️ Aviso: Não foi possível salvar a seleção da campanha.")

        # Tutorial narrado com introdução do Ressoar
        player_name = tutorial_introduction()

        # Cria estado inicial com modo RPG
        world_state = create_initial_world_state(player_name)
        world_state['game_mode'] = 'rpg'  # Marca o modo de jogo
        current_act = 1

        campaign = get_current_campaign()
        campaign_name = campaign.get('name', 'sua aventura')
        print(f"\n{player_name}, {campaign_name} começa agora...")

        game_context = load_game_context_for_act(current_act, world_state)
        # Contexto sem gatilhos para cena de abertura (foco na apresentação do cenário)
        contexto_sem_gatilhos = {**game_context, "gatilhos": []}
        opening_scene = get_gm_narrative(world_state, "Iniciou a aventura", contexto_sem_gatilhos)
        cleaned_opening, world_state = clean_and_process_ai_response(opening_scene, world_state)
        print(f"\n{cleaned_opening}\n")

        # Efeitos sonoros contextuais para a cena de abertura
        trigger_contextual_sfx(cleaned_opening)

        # Narração por voz da cena de abertura (Brian - Mestre)
        if AUDIO_ENABLED:
            master_speech(cleaned_opening)
            # Toca o chime após a narração inicial para indicar que o jogador pode começar
            play_chime()

        world_state = update_world_state(world_state, "Iniciou a aventura", opening_scene)

    # Inicia o loop de jogo RPG (mantém toda a funcionalidade existente)
    game_context = load_game_context_for_act(current_act, world_state)
    new_game_loop(world_state, save_filepath, game_context)

def get_story_master_narrative(texto_completo: str, eventos_json: dict, estado_atual: dict) -> str:
    """
    Função especializada para o Mestre do Conto - narra contos interativos.
    """
    try:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return "Erro: API key não encontrada."

        # SYSTEM: persona e missão estáveis do Mestre do Conto
        system_content = """Você é um "Mestre de Contos" — um narrador literário que adapta obras clássicas para experiências interativas.

--- SUA MISSÃO ---
1. Localize o evento_atual no MAPA DA HISTÓRIA fornecido pelo usuário.
2. Narre a cena descrita em `descricao_para_ia` usando o estilo e trechos da OBRA ORIGINAL.
3. Se o evento contiver a palavra "final", narre o desfecho com o texto da Obra Original e encerre a história.
4. Se não for um final, apresente as opções de múltipla escolha (A, B, C) exatamente como definidas no evento.
5. Sua resposta deve conter APENAS a narração e as opções (se houver). Nenhum texto adicional.
6. Use linguagem rica e atmosférica, mantendo o tom e vocabulário da obra original.
7. Separe as opções da narração com uma linha em branco."""

        # USER: dados dinâmicos — a obra, o mapa e o estado atual
        user_content = f"""--- OBRA ORIGINAL (fonte de estilo e vocabulário) ---
{texto_completo}

--- MAPA DA HISTÓRIA ---
{json.dumps(eventos_json, indent=2, ensure_ascii=False)}

--- ESTADO ATUAL ---
{json.dumps(estado_atual, indent=2, ensure_ascii=False)}

Narre o evento: "{estado_atual.get('evento_atual', '')}" """

        model_name = os.environ.get('OPENAI_MODEL_CONTO') or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.75,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Erro na IA do Mestre do Conto: {str(e)}"

def load_interactive_story(story_name: str) -> tuple[str, dict]:
    """
    Carrega um conto interativo (arquivo .txt e _eventos.json).
    Retorna (texto_completo, eventos_json).
    """
    try:
        # Carrega texto completo
        txt_path = f"contos_interativos/{story_name}.txt"
        with open(txt_path, 'r', encoding='utf-8') as f:
            texto_completo = f.read()

        # Carrega eventos
        json_path = f"contos_interativos/{story_name}_eventos.json"
        with open(json_path, 'r', encoding='utf-8') as f:
            eventos_json = json.load(f)

        return texto_completo, eventos_json

    except FileNotFoundError as e:
        print(f"❌ Arquivo não encontrado: {e}")
        return "", {}
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao ler JSON: {e}")
        return "", {}
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return "", {}

def select_interactive_story() -> str:
    """
    Apresenta menu de contos interativos disponíveis.
    Retorna o nome do arquivo (sem extensão) do conto escolhido.
    """
    print("\n" + "="*50)
    print("📖 BIBLIOTECA DE CONTOS INTERATIVOS")
    print("="*50)

    # Lista contos disponíveis (procura por arquivos _eventos.json)
    import glob
    story_files = glob.glob("contos_interativos/*_eventos.json")

    if not story_files:
        print("❌ Nenhum conto interativo encontrado.")
        return ""

    stories = []
    print("\nContos disponíveis:")

    for i, filepath in enumerate(story_files, 1):
        # Extrai nome do arquivo
        story_name = os.path.basename(filepath).replace('_eventos.json', '')
        stories.append(story_name)

        # Tenta carregar informações do conto
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                story_data = json.load(f)

            titulo = story_data.get('titulo', story_name)
            autor = story_data.get('autor', 'Autor desconhecido')

            print(f"\n{i}. {titulo}")
            print(f"   Por: {autor}")
        except:
            print(f"\n{i}. {story_name}")
            print(f"   (Informações não disponíveis)")

    print("\n" + "-"*50)

    while True:
        if AUDIO_ENABLED:
            master_speech(f"Escolha um conto de 1 a {len(stories)}.")

        try:
            choice = input(f"Digite sua escolha (1-{len(stories)}): ").strip()
            choice_num = int(choice)

            if 1 <= choice_num <= len(stories):
                selected_story = stories[choice_num - 1]
                print(f"\n📖 Conto '{selected_story}' selecionado!")

                if AUDIO_ENABLED:
                    master_speech(f"Conto selecionado! Preparando sua história interativa...")

                return selected_story
            else:
                print(f"❌ Escolha inválida. Digite um número de 1 a {len(stories)}.")
        except ValueError:
            print(f"❌ Digite apenas números de 1 a {len(stories)}.")

def iniciar_modo_conto(existing_state: dict = None):
    """
    Inicia o Modo Conto Interativo.
    """
    if existing_state and 'story_state' in existing_state:
        # Continua história existente
        print("--- Continuando sua história interativa... ---\n")
        story_state = existing_state['story_state']
        story_name = story_state['story_name']
        texto_completo, eventos_json = load_interactive_story(story_name)

        if not eventos_json:
            print("❌ Erro ao carregar história salva. Iniciando nova história.")
            iniciar_modo_conto(None)
            return
    else:
        # Nova história
        story_name = select_interactive_story()

        if not story_name:
            print("❌ Nenhum conto disponível. Retornando ao menu principal.")
            return

        texto_completo, eventos_json = load_interactive_story(story_name)

        if not eventos_json:
            print("❌ Erro ao carregar conto. Retornando ao menu principal.")
            return

        # Inicializa estado da história
        story_state = {
            'game_mode': 'conto',
            'story_name': story_name,
            'evento_atual': eventos_json.get('evento_inicial', 'inicio'),
            'variaveis_narrativas': eventos_json.get('variaveis_iniciais', {}),
            'historico_escolhas': []
        }

        # Apresenta título e autor
        titulo = eventos_json.get('titulo', story_name)
        autor = eventos_json.get('autor', 'Autor desconhecido')

        print(f"\n{'='*60}")
        print(f"📖 {titulo}")
        print(f"Por: {autor}")
        print(f"{'='*60}\n")

        if AUDIO_ENABLED:
            # Narração de abertura com voz feminina (Ressoar)
            intro_text = f"Bem-vindo à experiência narrativa: {titulo}, por {autor}. Prepare-se para uma jornada onde suas escolhas moldarão o destino da história."
            master_speech(intro_text)
            play_chime()

    # Loop principal do conto interativo
    interactive_story_loop(story_state, texto_completo, eventos_json)

def interactive_story_loop(story_state: dict, texto_completo: str, eventos_json: dict):
    """
    Loop principal para contos interativos.
    """
    while True:
        evento_atual = story_state['evento_atual']

        # Verifica se chegou ao final
        if evento_atual.startswith('final_') or 'final' in evento_atual:
            # Evento final - apenas narra e termina
            estado_para_ia = {
                'evento_atual': evento_atual,
                'variaveis_narrativas': story_state['variaveis_narrativas']
            }

            final_narrative = get_story_master_narrative(texto_completo, eventos_json, estado_para_ia)
            print(f"\n{final_narrative}\n")

            # Efeitos sonoros contextuais para o final
            trigger_contextual_sfx(final_narrative)

            if AUDIO_ENABLED:
                master_speech(final_narrative)
                # Chime final para indicar conclusão da história
                play_chime()

            # Mostra estatísticas finais
            print("="*50)
            print("📊 ESTATÍSTICAS FINAIS")
            print("="*50)
            for var, valor in story_state['variaveis_narrativas'].items():
                print(f"{var.capitalize()}: {valor}")

            print(f"\nEscolhas feitas: {len(story_state['historico_escolhas'])}")
            print("="*50)

            print("\n🎭 Obrigado por participar desta história interativa!")
            if AUDIO_ENABLED:
                # Cria resumo das estatísticas para TTS
                stats_summary = f"História concluída! Suas estatísticas finais: "
                stats_parts = []
                for var, valor in story_state['variaveis_narrativas'].items():
                    stats_parts.append(f"{var} {valor}")
                stats_summary += ", ".join(stats_parts)
                stats_summary += f". Você fez {len(story_state['historico_escolhas'])} escolhas ao longo da jornada. Obrigado por participar desta experiência narrativa."
                master_speech(stats_summary)

            input("\nPressione Enter para retornar ao menu principal...")
            break

        # Evento normal - narra e apresenta opções
        estado_para_ia = {
            'evento_atual': evento_atual,
            'variaveis_narrativas': story_state['variaveis_narrativas']
        }

        narrative = get_story_master_narrative(texto_completo, eventos_json, estado_para_ia)
        print(f"\n{narrative}\n")

        # Efeitos sonoros contextuais para a narrativa
        trigger_contextual_sfx(narrative)

        if AUDIO_ENABLED:
            master_speech(narrative)
            # Chime para indicar que o jogador pode fazer sua escolha
            play_chime()

        # Pega opções do evento atual
        evento_data = eventos_json['eventos'].get(evento_atual, {})
        opcoes = evento_data.get('opcoes', [])

        if not opcoes:
            print("❌ Erro: Evento sem opções. Encerrando história.")
            break

        # Aguarda escolha do jogador
        while True:
            if AUDIO_ENABLED:
                master_speech("Faça sua escolha.")

            escolha = input("Digite sua escolha (A, B, C, etc.): ").strip().upper()

            # Valida escolha
            opcao_escolhida = None
            for opcao in opcoes:
                if opcao['texto'].startswith(f"({escolha})"):
                    opcao_escolhida = opcao
                    break

            if opcao_escolhida:
                # Aplica efeitos da escolha
                efeitos = opcao_escolhida.get('efeito', {})
                for variavel, mudanca in efeitos.items():
                    if variavel in story_state['variaveis_narrativas']:
                        story_state['variaveis_narrativas'][variavel] += mudanca
                    else:
                        story_state['variaveis_narrativas'][variavel] = mudanca

                # Registra escolha no histórico
                story_state['historico_escolhas'].append({
                    'evento': evento_atual,
                    'escolha': escolha,
                    'texto': opcao_escolhida['texto']
                })

                # Avança para próximo evento
                story_state['evento_atual'] = opcao_escolhida.get('proximo_evento', 'final_erro')

                print(f"\n✅ Escolha {escolha} selecionada.")
                break
            else:
                opcoes_validas = [opcao['texto'][1] for opcao in opcoes]
                print(f"❌ Escolha inválida. Opções disponíveis: {', '.join(opcoes_validas)}")

        # Salva estado (opcional - pode ser implementado depois)
        # save_story_state(story_state)

def select_game_mode() -> str:
    """
    Apresenta ao jogador a escolha entre Modo RPG e Modo Conto Interativo.
    Inclui sequência especial de abertura do Ressoar.
    Retorna 'rpg' ou 'conto'.
    """
    # SEQUÊNCIA ESPECIAL DE ABERTURA
    if AUDIO_ENABLED:
        from audio_manager import play_ressoar_opening_sequence
        play_ressoar_opening_sequence()

    print("\n" + "="*60)
    print("🎮 PLATAFORMA RESSOAR - SELEÇÃO DE MODO")
    print("="*60)
    print("\nEscolha sua experiência narrativa:")
    print("\n1. 🗡️  MODO RPG")
    print("   Viva uma aventura com regras, inventário e liberdade de ação.")
    print("   • Sistema de Interação Ambiental Dinâmica")
    print("   • Inventário com slots limitados")
    print("   • Múltiplas campanhas disponíveis")
    print("   • Progressão de personagem")

    print("\n2. 📖 MODO CONTO INTERATIVO")
    print("   Participe de histórias clássicas com escolhas e finais alternativos.")
    print("   • Narrativas baseadas em obras literárias")
    print("   • Múltiplas escolhas e consequências")
    print("   • Finais alternativos únicos")
    print("   • Variáveis narrativas dinâmicas")

    print("\n" + "-"*60)

    # ÁUDIO ESPECÍFICO PARA SELEÇÃO
    if AUDIO_ENABLED:
        from audio_manager import play_mode_selection_audio
        play_mode_selection_audio()

    while True:
        if AUDIO_ENABLED:
            choice = input("Digite 1 ou 2: ").strip()
        else:
            choice = input("Digite sua escolha (1 ou 2): ").strip()

        if choice == "1":
            print("\n🗡️ Modo RPG selecionado!")
            if AUDIO_ENABLED:
                master_speech("Modo RPG selecionado! Preparando suas aventuras...")
            return "rpg"
        elif choice == "2":
            print("\n📖 Modo Conto Interativo selecionado!")
            if AUDIO_ENABLED:
                master_speech("Modo Conto Interativo selecionado! Preparando suas histórias...")
            return "conto"
        else:
            print("❌ Escolha inválida. Digite 1 para RPG ou 2 para Conto Interativo.")
            if AUDIO_ENABLED:
                master_speech("Escolha inválida. Digite 1 para RPG ou 2 para Conto Interativo.")

def main():
    # Carrega estado existente para verificar se é continuação
    save_filepath = 'estado_do_mundo.json'
    world_state = load_world_state(save_filepath)

    # --- BYPASS: entrada direta no RPG (menu comentado para testes) ---
    if world_state and 'game_mode' in world_state:
        print(f"\n--- Continuando jogo salvo ---")
    iniciar_modo_rpg(world_state if world_state else None, save_filepath)

    # if world_state and 'game_mode' in world_state:
    #     # Jogo existente - continua no modo salvo
    #     game_mode = world_state['game_mode']
    #     print(f"\n--- Continuando no {game_mode.upper()} ---")
    #
    #     if game_mode == 'rpg':
    #         iniciar_modo_rpg(world_state, save_filepath)
    #     elif game_mode == 'conto':
    #         iniciar_modo_conto(world_state)
    # else:
    #     # Novo jogo - seleção de modo
    #     game_mode = select_game_mode()
    #
    #     if game_mode == 'rpg':
    #         iniciar_modo_rpg(None, save_filepath)
    #     elif game_mode == 'conto':
    #         iniciar_modo_conto(None)

if __name__ == "__main__":
    main()