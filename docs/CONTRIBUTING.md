# Contributing Guide

We appreciate your interest in contributing to our project! This guide outlines our spec-first development workflow to ensure high-quality, well-documented changes.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to ensure a welcoming environment for all contributors.

## Spec-First Development Workflow

We follow a specification-first approach to ensure all changes are well-documented and reviewed before implementation.

### 1. Open an Issue
- Create a new issue describing the problem, feature request, or improvement
- Use descriptive titles and provide detailed context
- Tag the issue appropriately (bug, enhancement, documentation, etc.)
- Reference any related issues or discussions

### 2. Propose Spec Change
- Once the issue is discussed and approved, propose changes to the specification
- Include:
  - Detailed technical specification
  - API changes (if applicable)
  - Behavior changes
  - Migration considerations
  - Testing approach
- Use the issue comments or create a specification document

### 3. Submit PR to Specs Branch
- Create a pull request targeting the `specs` branch
- Include:
  - Reference to the original issue
  - Detailed specification document
  - Unique spec ID (format: `SPEC-YYYY-MM-DD-###`)
  - Rationale and alternatives considered
- Follow the spec PR template

### 4. Spec Review Process
- Maintainers and community members review the specification
- Address feedback and iterate on the design
- Ensure backwards compatibility considerations
- Get approval from at least 2 maintainers
- Spec must be merged before implementation begins

### 5. Implementation
- After spec approval, implement the changes in a new PR
- Target the appropriate branch (usually `main` or `develop`)
- Reference the spec ID in:
  - Commit messages: `feat: implement user authentication (SPEC-2024-01-15-001)`
  - Code comments: `// Implementation of SPEC-2024-01-15-001`
  - Documentation updates
- Include comprehensive tests
- Update relevant documentation

## Development Setup

### Prerequisites
- Git
- Pre-commit hooks (automatically installed)
- Development dependencies as listed in project documentation

### Getting Started
1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Install pre-commit hooks: `pre-commit install`
4. Create a feature branch: `git checkout -b feature/your-feature-name`
5. Make your changes following the spec-first workflow
6. Run tests and linting
7. Commit with descriptive messages
8. Push and create a pull request

## Pull Request Guidelines

### For Specifications
- Target the `specs` branch
- Include spec ID in title
- Reference the original issue
- Provide clear rationale and alternatives

### For Implementation
- Target the main development branch
- Reference the approved spec ID
- Include tests for new functionality
- Update documentation as needed
- Ensure all CI checks pass

## Commit Message Format

Use conventional commits format:
```
<type>(<scope>): <description> (<spec-id>)

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `spec`

Examples:
- `spec: add user authentication specification (SPEC-2024-01-15-001)`
- `feat: implement OAuth2 login (SPEC-2024-01-15-001)`
- `fix: resolve session timeout issue (SPEC-2024-01-10-003)`

## Code Style

- Follow the project's `.editorconfig` settings
- Run pre-commit hooks before committing
- Use meaningful variable and function names
- Add comments for complex logic
- Follow language-specific style guides

## Testing

- Write tests for all new functionality
- Ensure existing tests continue to pass
- Aim for high test coverage
- Include integration tests where appropriate

## Documentation

- Update relevant documentation for any changes
- Include code examples where helpful
- Update API documentation for interface changes
- Keep README.md current

## Review Process

1. **Automated Checks**: All CI checks must pass
2. **Code Review**: At least one maintainer review required
3. **Testing**: Ensure comprehensive test coverage
4. **Documentation**: Verify documentation is updated
5. **Spec Compliance**: Implementation must match approved spec

## Questions and Support

- Open an issue for bugs or feature requests
- Use discussions for questions and community interaction
- Join our community channels (if available)
- Review existing issues and documentation first

## Recognition

We appreciate all contributions! Contributors will be:
- Listed in the project's contributors
- Mentioned in release notes for significant contributions
- Invited to join the maintainer team for ongoing contributors

Thank you for contributing to our project!
