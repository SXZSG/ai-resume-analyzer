import json
import os
import re
from typing import Any, Dict, List

import requests

from scoring import extract_keywords_from_text


class LLMClientError(Exception):
    """Raised when the configured LLM service cannot return usable JSON."""


DEFAULT_RESUME_INFO: Dict[str, Any] = {
    "basic_info": {
        "name": "",
        "phone": "",
        "email": "",
        "address": "",
    },
    "job_intention": {
        "position": "",
        "expected_salary": "",
    },
    "background": {
        "education": "",
        "work_years": "",
        "skills": [],
        "projects": [],
        "experiences": [],
    },
}


def extract_resume_info(resume_text: str) -> Dict[str, Any]:
    """Extract structured resume fields. Falls back to mock parsing without an API key."""
    if not os.getenv("LLM_API_KEY"):
        return mock_extract_resume_info(resume_text)

    prompt = (
        "你是招聘系统中的简历信息抽取器。请只返回严格 JSON，不要 Markdown。\n"
        "字段结构必须为：basic_info{name,phone,email,address}, "
        "job_intention{position,expected_salary}, "
        "background{education,work_years,skills,projects,experiences}。\n"
        "数组字段必须返回字符串数组，未知字段返回空字符串或空数组。"
    )
    payload = call_openai_compatible_json(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": resume_text[:14000]},
        ],
        temperature=0,
    )
    return normalize_resume_info(payload)


def analyze_match(
    resume_info: Dict[str, Any],
    job_description: str,
    rule_match: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate readable match comments. Falls back to deterministic mock comments."""
    if not os.getenv("LLM_API_KEY"):
        return mock_analyze_match(resume_info, job_description, rule_match)

    prompt = (
        "你是招聘简历评估助手。请基于规则评分结果补充优势、风险和总结。"
        "只返回严格 JSON，结构为："
        '{"advantages":[""],"risks":[""],"summary":""}。'
        "不要修改分数，不要输出 Markdown。"
    )
    payload = call_openai_compatible_json(
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "resume_info": resume_info,
                        "job_description": job_description,
                        "rule_match": rule_match,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0.2,
    )
    return normalize_match_comment(payload)


def call_openai_compatible_json(messages: List[Dict[str, str]], temperature: float = 0) -> Dict[str, Any]:
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        raise LLMClientError("未配置 LLM_API_KEY。")

    url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=60)
        response.raise_for_status()
        raw = response.json()
        content = raw["choices"][0]["message"]["content"]
    except Exception as exc:
        raise LLMClientError(f"大模型调用失败：{exc}") from exc

    try:
        parsed = tolerant_json_loads(content)
    except ValueError as exc:
        raise LLMClientError("大模型返回结果不是合法 JSON。") from exc

    if not isinstance(parsed, dict):
        raise LLMClientError("大模型返回 JSON 必须是对象。")
    return parsed


def tolerant_json_loads(content: str) -> Any:
    """Parse JSON with a small amount of tolerance for fenced or prefixed output."""
    if not content:
        raise ValueError("empty content")

    content = content.strip()
    content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE).strip()
    content = re.sub(r"```$", "", content).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(content[start : end + 1])


def mock_extract_resume_info(resume_text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    text = "\n".join(lines)

    email = first_match(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    phone = first_match(r"(?:\+?86[-\s]?)?1[3-9]\d{9}|(?:\+?\d{1,3}[-\s]?)?(?:\d[-\s]?){7,12}\d", text)
    name = (
        first_match(r"(?:姓名|Name)[:：\s]+([^\n，,]{2,30})", text)
        or infer_name_from_first_lines(lines)
    )
    address = first_match(r"(?:地址|住址|Address)[:：\s]+([^\n]{2,80})", text)
    position = first_match(r"(?:求职意向|应聘岗位|目标岗位|Position)[:：\s]+([^\n]{2,80})", text)
    expected_salary = first_match(r"(?:期望薪资|薪资要求|Expected Salary)[:：\s]+([^\n]{2,50})", text)
    education = extract_education(text)
    work_years = extract_work_years(text)
    skills = extract_skills(text)
    projects = extract_section_items(text, ("项目经历", "项目经验", "Projects", "Project Experience"), limit=5)
    experiences = extract_section_items(text, ("工作经历", "实习经历", "Work Experience", "Experience"), limit=5)

    return normalize_resume_info(
        {
            "basic_info": {
                "name": name,
                "phone": phone,
                "email": email,
                "address": address,
            },
            "job_intention": {
                "position": position,
                "expected_salary": expected_salary,
            },
            "background": {
                "education": education,
                "work_years": work_years,
                "skills": skills,
                "projects": projects,
                "experiences": experiences,
            },
        }
    )


def mock_analyze_match(
    resume_info: Dict[str, Any],
    job_description: str,
    rule_match: Dict[str, Any],
) -> Dict[str, Any]:
    matched = rule_match.get("matched_keywords") or []
    missing = rule_match.get("missing_keywords") or []
    overall_score = int(rule_match.get("overall_score") or 0)

    advantages: List[str] = []
    risks: List[str] = []

    if matched:
        advantages.append(f"简历覆盖了岗位中的核心关键词：{'、'.join(matched[:5])}。")
    if resume_info.get("background", {}).get("projects"):
        advantages.append("存在可用于进一步追问的项目经历。")
    if overall_score >= 75:
        advantages.append("综合评分较高，可进入下一轮筛选。")

    if missing:
        risks.append(f"岗位关键词缺口包括：{'、'.join(missing[:5])}。")
    if not resume_info.get("background", {}).get("experiences"):
        risks.append("工作经历信息较少，建议面试时核实项目角色和产出。")
    if overall_score < 60:
        risks.append("综合匹配度偏低，需要结合业务背景谨慎判断。")

    if overall_score >= 80:
        summary = "候选人与 JD 匹配度较高，建议重点核实项目深度、职责边界和稳定性。"
    elif overall_score >= 60:
        summary = "候选人与 JD 存在一定匹配基础，建议围绕缺失关键词和真实项目贡献做进一步沟通。"
    else:
        summary = "候选人与 JD 的显性匹配度不足，建议作为备选或补充材料后再评估。"

    return normalize_match_comment(
        {
            "advantages": advantages,
            "risks": risks,
            "summary": summary,
        }
    )


def normalize_resume_info(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = json.loads(json.dumps(DEFAULT_RESUME_INFO, ensure_ascii=False))
    for section in ("basic_info", "job_intention", "background"):
        if isinstance(payload.get(section), dict):
            result[section].update(payload[section])

    background = result["background"]
    for key in ("skills", "projects", "experiences"):
        background[key] = ensure_string_list(background.get(key))

    for section in ("basic_info", "job_intention"):
        for key, value in result[section].items():
            result[section][key] = str(value or "").strip()

    for key in ("education", "work_years"):
        background[key] = str(background.get(key) or "").strip()

    return result


def normalize_match_comment(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "advantages": ensure_string_list(payload.get("advantages")),
        "risks": ensure_string_list(payload.get("risks")),
        "summary": str(payload.get("summary") or "").strip(),
    }


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text or "", flags=re.IGNORECASE)
    if not match:
        return ""
    value = match.group(1) if match.groups() else match.group(0)
    return value.strip(" ：:，,;；")


def infer_name_from_first_lines(lines: List[str]) -> str:
    for line in lines[:8]:
        if any(marker in line for marker in ("简历", "Resume", "电话", "邮箱", "@")):
            continue
        if 2 <= len(line) <= 30 and not re.search(r"\d", line):
            return line
    return ""


def extract_education(text: str) -> str:
    education_lines = [
        line.strip()
        for line in text.splitlines()
        if any(keyword in line for keyword in ("本科", "硕士", "博士", "学士", "研究生", "大学", "学院"))
        or re.search(r"\b(Bachelor|Master|PhD|Doctor|University|College)\b", line, flags=re.IGNORECASE)
    ]
    return "；".join(education_lines[:3])


def extract_work_years(text: str) -> str:
    patterns = [
        r"(\d+\s*年(?:以上)?(?:工作)?经验)",
        r"(工作年限[:：\s]*\d+\s*年)",
        r"(\d+\s*(?:years?|yrs?)\s*(?:of)?\s*experience)",
    ]
    for pattern in patterns:
        value = first_match(pattern, text)
        if value:
            return value
    return ""


def extract_skills(text: str) -> List[str]:
    skills = extract_keywords_from_text(text)
    skill_line = first_match(r"(?:技能|专业技能|Skills)[:：\s]+([^\n]{2,300})", text)
    if skill_line:
        pieces = re.split(r"[,，/、;；\s]+", skill_line)
        for piece in pieces:
            piece = piece.strip()
            if 2 <= len(piece) <= 30:
                skills.append(piece)
    return ensure_string_list(skills)


def extract_section_items(text: str, headers: tuple[str, ...], limit: int = 5) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items: List[str] = []
    capture = False
    stop_headers = ("教育经历", "专业技能", "技能", "自我评价", "证书", "获奖", "基本信息")

    for line in lines:
        if any(header.lower() in line.lower() for header in headers):
            capture = True
            continue
        if capture and any(header in line for header in stop_headers):
            break
        if capture and 8 <= len(line) <= 180:
            items.append(line)
        if len(items) >= limit:
            break

    return ensure_string_list(items)


def ensure_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        values = re.split(r"[,，;；、\n]+", value)
    else:
        values = [str(value)]

    result: List[str] = []
    seen = set()
    for item in values:
        item = str(item or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
