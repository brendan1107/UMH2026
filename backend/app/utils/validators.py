"""
Input Validators

Common validation utilities for user inputs.
"""


def validate_email(email: str) -> bool:
    """Validate email format."""
    # TODO: Implement email validation
    pass


def validate_file_type(content_type: str, allowed_types: list) -> bool:
    """Validate uploaded file type against allowed list."""
    return content_type in allowed_types


ALLOWED_UPLOAD_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "text/plain",
    "text/csv",
]

MAX_UPLOAD_SIZE_MB = 10
