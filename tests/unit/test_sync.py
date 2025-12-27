"""Unit tests for sync module functionality."""

import pytest
from unittest.mock import MagicMock

from kvm_clone.sync import VMSynchronizer


class TestRsyncStatsParsing:
    """Test rsync stats parsing functionality."""

    @pytest.fixture
    def synchronizer(self):
        """Create a VMSynchronizer with mocked dependencies."""
        transport = MagicMock()
        libvirt_wrapper = MagicMock()
        return VMSynchronizer(transport, libvirt_wrapper)

    @pytest.mark.unit
    def test_parse_rsync_stats_valid_output(self, synchronizer):
        """Test parsing valid rsync --stats output."""
        rsync_output = """
Number of files: 1
Total file size: 1,234,567 bytes
Total transferred file size: 123,456 bytes
Literal data: 123,456 bytes
Matched data: 0 bytes
        """
        stats = synchronizer._parse_rsync_stats(rsync_output)
        assert stats["total_size"] == 1234567
        assert stats["transferred_size"] == 123456

    @pytest.mark.unit
    def test_parse_rsync_stats_no_commas(self, synchronizer):
        """Test parsing rsync output without thousands separators."""
        rsync_output = """
Total file size: 1234567 bytes
Total transferred file size: 123456 bytes
        """
        stats = synchronizer._parse_rsync_stats(rsync_output)
        assert stats["total_size"] == 1234567
        assert stats["transferred_size"] == 123456

    @pytest.mark.unit
    def test_parse_rsync_stats_empty_output(self, synchronizer):
        """Test parsing empty rsync output returns zeros."""
        stats = synchronizer._parse_rsync_stats("")
        assert stats["total_size"] == 0
        assert stats["transferred_size"] == 0

    @pytest.mark.unit
    def test_parse_rsync_stats_missing_patterns(self, synchronizer):
        """Test parsing rsync output without expected patterns."""
        rsync_output = "Some random output without stats"
        stats = synchronizer._parse_rsync_stats(rsync_output)
        assert stats["total_size"] == 0
        assert stats["transferred_size"] == 0

    @pytest.mark.unit
    def test_parse_rsync_stats_partial_output(self, synchronizer):
        """Test parsing rsync output with only total size."""
        rsync_output = "Total file size: 5,000,000 bytes"
        stats = synchronizer._parse_rsync_stats(rsync_output)
        assert stats["total_size"] == 5000000
        assert stats["transferred_size"] == 0

    @pytest.mark.unit
    def test_parse_rsync_stats_case_insensitive(self, synchronizer):
        """Test that parsing is case insensitive."""
        rsync_output = """
TOTAL FILE SIZE: 1,000,000 bytes
total transferred file size: 500,000 bytes
        """
        stats = synchronizer._parse_rsync_stats(rsync_output)
        assert stats["total_size"] == 1000000
        assert stats["transferred_size"] == 500000

    @pytest.mark.unit
    def test_parse_rsync_transfer_stats_sent_received(self, synchronizer):
        """Test parsing 'sent X bytes received Y bytes' format."""
        rsync_output = """
sending incremental file list
sent 1,234,567 bytes  received 89 bytes  823,104.00 bytes/sec
total size is 10,000,000  speedup is 8.10
        """
        stats = synchronizer._parse_rsync_transfer_stats(rsync_output)
        assert stats["bytes_transferred"] == 1234567
        assert stats["blocks_synchronized"] == 1234567 // 4096

    @pytest.mark.unit
    def test_parse_rsync_transfer_stats_fallback(self, synchronizer):
        """Test fallback to 'Total transferred file size' pattern."""
        rsync_output = """
Number of files: 1
Total transferred file size: 500,000 bytes
        """
        stats = synchronizer._parse_rsync_transfer_stats(rsync_output)
        assert stats["bytes_transferred"] == 500000

    @pytest.mark.unit
    def test_parse_rsync_transfer_stats_empty(self, synchronizer):
        """Test parsing empty transfer stats output."""
        stats = synchronizer._parse_rsync_transfer_stats("")
        assert stats["bytes_transferred"] == 0
        assert stats["blocks_synchronized"] == 0

    @pytest.mark.unit
    def test_parse_rsync_transfer_stats_no_match(self, synchronizer):
        """Test parsing output with no matching patterns."""
        rsync_output = "rsync completed successfully"
        stats = synchronizer._parse_rsync_transfer_stats(rsync_output)
        assert stats["bytes_transferred"] == 0
        assert stats["blocks_synchronized"] == 0

    @pytest.mark.unit
    def test_parse_rsync_stats_singular_byte(self, synchronizer):
        """Test parsing with 'byte' (singular) instead of 'bytes'."""
        rsync_output = """
Total file size: 1 byte
Total transferred file size: 1 byte
        """
        stats = synchronizer._parse_rsync_stats(rsync_output)
        assert stats["total_size"] == 1
        assert stats["transferred_size"] == 1
