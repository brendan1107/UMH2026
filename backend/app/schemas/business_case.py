"""Business case request/response schemas."""

# What is this app/schemas directory for?
# The app/schemas directory contains Pydantic models that define the structure of the data we expect to receive in API requests and send in API responses. These schemas help us validate incoming data and ensure that our API endpoints receive the correct information in the expected format. For example, when a client sends a request to create a new business case, we can use the CaseCreate schema to validate the request body and ensure it contains all the necessary fields with the correct data types. Similarly, when we return data about a business case in an API response, we can use the CaseResponse schema to structure that response consistently. This approach promotes data integrity and makes it easier to maintain and understand our API's input and output formats.

#What is pydantic model?
# In simple words, a Pydantic model is like a blueprint for the data we expect to work with in our application. It defines what fields we need, what types of data those fields should contain, and whether any of those fields are optional. When we use a Pydantic model to create an instance, it checks that the data we provided matches the blueprint and gives us an error if something is wrong. This helps us catch mistakes early and ensures that our API works smoothly with the right kind of data.

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    stage: str = "new"  # new | existing
    business_type: Optional[str] = None
    target_location: Optional[str] = None
    budget_myr: Optional[float] = None       # startup budget in MYR, used by AI agent


class CaseUpdate(BaseModel):
    """Fields the client is allowed to update on a case."""
    title: Optional[str] = None
    description: Optional[str] = None
    stage: Optional[str] = None
    business_type: Optional[str] = None
    target_location: Optional[str] = None
    status: Optional[str] = None


class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    stage: str
    business_type: Optional[str]
    target_location: Optional[str]
    status: str
    created_at: datetime
    budget_myr: Optional[float] = None       # included in response so frontend can display it

    class Config:
        from_attributes = True