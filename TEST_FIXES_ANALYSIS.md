# SDEX Trading v2 Test Failures - Root Cause Analysis & Fixes

## Test Results Summary

**Passed:** 12/15 tests (80%)
**Failed:** 3 tests

---

## Failed Test #9: Place Limit Sell Order (op_underfunded)

### Root Cause

**The tool's semantic design vs. test intent mismatch.**

The `trading()` tool uses this convention:
- `base_asset` = Your "money" (e.g., XLM)
- `quote_asset` = The asset you're trading (e.g., USDC)

Actions:
- **`limit_buy`** = Buy quote asset WITH base asset
  - Sells XLM, buys USDC
  - Uses `manage_buy_offer_op`
  - `amount` = how much USDC to buy
  - `price` = how much XLM per USDC

- **`limit_sell`** = Sell quote asset FOR base asset
  - Sells USDC, buys XLM
  - Uses `manage_sell_offer_op`
  - `amount` = how much USDC to sell
  - `price` = how much XLM per USDC

### The Problem

Test 9 (line 283) comment says: **"Account B: Sell 100 XLM for USDC at 2.0 USDC/XLM"**

But the code does:
```python
result = trading(
    action="limit_sell",  # ❌ This means "sell USDC for XLM"
    account_id=account_b,
    base_asset="XLM",
    quote_asset="USDC",
    quote_issuer=USDC_ISSUER,
    amount="100",         # ❌ This means "sell 100 USDC"
    price="2.0",          # Price: 2.0 XLM per USDC
    auto_sign=True
)
```

**Result:** Account B tries to sell 100 USDC, but has 0 USDC → `op_underfunded`

### Fix Option 1: Change Test to Match Tool Semantics (RECOMMENDED)

To **sell 100 XLM for USDC at 2.0 USDC per XLM**, we should **buy USDC with XLM**:

```python
result = trading(
    action="limit_buy",    # ✅ Buy USDC with XLM
    account_id=account_b,
    base_asset="XLM",
    quote_asset="USDC",
    quote_issuer=USDC_ISSUER,
    amount="200",          # ✅ Buy 200 USDC (= 100 XLM * 2.0 rate)
    price="0.5",           # ✅ Pay 0.5 XLM per USDC (= 1/2.0)
    auto_sign=True
)
```

**Calculation:**
- Want to sell: 100 XLM
- Want rate: 2.0 USDC per XLM
- USDC received: 100 × 2.0 = 200 USDC
- Price in manage_buy_offer terms: 1/2.0 = 0.5 XLM per USDC
- Total XLM spent: 200 USDC × 0.5 = 100 XLM ✅

### Fix Option 2: Redesign Tool Semantics (NOT RECOMMENDED)

Add parameters to clarify which direction:
- `selling_asset` / `buying_asset` instead of base/quote
- More verbose but clearer

**Recommendation:** Use Fix Option 1 (simpler, no breaking changes)

---

## Failed Test #13: Cancel Order B (Cascading Failure)

### Root Cause

Test 9 failed → no sell order created → nothing to cancel

### Fix

Automatically resolves when Test 9 is fixed.

---

## Failed Test #15: Market Buy USDC (Trade Didn't Fill)

### Root Cause

**Bug in `market_buy` price calculation (stellar_tools_v2.py line 334)**

Current code:
```python
elif action == "market_buy":
    # Buy quote asset with base asset
    # Use very low price to cross the spread
    selling = base      # XLM
    buying = quote      # USDC
    price_value = price or "0.0001"  # ❌ BUG: Price too LOW
    op_type = "buy"
```

This creates a `manage_buy_offer_op` with:
- `selling` = XLM
- `buying` = USDC
- `amount` = 0.1 (buy 0.1 USDC)
- `price` = 0.0001 (pay 0.0001 XLM per USDC)

### The Problem

In `manage_buy_offer_op`, the `price` parameter means:
> **How much of SELLING asset per unit of BUYING asset**

So `price=0.0001` means:
- "I'm willing to pay only 0.0001 XLM for 1 USDC"

This is **absurdly low** and won't fill any real asks on the orderbook. The market rate is typically around 0.08-0.15 XLM per USDC on testnet.

### Fix: Use High Price for Market Buy

```python
elif action == "market_buy":
    # Buy quote asset with base asset
    # Use very HIGH price to cross the spread and fill immediately
    selling = base      # XLM
    buying = quote      # USDC
    price_value = price or "10000"  # ✅ FIX: High price crosses spread
    op_type = "buy"
```

**Why 10000 works:**
- `price=10000` means "willing to pay up to 10000 XLM per USDC"
- This is intentionally way above market rate (~0.1 XLM/USDC)
- The order will fill at the **best available ask price**, not at 10000
- Stellar's matching engine ensures you get the best price available

### Alternative Fix: Query Orderbook and Use 2x Best Ask

For more precision:
```python
elif action == "market_buy":
    selling = base
    buying = quote

    if not price:
        # Query orderbook for best ask
        orderbook = horizon.orderbook(
            selling=selling,
            buying=buying
        ).call()

        if orderbook["asks"]:
            best_ask = float(orderbook["asks"][0]["price"])
            price_value = str(best_ask * 2)  # 2x best ask to ensure fill
        else:
            price_value = "10000"  # Fallback
    else:
        price_value = price

    op_type = "buy"
```

**Recommendation:** Use simple fix (change to "10000") for consistency with `market_sell` (which uses "10000")

---

## Summary of Required Changes

### 1. Fix Test #9 - test_sdex_trading_v2.py (lines 283-307)

**Change:**
```python
# OLD (line 287)
action="limit_sell",
amount="100",
price="2.0",

# NEW
action="limit_buy",
amount="200",
price="0.5",
```

**Update comment:**
```python
# OLD (line 283)
print("Test 9: Placing limit sell order (Account B: Sell 100 XLM for USDC at 2.0 USDC/XLM)...")

# NEW
print("Test 9: Placing limit buy order (Account B: Buy 200 USDC with 100 XLM at 0.5 XLM/USDC)...")
```

### 2. Fix Test #15 - stellar_tools_v2.py (line 334)

**Change:**
```python
# OLD
price_value = price or "0.0001"

# NEW
price_value = price or "10000"
```

**Update comment:**
```python
# OLD (line 331)
# Use very low price to cross the spread

# NEW
# Use very high price to cross the spread and fill at best available ask
```

### 3. Test #13 Auto-Fixes

No changes needed - will pass once Test #9 is fixed.

---

## Verification Plan

After applying fixes:

1. **Run test_sdex_trading_v2.py**
   ```bash
   source .venv/bin/activate
   python test_sdex_trading_v2.py
   ```

2. **Expected results:**
   - Test 9: ✅ PASSED (limit buy order placed successfully)
   - Test 13: ✅ PASSED (order cancelled successfully)
   - Test 15: ✅ PASSED (market buy fills, USDC balance increases)

3. **Success criteria:**
   - 15/15 tests pass (100% success rate)
   - Real USDC acquired in Test 15
   - Report shows "REAL TRADE EXECUTED!"

---

## Additional Notes

### Why the Tool Design Is Actually Good

The base/quote convention is standard in trading:
- **XLM/USDC pair** means "price of USDC in XLM"
- `buy` operation = buy quote (USDC) with base (XLM)
- `sell` operation = sell quote (USDC) for base (XLM)

This matches traditional trading semantics where:
- You "buy USDC" means you're spending XLM to get USDC
- You "sell USDC" means you're getting XLM by selling USDC

### Stellar Price Semantics Reference

**manage_buy_offer:**
- `price` = amount of **selling** asset per unit of **buying** asset
- To cross spread: use **HIGH** price (overpay)

**manage_sell_offer:**
- `price` = amount of **buying** asset per unit of **selling** asset
- To cross spread: use **HIGH** price (underprice)

Both market operations should use **high prices** (10000) to ensure immediate fills.
