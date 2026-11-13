"""Catálogo de itens da campanha: todo item tem categoria com campos mecânicos.

O item é definido uma vez (itens_comuns.json / itens_magicos.json); salas (`itens` em
locais.json) e NPCs (`itens` em npcs.json) só apontam para o id. Campanha com
`catalogo_estrito: true` no config.json não carrega se o catálogo estiver inválido;
as outras carregam do jeito que estão (o motor aceita e registra).
"""
from dataclasses import dataclass, field

from campaign_manager import get_current_campaign, load_campaign_data
from gm_tags import _norm

BASE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "luz": ("alcance", "duracao_min", "precisa_fogo", "chance_apagar"),
    "chave": ("abre",),
    "consumivel": ("efeito", "usos"),
    "arma": ("dano", "alcance"),
    "armadura": ("ca",),
    "ferramenta": ("permite",),
    "recipiente": ("capacidade",),
    "tesouro": ("valor_gp",),
    "narrativo": (),
}
DIFFICULTIES = (9, 12, 15, 18)  # fácil, normal, difícil, extrema (Shadowdark)
HIDDEN_FIELDS = ("dificuldade", "local", "pista")


class CatalogError(ValueError):
    """Catálogo inválido numa campanha de catálogo estrito."""


@dataclass(frozen=True)
class Catalog:
    items: dict = field(default_factory=dict)
    locais: dict = field(default_factory=dict)
    npcs: dict = field(default_factory=dict)
    strict: bool = False

    def find(self, name: str) -> str | None:
        """Id do item a partir do id, nome ou apelido (sem acento nem maiúscula)."""
        key = _norm(name)
        for item_id, item in self.items.items():
            names = [item_id, item_id.replace("_", " "), item.get("nome", ""), *item.get("apelidos", [])]
            if key in {_norm(n) for n in names if isinstance(n, str)}:
                return item_id
        return None


def _item_errors(item_id: str, item: dict, categories: dict, flags: set[str]) -> list[str]:
    if not isinstance(item, dict):
        return [f"item {item_id}: definição inválida"]
    errors = [] if item.get("nome") else [f"item {item_id}: falta nome"]
    category = item.get("categoria")
    if category not in categories:
        return errors + [f"item {item_id}: categoria desconhecida ({category})"]
    errors += [f"item {item_id}: categoria {category} exige {name}" for name in categories[category] if name not in item]
    if category == "chave" and "abre" in item and item["abre"] not in flags:
        errors.append(f"item {item_id}: abre a flag {item['abre']}, que não existe na campanha")
    return errors


def _placement_errors(place: str, entry, items: dict) -> list[str]:
    if not isinstance(entry, dict) or entry.get("id") not in items:
        return [f"{place}: item fora do catálogo ({entry.get('id') if isinstance(entry, dict) else entry})"]
    hidden = entry.get("escondido")
    if hidden is None:
        return []
    if not isinstance(hidden, dict):
        return [f"{place}: escondido inválido em {entry['id']}"]
    errors = [f"{place}: item escondido {entry['id']} exige {name}" for name in HIDDEN_FIELDS if not hidden.get(name)]
    if hidden.get("dificuldade") not in DIFFICULTIES:
        errors.append(f"{place}: dificuldade de {entry['id']} deve ser uma de {DIFFICULTIES}")
    return errors


def validate(items: dict, locais: dict, npcs: dict, flags: set[str], extra_categories: dict) -> list[str]:
    """Lista de problemas do catálogo; vazia quando está tudo certo."""
    categories = {**BASE_CATEGORIES, **{name: tuple(fields) for name, fields in (extra_categories or {}).items()}}
    errors = [e for item_id, item in items.items() for e in _item_errors(item_id, item, categories, flags)]
    for key, local in locais.items():
        for entry in (local.get("itens") or []) if isinstance(local, dict) else []:
            errors += _placement_errors(f"local {key}", entry, items)
    for key, npc in npcs.items():
        for item_id in (npc.get("itens") or []) if isinstance(npc, dict) else []:
            if item_id not in items:
                errors.append(f"npc {key}: item fora do catálogo ({item_id})")
    return errors


def load() -> Catalog:
    """Catálogo da campanha da sessão. Estrita + inválida = CatalogError com todos os problemas."""
    campaign = get_current_campaign()
    files = campaign.get("files", {})
    items = {**load_campaign_data(files.get("itens_comuns", "")).get("itens_comuns", {}),
             **load_campaign_data(files.get("itens_magicos", "")).get("itens_magicos", {})}
    locais = load_campaign_data(files.get("locais", "")).get("locais", {})
    npcs_file = load_campaign_data(files.get("npcs", ""))
    npcs = npcs_file.get("npcs", npcs_file)
    strict = bool(campaign.get("catalogo_estrito"))
    if strict:
        flag_groups = campaign.get("world_template", {}).get("initial_flags", {})
        flags = {name for group in flag_groups.values() for name in group}
        errors = validate(items, locais, npcs, flags, campaign.get("categorias", {}))
        if errors:
            raise CatalogError("catálogo inválido:\n- " + "\n- ".join(errors))
    return Catalog(items=items, locais=locais, npcs=npcs, strict=strict)
