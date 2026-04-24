"""
Firestore Session / Client Access

Provides the Firestore client for use across the application.
"""
# What is session.py for?
# The session.py file in the app/db directory is responsible for providing access to 
# the Firestore client instance that we initialized in database.py. It defines 
# functions like get_db() and get_storage_bucket() that return the Firestore client and
#  Firebase Storage bucket instances, respectively. These functions can be used as 
# dependencies in our API route handlers to interact with the database and manage file
#  uploads without having to initialize the clients multiple times throughout the 
# application. This approach promotes code reuse and keeps our database access 
# organized. 

#Example usage of session.py:
# In our API route handlers (e.g., in cases.py), we can use the get_db() function as a
#  dependency to access the Firestore client. For instance, when we want to create a 
# new case or retrieve case details, we can call get_db() to get the Firestore client
#  and perform the necessary database operations. Similarly, if we need to handle file 
# uploads for evidence, we can use get_storage_bucket() to access the Firebase Storage
#  bucket and manage our file uploads efficiently. This setup allows us to keep our 
# database interactions clean and consistent across our application.
from app.db.database import db, bucket


def get_db():
    """Return the Firestore client instance."""
    return db


def get_storage_bucket():
    """Return the Firebase Storage bucket instance."""
    return bucket
