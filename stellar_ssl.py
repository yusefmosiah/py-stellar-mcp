"""SSL certificate handling for Stellar/Soroban connections.

Solves the macOS Python 3.6+ issue where bundled OpenSSL lacks certificates.

This module provides SSL-configured clients that work across all platforms
(macOS, Linux, Windows) without requiring environment variable configuration.
"""

import ssl
from typing import Optional, Dict

try:
    import certifi
    import aiohttp
    from stellar_sdk.client.aiohttp_client import AiohttpClient
    from stellar_sdk.client import defines
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


def create_ssl_context() -> ssl.SSLContext:
    """Create SSL context with certifi's CA bundle.

    This ensures HTTPS connections work on macOS where Python 3.6+ bundles
    OpenSSL without certificates. Uses certifi's maintained CA bundle for
    certificate verification.

    Returns:
        ssl.SSLContext: Configured context for HTTPS connections

    Raises:
        ImportError: If certifi is not installed
    """
    if not _DEPS_AVAILABLE:
        raise ImportError(
            "Required dependencies not installed. "
            "Install with: pip install certifi aiohttp stellar-sdk[aiohttp]"
        )

    context = ssl.create_default_context(cafile=certifi.where())
    return context


class StellarAiohttpClient(AiohttpClient):
    """Extended AiohttpClient with proper SSL certificate handling.

    This client automatically configures SSL using certifi's CA bundle,
    eliminating the need for SSL_CERT_FILE environment variables.

    Use this client with SorobanServerAsync or any Stellar SDK async operations
    that require HTTPS connections.

    Example:
        >>> from stellar_sdk.soroban_server_async import SorobanServerAsync
        >>> from stellar_ssl import StellarAiohttpClient
        >>>
        >>> client = StellarAiohttpClient()
        >>> soroban = SorobanServerAsync(
        ...     server_url="https://soroban-testnet.stellar.org",
        ...     client=client
        ... )
    """

    def __init__(
        self,
        pool_size: Optional[int] = None,
        request_timeout: float = defines.DEFAULT_GET_TIMEOUT_SECONDS,
        post_timeout: float = defines.DEFAULT_POST_TIMEOUT_SECONDS,
        backoff_factor: Optional[float] = 0.5,
        user_agent: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> None:
        """Initialize SSL-configured aiohttp client.

        Args:
            pool_size: Connection pool size (None for unlimited)
            request_timeout: Timeout for GET requests in seconds
            post_timeout: Timeout for POST requests in seconds
            backoff_factor: Backoff factor for retries
            user_agent: Custom user agent string
            custom_headers: Additional HTTP headers to include
            **kwargs: Additional arguments passed to ClientSession
        """
        super().__init__(
            pool_size=pool_size,
            request_timeout=request_timeout,
            post_timeout=post_timeout,
            backoff_factor=backoff_factor,
            user_agent=user_agent,
            custom_headers=custom_headers,
            **kwargs,
        )
        # Store SSL context for use during session initialization
        self._ssl_context = create_ssl_context()

    async def _StellarAiohttpClient__init_session(self):
        """Initialize session with SSL-configured connector.

        Overrides parent's __init_session to inject SSL context into the
        TCPConnector before creating the ClientSession.
        """
        if self._session is None:
            # Create connector with SSL context
            if self.pool_size is None:
                connector = aiohttp.TCPConnector(ssl=self._ssl_context)
            else:
                connector = aiohttp.TCPConnector(
                    limit=self.pool_size,
                    ssl=self._ssl_context
                )

            # Create session with SSL-configured connector
            self._session = aiohttp.ClientSession(
                headers=self.headers.copy(),
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.request_timeout),
                **self._AiohttpClient__kwargs,
            )

    # Alias the method to match parent's name mangling
    _AiohttpClient__init_session = _StellarAiohttpClient__init_session


def create_soroban_client_with_ssl(server_url: str):
    """Create Soroban RPC client with proper SSL certificate handling.

    This is a convenience function that creates a SorobanServerAsync instance
    with SSL properly configured for macOS Python 3.6+ and all other platforms.

    Args:
        server_url: Soroban RPC endpoint URL (e.g., "https://soroban-testnet.stellar.org")

    Returns:
        SorobanServerAsync: Configured Soroban RPC client

    Example:
        >>> soroban = create_soroban_client_with_ssl(
        ...     "https://soroban-testnet.stellar.org"
        ... )
        >>> health = await soroban.get_health()
    """
    if not _DEPS_AVAILABLE:
        raise ImportError(
            "Required dependencies not installed. "
            "Install with: pip install certifi aiohttp stellar-sdk[aiohttp]"
        )

    from stellar_sdk.soroban_server_async import SorobanServerAsync

    client = StellarAiohttpClient()
    return SorobanServerAsync(server_url=server_url, client=client)
