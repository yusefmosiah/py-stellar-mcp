# Stellar MCP Server Refactoring Plan
**Goal**: Reduce tool count from 17 to 5-6 composite tools while maintaining flexibility

---

## Problems with Current Design

### 1. Token Overhead
- **17 individual tools** = ~3,000-5,000 tokens per tool definition
- Total: ~50,000-85,000 tokens consumed just for tool registration
- Context window bloat for every agent interaction

### 2. Multi-Step Workflows
```python
# Current: 3 tool calls to place an order
xdr = build_order_transaction_tool(...)
signed = sign_transaction_tool(account_id, xdr["xdr"])
result = submit_transaction_tool(signed["signed_xdr"])
```

### 3. Complex Parameter Passing
```python
# Current: 10 parameters for a simple buy order
build_order_transaction_tool(
    account_id="G...",
    buy_or_sell="buy",
    selling_asset_type="native",
    buying_asset_type="credit",
    amount="10",
    price="0.50",
    selling_asset_code=None,
    selling_asset_issuer=None,
    buying_asset_code="USDC",
    buying_asset_issuer="GBBD..."
)
```

### 4. No Abstraction Layer
- Agents must understand CLOB order mechanics
- No "market order" semantic - just price manipulation
- No "swap" semantic - must know selling/buying assets

---

## Proposed Architecture: Composite Tools

### New Tool Structure (5 tools instead of 17)

```python
1. account_manager(action, **kwargs)      # 7 operations → 1 tool
2. trading(action, **kwargs)              # 6 operations → 1 tool  
3. trustline_manager(action, **kwargs)    # 2 operations → 1 tool
4. market_data(action, **kwargs)          # 2 operations → 1 tool
5. utilities(action, **kwargs)            # 2 operations → 1 tool
```

**Token Savings**: ~50,000 tokens → ~15,000 tokens (70% reduction)

---

## Tool 1: Account Manager

**Consolidates**: 7 account operations into 1 tool

```python
@mcp.tool()
def account_manager(
    action: str,
    account_id: str = None,
    secret_key: str = None,
    limit: int = 10
) -> dict:
    """
    Unified account management tool for Stellar operations.
    
    Actions:
        - "create": Generate new testnet account
        - "fund": Fund account via Friendbot (testnet only)
        - "get": Get account details (balances, sequence, trustlines)
        - "transactions": Get transaction history
        - "list": List all managed accounts
        - "export": Export secret key (⚠️ dangerous!)
        - "import": Import existing keypair
    
    Args:
        action: Operation to perform
        account_id: Stellar public key (required for most actions)
        secret_key: Secret key (required only for "import")
        limit: Transaction limit (for "transactions" action)
    
    Returns:
        Action-specific response dict
    """
```

**Usage Examples:**
```python
# Create account
account_manager(action="create")
# {"account_id": "G...", "message": "..."}

# Fund account
account_manager(action="fund", account_id="G...")
# {"success": true, "balance": "10000.0000000"}

# Get account details
account_manager(action="get", account_id="G...")
# {"balances": [...], "sequence": "...", ...}

# Get transactions
account_manager(action="transactions", account_id="G...", limit=20)
# {"transactions": [...]}

# List all accounts
account_manager(action="list")
# {"accounts": ["G...", "G..."], "count": 2}

# Export keypair
account_manager(action="export", account_id="G...")
# {"secret_key": "S...", "warning": "..."}

# Import keypair
account_manager(action="import", secret_key="S...")
# {"account_id": "G...", "message": "..."}
```

---

## Tool 2: Trading

**Consolidates**: 6 trading operations + smart defaults

```python
@mcp.tool()
def trading(
    action: str,
    account_id: str,
    base_asset: str = "XLM",
    quote_asset: str = None,
    quote_issuer: str = None,
    amount: str = None,
    price: str = None,
    offer_id: str = None,
    auto_sign: bool = True
) -> dict:
    """
    Unified SDEX trading tool with smart defaults and high-level semantics.
    
    Actions:
        - "market_buy": Buy quote asset at market price
        - "market_sell": Sell quote asset at market price
        - "limit_buy": Place limit buy order
        - "limit_sell": Place limit sell order
        - "cancel": Cancel open order
        - "orders": Get open orders
    
    Args:
        action: Trading operation
        account_id: Stellar public key
        base_asset: Base asset code (default: "XLM" for native)
        quote_asset: Quote asset code (e.g., "USDC")
        quote_issuer: Quote asset issuer (required if quote_asset != "XLM")
        amount: Amount to buy/sell (decimal string)
        price: Price per unit (for limit orders)
        offer_id: Offer ID (for cancel action)
        auto_sign: Auto-sign and submit (default: True)
    
    Returns:
        {"success": bool, "hash": "...", "ledger": 123, ...}
    """
```

**Usage Examples:**
```python
# Market buy 10 USDC with XLM
trading(
    action="market_buy",
    account_id="G...",
    quote_asset="USDC",
    quote_issuer="GBBD...",
    amount="10"
)
# Internally: Sets price=0.0001 to cross the spread

# Market sell 5 USDC for XLM
trading(
    action="market_sell",
    account_id="G...",
    quote_asset="USDC",
    quote_issuer="GBBD...",
    amount="5"
)

# Limit buy 10 USDC at 0.50 XLM per USDC
trading(
    action="limit_buy",
    account_id="G...",
    quote_asset="USDC",
    quote_issuer="GBBD...",
    amount="10",
    price="0.50"
)

# Limit sell 5 USDC at 0.60 XLM per USDC
trading(
    action="limit_sell",
    account_id="G...",
    quote_asset="USDC",
    quote_issuer="GBBD...",
    amount="5",
    price="0.60"
)

# Cancel order
trading(
    action="cancel",
    account_id="G...",
    offer_id="12345"
)

# Get open orders
trading(
    action="orders",
    account_id="G..."
)
```

**Smart Defaults:**
- `base_asset="XLM"` assumes native XLM as base
- `auto_sign=True` automatically signs and submits
- `market_buy`/`market_sell` use aggressive pricing to cross spread
- Simplified asset parameters (no more `selling_asset_type`, `buying_asset_type`, etc.)

---

## Tool 3: Trustline Manager

**Consolidates**: 2 trustline operations

```python
@mcp.tool()
def trustline_manager(
    action: str,
    account_id: str,
    asset_code: str,
    asset_issuer: str,
    limit: str = None
) -> dict:
    """
    Manage trustlines for issued assets.
    
    Actions:
        - "establish": Create trustline (required before receiving assets)
        - "remove": Remove trustline (requires zero balance)
    
    Args:
        action: Trustline operation
        account_id: Stellar public key
        asset_code: Asset code (e.g., "USDC")
        asset_issuer: Asset issuer public key
        limit: Optional trust limit (default: maximum)
    
    Returns:
        {"success": bool, "hash": "...", "message": "..."}
    """
```

**Usage Examples:**
```python
# Establish trustline
trustline_manager(
    action="establish",
    account_id="G...",
    asset_code="USDC",
    asset_issuer="GBBD..."
)

# Remove trustline
trustline_manager(
    action="remove",
    account_id="G...",
    asset_code="USDC",
    asset_issuer="GBBD..."
)
```

---

## Tool 4: Market Data

**Consolidates**: 2 market data operations

```python
@mcp.tool()
def market_data(
    action: str,
    base_asset: str = "XLM",
    quote_asset: str = None,
    quote_issuer: str = None,
    limit: int = 20
) -> dict:
    """
    Query SDEX market data.
    
    Actions:
        - "orderbook": Get orderbook for asset pair
        - "trades": Get recent trades (future)
    
    Args:
        action: Market data query type
        base_asset: Base asset code (default: "XLM")
        quote_asset: Quote asset code
        quote_issuer: Quote asset issuer (if not XLM)
        limit: Number of results (default: 20)
    
    Returns:
        Action-specific market data
    """
```

**Usage Examples:**
```python
# Get USDC/XLM orderbook
market_data(
    action="orderbook",
    quote_asset="USDC",
    quote_issuer="GBBD...",
    limit=10
)
# {"bids": [...], "asks": [...], "base": {...}, "counter": {...}}
```

---

## Tool 5: Utilities

**Consolidates**: 2 utility operations

```python
@mcp.tool()
def utilities(action: str) -> dict:
    """
    Network utilities and server information.
    
    Actions:
        - "status": Get Horizon server status
        - "fee": Estimate current transaction fee
    
    Returns:
        Action-specific utility data
    """
```

**Usage Examples:**
```python
# Get server status
utilities(action="status")
# {"horizon_version": "...", "core_version": "..."}

# Estimate fee
utilities(action="fee")
# {"fee": "100", "unit": "stroops", ...}
```

---

## Implementation Strategy

### Phase 1: Create New Composite Tools (Without Breaking Old Ones)
1. Create `stellar_tools_v2.py` with composite implementations
2. Create `server_v2.py` registering only composite tools
3. Test composite tools in isolation
4. Verify all workflows work with new tools

### Phase 2: Deprecate Old Tools
1. Move old tools to `stellar_tools_legacy.py`
2. Update `server.py` to use v2 tools
3. Keep legacy tools available but hidden (optional)

### Phase 3: Documentation
1. Update `README.md` with new usage patterns
2. Create migration guide for agents
3. Add comparison table (old vs new)

---

## Benefits

### 1. Massive Token Savings
- **Before**: 17 tools × ~3,000 tokens = ~51,000 tokens
- **After**: 5 tools × ~3,000 tokens = ~15,000 tokens
- **Savings**: 70% reduction in context overhead

### 2. Simpler Agent Workflows
```python
# OLD: 3 calls for market buy
xdr = build_order_transaction_tool(...)
signed = sign_transaction_tool(...)
result = submit_transaction_tool(...)

# NEW: 1 call for market buy
trading(action="market_buy", account_id="G...", quote_asset="USDC", amount="10")
```

### 3. Better Semantics
- `market_buy` / `market_sell` instead of price manipulation
- Simplified asset parameters (no more `selling_asset_type`)
- Clearer action-based API

### 4. Backward Compatibility (Optional)
- Keep legacy tools available during migration
- Agents can adopt new tools gradually

---

## Migration Path for Agents

### Before (17 tools):
```python
# Create and fund account
account = create_account_tool()
fund_account_tool(account["account_id"])

# Setup trustline
establish_trustline_tool(account_id, "USDC", "GBBD...")

# Market buy USDC
xdr = build_order_transaction_tool(
    account_id, "buy", "native", "credit",
    "10", "0.0001", None, None, "USDC", "GBBD..."
)
signed = sign_transaction_tool(account_id, xdr["xdr"])
submit_transaction_tool(signed["signed_xdr"])
```

### After (5 tools):
```python
# Create and fund account
account = account_manager(action="create")
account_manager(action="fund", account_id=account["account_id"])

# Setup trustline
trustline_manager(action="establish", account_id=account_id, 
                 asset_code="USDC", asset_issuer="GBBD...")

# Market buy USDC (ONE CALL!)
trading(action="market_buy", account_id=account_id,
        quote_asset="USDC", quote_issuer="GBBD...", amount="10")
```

---

## Open Questions

1. **Should we keep low-level tools (build/sign/submit)?**
   - Pro: Maximum flexibility for advanced users
   - Con: Adds 3 more tools, reduces savings
   - **Recommendation**: Add `auto_sign=False` option in trading() instead

2. **Should we support batch operations?**
   - e.g., `trading(action="batch", orders=[...])`
   - **Recommendation**: Add in v3 if needed

3. **How to handle complex asset pairs (non-XLM base)?**
   - Current design assumes XLM base
   - **Recommendation**: Add `base_issuer` parameter for full flexibility

4. **Should market_buy/sell query orderbook first?**
   - Pro: More accurate pricing
   - Con: Slower, 2 Horizon calls per trade
   - **Recommendation**: Let agent query orderbook separately if needed

---

## Success Metrics

- ✅ **70% reduction in tool count** (17 → 5)
- ✅ **70% reduction in token overhead** (~51k → ~15k)
- ✅ **50% reduction in average workflow steps** (3-5 calls → 1-2 calls)
- ✅ **Maintain 100% functionality** (no features lost)
- ✅ **Zero breaking changes** (keep legacy tools available)

---

## Next Steps

1. Review this plan with stakeholders
2. Implement `stellar_tools_v2.py` 
3. Implement `server_v2.py`
4. Write comprehensive tests
5. Create migration guide
6. Deploy and monitor adoption

---

**Let's build a more efficient Stellar MCP server!** 🚀
