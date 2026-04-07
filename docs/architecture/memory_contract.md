# Memory Contract (Layered Architecture)

## Goal
Define ownership, precedence, and conflict resolution for the memory migration from monolithic snapshot (`estado_do_mundo.json`) to layered topic files.

This document is authoritative for Phases 2 to 7.

## Operating Modes

- `legacy`: only `estado_do_mundo.json` is authoritative.
- `dual_write`: topic files and legacy snapshot are both written.
- `layered`: topic files + index are authoritative; legacy snapshot is compatibility output only.

## Precedence Rule (Mandatory)

When `memory_mode != legacy`, topic files win over legacy snapshot.
If a field value differs, the topic value must be applied and the snapshot must be reconciled to it (never the opposite).

## Rollout Configuration

- `MEMORY_MODE` (default: `legacy`)
- `MEMORY_DUAL_WRITE_MIN_SESSIONS` (default: `20`)

`MEMORY_DUAL_WRITE_MIN_SESSIONS` must stay configurable via environment variable so rollout criteria can be tuned without code changes.

## WAL Commit Flow (Text Diagram)

```
plan(writes) [journal: planned]
  -> write tmp files [journal: writing]
  -> validate tmp syntax/required fields
  -> validate invariants (combat, resurrection, location, npc files)
  -> atomic replace tmp -> final topics
  -> update MEMORY.md index
  -> sync legacy snapshot (while memory_mode != layered)
  -> journal committed

if any failure before replace/index/sync:
  -> rollback tmp/restores
  -> journal aborted + rollback_applied=true
```

## Source Of Truth Matrix

| Field / Domain | Source of truth | Primary readers | Allowed writers |
| --- | --- | --- | --- |
| `player_character.status.hp` / `max_hp` | `memory/player.md` | GM prompt, HUD, validations | Archivista patch flow |
| `player_character.inventory` | `memory/player.md` | GM prompt, inventory systems | Archivista patch flow, local command handlers |
| `world_state.current_location_key` | `memory/location.md` + indexed in `memory/MEMORY.md` | GM prompt, scene loader, travel hooks | Archivista patch flow |
| `world_state.interactable_elements_in_scene` | `memory/location.md` | GM prompt, action validator | Archivista patch flow |
| `world_state.active_quests` | `memory/quests.md` | GM prompt, quest logic | Archivista patch flow |
| `world_state.npc_signatures` | `memory/npcs/<id>.md` | GM prompt, NPC resolver | Archivista patch flow, NPC builder |
| `world_state.scene_npc_signatures` | `memory/scene/current_npcs.md` | GM prompt, combat/threat logic | Archivista patch flow, NPC builder |
| `narration_mood` + emotional pacing hints | `memory/mood.md` | GM prompt, audio pacing | Mestre auto tags, Archivista patch flow, KAIROS |
| `world_state.combat_state` | `memory/combat.md` | GM prompt, combat rules | `_update_combat_state` pipeline |
| `resurrection_state` + resurrection metadata | `memory/resurrection.md` | GM prompt, resurrection resolver | `start_resurrection_limbo`, resurrection resolver |
| Session condensed context | `memory/session_reentry.md` | Session bootstrap | KAIROS consolidator |

## Conflict Resolution

When two writers target the same domain in the same turn:

1. Reject direct concurrent writes in the same phase (single-writer commit order).
2. Use WAL (`turn_journal.jsonl`) status progression:
   - `planned -> writing -> validated -> committed|aborted`
3. Record `agent` per journal entry (`Archivista`, `NPC builder`, `KAIROS`, `Combat pipeline`, etc.).
4. On validation failure, abort commit and keep last validated state.

## Minimum Invariants (Phase 4 baseline)

- `combat_active=false` cannot coexist with non-empty initiative order.
- `resurrection_state.stage` set while HP > 0 is invalid.
- `current_location_key` must exist in active campaign locations.
- Every NPC listed in `scene_npc_signatures` must have a corresponding `memory/npcs/<id>.md`.

## Dual-Write Exit Criterion

`memory_mode` must remain `dual_write` until:

1. `dual_write_clean_sessions >= MEMORY_DUAL_WRITE_MIN_SESSIONS`
2. `last_divergence_at == null` for the rolling window
3. `dual_write_threshold_reached == true`

When the criterion is reached, the system only marks:

- `promotion_recommended: true`
- `promotion_requires_manual_confirmation: true`

No automatic switch to `layered` on first achievement.

## Manual Bootstrap Operation

Run one-time bootstrap when `memory/` does not exist and legacy save exists:

1. Execute `bootstrap_memory(...)` from `memory_bootstrap.py`
2. It creates topic files via WAL (`agent: bootstrap`)
3. It writes `memory/MEMORY.md`
4. It updates `memory_migration_baseline.json` with:
   - `memory_mode: dual_write`
   - `bootstrap_at`
   - `bootstrap_session`
5. On invariant failure it aborts and keeps `memory/` absent/clean
