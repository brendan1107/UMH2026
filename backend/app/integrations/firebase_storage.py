"""
Firebase Storage Client

Handles file uploads and downloads for evidence (images, documents).
Uses Firebase Admin SDK's storage module.
"""

# What is this app/integrations directory for?
# The app/integrations directory contains code for integrating third-party services and APIs that our application relies on. This includes services like Firebase for storage and database, AI models for analysis, and Google APIs for calendar integration. By organizing our integration code in this directory, we can keep our application modular and maintainable, making it easier to manage external dependencies and interactions with third-party services.

# What is this firebase_storage.py file for?
# The firebase_storage.py file defines a client for interacting with Firebase Storage. It provides methods for uploading files, retrieving download URLs, deleting files, and checking if a file exists in storage. This client will be used in our API route handlers (e.g., in uploads.py) to manage evidence file uploads related to business cases. By encapsulating the Firebase Storage interactions in this client, we can keep our code organized and make it easier to manage file uploads across our application.

from firebase_admin import storage
from app.db.database import bucket


class FirebaseStorageClient:
    """Client for Firebase Storage."""

    def __init__(self):
        self.bucket = bucket

    async def upload_file(self, destination_path: str, file_data: bytes, content_type: str = None) -> str:
        """
        Upload a file to Firebase Storage.

        Args:
            destination_path: Path in storage (e.g., "evidence/case_123/photo.jpg")
            file_data: File bytes
            content_type: MIME type

        Returns:
            The public download URL.
        """
        blob = self.bucket.blob(destination_path)
        blob.upload_from_string(file_data, content_type=content_type)
        blob.make_public()
        return blob.public_url

    async def get_download_url(self, storage_path: str) -> str:
        """Get the public URL for a stored file."""
        blob = self.bucket.blob(storage_path)
        blob.make_public()
        return blob.public_url

    async def delete_file(self, storage_path: str):
        """Delete a file from Firebase Storage."""
        blob = self.bucket.blob(storage_path)
        blob.delete()

    async def file_exists(self, storage_path: str) -> bool:
        """Check if a file exists in storage."""
        blob = self.bucket.blob(storage_path)
        return blob.exists()
