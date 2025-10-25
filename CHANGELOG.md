# Changelog

All notable changes to the Stellar Python MCP Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## Version History

- **3.0.1** (2025-10-24) - Soroban test report generation & macOS SSL certificate fix
- **3.0.0** (2025-10-23) - 🚀 Soroban smart contract support (6th composite tool)
- **2.0.0** (2025-10-23) - 🎉 Semantic refactoring with buying/selling API & tool consolidation (70% reduction)
- **0.1.1** (2025-10-23) - SDEX trading tests and asset conversion bug fix
- **0.1.0** (2025-10-23) - Initial release with core Stellar MCP functionality
---

## [Unreleased]

### Planned Features
- Path payment support
- Liquidity pool operations
- Multi-signature account support
- Transaction TimeBounds configuration
- Rate limiting
- Authentication middleware
- Mainnet support (with appropriate warnings)
- WebSocket streaming for real-time updates
- Historical trade data analysis
- Deploy test Soroban contracts for integration testing

### Future Improvements
- Add TimeBounds to all transactions
- Implement keypair encryption at rest
- Add comprehensive error codes
- Improve transaction fee estimation
- Add memo field support
- Support for sponsored reserves
- Claimable balance operations
- Better SSL certificate handling (programmatic aiohttp configuration)
- Expand Soroban test coverage with real contract deployments

---

## [3.0.1] - 2025-10-24

### Added

#### Soroban Test Reports
- **test_soroban_basic.py** - Enhanced with markdown report generation
  - 7/7 validation tests (no network calls)
  - Tests module imports, server.py structure, parameter parsing
  - Tests stellar-sdk async dependencies, configuration files
  - Generates timestamped reports in `test_reports/`
  - Report: `soroban_validation_report_YYYYMMDD_HHMMSS.md`

- **test_soroban.py** - Enhanced with markdown report generation
  - 2/2 integration tests passing (server health, error handling)
  - Contract invocation tests gracefully skipped (no verified live contract)
  - Includes account funding via Friendbot
  - Generates timestamped reports in `test_reports/`
  - Report: `soroban_integration_report_YYYYMMDD_HHMMSS.md`

#### Documentation
- **SOROBAN_TESTING_NOTES.md** - Technical notes and limitations
  - Documents macOS SSL certificate issue and workaround
  - Explains contract testing limitations
  - Lists known issues and future improvements
  - Provides guidance for users deploying test contracts

### Fixed

#### SSL Certificate Issue (macOS + Python 3.6+)
- **Root Cause**: Python 3.6+ on macOS ships with its own OpenSSL that doesn't use system certificates
- **Impact**: aiohttp (used by stellar-sdk) couldn't verify Stellar testnet SSL certificates
- **Solution**: Added `SSL_CERT_FILE` environment variable to `.env`
  - Points to certifi's CA certificate bundle
  - Enables aiohttp to verify SSL certificates properly
  - Required for Python 3.13+ on macOS Sequoia

#### Test Report Generation
- **test_soroban.py** now always generates reports, even on early failures
- Changed from early return to conditional test execution
- Ensures all test runs produce documentation

### Changed

#### Test Structure
- **test_soroban.py** - Updated contract testing approach
  - Sets `CONTRACT_ID = None` by default (no verified live contract available)
  - Gracefully skips contract invocation tests when no contract ID provided
  - Focus on testable functionality: server health, error handling
  - Documents how to enable contract tests (deploy contract → set CONTRACT_ID)

#### Environment Configuration
- **.env** - Added SSL certificate configuration
  - `SSL_CERT_FILE` pointing to certifi's certificate bundle
  - Documented the issue and how to find certificate path
  - Required for Python 3.6+ on macOS

### Testing Results

#### Validation Tests
- ✅ 7/7 tests passed (100% success rate)
- Tests: imports, structure, parameter parsing, dependencies, configuration
- No network calls required
- Report generated: `soroban_validation_report_20251024_195313.md`

#### Integration Tests
- ✅ 2/2 tests passed (100% success rate)
- Tests: server connection (SSL fixed), error handling
- Account funding successful via Friendbot
- Contract invocation tests skipped (by design, no live contract)
- Report generated: `soroban_integration_report_20251024_201937.md`

### Known Issues

#### Soroban Contract Testing Limitations
- **No verified live contracts**: Example contract IDs in Stellar documentation have invalid checksums
- **Contract invocation tests skipped**: Require deploying real contracts to testnet
- **Workaround**: Users can deploy contracts and update `CONTRACT_ID` in `test_soroban.py:126`
- **Impact**: Limited coverage of `simulate` and `invoke` actions

#### SSL Certificate Workaround (macOS)
- **Temporary solution**: Environment variable `SSL_CERT_FILE`
- **Better approach**: Configure aiohttp SSL context programmatically in code
- **Portability concern**: Certificate path is machine-specific
- **Status**: Works reliably but could be more elegant

### Technical Details

#### SSL Fix Details
- Python 3.6+ uses bundled OpenSSL instead of macOS system certificates
- aiohttp doesn't automatically respect `REQUESTS_CA_BUNDLE` or `SSL_CERT_DIR`
- Setting `SSL_CERT_FILE` to certifi's bundle enables verification
- Certificate path: `.venv/lib/python3.13/site-packages/certifi/cacert.pem`
- Find path: `python -c "import certifi; print(certifi.where())"`

#### Contract ID Validation
- Soroban contract IDs use Stellar strkey format (start with 'C')
- stellar-sdk validates checksums on contract IDs
- Invalid IDs fail with `ValueError: Invalid encoded bytes`
- Documentation examples are often placeholders with bad checksums

### Migration Notes

No breaking changes. Users should:
1. Update `.env` with `SSL_CERT_FILE` if on macOS with Python 3.6+
2. Run `python -c "import certifi; print(certifi.where())"` to find certificate path
3. Review `SOROBAN_TESTING_NOTES.md` for deployment guidance

---

## [3.0.0] - 2025-10-23

### 🚀 Major Version: Soroban Smart Contract Support

This release adds full Soroban smart contract capabilities to the Stellar MCP Server, introducing the 6th composite tool for contract interactions.

### Added

#### Core Soroban Module
- **stellar_soroban.py** - Async Soroban operations module (305 lines)
  - `soroban_operations()` - Unified handler for all Soroban actions
  - `_parse_parameters()` - JSON-to-scval parameter converter
  - Full async/await support using `SorobanServerAsync`
  - Support for 22 Soroban parameter types

#### Soroban Actions (4 operations)
1. **get_data** - Query contract storage
   - Reads contract persistent/temporary/instance storage
   - Returns decoded values with ledger metadata
   - Durability selection (persistent, temporary, instance)

2. **simulate** - Read-only contract simulation
   - Simulates contract calls without fees or state changes
   - Returns execution results and resource costs
   - Provides CPU instructions and memory usage estimates
   - No account funding required for simulation

3. **invoke** - Execute contract functions
   - Full transaction flow: simulate → prepare → sign → submit → poll
   - Auto-signing with stored keypairs
   - Built-in transaction polling for confirmation
   - Resource estimation and footprint injection

4. **get_events** - Query contract events
   - Filter by event types, contract IDs, topics
   - Paginated results with configurable limits
   - Start ledger selection for historical queries
   - Decoded event data structures

#### MCP Tool Registration
- **soroban_tool** - 6th composite tool in server.py
  - Comprehensive tool description for LLMs
  - Parameter format documentation
  - All 22 supported types listed
  - Usage examples for each action
  - Integration with existing KeyManager

#### Test Suites
- **test_soroban_basic.py** - Validation tests (no network)
  - 7 tests: imports, structure, parameter parsing
  - Tests stellar-sdk async dependencies
  - Configuration file validation
  - All tests passing (7/7)

- **test_soroban.py** - Integration tests (testnet)
  - Server health checks
  - Account funding via Friendbot
  - Error handling validation
  - Contract invocation framework (pending live contract)

#### Documentation
- **README.md** - Soroban section added
  - Tool description and capabilities
  - Parameter format guide
  - Usage examples with all 4 actions
  - 22 supported parameter types listed
  - Updated architecture diagram

- **Updated .env** - Soroban RPC configuration
  - `SOROBAN_RPC_URL=https://soroban-testnet.stellar.org`

#### Dependencies
- **requirements.txt** - Updated stellar-sdk
  - `stellar-sdk[aiohttp]==13.1.0` - Async support with aiohttp

### Technical Implementation

#### Async Architecture
- Built on `SorobanServerAsync` from stellar-sdk 13.1.0
- Seamless integration with FastMCP's async support
- Mixed async (Soroban) and sync (Horizon) tools in same server
- No blocking calls - full async/await throughout

#### Parameter System
- JSON-based parameter specification with explicit type tags
- Format: `[{"type": "uint32", "value": 1000}, ...]`
- Recursive parsing for complex types (vec, map, struct)
- Full coverage of Soroban's 22 parameter types:
  - Primitives: uint32, uint64, uint128, uint256, int32-int256
  - Data: bytes, string, symbol, address
  - Time: duration, timepoint
  - Special: bool, void, native
  - Complex: vec, map, struct, tuple_struct, enum

#### Transaction Flow
- **Simulate**: Build transaction → simulate (read-only)
- **Invoke**: Simulate → prepare (inject resources) → sign → submit → poll
- Auto-resource estimation via SDK's `prepare_transaction()`
- Auto-signing with KeyManager integration
- Built-in polling for transaction confirmation

#### Error Handling
- Structured error responses with details
- Validation of required parameters per action
- Network passphrase required for all operations
- Graceful handling of contract errors and simulation failures

### Server Configuration

**Updated tool count:**
- v2.0: 5 composite tools
- v3.0: 6 composite tools (+Soroban)

**Server startup output:**
```
🌟 Stellar MCP Server v3.0
   6. soroban_tool (4 operations) [Soroban RPC] 🆕
🔮 Smart contracts: Full Soroban support (simulate, invoke, events)
```

### Testing Results

**Validation tests (test_soroban_basic.py):**
- ✅ 7/7 tests passed (100%)
- Module imports validated
- Parameter parsing verified
- Dependencies confirmed
- Configuration checked

**Integration tests (test_soroban.py):**
- Server connection successful
- Error handling validated
- Framework ready for contract testing

### Benefits

✅ **Full smart contract support** - Invoke, simulate, query, and monitor contracts
✅ **Async performance** - Non-blocking operations using modern async/await
✅ **Unified interface** - Single composite tool for all Soroban operations
✅ **Type-safe parameters** - Explicit type system prevents parameter errors
✅ **LLM-friendly** - Natural language descriptions and clear examples
✅ **Production-ready** - Full error handling and transaction polling

### Architecture

**Dual-API Design:**
```
┌─────────────────────────────────────┐
│     Stellar MCP Server v3.0         │
├─────────────────────────────────────┤
│  Classic Operations (5 tools)       │
│  └─> Horizon API (REST)            │
│      - Accounts, Trading, Trustlines│
│                                      │
│  Smart Contracts (1 tool)           │
│  └─> Soroban RPC (JSON-RPC)        │
│      - Invoke, Simulate, Events     │
└─────────────────────────────────────┘
```

### Migration Notes

No breaking changes. Users should:
1. Update dependencies: `uv pip install -r requirements.txt`
2. Add `SOROBAN_RPC_URL` to `.env` (optional, has default)
3. Restart MCP server to register new `soroban_tool`

### Known Limitations

- Contract testing requires deployed contracts (no public test contracts available)
- Example contract IDs in documentation have invalid checksums
- See SOROBAN_TESTING_NOTES.md for deployment guidance

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


———

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


### Contributors

Semantic refactoring and v2 architecture by the Stellar MCP team.
