"""
Secure keypair storage for Stellar accounts.
In-memory storage for hackathon; consider encrypted file storage for production.
"""

from stellar_sdk import Keypair


class KeyManager:
    """Manages Stellar keypairs securely server-side"""

    def __init__(self):
        self._keypair_store = {}

    def store(self, account_id: str, secret_key: str):
        """
        Store keypair securely indexed by account_id (public key)

        Args:
            account_id: Stellar public key (G...)
            secret_key: Stellar secret key (S...)
        """
        self._keypair_store[account_id] = secret_key

    def get_keypair(self, account_id: str) -> Keypair:
        """
        Retrieve keypair for signing operations

        Args:
            account_id: Stellar public key (G...)

        Returns:
            Keypair object for signing

        Raises:
            ValueError: If account_id not found in storage
        """
        secret = self._keypair_store.get(account_id)
        if not secret:
            raise ValueError(
                f"Account {account_id} not found in key storage. "
                "Use create_account() or import_keypair() first."
            )
        return Keypair.from_secret(secret)

    def list_accounts(self) -> list:
        """
        List all managed account public keys

        Returns:
            List of account_ids (public keys)
        """
        return list(self._keypair_store.keys())

    def export_secret(self, account_id: str) -> str:
        """
        Export secret key for backup/migration (USE WITH CAUTION!)

        Args:
            account_id: Stellar public key (G...)

        Returns:
            Secret key (S...)

        Raises:
            ValueError: If account_id not found
        """
        secret = self._keypair_store.get(account_id)
        if not secret:
            raise ValueError(f"Account {account_id} not found in storage")
        return secret

    def import_keypair(self, secret_key: str) -> str:
        """
        Import existing keypair into storage

        Args:
            secret_key: Stellar secret key (S...)

        Returns:
            account_id: Derived public key (G...)
        """
        keypair = Keypair.from_secret(secret_key)
        account_id = keypair.public_key
        self._keypair_store[account_id] = secret_key
        return account_id

    def has_account(self, account_id: str) -> bool:
        """
        Check if account exists in storage

        Args:
            account_id: Stellar public key (G...)

        Returns:
            True if account exists, False otherwise
        """
        return account_id in self._keypair_store
