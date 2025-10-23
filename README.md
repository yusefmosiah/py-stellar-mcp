# Stellar Python MCP Server

A **Model Context Protocol (MCP)** server that exposes Stellar blockchain operations as tools for AI agents and LLMs. Built with FastMCP and Stellar SDK for testnet trading and account management.

---

## Features

- **Account Management**: Create, fund, and query Stellar testnet accounts
- **Secure Key Storage**: Server-side keypair management (no secret keys exposed to agents)
- **SDEX Trading**: Place, cancel, and query orders on Stellar Decentralized Exchange
- **Trustline Management**: Establish and remove trustlines for issued assets
- **Transaction Flow**: Flexible build → sign → submit pattern
- **MCP Compliant**: Full tool registration and discovery support

---

## Quick Start

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

### 3. Run Server

```bash
python server.py
```

The MCP server will start and expose all Stellar tools for agent connections.

---

## Tool Reference

### Account Management

| Tool | Description |
|------|-------------|
| `create_account_tool()` | Generate new testnet account and store keypair |
| `fund_account_tool(account_id)` | Fund account via Friendbot (testnet only) |
| `get_account_tool(account_id)` | Get account balances and details |
| `get_transactions_tool(account_id, limit)` | Get transaction history |
| `list_accounts_tool()` | List all managed accounts |
| `export_keypair_tool(account_id)` | Export secret key (⚠️ dangerous!) |
| `import_keypair_tool(secret_key)` | Import existing keypair |

### Trustline Management

| Tool | Description |
|------|-------------|
| `establish_trustline_tool(account_id, asset_code, asset_issuer, limit)` | Enable trading of issued assets |
| `remove_trustline_tool(account_id, asset_code, asset_issuer)` | Remove trustline (requires zero balance) |

### SDEX Trading

| Tool | Description |
|------|-------------|
| `build_order_transaction_tool(...)` | Build unsigned order transaction |
| `sign_transaction_tool(account_id, xdr)` | Sign transaction with stored keypair |
| `submit_transaction_tool(signed_xdr)` | Submit signed transaction to network |
| `cancel_order_tool(account_id, offer_id)` | Cancel open order |
| `get_orderbook_tool(...)` | Fetch SDEX orderbook for asset pair |
| `get_open_orders_tool(account_id)` | Get account's open offers |

### Utilities

| Tool | Description |
|------|-------------|
| `get_server_status_tool()` | Get Horizon server health and status |
| `estimate_fee_tool()` | Get current network base fee |

---

## Usage Examples

### Example 1: Create and Fund Account

```python
# Agent workflow:

# 1. Create new account
result = create_account_tool()
account_id = result["account_id"]  # G...

# 2. Fund it with testnet XLM
fund_result = fund_account_tool(account_id)
# {"success": true, "balance": "10000.0000000"}

# 3. Check balance
account = get_account_tool(account_id)
print(account["balances"])
```

### Example 2: Setup Trading Account

```python
# Enable trading USDC/XLM

# 1. Create and fund account
account = create_account_tool()
account_id = account["account_id"]
fund_account_tool(account_id)

# 2. Establish trustline for USDC
usdc_issuer = "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"
trustline_result = establish_trustline_tool(
    account_id,
    "USDC",
    usdc_issuer
)

# 3. Verify trustline
account = get_account_tool(account_id)
# Should now see USDC in balances with 0 balance
```

### Example 3: Place Buy Order

```python
# Buy 10 USDC at 0.50 XLM per USDC

# 1. Build order transaction
order_xdr = build_order_transaction_tool(
    account_id=account_id,
    buy_or_sell="buy",
    selling_asset_type="native",  # XLM
    buying_asset_type="credit",   # USDC
    amount="10",                   # Buy 10 USDC
    price="0.50",                  # At 0.50 XLM per USDC
    buying_asset_code="USDC",
    buying_asset_issuer=usdc_issuer
)

# 2. Sign transaction
signed = sign_transaction_tool(account_id, order_xdr["xdr"])

# 3. Submit to network
result = submit_transaction_tool(signed["signed_xdr"])
# {"success": true, "hash": "...", "ledger": 123}
```

### Example 4: Check Orderbook and Open Orders

```python
# Get USDC/XLM orderbook
orderbook = get_orderbook_tool(
    selling_asset_type="native",
    buying_asset_type="credit",
    buying_asset_code="USDC",
    buying_asset_issuer=usdc_issuer,
    limit=10
)

print(orderbook["bids"])  # Buy orders
print(orderbook["asks"])  # Sell orders

# Check your open orders
orders = get_open_orders_tool(account_id)
print(orders["offers"])
```

### Example 5: Cancel Order

```python
# Get your open orders
orders = get_open_orders_tool(account_id)
offer_id = orders["offers"][0]["id"]

# Cancel specific order
cancel_result = cancel_order_tool(account_id, offer_id)
# {"success": true, "hash": "...", "message": "Order cancelled"}
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
│  KeyManager          │ ← Secure keypair storage
│  (in-memory)         │
└──────────────────────┘
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

### Key Design Principles

1. **Stateless Protocol Wrapper**: No business logic, just blockchain operations
2. **Secure Key Management**: Secret keys never exposed to agents
3. **Flexible Transaction Flow**: Build → inspect → sign → submit
4. **MCP Compliant**: Full tool discovery and registration
5. **Testnet Only**: Safe for hackathons and development

---

## Asset Representation

### Native XLM
```python
# In tool calls, use:
selling_asset_type="native"
# No code or issuer needed
```

### Issued Assets (e.g., USDC)
```python
# In tool calls, use:
selling_asset_type="credit"
selling_asset_code="USDC"
selling_asset_issuer="GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"
```

---

## Common Testnet Assets

### USDC (Testnet)
```
Code: USDC
Issuer: GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5
```

**Note**: Testnet asset issuers may change. Verify on [Stellar Expert Testnet](https://stellar.expert/explorer/testnet).

---

## Transaction Flow Pattern

All trading operations follow this pattern:

1. **Build**: Create unsigned transaction XDR
   - Allows inspection and modification
   - No commitment to network yet

2. **Sign**: Sign transaction with stored keypair
   - Server retrieves keypair securely
   - Returns signed XDR

3. **Submit**: Submit signed transaction to network
   - Transaction is final and broadcast
   - Returns success/failure with hash

This pattern gives agents maximum flexibility while keeping keys secure.

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

### Hackathon Version (Current)
- ✅ In-memory keypair storage
- ✅ Testnet only (no real funds at risk)
- ✅ Secret keys never exposed to agents
- ⚠️ Keypairs lost on server restart

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
├── server.py              # FastMCP entry point
├── stellar_tools.py       # Tool implementations
├── key_manager.py         # Keypair storage
├── requirements.txt       # Dependencies
├── requirements.md        # Setup guide
├── .env                   # Configuration (git-ignored)
├── .gitignore            # Excludes secrets
├── README.md             # This file
└── stellar-mcp-architecture-v2.md  # Design doc
```

### Adding New Tools

1. Implement function in `stellar_tools.py`:
```python
def my_new_tool(account_id: str, horizon: Server) -> dict:
    """Tool implementation"""
    try:
        # Your code here
        return {"success": True, "data": result}
    except Exception as e:
        return {"error": str(e)}
```

2. Register in `server.py`:
```python
@mcp.tool()
def my_new_tool_tool(account_id: str) -> dict:
    """Tool description for MCP"""
    return my_new_tool(account_id, horizon)
```

---

## Testing

### Manual Testing
```bash
# Start server
python server.py

# In another terminal, use MCP client to call tools
# Or test with Claude Desktop integration
```

### Unit Testing (Future)
```bash
pytest tests/
```

---

## Troubleshooting

### "Account not found in key storage"
- Use `create_account_tool()` or `import_keypair_tool()` first
- Check `list_accounts_tool()` to see managed accounts

### "Friendbot request failed"
- Friendbot may be rate-limited or down
- Try again after a few seconds
- Verify testnet connectivity: `curl https://friendbot.stellar.org`

### "No trustline for asset"
- Use `establish_trustline_tool()` before receiving issued assets
- Check `get_account_tool()` to verify trustlines

### Transaction Failed
- Check account has sufficient XLM balance (for fees)
- Verify asset trustlines are established
- Check price format (use decimal strings like "1.5")
- Review error message in response

---

## Resources

- **Stellar Developers**: https://developers.stellar.org
- **Stellar SDK Docs**: https://stellar-sdk.readthedocs.io
- **Horizon API**: https://horizon.stellar.org
- **Testnet Explorer**: https://stellar.expert/explorer/testnet
- **FastMCP**: https://github.com/jlowin/fastmcp
- **MCP Protocol**: https://modelcontextprotocol.io

---

## Contributing

This is a hackathon project. For production use:
1. Implement persistent keypair storage
2. Add comprehensive testing
3. Implement rate limiting
4. Add authentication
5. Enhance error handling
6. Add logging and monitoring

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

Built with:
- **FastMCP** - MCP server framework
- **Stellar SDK** - Blockchain operations
- **Stellar Network** - Decentralized exchange

---

## Support

For issues or questions:
1. Check [Stellar Developers Discord](https://discord.gg/stellar)
2. Review [Stellar Stack Exchange](https://stellar.stackexchange.com)
3. Read [FastMCP Documentation](https://github.com/jlowin/fastmcp)

---

**Ready to build AI-powered Stellar trading agents!** 🚀
