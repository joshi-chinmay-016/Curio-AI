from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

class CurioException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class ResourceNotFoundError(CurioException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

class InvalidStateTransitionError(CurioException):
    def __init__(self, message: str = "Invalid mode transition"):
        super().__init__(message, code="INVALID_TRANSITION", status_code=status.HTTP_400_BAD_REQUEST)

class AIServiceError(CurioException):
    def __init__(self, message: str = "Failed to communicate with AI Provider"):
        super().__init__(message, code="AI_PROVIDER_ERROR", status_code=status.HTTP_502_BAD_GATEWAY)

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CurioException)
    async def curio_exception_handler(request: Request, exc: CurioException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred."
            }
        )
