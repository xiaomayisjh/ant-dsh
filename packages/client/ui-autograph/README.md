# @deepseek-ai/dsh-client-ui-autograph

English | [中文](README.zh.md)

Autonomous red-team graph and runtime settings surfaces for the Web client.

The package contributes the AutoGraph conversation view and the **Red Team 环境** settings section. The settings section displays runtime discovery and install state, then exposes MCP, Skill, and Rule configuration. MCP configuration supports a master-detail visual editor, direct `mcpServers` JSON import/export, stdio/SSE/Streamable HTTP fields, environment variables or headers, validation, save/reset state, and probe/reload feedback. Configuration binds the standard `ant-sword-runtime` settings scope when exposed and otherwise uses the owning bundle's loopback-only bridge; both paths retain the same revision-fenced Host settings transaction.

## Model Experience

This package changes presentation and operator configuration only. It does not add model-visible context or tools; configured MCP servers are applied by the owning Host runtime.