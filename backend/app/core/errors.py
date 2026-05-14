from dataclasses import dataclass
from fastapi.exceptions import RequestValidationError


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int


# ─── Pydantic validation → Vietnamese translation ─────────────────────────────

_FIELD_LABELS: dict[str, str] = {
    "email": "Email",
    "password": "Mật khẩu",
    "new_password": "Mật khẩu mới",
    "display_name": "Tên hiển thị",
    "nickname": "Tên gọi",
    "disclaimer_accepted": "Chấp nhận điều khoản",
    "message": "Nội dung tin nhắn",
    "content": "Nội dung",
    "totp_code": "Mã xác thực",
    "token": "Token",
    "mood": "Tâm trạng",
    "items_text": "Nội dung bữa ăn",
    "meal_slot": "Bữa ăn",
    "session_id": "Phiên trò chuyện",
    "persona_id": "Persona",
}

_ERROR_MSGS: dict[str, str] = {
    "string_too_short": "quá ngắn",
    "string_too_long": "quá dài",
    "missing": "không được để trống",
    "value_error": "không hợp lệ",
    "string_pattern_mismatch": "không đúng định dạng",
    "int_parsing": "phải là số",
    "bool_parsing": "phải là đúng/sai",
    "enum": "giá trị không hợp lệ",
}


def humanize_validation_errors(exc: RequestValidationError) -> str:
    """Convert Pydantic validation errors into a human-readable Vietnamese string."""
    errors = exc.errors()
    messages: list[str] = []

    for err in errors:
        loc = err.get("loc", ())
        field = str(loc[-1]) if loc else "dữ liệu"
        label = _FIELD_LABELS.get(field, field)
        err_type = err.get("type", "")

        # Special handling for common auth validation cases
        if field == "email" and "value_error" in err_type:
            messages.append("Email không đúng định dạng")
        elif field == "password" and "string_too_short" in err_type:
            ctx = err.get("ctx", {})
            min_len = ctx.get("min_length", 8)
            messages.append(f"Mật khẩu phải có ít nhất {min_len} ký tự")
        elif field == "password" and "string_too_long" in err_type:
            messages.append("Mật khẩu quá dài")
        elif field == "display_name" and "string_too_short" in err_type:
            messages.append("Tên hiển thị không được để trống")
        elif err_type == "missing":
            messages.append(f"{label} không được để trống")
        else:
            friendly = _ERROR_MSGS.get(err_type, "không hợp lệ")
            messages.append(f"{label} {friendly}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for m in messages:
        if m not in seen:
            seen.add(m)
            unique.append(m)

    return ". ".join(unique) if unique else "Dữ liệu không hợp lệ"
