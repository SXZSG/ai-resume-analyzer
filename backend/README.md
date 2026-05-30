# 后端运行说明

FastAPI 后端提供 PDF 简历解析、结构化信息提取、规则评分和可选大模型增强分析。

## 本地启动

```bash
cd backend
python -m venv venv
source venv/bin/activate
# Windows:
# venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：

- 健康检查：`http://127.0.0.1:8000/health`
- API 文档：`http://127.0.0.1:8000/docs`

## 环境变量

复制 `.env.example` 为 `.env`，按需配置：

```bash
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
ANALYZE_CACHE_FILE=./.cache/analyze_cache.json
```

未配置 `LLM_API_KEY` 时，系统会使用 mock 抽取和 mock 分析逻辑，仍可完整演示。

## API

### `GET /health`

```json
{
  "status": "ok"
}
```

### `POST /api/analyze`

`multipart/form-data` 参数：

- `resume`：PDF 文件，必填
- `job_description`：岗位 JD 文本，必填

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -F "resume=@resume.pdf" \
  -F "job_description=需要 Python、FastAPI、Docker、MySQL 经验"
```

## 测试

```bash
pytest
```
