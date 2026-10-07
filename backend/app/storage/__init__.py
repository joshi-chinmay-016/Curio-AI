"""
Storage abstraction for document file persistence.

Provides a clean interface for saving, deleting, and managing
document files without exposing filesystem implementation details
to the service layer.
"""

from backend.app.storage.local import LocalStorage, get_storage, set_storage

__all__ = ["LocalStorage", "get_storage", "set_storage"]