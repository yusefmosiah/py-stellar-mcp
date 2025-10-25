# Soroban Testing Notes

Technical documentation of issues, workarounds, and limitations discovered during Soroban integration testing.

**Last Updated:** 2025-10-24
**Version:** 2.0.1

---

## Overview

This document captures the technical details, workarounds, and open questions encountered while implementing and testing Soroban smart contract support in the Stellar MCP Server.

---

## 1. SSL Certificate Issue (macOS + Python 3.6+)

### The Problem

**Symptom:**
```
SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: unable to get local issuer certificate (_ssl.c:1028)
```

**When it occurs:**
- Only when making HTTPS connections via `aiohttp` (used by `stellar-sdk` async operations)
- Specifically affects `SorobanServerAsync` connections to `soroban-testnet.stellar.org`
- Does **not** affect classic Horizon API calls (which use `requests` library)

### Root Cause

Starting with Python 3.6, the official Python distribution on macOS began shipping with its own OpenSSL library rather than using the system's OpenSSL. This bundled OpenSSL **does not use the macOS system certificate store** by default.

**Why Stellar's certificate is valid:**
- The certificate is issued by Sectigo (legitimate CA)
- `curl`, `openssl`, and browsers verify it successfully
- `openssl s_client -connect soroban-testnet.stellar.org:443` works fine
- The issue is entirely on the Python/aiohttp client side

**Confirmed with:**
```bash
$ openssl s_client -connect soroban-testnet.stellar.org:443 -servername soroban-testnet.stellar.org
# Output shows: SSL certificate verify ok
# Issuer: C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV R36
# Subject: CN=*.stellar.org

$ curl -v https://soroban-testnet.stellar.org 2>&1 | grep -E "(SSL|certificate)"
# Output shows: SSL certificate verify ok
```

### Why This Affects aiohttp Specifically

The `requests` library (used for Horizon API) has better CA bundle detection:
- Automatically uses `certifi` package if available
- Falls back to system certificates
- Generally "just works"

The `aiohttp` library (used for Soroban RPC):
- Does NOT automatically use `certifi`
- Requires explicit SSL context configuration OR environment variables
- Documented limitation: doesn't respect `SSL_CERT_DIR` environment variable
- Only responds to `SSL_CERT_FILE` environment variable

### Current Workaround (v2.0.1)

**Solution:** Set `SSL_CERT_FILE` environment variable pointing to certifi's CA bundle.

**Implementation:**

1. **In `.env` file:**
```bash
SSL_CERT_FILE=/Users/wiz/py-stellar-mcp/.venv/lib/python3.13/site-packages/certifi/cacert.pem
```

2. **To find your path:**
```bash
python -c "import certifi; print(certifi.where())"
```

3. **For running tests:**
```bash
SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())") python test_soroban.py
```

**Pros:**
- ✅ Simple, no code changes required
- ✅ Works reliably
- ✅ Standard Python approach
- ✅ Certified CA bundle from Mozilla

**Cons:**
- ❌ Path is machine-specific (not portable)
- ❌ Requires manual configuration
- ❌ Environment variable must be set before running
- ❌ Kludge rather than elegant solution

### Better Solution (Future)

**Programmatic SSL context configuration in `stellar_soroban.py`:**

```python
import ssl
import certifi
import aiohttp

# Create SSL context with certifi's CA bundle
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Pass to SorobanServerAsync
connector = aiohttp.TCPConnector(ssl=ssl_context)
soroban = SorobanServerAsync(
    base_url=SOROBAN_RPC_URL,
    connector=connector
)
```

**Benefits:**
- ✅ Works without environment variables
- ✅ Portable across machines
- ✅ Explicit and self-documenting
- ✅ No user configuration required

**Why not implemented yet:**
- Need to verify stellar-sdk's `SorobanServerAsync` constructor accepts connector parameter
- Would require changes to both `stellar_soroban.py` and `server.py`
- Environment variable approach works and was faster to implement

### Open Questions

1. **Does stellar-sdk 13.1.0 support custom SSL contexts?**
   - Need to review `SorobanServerAsync` constructor
   - May require custom session parameter
   - Documentation unclear on this

2. **Should we patch this in the MCP server or the test files?**
   - Server: More elegant, works for all users
   - Tests: Isolated change, less risk
   - Current: Environment variable (middle ground)

3. **Will this be fixed upstream?**
   - Has anyone reported this to stellar-sdk maintainers?
   - Is this considered a bug or expected behavior?
   - Should aiohttp bundle better CA detection?

---

## 2. Soroban Contract Testing Limitations

### The Problem

**Cannot run full integration tests** because:
- No verified live test contracts with known function signatures
- Example contract IDs in Stellar documentation have invalid checksums
- Cannot invoke or simulate without valid contract addresses

### Research Findings

**Contract IDs found in documentation:**
- `CACDYF3CYMJEJTIVFESQYZTN67GO2R5D5IUABTCUG3HXQSRXCSOROBAN` (increment example)
- `CBGTG3KGTGQ3IVHJVRILHLJITP3VX5DSYKHPZKLZARKJ6E5TGZO5IUEU` (hello world)
- `CAEDPEZDRCEJCF73ASC5JGNKCIJDV2QJQSW6DJ6B74MYALBNKCJ5IFP` (DIA Oracle)

**All fail with:**
```python
ValueError: Invalid encoded bytes
# or
`contract_id` is invalid
```

**Why they fail:**
- stellar-sdk validates contract ID checksums using `strkey.StrKey.decode_contract()`
- Documentation examples are **placeholders**, not real deployed contracts
- They're educational examples showing format, not actual addresses

**Verified with:**
```python
from stellar_sdk import strkey

# Attempt to decode - fails with ValueError
decoded = strkey.StrKey.decode_contract('CAEDPEZDRCEJCF73ASC5JGNKCIJDV2QJQSW6DJ6B74MYALBNKCJ5IFP')
# ValueError: Invalid Pre Auth Tx Key
```

### Current Testing Approach (v2.0.1)

**What we CAN test (without contracts):**
- ✅ Server health checks (`soroban.get_health()`)
- ✅ Error handling and action validation
- ✅ Module imports and dependencies
- ✅ Parameter parsing logic
- ✅ Configuration file structure
- ✅ SSL certificate handling

**What we CANNOT test (need contracts):**
- ❌ `simulate` action with real contract calls
- ❌ `invoke` action with transaction submission
- ❌ `get_data` action with contract storage reads
- ❌ `get_events` action with contract event queries
- ❌ Parameter encoding with actual contract responses
- ❌ scval conversions with real return values

**Test Results:**
```
test_soroban_basic.py:  7/7 tests passed (validation only)
test_soroban.py:        2/2 tests passed (skips contract calls)
```

### How to Enable Full Testing

Users can deploy their own test contracts:

**1. Install Stellar CLI:**
```bash
# macOS
brew install stellar-cli

# Or download from
# https://developers.stellar.org/docs/tools/developer-tools
```

**2. Deploy a test contract:**
```bash
# Clone soroban examples
git clone https://github.com/stellar/soroban-examples
cd soroban-examples/hello_world

# Build contract
stellar contract build

# Deploy to testnet
stellar contract deploy \
  --wasm target/wasm32v1-none/release/hello_world.wasm \
  --source-account alice \
  --network testnet

# Returns: CONTRACT_ID (starts with 'C')
```

**3. Update test file:**
```python
# test_soroban.py:126
CONTRACT_ID = "CXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # Your deployed contract
```

**4. Update function names:**
```python
# test_soroban.py:183 and :211
function_name="hello"  # Or whatever functions your contract has
```

**5. Run tests:**
```bash
SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())") python test_soroban.py
```

### Open Questions

1. **Should we maintain a persistent test contract?**
   - Deploy simple test contract to testnet
   - Keep it funded and maintained
   - Hard-code its ID in tests
   - **Concern:** Contract might expire or be archived

2. **Should we deploy contracts as part of CI/CD?**
   - Automate contract deployment in test suite
   - Deploy fresh contract per test run
   - Clean up after tests complete
   - **Concern:** Requires funded testnet account, Stellar CLI installation

3. **Can we use a public test contract?**
   - Research if Stellar maintains any
   - Check if protocol test contracts are available
   - Community-maintained test contracts?
   - **Issue:** Availability, documentation, stability

4. **What's the minimal contract for testing?**
   - Needs to accept various parameter types
   - Should have storage operations
   - Should emit events
   - Return different value types
   - **Idea:** Create `mcp-test-contract` repo

---

## 3. Contract ID Format Validation

### Technical Details

**Correct format:**
- Contract IDs use Stellar strkey format
- Always start with 'C'
- 56 characters total
- Base32 encoded with checksum
- Example: `CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5SOAOPIFY6YQGAXE`

**Validation:**
```python
from stellar_sdk import strkey

# Valid contract ID check
try:
    decoded = strkey.StrKey.decode_contract(contract_id)
    # If this succeeds, contract ID format is valid
    # (Doesn't mean contract exists on-chain)
except ValueError:
    # Invalid format or bad checksum
    pass
```

**Common mistakes:**
- Using account addresses (start with 'G')
- Using example IDs from documentation
- Truncating or typos in contract IDs
- Using old hex format instead of strkey

### Should We Add Validation?

**Pros of adding validation to `stellar_soroban.py`:**
- ✅ Fail fast with clear error message
- ✅ Catch typos before network call
- ✅ Better user experience
- ✅ Save RPC credits on invalid calls

**Cons:**
- ❌ Duplicate validation (stellar-sdk does it)
- ❌ More code to maintain
- ❌ May reject valid formats we don't know about
- ❌ stellar-sdk errors are already clear enough

**Current decision:** Let stellar-sdk handle it. Their error messages are clear:
```
`contract_id` is invalid.
```

---

## 4. Parameter Type Coverage

### What's Tested (v2.0.1)

**Simple types:**
- ✅ `uint32`, `string`, `symbol` - tested in `test_soroban_basic.py`

**Complex types:**
- ✅ `vec` (array) - tested with nested uint32 values

**Untested types:**
- ⚠️ `address`, `bool`, `bytes`, `duration`
- ⚠️ `int32`, `int64`, `int128`, `int256`
- ⚠️ `uint64`, `uint128`, `uint256`
- ⚠️ `timepoint`, `void`, `native`
- ⚠️ `map`, `struct`, `tuple_struct`, `enum`

### Testing Limitations

Cannot fully test parameter encoding without contracts that:
- Accept all parameter types
- Return various types for round-trip testing
- Validate correct encoding/decoding

**Current approach:** Trust stellar-sdk's scval implementation and test basic parsing logic.

### Open Questions

1. **Should we create unit tests with mock responses?**
   - Test parameter encoding in isolation
   - Mock stellar-sdk responses
   - Verify our parsing logic
   - **Benefit:** Complete coverage without contracts

2. **Are there edge cases in our parameter parsing?**
   - Large integers (int256, uint256)?
   - Nested complex types (map of vecs)?
   - Empty arrays/maps?
   - Special values (MAX_INT, null equivalents)?

3. **How do we test error cases?**
   - Invalid type names?
   - Mismatched value types?
   - Missing required fields?
   - **Current:** Relies on stellar-sdk validation

---

## 5. Future Improvements

### Priority 1: SSL Certificate Handling

**Goal:** Remove environment variable requirement

**Options:**
1. Programmatic SSL context in code (recommended)
2. Auto-detect certificate path on startup
3. Bundle certifi configuration in installer
4. Document in README with clear instructions

### Priority 2: Contract Testing Infrastructure

**Goal:** Enable full integration tests

**Options:**
1. Deploy and maintain persistent test contract
2. Create contract deployment scripts for CI/CD
3. Build minimal test contract with all parameter types
4. Document community test contracts if available

### Priority 3: Extended Parameter Testing

**Goal:** Validate all 22 parameter types

**Options:**
1. Create unit tests with mocked responses
2. Build comprehensive test contract
3. Add parameter validation examples to README
4. Create interactive parameter testing tool

### Priority 4: Error Handling Improvements

**Goal:** Better error messages and recovery

**Enhancements:**
1. Detect common mistakes (wrong contract ID format)
2. Suggest fixes (check CONTRACT_ID is set)
3. Validate parameters before network calls
4. Add retry logic for transient failures

---

## 6. Known Workarounds Summary

| Issue | Workaround | Better Solution |
|-------|-----------|----------------|
| SSL Certificate Error | `SSL_CERT_FILE` environment variable | Programmatic SSL context in code |
| No test contracts | Skip contract invocation tests | Deploy persistent test contract |
| Invalid example contract IDs | Use `CONTRACT_ID = None` | Maintain verified contract ID |
| Path portability | User must set certificate path | Auto-detect certifi location |
| Limited parameter testing | Trust stellar-sdk implementation | Unit tests with mock responses |

---

## 7. Questions for Community/Upstream

1. **Stellar SDK:**
   - Is there a recommended way to configure SSL in SorobanServerAsync?
   - Should stellar-sdk automatically use certifi if available?
   - Are there maintained test contracts on testnet?

2. **Stellar DevRel:**
   - Can documentation include real deployed contract IDs?
   - Are there protocol test contracts available?
   - Best practices for contract testing in CI/CD?

3. **aiohttp:**
   - Plans to auto-detect certifi like requests does?
   - Why doesn't it respect `SSL_CERT_DIR`?
   - Is `SSL_CERT_FILE` the recommended approach?

---

## 8. References

**Related Issues:**
- Python tracker #43404: No SSL certificates when using Mac installer
- aiohttp #3180: Ignoring SSL_CERT_DIR and SSL_CERT_FILE environment vars
- stellar-sdk: (no open issues found related to SSL on macOS)

**Documentation:**
- Stellar Soroban Docs: https://developers.stellar.org/docs/smart-contracts
- stellar-sdk Python: https://stellar-sdk.readthedocs.io
- certifi package: https://github.com/certifi/python-certifi
- aiohttp SSL: https://docs.aiohttp.org/en/stable/client_advanced.html#ssl-control-for-tcp-sockets

**Test Reports:**
- `test_reports/soroban_validation_report_20251024_195313.md` - 7/7 passed
- `test_reports/soroban_integration_report_20251024_201937.md` - 2/2 passed

---

## Changelog

**2025-10-24 (v2.0.1):**
- Initial documentation of SSL certificate issue
- Documented contract testing limitations
- Added workarounds and future improvements
- Listed open questions for investigation

---

**For questions or contributions, please:**
1. Open an issue on GitHub
2. Check Stellar Discord #soroban channel
3. Review stellar-sdk documentation
4. Test on your platform and report findings
