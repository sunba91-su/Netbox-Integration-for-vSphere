from __future__ import annotations


class DomainError(Exception):
    """Base exception for all domain-level errors."""


class ConfigError(DomainError):
    """Configuration is invalid or incomplete."""


class CredentialNotFoundError(ConfigError):
    """A required credential could not be resolved from any source."""


class ConnectionError(DomainError):
    """Could not connect to an external system."""


class VCenterConnectionError(ConnectionError):
    """Could not connect to vCenter."""


class NetBoxConnectionError(ConnectionError):
    """Could not connect to NetBox."""


class VaultConnectionError(ConnectionError):
    """Could not connect to Vault."""


class SyncError(DomainError):
    """Error during sync execution."""


class EntityNotFoundError(DomainError):
    """A required entity could not be found by natural key."""


class NaturalKeyError(DomainError):
    """Natural key construction or matching failed."""


class BootstrapError(DomainError):
    """NetBox metadata bootstrap failed."""


class LockError(DomainError):
    """Could not acquire or release the sync lock."""


class LockAcquiredError(LockError):
    """Another sync process holds the lock."""


class LockStaleError(LockError):
    """Lock file exists but process is dead — removed and re-acquired."""
