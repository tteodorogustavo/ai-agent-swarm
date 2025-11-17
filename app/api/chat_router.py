"""
chat_router.py
This file defines the API endpoints using FastAPI's APIRouter.
It acts as the "waiter" that receives user requests at specific endpoints (e.g., /api/v1/chat), validates them using the models from models.py, and forwards valid requests to the core logic (the agent graph).
Purpose: API routing logic, request validation, and response delivery.
"""