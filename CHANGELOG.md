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

## [Unreleased]

### Planned Features
- SDEX trading integration tests
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

- **0.1.0** (2025-10-23) - Initial release with core Stellar MCP functionality
