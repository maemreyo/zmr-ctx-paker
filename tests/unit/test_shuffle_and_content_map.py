"""Unit tests for shuffle_for_model_recall and XMLPacker content_map support."""

import os
import tempfile

import pytest

from ws_ctx_engine.packer.xml_packer import XMLPacker, shuffle_for_model_recall


class TestShuffleForModelRecall:
    def test_short_list_unchanged(self):
        files = ["a.py", "b.py", "c.py"]
        result = shuffle_for_model_recall(files, top_k=3, bottom_k=3)
        assert result == files

    def test_exact_threshold_unchanged(self):
        files = list("abcdef")
        result = shuffle_for_model_recall(files, top_k=3, bottom_k=3)
        assert result == files

    def test_top_and_bottom_placement(self):
        files = list("abcdefghij")  # 10 files
        result = shuffle_for_model_recall(files, top_k=2, bottom_k=2)
        # Top 2 should stay first
        assert result[:2] == ["a", "b"]
        # Last 2 of original (i, j) should now be last in result
        assert result[-2:] == ["i", "j"]
        # Middle should be c..h
        assert result[2:-2] == list("cdefgh")

    def test_length_preserved(self):
        files = list("abcde")
        result = shuffle_for_model_recall(files, top_k=1, bottom_k=1)
        assert len(result) == len(files)

    def test_empty_list(self):
        assert shuffle_for_model_recall([]) == []

    def test_single_element(self):
        assert shuffle_for_model_recall(["a.py"]) == ["a.py"]


class TestXMLPackerContentMap:
    def test_content_map_overrides_disk_read(self):
        """When content_map is provided, XMLPacker should use it instead of reading disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write file with one content to disk
            file_path = os.path.join(tmpdir, "src.py")
            with open(file_path, "w") as f:
                f.write("DISK_CONTENT")

            # Provide different content via content_map
            packer = XMLPacker()
            metadata = {"repo_name": "test", "file_count": 1, "total_tokens": 5}
            content_map = {"src.py": "PRELOADED_CONTENT"}
            output = packer.pack(
                selected_files=["src.py"],
                repo_path=tmpdir,
                metadata=metadata,
                content_map=content_map,
            )

            assert "PRELOADED_CONTENT" in output
            assert "DISK_CONTENT" not in output

    def test_without_content_map_reads_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "hello.py")
            with open(file_path, "w") as f:
                f.write("def hello(): pass")

            packer = XMLPacker()
            metadata = {"repo_name": "test", "file_count": 1, "total_tokens": 5}
            output = packer.pack(
                selected_files=["hello.py"],
                repo_path=tmpdir,
                metadata=metadata,
            )

            assert "def hello(): pass" in output

    def test_partial_content_map_falls_back_to_disk(self):
        """Files not in content_map should still be read from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name, content in [("a.py", "CONTENT_A"), ("b.py", "CONTENT_B")]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write(content)

            packer = XMLPacker()
            metadata = {"repo_name": "test", "file_count": 2, "total_tokens": 10}
            # Only override a.py
            content_map = {"a.py": "OVERRIDDEN_A"}
            output = packer.pack(
                selected_files=["a.py", "b.py"],
                repo_path=tmpdir,
                metadata=metadata,
                content_map=content_map,
            )

            assert "OVERRIDDEN_A" in output
            assert "CONTENT_B" in output
            assert "CONTENT_A" not in output

    def test_dedup_marker_in_output(self):
        """Content map with dedup marker is passed through unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "seen.py"), "w") as f:
                f.write("original content")

            packer = XMLPacker()
            metadata = {"repo_name": "test", "file_count": 1, "total_tokens": 3}
            marker = "[DEDUPLICATED: seen.py — already sent in this session. Hash: abcd1234]"
            content_map = {"seen.py": marker}
            output = packer.pack(
                selected_files=["seen.py"],
                repo_path=tmpdir,
                metadata=metadata,
                content_map=content_map,
            )

            assert "DEDUPLICATED" in output
