"""
Stellar Python MCP Server
FastMCP server with consolidated tools (17 → 6)
Includes Horizon API + Soroban RPC support
"""

import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from stellar_sdk import Server, Network

from stellar_ssl import create_soroban_client_with_ssl
from key_manager import KeyManager
from stellar_tools import (
    account_manager,
    trading,
    trustline_manager,
    market_data,
    utilities
)
from stellar_soroban import soroban_operations

# Load environment variables
load_dotenv()

# Configuration
HORIZON_URL = os.getenv("HORIZON_URL", "https://horizon-testnet.stellar.org")
SOROBAN_RPC_URL = os.getenv("SOROBAN_RPC_URL", "https://soroban-testnet.stellar.org")
STELLAR_NETWORK = os.getenv("STELLAR_NETWORK", "testnet")
TESTNET_NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

# Initialize FastMCP server
mcp = FastMCP("Stellar MCP Server")

# Initialize Stellar SDK and KeyManager
horizon = Server(HORIZON_URL)
soroban = create_soroban_client_with_ssl(SOROBAN_RPC_URL)
keys = KeyManager()

print(f"🚀 Stellar MCP Server (Composite Tools)")
print(f"📡 Network: {STELLAR_NETWORK}")
print(f"🌐 Horizon: {HORIZON_URL}")
print(f"🔮 Soroban RPC: {SOROBAN_RPC_URL}")
print(f"🔧 Tool count: 6 composite tools (was 17)")
print()


# ============================================================================
# COMPOSITE TOOL 1: ACCOUNT MANAGER (7 operations → 1 tool)
# ============================================================================

@mcp.tool()
def account_manager_tool(
    action: str,
    account_id: str = None,
    secret_key: str = None,
    limit: int = 10
) -> dict:
    """
    Unified account management for Stellar operations.
    
    Actions:
        create - Generate new testnet account
        fund - Fund account via Friendbot (testnet only)
        get - Get account details (balances, sequence, trustlines)
        transactions - Get transaction history
        list - List all managed accounts
        export - Export secret key (⚠️ dangerous!)
        import - Import existing keypair
    
    Args:
        action: Operation to perform (see Actions above)
        account_id: Stellar public key (G...) - required for most actions
        secret_key: Secret key (S...) - required only for import action
        limit: Transaction limit for transactions action (default: 10)
    
    Examples:
        account_manager_tool(action="create")
        account_manager_tool(action="fund", account_id="G...")
        account_manager_tool(action="get", account_id="G...")
        account_manager_tool(action="list")
    
    Returns:
        Action-specific response dict with success/error status
    """
    return account_manager(
        action=action,
        key_manager=keys,
        horizon=horizon,
        account_id=account_id,
        secret_key=secret_key,
        limit=limit
    )


# ============================================================================
# COMPOSITE TOOL 2: TRADING (6 operations → 1 tool)
# ============================================================================

@mcp.tool()
def trading_tool(
    action: str,
    account_id: str,
    buying_asset: str = None,
    selling_asset: str = None,
    buying_issuer: str = None,
    selling_issuer: str = None,
    amount: str = None,
    price: str = None,
    order_type: str = "limit",
    offer_id: str = None,
    auto_sign: bool = True
) -> dict:
    """
    Intuitive SDEX trading with explicit buying/selling semantics.

    Actions:
        buy - Acquire buying_asset by spending selling_asset
        sell - Give up selling_asset to acquire buying_asset
        cancel_order - Cancel an open order by offer_id
        get_orders - Get all open orders for account

    Args:
        action: Trading operation (buy, sell, cancel_order, get_orders)
        account_id: Stellar public key (G...)
        buying_asset: Asset you want to acquire (e.g., "USDC")
        selling_asset: Asset you're spending (e.g., "XLM")
        buying_issuer: Issuer of buying_asset (required if buying_asset != "XLM")
        selling_issuer: Issuer of selling_asset (required if selling_asset != "XLM")
        amount: For buy: amount of buying_asset; For sell: amount of selling_asset
        price: Price for limit orders. For buy: selling_asset per buying_asset
        order_type: "limit" or "market" (default: "limit")
        offer_id: Offer ID for cancel_order action
        auto_sign: Auto-sign and submit transaction (default: True)

    Examples:
        # Market buy 4 USDC by spending XLM
        trading_tool(action="buy", order_type="market", account_id="G...",
                    buying_asset="USDC", selling_asset="XLM",
                    buying_issuer="GBBD...", amount="4")

        # Limit buy 4 USDC, willing to pay 15 XLM per USDC
        trading_tool(action="buy", order_type="limit", account_id="G...",
                    buying_asset="USDC", selling_asset="XLM",
                    buying_issuer="GBBD...", amount="4", price="15")

        # Sell 100 XLM for USDC, wanting 0.01 USDC per XLM
        trading_tool(action="sell", order_type="limit", account_id="G...",
                    selling_asset="XLM", buying_asset="USDC",
                    buying_issuer="GBBD...", amount="100", price="0.01")

        # Cancel order
        trading_tool(action="cancel_order", account_id="G...", offer_id="12345")

        # Get open orders
        trading_tool(action="get_orders", account_id="G...")

    Returns:
        {"success": bool, "hash": "...", "ledger": 123, "market_execution": {...}}
    """
    return trading(
        action=action,
        account_id=account_id,
        key_manager=keys,
        horizon=horizon,
        buying_asset=buying_asset,
        selling_asset=selling_asset,
        buying_issuer=buying_issuer,
        selling_issuer=selling_issuer,
        amount=amount,
        price=price,
        order_type=order_type,
        offer_id=offer_id,
        auto_sign=auto_sign
    )


# ============================================================================
# COMPOSITE TOOL 3: TRUSTLINE MANAGER (2 operations → 1 tool)
# ============================================================================

@mcp.tool()
def trustline_manager_tool(
    action: str,
    account_id: str,
    asset_code: str,
    asset_issuer: str,
    limit: str = None
) -> dict:
    """
    Manage trustlines for issued assets (required before receiving non-XLM assets).
    
    Actions:
        establish - Create trustline to enable holding/trading asset
        remove - Remove trustline (requires zero balance of asset)
    
    Args:
        action: Trustline operation (establish or remove)
        account_id: Stellar public key (G...)
        asset_code: Asset code (e.g., "USDC")
        asset_issuer: Asset issuer public key (G...)
        limit: Optional trust limit (default: maximum)
    
    Examples:
        # Establish USDC trustline
        trustline_manager_tool(action="establish", account_id="G...",
                              asset_code="USDC", asset_issuer="GBBD...")
        
        # Remove USDC trustline (requires 0 balance)
        trustline_manager_tool(action="remove", account_id="G...",
                              asset_code="USDC", asset_issuer="GBBD...")
    
    Returns:
        {"success": bool, "hash": "...", "message": "..."}
    """
    return trustline_manager(
        action=action,
        account_id=account_id,
        asset_code=asset_code,
        asset_issuer=asset_issuer,
        key_manager=keys,
        horizon=horizon,
        limit=limit
    )


# ============================================================================
# COMPOSITE TOOL 4: MARKET DATA (2 operations → 1 tool)
# ============================================================================

@mcp.tool()
def market_data_tool(
    action: str,
    base_asset: str = "XLM",
    quote_asset: str = None,
    quote_issuer: str = None,
    limit: int = 20
) -> dict:
    """
    Query SDEX market data for asset pairs.
    
    Actions:
        orderbook - Get bids/asks for asset pair
    
    Args:
        action: Market data query type (orderbook)
        base_asset: Base asset code (default: "XLM")
        quote_asset: Quote asset code (e.g., "USDC")
        quote_issuer: Quote asset issuer (required if quote_asset != "XLM")
        limit: Number of orders per side (default: 20)
    
    Examples:
        # Get USDC/XLM orderbook
        market_data_tool(action="orderbook", quote_asset="USDC",
                        quote_issuer="GBBD...", limit=10)
    
    Returns:
        {"bids": [...], "asks": [...], "base": {...}, "counter": {...}}
    """
    return market_data(
        action=action,
        horizon=horizon,
        base_asset=base_asset,
        quote_asset=quote_asset,
        quote_issuer=quote_issuer,
        limit=limit
    )


# ============================================================================
# COMPOSITE TOOL 5: UTILITIES (2 operations → 1 tool)
# ============================================================================

@mcp.tool()
def utilities_tool(action: str) -> dict:
    """
    Network utilities and server information.

    Actions:
        status - Get Horizon server status and health
        fee - Estimate current transaction fee

    Args:
        action: Utility operation (status or fee)

    Examples:
        utilities_tool(action="status")
        utilities_tool(action="fee")

    Returns:
        Action-specific utility data
    """
    return utilities(action=action, horizon=horizon)


# ============================================================================
# COMPOSITE TOOL 6: SOROBAN (4 operations → 1 tool)
# ============================================================================

@mcp.tool()
async def soroban_tool(
    action: str,
    contract_id: str = None,
    key: str = None,
    function_name: str = None,
    parameters: str = None,
    source_account: str = None,
    durability: str = "persistent",
    start_ledger: int = None,
    event_types: list = None,
    limit: int = 100,
    auto_sign: bool = True
) -> dict:
    """
    Unified Soroban smart contract operations tool.

    Actions:
        get_data - Read contract storage data directly
        simulate - Simulate contract call (read-only, no fees)
        invoke - Execute contract function (writes to blockchain)
        get_events - Query contract event history

    Args:
        action: Operation to perform (see Actions above)
        contract_id: Contract address (C...)
        key: Storage key for get_data action
        function_name: Contract function name for simulate/invoke
        parameters: JSON string of typed parameters (see Parameter Format)
        source_account: Caller's public key (G...)
        durability: Storage type for get_data ("persistent" or "temporary")
        start_ledger: Starting ledger for get_events
        event_types: Event type filters for get_events
        limit: Result limit for get_events (default: 100)
        auto_sign: Auto-sign and submit for invoke (default: True)

    Parameter Format:
        JSON string with type tags for all contract parameters:

        '[
            {"type": "address", "value": "GABC..."},
            {"type": "uint32", "value": 1000},
            {"type": "string", "value": "hello"},
            {"type": "symbol", "value": "token_name"},
            {"type": "vec", "value": [
                {"type": "uint32", "value": 1},
                {"type": "uint32", "value": 2}
            ]}
        ]'

    Supported Types:
        Primitives: address, bool, bytes, duration, int32, int64, int128,
                   int256, uint32, uint64, uint128, uint256
        Text: string, symbol
        Special: timepoint, void, native
        Complex: vec (array), map (dictionary), struct, tuple_struct, enum

    Examples:
        # Read contract storage
        soroban_tool(
            action="get_data",
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2KM",
            key="counter",
            durability="persistent"
        )

        # Simulate contract call (read-only)
        soroban_tool(
            action="simulate",
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2KM",
            function_name="get_balance",
            parameters='[{"type": "address", "value": "GABC..."}]',
            source_account="GABC..."
        )

        # Execute contract function (write)
        soroban_tool(
            action="invoke",
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2KM",
            function_name="transfer",
            parameters='[
                {"type": "address", "value": "GFROM..."},
                {"type": "address", "value": "GTO..."},
                {"type": "int128", "value": 1000000}
            ]',
            source_account="GFROM...",
            auto_sign=True
        )

        # Query contract events
        soroban_tool(
            action="get_events",
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2KM",
            start_ledger=1000000,
            limit=50
        )

    Returns:
        Action-specific response dict with success/error status
    """
    return await soroban_operations(
        action=action,
        soroban_server=soroban,
        key_manager=keys,
        contract_id=contract_id,
        key=key,
        function_name=function_name,
        parameters=parameters,
        source_account=source_account,
        durability=durability,
        start_ledger=start_ledger,
        event_types=event_types,
        limit=limit,
        auto_sign=auto_sign,
        network_passphrase=TESTNET_NETWORK_PASSPHRASE
    )


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("🔧 Registered composite tools:")
    print("   1. account_manager_tool (7 operations) [Horizon]")
    print("   2. trading_tool (6 operations) [Horizon]")
    print("   3. trustline_manager_tool (2 operations) [Horizon]")
    print("   4. market_data_tool (2 operations) [Horizon]")
    print("   5. utilities_tool (2 operations) [Horizon]")
    print("   6. soroban_tool (4 operations) [Soroban RPC] 🆕")
    print()
    print("📊 Token savings: ~70% reduction vs previous version (17 tools)")
    print("⚡ Workflow simplification: 1-2 calls vs 3-5 calls")
    print("🔮 Smart contracts: Full Soroban support (simulate, invoke, events)")
    print()
    print("✅ Starting MCP server...")
    print()

    mcp.run()
