# @deepseek-ai/dsh-client-ui-autograph

[English](README.md) | 中文

面向 Web 客户端的自主红队图与运行时设置界面。

此包提供 AutoGraph 对话视图与 **Red Team 环境** 设置区。设置区会展示运行时发现与安装状态，并提供 MCP、Skill 和 Rule 配置。MCP 配置支持主从式可视化编辑器、直接导入/导出 `mcpServers` JSON、stdio/SSE/Streamable HTTP 字段、环境变量或请求头、校验、保存/重置状态，以及探测/重载反馈。配置会在标准 `ant-sword-runtime` 设置作用域可用时绑定该作用域，否则使用所属 bundle 中仅限 loopback 的桥接；两条路径均保留同一套带 revision fence 的 Host 设置事务。

## 模型体验

此包仅改变界面呈现与操作者配置。它不会增加模型可见的上下文或工具；已配置的 MCP 服务器由所属 Host 运行时应用。