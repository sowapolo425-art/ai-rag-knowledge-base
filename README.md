# 企业知识库 A

一个可实际运行的中文企业文档问答作品集：上传 PDF、DOCX 或 TXT，提取并切分文字，用向量检索定位依据，再由模型回答并展示来源。示例员工手册是虚构内容。

**[打开公网演示](http://139.199.90.153/)** · [查看验证记录](VERIFICATION.md) · [查看云端维护说明](DEPLOYMENT.md) · [查看面试展示提纲](PORTFOLIO.md)

公网演示已预置虚构文档。可直接问“员工申请年假要提前几个工作日？”或“800 元办公用品由谁审批？”。公网仅开放阅读和提问；上传、删除请在本地运行体验。当前演示使用服务器 IP 的 HTTP 地址，尚未配置域名和 HTTPS；请勿提交真实或机密资料。

![项目页面](screenshot.png)

## 功能与架构

- PDF 按页、DOCX 与 TXT 按段落保留来源；问答返回原文、位置与引用编号。
- 原始文档保存在数据目录，元数据使用 SQLite，向量索引使用本地 Qdrant。重启后文档仍在。
- 支持兼容 OpenAI 的聊天与 Embeddings 接口，也支持免费的本地中文语义 Embedding。
- 无模型配置时可运行字符向量检索和摘录式回答，便于离线体验流程。该模式不代表语义理解或大模型生成。
- 页面保留本次会话最近 6 条消息用于追问；刷新后清空。提供 FastAPI 接口文档与自动化测试。

```text
浏览器 → FastAPI ┬→ 文档解析与分块 → Embedding → Qdrant 检索
                 └→ 问题与命中片段 → 聊天模型或离线摘录 → 答案与原文来源
文档元数据 → SQLite；原始文件 → data/uploads
```

公网实例运行在用户的广州云服务器上：`BAAI/bge-small-zh-v1.5` 负责中文语义检索，`Qwen2.5-1.5B-Instruct` 的 Q4_K_M 量化版本通过 llama.cpp 在服务器本地生成答案。两者均不依赖用户电脑持续在线。模型权重不包含在仓库与压缩包中；[Qwen 模型](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) 为 Apache-2.0，[Embedding 模型](https://huggingface.co/Qdrant/bge-small-zh-v1.5) 为 MIT。小模型仍可能答错，页面提供原文供核对。

## 本地运行

需要 Docker Desktop。进入本目录运行：

```powershell
docker compose up --build -d
```

打开 <http://127.0.0.1:8765>，上传 `sample/员工手册示例.txt` 后提问。API 文档在 <http://127.0.0.1:8765/docs>。默认没有密钥，运行离线摘录模式；端口冲突时可设置 `HOST_PORT`。停止服务用 `docker compose down`；`docker compose down -v` 会删除上传文档和索引。

也可安装 Python 3.11+，创建虚拟环境后安装 `requirements.txt`，执行 `python -m uvicorn app.main:create_app --factory`。

### 启用模型

复制 `.env.example` 为 `.env`。填写 `OPENAI_BASE_URL`、`OPENAI_API_KEY`、`OPENAI_CHAT_MODEL` 后启用兼容 OpenAI Chat Completions 的模型；填写 `OPENAI_EMBEDDING_MODEL` 可改用提供商的 Embeddings API。只需本地中文语义检索时，设置 `LOCAL_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5`，首次启动会下载约 90 MB 模型。外部 Embeddings 配置优先于本地模型。不要提交 `.env`、模型权重或真实业务资料。

切换 Embedding 模式或模型会使用新的 Qdrant 集合；旧文档仍在数据目录，但不会显示在新模式的列表中，需要重新上传以建立新索引。

## API 与测试

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/status` | 模式、文档数、只读状态 |
| GET | `/api/documents` | 文档列表 |
| POST | `/api/documents` | `multipart/form-data` 上传 `file` |
| DELETE | `/api/documents/{id}` | 删除文档及其索引 |
| POST | `/api/ask` | JSON `{"question":"...","history":[]}`，返回答案与来源 |

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

目前自动化测试为 **4 passed**，覆盖真实 PDF/DOCX 流程、TXT 段落位置、删除与错误上传，以及公网只读约束。公网实例还经过实际模型问答、无依据问题、接口限制与服务重启验证。详细证据和局限见 [VERIFICATION.md](VERIFICATION.md)。

## 使用边界

这是公开求职作品集演示，不是企业生产系统。没有员工登录、租户隔离、恶意文件扫描或扫描版 PDF 的 OCR。公网关闭上传与删除，并对提问限速；本地模式允许上传自己的测试资料。模型回答可能遗漏条件或出错，应以展示的原文为准。
