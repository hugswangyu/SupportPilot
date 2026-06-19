# SupportPilot — 电商智能客服系统

一个基于 OpenAI + ReAct + RAG + MCP + Multi-Agent + Memory + Skill 的电商客服 Agent，模拟"并夕夕"平台的智能客服「小夕」。

## 核心特性

| 模块 | 说明 |
|------|------|
| **ReAct Agent** | 思考 → 工具调用 → 观察 → 循环，支持多步推理 |
| **RAG 知识检索** | 退换货政策、配送说明、会员权益等文档的向量检索（支持 Numpy / ChromaDB 两种后端） |
| **MCP 工具服务** | 通过 Model Context Protocol 暴露订单/物流/商品/退款工具，支持远程调用 |
| **Multi-Agent** | Router 意图分类 → 专属子 Agent 执行（订单、售后、商品咨询等） |
| **Memory 记忆** | 短期记忆（本次对话摘要）+ 长期记忆（跨会话用户偏好持久化） |
| **Skill 技能** | 可插拔技能模块，Agent 可按需编排复用能力 |
| **Evaluation** | LLM-as-Judge 离线评测框架，自动化质量/幻觉/过程合理性打分 |

## 项目结构

```
SupportPilot/
├── main.py                    # 入口：交互式命令行
├── app/
│   ├── agent/
│   │   ├── chat.py            # EcomAgent：单 Agent ReAct 主循环
│   │   ├── tools/             # 工具集：订单/物流/商品/退款/知识库/记忆/技能
│   │   ├── memory.py          # 短期 + 长期记忆管理
│   │   ├── skills/            # 可插拔技能定义
│   │   └── rag/               # 向量检索（Numpy/ChromaDB）
│   ├── multi_agent/
│   │   ├── orchestrator.py    # Multi-Agent 编排器
│   │   ├── router.py          # 意图路由
│   │   └── agents.py          # 子 Agent 配置
│   ├── evaluation/            # 离线评测框架
│   ├── prompts/               # 各模块系统提示词
│   ├── schemas/               # Pydantic 响应模型
│   └── config/settings.py     # 统一配置（从 .env 读取）
├── mcp_server/server.py       # FastMCP HTTP 服务（端口 9123）
├── tests/                     # 单元测试
├── .env.example               # 配置模板
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写 OPENAI_API_KEY 和其他配置
```

### 3. 构建知识库索引（RAG）

```bash
python app/scripts/build_kb_index.py
```

### 4. 启动客服对话

```bash
python main.py
```

启动后支持以下命令：

| 命令 | 功能 |
|------|------|
| `reset` | 重置当前对话 |
| `memory` | 查看短期/长期记忆 |
| `skills` | 查看已加载的技能列表 |
| `quit` / `exit` | 退出并保存会话 |

## 运行模式

### 单 Agent 模式（默认）

```bash
# .env 中设置
MULTI_AGENT_ENABLED=false
```

ReAct 循环 + 全量工具，适合功能验证和教学演示。

### Multi-Agent 模式

```bash
# .env 中设置
MULTI_AGENT_ENABLED=true
```

Router 按意图分发给专属子 Agent，各 Agent 只持有对应工具集，结构更清晰。

### 启用 MCP 工具服务

```bash
# 先启动 MCP Server
python mcp_server/server.py

# .env 中设置
MCP_ENABLED=true
MCP_SERVER_URL=http://127.0.0.1:9123/mcp
```

## 配置参考

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `OPENAI_API_KEY` | — | OpenAI API Key（必填） |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 代理地址 |
| `MODEL_NAME` | `gpt-4o-mini` | 模型名称 |
| `TEMPERATURE` | `0.7` | 生成温度 |
| `RAG_BACKEND` | `numpy` | 向量后端：`numpy` / `chroma` |
| `MCP_ENABLED` | `false` | 是否启用 MCP 远程工具 |
| `MULTI_AGENT_ENABLED` | `false` | 是否启用 Multi-Agent 模式 |
| `MEMORY_ENABLED` | `true` | 是否启用记忆系统 |
| `SKILLS_ENABLED` | `true` | 是否启用技能模块 |

完整配置项见 `.env.example`。

## 离线评测

```bash
python app/scripts/run_eval.py
```

评测框架使用 LLM-as-Judge 对回复进行质量、幻觉、过程合理性三个维度打分，结果输出到控制台。

## 运行测试

```bash
python -m pytest tests/ -v
```

## 技术栈

- **LLM**: OpenAI GPT 系列（通过 OpenAI Python SDK）
- **向量检索**: Numpy（余弦相似度）/ ChromaDB
- **MCP**: `mcp>=1.8.0`（FastMCP Streamable HTTP）
- **数据校验**: Pydantic v2
- **配置管理**: pydantic-settings + python-dotenv
