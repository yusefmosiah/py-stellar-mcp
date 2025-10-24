# Stellar Python MCP Server

A **Model Context Protocol (MCP)** server that exposes Stellar blockchain operations as intuitive composite tools for AI agents and LLMs. Built with FastMCP and Stellar SDK for testnet trading and account management.

**Key Features:**
- 🎯 **Intuitive buying/selling semantics** - Natural language API for LLMs
- 🚀 **Composite tools** - 5 consolidated tools instead of many individual operations
- 🔒 **Persistent key storage** - File-based keypair management that survives restarts
- ⚡ **Single-call operations** - Built-in auto-signing reduces complexity

---

## Features

- **Account Management**: Create, fund, and query Stellar testnet accounts
- **Persistent Key Storage**: Secure file-based keypair management
- **SDEX Trading**: Intuitive buy/sell API with explicit asset semantics
- **Trustline Management**: Establish and remove trustlines for issued assets
- **Composite Tools**: Consolidated operations reduce MCP overhead by ~70%
- **MCP Compliant**: Full tool registration and discovery support

---

## Quick Start

### 0. Configure MCP Client

Add to your MCP client configuration (e.g., Claude Desktop `~/Library/Application Support/Claude/claude_desktop_config.json`):

**Option A: Using `uv` (automatic dependency management)**
```json
{
  "mcpServers": {
    "stellar": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/py-stellar-mcp",
        "run",
        "server.py"
      ]
    }
  }
}
```

**Option B: Using Python directly (explicit control)**
```json
{
  "mcpServers": {
    "stellar": {
      "command": "/ABSOLUTE/PATH/TO/py-stellar-mcp/.venv/bin/python",
      "args": [
        "/ABSOLUTE/PATH/TO/py-stellar-mcp/server.py"
      ]
    }
  }
}
```

**Important:** Replace `/ABSOLUTE/PATH/TO/py-stellar-mcp` with your actual project path.

### 1. Install Dependencies

```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # macOS/Linux

# Install packages
uv pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

Create `.env` file:
```bash
STELLAR_NETWORK=testnet
HORIZON_URL=https://horizon-testnet.stellar.org
```

### 3. Test Server Locally (Optional)

You can test the server directly before using it with an MCP client:

**Option A: Using `uv`**
```bash
uv run server.py
```

**Option B: Using Python directly**
```bash
source .venv/bin/activate
python server.py
```

The MCP server will start and expose 5 composite Stellar tools. For production use, restart your MCP client (e.g., Claude Desktop) to load the server.

---

## Composite Tool Reference

### 1. Account Manager (`account_manager_tool`)

**7 operations in 1 tool:** create, fund, get, transactions, list, export, import

```python
# Create new account
account_manager_tool(action="create")
# → {"account_id": "G...", "public_key": "G..."}

# Fund account (testnet only)
account_manager_tool(action="fund", account_id="G...")
# → {"success": true, "balance": "10000.0000000"}

# Get account details
account_manager_tool(action="get", account_id="G...")
# → {"balances": [...], "sequence": "123", ...}

# Get transactions
account_manager_tool(action="transactions", account_id="G...", limit=10)

# List all managed accounts
account_manager_tool(action="list")

# Export keypair (⚠️ dangerous!)
account_manager_tool(action="export", account_id="G...")

# Import existing keypair
account_manager_tool(action="import", secret_key="S...")
```

### 2. Trading (`trading_tool`)

**6 operations in 1 tool:** buy (market/limit), sell (market/limit), cancel_order, get_orders

**Key Design:** Explicit buying/selling semantics that match user intent

```python
# Market buy: Buy 4 USDC by spending XLM
trading_tool(
    action="buy",
    order_type="market",
    account_id="G...",
    buying_asset="USDC",
    selling_asset="XLM",
    buying_issuer="GBBD...",
    amount="4"  # Buy 4 USDC at market price
)

# Limit buy: Buy 4 USDC, willing to pay 15 XLM per USDC
trading_tool(
    action="buy",
    order_type="limit",
    account_id="G...",
    buying_asset="USDC",
    selling_asset="XLM",
    buying_issuer="GBBD...",
    amount="4",    # Buy 4 USDC
    price="15"     # Pay 15 XLM per USDC
)

# Sell: Sell 100 XLM for USDC, want 0.01 USDC per XLM
trading_tool(
    action="sell",
    order_type="limit",
    account_id="G...",
    selling_asset="XLM",
    buying_asset="USDC",
    buying_issuer="GBBD...",
    amount="100",  # Sell 100 XLM
    price="0.01"   # Get 0.01 USDC per XLM
)

# Cancel order
trading_tool(action="cancel_order", account_id="G...", offer_id="12345")

# Get open orders
trading_tool(action="get_orders", account_id="G...")
```

### 3. Trustline Manager (`trustline_manager_tool`)

**2 operations in 1 tool:** establish, remove

```python
# Establish USDC trustline
trustline_manager_tool(
    action="establish",
    account_id="G...",
    asset_code="USDC",
    asset_issuer="GBBD...",
    limit=None  # Optional trust limit
)

# Remove trustline (requires 0 balance)
trustline_manager_tool(
    action="remove",
    account_id="G...",
    asset_code="USDC",
    asset_issuer="GBBD..."
)
```

### 4. Market Data (`market_data_tool`)

**2 operations in 1 tool:** orderbook queries

```python
# Get USDC/XLM orderbook
market_data_tool(
    action="orderbook",
    base_asset="XLM",       # Default base
    quote_asset="USDC",
    quote_issuer="GBBD...",
    limit=20                # Orders per side
)
# → {"bids": [...], "asks": [...]}
```

### 5. Utilities (`utilities_tool`)

**2 operations in 1 tool:** status, fee

```python
# Get Horizon server status
utilities_tool(action="status")

# Get network fee estimate
utilities_tool(action="fee")
```

---

## Usage Examples

### Example 1: Create and Fund Trading Account

```python
# 1. Create account
result = account_manager_tool(action="create")
account_id = result["account_id"]

# 2. Fund with testnet XLM
account_manager_tool(action="fund", account_id=account_id)
# → 10,000 XLM from Friendbot

# 3. Establish USDC trustline
usdc_issuer = "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"
trustline_manager_tool(
    action="establish",
    account_id=account_id,
    asset_code="USDC",
    asset_issuer=usdc_issuer
)

# 4. Ready to trade!
```

### Example 2: Place Market Buy Order

```python
# Buy 0.5 USDC at current market price using XLM
result = trading_tool(
    action="buy",
    order_type="market",
    account_id=account_id,
    buying_asset="USDC",
    selling_asset="XLM",
    buying_issuer=usdc_issuer,
    amount="0.5"
)
# → {"success": true, "hash": "...", "market_execution": {...}}
```

### Example 3: Place Limit Orders

```python
# Place buy limit: Buy 10 USDC, willing to pay up to 50 XLM per USDC
trading_tool(
    action="buy",
    order_type="limit",
    account_id=account_id,
    buying_asset="USDC",
    selling_asset="XLM",
    buying_issuer=usdc_issuer,
    amount="10",
    price="50"
)

# Place sell limit: Sell 100 XLM, want at least 0.02 USDC per XLM
trading_tool(
    action="sell",
    order_type="limit",
    account_id=account_id,
    selling_asset="XLM",
    buying_asset="USDC",
    buying_issuer=usdc_issuer,
    amount="100",
    price="0.02"
)
```

### Example 4: Manage Orders

```python
# Check orderbook
orderbook = market_data_tool(
    action="orderbook",
    quote_asset="USDC",
    quote_issuer=usdc_issuer,
    limit=10
)
print(orderbook["bids"])  # People buying XLM (selling USDC)
print(orderbook["asks"])  # People selling XLM (buying USDC)

# Get your open orders
orders = trading_tool(action="get_orders", account_id=account_id)
print(orders["offers"])

# Cancel specific order
if orders["offers"]:
    offer_id = orders["offers"][0]["id"]
    trading_tool(action="cancel_order", account_id=account_id, offer_id=offer_id)
```

---

## Architecture

```
┌──────────────────────┐
│  AI Agent / LLM      │ ← Strategy, decision-making
└──────────┬───────────┘
           │ MCP Protocol
           ↓
┌──────────────────────┐
│  FastMCP Server      │ ← Tool registration
│  (server.py)         │
└──────────┬───────────┘
           │
┌──────────┴───────────┐
│  Composite Tools     │ ← Consolidated operations
│  (stellar_tools)     │
└──────────┬───────────┘
           │
┌──────────┴───────────┐
│  KeyManager          │ ← Persistent file storage
│  (.stellar_keystore) │
└──────────┬───────────┘
           │
┌──────────┴───────────┐
│  Stellar SDK         │ ← Blockchain operations
└──────────┬───────────┘
           │
┌──────────┴───────────┐
│  Stellar Testnet     │
│  (Horizon API)       │
└──────────────────────┘
```

### Design Principles

1. **Intuitive Semantics**: Buying/selling API matches user mental model
2. **Composite Tools**: Consolidated operations reduce MCP call overhead
3. **Secure Key Management**: File-based persistence with 600 permissions
4. **Single-Call Operations**: Built-in auto-signing simplifies workflows
5. **Testnet Only**: Safe for hackathons and development

---

## API Semantics

### Buying/Selling Intent

The trading API uses **explicit buying/selling semantics** that match how humans think about trading:

```python
# ✅ Clear: "I want to buy 4 USDC by spending XLM"
trading_tool(
    action="buy",
    buying_asset="USDC",   # What I want
    selling_asset="XLM",   # What I'm spending
    amount="4",            # 4 USDC
    price="15"             # Willing to pay 15 XLM per USDC
)

# ✅ Clear: "I want to sell 100 XLM to get USDC"
trading_tool(
    action="sell",
    selling_asset="XLM",   # What I'm giving up
    buying_asset="USDC",   # What I want
    amount="100",          # 100 XLM
    price="0.01"           # Want 0.01 USDC per XLM
)
```

### Amount Interpretation

- **For `action="buy"`**: `amount` = quantity of `buying_asset` to acquire
- **For `action="sell"`**: `amount` = quantity of `selling_asset` to give up

### Price Interpretation

- **For `action="buy"`**: `price` = `selling_asset` per `buying_asset`
- **For `action="sell"`**: `price` = `buying_asset` per `selling_asset`

### Design Rationale

1. **Matches Stellar SDK**: Uses same buying/selling concepts as native `manage_buy_offer` and `manage_sell_offer`
2. **Intuitive for LLMs**: Natural language expressions like "Buy 4 USDC with XLM"
3. **No orderbook knowledge needed**: Internal translation handles base/quote orientation
4. **Zero ambiguity**: Clear intent in every API call

---

## Common Testnet Assets

### USDC (Testnet)
```
Code: USDC
Issuer: GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5
Faucet: https://stellar.org/faucet (web-based, rate-limited)
```

**Note**: Testnet USDC is scarce. Use web faucet to acquire small amounts for testing.

---

## Error Handling

All tools return structured responses:

**Success:**
```json
{
  "success": true,
  "hash": "abc123...",
  "ledger": 12345,
  "message": "Operation completed"
}
```

**Failure:**
```json
{
  "success": false,
  "error": "Account not found in key storage"
}
```

---

## Security Considerations

### Current Implementation
- ✅ File-based keypair storage (`.stellar_keystore.json`)
- ✅ Secure permissions (600 - owner read/write only)
- ✅ Testnet only (no real funds at risk)
- ✅ Secret keys never exposed to agents (except export action)
- ✅ Keypairs persist across restarts

### Production Recommendations
- Use encrypted file storage or HSM for keypairs
- Add authentication and rate limiting
- Implement audit logging
- Consider multi-signature accounts
- Use mainnet with proper key backup

---

## Development

### Project Structure
```
py-stellar-mcp/
├── server.py                 # FastMCP entry point
├── stellar_tools.py          # Composite tool implementations
├── key_manager.py            # Persistent keypair storage
├── test_basic.py             # Basic integration tests
├── test_sdex_trading.py      # SDEX trading tests (15/15 passing)
├── requirements.txt          # Dependencies
├── .env                      # Configuration (git-ignored)
├── .stellar_keystore.json    # Keypair storage (git-ignored)
├── .gitignore               # Excludes secrets
├── CHANGELOG.md             # Version history
├── SESSION_PROGRESS.md      # Development notes
└── README.md                # This file
```

### Adding New Actions

Extend existing composite tools:

```python
# In stellar_tools.py
def trading(action, account_id, ...):
    if action == "my_new_action":
        # Your implementation
        return {"success": True, "data": result}
    # ... existing actions
```

No need to register new MCP tools - just extend composite functions!

---

## Testing

### Run Integration Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run SDEX trading tests (15 tests)
python test_sdex_trading.py

# Run basic tests
python test_basic.py
```

### Test Reports

Timestamped markdown reports are generated in `test_reports/`:
- Account creation and funding
- Trustline establishment
- Orderbook queries
- Limit order placement
- Order cancellation
- Real market trade execution

---

## Troubleshooting

### "Account not found in key storage"
- Use `account_manager_tool(action="create")` or `action="import"` first
- Check `action="list"` to see managed accounts

### "Friendbot request failed"
- Friendbot may be rate-limited or down
- Try again after a few seconds

### "No trustline for asset"
- Use `trustline_manager_tool(action="establish", ...)` before receiving issued assets
- Check `account_manager_tool(action="get", ...)` to verify trustlines

### Transaction Failed
- Check account has sufficient XLM balance (for fees)
- Verify asset trustlines are established
- Check price format (use decimal strings like "15" or "0.01")
- Review error message in response

### Configuration Issues
- Ensure `.env` file exists with correct Horizon URL
- Verify Python 3.9+ is installed
- Check virtual environment is activated

---

## Resources

- **Stellar Developers**: https://developers.stellar.org
- **Stellar SDK Docs**: https://stellar-sdk.readthedocs.io
- **Horizon API**: https://developers.stellar.org/docs/data/horizon
- **Testnet Explorer**: https://stellar.expert/explorer/testnet
- **USDC Faucet**: https://stellar.org/faucet
- **FastMCP**: https://github.com/jlowin/fastmcp
- **MCP Protocol**: https://modelcontextprotocol.io

---

## Contributing

This is a hackathon project evolving toward production use. For enhancements:
1. ✅ Persistent keypair storage (implemented)
2. Add comprehensive error codes
3. Implement rate limiting
4. Add authentication
5. Enhance logging and monitoring
6. Consider mainnet support with proper warnings

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

Built with:
- **FastMCP** - MCP server framework
- **Stellar SDK** - Blockchain operations
- **Stellar Network** - Decentralized exchange

Trading API design inspired by Stellar's native SDK patterns.

---

## Support

For issues or questions:
1. Check [Stellar Developers Discord](https://discord.gg/stellar)
2. Review [Stellar Stack Exchange](https://stellar.stackexchange.com)
3. Read [FastMCP Documentation](https://github.com/jlowin/fastmcp)

---

**Ready to build AI-powered Stellar trading agents!** 🚀
