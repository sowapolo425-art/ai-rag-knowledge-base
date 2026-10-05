# 广州云服务器部署与维护

本页记录 2026-10-05 已完成的公网作品集部署。访问地址：<http://139.199.90.153/>。当前使用 IP 和 HTTP，未配置域名及 HTTPS；演示只使用虚构资料，访客不能上传或删除。

## 当前运行方式

| 项目 | 位置或服务 |
| --- | --- |
| 应用目录 | `/home/ubuntu/apps/ai-rag-knowledge-base` |
| Web 服务 | `ai-rag-kb.service`，公网 80 端口 |
| 本地聊天模型 | `ai-rag-llm.service`，仅监听 `127.0.0.1:8780` |
| 文档与索引 | 应用目录下的 `data/` |
| 配置 | 应用目录下的 `.env`，权限 600；不要提交到仓库 |

应用使用 Python 虚拟环境和 systemd，聊天模型使用 llama.cpp `b11414` 与 `Qwen2.5-1.5B-Instruct-Q4_K_M`。中文向量模型是 `BAAI/bge-small-zh-v1.5`。模型权重位于服务器本地，不在 GitHub 或压缩包中。本地 Docker Compose 仍可独立运行项目的离线模式。

## 日常检查

使用已配置的 `gz-dev` SSH 连接登录后：

```bash
systemctl is-active ai-rag-kb.service ai-rag-llm.service
curl -fsS http://127.0.0.1/api/status
curl -fsS http://127.0.0.1:8780/health
sudo journalctl -u ai-rag-kb.service -n 50 --no-pager
sudo journalctl -u ai-rag-llm.service -n 50 --no-pager
df -h /
```

`/api/status` 应显示 `embedding_mode=semantic`、`answer_mode=llm`、`demo_readonly=true`。公网只读约束由应用处理；`POST /api/documents` 和 `DELETE /api/documents/{id}` 应返回 403。提问按来源 IP 每分钟最多 6 次。Web 服务需要约 3–4 秒加载向量模型；重启后请等待状态接口可用，再判断是否失败。

## 更新与回退

更新源码前，保存 `data/` 与当前应用版本；保留 `.env`。同步新版 `app/` 后重启 Web 服务：

```bash
sudo systemctl restart ai-rag-kb.service
```

仅改动聊天模型或 `ai-rag-llm.service` 时重启该服务，再检查 `/health` 和实际问答。回退时恢复之前的源码、数据快照及服务文件，依次重启模型和 Web 服务。**不要使用 `docker compose down -v` 清理云端数据**；云端当前也并非以 Compose 容器运行。

若要更换 Embedding 模型，请先备份 `data/`，再重新上传示例文档建立新集合。公网维护时应先将 Web 服务改为仅监听本机，再临时关闭 `DEMO_READONLY`，完成上传后恢复只读及公网监听，避免出现可匿名上传的窗口。

## 当前边界

- 未启用 HTTPS，勿输入或上传真实资料；若将来绑定域名，再配置可信证书和反向代理。
- 这是一台内存约 3.6 GiB 的共享云服务器。模型仅 CPU 推理，性能适合少量作品集访问；不要将其当作企业多人生产服务。
- 扫描 PDF 不支持 OCR，模型回答可能有遗漏。页面始终展示原文出处。
