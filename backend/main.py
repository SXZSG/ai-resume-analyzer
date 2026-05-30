import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cache import get_cache, make_cache_key, set_cache
from llm_client import LLMClientError, analyze_match, extract_resume_info
from parser import PDFParseError, extract_text_from_pdf
from schemas import AnalyzeData
from scoring import calculate_match_score


logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Resume Analyzer",
    description="AI 赋能的智能简历分析系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze_resume(
    resume: Optional[UploadFile] = File(default=None),
    job_description: Optional[str] = Form(default=None),
) -> JSONResponse:
    try:
        validation_error = validate_request(resume, job_description)
        if validation_error:
            return error_response(validation_error, status_code=400)

        assert resume is not None
        assert job_description is not None

        pdf_bytes = await resume.read()
        if not pdf_bytes:
            return error_response("没有上传文件或文件内容为空。", status_code=400)
        if not pdf_bytes.startswith(b"%PDF"):
            return error_response("文件不是有效的 PDF。", status_code=400)

        try:
            resume_text = extract_text_from_pdf(pdf_bytes)
        except PDFParseError as exc:
            return error_response(str(exc), status_code=400)

        cache_key = make_cache_key(resume_text, job_description)
        cached = get_cache(cache_key)
        if cached:
            return success_response("Analyze successfully.", cached, cached=True)

        resume_info = extract_resume_info(resume_text)
        rule_match = calculate_match_score(resume_info, job_description, resume_text)
        llm_comment = analyze_match(resume_info, job_description, rule_match)

        match_result = {
            **rule_match,
            "advantages": llm_comment.get("advantages", []),
            "risks": llm_comment.get("risks", []),
            "summary": llm_comment.get("summary") or rule_match.get("summary", ""),
        }
        data = {
            **resume_info,
            "match_result": match_result,
            "raw_text_preview": resume_text[:1000],
        }
        normalized_data = dump_model(AnalyzeData(**data))
        set_cache(cache_key, normalized_data)
        return success_response("Analyze successfully.", normalized_data, cached=False)

    except LLMClientError as exc:
        logger.exception("LLM call failed")
        return error_response(str(exc), status_code=502)
    except Exception:
        logger.exception("Unexpected service error")
        return error_response("服务内部错误。", status_code=500)


def validate_request(resume: Optional[UploadFile], job_description: Optional[str]) -> str:
    if resume is None:
        return "没有上传文件。"
    if not (job_description or "").strip():
        return "岗位 JD 不能为空。"

    filename = resume.filename or ""
    content_type = resume.content_type or ""
    is_pdf_filename = filename.lower().endswith(".pdf")
    is_pdf_content_type = content_type.lower() in {"application/pdf", "application/x-pdf"}
    if not (is_pdf_filename or is_pdf_content_type):
        return "文件不是 PDF。"
    return ""


def success_response(message: str, data: Dict[str, Any], cached: bool) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": message,
            "data": data,
            "cached": cached,
        },
    )


def error_response(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "data": None,
        },
    )


def dump_model(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
