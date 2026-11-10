"""Unified error model: every error response is {error_code, message, details}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: object) -> None:
        super().__init__(
            404,
            f"{resource.upper()}_NOT_FOUND",
            f"{resource.capitalize()} '{resource_id}' was not found. It may have been deleted.",
        )


def error_body(error_code: str, message: str, details: Any | None = None) -> dict:
    body: dict[str, Any] = {"error_code": error_code, "message": message}
    if details is not None:
        body["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body(
                "VALIDATION_ERROR",
                "Some request parameters are invalid. Check the highlighted fields and try again.",
                details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
        import logging

        logging.getLogger("loglens").exception("Unhandled error")
        return JSONResponse(
            status_code=500,
            content=error_body(
                "INTERNAL_ERROR",
                "An unexpected server error occurred. Please retry; if it persists, check the server logs.",
            ),
        )
