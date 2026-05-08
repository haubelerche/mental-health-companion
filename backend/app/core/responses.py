from typing import Any
from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

def ok(data: Any, status_code: int = 200, response: Response | None = None):
    payload = {"success": True, "data": data, "error": None}
    if response is not None:
        response.status_code = status_code
        return payload
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def fail(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {"code": code, "message": message},
        },
    )
