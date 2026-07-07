"""
CommandCenter Parser - High-fidelity replay parsing using PyCommandCenter.

This module provides accurate economic and damage statistics by running replays
through the actual StarCraft II engine via the SC2 API.

Requirements:
- StarCraft II installed (Linux headless or Windows)
- PyCommandCenter library compiled and available in backend/app/lib/

Supports:
- Linux: ~/StarCraftII with headless SC2_x64
- Windows: Standard SC2 installation paths
- All game modes: 1v1, 2v2, 3v3, 4v4, 5v5 (up to 10 players)
"""

import glob
import os
import platform
import subprocess
import sys
import time
import logging
import urllib.request
import zipfile
import shutil
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Type, cast

# Add the lib directory to path
LIB_PATH = "/home/vtee/projects/sc2mmr/backend/app/lib"
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

logger = logging.getLogger(__name__)

# Try to import PyCommandCenter
HAS_CC = False
_Coordinator: Any = None
_IDAReplayObserver: Any = None
_Race: Any = None
_GameResult: Any = None

try:
    from library import Coordinator as _Coordinator  # type: ignore
    from library import IDAReplayObserver as _IDAReplayObserver  # type: ignore
    from library import Race as _Race, GameResult as _GameResult  # type: ignore

    HAS_CC = True
except ImportError as e:
    logger.warning(
        f"PyCommandCenter library not found: {e}. CommandCenterParser will be unavailable."
    )

from app.types.results import PlayerMatchResult
from app.config import settings


# SC2 Linux headless download URL (Blizzard's official Linux build)
SC2_LINUX_DOWNLOAD_URL = "https://blzdistsc2-a.akamaihd.net/Linux/SC2.4.10.zip"
SC2_DEFAULT_INSTALL_PATH = os.path.expanduser("~/StarCraftII")


@dataclass
class PlayerMetrics:
    """Comprehensive metrics for a single player from SC2 API."""

    # Final score
    total_score: float = 0.0

    # Economic metrics
    collected_minerals: int = 0
    collected_vespene: int = 0
    spent_minerals: int = 0
    spent_vespene: int = 0
    collection_rate_minerals: float = 0.0  # Final income rate
    collection_rate_vespene: float = 0.0

    # Idle time (efficiency)
    idle_production_time: int = 0
    idle_worker_time: int = 0

    # Army value
    total_value_units: int = 0
    total_value_structures: int = 0
    killed_value_units: int = 0
    killed_value_structures: int = 0

    # Damage stats (actual HP damage, not cost-based)
    damage_dealt_life: float = 0.0
    damage_dealt_shields: float = 0.0
    damage_taken_life: float = 0.0
    damage_taken_shields: float = 0.0

    # Killed resources breakdown
    killed_minerals_army: int = 0
    killed_minerals_economy: int = 0
    killed_vespene_army: int = 0
    killed_vespene_economy: int = 0

    # Per-second economic tracking (game_second -> rate)
    income_timeline: Dict[int, Dict[str, float]] = field(default_factory=dict)

    @property
    def total_damage_dealt(self) -> float:
        """Total damage dealt (life + shields)."""
        return self.damage_dealt_life + self.damage_dealt_shields

    @property
    def total_damage_taken(self) -> float:
        """Total damage taken (life + shields)."""
        return self.damage_taken_life + self.damage_taken_shields

    @property
    def total_collected(self) -> int:
        """Total resources collected."""
        return self.collected_minerals + self.collected_vespene

    @property
    def total_spent(self) -> int:
        """Total resources spent."""
        return self.spent_minerals + self.spent_vespene

    @property
    def total_killed_value(self) -> int:
        """Total value of units and structures killed."""
        return self.killed_value_units + self.killed_value_structures

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        return {
            "total": self.total_score,
            "collected_minerals": self.collected_minerals,
            "collected_vespene": self.collected_vespene,
            "spent_minerals": self.spent_minerals,
            "spent_vespene": self.spent_vespene,
            "collection_rate_minerals": self.collection_rate_minerals,
            "collection_rate_vespene": self.collection_rate_vespene,
            "idle_production_time": self.idle_production_time,
            "idle_worker_time": self.idle_worker_time,
            "total_value_units": self.total_value_units,
            "total_value_structures": self.total_value_structures,
            "killed_value_units": self.killed_value_units,
            "killed_value_structures": self.killed_value_structures,
            "total_damage_dealt_life": self.damage_dealt_life,
            "total_damage_dealt_shields": self.damage_dealt_shields,
            "total_damage_taken_life": self.damage_taken_life,
            "total_damage_taken_shields": self.damage_taken_shields,
            "killed_minerals_army": self.killed_minerals_army,
            "killed_minerals_economy": self.killed_minerals_economy,
            "killed_vespene_army": self.killed_vespene_army,
            "killed_vespene_economy": self.killed_vespene_economy,
            # Computed values
            "total_damage_dealt": self.total_damage_dealt,
            "total_damage_taken": self.total_damage_taken,
            "total_collected": self.total_collected,
            "total_spent": self.total_spent,
            "total_killed_value": self.total_killed_value,
            # Timeline data
            "income_timeline": self.income_timeline,
        }


# Game runs at ~22.4 frames per second at "Faster" speed
FRAMES_PER_SECOND = 22.4
# Sample income rates every N game seconds
INCOME_SAMPLE_INTERVAL = 30
# Maximum supported players (5v5)
MAX_PLAYERS = 10


def _get_metrics_collector_class() -> Optional[Type]:
    """
    Get the MetricsCollector class if PyCommandCenter is available.

    Returns the class type, not an instance.
    """
    if not HAS_CC or _IDAReplayObserver is None:
        return None

    class MetricsCollector(_IDAReplayObserver):  # type: ignore[misc]
        """
        Collects detailed metrics from replay observation.

        Supports all game modes from 1v1 through 5v5 (up to 10 players).
        Tracks economic metrics over time for income rate analysis.
        """

        def __init__(self, num_players: int = 2):
            super().__init__()
            if num_players < 1 or num_players > MAX_PLAYERS:
                raise ValueError(f"num_players must be between 1 and {MAX_PLAYERS}")
            self.num_players = num_players
            self.results: Dict[int, PlayerMetrics] = {}
            self.game_ended = False
            self._current_frame = 0
            self._last_sample_second = 0
            # Track per-player metrics during game
            self._frame_metrics: Dict[int, List[Dict[str, Any]]] = {
                pid: [] for pid in range(1, num_players + 1)
            }

        def on_game_start(self) -> None:
            """Called when replay observation begins."""
            logger.info(
                f"Replay observation started (tracking {self.num_players} players)"
            )
            self._current_frame = 0
            self._last_sample_second = 0

        def on_step(self) -> None:
            """
            Called every game frame during replay observation.

            We sample economic data periodically to track income over time.
            """
            self._current_frame += 1
            current_second = int(self._current_frame / FRAMES_PER_SECOND)

            # Sample income rates periodically
            if current_second >= self._last_sample_second + INCOME_SAMPLE_INTERVAL:
                self._last_sample_second = current_second
                self._sample_income_rates(current_second)

        def _sample_income_rates(self, game_second: int) -> None:
            """Sample current income rates for all players."""
            try:
                for pid in range(1, self.num_players + 1):
                    self.set_replay_perspective(pid)
                    score = self.get_score()

                    if pid not in self._frame_metrics:
                        self._frame_metrics[pid] = []

                    self._frame_metrics[pid].append(
                        {
                            "second": game_second,
                            "collection_rate_minerals": score.get(
                                "collection_rate_minerals", 0
                            ),
                            "collection_rate_vespene": score.get(
                                "collection_rate_vespene", 0
                            ),
                            "collected_minerals": score.get("collected_minerals", 0),
                            "collected_vespene": score.get("collected_vespene", 0),
                        }
                    )
            except Exception as e:
                logger.debug(f"Error sampling income rates at {game_second}s: {e}")

        def on_game_end(self) -> None:
            """
            Called when replay observation ends.

            Collects final scores for all players from their perspectives.
            """
            logger.info("Replay observation ended - collecting final metrics")
            self.game_ended = True

            try:
                for pid in range(1, self.num_players + 1):
                    self.set_replay_perspective(pid)
                    score = self.get_score()

                    metrics = PlayerMetrics(
                        total_score=score.get("total", 0),
                        collected_minerals=int(score.get("collected_minerals", 0)),
                        collected_vespene=int(score.get("collected_vespene", 0)),
                        spent_minerals=int(score.get("spent_minerals", 0)),
                        spent_vespene=int(score.get("spent_vespene", 0)),
                        collection_rate_minerals=score.get(
                            "collection_rate_minerals", 0
                        ),
                        collection_rate_vespene=score.get("collection_rate_vespene", 0),
                        idle_production_time=int(score.get("idle_production_time", 0)),
                        idle_worker_time=int(score.get("idle_worker_time", 0)),
                        total_value_units=int(score.get("total_value_units", 0)),
                        total_value_structures=int(
                            score.get("total_value_structures", 0)
                        ),
                        killed_value_units=int(score.get("killed_value_units", 0)),
                        killed_value_structures=int(
                            score.get("killed_value_structures", 0)
                        ),
                        damage_dealt_life=score.get("total_damage_dealt_life", 0),
                        damage_dealt_shields=score.get("total_damage_dealt_shields", 0),
                        damage_taken_life=score.get("total_damage_taken_life", 0),
                        damage_taken_shields=score.get("total_damage_taken_shields", 0),
                        killed_minerals_army=int(score.get("killed_minerals_army", 0)),
                        killed_minerals_economy=int(
                            score.get("killed_minerals_economy", 0)
                        ),
                        killed_vespene_army=int(score.get("killed_vespene_army", 0)),
                        killed_vespene_economy=int(
                            score.get("killed_vespene_economy", 0)
                        ),
                    )

                    # Build income timeline from sampled data
                    for sample in self._frame_metrics.get(pid, []):
                        metrics.income_timeline[sample["second"]] = {
                            "minerals_rate": sample["collection_rate_minerals"],
                            "vespene_rate": sample["collection_rate_vespene"],
                            "minerals_total": sample["collected_minerals"],
                            "vespene_total": sample["collected_vespene"],
                        }

                    self.results[pid] = metrics
                    logger.info(
                        f"Player {pid}: minerals={metrics.collected_minerals}, "
                        f"vespene={metrics.collected_vespene}, "
                        f"damage_dealt={metrics.total_damage_dealt:.0f}, "
                        f"damage_taken={metrics.total_damage_taken:.0f}"
                    )

            except Exception as e:
                logger.error(f"Error collecting final scores: {e}", exc_info=True)

    return MetricsCollector


def find_sc2_installation() -> Optional[str]:
    """
    Auto-detect StarCraft II installation path.

    Searches common installation locations for both Linux and Windows.
    On WSL, also checks Windows paths via /mnt/c and /mnt/d.

    Returns:
        Path to SC2 installation directory, or None if not found.
    """
    system = platform.system()
    running_wsl = is_wsl()

    candidates = []

    if system == "Linux":
        # Linux paths (headless SC2 or Wine)
        candidates = [
            os.path.expanduser("~/StarCraftII"),
            "/opt/StarCraftII",
        ]

        # On WSL, also check Windows paths
        if running_wsl:
            candidates.extend(
                [
                    "/mnt/c/Program Files (x86)/StarCraft II",
                    "/mnt/c/Program Files/StarCraft II",
                    "/mnt/d/Program Files (x86)/StarCraft II",
                    "/mnt/d/Program Files/StarCraft II",
                    "/mnt/c/Games/StarCraft II",
                    "/mnt/d/Games/StarCraft II",
                ]
            )

        # Wine paths
        candidates.extend(
            [
                os.path.expanduser("~/.wine/drive_c/Program Files (x86)/StarCraft II"),
                os.path.expanduser("~/.wine/drive_c/Program Files/StarCraft II"),
            ]
        )
    elif system == "Windows":
        # Windows paths
        candidates = [
            "C:\\Program Files (x86)\\StarCraft II",
            "C:\\Program Files\\StarCraft II",
            os.path.expanduser("~\\StarCraft II"),
        ]
    else:
        # macOS or other
        candidates = [
            "/Applications/StarCraft II",
            os.path.expanduser("~/Applications/StarCraft II"),
        ]

    for path in candidates:
        if os.path.isdir(path):
            # Verify it has the Versions directory
            versions_path = os.path.join(path, "Versions")
            if os.path.isdir(versions_path):
                logger.info(f"Found SC2 installation at: {path}")
                return path

    return None


def is_wsl() -> bool:
    """Check if running under Windows Subsystem for Linux."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except:
        return False


def wsl_to_windows_path(wsl_path: str) -> str:
    r"""
    Convert a WSL path (e.g., /mnt/c/...) to a Windows path (e.g., C:\...).

    Args:
        wsl_path: Path in WSL format.

    Returns:
        Path in Windows format.
    """
    if not wsl_path.startswith("/mnt/"):
        return wsl_path

    # /mnt/c/foo/bar -> C:\foo\bar
    parts = wsl_path.split("/")
    if len(parts) < 3:
        return wsl_path

    drive = parts[2].upper()
    rest = "\\".join(parts[3:])
    return f"{drive}:\\{rest}"


def find_sc2_executable(sc2_path: str) -> Optional[str]:
    """
    Find the SC2 executable for the latest installed version.

    Args:
        sc2_path: Path to SC2 installation directory.

    Returns:
        Path to SC2 executable, or None if not found.
    """
    versions_path = os.path.join(sc2_path, "Versions")
    if not os.path.isdir(versions_path):
        return None

    system = platform.system()
    running_wsl = is_wsl()

    # Find all Base* directories (e.g., Base75689, Base92440)
    base_dirs = glob.glob(os.path.join(versions_path, "Base*"))
    if not base_dirs:
        return None

    # Sort to get highest version (latest)
    base_dirs.sort(reverse=True)

    for base_dir in base_dirs:
        # On WSL, prefer Windows .exe files (can run via WSL interop)
        if running_wsl:
            exe_candidates = [
                os.path.join(base_dir, "SC2_x64.exe"),
                os.path.join(base_dir, "SC2.exe"),
                os.path.join(base_dir, "SC2_x64"),
            ]
        elif system == "Linux":
            exe_candidates = [
                os.path.join(base_dir, "SC2_x64"),
                os.path.join(
                    base_dir, "SC2_x64.exe"
                ),  # Fallback for mounted Windows drives
            ]
        elif system == "Windows":
            exe_candidates = [
                os.path.join(base_dir, "SC2_x64.exe"),
                os.path.join(base_dir, "SC2.exe"),
            ]
        else:
            exe_candidates = [
                os.path.join(base_dir, "SC2.app", "Contents", "MacOS", "SC2"),
            ]

        for exe_path in exe_candidates:
            if os.path.isfile(exe_path):
                logger.info(f"Found SC2 executable: {exe_path}")
                return exe_path

    return None


def verify_sc2_executable(exe_path: str) -> bool:
    """
    Verify that the SC2 executable is valid and can run.

    Args:
        exe_path: Path to SC2 executable.

    Returns:
        True if executable is valid, False otherwise.
    """
    if not os.path.isfile(exe_path):
        return False

    # For Windows executables on WSL, we can't check executable bit
    is_windows_exe = exe_path.endswith(".exe")

    if not is_windows_exe:
        # Check if file is executable (only for native Linux binaries)
        if not os.access(exe_path, os.X_OK):
            logger.warning(f"SC2 executable not executable: {exe_path}")
            try:
                os.chmod(exe_path, 0o755)
                logger.info(f"Made SC2 executable: {exe_path}")
            except Exception as e:
                logger.error(f"Failed to make executable: {e}")
                return False

    # Check file size as a sanity check
    file_size = os.path.getsize(exe_path)
    if file_size < 1000000:  # Less than 1MB is suspicious
        logger.warning(f"SC2 executable seems too small: {file_size} bytes")
        return False

    return True


def download_sc2_linux(install_path: Optional[str] = None) -> str:
    """
    Download and install StarCraft II Linux headless build.

    Args:
        install_path: Where to install SC2. Defaults to ~/StarCraftII.

    Returns:
        Path to installed SC2 directory.

    Raises:
        RuntimeError: If download or installation fails.
    """
    if install_path is None:
        install_path = SC2_DEFAULT_INSTALL_PATH

    logger.info(f"Downloading StarCraft II Linux build to {install_path}...")

    # Create temp directory for download
    temp_dir = os.path.join(os.path.dirname(install_path), ".sc2_download_temp")
    os.makedirs(temp_dir, exist_ok=True)
    zip_path = os.path.join(temp_dir, "SC2.zip")

    try:
        # Download the zip file
        logger.info(f"Downloading from {SC2_LINUX_DOWNLOAD_URL}...")

        def _report_progress(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0:
                percent = min(100, block_num * block_size * 100 // total_size)
                if block_num % 100 == 0:  # Log every 100 blocks
                    logger.info(f"Download progress: {percent}%")

        urllib.request.urlretrieve(SC2_LINUX_DOWNLOAD_URL, zip_path, _report_progress)
        logger.info("Download complete. Extracting...")

        # Extract the zip file
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(os.path.dirname(install_path))

        logger.info(f"Extraction complete. SC2 installed at {install_path}")

        # Make executable
        exe_path = find_sc2_executable(install_path)
        if exe_path:
            os.chmod(exe_path, 0o755)
            logger.info(f"Made executable: {exe_path}")

        return install_path

    except Exception as e:
        logger.error(f"Failed to download/install SC2: {e}")
        raise RuntimeError(f"Failed to download StarCraft II: {e}")
    finally:
        # Cleanup temp files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def ensure_sc2_installed(auto_download: bool = True) -> str:
    """
    Ensure StarCraft II is installed and return the path.

    Args:
        auto_download: If True, automatically download SC2 if not found (Linux only).

    Returns:
        Path to SC2 installation.

    Raises:
        RuntimeError: If SC2 is not installed and cannot be downloaded.
    """
    # First, try to find existing installation
    sc2_path = find_sc2_installation()

    if sc2_path:
        exe_path = find_sc2_executable(sc2_path)
        if exe_path and verify_sc2_executable(exe_path):
            logger.info(f"Using existing SC2 installation: {sc2_path}")
            return sc2_path
        else:
            logger.warning(f"SC2 installation at {sc2_path} appears invalid")

    # No valid installation found
    if platform.system() != "Linux":
        raise RuntimeError(
            "StarCraft II not found. Please install StarCraft II manually."
        )

    if not auto_download:
        raise RuntimeError(
            "StarCraft II not found. Set auto_download=True to download automatically."
        )

    # Download SC2 for Linux
    logger.info("SC2 not found. Downloading Linux headless build...")
    return download_sc2_linux()


class CommandCenterParser:
    """
    High-fidelity replay parser using PyCommandCenter and the SC2 API.

    This parser runs replays through the actual SC2 engine to extract
    accurate economic and combat statistics that aren't available from
    replay file parsing alone.

    Features:
    - Accurate damage dealt/taken (actual HP, not cost-based estimates)
    - Real income rates (minerals/vespene per minute)
    - Idle production and worker time
    - Support for all game modes: 1v1, 2v2, 3v3, 4v4, 5v5
    """

    def __init__(
        self,
        sc2_path: Optional[str] = None,
        exe_path: Optional[str] = None,
        auto_download: bool = True,
    ):
        """
        Initialize the CommandCenter parser.

        Args:
            sc2_path: Path to SC2 installation. Auto-detected if not provided.
            exe_path: Path to SC2 executable. Auto-detected if not provided.
            auto_download: If True, download SC2 automatically if not found (Linux only).
        """
        if not HAS_CC:
            raise RuntimeError(
                "PyCommandCenter not installed. "
                "Ensure library.so is in backend/app/lib/"
            )

        # Find or download SC2 installation
        if sc2_path:
            self.sc2_path = sc2_path
        else:
            self.sc2_path = ensure_sc2_installed(auto_download=auto_download)

        # Find executable (using WSL path for file checks)
        if exe_path:
            self.exe_path = exe_path
        else:
            self.exe_path = find_sc2_executable(self.sc2_path)
            if not self.exe_path:
                raise RuntimeError(
                    f"SC2 executable not found in {self.sc2_path}. "
                    "Please verify your SC2 installation."
                )

        # Verify executable works
        if not verify_sc2_executable(self.exe_path):
            raise RuntimeError(
                f"SC2 executable at {self.exe_path} appears to be invalid. "
                "Try deleting the installation and letting it re-download."
            )

        # On WSL with Windows SC2 installation, convert paths to Windows format
        # But prefer native Linux SC2 if available (doesn't start with /mnt/)
        if is_wsl() and self.sc2_path.startswith("/mnt/"):
            self.sc2_path_for_sc2 = wsl_to_windows_path(self.sc2_path)
            self.exe_path_for_sc2 = wsl_to_windows_path(self.exe_path)
            logger.info(f"WSL detected with Windows SC2, using Windows paths:")
            logger.info(f"  SC2PATH: {self.sc2_path_for_sc2}")
            logger.info(f"  Executable: {self.exe_path_for_sc2}")
        else:
            # Native Linux SC2 or regular Windows
            self.sc2_path_for_sc2 = self.sc2_path
            self.exe_path_for_sc2 = self.exe_path

        # Set environment variable for SC2 API
        os.environ["SC2PATH"] = self.sc2_path_for_sc2

        # Get the MetricsCollector class
        metrics_collector_class = _get_metrics_collector_class()
        if metrics_collector_class is None:
            raise RuntimeError("Failed to create MetricsCollector class")
        self._MetricsCollector: Type = metrics_collector_class

        logger.info(f"CommandCenterParser initialized with SC2 at: {self.exe_path}")

    def test_sc2_connection(self) -> bool:
        """
        Test that SC2 can be launched and responds correctly.

        Returns:
            True if SC2 is working, False otherwise.
        """
        try:
            # Create a minimal coordinator and see if it initializes
            coordinator = _Coordinator(self.exe_path_for_sc2)
            # Just creating the coordinator is enough to test
            logger.info("SC2 connection test passed")
            return True
        except Exception as e:
            logger.error(f"SC2 connection test failed: {e}")
            return False

    def parse_replay(
        self,
        replay_path: str,
        num_players: int = 2,
        timeout: int = 300,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Parse a replay and return high-fidelity metrics for all players.

        Args:
            replay_path: Path to the .SC2Replay file.
            num_players: Number of players in the game (2 for 1v1, 4 for 2v2,
                         6 for 3v3, 8 for 4v4, 10 for 5v5).
            timeout: Maximum seconds to spend parsing (default 5 minutes).

        Returns:
            Dictionary mapping player_id (1-indexed) to their metrics dict.
        """
        if not os.path.isfile(replay_path):
            raise FileNotFoundError(f"Replay not found: {replay_path}")

        # On WSL, convert replay path to Windows format if it's on a Windows drive
        replay_path_for_sc2 = replay_path
        if is_wsl():
            if replay_path.startswith("/mnt/"):
                replay_path_for_sc2 = wsl_to_windows_path(replay_path)
            else:
                # For files in WSL filesystem, use \\wsl$\ UNC path
                import socket

                distro = (
                    os.popen("wsl.exe -l -q 2>/dev/null | head -1").read().strip()
                    or "Ubuntu"
                )
                replay_path_for_sc2 = f"\\\\wsl$\\{distro}{replay_path}"

        coordinator = _Coordinator(self.exe_path_for_sc2)  # type: ignore[misc]
        MetricsCollectorCls = cast(Type, self._MetricsCollector)
        collector = MetricsCollectorCls(num_players=num_players)

        coordinator.add_replay_observer(collector)
        coordinator.load_replay_list(replay_path_for_sc2)

        # Run at maximum speed (not real-time)
        coordinator.set_real_time(False)

        logger.info(
            f"Starting CommandCenter parsing for: {os.path.basename(replay_path)} "
            f"({num_players} players)"
        )
        start_time = time.time()

        try:
            while coordinator.update():
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.warning(
                        f"Parsing timed out after {timeout}s for {replay_path}"
                    )
                    break
                if collector.game_ended:
                    break
        except Exception as e:
            logger.error(f"Error during replay parsing: {e}", exc_info=True)
            raise

        elapsed = time.time() - start_time
        logger.info(f"CommandCenter parsing completed in {elapsed:.2f}s")

        # Convert PlayerMetrics to dict for compatibility
        return {pid: metrics.to_dict() for pid, metrics in collector.results.items()}

    def parse_replay_detailed(
        self,
        replay_path: str,
        num_players: int = 2,
        timeout: int = 300,
    ) -> Dict[int, PlayerMetrics]:
        """
        Parse a replay and return detailed PlayerMetrics objects.

        This is the preferred method for new code that wants full access
        to the structured metrics data.

        Args:
            replay_path: Path to the .SC2Replay file.
            num_players: Number of players in the game.
            timeout: Maximum seconds to spend parsing.

        Returns:
            Dictionary mapping player_id to PlayerMetrics dataclass.
        """
        if not os.path.isfile(replay_path):
            raise FileNotFoundError(f"Replay not found: {replay_path}")

        # On WSL, convert replay path to Windows format
        replay_path_for_sc2 = replay_path
        if is_wsl():
            if replay_path.startswith("/mnt/"):
                replay_path_for_sc2 = wsl_to_windows_path(replay_path)
            else:
                distro = (
                    os.popen("wsl.exe -l -q 2>/dev/null | head -1").read().strip()
                    or "Ubuntu"
                )
                replay_path_for_sc2 = f"\\\\wsl$\\{distro}{replay_path}"

        coordinator = _Coordinator(self.exe_path_for_sc2)  # type: ignore[misc]
        MetricsCollectorCls = cast(Type, self._MetricsCollector)
        collector = MetricsCollectorCls(num_players=num_players)

        coordinator.add_replay_observer(collector)
        coordinator.load_replay_list(replay_path_for_sc2)
        coordinator.set_real_time(False)

        logger.info(
            f"Starting detailed CommandCenter parsing: {os.path.basename(replay_path)}"
        )
        start_time = time.time()

        try:
            while coordinator.update():
                if time.time() - start_time > timeout:
                    logger.warning(f"Parsing timed out for {replay_path}")
                    break
                if collector.game_ended:
                    break
        except Exception as e:
            logger.error(f"Error during replay parsing: {e}", exc_info=True)
            raise

        logger.info(f"Detailed parsing completed in {time.time() - start_time:.2f}s")
        return collector.results


# The SC2 engine subprocess can hang indefinitely (observed directly:
# "Waiting for connection..." after the engine itself printed a fatal
# error and died) instead of returning from coordinator.update(). The
# existing `timeout` kwarg on CommandCenterParser.parse_replay only checks
# elapsed time *between* update() calls, so it never fires if a single
# update() call blocks forever. Isolating the parse in a child process lets
# us SIGKILL it from outside when that happens, instead of hanging whatever
# thread called us (the replay-folder watcher, or a background upload task)
# forever and leaking a zombie SC2 process every time.
_ISOLATED_PARSE_HARD_TIMEOUT_SECONDS = 180


def _isolated_parse_worker(
    replay_path: str, num_players: int, timeout: int, result_queue: Any
) -> None:
    """Runs in a child process. Do not call directly."""
    try:
        parser = get_commandcenter_parser(auto_download=False)
        if parser is None:
            result_queue.put(("unavailable", None))
            return
        results = parser.parse_replay(replay_path, num_players=num_players, timeout=timeout)
        result_queue.put(("ok", results))
    except Exception as e:  # noqa: BLE001 - must not let the child crash silently
        result_queue.put(("error", str(e)))


def parse_replay_isolated(
    replay_path: str,
    num_players: int,
    hard_timeout: int = _ISOLATED_PARSE_HARD_TIMEOUT_SECONDS,
) -> Optional[Dict[int, Dict[str, Any]]]:
    """
    Parse a replay with PyCommandCenter in a child process with a hard
    wall-clock timeout, so a hung or crashed SC2 engine can be killed from
    outside instead of freezing the caller forever.

    Returns None on any failure (unavailable, timeout, crash, exception) —
    this is a best-effort high-fidelity enrichment, not a required step, so
    callers should fall back to sc2reader-based metrics rather than raise.
    """
    import multiprocessing

    if not HAS_CC:
        return None

    ctx = multiprocessing.get_context("spawn")
    result_queue: Any = ctx.Queue()
    proc = ctx.Process(
        target=_isolated_parse_worker,
        args=(replay_path, num_players, max(hard_timeout - 20, 10), result_queue),
    )
    proc.start()
    proc.join(timeout=hard_timeout)

    if proc.is_alive():
        logger.warning(
            f"CommandCenter parse of {os.path.basename(replay_path)} exceeded "
            f"{hard_timeout}s hard timeout; killing subprocess"
        )
        proc.terminate()
        proc.join(5)
        if proc.is_alive():
            proc.kill()
            proc.join(5)
        return None

    if result_queue.empty():
        logger.warning(
            f"CommandCenter parse of {os.path.basename(replay_path)} produced no result "
            f"(subprocess exit code: {proc.exitcode})"
        )
        return None

    status, payload = result_queue.get()
    if status == "unavailable":
        logger.debug("CommandCenter parser unavailable in child process")
        return None
    if status == "error":
        logger.warning(f"CommandCenter parse failed: {payload}")
        return None
    return cast(Dict[int, Dict[str, Any]], payload)


def get_commandcenter_parser(
    auto_download: bool = True,
) -> Optional[CommandCenterParser]:
    """
    Get a CommandCenterParser instance if available.

    Args:
        auto_download: If True, download SC2 automatically if not found (Linux only).

    Returns:
        CommandCenterParser instance, or None if PyCommandCenter is not available
        or SC2 is not installed.
    """
    if not HAS_CC:
        logger.debug("PyCommandCenter not available")
        return None

    try:
        return CommandCenterParser(auto_download=auto_download)
    except RuntimeError as e:
        logger.warning(f"Could not initialize CommandCenterParser: {e}")
        return None


def is_commandcenter_available() -> bool:
    """Check if CommandCenter parsing is available."""
    if not HAS_CC:
        return False

    sc2_path = find_sc2_installation()
    if not sc2_path:
        return False

    exe_path = find_sc2_executable(sc2_path)
    if not exe_path:
        return False

    return verify_sc2_executable(exe_path)
