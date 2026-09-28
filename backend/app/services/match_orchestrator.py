"""
Ingest a replay file from a script (batch upload, external folders, ghost-match
restore) through the same parser, winner rule and save path as a web upload.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.advanced_parser import parse_replay_advanced
from app.models import Match
from app.services import replay_storage
from app.services.ingestion import ingest_match, post_process_match, save_advanced_metrics


@dataclass
class MatchOrchestrationResult:
    match: Match
    num_players: int
    message: str
    created: bool = True


class MatchOrchestrator:
    def __init__(self, db: Session):
        self.db = db

    def parse(self, file_path: str, manual_winner_team: Optional[int] = None):
        return parse_replay_advanced(file_path, manual_winner_team=manual_winner_team)

    def orchestrate_match(
        self,
        file_path: str,
        filename: str,
        manual_winner_team: Optional[int] = None,
        persist_replay: bool = False,
    ) -> MatchOrchestrationResult:
        advanced = self.parse(file_path, manual_winner_team)
        replay_data = advanced.basic_data
        stored_path = None
        if persist_replay:
            with open(file_path, "rb") as replay_file:
                stored_path = replay_storage.save_replay(replay_file.read(), replay_data.replay_hash)
        match, created = ingest_match(
            self.db, replay_data, stored_path,
            save_metrics=lambda work, recorded: save_advanced_metrics(work, recorded, advanced),
            require_experience=False,
        )
        if created:
            self._trigger_post_processing(match, file_path)
        return MatchOrchestrationResult(
            match=match, num_players=len(replay_data.players),
            message=f"Match {match.id} from {filename} ingested", created=created,
        )

    def _trigger_post_processing(self, match: Match, replay_path: str) -> None:
        post_process_match(self.db, int(match.id), True, replay_path)
