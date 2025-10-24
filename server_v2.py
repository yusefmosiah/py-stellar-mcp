"""
Stellar Python MCP Server (v2 - Composite Tools)
FastMCP server with consolidated tools (17 → 5)
"""

import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from stellar_sdk import Server

from key_manager import KeyManager
from stellar_tools_v2 import (
    account_manager,
    trading,
    trustline_manager,
    market_data,
    utilities
)

# Load environment variables
load_dotenv()

# Configuration
HORIZON_URL = os.getenv("HORIZON_URL", "https://horizon-testnet.stellar.org")
STELLAR_NETWORK = os.getenv("STELLAR_NETWORK", "testnet")

# Initialize FastMCP server
mcp = FastMCP("Stellar MCP Server v2")

# Initialize Stellar SDK and KeyManager
horizon = Server(HORIZON_URL)
keys = KeyManager()

print(f"🚀 Stellar MCP Server v2 (Composite Tools)")
print(f"📡 Network: {STELLAR_NETWORK}")
print(f"🌐 Horizon: {HORIZON_URL}")
print(f"🔧 Tool count: 5 composite tools (was 17)")
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
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("🔧 Registered composite tools:")
    print("   1. account_manager_tool (7 operations)")
    print("   2. trading_tool (6 operations)")
    print("   3. trustline_manager_tool (2 operations)")
    print("   4. market_data_tool (2 operations)")
    print("   5. utilities_tool (2 operations)")
    print()
    print("📊 Token savings: ~70% reduction vs v1 (17 tools)")
    print("⚡ Workflow simplification: 1-2 calls vs 3-5 calls")
    print()
    print("✅ Starting MCP server...")
    print()

    mcp.run()
