# KVM Clone Testing Framework

This directory contains the testing framework for the KVM cloning utility, configured with pytest, coverage reporting, and specification conformance tracking.

## Structure

```
tests/
├── __init__.py                    # Package initialization
├── conftest.py                    # Test configuration and fixtures
├── unit/                          # Unit tests
│   └── test_core_functionality.py # Core functionality unit tests
├── integration/                   # Integration tests
│   └── test_end_to_end.py        # End-to-end workflow tests
├── spec/                          # Specification conformance tests
│   └── test_conformance.py       # Requirements conformance tests
└── README.md                      # This file
```

## Test Categories

### Unit Tests
- **Purpose**: Test individual components in isolation
- **Marker**: `@pytest.mark.unit`
- **Location**: `tests/unit/`
- **Coverage**: Core functions, classes, and methods

### Integration Tests
- **Purpose**: Test component interactions and workflows
- **Marker**: `@pytest.mark.integration`
- **Location**: `tests/integration/`
- **Coverage**: Multi-component scenarios, external integrations

### Specification Conformance Tests
- **Purpose**: Verify compliance with functional requirements
- **Marker**: `@spec("SPEC-ID")`
- **Location**: `tests/spec/`
- **Coverage**: Requirements traceability and compliance

## Custom Markers

### @spec("SPEC-ID")
Used to mark tests that verify compliance with specific requirements:

```python
from tests.conftest import spec

@spec("FUNC-1")
def test_vm_configuration_parsing():
    """Verify VM configuration parsing meets FUNC-1 specification."""
    # Test implementation
```

### Standard Markers
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.slow` - Long-running tests

## Running Tests

### All Tests
```bash
poetry run pytest
```

### By Category
```bash
# Unit tests only
poetry run pytest -m unit

# Integration tests only
poetry run pytest -m integration

# Specification conformance tests only
poetry run pytest -m spec

# Exclude slow tests
poetry run pytest -m "not slow"
```

### By Specification ID
```bash
# Tests for a specific spec ID
poetry run pytest -k "FUNC-1"
```

### With Coverage
```bash
# Run with coverage report
poetry run pytest --cov=src/kvm_clone --cov-report=html

# Enforce 90% coverage
poetry run pytest --cov-fail-under=90
```

## Coverage Requirements

- **Minimum Coverage**: 90%
- **Enforcement**: Automatic via Git hooks and pytest configuration
- **Reports**: 
  - Terminal output with missing lines
  - HTML report in `htmlcov/`
  - XML report in `coverage.xml`

## Git Hooks

### Pre-commit Hook
- Runs tests with coverage check before each commit
- Blocks commits if coverage is below 90%
- Location: `.git/hooks/pre-commit`

### Pre-push Hook  
- Runs full test suite before push
- Generates comprehensive coverage report
- Location: `.git/hooks/pre-push`

## Configuration

### pytest.ini
- Test discovery patterns
- Coverage settings
- Custom marker definitions
- Default options

### .coveragerc
- Coverage measurement configuration
- Exclusion patterns
- Report formatting
- Fail-under threshold

## Fixtures

Available test fixtures in `conftest.py`:

- `sample_vm_config`: Sample VM configuration for testing
- `mock_ssh_connection`: Mock SSH connection (placeholder)
- `temp_clone_config`: Temporary clone configuration

## Best Practices

1. **Specification Traceability**: Always use `@spec("ID")` for requirement tests
2. **Isolation**: Unit tests should not depend on external resources
3. **Meaningful Names**: Test names should clearly describe what they verify
4. **Coverage**: Aim for 100% line coverage, minimum 90%
5. **Markers**: Use appropriate markers for test categorization
6. **Documentation**: Include docstrings explaining test purpose

## Examples

### Unit Test with Spec Marker
```python
@spec("FUNC-1")
@pytest.mark.unit
def test_vm_config_validation(sample_vm_config):
    """Test VM configuration validation meets FUNC-1."""
    # Test implementation
    assert sample_vm_config["name"] == "test-vm"
```

### Integration Test
```python
@spec("INT-1")
@pytest.mark.integration
@pytest.mark.slow
def test_complete_clone_workflow(temp_clone_config):
    """Test complete VM cloning workflow."""
    # Integration test implementation
```

## Maintenance

- Update specification IDs when requirements change
- Add new test categories as needed
- Maintain fixture dependencies
- Review coverage exclusions periodically
- Update Git hooks for new requirements
