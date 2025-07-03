"""Base model for objects that sync with a remote backend."""
from typing import Any, Dict
from pydantic import BaseModel


class RemoteModel(BaseModel):
    """Base model that tracks changes and syncs with remote backend."""

    _sync: bool = True
    _transaction: Dict[str, Any] = {}

    def __init__(self, _sync: bool = True, **data):
        super().__init__(**data)
        self._sync = _sync
        self._transaction = {}

    def __setattr__(self, name: str, value: Any):
        # Skip private attributes
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        # Get old value if exists
        old_value = getattr(self, name, None) if hasattr(self, name) else None

        # Set the value
        super().__setattr__(name, value)

        # Track change if value changed
        if old_value != value:
            self._transaction[name] = value

            # Auto-commit if sync is enabled
            if self._sync:
                self.commit()

    def __enter__(self):
        """Enter transaction mode - disable auto-sync."""
        self._old_sync = self._sync
        self._sync = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction mode - commit changes."""
        self._sync = self._old_sync
        if self._transaction:
            self.commit()

    @classmethod
    def from_remote(cls, **data):
        """Create instance from remote data without syncing back."""
        instance = cls(sync=False, **data)
        instance._drop_transaction()
        return instance

    def _drop_transaction(self):
        """Clear pending changes without committing."""
        self._transaction.clear()

    @property
    def dirty_fields(self):
        """Get list of fields with pending changes."""
        return list(self._transaction.keys())

    def commit(self):
        """Commit pending changes to remote backend.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement commit()")

    class Config:
        # Pydantic config
        arbitrary_types_allowed = True
