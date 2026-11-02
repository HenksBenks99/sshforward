# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI/CD workflow for automated builds
- Issue templates for bug reports and feature requests
- CONTRIBUTING.md guidelines
- requirements.txt for dependency management

## [1.0.0] - 2024-11-02

### Added
- Initial release of SSH Port Forwarder Pro
- Single tunnel mode for individual port forwarding
- Multi-Cam mode supporting up to 150 cameras
- Switch mode supporting up to 20 fiber switches
- Secure credential handling (environment variable + config file)
- Modern dark-mode GUI with CustomTkinter
- Flexible input parsing (ranges: 1-16, lists: 1,5,7)
- Standalone Windows executable via PyInstaller
- Automatic IP mapping for cameras (10.10.0.100+) and switches (10.10.0.230+)
- Single SSH session multiplexing for all tunnels
- Configuration template file (sshforward_config.json.template)
- Comprehensive .gitignore for security

### Security
- Passwords never hardcoded in source
- Credentials loaded from SSH_PASSWORD env var or external config file
- Config file excluded from git via .gitignore

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2024-11-02 | Initial release |

---

## Release Checklist

For future releases:

- [ ] Update version in code/constants
- [ ] Update CHANGELOG.md
- [ ] Create and push git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] Verify GitHub Actions build succeeds
- [ ] Verify release artifacts are uploaded
- [ ] Test executable on target platforms