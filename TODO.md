# TODO

The following contributing-infrastructure tasks are still pending and should be completed before closing Step 9.

- [ ] Create `CODE_OF_CONDUCT.md`
  - Adopt Contributor Covenant v2.1 or similar
  - Reference it from `CONTRIBUTING.md`

- [ ] Add `.editorconfig`
  - Define indentation (spaces vs tabs) and line endings
  - Configure charset (utf-8)
  - Set trim trailing whitespace and insert final newline

- [ ] Add pre-commit configuration
  - Create `.pre-commit-config.yaml`
  - Include hooks such as:
    - trailing-whitespace
    - end-of-file-fixer
    - check-added-large-files
    - black (for Python) / other formatters as needed
  - Update documentation to instruct contributors to run `pre-commit install`

Once these items are completed, Step 9 will be fully satisfied.
