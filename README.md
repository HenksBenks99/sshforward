# SSH Port Forwarder Pro

> **Multi-Cam & Switch** - Desktop application for managing SSH tunnels with support for single port forwarding, multi-camera (up to 150 devices), and multi-switch (up to 20 devices) configurations.

![SSH Port Forwarder](https://img.shields.io/badge/SSH-Port%20Forwarder-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

---

## 🚀 Features

| Mode | Description | Max Devices | Use Case |
|------|-------------|-------------|----------|
| **Single** | Single port forwarding | 1 | Quick access to one device |
| **Multi-Cam** | Multiple cameras via single SSH session | 150 | IP camera management |
| **Switch** | Fiber switches management | 20 | Network switch administration |

### Key Capabilities
- 🔐 **Secure credential handling** - Passwords loaded from environment variable or external config file (never hardcoded)
- ⚡ **Ultra-fast multi-tunnel** - Single SSH connection multiplexes all tunnels
- 🎯 **Smart IP mapping** - Automatic IP assignment: `10.10.0.(100+camera_id)` and `10.10.0.(230+switch_id)`
- 🔢 **Flexible input parsing** - Support for ranges (`1-16`) and lists (`1,5,7,8,9`)
- 🖥️ **Modern GUI** - Built with CustomTkinter (dark mode by default)
- 📦 **Standalone executable** - No Python installation required for end users

---

## 📥 Installation

### Option 1: Download Executable (Recommended)
1. Go to [Releases](https://github.com/HenksBenks99/sshforward/releases)
2. Download `sshforward.exe` for Windows
3. Run directly - no installation needed

### Option 2: Run from Source
```bash
# Clone the repository
git clone https://github.com/HenksBenks99/sshforward.git
cd sshforward

# Install dependencies
pip install customtkinter sshtunnel

# Run the application
python sshforward.py
```

### Option 3: Build Your Own Executable
```bash
pip install pyinstaller
pyinstaller sshforward.spec
# Output: dist/sshforward.exe
```

---

## ⚙️ Configuration

### 1. Create Config File (Recommended)
Copy the template and fill in your credentials:

```bash
cp sshforward_config.json.template sshforward_config.json
```

Edit `sshforward_config.json`:
```json
{
  "password": "your_ssh_password_here",
  "username": "pi",
  "host": "192.168.1.10"
}
```

> ⚠️ **Security Note**: `sshforward_config.json` is gitignored. Never commit real credentials!

### 2. Environment Variable (Alternative)
```bash
# Windows (PowerShell)
$env:SSH_PASSWORD="your_password"

# Linux/macOS
export SSH_PASSWORD="your_password"
```

### Priority Order
1. `SSH_PASSWORD` environment variable
2. `sshforward_config.json` file
3. Manual entry in the GUI

---

## 🎮 Usage

### Single Tunnel Mode
1. Select **"Singolo"** radio button
2. Enter SSH credentials (or use config file)
3. Set **IP Destinatario** (e.g., `10.10.0.101`)
4. Set **Porta Destinatario** (e.g., `3001`)
5. Set **Porta PC** (local port, e.g., `8080`)
6. Click **AVVIA TUNNEL**

Access your device at: `http://localhost:8080`

### Multi-Cam Mode
1. Select **"Multi-Cam"** radio button
2. Enter camera IDs:
   - Range: `1-16`
   - List: `1,5,7,8,9`
   - Mixed: `1-5,10,15-20`
3. Set **Porta Nativa** (default: `80`)
4. Click **AVVIA TUNNEL**

Each camera gets a local port: `8000 + (camera_id - 1)`
- Camera 1 → `localhost:8000`
- Camera 5 → `localhost:8004`
- Camera 16 → `localhost:8015`

### Switch Mode
1. Select **"Switch Fibra"** radio button
2. Enter switch IDs (1-20): `1-20` or `1,3,5`
3. Set **Porta Nativa** (default: `80`)
4. Click **AVVIA TUNNEL**

Each switch gets a local port: `7000 + (switch_id - 1)`
- Switch 1 → `localhost:7000`
- Switch 20 → `localhost:7019`

---

## 🔧 Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR PC (localhost)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Port 8000   │  │ Port 8001   │  │ Port 8002   │  ...     │
│  │ (Cam 1)     │  │ (Cam 2)     │  │ (Cam 3)     │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│              ┌───────────────────────┐                       │
│              │   Single SSH Tunnel   │                       │
│              │   (SSH Server:22)     │                       │
│              └───────────┬───────────┘                       │
└──────────────────────────┼──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │10.10.0.101│       │10.10.0.102│       │10.10.0.103│
    │  :80    │       │  :80    │       │  :80    │
    │ Cam 1   │       │ Cam 2   │       │ Cam 3   │
    └─────────┘       └─────────┘       └─────────┘
```

---

## 🛠️ Development

### Project Structure
```
sshforward/
├── sshforward.py              # Main application
├── sshforward.spec            # PyInstaller spec
├── sshforward_config.json.template  # Config template
├── dist/sshforward.exe        # Compiled binary
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

### Key Classes
| Class | Purpose |
|-------|---------|
| `SSHForwarderApp` | Main GUI application |
| `TunnelManager` | SSH tunnel lifecycle management |
| `EndpointGenerator` | Camera/switch endpoint generation |
| `InputParser` | User input parsing (ranges, lists) |
| `SSHCredentials` | Secure credential handling |
| `NetworkConfig` | Network constants and limits |

### Dependencies
- `customtkinter` - Modern Tkinter UI
- `sshtunnel` - SSH tunnel library
- Standard library: `threading`, `json`, `subprocess`, `dataclasses`, `logging`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Style
- Type hints for all public methods
- Docstrings for all classes and public methods
- Follow existing naming conventions
- Keep security-first mindset (no hardcoded credentials)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This tool is for **authorized network administration only**. Ensure you have permission to access the target devices and networks. The authors are not responsible for misuse.

---

## 🙏 Acknowledgments

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern UI toolkit
- [sshtunnel](https://github.com/pahaz/sshtunnel) - SSH tunneling library
- [PyInstaller](https://pyinstaller.org/) - Executable bundler

---

<div align="center">

**Made with ❤️ for network administrators**

[Report Bug](https://github.com/HenksBenks99/sshforward/issues) • [Request Feature](https://github.com/HenksBenks99/sshforward/issues/new)

</div>