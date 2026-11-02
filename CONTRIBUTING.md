# Contributing to SSH Port Forwarder Pro

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## 🎯 Ways to Contribute

- **Bug Reports** - Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml)
- **Feature Requests** - Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml)
- **Code Contributions** - Pull requests welcome!
- **Documentation** - Improve README, add examples, translate
- **Testing** - Test on different platforms, report issues

## 🔧 Development Setup

### Prerequisites
- Python 3.8+
- Git

### Local Development
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/sshforward.git
cd sshforward

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .  # Optional: install in development mode

# Run the application
python sshforward.py
```

### Running Tests
```bash
# Syntax check
python -m py_compile sshforward.py

# Linting (optional)
pip install ruff
ruff check sshforward.py
```

## 📝 Code Style Guidelines

### Python Style
- Follow [PEP 8](https://pep8.org/) with these exceptions:
  - Line length: 100 characters (not 79)
  - Use type hints for all public functions/methods
- Use [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- Run `ruff check` before committing

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `SSHForwarderApp` |
| Functions/Methods | snake_case | `create_single_tunnel` |
| Constants | UPPER_SNAKE_CASE | `CAMERA_BASE_IP_OFFSET` |
| Private methods | _snake_case | `_apply_secure_defaults` |
| Type variables | PascalCase | `T` |

### Security Guidelines
- **NEVER** hardcode passwords, tokens, or credentials
- Use `load_secure_config()` for all credential loading
- Keep `.gitignore` updated to exclude sensitive files
- Review security implications of new features

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description

Longer description if needed

Closes #123
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Formatting, no code changes
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks

**Examples:**
```
feat(gui): add dark/light theme toggle
fix(tunnel): handle connection timeout gracefully
docs(readme): update installation instructions
```

## 🚀 Pull Request Process

1. **Create an issue** first (for significant changes)
2. **Fork** the repository
3. **Create a branch**: `git checkout -b feat/your-feature-name`
4. **Make changes** with clear, focused commits
5. **Test thoroughly** on your platform
6. **Update documentation** if needed
7. **Push** and open a Pull Request

### PR Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No hardcoded credentials
- [ ] Tested on target platform(s)
- [ ] CI passes (if configured)

## 🏷️ Release Process

Releases are automated via GitHub Actions when a version tag is pushed:

```bash
# Create and push tag
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

This triggers:
1. Build on Windows and Linux
2. Create GitHub Release with artifacts
3. Auto-generate release notes

## 📋 Issue Labels

| Label | Purpose |
|-------|---------|
| `bug` | Something isn't working |
| `enhancement` | New feature request |
| `documentation` | Docs improvements |
| `good first issue` | Beginner-friendly |
| `help wanted` | Community help needed |
| `security` | Security-related |
| `wontfix` | Not planned |

## 💬 Communication

- **Issues** - Bug reports, feature requests
- **Discussions** - General questions, ideas
- **Pull Requests** - Code review, collaboration

## 🙏 Recognition

Contributors will be acknowledged in:
- Release notes
- README contributors section (optional)
- Git commit history

---

**Thank you for contributing!** 🎉