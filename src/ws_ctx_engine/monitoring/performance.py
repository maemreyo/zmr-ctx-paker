"""
Performance monitoring and metrics tracking for ws-ctx-engine.

Provides PerformanceMetrics and PerformanceTracker classes for tracking
indexing and query performance metrics.
"""

import os
import time
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """Performance metrics for indexing and query operations.

    This class stores comprehensive performance metrics including timing,
    file counts, index sizes, token counts, and memory usage.

    Attributes:
        # Indexing metrics
        indexing_time: Total time for indexing phase (seconds)
        files_processed: Number of files processed during indexing
        index_size: Total size of index files on disk (bytes)

        # Query metrics
        query_time: Total time for query phase (seconds)
        files_selected: Number of files selected within budget
        total_tokens: Total tokens in selected files

        # Memory metrics
        memory_usage: Peak memory usage during operations (bytes)

        # Phase-specific timing
        phase_timings: Dictionary of phase names to durations (seconds)
    """

    # Indexing metrics
    indexing_time: float = 0.0
    files_processed: int = 0
    index_size: int = 0

    # Query metrics
    query_time: float = 0.0
    files_selected: int = 0
    total_tokens: int = 0

    # Memory metrics
    memory_usage: int = 0

    # Phase-specific timing
    phase_timings: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for serialization.

        Returns:
            Dictionary representation of metrics
        """
        return {
            "indexing_time": self.indexing_time,
            "files_processed": self.files_processed,
            "index_size": self.index_size,
            "query_time": self.query_time,
            "files_selected": self.files_selected,
            "total_tokens": self.total_tokens,
            "memory_usage": self.memory_usage,
            "phase_timings": self.phase_timings,
        }


class PerformanceTracker:
    """Tracks performance metrics across indexing and query phases.

    This class provides methods to track timing, file counts, index sizes,
    token counts, and memory usage during ws-ctx-engine operations.

    Example:
        >>> tracker = PerformanceTracker()
        >>> tracker.start_phase("parsing")
        >>> # ... do parsing work ...
        >>> tracker.end_phase("parsing")
        >>> tracker.set_files_processed(100)
        >>> metrics = tracker.get_metrics()
        >>> print(f"Indexing time: {metrics.indexing_time:.2f}s")
    """

    def __init__(self) -> None:
        """Initialize performance tracker."""
        self.metrics = PerformanceMetrics()
        self._phase_start_times: dict[str, float] = {}
        self._indexing_start: float | None = None
        self._query_start: float | None = None

    def start_indexing(self) -> None:
        """Start tracking indexing phase."""
        self._indexing_start = time.time()

    def end_indexing(self) -> None:
        """End tracking indexing phase and record total time."""
        if self._indexing_start is not None:
            self.metrics.indexing_time = time.time() - self._indexing_start
            self._indexing_start = None

    def start_query(self) -> None:
        """Start tracking query phase."""
        self._query_start = time.time()

    def end_query(self) -> None:
        """End tracking query phase and record total time."""
        if self._query_start is not None:
            self.metrics.query_time = time.time() - self._query_start
            self._query_start = None

    def start_phase(self, phase_name: str) -> None:
        """Start tracking a specific phase.

        Args:
            phase_name: Name of the phase (e.g., "parsing", "vector_indexing")
        """
        self._phase_start_times[phase_name] = time.time()

    def end_phase(self, phase_name: str) -> None:
        """End tracking a specific phase and record duration.

        Args:
            phase_name: Name of the phase to end
        """
        if phase_name in self._phase_start_times:
            duration = time.time() - self._phase_start_times[phase_name]
            self.metrics.phase_timings[phase_name] = duration
            del self._phase_start_times[phase_name]

    def set_files_processed(self, count: int) -> None:
        """Set the number of files processed during indexing.

        Args:
            count: Number of files processed
        """
        self.metrics.files_processed = count

    def set_index_size(self, index_dir: str) -> None:
        """Calculate and set the total size of index files.

        Args:
            index_dir: Path to the index directory
        """
        total_size = 0

        if os.path.exists(index_dir):
            for root, _dirs, files in os.walk(index_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass  # Skip files we can't access

        self.metrics.index_size = total_size

    def set_files_selected(self, count: int) -> None:
        """Set the number of files selected during query.

        Args:
            count: Number of files selected
        """
        self.metrics.files_selected = count

    def set_total_tokens(self, tokens: int) -> None:
        """Set the total tokens in selected files.

        Args:
            tokens: Total token count
        """
        self.metrics.total_tokens = tokens

    def set_memory_usage(self, bytes_used: int) -> None:
        """Set the peak memory usage.

        Args:
            bytes_used: Memory usage in bytes
        """
        self.metrics.memory_usage = bytes_used

    def track_memory(self) -> None:
        """Track current memory usage and update peak if higher.

        This method uses psutil if available to track memory usage.
        If psutil is not available, memory tracking is skipped.
        """
        try:
            import psutil  # type: ignore[import-untyped]

            process = psutil.Process()
            memory_info = process.memory_info()
            current_memory = int(memory_info.rss)  # Resident Set Size

            if current_memory > self.metrics.memory_usage:
                self.metrics.memory_usage = current_memory
        except ImportError:
            # psutil not available, skip memory tracking
            pass
        except Exception:
            # Any other error, skip memory tracking
            pass

    def get_metrics(self) -> PerformanceMetrics:
        """Get the current performance metrics.

        Returns:
            PerformanceMetrics instance with all tracked metrics
        """
        return self.metrics

    def format_metrics(self, phase: str = "both") -> str:
        """Format metrics as a human-readable string.

        Args:
            phase: Which phase to format ("indexing", "query", or "both")

        Returns:
            Formatted string with metrics
        """
        lines = []

        if phase in ("indexing", "both") and self.metrics.indexing_time > 0:
            lines.append("Indexing Metrics:")
            lines.append(f"  Total time: {self.metrics.indexing_time:.2f}s")
            lines.append(f"  Files processed: {self.metrics.files_processed}")
            lines.append(f"  Index size: {self._format_bytes(self.metrics.index_size)}")

        if phase in ("query", "both") and self.metrics.query_time > 0:
            if lines:
                lines.append("")
            lines.append("Query Metrics:")
            lines.append(f"  Total time: {self.metrics.query_time:.2f}s")
            lines.append(f"  Files selected: {self.metrics.files_selected}")
            lines.append(f"  Total tokens: {self.metrics.total_tokens}")

        if self.metrics.memory_usage > 0:
            if lines:
                lines.append("")
            lines.append(f"Peak memory usage: {self._format_bytes(self.metrics.memory_usage)}")

        return "\n".join(lines)

    @staticmethod
    def _format_bytes(bytes_count: int) -> str:
        """Format byte count as human-readable string.

        Args:
            bytes_count: Number of bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        count: float = float(bytes_count)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if count < 1024.0:
                return f"{count:.2f} {unit}"
            count /= 1024.0
        return f"{count:.2f} PB"
