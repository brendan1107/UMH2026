"""
Firebase Initialization

Configures Firebase Admin SDK for Firestore and Storage.
Replaces SQLAlchemy/PostgreSQL — Firestore is a NoSQL document database.
"""
# What is /backend/app/db directory for?
# The /backend/app/db directory contains the database configuration and initialization
#  code for our application. In this case, we are using Firebase Firestore as our 
# database, so this directory includes the setup for the Firebase Admin SDK, which 
# allows us to interact with Firestore and Firebase Storage.

# What is this database.py file for?
# The database.py file is responsible for initializing the Firebase Admin SDK with the
#  necessary credentials and configuration. It sets up the Firestore client and the
#  Firebase Storage bucket that we will use throughout our application to manage data
#  and file uploads. By centralizing this initialization in one file, we can easily 
# import the Firestore client and Storage bucket in our API route handlers and other 
# parts of the application without having to repeat the initialization code. This 
# promotes code reuse and keeps our database access organized.

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.config import settings

# Initialize Firebase Admin SDK
_cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
_app = firebase_admin.initialize_app(_cred, {
    "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
})

# Firestore client
db = firestore.client()

# Storage bucket
bucket = storage.bucket()
