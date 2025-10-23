"""
Stellar Python MCP Server
FastMCP server exposing Stellar blockchain operations as MCP tools
"""

import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from stellar_sdk import Server

from key_manager import KeyManager
from stellar_tools import (
    create_account,
    fund_account,
    get_account,
    get_transactions,
    list_accounts,
    export_keypair,
    import_keypair,
    establish_trustline,
    remove_trustline,
    build_order_transaction,
    sign_transaction,
    submit_transaction,
    cancel_order,
    get_orderbook,
    get_open_orders,
    get_server_status,
    estimate_fee
)

# Load environment variables
load_dotenv()

# Configuration
HORIZON_URL = os.getenv("HORIZON_URL", "https://horizon-testnet.stellar.org")
STELLAR_NETWORK = os.getenv("STELLAR_NETWORK", "testnet")

# Initialize FastMCP server
mcp = FastMCP("Stellar MCP Server")

# Initialize Stellar SDK and KeyManager
horizon = Server(HORIZON_URL)
keys = KeyManager()

print(f"🚀 Stellar MCP Server")
print(f"📡 Network: {STELLAR_NETWORK}")
print(f"🌐 Horizon: {HORIZON_URL}")
print()


# ============================================================================
# ACCOUNT MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def create_account_tool() -> dict:
    """
    Generate new Stellar testnet account and store keypair securely.
    Account is created but unfunded - use fund_account_tool() to activate.

    Returns:
        {"account_id": "G...", "message": "..."}
    """
    return create_account(keys)


@mcp.tool()
def fund_account_tool(account_id: str) -> dict:
    """
    Fund testnet account using Friendbot.
    Only works on testnet - will fail on mainnet.

    Args:
        account_id: Stellar public key (G...)

    Returns:
        {"success": true, "balance": "10000.0000000", ...}
    """
    return fund_account(account_id, horizon)


@mcp.tool()
def get_account_tool(account_id: str) -> dict:
    """
    Get account details including balances, sequence, and trustlines.

    Args:
        account_id: Stellar public key (G...)

    Returns:
        {"account_id": "G...", "balances": [...], "sequence": "...", ...}
    """
    return get_account(account_id, horizon)


@mcp.tool()
def get_transactions_tool(account_id: str, limit: int = 10) -> dict:
    """
    Get transaction history for account.

    Args:
        account_id: Stellar public key (G...)
        limit: Number of transactions to retrieve (default: 10)

    Returns:
        {"transactions": [...]}
    """
    return get_transactions(account_id, horizon, limit)


@mcp.tool()
def list_accounts_tool() -> dict:
    """
    List all account public keys managed by this server.

    Returns:
        {"accounts": ["G...", "G..."], "count": 2}
    """
    return list_accounts(keys)


@mcp.tool()
def export_keypair_tool(account_id: str) -> dict:
    """
    Export secret key for backup/migration.
    ⚠️ DANGEROUS - use with extreme caution! Keep secret key secure.

    Args:
        account_id: Stellar public key (G...)

    Returns:
        {"account_id": "G...", "secret_key": "S...", "warning": "..."}
    """
    return export_keypair(account_id, keys)


@mcp.tool()
def import_keypair_tool(secret_key: str) -> dict:
    """
    Import existing keypair into server storage.

    Args:
        secret_key: Stellar secret key (S...)

    Returns:
        {"account_id": "G...", "message": "Keypair imported successfully"}
    """
    return import_keypair(secret_key, keys)


# ============================================================================
# TRUSTLINE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def establish_trustline_tool(
    account_id: str,
    asset_code: str,
    asset_issuer: str,
    limit: str = None
) -> dict:
    """
    Establish trustline to enable holding/trading an issued asset.
    Required before receiving non-XLM assets.

    Args:
        account_id: Stellar public key (G...)
        asset_code: Asset code (e.g., "USDC")
        asset_issuer: Asset issuer public key (G...)
        limit: Optional trust limit (None = maximum)

    Returns:
        {"success": true, "hash": "...", "ledger": 123}
    """
    asset = {"code": asset_code, "issuer": asset_issuer}
    return establish_trustline(account_id, asset, keys, horizon, limit)


@mcp.tool()
def remove_trustline_tool(
    account_id: str,
    asset_code: str,
    asset_issuer: str
) -> dict:
    """
    Remove trustline for an asset.
    Requires zero balance of that asset.

    Args:
        account_id: Stellar public key (G...)
        asset_code: Asset code (e.g., "USDC")
        asset_issuer: Asset issuer public key (G...)

    Returns:
        {"success": true, "hash": "...", "ledger": 123}
    """
    asset = {"code": asset_code, "issuer": asset_issuer}
    return remove_trustline(account_id, asset, keys, horizon)


# ============================================================================
# SDEX TRADING TOOLS
# ============================================================================

@mcp.tool()
def build_order_transaction_tool(
    account_id: str,
    buy_or_sell: str,
    selling_asset_type: str,
    buying_asset_type: str,
    amount: str,
    price: str,
    selling_asset_code: str = None,
    selling_asset_issuer: str = None,
    buying_asset_code: str = None,
    buying_asset_issuer: str = None
) -> dict:
    """
    Build unsigned order transaction for SDEX.
    Returns XDR for inspection before signing.

    Args:
        account_id: Stellar public key (G...)
        buy_or_sell: "buy" or "sell"
        selling_asset_type: "native" or "credit"
        buying_asset_type: "native" or "credit"
        amount: Decimal string (e.g., "100.50")
        price: Decimal string ratio (e.g., "1.5" = 1.5 buying per 1 selling)
        selling_asset_code: Required if selling_asset_type is "credit"
        selling_asset_issuer: Required if selling_asset_type is "credit"
        buying_asset_code: Required if buying_asset_type is "credit"
        buying_asset_issuer: Required if buying_asset_type is "credit"

    Returns:
        {"xdr": "...", "tx_hash": "...", "message": "..."}
    """
    # Build asset dicts
    if selling_asset_type == "native":
        selling_asset = {"type": "native"}
    else:
        selling_asset = {"code": selling_asset_code, "issuer": selling_asset_issuer}

    if buying_asset_type == "native":
        buying_asset = {"type": "native"}
    else:
        buying_asset = {"code": buying_asset_code, "issuer": buying_asset_issuer}

    return build_order_transaction(
        account_id, buy_or_sell, selling_asset, buying_asset, amount, price, horizon
    )


@mcp.tool()
def sign_transaction_tool(account_id: str, xdr: str) -> dict:
    """
    Sign transaction XDR using stored keypair.

    Args:
        account_id: Stellar public key (G...)
        xdr: Unsigned transaction XDR string

    Returns:
        {"signed_xdr": "...", "message": "..."}
    """
    return sign_transaction(account_id, xdr, keys)


@mcp.tool()
def submit_transaction_tool(signed_xdr: str) -> dict:
    """
    Submit signed transaction to Stellar network.

    Args:
        signed_xdr: Signed transaction XDR string

    Returns:
        {"success": true, "hash": "...", "ledger": 123}
    """
    return submit_transaction(signed_xdr, horizon)


@mcp.tool()
def cancel_order_tool(account_id: str, offer_id: str) -> dict:
    """
    Cancel open order on SDEX.
    Convenience method that builds, signs, and submits in one call.

    Args:
        account_id: Stellar public key (G...)
        offer_id: ID of offer to cancel

    Returns:
        {"success": true, "hash": "...", "message": "..."}
    """
    return cancel_order(account_id, offer_id, keys, horizon)


@mcp.tool()
def get_orderbook_tool(
    selling_asset_type: str,
    buying_asset_type: str,
    limit: int = 20,
    selling_asset_code: str = None,
    selling_asset_issuer: str = None,
    buying_asset_code: str = None,
    buying_asset_issuer: str = None
) -> dict:
    """
    Fetch SDEX orderbook for asset pair.

    Args:
        selling_asset_type: "native" or "credit"
        buying_asset_type: "native" or "credit"
        limit: Number of orders per side (default: 20)
        selling_asset_code: Required if selling_asset_type is "credit"
        selling_asset_issuer: Required if selling_asset_type is "credit"
        buying_asset_code: Required if buying_asset_type is "credit"
        buying_asset_issuer: Required if buying_asset_type is "credit"

    Returns:
        {"bids": [...], "asks": [...], "base": {...}, "counter": {...}}
    """
    # Build asset dicts
    if selling_asset_type == "native":
        selling_asset = {"type": "native"}
    else:
        selling_asset = {"code": selling_asset_code, "issuer": selling_asset_issuer}

    if buying_asset_type == "native":
        buying_asset = {"type": "native"}
    else:
        buying_asset = {"code": buying_asset_code, "issuer": buying_asset_issuer}

    return get_orderbook(selling_asset, buying_asset, horizon, limit)


@mcp.tool()
def get_open_orders_tool(account_id: str) -> dict:
    """
    Get all open offers for an account.

    Args:
        account_id: Stellar public key (G...)

    Returns:
        {"offers": [...], "count": 2}
    """
    return get_open_orders(account_id, horizon)


# ============================================================================
# UTILITY TOOLS
# ============================================================================

@mcp.tool()
def get_server_status_tool() -> dict:
    """
    Get Horizon server status and health.

    Returns:
        {"horizon_version": "...", "core_version": "...", "history_latest_ledger": 123}
    """
    return get_server_status(horizon)


@mcp.tool()
def estimate_fee_tool() -> dict:
    """
    Get current network base fee estimate.

    Returns:
        {"fee": "100", "unit": "stroops", "message": "..."}
    """
    return estimate_fee(horizon)


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("🔧 Registered tools:")
    print(f"   • Account Management: {len([f for f in dir() if 'account' in f.lower() and 'tool' in f])} tools")
    print(f"   • Trustline Management: {len([f for f in dir() if 'trustline' in f.lower() and 'tool' in f])} tools")
    print(f"   • SDEX Trading: {len([f for f in dir() if any(x in f.lower() for x in ['order', 'transaction']) and 'tool' in f])} tools")
    print(f"   • Utilities: {len([f for f in dir() if any(x in f.lower() for x in ['status', 'fee']) and 'tool' in f])} tools")
    print()
    print("✅ Starting MCP server...")
    print()

    mcp.run()
