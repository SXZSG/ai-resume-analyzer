# 阿里云函数计算 FC 部署说明

本文档给出两种部署思路：推荐使用自定义容器镜像，也可以使用 ZIP 代码包方式部署 Python 运行时。

## 方案一：自定义容器镜像

1. 在项目根目录构建镜像：

```bash
docker build -f deployment/Dockerfile -t ai-resume-analyzer:latest .
```

2. 将镜像推送到阿里云容器镜像服务 ACR。

3. 在阿里云函数计算 FC 中创建函数：

- 运行环境选择自定义容器。
- 镜像地址填写 ACR 镜像地址。
- 监听端口填写 `8000`。
- 启动命令使用 Dockerfile 默认命令即可。

4. 配置环境变量：

```text
LLM_API_KEY=你的大模型 API Key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
ANALYZE_CACHE_FILE=/tmp/analyze_cache.json
```

未配置 `LLM_API_KEY` 时，函数仍会使用 mock 模式返回演示结果。

5. 创建 HTTP 触发器：

- 认证方式可根据需要选择匿名或签名认证。
- 允许方法至少包含 `GET` 和 `POST`。
- 如果前端通过 GitHub Pages 调用，后端已开启 CORS。

6. 访问健康检查：

```text
https://你的触发器域名/health
```

## 方案二：ZIP 代码包

1. 在本地安装依赖到发布目录：

```bash
mkdir -p package
pip install -r backend/requirements.txt -t package
cp -r backend/* package/
```

Windows PowerShell 可使用：

```powershell
New-Item -ItemType Directory -Force package
pip install -r backend/requirements.txt -t package
Copy-Item backend\* package -Recurse -Force
```

2. 将 `package` 目录压缩为 ZIP 并上传到 FC。

3. 入口需要使用支持 ASGI 的方式运行 FastAPI。若 FC Python 运行时不直接支持常驻 HTTP 服务，建议改用自定义容器方案。

## 前端 API 地址配置

前端位于 `docs/`，可以部署到 GitHub Pages。页面顶部有 API 地址输入框：

```text
http://127.0.0.1:8000
```

部署到 FC 后，将该地址改成 HTTP 触发器线上地址并点击“保存”。地址会写入浏览器 `localStorage`，不需要重新打包前端。

## 注意事项

- 不要把 `LLM_API_KEY` 写入代码或提交到 Git。
- 上传真实简历前请确认数据合规与脱敏要求。
- `/tmp` 更适合函数计算中的临时缓存文件，实例回收后缓存可能丢失。
- PDF 解析依赖 PyMuPDF，使用 ZIP 部署时需要确保依赖和目标运行环境兼容。
