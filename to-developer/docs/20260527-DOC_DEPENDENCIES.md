# 文档依赖关系

> 改一个文档时，检查是否需要同步更新其他文档。

## 依赖图

```
README.md（总入口）
  ├── 引用 → QUICK_START.md
  ├── 引用 → docs/OPERATIONS_GUIDE.md
  ├── 引用 → docs/SKILL_CATALOG.md / SKILL_CATALOG_CN.md
  ├── 引用 → deploy/DEPLOY_GUIDE.md
  ├── 引用 → docs/TRIPARTITE_ARCHITECTURE_GUIDE.md
  └── 引用 → docs/FEISHU_INTEGRATION.md

QUICK_START.md（新手入口）
  └── 引用 → OPERATIONS_GUIDE, DEPLOY_GUIDE, TRIPARTITE

docs/OPERATIONS_GUIDE.md（操作手册）
  └── 引用 → SKILL_CATALOG, SKILL_CATALOG_CN

docs/SKILL_CATALOG.md（英文，自动生成）
  └── 来源 → skills/*/SKILL.md frontmatter
  └── 生成 → python3 tools/generate_skill_catalog.py

docs/SKILL_CATALOG_CN.md（中文，自动生成）
  └── 来源 → SKILL_CATALOG.md + tools/translate_skill_catalog.py 映射表
  └── 生成 → python3 tools/translate_skill_catalog.py

deploy/DEPLOY_GUIDE.md（部署指南）
  └── 独立，改 Dockerfile/compose 时同步更新
```

## 修改触发表

| 你改了什么 | 需要同步更新 |
|-----------|-------------|
| 新增/删除 skill | 1. `tools/generate_skill_catalog.py` 的 CATEGORY_MAP 加映射<br>2. `tools/translate_skill_catalog.py` 的 CN_DESC + CN_ARG_HINT 加翻译<br>3. 跑 `python3 tools/generate_skill_catalog.py && python3 tools/translate_skill_catalog.py` |
| 改 skill 的 description/argument-hint | 跑两个生成脚本重新生成 catalog |
| 改部署方式（Dockerfile/compose） | 更新 `deploy/DEPLOY_GUIDE.md` + `QUICK_START.md` Docker 段 |
| 改三边架构规则 | 更新 `docs/TRIPARTITE_ARCHITECTURE_GUIDE.md` + README 架构段 + OPERATIONS_GUIDE 三边章节 |
| 改 API 配置方式 | 更新 `docs/OPERATIONS_GUIDE.md` API 章节 |
| 改飞书 bridge / runner / `.env` 配置 | 更新 `docs/FEISHU_INTEGRATION.md` + `mcp-servers/README.md` + README 文档索引 |
| 改 project.yaml 模板 | 更新 `QUICK_START.md` 配置示例 + `OPERATIONS_GUIDE.md` 概念段 |
| 框架更新（git pull） | `/framework-update` 会自动重新生成 SKILL_CATALOG |

## 单一数据源原则

| 信息 | 唯一来源 | 其他文档怎么引用 |
|------|---------|----------------|
| Skill 完整列表 | `docs/SKILL_CATALOG.md` (自动生成) | 链接，不复制 |
| Skill 中文列表 | `docs/SKILL_CATALOG_CN.md` (自动生成) | 链接，不复制 |
| 部署步骤 | `deploy/DEPLOY_GUIDE.md` | README/QUICK_START 简述 + 链接 |
| 三边架构详情 | `docs/TRIPARTITE_ARCHITECTURE_GUIDE.md` | README 简表 + 链接 |
| API 配置详情 | `docs/OPERATIONS_GUIDE.md` #api-配置 | README 链接 |
| 飞书集成 | `docs/FEISHU_INTEGRATION.md` | README 和 `mcp-servers/README.md` 链接 |
| project.yaml 规格 | `templates/project.yaml.tmpl` + OPERATIONS_GUIDE | QUICK_START 示例片段 |
