"""
Authentication Service

Handles user registration, login, password hashing, and JWT token management.
"""


class AuthService:
    """Service for authentication operations."""

    async def register_user(self, email: str, password: str, full_name: str = None):
        """Register a new user with hashed password."""
        # TODO: Hash password, create user record, return user
        pass

    async def authenticate_user(self, email: str, password: str):
        """Validate credentials and return JWT token."""
        # TODO: Verify password, generate JWT token
        pass

    async def create_access_token(self, user_id: str) -> str:
        """Generate a JWT access token."""
        # TODO: Create signed JWT
        pass
