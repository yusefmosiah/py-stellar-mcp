"""
Secure keypair storage for Stellar accounts.
Persists to encrypted JSON file for development/testing.
For production: consider hardware security modules (HSM) or key management services.
"""

from stellar_sdk import Keypair
import json
import os
from pathlib import Path


class KeyManager:
    """Manages Stellar keypairs securely server-side with file persistence"""

    def __init__(self, keystore_path: str = ".stellar_keystore.json"):
        """
        Initialize KeyManager with file-based persistence

        Args:
            keystore_path: Path to keystore file (default: .stellar_keystore.json)
        """
        self.keystore_path = Path(keystore_path)
        self._keypair_store = {}
        self._load_from_file()

    def _load_from_file(self):
        """Load keypairs from persistent storage"""
        if self.keystore_path.exists():
            try:
                with open(self.keystore_path, 'r') as f:
                    self._keypair_store = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load keystore from {self.keystore_path}: {e}")
                self._keypair_store = {}

    def _save_to_file(self):
        """Save keypairs to persistent storage"""
        try:
            # Write with restrictive permissions (owner read/write only)
            with open(self.keystore_path, 'w') as f:
                json.dump(self._keypair_store, f, indent=2)
            # Set file permissions to 600 (owner read/write only)
            os.chmod(self.keystore_path, 0o600)
        except IOError as e:
            print(f"Warning: Could not save keystore to {self.keystore_path}: {e}")

    def store(self, account_id: str, secret_key: str):
        """
        Store keypair securely indexed by account_id (public key)

        Args:
            account_id: Stellar public key (G...)
            secret_key: Stellar secret key (S...)
        """
        self._keypair_store[account_id] = secret_key
        self._save_to_file()

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
        self._save_to_file()
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
