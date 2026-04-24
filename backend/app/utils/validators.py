"""
Input Validators

Common validation utilities for user inputs.
"""

import re

#Why this validators.py file does not have a class like other utils file?
# The validators.py file is designed to contain standalone utility functions for validating user inputs, such as email formats and file types. Since these functions are simple and do not require maintaining any state or complex interactions, we can define them as independent functions rather than encapsulating them within a class. This approach keeps the code straightforward and easy to use, as we can directly call these validation functions without needing to instantiate a class. In contrast, other utility files like file_processor.py and pdf_generator.py contain classes because they may need to maintain state or have multiple related methods that logically belong together, making a class structure more appropriate for those cases.

# Can i change this to a class based structure?
# Yes, you could change this to a class-based structure if you prefer that style. For example, you could define a Validator class and make these functions static methods of that class. However, since these validation functions are simple and do not require any shared state or complex interactions, it may be more straightforward to keep them as standalone functions. Using a class for this purpose might add unnecessary complexity without providing significant benefits in terms of organization or functionality. Ultimately, the choice between a class-based structure and standalone functions depends on your coding style preferences and the specific needs of your application.

def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    return bool(
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email.strip(),
        )
    )


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
