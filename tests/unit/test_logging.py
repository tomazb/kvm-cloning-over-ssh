"""Comprehensive unit tests for structured logging."""

import pytest
import json
import logging
from io import StringIO
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from kvm_clone.logging import StructuredLogger, logger


class TestStructuredLogger:
    """Test StructuredLogger class."""
    
    def test_structured_logger_initialization(self):
        """Test StructuredLogger can be initialized."""
        test_logger = StructuredLogger("test_logger")
        assert test_logger is not None
        assert test_logger.logger is not None
        assert test_logger.logger.name == "test_logger"
    
    def test_structured_logger_default_level(self):
        """Test StructuredLogger has default log level."""
        test_logger = StructuredLogger("test_default")
        assert test_logger.logger.level == logging.INFO
    
    def test_structured_logger_custom_level(self):
        """Test StructuredLogger with custom log level."""
        test_logger = StructuredLogger("test_custom", level=logging.DEBUG)
        assert test_logger.logger.level == logging.DEBUG
    
    def test_structured_logger_has_json_formatter(self):
        """Test StructuredLogger uses JSON formatter."""
        test_logger = StructuredLogger("test_formatter")
        assert len(test_logger.logger.handlers) > 0
        handler = test_logger.logger.handlers[0]
        assert isinstance(handler.formatter, StructuredLogger.JsonFormatter)
    
    def test_structured_logger_clears_existing_handlers(self):
        """Test StructuredLogger clears existing handlers to avoid duplicates."""
        # Create logger with handler
        test_logger = StructuredLogger("test_clear")
        initial_handler_count = len(test_logger.logger.handlers)
        
        # Reinitialize - should clear handlers and add only one
        test_logger = StructuredLogger("test_clear")
        assert len(test_logger.logger.handlers) == initial_handler_count


class TestJsonFormatter:
    """Test JsonFormatter class."""
    
    def test_json_formatter_formats_basic_record(self):
        """Test JsonFormatter produces valid JSON."""
        formatter = StructuredLogger.JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)  # Should not raise
        
        assert "timestamp" in data
        assert "level" in data
        assert "logger" in data
        assert "message" in data
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
    
    def test_json_formatter_includes_timestamp(self):
        """Test JsonFormatter includes ISO format timestamp."""
        formatter = StructuredLogger.JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        # Verify timestamp is valid ISO format
        timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)
    
    def test_json_formatter_with_exception(self):
        """Test JsonFormatter includes exception information."""
        formatter = StructuredLogger.JsonFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "Test exception" in data["exception"]
    
    def test_json_formatter_with_extra_fields(self):
        """Test JsonFormatter includes extra fields."""
        formatter = StructuredLogger.JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        # When extra={...} is passed to logger, fields are added directly to LogRecord
        record.operation_id = "123"
        record.user = "admin"
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "operation_id" in data
        assert "user" in data
        assert data["operation_id"] == "123"
        assert data["user"] == "admin"


class TestStructuredLoggerMethods:
    """Test StructuredLogger logging methods."""
    
    def setup_method(self):
        """Set up test logger with string stream."""
        self.stream = StringIO()
        self.test_logger = StructuredLogger("test_methods")
        # Replace handler with one that writes to our stream
        self.test_logger.logger.handlers.clear()
        handler = logging.StreamHandler(self.stream)
        handler.setFormatter(StructuredLogger.JsonFormatter())
        self.test_logger.logger.addHandler(handler)
    
    def get_log_output(self):
        """Get and parse log output."""
        output = self.stream.getvalue()
        if output:
            return json.loads(output.strip().split('\n')[-1])
        return None
    
    def test_info_method(self):
        """Test info logging method."""
        self.test_logger.info("Info message")
        data = self.get_log_output()
        
        assert data is not None
        assert data["level"] == "INFO"
        assert data["message"] == "Info message"
    
    def test_info_with_kwargs(self):
        """Test info logging with keyword arguments."""
        self.test_logger.info("Operation started", operation_id="op-123", host="server1")
        data = self.get_log_output()
        
        assert data["message"] == "Operation started"
        assert data["operation_id"] == "op-123"
        assert data["host"] == "server1"
    
    def test_error_method(self):
        """Test error logging method."""
        self.test_logger.error("Error message")
        data = self.get_log_output()
        
        assert data["level"] == "ERROR"
        assert data["message"] == "Error message"
    
    def test_error_with_exc_info(self):
        """Test error logging with exception info."""
        try:
            raise RuntimeError("Test error")
        except RuntimeError:
            self.test_logger.error("Error occurred", exc_info=True)
        
        data = self.get_log_output()
        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "RuntimeError" in data["exception"]
    
    def test_warning_method(self):
        """Test warning logging method."""
        self.test_logger.warning("Warning message")
        data = self.get_log_output()
        
        assert data["level"] == "WARNING"
        assert data["message"] == "Warning message"
    
    def test_warning_with_kwargs(self):
        """Test warning logging with keyword arguments."""
        self.test_logger.warning("Disk space low", path="/var", available_gb=5)
        data = self.get_log_output()
        
        assert data["message"] == "Disk space low"
        assert data["path"] == "/var"
        assert data["available_gb"] == 5
    
    def test_debug_method(self):
        """Test debug logging method."""
        self.test_logger.logger.setLevel(logging.DEBUG)
        self.test_logger.debug("Debug message")
        data = self.get_log_output()
        
        assert data["level"] == "DEBUG"
        assert data["message"] == "Debug message"
    
    def test_debug_with_kwargs(self):
        """Test debug logging with keyword arguments."""
        self.test_logger.logger.setLevel(logging.DEBUG)
        self.test_logger.debug("Connection details", host="server", port=22)
        data = self.get_log_output()
        
        assert data["host"] == "server"
        assert data["port"] == 22
    
    def test_critical_method(self):
        """Test critical logging method."""
        self.test_logger.critical("Critical error")
        data = self.get_log_output()
        
        assert data["level"] == "CRITICAL"
        assert data["message"] == "Critical error"
    
    def test_critical_with_exc_info(self):
        """Test critical logging includes exception by default."""
        try:
            raise SystemError("System failure")
        except SystemError:
            self.test_logger.critical("System error occurred")
        
        data = self.get_log_output()
        assert data["level"] == "CRITICAL"
        # Default exc_info=True for critical
        assert "exception" in data


class TestGlobalLogger:
    """Test global logger instance."""
    
    def test_global_logger_exists(self):
        """Test global logger is accessible."""
        assert logger is not None
        assert isinstance(logger, StructuredLogger)
    
    def test_global_logger_name(self):
        """Test global logger has expected name."""
        assert logger.logger.name == "kvm_clone"
    
    def test_global_logger_can_log(self):
        """Test global logger can log messages."""
        # Should not raise
        logger.info("Test message")
        logger.error("Test error")
        logger.warning("Test warning")


class TestLoggingLevels:
    """Test logging level filtering."""
    
    def test_debug_not_logged_at_info_level(self):
        """Test debug messages not logged when level is INFO."""
        stream = StringIO()
        test_logger = StructuredLogger("test_level", level=logging.INFO)
        test_logger.logger.handlers.clear()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredLogger.JsonFormatter())
        test_logger.logger.addHandler(handler)
        
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        
        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        
        # Should only have info message
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["level"] == "INFO"
    
    def test_all_levels_logged_at_debug(self):
        """Test all messages logged when level is DEBUG."""
        stream = StringIO()
        test_logger = StructuredLogger("test_debug", level=logging.DEBUG)
        test_logger.logger.handlers.clear()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredLogger.JsonFormatter())
        test_logger.logger.addHandler(handler)
        
        test_logger.debug("Debug")
        test_logger.info("Info")
        test_logger.warning("Warning")
        test_logger.error("Error")
        test_logger.critical("Critical")
        
        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        
        assert len(lines) == 5
        levels = [json.loads(line)["level"] for line in lines]
        assert "DEBUG" in levels
        assert "INFO" in levels
        assert "WARNING" in levels
        assert "ERROR" in levels
        assert "CRITICAL" in levels


class TestLoggingEdgeCases:
    """Test edge cases and special scenarios."""
    
    def setup_method(self):
        """Set up test logger."""
        self.stream = StringIO()
        self.test_logger = StructuredLogger("test_edge")
        self.test_logger.logger.handlers.clear()
        handler = logging.StreamHandler(self.stream)
        handler.setFormatter(StructuredLogger.JsonFormatter())
        self.test_logger.logger.addHandler(handler)
    
    def test_empty_message(self):
        """Test logging empty message."""
        self.test_logger.info("")
        output = self.stream.getvalue()
        data = json.loads(output.strip())
        assert data["message"] == ""
    
    def test_very_long_message(self):
        """Test logging very long message."""
        long_message = "A" * 10000
        self.test_logger.info(long_message)
        output = self.stream.getvalue()
        data = json.loads(output.strip())
        assert data["message"] == long_message
    
    def test_special_characters_in_message(self):
        """Test logging message with special characters."""
        special_message = 'Message with "quotes" and \\ backslashes and \n newlines'
        self.test_logger.info(special_message)
        output = self.stream.getvalue()
        data = json.loads(output.strip())
        assert data["message"] == special_message
    
    def test_unicode_in_message(self):
        """Test logging message with Unicode characters."""
        unicode_message = "Testing Unicode: 你好世界 🚀 café"
        self.test_logger.info(unicode_message)
        output = self.stream.getvalue()
        data = json.loads(output.strip())
        assert data["message"] == unicode_message
    
    def test_none_kwargs(self):
        """Test logging with None values in kwargs."""
        self.test_logger.info("Message", value=None, empty=None)
        output = self.stream.getvalue()
        data = json.loads(output.strip())
        assert data["value"] is None
        assert data["empty"] is None
    
    def test_complex_data_in_kwargs(self):
        """Test logging with complex data structures in kwargs."""
        self.test_logger.info(
            "Complex data",
            list_data=[1, 2, 3],
            dict_data={"key": "value"},
            nested={"level1": {"level2": "value"}}
        )
        output = self.stream.getvalue()
        data = json.loads(output.strip())
        assert data["list_data"] == [1, 2, 3]
        assert data["dict_data"] == {"key": "value"}
        assert data["nested"]["level1"]["level2"] == "value"
    
    def test_logging_numbers(self):
        """Test logging various number types."""
        self.test_logger.info(
            "Numbers",
            integer=42,
            float_val=3.14159,
            negative=-100,
            zero=0
        )
        output = self.stream.getvalue()
        data = json.loads(output.strip())
        assert data["integer"] == 42
        assert data["float_val"] == 3.14159
        assert data["negative"] == -100
        assert data["zero"] == 0
    
    def test_logging_booleans(self):
        """Test logging boolean values."""
        self.test_logger.info("Booleans", true_val=True, false_val=False)
        output = self.stream.getvalue()
        data = json.loads(output.strip())
        assert data["true_val"] is True
        assert data["false_val"] is False


class TestLoggingConcurrency:
    """Test logging in concurrent scenarios."""
    
    def test_multiple_loggers_independent(self):
        """Test multiple logger instances are independent."""
        logger1 = StructuredLogger("logger1", level=logging.DEBUG)
        logger2 = StructuredLogger("logger2", level=logging.ERROR)
        
        assert logger1.logger.level == logging.DEBUG
        assert logger2.logger.level == logging.ERROR
        assert logger1.logger.name != logger2.logger.name
    
    def test_logger_thread_safety(self):
        """Test logger is thread-safe (basic check)."""
        import threading
        
        stream = StringIO()
        test_logger = StructuredLogger("test_thread")
        test_logger.logger.handlers.clear()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredLogger.JsonFormatter())
        test_logger.logger.addHandler(handler)
        
        def log_messages():
            for i in range(10):
                test_logger.info(f"Message {i}")
        
        threads = [threading.Thread(target=log_messages) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        # Should have 50 messages (5 threads * 10 messages)
        assert len(lines) == 50