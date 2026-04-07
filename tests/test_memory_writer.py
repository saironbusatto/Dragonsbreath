import json
from pathlib import Path

from memory_writer import MemoryWriter, WriteIntent


def _read_journal(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _valid_state() -> dict:
    return {
        "player_character": {
            "status": {"hp": 12, "max_hp": 20}
        },
        "world_state": {
            "current_location_key": "taverna_corvo_ferido",
            "combat_state": {"active": False, "initiative_order": []},
            "scene_npc_signatures": {},
        },
    }


def test_valid_write_two_topic_files_committed(tmp_path):
    memory_dir = tmp_path / "memory"
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    legacy.write_text(json.dumps({"baseline": True}), encoding="utf-8")

    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais={"taverna_corvo_ferido": {}},
        memory_mode="dual_write",
    )

    intents = [
        WriteIntent(file="memory/player.md", content="hp: 12\n", required_fields=["hp:"]),
        WriteIntent(
            file="memory/location.md",
            content="location: taverna_corvo_ferido\n",
            required_fields=["location:"],
        ),
    ]
    entry = writer.plan(intents)
    entry.projected_state = _valid_state()
    entry.index_content = "player: memory/player.md\nlocation: memory/location.md\n"
    entry.legacy_state = {"synced": True}

    result = writer.execute(entry)

    assert result.success is True
    assert result.status == "committed"
    assert (memory_dir / "player.md").exists()
    assert (memory_dir / "location.md").exists()
    assert (memory_dir / "MEMORY.md").exists()

    rows = _read_journal(journal)
    assert any(r["status"] == "committed" for r in rows)


def test_invariant_violation_aborts_and_keeps_legacy_intact(tmp_path):
    memory_dir = tmp_path / "memory"
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    original_legacy = {"old": "state"}
    legacy.write_text(json.dumps(original_legacy), encoding="utf-8")

    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais={"taverna_corvo_ferido": {}},
        memory_mode="dual_write",
    )

    intents = [
        WriteIntent(file="memory/player.md", content="hp: 10\n", required_fields=["hp:"]),
    ]
    entry = writer.plan(intents)
    entry.projected_state = {
        "player_character": {"hp_current": 10},
        "resurrection_state": {"stage": "awaiting_offering"},
        "world_state": {
            "current_location_key": "taverna_corvo_ferido",
            "combat_state": {"active": False, "initiative_order": []},
            "scene_npc_signatures": {},
        },
    }
    entry.legacy_state = {"new": "state"}

    result = writer.execute(entry)
    assert result.success is False
    assert result.status == "aborted"
    assert result.entry.rollback_applied is True
    assert (memory_dir / "player.md").exists() is False
    assert list(memory_dir.glob(".tmp_*")) == []

    current_legacy = json.loads(legacy.read_text(encoding="utf-8"))
    assert current_legacy == original_legacy


def test_failure_during_step_3_aborts_with_rollback(tmp_path, monkeypatch):
    memory_dir = tmp_path / "memory"
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    legacy.write_text(json.dumps({"baseline": True}), encoding="utf-8")

    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais={"taverna_corvo_ferido": {}},
        memory_mode="dual_write",
    )

    intents = [
        WriteIntent(file="memory/player.md", content="hp: 7\n", required_fields=["hp:"]),
    ]
    entry = writer.plan(intents)
    entry.projected_state = _valid_state()

    def _boom(_state):
        raise OSError("disk failure while validating projected state")

    monkeypatch.setattr(writer, "validate_invariants", _boom)
    result = writer.execute(entry)

    assert result.success is False
    assert result.status == "aborted"
    assert result.entry.rollback_applied is True
    assert "disk failure" in (result.entry.error or "")
    assert list(memory_dir.glob(".tmp_*")) == []


def test_duplicate_write_same_turn_keeps_both_entries(tmp_path):
    memory_dir = tmp_path / "memory"
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    legacy.write_text(json.dumps({"baseline": True}), encoding="utf-8")

    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais={"taverna_corvo_ferido": {}},
        memory_mode="dual_write",
    )

    entry1 = writer.plan([WriteIntent(file="memory/player.md", content="hp: 10\n")])
    entry1.turn = 47
    entry1.projected_state = _valid_state()
    result1 = writer.execute(entry1)
    assert result1.success is True

    entry2 = writer.plan([WriteIntent(file="memory/location.md", content="loc: taverna\n")])
    entry2.turn = 47
    entry2.projected_state = _valid_state()
    result2 = writer.execute(entry2)
    assert result2.success is True

    rows = _read_journal(journal)
    committed_turn_47 = [r for r in rows if r.get("status") == "committed" and r.get("turn") == 47]
    assert len(committed_turn_47) == 2


def test_corrupted_journal_uses_last_valid_line_for_next_turn(tmp_path):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    journal = memory_dir / "turn_journal.jsonl"
    journal.write_text(
        "\n".join(
            [
                json.dumps({"turn": 1, "status": "committed"}),
                "{invalid json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=tmp_path / "estado_do_mundo.json",
        campaign_locais={},
        memory_mode="dual_write",
    )

    entry = writer.plan([WriteIntent(file="memory/player.md", content="hp: 5\n")])
    assert entry.turn == 2


def test_create_npc_topic_if_missing_creates_file_and_commits_journal(tmp_path):
    memory_dir = tmp_path / "memory"
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    legacy.write_text(json.dumps({"baseline": True}), encoding="utf-8")
    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais={"taverna_corvo_ferido": {}},
        memory_mode="dual_write",
        session_id="sessao_teste",
    )

    world_state = {
        "world_state": {
            "current_location_key": "taverna_corvo_ferido",
            "combat_state": {"active": False, "initiative_order": []},
            "scene_npc_signatures": {"figura encapuzada": {"referencia_id": "improvisado_figura"}},
        }
    }
    signature = {
        "nome": "Figura Encapuzada",
        "origem": "improvisado",
        "tipo": "npc_improvisado",
        "moral_tonalidade": "ambigua",
        "arquetipo_social": "habitante",
        "motivacao_principal": "Observar o heroi.",
        "voz_textual": "Sussurrante.",
    }

    created = writer.create_npc_topic_if_missing("improvisado_figura", signature, world_state)
    assert created is True

    topic_path = memory_dir / "npcs" / "improvisado_figura.md"
    assert topic_path.exists()
    content = topic_path.read_text(encoding="utf-8")
    assert "id: improvisado_figura" in content
    assert "criado_em: sessao_teste" in content
    assert "ultima_aparicao: sessao_teste" in content

    rows = _read_journal(journal)
    npc_builder_commits = [
        r for r in rows if r.get("agent") == "npc_builder" and r.get("status") == "committed"
    ]
    assert npc_builder_commits


def test_create_npc_topic_if_missing_returns_false_when_exists(tmp_path):
    memory_dir = tmp_path / "memory"
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    legacy.write_text(json.dumps({"baseline": True}), encoding="utf-8")
    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais={},
        memory_mode="dual_write",
    )
    npc_path = memory_dir / "npcs" / "npc_1.md"
    npc_path.parent.mkdir(parents=True, exist_ok=True)
    npc_path.write_text("# NPC: N\nid: npc_1\n", encoding="utf-8")

    before_rows = len(_read_journal(journal))
    created = writer.create_npc_topic_if_missing("npc_1", {"nome": "N"}, {})
    after_rows = len(_read_journal(journal))

    assert created is False
    assert before_rows == after_rows


def test_startup_gc_removes_tmp_and_logs_gc_startup(tmp_path):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    stale_tmp = memory_dir / ".tmp_player.md"
    stale_tmp.write_text("stale", encoding="utf-8")
    journal = memory_dir / "turn_journal.jsonl"

    MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=tmp_path / "estado_do_mundo.json",
        campaign_locais={},
        memory_mode="dual_write",
    )

    assert stale_tmp.exists() is False
    rows = _read_journal(journal)
    gc_rows = [r for r in rows if r.get("agent") == "gc_startup" and r.get("status") == "committed"]
    assert gc_rows


def test_commit_aborts_when_location_does_not_exist(tmp_path, campaign_locais_minimal):
    memory_dir = tmp_path / "memory"
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    legacy.write_text(json.dumps({"baseline": True}), encoding="utf-8")
    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais=campaign_locais_minimal,
        memory_mode="dual_write",
    )

    entry = writer.plan([WriteIntent(file="memory/location.md", content="location: torre_fantasma\n")])
    entry.projected_state = {
        "player_character": {"status": {"hp": 10}},
        "world_state": {
            "current_location_key": "torre_fantasma",
            "combat_state": {"active": False, "initiative_order": []},
            "scene_npc_signatures": {},
        },
    }
    result = writer.execute(entry)

    assert result.success is False
    assert any(v.code == "ghost_location" for v in result.violations)
    assert result.entry.rollback_applied is True


def test_commit_reports_two_violations_and_aborts_once(tmp_path, campaign_locais_minimal):
    memory_dir = tmp_path / "memory"
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    legacy.write_text(json.dumps({"baseline": True}), encoding="utf-8")
    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais=campaign_locais_minimal,
        memory_mode="dual_write",
    )

    entry = writer.plan([WriteIntent(file="memory/location.md", content="location: torre_fantasma\n")])
    entry.projected_state = {
        "player_character": {"status": {"hp": 10}},
        "world_state": {
            "current_location_key": "torre_fantasma",
            "combat_state": {"active": False, "initiative_order": ["aldric"]},
            "scene_npc_signatures": {},
        },
    }
    result = writer.execute(entry)

    assert result.success is False
    codes = {v.code for v in result.violations}
    assert "ghost_location" in codes
    assert "combat_ghost_initiative" in codes
    rows = _read_journal(journal)
    assert len([r for r in rows if r.get("status") == "aborted"]) == 1


def test_rollback_preserves_previous_topic_file_content(tmp_path, campaign_locais_minimal):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    existing_player = memory_dir / "player.md"
    existing_player.write_text("hp: 20\n", encoding="utf-8")
    journal = memory_dir / "turn_journal.jsonl"
    legacy = tmp_path / "estado_do_mundo.json"
    legacy.write_text(json.dumps({"baseline": True}), encoding="utf-8")

    writer = MemoryWriter(
        memory_dir=memory_dir,
        journal_path=journal,
        legacy_path=legacy,
        campaign_locais=campaign_locais_minimal,
        memory_mode="dual_write",
    )

    entry = writer.plan([WriteIntent(file="memory/player.md", content="hp: 5\n", required_fields=["hp:"])])
    entry.projected_state = {
        "player_character": {"hp_current": 5},
        "resurrection_state": {"stage": "awaiting_offering"},
        "world_state": {
            "current_location_key": "umbraton",
            "combat_state": {"active": False, "initiative_order": []},
            "scene_npc_signatures": {},
        },
    }
    result = writer.execute(entry)

    assert result.success is False
    assert result.entry.rollback_applied is True
    assert existing_player.read_text(encoding="utf-8") == "hp: 20\n"
