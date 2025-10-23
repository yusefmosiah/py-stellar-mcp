"""
Stellar blockchain tool implementations for MCP server.
All tools are stateless except for keypair retrieval.
"""

from stellar_sdk import (
    Server,
    TransactionBuilder,
    Keypair,
    Network,
    Asset,
    TransactionEnvelope,
    Account
)
import requests
from key_manager import KeyManager

# Constants
TESTNET_NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
FRIENDBOT_URL = "https://friendbot.stellar.org"


def _dict_to_asset(asset_dict: dict) -> Asset:
    """
    Convert asset dict to Stellar SDK Asset object

    Args:
        asset_dict: {"type": "native"} or {"code": "USDC", "issuer": "G..."}

    Returns:
        Asset object for use in SDK operations
    """
    if asset_dict.get("type") == "native":
        return Asset.native()
    return Asset(asset_dict["code"], asset_dict["issuer"])


# ============================================================================
# ACCOUNT MANAGEMENT TOOLS
# ============================================================================

def create_account(key_manager: KeyManager) -> dict:
    """
    Generate new testnet account and store keypair securely.
    Account is created but unfunded - use fund_account() to activate.

    Args:
        key_manager: KeyManager instance

    Returns:
        {"account_id": "G...", "message": "..."}
    """
    try:
        keypair = Keypair.random()
        account_id = keypair.public_key
        key_manager.store(account_id, keypair.secret)

        return {
            "account_id": account_id,
            "message": "Account created (unfunded). Use fund_account() to activate on testnet."
        }
    except Exception as e:
        return {"error": str(e)}


def fund_account(account_id: str, horizon: Server) -> dict:
    """
    Fund testnet account via Friendbot.
    Only works on testnet - will fail on mainnet.

    Args:
        account_id: Stellar public key (G...)
        horizon: Horizon server instance

    Returns:
        {"success": true, "balance": "10000.0000000", ...}
    """
    try:
        # Request funding from Friendbot
        response = requests.get(f"{FRIENDBOT_URL}?addr={account_id}", timeout=10)
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
            "message": "Account funded successfully with testnet XLM"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Friendbot request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_account(account_id: str, horizon: Server) -> dict:
    """
    Get account details including balances, sequence, and trustlines

    Args:
        account_id: Stellar public key (G...)
        horizon: Horizon server instance

    Returns:
        {"account_id": "G...", "balances": [...], "sequence": "...", ...}
    """
    try:
        account = horizon.accounts().account_id(account_id).call()
        return {
            "account_id": account_id,
            "sequence": account["sequence"],
            "balances": account["balances"],
            "signers": account["signers"],
            "thresholds": account["thresholds"],
            "flags": account.get("flags", {})
        }
    except Exception as e:
        return {"error": str(e)}


def get_transactions(account_id: str, horizon: Server, limit: int = 10) -> dict:
    """
    Get transaction history for account

    Args:
        account_id: Stellar public key (G...)
        horizon: Horizon server instance
        limit: Number of transactions to retrieve (default: 10)

    Returns:
        {"transactions": [...]}
    """
    try:
        transactions = (
            horizon.transactions()
            .for_account(account_id)
            .limit(limit)
            .order(desc=True)
            .call()
        )

        return {
            "transactions": [
                {
                    "hash": tx["hash"],
                    "ledger": tx["ledger"],
                    "created_at": tx["created_at"],
                    "source_account": tx["source_account"],
                    "fee_charged": tx["fee_charged"],
                    "operation_count": tx["operation_count"],
                    "successful": tx["successful"]
                }
                for tx in transactions["_embedded"]["records"]
            ]
        }
    except Exception as e:
        return {"error": str(e)}


def list_accounts(key_manager: KeyManager) -> dict:
    """
    List all account public keys managed by this server

    Args:
        key_manager: KeyManager instance

    Returns:
        {"accounts": ["G...", "G..."]}
    """
    try:
        accounts = key_manager.list_accounts()
        return {
            "accounts": accounts,
            "count": len(accounts)
        }
    except Exception as e:
        return {"error": str(e)}


def export_keypair(account_id: str, key_manager: KeyManager) -> dict:
    """
    Export secret key for backup/migration.
    DANGEROUS - use with extreme caution!

    Args:
        account_id: Stellar public key (G...)
        key_manager: KeyManager instance

    Returns:
        {"account_id": "G...", "secret_key": "S..."}
    """
    try:
        secret_key = key_manager.export_secret(account_id)
        return {
            "account_id": account_id,
            "secret_key": secret_key,
            "warning": "Keep this secret key secure! Anyone with this key can control your account."
        }
    except Exception as e:
        return {"error": str(e)}


def import_keypair(secret_key: str, key_manager: KeyManager) -> dict:
    """
    Import existing keypair into server storage

    Args:
        secret_key: Stellar secret key (S...)
        key_manager: KeyManager instance

    Returns:
        {"account_id": "G...", "message": "..."}
    """
    try:
        account_id = key_manager.import_keypair(secret_key)
        return {
            "account_id": account_id,
            "message": "Keypair imported successfully"
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# TRUSTLINE MANAGEMENT TOOLS
# ============================================================================

def establish_trustline(
    account_id: str,
    asset: dict,
    key_manager: KeyManager,
    horizon: Server,
    limit: str = None
) -> dict:
    """
    Establish trustline to enable holding/trading an issued asset.
    Required before receiving non-XLM assets.

    Args:
        account_id: Stellar public key (G...)
        asset: {"code": "USDC", "issuer": "G..."}
        key_manager: KeyManager instance
        horizon: Horizon server instance
        limit: Optional trust limit (None = maximum)

    Returns:
        {"success": true, "hash": "...", "ledger": 123}
    """
    try:
        keypair = key_manager.get_keypair(account_id)
        asset_obj = _dict_to_asset(asset)

        # Build trustline transaction
        account = horizon.load_account(account_id)
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

        # Submit transaction
        response = horizon.submit_transaction(tx)
        return {
            "success": response.get("successful", False),
            "hash": response.get("hash"),
            "ledger": response.get("ledger"),
            "message": f"Trustline established for {asset.get('code', 'asset')}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def remove_trustline(
    account_id: str,
    asset: dict,
    key_manager: KeyManager,
    horizon: Server
) -> dict:
    """
    Remove trustline for an asset.
    Requires zero balance of that asset.

    Args:
        account_id: Stellar public key (G...)
        asset: {"code": "USDC", "issuer": "G..."}
        key_manager: KeyManager instance
        horizon: Horizon server instance

    Returns:
        {"success": true, "hash": "...", "ledger": 123}
    """
    try:
        keypair = key_manager.get_keypair(account_id)
        asset_obj = _dict_to_asset(asset)

        # Build remove trustline transaction (limit = "0")
        account = horizon.load_account(account_id)
        tx_builder = TransactionBuilder(
            source_account=account,
            network_passphrase=TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )

        tx_builder.append_change_trust_op(
            asset=asset_obj,
            limit="0"
        )

        tx = tx_builder.build()
        tx.sign(keypair)

        # Submit transaction
        response = horizon.submit_transaction(tx)
        return {
            "success": response.get("successful", False),
            "hash": response.get("hash"),
            "ledger": response.get("ledger"),
            "message": f"Trustline removed for {asset.get('code', 'asset')}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# SDEX TRADING TOOLS
# ============================================================================

def build_order_transaction(
    account_id: str,
    buy_or_sell: str,
    selling_asset: dict,
    buying_asset: dict,
    amount: str,
    price: str,
    horizon: Server
) -> dict:
    """
    Build unsigned order transaction for SDEX.
    Returns XDR for inspection before signing.

    Args:
        account_id: Stellar public key (G...)
        buy_or_sell: "buy" or "sell"
        selling_asset: {"type": "native"} or {"code": "USDC", "issuer": "G..."}
        buying_asset: {"type": "native"} or {"code": "USDC", "issuer": "G..."}
        amount: Decimal string (e.g., "100.50")
        price: Decimal string ratio (e.g., "1.5" = 1.5 buying per 1 selling)
        horizon: Horizon server instance

    Returns:
        {"xdr": "...", "tx_hash": "..."}
    """
    try:
        account = horizon.load_account(account_id)

        selling = _dict_to_asset(selling_asset)
        buying = _dict_to_asset(buying_asset)

        tx_builder = TransactionBuilder(
            source_account=account,
            network_passphrase=TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )

        if buy_or_sell.lower() == "buy":
            tx_builder.append_manage_buy_offer_op(
                selling=selling,
                buying=buying,
                amount=amount,
                price=price
            )
        elif buy_or_sell.lower() == "sell":
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
            "tx_hash": tx.hash().hex(),
            "message": f"Built {buy_or_sell} order transaction (unsigned)"
        }
    except Exception as e:
        return {"error": str(e)}


def sign_transaction(account_id: str, xdr: str, key_manager: KeyManager) -> dict:
    """
    Sign transaction XDR using stored keypair

    Args:
        account_id: Stellar public key (G...)
        xdr: Unsigned transaction XDR string
        key_manager: KeyManager instance

    Returns:
        {"signed_xdr": "..."}
    """
    try:
        keypair = key_manager.get_keypair(account_id)
        tx = TransactionEnvelope.from_xdr(xdr, TESTNET_NETWORK_PASSPHRASE)
        tx.sign(keypair)
        return {
            "signed_xdr": tx.to_xdr(),
            "message": "Transaction signed successfully"
        }
    except Exception as e:
        return {"error": str(e)}


def submit_transaction(signed_xdr: str, horizon: Server) -> dict:
    """
    Submit signed transaction to Stellar network

    Args:
        signed_xdr: Signed transaction XDR string
        horizon: Horizon server instance

    Returns:
        {"success": true, "hash": "...", "ledger": 123}
    """
    try:
        tx = TransactionEnvelope.from_xdr(signed_xdr, TESTNET_NETWORK_PASSPHRASE)
        response = horizon.submit_transaction(tx)
        return {
            "success": response.get("successful", False),
            "hash": response.get("hash"),
            "ledger": response.get("ledger"),
            "message": "Transaction submitted successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def cancel_order(
    account_id: str,
    offer_id: str,
    key_manager: KeyManager,
    horizon: Server
) -> dict:
    """
    Cancel open order on SDEX.
    Convenience method that builds, signs, and submits in one call.

    Args:
        account_id: Stellar public key (G...)
        offer_id: ID of offer to cancel
        key_manager: KeyManager instance
        horizon: Horizon server instance

    Returns:
        {"success": true, "hash": "...", "message": "..."}
    """
    try:
        keypair = key_manager.get_keypair(account_id)

        # Get offer details to know which assets to use
        offer = horizon.offers().offer(offer_id).call()

        selling = _dict_to_asset(offer["selling"])
        buying = _dict_to_asset(offer["buying"])

        # Build cancel transaction (amount = 0)
        account = horizon.load_account(account_id)
        tx_builder = TransactionBuilder(
            source_account=account,
            network_passphrase=TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )

        tx_builder.append_manage_sell_offer_op(
            selling=selling,
            buying=buying,
            amount="0",
            price=offer["price"],
            offer_id=int(offer_id)
        )

        tx = tx_builder.build()
        tx.sign(keypair)

        # Submit transaction
        response = horizon.submit_transaction(tx)
        return {
            "success": response.get("successful", False),
            "hash": response.get("hash"),
            "ledger": response.get("ledger"),
            "message": f"Order {offer_id} cancelled successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_orderbook(
    selling_asset: dict,
    buying_asset: dict,
    horizon: Server,
    limit: int = 20
) -> dict:
    """
    Fetch SDEX orderbook for asset pair

    Args:
        selling_asset: {"type": "native"} or {"code": "USDC", "issuer": "G..."}
        buying_asset: {"type": "native"} or {"code": "USDC", "issuer": "G..."}
        horizon: Horizon server instance
        limit: Number of orders per side (default: 20)

    Returns:
        {"bids": [...], "asks": [...], "base": {...}, "counter": {...}}
    """
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


def get_open_orders(account_id: str, horizon: Server) -> dict:
    """
    Get all open offers for an account

    Args:
        account_id: Stellar public key (G...)
        horizon: Horizon server instance

    Returns:
        {"offers": [{"id": "123", "selling": {...}, "buying": {...}, ...}]}
    """
    try:
        offers = horizon.offers().for_account(account_id).call()
        return {
            "offers": [
                {
                    "id": offer["id"],
                    "selling": offer["selling"],
                    "buying": offer["buying"],
                    "amount": offer["amount"],
                    "price": offer["price"],
                    "last_modified_ledger": offer["last_modified_ledger"]
                }
                for offer in offers["_embedded"]["records"]
            ],
            "count": len(offers["_embedded"]["records"])
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# UTILITY TOOLS
# ============================================================================

def get_server_status(horizon: Server) -> dict:
    """
    Get Horizon server status and health

    Args:
        horizon: Horizon server instance

    Returns:
        {"horizon_version": "...", "core_version": "...", "history_latest_ledger": 123}
    """
    try:
        root = horizon.root().call()
        return {
            "horizon_version": root.get("horizon_version"),
            "core_version": root.get("core_version"),
            "history_latest_ledger": root.get("history_latest_ledger"),
            "network_passphrase": root.get("network_passphrase")
        }
    except Exception as e:
        return {"error": str(e)}


def estimate_fee(horizon: Server) -> dict:
    """
    Get current network base fee estimate

    Args:
        horizon: Horizon server instance

    Returns:
        {"fee": "100", "unit": "stroops", "message": "..."}
    """
    try:
        fee_stats = horizon.fee_stats().call()
        return {
            "fee": fee_stats.get("last_ledger_base_fee", "100"),
            "unit": "stroops",
            "fee_charged_max": fee_stats.get("max_fee", {}).get("max"),
            "fee_charged_min": fee_stats.get("min_fee", {}).get("min"),
            "message": "Fee is dynamic. Use at least the base fee for transaction."
        }
    except Exception as e:
        return {"error": str(e)}
