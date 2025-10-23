# Stellar Python MCP Server — Architecture v2 (Implementation-Ready)

## Purpose

Enable AI agents (LLMs) to interact with the Stellar **testnet** blockchain and SDEX for practical trading operations, exposing a minimal, MCP-compliant interface.

**All strategy management, data analysis, and decision-making are EXCLUDED**—agents call this server only for execution and blockchain queries.

---

## Changes from v1

- ✅ Added `establish_trustline()` tool (required for trading non-XLM assets)
- ✅ Added `list_accounts()` utility tool
- ✅ Added asset conversion helper function (`_dict_to_asset`)
- ✅ Clarified price format (string representation: "1.5")
- ✅ Added proper imports (TransactionEnvelope)
- ✅ Specified Friendbot implementation details
- ✅ Added error handling for missing keypairs
- ✅ Added keypair import/export tools for persistence

---

## Boundary Principles

- **MCP server is a stateless protocol wrapper**: exposes blockchain operations as tools
- **No business, strategy, or decision logic lives inside the MCP server**
- **LLM agent orchestration, strategy management, and advanced analysis are handled externally**
- **Full compatibility with MCP protocol tool registration/discovery**
- **Testnet-only for hackathon scope**

---

## Core Toolset (MCP Server Methods/Endpoints)

### 1. Account Management

- **`create_account()`**
  - Generates new Stellar keypair
  - Stores keypair securely server-side
  - Returns: `{"account_id": "G...", "message": "Account created (unfunded)"}`

- **`fund_account(account_id: str)`**
  - Funds testnet account via Friendbot (https://friendbot.stellar.org)
  - Returns: `{"success": true, "balance": "10000.0000000"}`
  - NOTE: Only works on testnet, returns error on mainnet

- **`get_account(account_id: str)`**
  - Returns account balances, sequence number, and trustlines
  - Returns: `{"balances": [...], "sequence": "...", "signers": [...]}`

- **`get_transactions(account_id: str, limit: int = 10)`**
  - Returns transaction and payment history
  - Returns: list of recent transactions

- **`list_accounts()`**
  - Lists all account_ids currently managed by server
  - Returns: `{"accounts": ["G...", "G..."]}`
  - Useful for debugging and account discovery

- **`export_keypair(account_id: str)`**
  - **DANGEROUS**: Exports secret key for backup/migration
  - Returns: `{"account_id": "G...", "secret_key": "S..."}`
  - Use with extreme caution

- **`import_keypair(secret_key: str)`**
  - Imports existing keypair into server storage
  - Returns: `{"account_id": "G..."}`

### 2. Asset & Trustline Management

- **`establish_trustline(account_id: str, asset: dict, limit: str = None)`**
  - Creates trustline to enable holding/trading an issued asset
  - Required before receiving non-XLM assets
  - `limit`: Optional trust limit (defaults to maximum)
  - Returns: transaction result with hash
  - Example:
    ```python
    establish_trustline(
        "G...",
        {"code": "USDC", "issuer": "G..."},
        limit="1000"
    )
    ```

- **`remove_trustline(account_id: str, asset: dict)`**
  - Removes trustline (requires zero balance of that asset)
  - Returns: transaction result

### 3. SDEX Trading (Low-Level Transaction Flow)

- **`build_order_transaction(account_id: str, buy_or_sell: str, selling_asset: dict, buying_asset: dict, amount: str, price: str)`**
  - Builds unsigned transaction XDR for manage_buy_offer or manage_sell_offer
  - `buy_or_sell`: "buy" or "sell"
  - `amount`: Decimal string (e.g., "100.50")
  - `price`: Decimal string ratio (e.g., "1.5" means 1.5 buying per 1 selling)
  - Returns: `{"xdr": "...", "tx_hash": "..."}`

- **`sign_transaction(account_id: str, xdr: str)`**
  - Signs transaction XDR using server-stored keypair
  - Returns: `{"signed_xdr": "..."}`
  - Raises error if account_id not found in storage

- **`submit_transaction(signed_xdr: str)`**
  - Submits signed transaction to testnet
  - Returns: `{"success": true/false, "hash": "...", "ledger": 123, "error": "..." (if failed)}`

- **`cancel_order(account_id: str, offer_id: str)`**
  - Convenience method: builds, signs, and submits cancel order transaction
  - Sets offer amount to 0 to cancel
  - Returns: transaction result

- **`get_orderbook(selling_asset: dict, buying_asset: dict, limit: int = 20)`**
  - Fetches current SDEX orderbook snapshot
  - Returns: `{"bids": [...], "asks": [...]}`

- **`get_open_orders(account_id: str)`**
  - Lists currently active offers for account
  - Returns: `{"offers": [{"id": "123", "selling": {...}, "buying": {...}, "amount": "100", "price": "1.5"}, ...]}`

### 4. Utility Methods

- **`get_server_status()`**
  - Returns Horizon server health, latest ledger
  - Returns: `{"horizon_version": "...", "core_version": "...", "history_latest_ledger": 123}`

- **`estimate_fee()`**
  - Estimates current transaction fee (base fee)
  - Returns: `{"fee": "100", "unit": "stroops"}`
  - NOTE: Stellar fees are dynamic, this returns network-recommended base fee

---

## Key Management (CRITICAL)

**NO secret keys passed as tool parameters** (except import_keypair for migration).

### Implementation:
1. Server maintains internal secure storage (in-memory dict for hackathon, file-based with encryption for prod)
2. `create_account()` generates keypair and stores it internally, indexed by `account_id`
3. All signing operations (`sign_transaction`) retrieve keypair from internal storage
4. Agent only ever sees/passes `account_id` (public key)
5. `export_keypair()` provided for backup but should be used sparingly

### Example Internal Storage:
```python
# key_manager.py
class KeyManager:
    def __init__(self):
        self._keypair_store = {}

    def store(self, account_id: str, secret_key: str):
        """Store keypair securely"""
        self._keypair_store[account_id] = secret_key

    def get_keypair(self, account_id: str):
        """Retrieve keypair for signing"""
        secret = self._keypair_store.get(account_id)
        if not secret:
            raise ValueError(f"Account {account_id} not found in key storage")
        return Keypair.from_secret(secret)

    def list_accounts(self):
        """List all managed accounts"""
        return list(self._keypair_store.keys())

    def export_secret(self, account_id: str):
        """Export secret key (dangerous!)"""
        secret = self._keypair_store.get(account_id)
        if not secret:
            raise ValueError(f"Account {account_id} not found")
        return secret
```

---

## Asset Representation

Assets use Stellar SDK standard format:

```python
# Native XLM
{"type": "native"}

# Issued asset
{
    "code": "USDC",
    "issuer": "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"
}
```

### Asset Conversion Helper (Internal):
```python
from stellar_sdk import Asset

def _dict_to_asset(asset_dict: dict) -> Asset:
    """Convert asset dict to Stellar SDK Asset object"""
    if asset_dict.get("type") == "native":
        return Asset.native()
    return Asset(asset_dict["code"], asset_dict["issuer"])
```

---

## Transaction Flow Pattern

**Agent orchestrates multi-step transactions:**

### Example 1: Place Order
```
1. Agent: build_order_transaction(account_id, "buy", selling, buying, amount, price)
   → Server: returns unsigned XDR

2. Agent: sign_transaction(account_id, xdr)
   → Server: signs with stored keypair, returns signed XDR

3. Agent: submit_transaction(signed_xdr)
   → Server: submits to Horizon, returns result
```

### Example 2: Setup Trading Account
```
1. Agent: create_account()
   → Server: returns account_id

2. Agent: fund_account(account_id)
   → Server: requests Friendbot funding

3. Agent: establish_trustline(account_id, {"code": "USDC", "issuer": "..."})
   → Server: builds, signs, submits trustline transaction

4. Agent: ready to trade USDC/XLM
```

This gives agents maximum flexibility to inspect/modify transactions before signing.

---

## Architectural Flow

```
┌──────────────────────┐
│  LLM/Agent Layer     │ ← Trading logic, strategy, decisions
└──────────┬───────────┘
           │ MCP Protocol
           ↓
┌──────────────────────┐
│  Python MCP Server   │ ← Stateless tool wrapper
│  (fastmcp)           │   - Account management
│                      │   - Transaction building/signing
│  ┌────────────────┐ │   - Keypair storage
│  │  KeyManager    │ │
│  │  (in-memory)   │ │
│  └────────────────┘ │
└──────────┬───────────┘
           │ stellar-sdk
           ↓
┌──────────────────────┐
│  Stellar Testnet     │
│  (Horizon API)       │
│  + Friendbot         │
└──────────────────────┘
```

---

## Directory Structure

```
py-stellar-mcp/
├── server.py              # MCP tool registration + FastMCP server
├── stellar_tools.py       # Tool implementations (account, trading, utils)
├── key_manager.py         # Secure keypair storage (in-memory for hackathon)
├── config.py              # Configuration and constants
├── requirements.txt       # fastmcp, stellar-sdk
├── .env                   # STELLAR_NETWORK=testnet, HORIZON_URL=... (optional)
├── .gitignore             # Exclude .env and keypair backups
├── README.md              # Usage guide and examples
└── tests/
    └── test_tools.py      # Basic integration tests
```

---

## Complete Code Structure

### server.py (FastMCP Entry Point)
```python
from fastmcp import FastMCP
from stellar_sdk import Server, TransactionBuilder, Keypair, Network, Asset, TransactionEnvelope
from key_manager import KeyManager
from stellar_tools import (
    create_account,
    fund_account,
    get_account,
    establish_trustline,
    build_order_transaction,
    sign_transaction,
    submit_transaction,
    get_orderbook,
    # ... import all tools
)

# Initialize
mcp = FastMCP("Stellar MCP Server")
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

horizon = Server(HORIZON_URL)
keys = KeyManager()

# Register all tools
@mcp.tool()
def create_account_tool() -> dict:
    """Generate new testnet account and store keypair securely"""
    return create_account(keys)

@mcp.tool()
def fund_account_tool(account_id: str) -> dict:
    """Fund testnet account using Friendbot"""
    return fund_account(account_id, horizon)

# ... register all other tools ...

if __name__ == "__main__":
    mcp.run()
```

### stellar_tools.py (Tool Implementations)
```python
from stellar_sdk import (
    Server,
    TransactionBuilder,
    Keypair,
    Network,
    Asset,
    TransactionEnvelope
)
import requests

TESTNET_NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
FRIENDBOT_URL = "https://friendbot.stellar.org"

def _dict_to_asset(asset_dict: dict) -> Asset:
    """Convert asset dict to Stellar SDK Asset object"""
    if asset_dict.get("type") == "native":
        return Asset.native()
    return Asset(asset_dict["code"], asset_dict["issuer"])

def create_account(key_manager):
    """Generate new testnet account"""
    keypair = Keypair.random()
    account_id = keypair.public_key
    key_manager.store(account_id, keypair.secret)
    return {
        "account_id": account_id,
        "message": "Account created (unfunded). Use fund_account() to activate."
    }

def fund_account(account_id: str, horizon: Server):
    """Fund account via Friendbot"""
    try:
        response = requests.get(f"{FRIENDBOT_URL}?addr={account_id}")
        response.raise_for_status()

        # Get updated balance
        account = horizon.accounts().account_id(account_id).call()
        xlm_balance = next(
            (b["balance"] for b in account["balances"] if b["asset_type"] == "native"),
            "0"
        )

        return {
            "success": True,
            "balance": xlm_balance,
            "message": "Account funded successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_account(account_id: str, horizon: Server):
    """Get account details"""
    try:
        account = horizon.accounts().account_id(account_id).call()
        return {
            "account_id": account_id,
            "sequence": account["sequence"],
            "balances": account["balances"],
            "signers": account["signers"],
            "thresholds": account["thresholds"]
        }
    except Exception as e:
        return {"error": str(e)}

def establish_trustline(
    account_id: str,
    asset: dict,
    limit: str,
    key_manager,
    horizon: Server
):
    """Establish trustline for issued asset"""
    try:
        keypair = key_manager.get_keypair(account_id)
        asset_obj = _dict_to_asset(asset)

        account = horizon.accounts().account_id(account_id).call()
        tx_builder = TransactionBuilder(
            source_account=account,
            network_passphrase=TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )

        tx_builder.append_change_trust_op(
            asset=asset_obj,
            limit=limit
        )

        tx = tx_builder.build()
        tx.sign(keypair)

        response = horizon.submit_transaction(tx)
        return {
            "success": response.get("successful", False),
            "hash": response.get("hash"),
            "ledger": response.get("ledger")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def build_order_transaction(
    account_id: str,
    buy_or_sell: str,
    selling_asset: dict,
    buying_asset: dict,
    amount: str,
    price: str,
    horizon: Server
):
    """Build unsigned order transaction"""
    try:
        account = horizon.accounts().account_id(account_id).call()

        selling = _dict_to_asset(selling_asset)
        buying = _dict_to_asset(buying_asset)

        tx_builder = TransactionBuilder(
            source_account=account,
            network_passphrase=TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )

        if buy_or_sell == "buy":
            tx_builder.append_manage_buy_offer_op(
                selling=selling,
                buying=buying,
                amount=amount,
                price=price
            )
        elif buy_or_sell == "sell":
            tx_builder.append_manage_sell_offer_op(
                selling=selling,
                buying=buying,
                amount=amount,
                price=price
            )
        else:
            raise ValueError("buy_or_sell must be 'buy' or 'sell'")

        tx = tx_builder.build()
        return {
            "xdr": tx.to_xdr(),
            "tx_hash": tx.hash().hex()
        }
    except Exception as e:
        return {"error": str(e)}

def sign_transaction(account_id: str, xdr: str, key_manager):
    """Sign transaction XDR"""
    try:
        keypair = key_manager.get_keypair(account_id)
        tx = TransactionEnvelope.from_xdr(xdr, TESTNET_NETWORK_PASSPHRASE)
        tx.sign(keypair)
        return {"signed_xdr": tx.to_xdr()}
    except Exception as e:
        return {"error": str(e)}

def submit_transaction(signed_xdr: str, horizon: Server):
    """Submit signed transaction"""
    try:
        tx = TransactionEnvelope.from_xdr(signed_xdr, TESTNET_NETWORK_PASSPHRASE)
        response = horizon.submit_transaction(tx)
        return {
            "success": response.get("successful", False),
            "hash": response.get("hash"),
            "ledger": response.get("ledger")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_orderbook(selling_asset: dict, buying_asset: dict, limit: int, horizon: Server):
    """Fetch SDEX orderbook"""
    try:
        selling = _dict_to_asset(selling_asset)
        buying = _dict_to_asset(buying_asset)

        orderbook = horizon.orderbook(selling, buying).limit(limit).call()
        return {
            "bids": orderbook["bids"],
            "asks": orderbook["asks"],
            "base": orderbook["base"],
            "counter": orderbook["counter"]
        }
    except Exception as e:
        return {"error": str(e)}

def get_open_orders(account_id: str, horizon: Server):
    """Get account's open offers"""
    try:
        offers = horizon.offers().for_account(account_id).call()
        return {
            "offers": [
                {
                    "id": offer["id"],
                    "selling": offer["selling"],
                    "buying": offer["buying"],
                    "amount": offer["amount"],
                    "price": offer["price"]
                }
                for offer in offers["_embedded"]["records"]
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def cancel_order(account_id: str, offer_id: str, key_manager, horizon: Server):
    """Cancel open order"""
    try:
        keypair = key_manager.get_keypair(account_id)
        account = horizon.accounts().account_id(account_id).call()

        # Get offer details to know which assets
        offer = horizon.offers().offer(offer_id).call()

        selling = _dict_to_asset(offer["selling"])
        buying = _dict_to_asset(offer["buying"])

        tx_builder = TransactionBuilder(
            source_account=account,
            network_passphrase=TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )

        # Setting amount to 0 cancels the offer
        tx_builder.append_manage_sell_offer_op(
            selling=selling,
            buying=buying,
            amount="0",
            price=offer["price"],
            offer_id=int(offer_id)
        )

        tx = tx_builder.build()
        tx.sign(keypair)

        response = horizon.submit_transaction(tx)
        return {
            "success": response.get("successful", False),
            "hash": response.get("hash"),
            "message": f"Order {offer_id} cancelled"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### key_manager.py
```python
from stellar_sdk import Keypair

class KeyManager:
    """In-memory keypair storage (hackathon version)"""

    def __init__(self):
        self._keypair_store = {}

    def store(self, account_id: str, secret_key: str):
        """Store keypair securely"""
        self._keypair_store[account_id] = secret_key

    def get_keypair(self, account_id: str) -> Keypair:
        """Retrieve keypair for signing"""
        secret = self._keypair_store.get(account_id)
        if not secret:
            raise ValueError(f"Account {account_id} not found in key storage. Use create_account() or import_keypair() first.")
        return Keypair.from_secret(secret)

    def list_accounts(self) -> list:
        """List all managed accounts"""
        return list(self._keypair_store.keys())

    def export_secret(self, account_id: str) -> str:
        """Export secret key (dangerous!)"""
        secret = self._keypair_store.get(account_id)
        if not secret:
            raise ValueError(f"Account {account_id} not found")
        return secret

    def import_keypair(self, secret_key: str) -> str:
        """Import existing keypair"""
        keypair = Keypair.from_secret(secret_key)
        account_id = keypair.public_key
        self._keypair_store[account_id] = secret_key
        return account_id
```

---

## Error Handling

**Simple but informative for hackathon:**

- Let Stellar SDK exceptions bubble up naturally
- Return error dict on failure: `{"success": false, "error": "message"}`
- No complex retry logic
- Validate critical parameters (account_id exists, asset format correct)
- Log errors to console for debugging

Example pattern:
```python
try:
    # operation
    return {"success": True, "data": result}
except Exception as e:
    return {"success": False, "error": str(e)}
```

---

## Testing Testnet Assets

Common testnet asset issuers for testing:

```python
# USDC Testnet
USDC_TESTNET = {
    "code": "USDC",
    "issuer": "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"
}

# Note: Testnet assets change; verify on https://stellar.expert/explorer/testnet
```

---

## Dependencies (requirements.txt)

```
fastmcp>=1.0.0
stellar-sdk>=9.0.0
requests>=2.31.0
python-dotenv>=1.0.0
```

Install with:
```bash
pip install -r requirements.txt
```

---

## Environment Setup (.env - Optional)

```bash
# Testnet configuration
STELLAR_NETWORK=testnet
HORIZON_URL=https://horizon-testnet.stellar.org
FRIENDBOT_URL=https://friendbot.stellar.org

# For production (not used in hackathon):
# STELLAR_NETWORK=public
# HORIZON_URL=https://horizon.stellar.org
```

---

## Excluded Concerns (Out of Scope)

- Strategy planning/optimization
- Historical data analysis
- Multi-agent orchestration
- Persistent storage (beyond in-memory keypairs)
- Rate limiting
- Production security hardening
- Mainnet support
- Multi-signature accounts
- Fee bump transactions
- Path payments

---

## Implementation Checklist

- [ ] Set up project structure and install dependencies
- [ ] Implement KeyManager with error handling
- [ ] Implement account management tools (create, fund, get, list)
- [ ] Implement trustline tools (establish, remove)
- [ ] Implement asset conversion helper
- [ ] Build transaction flow tools (build, sign, submit)
- [ ] Add SDEX query tools (orderbook, open orders)
- [ ] Add cancel order tool
- [ ] Implement utility tools (server status, estimate fee)
- [ ] Add export/import keypair tools
- [ ] Register all tools with FastMCP
- [ ] Test account creation and funding
- [ ] Test trustline establishment
- [ ] Test order placement and cancellation
- [ ] Test full trading flow (create → fund → trustline → trade)
- [ ] Write README with usage examples
- [ ] Add .gitignore for secrets

---

## Quick Start Guide (for README)

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Run Server
```bash
python server.py
```

### 3. Example Agent Flow (Pseudocode)
```python
# Create and fund account
account = create_account()
fund_account(account["account_id"])

# Setup USDC trading
establish_trustline(account["account_id"], USDC_ASSET)

# Check orderbook
orderbook = get_orderbook(
    {"type": "native"},
    USDC_ASSET
)

# Place buy order
xdr = build_order_transaction(
    account["account_id"],
    "buy",
    {"type": "native"},
    USDC_ASSET,
    "10",
    "0.50"
)
signed = sign_transaction(account["account_id"], xdr["xdr"])
result = submit_transaction(signed["signed_xdr"])
```

---

## Summary

**Implementation-ready Stellar Python MCP server:**
- Testnet-only, stateless except for keypair storage
- Complete transaction primitives (build → sign → submit)
- Trustline management for asset trading
- Asset conversion helpers
- Proper error handling for missing accounts
- No trading logic, strategy, or analysis
- Agent orchestrates all decisions and multi-step flows
- Fast to implement, easy to debug, fully MCP-compliant

**Ready for implementation with all gaps addressed.**
