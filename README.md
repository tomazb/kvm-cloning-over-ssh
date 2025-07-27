# KVM Cloning over SSH

A tool for copying/syncing KVM virtual machines from one machine to another using libvirt API over SSH.

This project provides functionality to clone and synchronize KVM virtual machines between different hosts by leveraging the libvirt API through SSH connections. The code uses the fastest method to achieve reliable VM transfer between machines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Project Status

This repository is **under active development**. We recently introduced a *spec-first* workflow and added initial contribution guidelines (`CONTRIBUTING.md`). Some supporting infrastructure is still pending (see `TODO.md`). Expect breaking changes until we cut the first stable release.

### What’s Implemented
- Core logic for cloning KVM virtual machines over SSH via libvirt
- Basic test scaffolding under `tests/`
- Initial documentation (this README, docs)

### What’s Next
- Finalize community files:
  - `CODE_OF_CONDUCT.md`
  - `.editorconfig`
  - `.pre-commit-config.yaml`
- Harden CLI UX and error handling
- Expand automated test coverage

See `TODO.md` for the authoritative list of pending tasks.

## Contributing

Contributions are welcome! Please read `CONTRIBUTING.md` to understand our spec-first process. If you are proposing a change, start by opening an issue to discuss the specification.
