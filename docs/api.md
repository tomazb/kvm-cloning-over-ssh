# API Reference

This page provides comprehensive API documentation automatically generated from source code using mkdocstrings.

## Overview

The API documentation includes:

- Function signatures with type annotations
- Docstring content with automatic formatting
- Source code links for easy navigation
- Automatic cross-referencing of spec IDs

## Modules

!!! info "Auto-generated Documentation"
    The sections below are automatically generated from Python modules in the source code.
    All spec IDs mentioned in docstrings will be automatically linked to their implementations.

### Example Usage

To include documentation for a specific module, use the mkdocstrings syntax:

```markdown
::: module_name
    options:
      show_source: true
      show_signature_annotations: true
```

### Core Modules

#### KVM Clone Module

The main module implementing VM cloning functionality with automatic spec ID linking:

::: kvm_clone
    options:
      show_source: true
      show_signature_annotations: true
      members_order: source
      show_submodules: false

## Spec ID Linking

When you reference spec IDs in your docstrings (e.g., `SPEC-001`, `REQ-123`), mkdocstrings will automatically:

1. Parse the spec ID format
2. Generate links to the corresponding source code locations
3. Provide hover tooltips with additional context
4. Enable bidirectional navigation between specs and implementations

### Supported Spec ID Formats

- `SPEC-XXX`: Specification requirements
- `REQ-XXX`: Functional requirements  
- `TEST-XXX`: Test specifications
- `DOC-XXX`: Documentation references

!!! tip "Best Practices"
    Include spec IDs in your docstrings using a consistent format. The linking system will automatically detect and process them during documentation generation.
