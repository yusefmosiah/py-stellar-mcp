# Market Order Architecture Issue & Solution

## Executive Summary

**Current Issue:** The `market_buy` and `market_sell` actions use hardcoded extreme prices (10000 / 0.0001) without querying the orderbook. This is a **semantic lie** - they're not true market orders, just limit orders with absurd prices that happen to cross the spread.

**Proposed Solution:** Implement proper market orders that:
1. Query orderbook to determine best available prices
2. Calculate expected fill prices and slippage
3. Support amount-based vs. total-based orders
4. Return realistic execution data
5. Fail gracefully when liquidity is insufficient

---

## Current Implementation Problems

### Problem 1: Hardcoded Prices (Not Market-Aware)

**Current Code (stellar_tools_v2.py lines 329-343):**

```python
if action == "market_buy":
    # Buy quote asset with base asset
    # Use very high price to cross the spread and fill at best available ask
    selling = base
    buying = quote
    price_value = price or "10000"  # ❌ HARDCODED
    op_type = "buy"

elif action == "market_sell":
    # Sell quote asset for base asset
    # Use very high price to cross the spread
    selling = quote
    buying = base
    price_value = price or "10000"  # ❌ HARDCODED
    op_type = "sell"
```

**What This Actually Does:**
- Creates a limit order at price 10000
- Relies on Stellar's matching engine to fill at best available price
- No visibility into what price you'll actually get
- No control over slippage
- No validation that liquidity exists

**Example Scenario:**

```
Orderbook for XLM/USDC:
  Best Ask: 0.10 XLM/USDC (100 USDC available)
  Next Ask: 0.15 XLM/USDC (200 USDC available)
  Next Ask: 0.20 XLM/USDC (500 USDC available)

User calls: market_buy(amount="150")

Current behavior:
  - Creates manage_buy_offer with price=10000
  - Stellar fills: 100 USDC @ 0.10 + 50 USDC @ 0.15
  - User has NO IDEA this happened
  - Average fill: 0.116 XLM/USDC
  - Total cost: 17.5 XLM
```

**The user never sees:**
- Expected fill price (0.116 XLM/USDC)
- Slippage (0.116 vs 0.10 = 16% slippage)
- Whether liquidity exists
- How much will actually fill

---

### Problem 2: Ambiguous Amount Semantics

**Current parameter:** `amount` (string)

**Questions:**
- Is this amount of quote asset to buy?
- Is this amount of base asset to spend?
- Is this total value?

**Example:**

```python
market_buy(
    quote_asset="USDC",
    amount="100",  # ❌ AMBIGUOUS
    ...
)
```

Does this mean:
- A) Buy 100 USDC (spending whatever XLM needed)?
- B) Spend 100 XLM to buy USDC?

**Current implementation:** (A) - Buy 100 USDC

But users might expect (B) - "I have 100 XLM, buy as much USDC as I can"

---

### Problem 3: No Slippage Protection

**Scenario:**

```
Orderbook:
  Best Ask: 0.10 XLM/USDC (10 USDC available)
  Next Ask: 10.00 XLM/USDC (1000 USDC available) ← PRICE MANIPULATION

User calls: market_buy(amount="50")

What happens:
  - Fills 10 USDC @ 0.10 = 1 XLM
  - Fills 40 USDC @ 10.00 = 400 XLM
  - Total: 401 XLM for 50 USDC
  - Average: 8.02 XLM/USDC (!!!!)
```

**User gets REKT with no warning.**

A proper market order implementation would:
1. Calculate total cost before execution
2. Check if slippage exceeds threshold (e.g., 5%)
3. Reject order if slippage too high
4. Return slippage info to user

---

### Problem 4: No Liquidity Validation

**Current behavior:**

```python
market_buy(amount="1000000")  # Buy 1M USDC
```

If orderbook only has 100 USDC available:
- Order creates a standing limit order for remaining 999,900 USDC
- User expects "market order" (immediate fill)
- Instead gets a limit order sitting on the book

**Expected behavior:**
- Calculate available liquidity
- Fill what's available
- Return info about partial fill or reject entirely

---

## Proposed Architecture

### Overview

```
┌─────────────────────────────────────────────────────┐
│              User calls market_buy()                 │
│        (amount="100", max_slippage=0.05)            │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│   STEP 1: Query Orderbook (market_data API)         │
│   - Fetch asks (for buy) or bids (for sell)         │
│   - Parse available liquidity                        │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│   STEP 2: Calculate Fill Strategy                   │
│   - Determine how much will fill at each level      │
│   - Calculate weighted average price                │
│   - Calculate total cost and slippage               │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│   STEP 3: Validate & Check Slippage                 │
│   - Check if sufficient liquidity exists            │
│   - Verify slippage within tolerance                │
│   - Return error if validation fails                │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│   STEP 4: Execute Order                             │
│   - Use calculated price (with buffer)              │
│   - Build → Sign → Submit transaction               │
│   - Return execution details + actual fill info     │
└─────────────────────────────────────────────────────┘
```

---

## Implementation Design

### New Function: `_calculate_market_fill()`

```python
def _calculate_market_fill(
    orderbook: Dict[str, Any],
    amount: str,
    side: str,  # "buy" or "sell"
    max_slippage: float = 0.05  # 5% default
) -> Dict[str, Any]:
    """
    Calculate market order fill details from orderbook data.

    Args:
        orderbook: Result from market_data(action="orderbook")
        amount: Amount to trade (quote asset for buy, base for sell)
        side: "buy" or "sell"
        max_slippage: Maximum allowed slippage (0.05 = 5%)

    Returns:
        {
            "feasible": bool,
            "fills": [
                {"price": "0.10", "amount": "100"},
                {"price": "0.12", "amount": "50"}
            ],
            "total_filled": "150",
            "average_price": "0.1067",
            "best_price": "0.10",
            "slippage": 0.067,  # 6.7%
            "total_cost": "16.0",  # Total base asset spent
            "execution_price": "0.12",  # Price to use (worst + buffer)
            "error": None or "Insufficient liquidity"
        }
    """
    try:
        # Get appropriate side (asks for buy, bids for sell)
        levels = orderbook.get("asks" if side == "buy" else "bids", [])

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
        for level in levels:
            level_price = Decimal(level["price"])
            level_amount = Decimal(level["amount"])

            fill_amount = min(remaining, level_amount)
            fill_cost = fill_amount * level_price

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
        average_price = total_cost / total_filled
        best_price = Decimal(levels[0]["price"])
        slippage = (average_price - best_price) / best_price

        # Check slippage tolerance
        if slippage > Decimal(str(max_slippage)):
            return {
                "feasible": False,
                "average_price": str(average_price),
                "best_price": str(best_price),
                "slippage": float(slippage),
                "error": f"Slippage {slippage*100:.2f}% exceeds max {max_slippage*100:.2f}%"
            }

        # Determine execution price (worst fill + 10% buffer)
        worst_price = Decimal(fills[-1]["price"])
        execution_price = worst_price * Decimal("1.1")  # 10% buffer

        return {
            "feasible": True,
            "fills": fills,
            "total_filled": str(total_filled),
            "average_price": str(average_price),
            "best_price": str(best_price),
            "worst_price": str(worst_price),
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
```

---

### Updated `trading()` Function

```python
def trading(
    action: str,
    account_id: str,
    key_manager: KeyManager,
    horizon: Server,
    base_asset: str = "XLM",
    quote_asset: Optional[str] = None,
    quote_issuer: Optional[str] = None,
    amount: Optional[str] = None,
    price: Optional[str] = None,
    offer_id: Optional[str] = None,
    max_slippage: float = 0.05,  # NEW: 5% default slippage tolerance
    auto_sign: bool = True
) -> Dict[str, Any]:
    """
    Unified SDEX trading tool with REAL market orders.

    Actions:
        - "market_buy": Buy quote asset at market price (orderbook-aware)
        - "market_sell": Sell quote asset at market price (orderbook-aware)
        - "limit_buy": Place limit buy order
        - "limit_sell": Place limit sell order
        - "cancel": Cancel open order
        - "orders": Get open orders

    Args:
        ...
        max_slippage: Maximum slippage tolerance for market orders (default: 0.05 = 5%)
        ...
    """
    try:
        # ... existing orders/cancel logic ...

        elif action in ["market_buy", "market_sell"]:
            if not quote_asset:
                return {"error": "quote_asset required for trading actions"}
            if not amount:
                return {"error": "amount required for trading actions"}

            # STEP 1: Query orderbook
            orderbook_result = market_data(
                action="orderbook",
                horizon=horizon,
                base_asset=base_asset,
                quote_asset=quote_asset,
                quote_issuer=quote_issuer,
                limit=20  # Get top 20 levels for depth analysis
            )

            if "error" in orderbook_result:
                return {
                    "error": f"Failed to fetch orderbook: {orderbook_result['error']}"
                }

            # STEP 2: Calculate fill strategy
            side = "buy" if action == "market_buy" else "sell"
            fill_calc = _calculate_market_fill(
                orderbook=orderbook_result,
                amount=amount,
                side=side,
                max_slippage=max_slippage
            )

            if not fill_calc.get("feasible"):
                return {
                    "success": False,
                    "error": fill_calc.get("error"),
                    "market_data": fill_calc  # Return diagnostic info
                }

            # STEP 3: Build order with calculated price
            base = _dict_to_asset(base_asset)
            quote = _dict_to_asset(quote_asset, quote_issuer)

            if action == "market_buy":
                selling = base
                buying = quote
                price_value = fill_calc["execution_price"]
                op_type = "buy"
            else:
                selling = quote
                buying = base
                price_value = fill_calc["execution_price"]
                op_type = "sell"

            # STEP 4: Execute transaction
            def trade_op(builder):
                if op_type == "buy":
                    builder.append_manage_buy_offer_op(
                        selling=selling,
                        buying=buying,
                        amount=amount,
                        price=price_value
                    )
                else:
                    builder.append_manage_sell_offer_op(
                        selling=selling,
                        buying=buying,
                        amount=amount,
                        price=price_value
                    )

            result = _build_sign_submit(account_id, [trade_op], key_manager, horizon, auto_sign)

            # Add market execution details to result
            if result.get("success"):
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

        elif action in ["limit_buy", "limit_sell"]:
            # ... existing limit order logic (unchanged) ...
            pass

    except Exception as e:
        return {"error": str(e)}
```

---

## New Features Enabled

### 1. Transparent Market Execution

**Before:**
```python
result = trading(action="market_buy", amount="100", ...)
# Result: {"success": true, "hash": "abc123", "ledger": 12345}
# NO IDEA what price was paid
```

**After:**
```python
result = trading(action="market_buy", amount="100", max_slippage=0.05, ...)
# Result:
{
  "success": true,
  "hash": "abc123",
  "ledger": 12345,
  "market_execution": {
    "requested_amount": "100",
    "expected_average_price": "0.106",
    "best_price": "0.10",
    "execution_price": "0.115",
    "slippage": 0.06,  # 6% slippage
    "total_cost_estimate": "10.6",
    "fills": [
      {"price": "0.10", "amount": "50"},
      {"price": "0.12", "amount": "50"}
    ]
  }
}
```

### 2. Slippage Protection

```python
# This will FAIL if slippage > 2%
result = trading(
    action="market_buy",
    amount="1000",
    max_slippage=0.02,  # 2% max
    ...
)

# Returns:
{
  "success": false,
  "error": "Slippage 8.50% exceeds max 2.00%",
  "market_data": {
    "average_price": "0.108",
    "best_price": "0.10",
    "slippage": 0.085
  }
}
```

### 3. Liquidity Validation

```python
# Orderbook only has 50 USDC available
result = trading(action="market_buy", amount="100", ...)

# Returns:
{
  "success": false,
  "error": "Insufficient liquidity: only 50 available",
  "partial_fill": "50",
  "requested": "100"
}
```

### 4. Pre-Execution Simulation

```python
# User can check market conditions before executing
result = trading(
    action="market_buy",
    amount="100",
    auto_sign=False,  # Don't execute, just calculate
    ...
)

# Shows what WOULD happen:
{
  "success": true,
  "market_execution": {
    "expected_average_price": "0.106",
    "slippage": 0.06,
    "total_cost_estimate": "10.6"
  },
  "xdr": "...",  # Can still execute later if desired
  "message": "Transaction built but not signed (auto_sign=False)"
}
```

---

## Migration Path

### Phase 1: Add New Implementation (Non-Breaking)

1. Add `_calculate_market_fill()` helper
2. Update `market_buy` and `market_sell` to use orderbook-based pricing
3. Add `max_slippage` parameter (default 0.05)
4. Keep backward compatibility (if orderbook fetch fails, fall back to high price)

### Phase 2: Update Tests

1. Update Test 15 to verify market execution details
2. Add new tests for:
   - Slippage rejection
   - Insufficient liquidity
   - Multi-level fills

### Phase 3: Update Documentation

1. Migration guide showing new features
2. Examples of slippage protection
3. Best practices for market orders

---

## Implementation Checklist

- [ ] Add `from decimal import Decimal` import
- [ ] Implement `_calculate_market_fill()` function
- [ ] Update `trading()` function for `market_buy`
- [ ] Update `trading()` function for `market_sell`
- [ ] Add `max_slippage` parameter to tool registration
- [ ] Add tests for slippage protection
- [ ] Add tests for insufficient liquidity
- [ ] Add tests for multi-level fills
- [ ] Update test_sdex_trading_v2.py Test 15
- [ ] Update MIGRATION_GUIDE.md with new features
- [ ] Add MARKET_ORDER_BEST_PRACTICES.md

---

## Testing Strategy

### Test Case 1: Simple Market Buy (Single Level Fill)

```python
# Orderbook: 100 USDC @ 0.10 XLM/USDC
result = trading(action="market_buy", amount="50", ...)

# Expected:
assert result["success"] == True
assert result["market_execution"]["slippage"] == 0.0  # Single level
assert result["market_execution"]["average_price"] == "0.10"
```

### Test Case 2: Multi-Level Fill

```python
# Orderbook:
#   50 USDC @ 0.10
#   50 USDC @ 0.12
#   100 USDC @ 0.15

result = trading(action="market_buy", amount="100", ...)

# Expected:
assert result["market_execution"]["fills"] == [
    {"price": "0.10", "amount": "50"},
    {"price": "0.12", "amount": "50"}
]
assert result["market_execution"]["average_price"] == "0.11"
assert result["market_execution"]["slippage"] == 0.1  # 10%
```

### Test Case 3: Slippage Rejection

```python
# Orderbook:
#   10 USDC @ 0.10
#   90 USDC @ 0.50  # Big jump

result = trading(
    action="market_buy",
    amount="100",
    max_slippage=0.10,  # 10% max
    ...
)

# Expected:
assert result["success"] == False
assert "exceeds max" in result["error"]
assert result["market_data"]["slippage"] > 0.10
```

### Test Case 4: Insufficient Liquidity

```python
# Orderbook: only 50 USDC available total

result = trading(action="market_buy", amount="100", ...)

# Expected:
assert result["success"] == False
assert "Insufficient liquidity" in result["error"]
assert result["partial_fill"] == "50"
```

---

## Benefits Summary

| Feature | Old (Hardcoded Price) | New (Orderbook-Aware) |
|---------|----------------------|------------------------|
| **Price Discovery** | ❌ No idea what you'll pay | ✅ Knows exact expected price |
| **Slippage Control** | ❌ No protection | ✅ Configurable max slippage |
| **Liquidity Check** | ❌ Blindly submits | ✅ Validates before execution |
| **Transparency** | ❌ Black box | ✅ Shows fill breakdown |
| **User Trust** | ❌ "Market order" is misleading | ✅ True market semantics |
| **Testing** | ❌ Hard to verify | ✅ Deterministic with mock orderbook |

---

## Conclusion

The current "market order" implementation is a **semantic lie** that could lead to:
- Unexpected slippage
- Failed expectations
- User confusion
- Poor trading outcomes

The proposed orderbook-aware implementation provides:
- **True market order semantics**
- **Slippage protection**
- **Liquidity validation**
- **Transparent execution**
- **Better UX for Claude agents and human users**

**Recommendation:** Implement this architecture before production release to prevent user confusion and potential losses from unexpected slippage.
