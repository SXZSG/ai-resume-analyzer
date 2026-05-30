# AI 赋能的智能简历分析系统

这是一个面向招聘流程的简历分析 Demo。用户上传 PDF 简历并输入岗位 JD，系统会解析 PDF 文本、抽取候选人关键信息、计算岗位匹配度，并以统一 JSON 和前端页面展示分析结果。

项目默认不依赖真实大模型 API Key。未配置 `LLM_API_KEY` 时，后端会自动使用 mock 抽取和 mock 分析逻辑，便于评审老师快速本地体验。

## 功能特性

- PDF 简历上传与 PyMuPDF 文本解析。
- 简历文本清洗，去除多余空格、空行和控制字符。
- OpenAI-compatible Chat Completions API 可选接入。
- 无 API Key 时自动 fallback 到 mock 版本。
- 规则评分不依赖大模型，覆盖技能、经验、学历和综合评分。
- 内置关键词提取，返回已匹配关键词和缺失关键词。
- 简单本地 JSON 缓存，相同简历文本和 JD 可直接复用结果。
- 纯 HTML + CSS + JavaScript 前端，适合 GitHub Pages 部署。
- 完整 RESTful API、README、部署说明和基础测试。

## 技术栈

- 后端：Python、FastAPI、Pydantic、PyMuPDF、Requests
- 前端：HTML、CSS、JavaScript
- 测试：pytest
- 部署：Uvicorn、本地 Docker、阿里云函数计算 FC 自定义容器

## 项目结构

```text
ai-resume-analyzer/
├── backend/
│   ├── main.py
│   ├── parser.py
│   ├── llm_client.py
│   ├── scoring.py
│   ├── cache.py
│   ├── schemas.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── docs/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── deployment/
│   ├── aliyun_fc.md
│   └── Dockerfile
├── examples/
│   └── sample_job_description.txt
├── tests/
│   └── test_scoring.py
├── README.md
└── .gitignore
```

## 本地运行

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
# Windows:
# venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

### 前端

可以直接打开：

```text
docs/index.html
```

也可以启动静态服务：

```bash
python -m http.server 8080 -d docs
```

然后访问：

```text
http://127.0.0.1:8080
```

### 测试

```bash
pip install -r backend/requirements.txt
pytest
```

## 环境变量

后端会优先读取环境变量：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `LLM_API_KEY` | 大模型 API Key，未配置则使用 mock 版本 | 空 |
| `LLM_BASE_URL` | OpenAI-compatible API Base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4o-mini` |
| `ANALYZE_CACHE_FILE` | 本地缓存文件路径 | `backend/.cache/analyze_cache.json` |

可复制 `backend/.env.example` 为 `.env`。不要将 `.env` 提交到 Git。

## API 文档

### `GET /health`

响应：

```json
{
  "status": "ok"
}
```

### `POST /api/analyze`

请求类型：`multipart/form-data`

参数：

- `resume`：PDF 文件，必填
- `job_description`：岗位描述文本，必填

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -F "resume=@resume.pdf" \
  -F "job_description=需要 Python、FastAPI、Docker、MySQL 经验"
```

错误统一返回：

```json
{
  "success": false,
  "message": "错误原因",
  "data": null
}
```

## 前端使用说明

1. 启动后端服务，默认地址为 `http://127.0.0.1:8000`。
2. 打开 `docs/index.html` 或使用 `python -m http.server 8080 -d docs`。
3. 在页面顶部确认 API 地址。
4. 上传 PDF 简历，粘贴岗位 JD，点击“开始分析”。
5. 页面会展示候选人信息、技能、项目经历、分项评分、关键词和原始 JSON。
6. API 地址会保存到浏览器 `localStorage`，部署到线上后可改为 FC HTTP 触发器地址。

## GitHub Pages 部署

1. 将代码推送到 GitHub。
2. 进入仓库 `Settings` -> `Pages`。
3. Source 选择 `Deploy from a branch`。
4. Branch 选择 `main`，目录选择 `/docs`。
5. 保存后等待 Pages 构建完成。

前端是静态页面，后端需要单独部署。本地或线上后端地址都可以在页面输入框中配置。

## 阿里云函数计算 FC 部署

推荐使用自定义容器部署：

```bash
docker build -f deployment/Dockerfile -t ai-resume-analyzer:latest .
```

将镜像推送到阿里云 ACR 后，在函数计算 FC 创建自定义容器函数，监听端口设置为 `8000`，并创建 HTTP 触发器。

需要配置的环境变量示例：

```text
LLM_API_KEY=你的大模型 API Key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
ANALYZE_CACHE_FILE=/tmp/analyze_cache.json
```

更详细步骤见 [deployment/aliyun_fc.md](deployment/aliyun_fc.md)。

## 示例返回 JSON

```json
{
  "success": true,
  "message": "Analyze successfully.",
  "data": {
    "basic_info": {
      "name": "张三",
      "phone": "13800000000",
      "email": "zhangsan@example.com",
      "address": "上海"
    },
    "job_intention": {
      "position": "Python 后端工程师",
      "expected_salary": "面议"
    },
    "background": {
      "education": "本科 计算机科学与技术",
      "work_years": "3 年工作经验",
      "skills": ["Python", "FastAPI", "Docker", "MySQL"],
      "projects": ["招聘系统简历解析模块"],
      "experiences": ["负责后端 API 开发"]
    },
    "match_result": {
      "overall_score": 82,
      "skill_score": 86,
      "experience_score": 78,
      "education_score": 80,
      "matched_keywords": ["Python", "FastAPI", "Docker", "MySQL"],
      "missing_keywords": ["Redis"],
      "advantages": ["简历覆盖了岗位中的核心关键词：Python、FastAPI、Docker、MySQL。"],
      "risks": ["岗位关键词缺口包括：Redis。"],
      "summary": "候选人与 JD 匹配度较高，建议重点核实项目深度、职责边界和稳定性。"
    },
    "raw_text_preview": "张三..."
  },
  "cached": false
}
```

## 加分项说明

- 大模型调用使用 OpenAI-compatible API，方便切换不同模型服务。
- 对大模型非 JSON 输出做了容错解析。
- 没有 Key 时仍可演示完整链路。
- 匹配评分为可解释规则评分，不完全依赖大模型。
- 缓存 key 使用简历文本 hash + JD 文本 hash。
- 前端 API 地址可保存，便于从本地切换到线上 FC。

## 注意事项

- 不要上传真实简历到不可信环境，测试时请使用脱敏文件。
- 不要把 `LLM_API_KEY`、线上服务密钥或真实个人信息提交到 Git。
- PDF 如果是扫描件图片，PyMuPDF 可能无法提取文字，需要额外接入 OCR。
- 本项目为笔试 Demo，未引入数据库、登录鉴权和生产级任务队列。
