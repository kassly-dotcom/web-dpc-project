"""Помилки у форматі Problem Details (RFC 9457), application/problem+json.

Будь-який обробник може кинути ProblemError — клієнт отримає тіло з полями
type/title/status/detail/code (+ request_id, якщо його поставив middleware О1.6).
Помилки валідації FastAPI (422) і пошкоджений JSON (400) теж перетворюються на Problem.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_BASE = "https://laundry.example.test/problems/"
PROBLEM_MEDIA_TYPE = "application/problem+json"


class ProblemError(Exception):
    def __init__(self, status: int, code: str, title: str, detail: str | None = None, **extra):
        super().__init__(detail or title)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.extra = extra


def problem_response(request: Request, status: int, code: str, title: str,
                     detail: str | None = None, **extra) -> JSONResponse:
    body = {
        "type": PROBLEM_BASE + code.replace("_", "-"),
        "title": title,
        "status": status,
        "code": code,
    }
    if detail:
        body["detail"] = detail
    request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id")
    if request_id:
        body["request_id"] = request_id
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE)


def _field_name(loc) -> str:
    return ".".join(str(part) for part in loc)


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem(request: Request, exc: ProblemError):
        return problem_response(request, exc.status, exc.code, exc.title, exc.detail, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        # Тіло, яке взагалі не є JSON, — це 400, а не 422.
        if any(e.get("type") == "json_invalid" for e in errors):
            msg = next(e.get("ctx", {}).get("error", "") for e in errors if e.get("type") == "json_invalid")
            return problem_response(request, 400, "malformed_json", "Malformed JSON", str(msg) or None)
        items = [{"field": _field_name(e["loc"]), "message": e["msg"]} for e in errors]
        detail = f"{len(items)} field{'s are' if len(items) != 1 else ' is'} invalid"
        return problem_response(request, 422, "validation_error", "Validation error", detail, errors=items)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return problem_response(request, exc.status_code, code, str(exc.detail))
