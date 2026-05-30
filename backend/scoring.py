import re
from typing import Any, Dict, Iterable, List, Sequence, Set


TECH_KEYWORDS: Sequence[str] = (
    "Python",
    "Java",
    "C++",
    "FastAPI",
    "Flask",
    "Django",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "Redis",
    "Docker",
    "Linux",
    "Git",
    "RESTful",
    "Machine Learning",
    "Deep Learning",
    "PyTorch",
    "TensorFlow",
    "NLP",
    "LLM",
    "CV",
    "YOLO",
    "Transformer",
    "Pandas",
    "NumPy",
    "JavaScript",
    "TypeScript",
    "Vue",
    "React",
    "HTML",
    "CSS",
    "PyMuPDF",
    "FastAPI",
    "API",
)

CHINESE_KEYWORDS: Sequence[str] = (
    "后端",
    "前端",
    "算法",
    "机器学习",
    "深度学习",
    "自然语言处理",
    "大模型",
    "简历解析",
    "数据分析",
    "数据挖掘",
    "计算机视觉",
    "数据库",
    "缓存",
    "部署",
    "阿里云",
    "函数计算",
    "微服务",
    "接口设计",
)

DEGREE_LEVELS = {
    "博士": 4,
    "doctor": 4,
    "phd": 4,
    "硕士": 3,
    "研究生": 3,
    "master": 3,
    "本科": 2,
    "学士": 2,
    "bachelor": 2,
    "大专": 1,
    "专科": 1,
    "college": 1,
}


def calculate_match_score(
    resume_info: Dict[str, Any],
    job_description: str,
    resume_text: str = "",
) -> Dict[str, Any]:
    """Calculate deterministic rule-based JD matching scores."""
    required_keywords = extract_jd_keywords(job_description)
    resume_keywords = extract_resume_keywords(resume_info, resume_text)

    matched_keywords = sorted(required_keywords & resume_keywords, key=str.lower)
    missing_keywords = sorted(required_keywords - resume_keywords, key=str.lower)

    skill_score = calculate_skill_score(required_keywords, resume_keywords)
    experience_score = calculate_experience_score(
        resume_info=resume_info,
        job_description=job_description,
        required_keywords=required_keywords,
        resume_text=resume_text,
    )
    education_score = calculate_education_score(resume_info, job_description)

    overall_score = clamp_score(
        round(skill_score * 0.5 + experience_score * 0.3 + education_score * 0.2)
    )

    return {
        "overall_score": overall_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "advantages": [],
        "risks": [],
        "summary": build_rule_summary(overall_score, matched_keywords, missing_keywords),
    }


def extract_jd_keywords(job_description: str) -> Set[str]:
    keywords = set(extract_keywords_from_text(job_description))

    for keyword in CHINESE_KEYWORDS:
        if keyword in job_description:
            keywords.add(keyword)

    return keywords


def extract_resume_keywords(resume_info: Dict[str, Any], resume_text: str = "") -> Set[str]:
    background = resume_info.get("background") or {}
    parts: List[str] = [resume_text]

    for key in ("education", "work_years"):
        value = background.get(key)
        if isinstance(value, str):
            parts.append(value)

    for key in ("skills", "projects", "experiences"):
        value = background.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, str):
            parts.append(value)

    text = "\n".join(parts)
    keywords = set(extract_keywords_from_text(text))
    for keyword in CHINESE_KEYWORDS:
        if keyword in text:
            keywords.add(keyword)
    return keywords


def extract_keywords_from_text(text: str) -> List[str]:
    if not text:
        return []

    found: List[str] = []
    for keyword in TECH_KEYWORDS:
        if contains_keyword(text, keyword):
            found.append(keyword)
    return dedupe_preserve_order(found)


def calculate_skill_score(required_keywords: Set[str], resume_keywords: Set[str]) -> int:
    if not required_keywords:
        return 60 if resume_keywords else 30

    ratio = len(required_keywords & resume_keywords) / len(required_keywords)
    return clamp_score(round(ratio * 100))


def calculate_experience_score(
    resume_info: Dict[str, Any],
    job_description: str,
    required_keywords: Set[str],
    resume_text: str = "",
) -> int:
    background = resume_info.get("background") or {}
    projects = ensure_list(background.get("projects"))
    experiences = ensure_list(background.get("experiences"))
    combined_experience_text = "\n".join(projects + experiences + [resume_text])

    if required_keywords:
        matched_in_experience = {
            keyword for keyword in required_keywords if contains_keyword(combined_experience_text, keyword)
        }
        keyword_component = (len(matched_in_experience) / len(required_keywords)) * 50
    else:
        keyword_component = 25 if combined_experience_text.strip() else 0

    context_component = min(30, len(projects) * 8 + len(experiences) * 10)

    required_years = extract_required_years(job_description)
    resume_years = extract_resume_years(background.get("work_years", ""), resume_text)
    if required_years:
        years_component = min(20, (resume_years / required_years) * 20) if resume_years else 0
    else:
        years_component = min(20, resume_years * 5) if resume_years else 10 if experiences else 0

    return clamp_score(round(keyword_component + context_component + years_component))


def calculate_education_score(resume_info: Dict[str, Any], job_description: str) -> int:
    background = resume_info.get("background") or {}
    education_text = str(background.get("education") or "")

    required_level = extract_degree_level(job_description)
    resume_level = extract_degree_level(education_text)

    if not required_level:
        return 80 if resume_level else 50
    if not resume_level:
        return 40
    if resume_level >= required_level:
        return 100
    if resume_level + 1 == required_level:
        return 70
    return 45


def contains_keyword(text: str, keyword: str) -> bool:
    if not text or not keyword:
        return False

    if re.fullmatch(r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*", keyword):
        pattern = rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None

    return keyword.casefold() in text.casefold()


def extract_required_years(text: str) -> int:
    patterns = [
        r"(\d+)\s*年(?:以上|及以上)?(?:工作)?经验",
        r"(\d+)\s*\+\s*年",
        r"(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*experience",
    ]
    return max(extract_numbers_by_patterns(text, patterns), default=0)


def extract_resume_years(work_years_text: str, resume_text: str = "") -> int:
    text = f"{work_years_text}\n{resume_text}"
    patterns = [
        r"(\d+)\s*年(?:以上)?(?:工作)?经验",
        r"工作年限[:：\s]*(\d+)\s*年",
        r"(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*experience",
    ]
    return max(extract_numbers_by_patterns(text, patterns), default=0)


def extract_numbers_by_patterns(text: str, patterns: Iterable[str]) -> List[int]:
    numbers: List[int] = []
    for pattern in patterns:
        for match in re.findall(pattern, text or "", flags=re.IGNORECASE):
            try:
                numbers.append(int(match))
            except ValueError:
                continue
    return numbers


def extract_degree_level(text: str) -> int:
    lowered = (text or "").casefold()
    levels = [level for keyword, level in DEGREE_LEVELS.items() if keyword.casefold() in lowered]
    return max(levels, default=0)


def build_rule_summary(overall_score: int, matched_keywords: List[str], missing_keywords: List[str]) -> str:
    matched = "、".join(matched_keywords[:6]) if matched_keywords else "暂无明显关键词"
    missing = "、".join(missing_keywords[:6]) if missing_keywords else "暂无关键缺口"
    if overall_score >= 80:
        level = "匹配度较高"
    elif overall_score >= 60:
        level = "匹配度中等"
    else:
        level = "匹配度偏低"
    return f"{level}。已匹配：{matched}；建议关注缺口：{missing}。"


def ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def clamp_score(score: float) -> int:
    return max(0, min(100, int(round(score))))
