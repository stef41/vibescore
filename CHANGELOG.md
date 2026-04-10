# Changelog

## [0.1.0] - 2025-04-10

### Added
- Initial release
- Code quality analysis (VC201–VC209): function length, complexity, parameters, type annotations, nesting, star imports, docstrings, mutable defaults
- Security analysis (VC301–VC309): hardcoded secrets, AWS keys, SQL injection, shell injection, unsafe deserialization, eval/exec, debug mode, private keys
- Dependency analysis (VC401–VC405): version pinning, lock files, deprecated setup.py
- Testing analysis (VC501–VC506): test presence, count, CI, conftest, test ratio
- ASCII terminal report with letter grades (A+ through F)
- JSON output format for CI pipelines
- `--min-score` flag for threshold-based CI gating
- Python library API: `from vibe_check import scan`
- Zero external dependencies
