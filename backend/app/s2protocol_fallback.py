"""
s2protocol Fallback Parser - patch-resilience fallback for parse_replay.

sc2reader is pinned at 1.8.0 and only recognizes protocol versions it
shipped with; a new SC2 patch can produce replays sc2reader fails to load
at all (an error before even reaching our winner-determination logic).
Blizzard's s2protocol package ships a new protocol module with every game
patch (confirmed 2026-07-03: s2protocol has releases up to build 97425
while sc2reader 1.8.0 predates it), so it can often decode a replay
sc2reader can't yet.

This is a minimal, best-effort decoder: it reads only replay.details (map,
players, teams, race, win/loss) plus the replay header (timestamp,
duration) — not sc2reader's rich event-level parsing (damage timelines,
APM, unit composition are unavailable through this path). It exists purely
so a replay from a too-new patch produces a degraded-but-real match instead
of a hard failure; used only when sc2reader itself fails to load the file.

Field mappings below were validated against a real local replay by
cross-checking s2protocol's raw output against sc2reader's parse of the
same file (see git history for the exploration).
"""

import html
import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional

import mpyq  # type: ignore
from s2protocol import versions  # type: ignore

from .models import GameMode, Race
from .replay_parser import (
    PlayerData,
    ReplayData,
    ReplayParseError,
    calculate_game_fingerprint,
    calculate_replay_hash,
)

logger = logging.getLogger(__name__)

# SC2 simulation runs at ~22.4 game-loops/second at "Faster" speed (the
# default and near-universal custom-game setting). Cross-checked against
# sc2reader's game_length.seconds on the same replay (782s == 17529 loops).
GAME_LOOPS_PER_SECOND = 22.4

_WINDOWS_EPOCH = datetime(1601, 1, 1)

# PlayerControl enum from the replay protocol (stable across versions):
# 0/1 = closed/computer-controlled, 2 = human.
_CONTROL_HUMAN = 2

# m_result enum from replay.details: 0 = Unknown/Tie, 1 = Win, 2 = Loss.
_RESULT_WIN = 1

_CLAN_TAG_PREFIX_RE = re.compile(r"^<[^>]+>\s*")


def _resolve_protocol(target_build: int):
    """
    Find the closest bundled s2protocol module at or before target_build.

    s2protocol only ships specific "checkpoint" build modules, each valid
    for a range of builds up to the next checkpoint — this mirrors how
    s2protocol's own versions.build() is meant to be used for builds
    between checkpoints (there is no built-in nearest-match helper).
    """
    base_path = os.path.dirname(versions.__file__)
    files = versions.list_all(base_path)
    builds = sorted(
        int(m.group(1)) for f in files if (m := re.match(r"protocol(\d+)\.py$", f))
    )
    if not builds:
        raise ReplayParseError("s2protocol has no bundled protocol versions")

    candidates = [b for b in builds if b <= target_build]
    chosen = candidates[-1] if candidates else builds[0]
    if chosen != target_build:
        logger.info(
            f"s2protocol: no exact module for build {target_build}, "
            f"using nearest available build {chosen}"
        )
    return versions.build(chosen)


def _clean_name(raw: Optional[bytes]) -> str:
    """Decode a replay player name: HTML-unescape, `<sp/>` -> space, strip clan tag."""
    if not raw:
        return "Unknown"
    name = html.unescape(raw.decode("utf-8", errors="replace"))
    name = name.replace("<sp/>", " ")
    name = _CLAN_TAG_PREFIX_RE.sub("", name).strip()
    return name or "Unknown"


def _decode_race(raw: Optional[bytes]) -> Race:
    text = (raw or b"").decode("utf-8", errors="replace")
    mapping = {"Terr": Race.TERRAN, "Prot": Race.PROTOSS, "Zerg": Race.ZERG}
    for prefix, race in mapping.items():
        if text.startswith(prefix):
            return race
    return Race.RANDOM


def _determine_game_mode(players_data: List[PlayerData]) -> GameMode:
    """Team-size-based mode detection, mirroring replay_parser.determine_game_mode
    but operating on PlayerData (.team) instead of sc2reader Player objects
    (.team_id)."""
    team_counts: dict = {}
    for p in players_data:
        team_counts[p.team] = team_counts.get(p.team, 0) + 1

    if len(team_counts) != 2:
        return GameMode.TWO_V_TWO if len(players_data) != 2 else GameMode.ONE_V_ONE

    sizes = sorted(team_counts.values(), reverse=True)
    try:
        return GameMode(f"{sizes[0]}v{sizes[1]}")
    except ValueError:
        return GameMode.ONE_V_ONE if sum(sizes) <= 2 else GameMode.TWO_V_TWO


def parse_replay_s2protocol(
    file_path: str, manual_winner_team: Optional[int] = None
) -> ReplayData:
    """
    Fallback parse using Blizzard's s2protocol when sc2reader cannot load
    the replay. Best-effort: recovers map/players/teams/win-loss, not the
    rich per-event metrics sc2reader/UnifiedParser normally extract.
    """
    try:
        archive = mpyq.MPQArchive(file_path)
        contents = archive.header["user_data_header"]["content"]
        header = versions.latest().decode_replay_header(contents)
        base_build = header["m_version"]["m_baseBuild"]
        protocol = _resolve_protocol(base_build)
        details = protocol.decode_replay_details(archive.read_file("replay.details"))
    except Exception as e:
        raise ReplayParseError(f"s2protocol fallback failed to decode replay: {e}")

    raw_players = details.get("m_playerList") or []
    human_players = [p for p in raw_players if p.get("m_control") == _CONTROL_HUMAN]
    if not human_players:
        raise ReplayParseError("s2protocol fallback found no human players")

    players_data: List[PlayerData] = []
    for p in raw_players:
        is_human = p.get("m_control") == _CONTROL_HUMAN
        team = int(p.get("m_teamId", 0)) + 1  # protocol team id is 0-indexed
        if manual_winner_team is not None:
            won = team == manual_winner_team
        else:
            won = p.get("m_result") == _RESULT_WIN
        players_data.append(
            PlayerData(
                name=_clean_name(p.get("m_name")),
                race=_decode_race(p.get("m_race")),
                team=team,
                won=won,
                is_ai=not is_human,
                difficulty=None,
            )
        )

    map_name = (details.get("m_title") or b"Unknown Map").decode(
        "utf-8", errors="replace"
    ) or "Unknown Map"

    time_utc_ticks = details.get("m_timeUTC", 0)
    played_at = _WINDOWS_EPOCH + timedelta(microseconds=time_utc_ticks / 10)

    duration_seconds = int(header.get("m_elapsedGameLoops", 0) / GAME_LOOPS_PER_SECOND)

    player_names = [p.name for p in players_data]
    game_fp = calculate_game_fingerprint(map_name, played_at, player_names)

    logger.info(
        f"s2protocol fallback recovered {os.path.basename(file_path)}: "
        f"{len(players_data)} players, map={map_name}"
    )

    return ReplayData(
        played_at=played_at,
        game_mode=_determine_game_mode(players_data),
        map_name=map_name,
        duration_seconds=duration_seconds,
        players=players_data,
        replay_hash=calculate_replay_hash(file_path),
        game_fingerprint=game_fp,
    )
