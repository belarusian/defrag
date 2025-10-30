"""
Progress tracking and logging for long-running analysis.

Writes state to file so you can monitor progress during execution.
"""

import json
import os
from datetime import datetime
from typing import Optional


class ProgressTracker:
    """Tracks and logs analysis progress to file."""

    def __init__(self, root_dir: str, log_file: str = "defrag_progress.log"):
        """
        Initialize progress tracker.

        Args:
            root_dir: Root directory to write log file
            log_file: Name of log file
        """
        self.log_path = os.path.join(root_dir, log_file)
        self.state_path = os.path.join(root_dir, ".defrag_state.json")
        self.start_time = datetime.now()

        # Initialize log
        with open(self.log_path, "w") as f:
            f.write(f"Defrag analysis started: {self.start_time.isoformat()}\n")
            f.write("=" * 60 + "\n\n")

    def log(self, message: str) -> None:
        """
        Write log message with timestamp.

        Args:
            message: Message to log
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        elapsed = (datetime.now() - self.start_time).total_seconds()

        with open(self.log_path, "a") as f:
            f.write(f"[{timestamp}] (+{elapsed:.1f}s) {message}\n")
            f.flush()

    def update_state(self, step: str, **kwargs) -> None:
        """
        Update state file with current progress.

        Args:
            step: Current step name
            **kwargs: Additional state data
        """
        state = {
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": (datetime.now() - self.start_time).total_seconds(),
            **kwargs,
        }

        with open(self.state_path, "w") as f:
            json.dump(state, f, indent=2)

    def section(self, title: str) -> None:
        """
        Log a section header.

        Args:
            title: Section title
        """
        with open(self.log_path, "a") as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"{title}\n")
            f.write("=" * 60 + "\n\n")
            f.flush()

    def complete(self) -> None:
        """Mark analysis as complete."""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        with open(self.log_path, "a") as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"Analysis complete! Total time: {elapsed:.1f}s\n")
            f.write("=" * 60 + "\n")
            f.flush()

        # Remove state file
        if os.path.exists(self.state_path):
            os.remove(self.state_path)
