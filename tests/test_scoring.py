import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from scoring import calculate_match_score  # noqa: E402


def test_calculate_match_score_returns_valid_scores():
    resume_info = {
        "background": {
            "education": "本科 计算机科学与技术",
            "work_years": "3 年工作经验",
            "skills": ["Python", "FastAPI", "Docker", "MySQL", "Git"],
            "projects": ["使用 FastAPI 构建 RESTful API，并使用 Docker 部署。"],
            "experiences": ["负责 Python 后端开发和 MySQL 数据库设计。"],
        }
    }
    jd = "需要 2 年以上 Python、FastAPI、Docker、MySQL、RESTful API 开发经验，本科及以上学历。"

    result = calculate_match_score(resume_info, jd)

    for key in ("overall_score", "skill_score", "experience_score", "education_score"):
        assert 0 <= result[key] <= 100
    assert "Python" in result["matched_keywords"]
    assert "FastAPI" in result["matched_keywords"]


def test_calculate_match_score_handles_empty_keywords():
    resume_info = {
        "background": {
            "education": "",
            "work_years": "",
            "skills": [],
            "projects": [],
            "experiences": [],
        }
    }

    result = calculate_match_score(resume_info, "沟通能力强，学习能力强。")

    for key in ("overall_score", "skill_score", "experience_score", "education_score"):
        assert 0 <= result[key] <= 100
    assert isinstance(result["matched_keywords"], list)
    assert isinstance(result["missing_keywords"], list)
