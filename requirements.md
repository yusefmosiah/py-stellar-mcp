# Requirements & Setup Guide

This guide covers setting up the Stellar Python MCP Server using `uv`, a fast Python package manager.

---

## Prerequisites

- **Python 3.9 or higher** (Python <4.0)
- **macOS, Linux, or Windows**
- **Internet connection** (for Stellar testnet access)

Check your Python version:
```bash
python --version
# or
python3 --version
```

---

## 1. Install uv

### macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Alternative (via pip):
```bash
pip install uv
```

Verify installation:
```bash
uv --version
```

---

## 2. Project Setup

### Clone or Navigate to Project:
```bash
cd /Users/wiz/py-stellar-mcp
```

### Create Virtual Environment:
```bash
uv venv
```

This creates a `.venv` directory with an isolated Python environment.

### Activate Virtual Environment:

**macOS/Linux:**
```bash
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

You should see `(.venv)` prefix in your terminal prompt.

---

## 3. Install Dependencies

### Create requirements.txt:

Create a file named `requirements.txt` with:

```
fastmcp>=1.0.0
stellar-sdk>=9.0.0
requests>=2.31.0
python-dotenv>=1.0.0
```

### Install with uv:
```bash
uv pip install -r requirements.txt
```

uv will:
- Resolve dependencies (very fast)
- Download packages
- Install them in your virtual environment

### Verify Installation:
```bash
python -c "import fastmcp; import stellar_sdk; print('All dependencies installed!')"
```

---

## 4. Project Dependencies Explained

| Package | Version | Purpose |
|---------|---------|---------|
| **fastmcp** | >=1.0.0 | MCP server framework for tool registration |
| **stellar-sdk** | >=9.0.0 | Official Stellar Python SDK for blockchain operations |
| **requests** | >=2.31.0 | HTTP library for Friendbot API calls |
| **python-dotenv** | >=1.0.0 | Environment variable management (optional) |

---

## 5. Environment Configuration (Optional)

The server works without configuration (uses testnet by default), but you can customize:

### Create .env file:
```bash
# Optional configuration
STELLAR_NETWORK=testnet
HORIZON_URL=https://horizon-testnet.stellar.org
FRIENDBOT_URL=https://friendbot.stellar.org
```

Note: The code currently hardcodes testnet URLs, so this is mainly for future extensibility.

---

## 6. Running the Server

Once dependencies are installed:

```bash
python server.py
```

The FastMCP server will start and listen for MCP protocol connections.

---

## 7. Stellar Testnet Setup

**No setup required!** The server handles everything:

1. **No Stellar account needed upfront** - Use `create_account()` tool
2. **No API keys required** - Horizon testnet is public
3. **No real funds needed** - `fund_account()` uses Friendbot (free testnet XLM)

### Testnet Resources:

- **Horizon API**: https://horizon-testnet.stellar.org
- **Friendbot**: https://friendbot.stellar.org
- **Testnet Explorer**: https://stellar.expert/explorer/testnet

---

## 8. Updating Dependencies

### Update all packages:
```bash
uv pip install --upgrade -r requirements.txt
```

### Update specific package:
```bash
uv pip install --upgrade stellar-sdk
```

### Check for outdated packages:
```bash
uv pip list --outdated
```

---

## 9. Development Workflow

### Daily workflow:
```bash
# 1. Navigate to project
cd /Users/wiz/py-stellar-mcp

# 2. Activate venv
source .venv/bin/activate

# 3. Run server
python server.py

# 4. Deactivate when done
deactivate
```

### Adding new dependencies:
```bash
# Install new package
uv pip install package-name

# Update requirements.txt
uv pip freeze > requirements.txt
```

---

## 10. Troubleshooting

### "uv: command not found"
- Restart terminal after installing uv
- Check PATH: `echo $PATH` should include `~/.cargo/bin`
- Reinstall: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### "No module named 'stellar_sdk'"
- Ensure venv is activated: `source .venv/bin/activate`
- Reinstall dependencies: `uv pip install -r requirements.txt`

### "Python version not compatible"
- Check version: `python --version` (need 3.9+)
- Use specific Python: `uv venv --python python3.11`

### Stellar SDK errors
- Verify testnet connectivity: `curl https://horizon-testnet.stellar.org`
- Check if Friendbot is online: `curl https://friendbot.stellar.org`

### FastMCP not starting
- Check if port is in use
- Verify FastMCP installation: `python -c "import fastmcp; print(fastmcp.__version__)"`

---

## 11. Platform-Specific Notes

### macOS
- May need to allow terminal in Security & Privacy settings
- If using Homebrew Python, ensure it's 3.9+

### Linux
- May need `python3-venv` package: `apt install python3-venv`
- Ensure `curl` is installed for uv installation

### Windows
- Use PowerShell (not Command Prompt) for best results
- May need to enable script execution: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## 12. CI/CD Considerations

For automated environments:

```bash
# Install uv in CI
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Run tests
python -m pytest tests/
```

---

## 13. Dependency Pinning (Production)

For production deployments, pin exact versions:

```bash
# Generate pinned requirements
uv pip freeze > requirements-lock.txt
```

Then install with:
```bash
uv pip install -r requirements-lock.txt
```

---

## 14. Quick Reference

| Task | Command |
|------|---------|
| Install uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Create venv | `uv venv` |
| Activate venv | `source .venv/bin/activate` |
| Install deps | `uv pip install -r requirements.txt` |
| Run server | `python server.py` |
| Deactivate venv | `deactivate` |
| Update all | `uv pip install --upgrade -r requirements.txt` |

---

## 15. Next Steps

After setup:

1. ✅ Dependencies installed
2. ✅ Virtual environment activated
3. ➡️ **Implement server.py** (see architecture-v2.md)
4. ➡️ **Test account creation and funding**
5. ➡️ **Test trading operations**
6. ➡️ **Build agent integration**

---

## Support Resources

- **uv Documentation**: https://github.com/astral-sh/uv
- **Stellar SDK Docs**: https://stellar-sdk.readthedocs.io
- **FastMCP GitHub**: https://github.com/jlowin/fastmcp
- **Stellar Developers**: https://developers.stellar.org

---

## Summary

**You need:**
- Python 3.9+ ✅
- uv package manager ✅
- Internet connection ✅

**You DON'T need:**
- Stellar account (server creates them)
- API keys (testnet is public)
- Real funds (Friendbot provides testnet XLM)

**Setup time: ~2 minutes**

Ready to implement!
