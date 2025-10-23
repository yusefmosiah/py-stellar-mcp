"""
Basic integration tests for Stellar MCP Server
Tests account creation, funding, and basic operations
"""

from stellar_sdk import Server
from key_manager import KeyManager
from stellar_tools import (
    create_account,
    fund_account,
    get_account,
    list_accounts,
    establish_trustline,
    get_server_status
)

# Initialize
horizon = Server("https://horizon-testnet.stellar.org")
keys = KeyManager()

print("=" * 60)
print("STELLAR MCP SERVER - BASIC TESTS")
print("=" * 60)
print()

# Test 1: Server Status
print("Test 1: Checking Horizon server status...")
status = get_server_status(horizon)
if "error" in status:
    print(f"❌ FAILED: {status['error']}")
    exit(1)
else:
    print(f"✅ PASSED: Horizon version {status.get('horizon_version')}")
    print(f"   Latest ledger: {status.get('history_latest_ledger')}")
print()

# Test 2: Create Account
print("Test 2: Creating new account...")
result = create_account(keys)
if "error" in result:
    print(f"❌ FAILED: {result['error']}")
    exit(1)
else:
    account_id = result["account_id"]
    print(f"✅ PASSED: Account created")
    print(f"   Account ID: {account_id}")
print()

# Test 3: List Accounts
print("Test 3: Listing managed accounts...")
accounts = list_accounts(keys)
if "error" in accounts:
    print(f"❌ FAILED: {accounts['error']}")
    exit(1)
else:
    print(f"✅ PASSED: {accounts['count']} account(s) found")
    print(f"   Accounts: {accounts['accounts']}")
print()

# Test 4: Fund Account
print("Test 4: Funding account via Friendbot...")
print("   (This may take a few seconds...)")
fund_result = fund_account(account_id, horizon)
if not fund_result.get("success"):
    print(f"❌ FAILED: {fund_result.get('error')}")
    print("   Note: Friendbot may be rate-limited. Try again in a few seconds.")
    exit(1)
else:
    print(f"✅ PASSED: Account funded")
    print(f"   Balance: {fund_result['balance']} XLM")
print()

# Test 5: Get Account Details
print("Test 5: Fetching account details...")
account = get_account(account_id, horizon)
if "error" in account:
    print(f"❌ FAILED: {account['error']}")
    exit(1)
else:
    print(f"✅ PASSED: Account details retrieved")
    print(f"   Sequence: {account['sequence']}")
    print(f"   Balances:")
    for balance in account['balances']:
        if balance['asset_type'] == 'native':
            print(f"      - XLM: {balance['balance']}")
        else:
            print(f"      - {balance['asset_code']}: {balance['balance']}")
print()

# Test 6: Establish Trustline
print("Test 6: Establishing trustline for USDC...")
USDC_ISSUER = "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"
trustline_result = establish_trustline(
    account_id,
    {"code": "USDC", "issuer": USDC_ISSUER},
    keys,
    horizon
)
if not trustline_result.get("success"):
    print(f"❌ FAILED: {trustline_result.get('error')}")
    exit(1)
else:
    print(f"✅ PASSED: Trustline established")
    print(f"   Transaction hash: {trustline_result['hash']}")
    print(f"   Ledger: {trustline_result['ledger']}")
print()

# Test 7: Verify Trustline
print("Test 7: Verifying trustline in account...")
account = get_account(account_id, horizon)
usdc_balance = None
for balance in account['balances']:
    if balance.get('asset_code') == 'USDC':
        usdc_balance = balance
        break

if usdc_balance:
    print(f"✅ PASSED: USDC trustline found")
    print(f"   Balance: {usdc_balance['balance']} USDC")
    print(f"   Limit: {usdc_balance['limit']}")
else:
    print(f"❌ FAILED: USDC trustline not found")
    exit(1)
print()

print("=" * 60)
print("ALL TESTS PASSED! ✅")
print("=" * 60)
print()
print(f"Test account created: {account_id}")
print("You can view it on Stellar Expert:")
print(f"https://stellar.expert/explorer/testnet/account/{account_id}")
print()
