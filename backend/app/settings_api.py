import os
import threading
import time

from fastapi import APIRouter, HTTPException, Request
from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import mask_secret, settings, update_llm_settings


router = APIRouter(prefix="/api", tags=["settings"])
PLACEHOLDER_API_KEYS = {"", "your-api-key-here"}


class PublicSettingsResponse(BaseModel):
    llm_base_url: str
    llm_model: str
    has_api_key: bool
    api_key_masked: str


class UpdateSettingsRequest(BaseModel):
    llm_api_key: str | None = Field(None, max_length=500)
    llm_base_url: str = Field(..., min_length=1, max_length=500)
    llm_model: str = Field(..., min_length=1, max_length=200)


class TestSettingsRequest(BaseModel):
    llm_api_key: str | None = Field(None, max_length=500)
    llm_base_url: str | None = Field(None, max_length=500)
    llm_model: str | None = Field(None, max_length=200)


def _is_configured_api_key(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip() not in PLACEHOLDER_API_KEYS)


def _public_settings() -> PublicSettingsResponse:
    has_api_key = _is_configured_api_key(settings.LLM_API_KEY)
    return PublicSettingsResponse(
        llm_base_url=settings.LLM_BASE_URL,
        llm_model=settings.LLM_MODEL,
        has_api_key=has_api_key,
        api_key_masked=mask_secret(settings.LLM_API_KEY) if has_api_key else "",
    )


@router.get("/settings", response_model=PublicSettingsResponse)
def get_settings():
    return _public_settings()


@router.put("/settings", response_model=PublicSettingsResponse)
def update_settings(req: UpdateSettingsRequest):
    update_llm_settings(req.llm_api_key, req.llm_base_url, req.llm_model)
    return _public_settings()


@router.post("/settings/test")
def test_settings(req: TestSettingsRequest | None = None):
    api_key = (req.llm_api_key.strip() if req and req.llm_api_key and req.llm_api_key.strip() else settings.LLM_API_KEY)
    base_url = (req.llm_base_url.strip() if req and req.llm_base_url and req.llm_base_url.strip() else settings.LLM_BASE_URL)
    model = (req.llm_model.strip() if req and req.llm_model and req.llm_model.strip() else settings.LLM_MODEL)

    if not _is_configured_api_key(api_key):
        raise HTTPException(status_code=400, detail="请先填写 API Key")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "用中文回复两个字：正常"}],
            max_tokens=10,
        )
        return {"ok": True, "message": response.choices[0].message.content or "正常"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


def _is_local_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "localhost"}


@router.post("/shutdown")
def shutdown(request: Request):
    if settings.TESTING:
        return {"ok": True, "message": "测试模式不会退出进程"}

    if not _is_local_request(request):
        raise HTTPException(status_code=403, detail="只允许本机退出 Bloom")

    def exit_later():
        time.sleep(0.5)
        os._exit(0)

    threading.Thread(target=exit_later, daemon=True).start()
    return {"ok": True, "message": "Bloom 正在退出"}
