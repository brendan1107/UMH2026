"""
Authentication Middleware

JWT token validation and user context injection.
"""

# The api/middleware directory is where we place code that acts as middleware for our
#  API routes in FastAPI. 
# Middleware is a layer of code that sits between the incoming HTTP request and the API 
# endpoint.

# In this auth.py file, we define functions that will be used to verify JWT tokens and
# inject user context into the request. This means that when a request comes in with a
# valid JWT token, we can extract the user information and make it available to the API
# endpoint.

#Why veify JWT token?
# JWT (JSON Web Token) is a standard for securely transmitting information between
#  parties as a JSON object. In our application, we use JWT tokens for authentication.
#  When a user logs in, they receive a JWT token that they can include in the 
# Authorization header of their requests. The verify_jwt_token function will check 
# the validity of this token, ensure it hasn't expired, and decode it to extract the 
# user information. This allows our API endpoints to know which user is making the 
# request and to enforce access control based on that user's identity and permissions.

# In simple word, to explain what is JWT token verification: When a user logs in to our 
# application, they receive a special token called a JWT token. This token is like a 
# digital ID card that proves who they are. When the user makes requests to our API, 
# they include this token in their request. The verify_jwt_token function checks this 
# token to make sure it's valid and hasn't expired. If the token is valid, it extracts 
# the user's information from it, so our API knows who is making the request and can 
# give them access to the right data and features based on their identity.
async def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and return decoded payload."""
    # TODO: Implement JWT verification
    pass
