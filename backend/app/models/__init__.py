# Database Models (Firestore Document Schemas)
# These define the structure of documents stored in Firebase Firestore.
# Firestore is NoSQL — no foreign keys or joins, but we maintain
# the same logical relationships via document references and subcollections.
#
# Collection structure:
#   users/{uid}
#   business_cases/{case_id}
#   business_cases/{case_id}/chat_sessions/{session_id}
#   business_cases/{case_id}/chat_sessions/{session_id}/messages/{msg_id}
#   business_cases/{case_id}/extracted_facts/{fact_id}
#   business_cases/{case_id}/recommendations/{rec_id}
#   business_cases/{case_id}/recommendations/{rec_id}/tasks/{task_id}
#   business_cases/{case_id}/evidence_uploads/{upload_id}
#   business_cases/{case_id}/place_results/{place_id}
#   report_exports/{export_id}
