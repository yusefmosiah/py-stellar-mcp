# Changelog

All notable changes to the Stellar Python MCP Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-23

### Added - Initial Release

#### Core Infrastructure
- **FastMCP Server** (`server.py`)
  - MCP protocol-compliant server implementation
  - 16 registered tools for Stellar blockchain operations
  - Environment configuration support via `.env`
  - Testnet-only mode for safe development

- **Stellar Tools Module** (`stellar_tools.py`)
  - Complete implementation of all blockchain operations
  - Asset conversion helper function (`_dict_to_asset`)
  - Comprehensive error handling with structured responses
  - Support for both native (XLM) and issued assets

- **Key Manager** (`key_manager.py`)
  - Secure server-side keypair storage (in-memory)
  - Never exposes secret keys to agents/clients
  - Import/export functionality for backup
  - Account existence checking

#### Account Management Tools (7 tools)
- `create_account_tool()` - Generate new Stellar keypair
- `fund_account_tool()` - Fund via Friendbot (testnet)
- `get_account_tool()` - Query account details and balances
- `get_transactions_tool()` - Retrieve transaction history
- `list_accounts_tool()` - List all managed accounts
- `export_keypair_tool()` - Export secret key (with warnings)
- `import_keypair_tool()` - Import existing keypair

#### Trustline Management Tools (2 tools)
- `establish_trustline_tool()` - Enable issued asset trading
- `remove_trustline_tool()` - Remove trustline (requires zero balance)

#### SDEX Trading Tools (6 tools)
- `build_order_transaction_tool()` - Build unsigned order XDR
- `sign_transaction_tool()` - Sign transaction with stored keypair
- `submit_transaction_tool()` - Submit to Stellar network
- `cancel_order_tool()` - Cancel open SDEX order
- `get_orderbook_tool()` - Fetch orderbook for asset pair
- `get_open_orders_tool()` - List account's open offers

#### Utility Tools (2 tools)
- `get_server_status_tool()` - Check Horizon health
- `estimate_fee_tool()` - Get network fee estimate

#### Documentation
- **README.md** - Complete usage guide with examples
  - Quick start instructions
  - Tool reference table
  - Usage examples for common workflows
  - Architecture diagram
  - Troubleshooting guide

- **requirements.md** - Comprehensive setup guide
  - `uv` package manager installation
  - Virtual environment setup
  - Platform-specific instructions (macOS/Linux/Windows)
  - Quick reference command table

- **stellar-mcp-architecture-v2.md** - Implementation-ready architecture
  - Complete design specification
  - Code structure examples
  - Transaction flow patterns
  - Security considerations

#### Testing
- **test_basic.py** - Integration test suite
  - Tests all 7 core operations
  - Validates account creation and funding
  - Verifies trustline establishment
  - Confirms Horizon connectivity
  - Provides test account explorer link

#### Configuration
- **requirements.txt** - Python dependencies
  - fastmcp >= 1.0.0
  - stellar-sdk >= 9.0.0
  - requests >= 2.31.0
  - python-dotenv >= 1.0.0

- **.gitignore** - Protects sensitive data
  - Environment files (.env)
  - Secret keys and keypair backups
  - Python cache and build files
  - Virtual environments

- **.env** - Environment configuration template
  - Testnet Horizon URL
  - Friendbot URL
  - Network passphrase

### Fixed

#### Transaction Builder Issues
- Fixed `Account` object creation in all transaction-building functions
  - Changed from `horizon.accounts().account_id().call()` (returns dict)
  - To `horizon.load_account()` (returns proper Account object)
  - Affected functions:
    - `establish_trustline()`
    - `remove_trustline()`
    - `build_order_transaction()`
    - `cancel_order()`

#### Import Statements
- Added missing `Account` import to `stellar_tools.py`
- Added `TransactionEnvelope` import for transaction signing

### Technical Details

#### Architecture
- **Stateless design** - No business logic in MCP server
- **Secure key management** - Server-side only, never exposed
- **Flexible transaction flow** - Build → Sign → Submit pattern
- **MCP compliant** - Full tool registration and discovery

#### Network Configuration
- **Testnet only** - Safe for development and hackathons
- **Horizon URL**: https://horizon-testnet.stellar.org
- **Friendbot URL**: https://friendbot.stellar.org

#### Transaction Features
- Supports both buy and sell orders
- Native (XLM) and issued asset support
- Configurable trustline limits
- Price specified as decimal strings (e.g., "1.5")
- Amount specified as decimal strings (e.g., "100.50")

### Known Issues

#### Warnings
- TimeBounds warning from stellar-sdk (non-critical)
  - Transactions work but lack timeout protection
  - Can be addressed in future versions
  - See: https://www.stellar.org/developers-blog/transaction-submission-timeouts-and-dynamic-fees-faq

#### Limitations (By Design)
- In-memory keypair storage (lost on restart)
- No rate limiting
- No authentication
- Testnet only
- No multi-signature support
- No path payment support
- No liquidity pool support

### Testing Results

All integration tests passing:
- ✅ Horizon server connectivity
- ✅ Account creation
- ✅ Account listing
- ✅ Friendbot funding
- ✅ Account detail retrieval
- ✅ USDC trustline establishment
- ✅ Trustline verification

Test account created: `GAUQBRGF4CIBKRPOLW36GNKYMPNE46UWMK7LMFUIUJ67AQHWSGXMF4WH`

### Dependencies

```
fastmcp>=1.0.0        # MCP server framework
stellar-sdk>=9.0.0    # Stellar blockchain SDK
requests>=2.31.0      # HTTP client for Friendbot
python-dotenv>=1.0.0  # Environment configuration
```

### Platform Support

- **Python**: 3.9 - 3.13
- **OS**: macOS, Linux, Windows
- **Package Manager**: uv (recommended) or pip

### Security

#### Implemented
- ✅ Server-side keypair storage
- ✅ Secret keys never in API responses (except export_keypair)
- ✅ .gitignore excludes all sensitive files
- ✅ Testnet only (no real funds at risk)

#### Recommended for Production
- Encrypted file storage or HSM for keypairs
- Authentication and authorization
- Rate limiting
- Audit logging
- Multi-signature account support
- Mainnet support with proper key backup

### Contributors

Built for Stellar hackathon with:
- FastMCP - https://github.com/jlowin/fastmcp
- Stellar SDK - https://github.com/StellarCN/py-stellar-base
- Stellar Network - https://stellar.org

### License

MIT License

---

## [0.1.1] - 2025-10-23

### Added

#### Testing
- **test_sdex_trading.py** - Comprehensive SDEX trading test suite
  - 15 integration tests covering full trading workflow
  - Tests account creation, funding, and trustline setup (6 tests)
  - Tests orderbook querying (1 test)
  - Tests order placement - buy and sell orders (2 tests)
  - Tests open order checking (2 tests)
  - Tests order cancellation (2 tests)
  - Tests cancellation verification (1 test)
  - **Real market trade execution** - Successfully acquired 0.1 USDC at 892.38 XLM/USDC (1 test)
  - Automatic markdown report generation with timestamped results
  - Test accounts with Stellar Expert explorer links
  - 100% success rate (15/15 tests passing)

#### Test Reports
- **test_reports/** directory - Markdown test reports
  - Timestamped reports for each test run
  - Full test results with status indicators
  - Transaction hashes and ledger numbers
  - Account balances before and after trades
  - Links to test accounts on Stellar Expert

### Fixed

#### Asset Conversion Bug
- **stellar_tools.py:_dict_to_asset()** - Enhanced asset conversion helper
  - Now handles both custom format: `{"type": "native"}` or `{"code": "USDC", "issuer": "G..."}`
  - Also supports Horizon API format: `{"asset_type": "native"}` or `{"asset_type": "credit_alphanum4", "asset_code": "USDC", "asset_issuer": "G..."}`
  - Fixes KeyError when processing offers from Horizon API
  - Enables cancel_order() to work correctly with Horizon offer data

### Testing Results

#### Real Trade Execution
- ✅ Successfully executed market buy on testnet SDEX
- ✅ Acquired 0.1 USDC at market price (892.37908 XLM/USDC)
- ✅ Cost: ~89.24 XLM (testnet funds from Friendbot)
- ✅ Verified balance updates in real-time
- ✅ Transaction recorded on testnet ledger

#### Testnet Orderbook Analysis
- Found 9 bid orders (buyers) for USDC/XLM
- Found 1 ask order (seller) at 892.38 XLM/USDC
- Confirmed limited USDC liquidity on testnet
- Successfully matched with available ask order

### Technical Details

#### Test Suite Features
- Parallel account creation and setup
- Real-time orderbook querying
- Transaction hash tracking
- Ledger number verification
- Balance verification before/after trades
- Automatic report generation with timestamps
- Error handling and detailed error messages
- Support for both filled and unfilled orders

---

## [2.0.0] - 2025-10-23

### 🎉 Major Version: Semantic Refactoring & Tool Consolidation

This release represents a complete redesign of the trading API with **breaking changes** to provide intuitive buying/selling semantics for both users and LLM agents.

### Breaking Changes

#### API Redesign: Buying/Selling Semantics
- **Removed**: Base/quote asset terminology that required orderbook understanding
- **Added**: Explicit `buying_asset` and `selling_asset` parameters
- **Changed**: Action names for clarity:
  - `market_buy` → `buy` with `order_type="market"`
  - `limit_buy` → `buy` with `order_type="limit"`
  - `market_sell` → `sell` with `order_type="market"`
  - `limit_sell` → `sell` with `order_type="limit"`
  - `orders` → `get_orders`
  - `cancel` → `cancel_order`

**Old API (v1.x):**
```python
trading_tool(action="limit_buy", base_asset="XLM", quote_asset="USDC",
             amount="4", price="15")  # Confusing: 4 of what? Price means what?
```

**New API (v2.0):**
```python
trading_tool(action="buy", order_type="limit",
             buying_asset="USDC", selling_asset="XLM",
             amount="4", price="15")  # Clear: Buy 4 USDC, pay 15 XLM per USDC
```

#### Tool Consolidation (70% Reduction)
Consolidated 17 individual tools into 5 composite tools:
- **v1**: 17 tools requiring 3-5 MCP calls per workflow
- **v2**: 5 composite tools requiring 1-2 MCP calls per workflow
- **Token savings**: ~70% reduction in MCP overhead
- **Workflow simplification**: Single-call operations with built-in signing

**Composite Tools:**
1. `account_manager_tool()` - 7 operations (create, fund, get, transactions, list, export, import)
2. `trading_tool()` - 6 operations (buy, sell, cancel_order, get_orders with market/limit modes)
3. `trustline_manager_tool()` - 2 operations (establish, remove)
4. `market_data_tool()` - 2 operations (orderbook)
5. `utilities_tool()` - 2 operations (status, fee)

### Removed (v1 deprecated)
- ❌ `server.py` - Replaced by `server_v2.py`
- ❌ `stellar_tools.py` - Replaced by `stellar_tools_v2.py`
- ❌ `test_basic.py` - Replaced by `test_basic_v2.py`
- ❌ `test_sdex_trading.py` - Replaced by `test_sdex_trading_v2.py`
- ❌ Old planning docs (REFACTORING_PLAN.md, MIGRATION_GUIDE.md, etc.)

### Added

#### v2 Core Files
- **server_v2.py** - Composite tool MCP server with intuitive descriptions
- **stellar_tools_v2.py** - Refactored trading logic with buying/selling semantics
- **test_basic_v2.py** - Updated test suite for v2 API
- **test_sdex_trading_v2.py** - 15/15 integration tests with new API

#### Key Manager Persistence
- **File-based storage**: `.stellar_keystore.json` with secure 600 permissions
- **Auto-save**: Automatic persistence on `store()` and `import_keypair()`
- **Auto-load**: Keypairs restored on KeyManager initialization
- **Security**: Added to `.gitignore`, never committed to repo

### Fixed

#### Architecture Validation
- ✅ **Confirmed Horizon is correct API for SDEX trading** (not deprecated)
- ✅ Stellar RPC (Soroban) is for smart contracts only, **cannot interact with SDEX**
- ✅ No migration needed - v1 architecture was already optimal
- ✅ Horizon continues to receive protocol updates for classic operations

#### Trading Semantics Clarity
- Internal translation layer handles orderbook orientation automatically
- Users specify intent (buy/sell) without needing orderbook knowledge
- Price and amount interpretation now explicit based on action
- Matches Stellar SDK's native `manage_buy_offer` and `manage_sell_offer` design

### Testing Results

#### v2 Test Suite
- **15/15 tests passed** with new API (100% success rate)
- Real market trade executed: **0.02 USDC at 50.00 XLM/USDC**
- Test report: `test_reports/sdex_trading_v2_report_20251023_194356.md`

**Tests cover:**
- Account creation and funding (2 tests)
- Trustline establishment (2 tests)
- Orderbook queries (1 test)
- Limit order placement with new semantics (2 tests)
- Open order retrieval with `get_orders` (2 tests)
- Order cancellation with `cancel_order` (2 tests)
- Cancellation verification (1 test)
- Real market buy execution (1 test)

### Technical Details

#### Amount Interpretation
- For `action="buy"`: amount = quantity of `buying_asset` to acquire
- For `action="sell"`: amount = quantity of `selling_asset` to give up

#### Price Interpretation
- For `action="buy"`: price = `selling_asset` per `buying_asset`
- For `action="sell"`: price = `buying_asset` per `selling_asset`

#### Internal Translation
1. User provides buying/selling semantics (intuitive)
2. Code determines orderbook orientation (XLM is base when paired with issued assets)
3. Queries appropriate orderbook side for market orders
4. Translates to correct Stellar operations (ManageBuyOffer or ManageSellOffer)

### Migration Guide (v1 → v2)

#### Update Configuration
Change Claude Code MCP config from `server.py` to `server_v2.py`:
```json
{
  "mcpServers": {
    "stellar": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/server_v2.py"]
    }
  }
}
```

#### Update Trading Calls
```python
# v1 (old)
trading_tool(action="limit_buy", base_asset="XLM", quote_asset="USDC",
             amount="10", price="0.50")

# v2 (new)
trading_tool(action="buy", order_type="limit",
             buying_asset="USDC", selling_asset="XLM",
             buying_issuer="GBBD...", amount="10", price="0.50")
```

### Benefits

✅ **Intuitive for users and LLMs**: Natural language expressions like "Buy 4 USDC with XLM"
✅ **Matches Stellar's design**: Uses same buying/selling concepts as native SDK
✅ **Maintains full control**: All limit order and market order functionality preserved
✅ **70% token savings**: Fewer MCP calls required per workflow
✅ **Zero ambiguity**: Clear intent in every API call

### Contributors

Semantic refactoring and v2 architecture by the Stellar MCP team.

---

## [Unreleased]

### Planned Features
- Path payment support
- Liquidity pool operations
- Multi-signature account support
- Persistent keypair storage
- Transaction TimeBounds configuration
- Rate limiting
- Authentication middleware
- Mainnet support (with appropriate warnings)
- WebSocket streaming for real-time updates
- Historical trade data analysis

### Future Improvements
- Add TimeBounds to all transactions
- Implement keypair encryption at rest
- Add comprehensive error codes
- Improve transaction fee estimation
- Add memo field support
- Support for sponsored reserves
- Claimable balance operations

---

## Version History

- **2.0.0** (2025-10-23) - 🎉 Semantic refactoring with buying/selling API & tool consolidation (70% reduction)
- **0.1.1** (2025-10-23) - SDEX trading tests and asset conversion bug fix
- **0.1.0** (2025-10-23) - Initial release with core Stellar MCP functionality
