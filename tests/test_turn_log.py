"""Registro de turnos (turn_log.py + run_turn)."""
import json
import logging
from pathlib import Path

import turn_log
from test_action_characterization import BASE_STATE, _run_case

NAMESPACE = BASE_STATE["_memory_namespace"]


def _lines(log_dir: str) -> list[dict]:
    path = Path(log_dir) / f"{NAMESPACE}.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_state_diff_reports_changed_added_and_removed_paths():
    before = {"a": 1, "b": {"c": 2, "d": 3}, "gone": True}
    after = {"a": 1, "b": {"c": 5, "d": 3}, "new": [1]}
    assert turn_log.state_diff(before, after) == {
        "b.c": [2, 5], "gone": [True, "<ausente>"], "new": ["<ausente>", [1]],
    }


def test_normal_turn_writes_one_line_with_training_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("TURN_LOG_DIR", str(tmp_path))
    _run_case("normal")
    (line,) = _lines(str(tmp_path))
    assert line["path"] == "normal"
    assert line["action"] == "abro o portão"
    assert line["character"] == {"name": "Aldric", "class": "Bardo"}
    assert line["gm_raw"].endswith("[MOOD:tense]") and not line["narrative"].endswith("[MOOD:tense]")
    assert line["state_before"]["world_state"]["immediate_scene_description"] == "Portões de Umbraton."
    assert line["state_diff"]["world_state.immediate_scene_description"][1].startswith("Após:")
    assert {"gm_ms", "archivist_ms", "tts_ms", "total_ms"} <= set(line["timings_ms"])


def test_every_path_is_logged(monkeypatch, tmp_path):
    monkeypatch.setenv("TURN_LOG_DIR", str(tmp_path))
    for case in ("with_roll", "inspection", "invalid", "resurrection"):
        _run_case(case)
    lines = _lines(str(tmp_path))
    assert [x["path"] for x in lines] == ["normal", "inspection", "invalid", "resurrection"]
    assert lines[0]["roll"]["roll"] == 15


def test_turn_log_off_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setenv("TURN_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("TURN_LOG", "off")
    _run_case("normal")
    assert _lines(str(tmp_path)) == []


def test_write_failure_never_breaks_the_turn(monkeypatch, tmp_path, caplog):
    blocker = tmp_path / "arquivo_no_lugar_do_dir"
    blocker.write_text("x")
    monkeypatch.setenv("TURN_LOG_DIR", str(blocker))
    with caplog.at_level(logging.ERROR, logger="turn_log"):
        result = _run_case("normal")  # _run_case exige status 200
    assert result["response"]["valid"] is True
    assert "[TURN_LOG]" in caplog.text
