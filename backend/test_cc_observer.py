import sys
import os
import time

# Add the lib directory to path
sys.path.append("/home/vtee/projects/sc2mmr/backend/app/lib")

try:
    from library import Coordinator, IDAReplayObserver, Race

    print("Library imported successfully from app/lib")
except ImportError as e:
    print(f"Failed to import library: {e}")
    sys.exit(1)


class MyReplayObserver(IDAReplayObserver):
    def __init__(self):
        super().__init__()
        self.match_data = {}

    def on_game_start(self):
        print("Replay started!")
        # You can extract player info here
        # self.get_player_race(1) etc.

    def on_step(self):
        # Extract periodic metrics
        pass

    def on_game_end(self):
        print("Replay ended!")
        try:
            score = self.get_score()
            print(f"Final Score: {score}")
        except Exception as e:
            print(f"Error getting score: {e}")


def main():
    # Set SC2PATH for the process
    sc2_path = os.path.expanduser("~/StarCraftII")
    os.environ["SC2PATH"] = sc2_path
    exe_path = os.path.join(sc2_path, "Versions/Base75689/SC2_x64")

    # Use the constructor that takes the executable path
    coordinator = Coordinator(exe_path)
    observer = MyReplayObserver()

    # Path to one of your replays
    replay_path = "/home/vtee/projects/sc2mmr/backend/replays/00fa59764cde6c4d8f6d056b88c1ff7d791bcfbeeff6975c450abfe66ee92a16.SC2Replay"

    if not os.path.exists(replay_path):
        print(f"Replay not found: {replay_path}")
        return

    print(f"Attempting to observe: {replay_path}")

    try:
        coordinator.add_replay_observer(observer)
        coordinator.load_replay_list(replay_path)

        # Try to avoid LaunchStarcraft if it asserts
        # The library might handle launch in update()

        print("Starting observation loop...")
        start_time = time.time()
        # Some versions of the API need a dummy participant to pass the assertion
        # participant = create_participants(Race.Terran, IDABot())
        # coordinator.set_participants([participant])

        while coordinator.update():
            if time.time() - start_time > 30:
                print("Test timed out")
                break

        print("Observation complete.")

    except Exception as e:
        print(f"Error during execution: {e}")


if __name__ == "__main__":
    main()
