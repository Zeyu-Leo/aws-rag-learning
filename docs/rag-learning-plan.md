# AWS RAG 实践计划

## 目标与起点

构建一个“ AWS 学习笔记问答助手”，学习 OpenSearch，并逐步将本地 RAG 迁移到 AWS。

已有经验：AWS Lambda、简单的本地 RAG。沿用当前 Python + uv 项目，分四次实践，每次预计 1～2 小时；云端配置可能需要额外时间。

资料使用自己编写的 5～10 篇 Markdown 学习笔记，例如 Lambda、S3、IAM 基础知识。使用容易核对答案的小规模数据集。

## 目标架构

```text
入库：
Markdown → 切分 → Embedding → OpenSearch

问答：
问题 → Embedding → OpenSearch 检索 Top 3
                           ↓
                    问题 + 文档片段
                           ↓
                    Portkey → 模型
                           ↓
                      答案 + 来源
```

Embedding 模型与回答生成模型分别配置。通过 Portkey 使用时，先确认 workspace 开放的模型、接口及使用许可，尤其是 embedding 接口。尚未准备好模型访问时，可以先完成关键词检索。

## 第一次：OpenSearch 基础与关键词搜索

在本地通过 Docker 运行单节点 OpenSearch，使用 `opensearch-py` 访问。学习 index、document、mapping、query 四个概念。

- [ ] 配置本地 OpenSearch，固定镜像版本；端口仅绑定本机。
- [ ] 使用 uv 添加 Python 客户端依赖。
- [ ] 创建 `learning-notes` 索引。
- [ ] 写入 10 条笔记片段，包含 `text`、`source`、`chunk_id`。
- [ ] 使用 `match` 查询搜索内容。
- [ ] 更新、删除一条记录，观察检索结果。

完成标准：输入“Lambda 超时”，能够打印相关片段及来源文件名。

参考：[OpenSearch 入门](https://docs.opensearch.org/latest/getting-started/)。本地演示配置不直接用于云端部署。

## 第二次：向量入库与检索

由 Python 应用生成 embedding，再把向量写入 OpenSearch，直接观察文本、向量与检索结果的关系。

- [ ] 选定并记录 embedding 模型及输出维度。
- [ ] 按 Markdown 段落切分笔记，保留来源信息。
- [ ] 创建包含 `knn_vector` 字段的索引，维度与模型输出一致。
- [ ] 为片段生成 embedding，并写入索引。
- [ ] 将问题转换为向量，执行 Top 3 检索。
- [ ] 对比同一问题的关键词检索和向量检索结果。
- [ ] 使用稳定的片段 ID，避免重复运行入库时增加重复记录。

文档与查询使用匹配的 embedding 模型及其推荐的输入格式。更换模型时重新生成文档向量；维度变化时重新创建相应索引。

完成标准：文档使用“执行时间限制”，提问“函数最多能跑多久”，也能检索到对应片段；未修改资料时，重复入库的记录数不增加。

参考：[创建向量索引](https://docs.opensearch.org/latest/vector-search/creating-vector-index/)。

## 第三次：接入模型，完成 RAG

保持检索与生成逻辑独立：

```text
retrieve(question) → 文档片段
answer(question, chunks) → 回答
```

- [ ] 将 Top 3 片段编号为 `[1]`、`[2]`、`[3]`。
- [ ] 组装问题和上下文，经 Portkey 调用获准的生成模型。
- [ ] 要求模型依据资料回答，并引用片段编号。
- [ ] 要求资料不足时说明无法从笔记中确定答案。
- [ ] 输出检索片段与来源，方便调试。
- [ ] 记录模型返回的 token 用量和请求耗时。
- [ ] 手动检查 5 个资料内问题、2 个资料未覆盖的问题。

完成标准：答案能指向正确来源；资料不足时说明不确定；可以区分检索错误和生成错误。提示词要求本身不保证模型始终遵守，需要检查实际结果。

## 第四次：迁移到 AWS Lambda 与 OpenSearch

```text
API Gateway → Lambda
                 ├─ 查询 Embedding
                 ├─ Amazon OpenSearch 检索
                 └─ Portkey 生成回答
```

- [ ] 选择适合实验的 Amazon OpenSearch Service 部署方式，确认费用及清理方式。
- [ ] 配置 AWS 身份认证、最小权限与网络访问。
- [ ] 确认 Lambda 同时能够访问 OpenSearch 和 Portkey；若放入 VPC，明确外部 HTTPS 出站路径及成本。
- [ ] 将问答入口封装为 Lambda，复用检索和模型访问代码。
- [ ] 配置 API Gateway HTTP 入口。
- [ ] 分别记录检索、生成和总耗时，设置合理超时。
- [ ] 验证一条成功请求，以及模型或检索失败时的返回行为。
- [ ] 清理实验创建的云端资源，确认没有遗留收费资源。

完成标准：HTTP 请求可以完成问答，日志可区分各阶段耗时，并能清理实验资源。

## 后续扩展：Step Functions 文档入库编排

前四次完成后，再将文档入库改为云端流程：

```text
S3 上传 → 触发工作流 → Step Functions
                         → 解析与切分 Lambda
                         → 批量 Embedding
                         → 写入 OpenSearch
```

重点练习批处理、重试、失败恢复与幂等写入。模型请求通过 Portkey 时，可使用 `Step Functions → Lambda → Portkey`；AWS 原生 `bedrock:invokeModel` 集成仍是直连 Bedrock。

第一版同步问答先使用一个 Lambda。Bedrock Knowledge Bases、混合检索、reranking 和 Agent 留作后续学习内容。

## 建议的文件结构

以下为逐步实现的目标结构，当前计划不代表这些文件已经创建：

```text
aws-bedrock/
├── docs/rag-learning-plan.md
├── notes/             # Markdown 学习笔记
├── ingest.py          # 切分、生成向量、入库
├── search.py          # 关键词和向量检索
├── ask.py             # 检索后调用模型
├── model_client.py    # 模型访问配置
├── compose.yaml       # 本地 OpenSearch
└── .env               # 本地配置，不提交密钥
```

下一步：完成第一次实践，先让 Python 成功写入 OpenSearch，再检索出一条笔记。
