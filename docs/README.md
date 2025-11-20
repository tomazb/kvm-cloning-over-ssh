# Documentation Setup

This directory contains the MkDocs-based documentation system with Material theme and automatic spec ID linking via mkdocstrings.

## Features

✅ **MkDocs with Material Theme**: Modern, responsive documentation site  
✅ **mkdocstrings Integration**: Automatic API documentation generation from Python docstrings  
✅ **Spec ID Linking**: Automatic linking of specification IDs to source code  
✅ **Makefile Integration**: Simple `make docs` command to build HTML documentation  
✅ **Search Functionality**: Full-text search across all documentation  
✅ **Dark/Light Theme**: Toggle between themes with persistent preference  

## Quick Start

### Build Documentation
```bash
make docs
```

### Serve Documentation Locally
```bash
make docs-serve
```
Then visit http://127.0.0.1:8000 to view the documentation with live reloading.

### Clean Build Artifacts
```bash
make docs-clean
```

## File Structure

```
docs/
├── index.md                     # Main documentation homepage
├── api.md                       # API reference with mkdocstrings
├── technical_spec.md            # Technical specification
├── SECURITY_FIXES_REPORT.md     # Security fixes and improvements
├── CONTRIBUTING.md              # Contribution guidelines
├── specs/                       # Specifications directory
│   └── functional_spec.md       # Functional specification
└── README.md                    # This file

mkdocs.yml                       # MkDocs configuration
```

## Spec ID Linking

The documentation system automatically detects and links specification IDs in your docstrings:

- `SPEC-XXX`: Specification requirements
- `REQ-XXX`: Functional requirements  
- `TEST-XXX`: Test specifications
- `DOC-XXX`: Documentation references

### Example

In your Python docstrings, simply reference spec IDs like this:

```python
def clone_vm(self, vm_name: str) -> bool:
    """
    Clone a virtual machine between hosts.
    
    This implements SPEC-001 for basic cloning functionality
    and handles edge cases per SPEC-004.
    """
```

The documentation system will automatically create clickable links to the relevant specifications.

## Adding New Modules

To add documentation for a new Python module:

1. Add the module to your project
2. Include it in `docs/api.md` using mkdocstrings syntax:

```markdown
::: your_module_name
    options:
      show_source: true
      show_signature_annotations: true
```

3. Run `make docs` to regenerate the documentation

## Configuration

The documentation configuration is in `mkdocs.yml`:

- **Theme**: Material with dark/light mode toggle
- **Plugins**: Search and mkdocstrings for auto-generation
- **Extensions**: Syntax highlighting, admonitions, and more
- **Navigation**: Organized sections for easy browsing

## Dependencies

The following packages are required:

- `mkdocs`: Static site generator
- `mkdocs-material`: Material theme
- `mkdocstrings[python]`: Python docstring processing

Install with:
```bash
pip install mkdocs mkdocs-material mkdocstrings[python]
```
