"""
Local filesystem storage implementation for document files.

Provides secure, streaming file operations with:
- Collision-resistant storage paths
- Streaming upload with size enforcement
- SHA-256 content hashing
- Safe path construction preventing traversal attacks
"""
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

from backend.app.core.config import settings


class LocalStorage:
    """Local filesystem storage for document files."""

    def __init__(self, storage_root: Optional[str] = None, max_file_size: Optional[int] = None):
        self._storage_root = Path(storage_root or settings.DOCUMENT_STORAGE_ROOT).resolve()
        self._max_file_size = max_file_size or settings.MAX_UPLOAD_SIZE
        self._chunk_size = settings.UPLOAD_CHUNK_SIZE
        self._allowed_mime_types = settings.ALLOWED_DOCUMENT_MIME_TYPES
        self._allowed_extensions = settings.ALLOWED_DOCUMENT_EXTENSIONS

        # Ensure storage root and temp directory exist
        self._storage_root.mkdir(parents=True, exist_ok=True)
        self._temp_dir = self._storage_root / "tmp"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def storage_root(self) -> Path:
        return self._storage_root

    @property
    def max_file_size(self) -> int:
        return self._max_file_size

    def _get_safe_extension(self, filename: str, mime_type: str) -> str:
        """Extract safe extension from filename, validated against MIME type."""
        # Get extension from filename
        ext = Path(filename).suffix.lower()
        
        # Validate extension is in allowed list
        if not ext or ext not in self._allowed_extensions:
            raise ValueError(f"File extension '{ext}' is not allowed. Allowed: {self._allowed_extensions}")
        
        # Cross-reference with MIME type
        mime_to_ext = {
            "application/pdf": ".pdf",
            "text/plain": ".txt",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        }
        expected_ext = mime_to_ext.get(mime_type)
        if expected_ext and ext != expected_ext:
            raise ValueError(f"File extension '{ext}' does not match MIME type '{mime_type}'")
        
        # Also validate MIME type is allowed
        if mime_type not in self._allowed_mime_types:
            raise ValueError(f"MIME type '{mime_type}' is not allowed. Allowed: {self._allowed_mime_types}")
        
        return ext

    def _build_storage_path(self, user_id: UUID, document_id: UUID, extension: str) -> Path:
        """Build secure storage path: storage_root/documents/<user_id>/<document_id><ext>"""
        # Use user_id and document_id for collision-resistant paths
        # This prevents cross-user collisions and path traversal
        user_dir = self._storage_root / "documents" / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Use document_id as filename with safe extension
        safe_filename = f"{document_id}{extension}"
        return user_dir / safe_filename

    def validate_file_type(self, filename: str, mime_type: str) -> str:
        """Validate file type and return safe extension."""
        return self._get_safe_extension(filename, mime_type)

    def save_uploaded_file(
        self,
        upload_file,
        user_id: UUID,
        document_id: UUID,
        filename: str,
        mime_type: str,
    ) -> Tuple[Path, int, str]:
        """
        Stream uploaded file to storage with size limit and hash calculation.
        
        Returns:
            Tuple of (storage_path, actual_file_size, sha256_hash)
        
        Raises:
            ValueError: If file type not allowed, empty file, or size exceeded
            IOError: If storage write fails
        """
        # Validate file type
        extension = self.validate_file_type(filename, mime_type)
        
        # Determine final storage path
        final_path = self._build_storage_path(user_id, document_id, extension)
        
        # Use temporary file for atomic write
        temp_fd, temp_path = tempfile.mkstemp(
            prefix=f"upload_{document_id}_",
            dir=self._temp_dir,
        )
        os.close(temp_fd)
        temp_path = Path(temp_path)
        
        try:
            sha256 = hashlib.sha256()
            total_size = 0
            
            # Stream file in chunks
            while True:
                chunk = upload_file.file.read(self._chunk_size)
                if not chunk:
                    break
                
                total_size += len(chunk)
                
                # Enforce size limit during streaming
                if total_size > self._max_file_size:
                    raise ValueError(
                        f"File size exceeds maximum allowed size of {self._max_file_size} bytes"
                    )
                
                # Write chunk and update hash
                with open(temp_path, "ab") as f:
                    f.write(chunk)
                sha256.update(chunk)
            
            # Check for empty file
            if total_size == 0:
                raise ValueError("Empty file uploads are not allowed")
            
            # Move temp file to final location (atomic on same filesystem)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(temp_path), str(final_path))
            
            return final_path, total_size, sha256.hexdigest()
            
        except Exception:
            # Clean up temp file on any error
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def delete_file(self, storage_path: Path) -> bool:
        """
        Delete a stored file.
        
        Returns True if file was deleted, False if it didn't exist.
        Never raises on missing file.
        """
        try:
            if storage_path.exists():
                storage_path.unlink()
                # Clean up empty parent directories
                self._cleanup_empty_dirs(storage_path.parent)
                return True
            return False
        except Exception:
            return False

    def _cleanup_empty_dirs(self, path: Path) -> None:
        """Recursively remove empty parent directories up to storage root."""
        try:
            current = path.resolve()
            storage_root = self._storage_root.resolve()
            
            while current != storage_root and current.parent != current:
                if current.exists() and current.is_dir() and not any(current.iterdir()):
                    current.rmdir()
                    current = current.parent
                else:
                    break
        except Exception:
            pass  # Best effort cleanup

    def file_exists(self, storage_path: Path) -> bool:
        """Check if a stored file exists."""
        return storage_path.exists() and storage_path.is_file()

    def get_file_size(self, storage_path: Path) -> Optional[int]:
        """Get size of stored file in bytes."""
        try:
            return storage_path.stat().st_size
        except Exception:
            return None


# Singleton instance
_storage_instance: Optional[LocalStorage] = None


def get_storage() -> LocalStorage:
    """Get the global storage instance (singleton pattern)."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalStorage()
    return _storage_instance


def set_storage(storage: LocalStorage) -> None:
    """Set the global storage instance (for testing)."""
    global _storage_instance
    _storage_instance = storage