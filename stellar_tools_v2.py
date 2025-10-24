"""
Stellar MCP Server - Composite Tools (v2)
Consolidated tool implementations reducing 17 tools to 5 composite tools.
"""

from stellar_sdk import (
    Server,
    TransactionBuilder,
    Keypair,
    Network,
    Asset,
    TransactionEnvelope,
)
import requests
from key_manager import KeyManager
from typing import Optional, Dict, Any
from decimal import Decimal

# Constants
TESTNET_NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
FRIENDBOT_URL = "https://friendbot.stellar.org"


def _dict_to_asset(asset_code: str, asset_issuer: Optional[str] = None) -> Asset:
    """Convert asset code/issuer to Stellar SDK Asset object"""
    if asset_code.upper() == "XLM" or asset_issuer is None:
        return Asset.native()
    return Asset(asset_code, asset_issuer)


def _calculate_market_fill(
    orderbook: Dict[str, Any],
    amount: str,
    side: str,  # "buy" or "sell"
    max_slippage: float = 0.05  # 5% default
) -> Dict[str, Any]:
    """
    Calculate market order fill details from orderbook data.

    This function works with orderbook(base, quote) semantics internally.
    The 'side' parameter indicates whether you're buying or selling the quote asset.

    Args:
        orderbook: Result from market_data(action="orderbook") for orderbook(base, quote)
        amount: Amount to trade (quote asset amount for side="buy", quote asset amount for side="sell")
        side: "buy" = buying quote asset with base; "sell" = selling quote asset for base
        max_slippage: Maximum allowed slippage (0.05 = 5%)

    Returns:
        {
            "feasible": bool,
            "fills": [{"price": "0.10", "amount": "100"}, ...],
            "total_filled": "150",
            "average_price": "0.1067",
            "best_price": "0.10",
            "worst_price": "0.12",
            "slippage": 0.067,
            "total_cost": "16.0",
            "execution_price": "0.132",
            "error": None or "error message"
        }
    """
    try:
        # Get appropriate orderbook side
        # For orderbook(base, quote):
        #   - bids: offers to buy base (sell quote) - use these when we want to buy quote
        #   - asks: offers to sell base (buy quote) - use these when we want to sell quote
        levels = orderbook.get("bids" if side == "buy" else "asks", [])

        if not levels:
            return {
                "feasible": False,
                "error": "No liquidity available in orderbook"
            }

        # Parse amount
        target_amount = Decimal(amount)
        remaining = target_amount
        fills = []
        total_cost = Decimal(0)

        # Simulate filling through orderbook levels
        # NOTE: For orderbook(base, quote) prices are in quote/base
        # When buying quote: bids show quote available at quote/base price
        # When selling quote: asks show base available at quote/base price
        for level in levels:
            level_price = Decimal(level["price"])  # quote/base (e.g., USDC/XLM)
            level_amount = Decimal(level["amount"])  # Amount of asset being offered

            if side == "buy":
                # Buying quote (USDC): level_amount is quote (USDC) available
                fill_amount = min(remaining, level_amount)
                # Cost is in base (XLM) = fill_amount / price (to get XLM from USDC)
                # Actually: if price is USDC/XLM, to get USDC we pay: USDC / (USDC/XLM) = XLM
                # No wait: if I get fill_amount USDC at level_price USDC/XLM
                # I pay: fill_amount / level_price XLM
                fill_cost = fill_amount / level_price
            else:
                # Selling quote (USDC): level_amount is base (XLM) available
                # Convert to quote amount available: level_amount * level_price
                quote_available = level_amount * level_price
                fill_amount = min(remaining, quote_available)
                # Cost is in base (XLM) = fill_amount / price
                fill_cost = fill_amount / level_price

            fills.append({
                "price": str(level_price),
                "amount": str(fill_amount)
            })

            total_cost += fill_cost
            remaining -= fill_amount

            if remaining <= 0:
                break

        # Check if fully fillable
        if remaining > 0:
            return {
                "feasible": False,
                "partial_fill": str(target_amount - remaining),
                "requested": str(target_amount),
                "error": f"Insufficient liquidity: only {target_amount - remaining} available"
            }

        # Calculate statistics
        total_filled = target_amount
        # Average cost in base (XLM) per unit of quote (USDC)
        average_cost_per_unit = total_cost / total_filled  # XLM/USDC

        # Best price from orderbook is in quote/base (USDC/XLM)
        # Convert to base/quote (XLM/USDC) for comparison
        best_orderbook_price = Decimal(levels[0]["price"])  # USDC/XLM
        best_cost_per_unit = Decimal("1") / best_orderbook_price  # XLM/USDC

        # Calculate slippage: how much worse than best price
        slippage = (average_cost_per_unit - best_cost_per_unit) / best_cost_per_unit

        # Check slippage tolerance
        if slippage > Decimal(str(max_slippage)):
            return {
                "feasible": False,
                "average_price": str(average_cost_per_unit),
                "best_price": str(best_cost_per_unit),
                "slippage": float(slippage),
                "error": f"Slippage {slippage*100:.2f}% exceeds max {max_slippage*100:.2f}%"
            }

        # Determine execution price for Stellar operation
        # For manage_buy_offer(selling=XLM, buying=USDC), price is in XLM/USDC
        # Use worst fill + 10% buffer to ensure execution
        worst_orderbook_price = Decimal(fills[-1]["price"])  # USDC/XLM
        worst_cost_per_unit = Decimal("1") / worst_orderbook_price  # XLM/USDC
        execution_price = worst_cost_per_unit * Decimal("1.1")  # 10% buffer

        return {
            "feasible": True,
            "fills": fills,
            "total_filled": str(total_filled),
            "average_price": str(average_cost_per_unit),
            "best_price": str(best_cost_per_unit),
            "worst_price": str(worst_cost_per_unit),
            "slippage": float(slippage),
            "total_cost": str(total_cost),
            "execution_price": str(execution_price),
            "error": None
        }

    except Exception as e:
        return {
            "feasible": False,
            "error": f"Fill calculation error: {str(e)}"
        }


def _build_sign_submit(
    account_id: str,
    operations: list,
    key_manager: KeyManager,
    horizon: Server,
    auto_sign: bool = True
) -> Dict[str, Any]:
    """
    Unified transaction flow: build → sign → submit
    
    Args:
        account_id: Stellar public key
        operations: List of operation callbacks
        key_manager: KeyManager instance
        horizon: Horizon server instance
        auto_sign: If True, automatically sign and submit

    Returns:
        Transaction result or unsigned XDR if auto_sign=False
    """
    try:
        account = horizon.load_account(account_id)
        tx_builder = TransactionBuilder(
            source_account=account,
            network_passphrase=TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )
        
        # Add all operations
        for op in operations:
            op(tx_builder)
        
        tx = tx_builder.build()
        
        if not auto_sign:
            return {
                "xdr": tx.to_xdr(),
                "tx_hash": tx.hash().hex(),
                "message": "Transaction built (unsigned). Call with auto_sign=True to submit."
            }
        
        # Sign and submit
        keypair = key_manager.get_keypair(account_id)
        tx.sign(keypair)
        response = horizon.submit_transaction(tx)
        
        return {
            "success": response.get("successful", False),
            "hash": response.get("hash"),
            "ledger": response.get("ledger"),
            "message": "Transaction submitted successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# COMPOSITE TOOL 1: ACCOUNT MANAGER
# ============================================================================

def account_manager(
    action: str,
    key_manager: KeyManager,
    horizon: Server,
    account_id: Optional[str] = None,
    secret_key: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Unified account management tool consolidating 7 operations.
    
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
        key_manager: KeyManager instance
        horizon: Horizon server instance
        account_id: Stellar public key (required for most actions)
        secret_key: Secret key (required only for "import")
        limit: Transaction limit (for "transactions" action)
    
    Returns:
        Action-specific response dict
    """
    try:
        if action == "create":
            keypair = Keypair.random()
            account_id = keypair.public_key
            key_manager.store(account_id, keypair.secret)
            return {
                "account_id": account_id,
                "message": "Account created (unfunded). Use action='fund' to activate."
            }
        
        elif action == "fund":
            if not account_id:
                return {"error": "account_id required for 'fund' action"}
            
            response = requests.get(f"{FRIENDBOT_URL}?addr={account_id}", timeout=10)
            response.raise_for_status()
            
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
        
        elif action == "get":
            if not account_id:
                return {"error": "account_id required for 'get' action"}
            
            account = horizon.accounts().account_id(account_id).call()
            return {
                "account_id": account_id,
                "sequence": account["sequence"],
                "balances": account["balances"],
                "signers": account["signers"],
                "thresholds": account["thresholds"],
                "flags": account.get("flags", {})
            }
        
        elif action == "transactions":
            if not account_id:
                return {"error": "account_id required for 'transactions' action"}
            
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
        
        elif action == "list":
            accounts = key_manager.list_accounts()
            return {
                "accounts": accounts,
                "count": len(accounts)
            }
        
        elif action == "export":
            if not account_id:
                return {"error": "account_id required for 'export' action"}
            
            secret_key = key_manager.export_secret(account_id)
            return {
                "account_id": account_id,
                "secret_key": secret_key,
                "warning": "Keep this secret key secure! Anyone with this key can control your account."
            }
        
        elif action == "import":
            if not secret_key:
                return {"error": "secret_key required for 'import' action"}
            
            account_id = key_manager.import_keypair(secret_key)
            return {
                "account_id": account_id,
                "message": "Keypair imported successfully"
            }
        
        else:
            return {
                "error": f"Unknown action: {action}",
                "valid_actions": ["create", "fund", "get", "transactions", "list", "export", "import"]
            }
    
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# COMPOSITE TOOL 2: TRADING
# ============================================================================

def trading(
    action: str,
    account_id: str,
    key_manager: KeyManager,
    horizon: Server,
    buying_asset: Optional[str] = None,
    selling_asset: Optional[str] = None,
    buying_issuer: Optional[str] = None,
    selling_issuer: Optional[str] = None,
    amount: Optional[str] = None,
    price: Optional[str] = None,
    order_type: str = "limit",
    offer_id: Optional[str] = None,
    max_slippage: float = 0.05,
    auto_sign: bool = True
) -> Dict[str, Any]:
    """
    Unified SDEX trading tool with intuitive buying/selling semantics.

    Actions:
        - "buy": Acquire buying_asset by spending selling_asset
        - "sell": Give up selling_asset to acquire buying_asset
        - "cancel_order": Cancel an open order
        - "get_orders": Get all open orders

    Args:
        action: Trading operation ("buy", "sell", "cancel_order", "get_orders")
        account_id: Stellar public key
        key_manager: KeyManager instance
        horizon: Horizon server instance
        buying_asset: Asset you want to acquire (e.g., "USDC")
        selling_asset: Asset you're spending (e.g., "XLM")
        buying_issuer: Issuer of buying_asset (required if buying_asset != "XLM")
        selling_issuer: Issuer of selling_asset (required if selling_asset != "XLM")
        amount: For buy: amount of buying_asset to acquire; For sell: amount of selling_asset to spend
        price: Price (for limit orders). For buy: selling_asset per buying_asset. For sell: buying_asset per selling_asset
        order_type: "limit" or "market" (default: "limit")
        offer_id: Offer ID (for cancel_order action)
        max_slippage: Maximum slippage tolerance for market orders (default: 0.05 = 5%)
        auto_sign: Auto-sign and submit (default: True)

    Returns:
        {"success": bool, "hash": "...", "ledger": 123, "market_execution": {...}}

    Examples:
        # Buy 4 USDC by spending XLM at market price:
        trading(action="buy", buying_asset="USDC", selling_asset="XLM",
                amount="4", order_type="market", ...)

        # Place limit order to buy 4 USDC, willing to pay 15 XLM per USDC:
        trading(action="buy", buying_asset="USDC", selling_asset="XLM",
                amount="4", price="15", order_type="limit", ...)

        # Sell 100 XLM for USDC, wanting 0.01 USDC per XLM:
        trading(action="sell", selling_asset="XLM", buying_asset="USDC",
                amount="100", price="0.01", order_type="limit", ...)
    """
    try:
        if action == "get_orders":
            # Get open orders
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

        elif action == "cancel_order":
            if not offer_id:
                return {"error": "offer_id required for 'cancel_order' action"}

            # Get offer details
            offer = horizon.offers().offer(offer_id).call()

            selling = Asset(offer["selling"]["asset_code"], offer["selling"]["asset_issuer"]) \
                if offer["selling"]["asset_type"] != "native" else Asset.native()
            buying = Asset(offer["buying"]["asset_code"], offer["buying"]["asset_issuer"]) \
                if offer["buying"]["asset_type"] != "native" else Asset.native()

            def cancel_op(builder):
                builder.append_manage_sell_offer_op(
                    selling=selling,
                    buying=buying,
                    amount="0",
                    price=offer["price"],
                    offer_id=int(offer_id)
                )

            result = _build_sign_submit(account_id, [cancel_op], key_manager, horizon, auto_sign)
            if result.get("success"):
                result["message"] = f"Order {offer_id} cancelled successfully"
            return result

        elif action in ["buy", "sell"]:
            # Validate inputs
            if not buying_asset or not selling_asset:
                return {"error": "Both buying_asset and selling_asset required for trading"}
            if not amount:
                return {"error": "amount required for trading"}
            if order_type == "limit" and not price:
                return {"error": "price required for limit orders"}

            # Build asset objects
            buying = _dict_to_asset(buying_asset, buying_issuer)
            selling = _dict_to_asset(selling_asset, selling_issuer)

            # Determine orderbook orientation for market orders
            # Convention: XLM is base when paired with issued assets
            if order_type == "market":
                # Determine base and quote for orderbook query
                if selling_asset.upper() == "XLM":
                    base_asset = selling_asset
                    quote_asset = buying_asset
                    quote_issuer_val = buying_issuer
                    # User wants to buy quote (buying_asset) by selling base (selling_asset)
                    orderbook_side = "buy"
                elif buying_asset.upper() == "XLM":
                    base_asset = buying_asset
                    quote_asset = selling_asset
                    quote_issuer_val = selling_issuer
                    # User wants to sell quote (selling_asset) to get base (buying_asset)
                    orderbook_side = "sell"
                else:
                    # Both are issued assets - use alphabetical order
                    if buying_asset < selling_asset:
                        base_asset = buying_asset
                        quote_asset = selling_asset
                        quote_issuer_val = selling_issuer
                        orderbook_side = "sell"
                    else:
                        base_asset = selling_asset
                        quote_asset = buying_asset
                        quote_issuer_val = buying_issuer
                        orderbook_side = "buy"

                # STEP 1: Query orderbook
                orderbook_result = market_data(
                    action="orderbook",
                    horizon=horizon,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    quote_issuer=quote_issuer_val,
                    limit=20
                )

                if "error" in orderbook_result:
                    return {"error": f"Failed to fetch orderbook: {orderbook_result['error']}"}

                # STEP 2: Calculate fill strategy
                fill_calc = _calculate_market_fill(
                    orderbook=orderbook_result,
                    amount=amount,
                    side=orderbook_side,
                    max_slippage=max_slippage
                )

                if not fill_calc.get("feasible"):
                    return {
                        "success": False,
                        "error": fill_calc.get("error"),
                        "market_data": fill_calc
                    }

                price_value = fill_calc["execution_price"]
            else:
                # Limit order - use user-provided price
                price_value = price

            # STEP 3: Execute transaction
            # For action="buy": use manage_buy_offer (amount is buying_asset amount)
            # For action="sell": use manage_sell_offer (amount is selling_asset amount)
            def trade_op(builder):
                if action == "buy":
                    builder.append_manage_buy_offer_op(
                        selling=selling,
                        buying=buying,
                        amount=amount,
                        price=price_value
                    )
                else:  # action == "sell"
                    builder.append_manage_sell_offer_op(
                        selling=selling,
                        buying=buying,
                        amount=amount,
                        price=price_value
                    )

            result = _build_sign_submit(account_id, [trade_op], key_manager, horizon, auto_sign)

            # Add market execution details for market orders
            if result.get("success") and order_type == "market":
                result["market_execution"] = {
                    "requested_amount": amount,
                    "expected_average_price": fill_calc["average_price"],
                    "best_price": fill_calc["best_price"],
                    "execution_price": fill_calc["execution_price"],
                    "slippage": fill_calc["slippage"],
                    "total_cost_estimate": fill_calc["total_cost"],
                    "fills": fill_calc["fills"]
                }

            return result

        else:
            return {
                "error": f"Unknown action: {action}",
                "valid_actions": ["buy", "sell", "cancel_order", "get_orders"]
            }
    
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# COMPOSITE TOOL 3: TRUSTLINE MANAGER
# ============================================================================

def trustline_manager(
    action: str,
    account_id: str,
    asset_code: str,
    asset_issuer: str,
    key_manager: KeyManager,
    horizon: Server,
    limit: Optional[str] = None
) -> Dict[str, Any]:
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
        key_manager: KeyManager instance
        horizon: Horizon server instance
        limit: Optional trust limit (default: maximum)
    
    Returns:
        {"success": bool, "hash": "...", "message": "..."}
    """
    try:
        asset = Asset(asset_code, asset_issuer)
        
        def trustline_op(builder):
            if action == "establish":
                builder.append_change_trust_op(asset=asset, limit=limit)
            elif action == "remove":
                builder.append_change_trust_op(asset=asset, limit="0")
            else:
                raise ValueError(f"Unknown action: {action}")
        
        result = _build_sign_submit(account_id, [trustline_op], key_manager, horizon, auto_sign=True)
        
        if result.get("success"):
            result["message"] = f"Trustline {'established' if action == 'establish' else 'removed'} for {asset_code}"
        
        return result
    
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# COMPOSITE TOOL 4: MARKET DATA
# ============================================================================

def market_data(
    action: str,
    horizon: Server,
    base_asset: str = "XLM",
    quote_asset: Optional[str] = None,
    quote_issuer: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Query SDEX market data.
    
    Actions:
        - "orderbook": Get orderbook for asset pair
    
    Args:
        action: Market data query type
        horizon: Horizon server instance
        base_asset: Base asset code (default: "XLM")
        quote_asset: Quote asset code
        quote_issuer: Quote asset issuer (if not XLM)
        limit: Number of results (default: 20)
    
    Returns:
        Action-specific market data
    """
    try:
        if action == "orderbook":
            if not quote_asset:
                return {"error": "quote_asset required for orderbook query"}
            
            base = _dict_to_asset(base_asset)
            quote = _dict_to_asset(quote_asset, quote_issuer)
            
            orderbook = horizon.orderbook(base, quote).limit(limit).call()
            return {
                "bids": orderbook["bids"],
                "asks": orderbook["asks"],
                "base": orderbook["base"],
                "counter": orderbook["counter"]
            }
        
        else:
            return {
                "error": f"Unknown action: {action}",
                "valid_actions": ["orderbook"]
            }
    
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# COMPOSITE TOOL 5: UTILITIES
# ============================================================================

def utilities(action: str, horizon: Server) -> Dict[str, Any]:
    """
    Network utilities and server information.
    
    Actions:
        - "status": Get Horizon server status
        - "fee": Estimate current transaction fee
    
    Args:
        action: Utility operation
        horizon: Horizon server instance
    
    Returns:
        Action-specific utility data
    """
    try:
        if action == "status":
            root = horizon.root().call()
            return {
                "horizon_version": root.get("horizon_version"),
                "core_version": root.get("core_version"),
                "history_latest_ledger": root.get("history_latest_ledger"),
                "network_passphrase": root.get("network_passphrase")
            }
        
        elif action == "fee":
            fee_stats = horizon.fee_stats().call()
            return {
                "fee": fee_stats.get("last_ledger_base_fee", "100"),
                "unit": "stroops",
                "fee_charged_max": fee_stats.get("max_fee", {}).get("max"),
                "fee_charged_min": fee_stats.get("min_fee", {}).get("min"),
                "message": "Fee is dynamic. Use at least the base fee for transaction."
            }
        
        else:
            return {
                "error": f"Unknown action: {action}",
                "valid_actions": ["status", "fee"]
            }
    
    except Exception as e:
        return {"error": str(e)}
