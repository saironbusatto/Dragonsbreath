"""Registro de turnos em JSONL — material para treinar especialistas (Arquivista-patch, classificador).

Uma linha por turno em {TURN_LOG_DIR}/{namespace}.jsonl. Ligado por padrão; TURN_LOG=off desliga.
Nunca derruba o turno: qualquer falha de escrita só vai para o log de erros.
Sem áudio nem imagem.
"""
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_MISSING = "<ausente>"


def is_enabled() -> bool:
    return os.environ.get("TURN_LOG", "on").strip().lower() != "off"


def state_diff(before, after, prefix: str = "") -> dict:
    """Diferença entre dois estados como {"caminho.pontuado": [antes, depois]}."""
    if isinstance(before, dict) and isinstance(after, dict):
        diff = {}
        for key in before.keys() | after.keys():
            path = f"{prefix}.{key}" if prefix else str(key)
            diff.update(state_diff(before.get(key, _MISSING), after.get(key, _MISSING), path))
        return diff
    return {} if before == after else {prefix: [before, after]}


def log_turn(namespace: str, record: dict) -> None:
    if not is_enabled():
        return
    try:
        base = os.environ.get("TURN_LOG_DIR", "turn_logs")
        os.makedirs(base, exist_ok=True)
        line = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), **record}
        with open(os.path.join(base, f"{namespace}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"[TURN_LOG] falha ao gravar turno ({namespace}): {e}")
