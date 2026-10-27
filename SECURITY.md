# Security Policy

## 支持版本

| 版本 | 支持 |
|---|---|
| 0.1.x | ✅ |
| < 0.1 | ❌ |

## 报告漏洞

**请勿通过公开 Issue 报告安全漏洞。**

任选一种方式：

1. 使用 GitHub Security Advisory：  
   https://github.com/WebAIHarnessRoom/GenerateProjectContext/security/advisories/new
2. 发送邮件至：`security@example.com`

报告时请包含：

- 受影响版本
- 复现步骤或 PoC
- 影响范围（信息泄露、任意文件读取、命令注入等）
- 你希望的披露方式

## 响应时间

- 确认收到：3 个工作日内
- 初步评估：7 个工作日内
- 修复与披露：根据严重程度协商

## 范围

本项目的安全关注点包括：

- 配置解析（TOML 注入、路径穿越）
- 文件遍历（符号链接、越界读取）
- Git 子进程调用（命令注入）
- GUI 子进程执行（命令拼装）

以下不属于安全漏洞：

- 对恶意项目目录的“预期行为”（例如项目本身包含巨大文件导致输出很大）
- 需要用户主动执行明显危险命令的场景
- 第三方依赖自身的已知问题（请直接报告给上游）

## 披露政策

修复版本发布后，我们会在 `CHANGELOG.md` 与 GitHub Release 中说明。  
在修复发布前，请勿公开漏洞细节。
```

`zhouyp001@gmail.com` 请替换成真实安全联系邮箱；若暂无专用邮箱，也可以只保留 GitHub Security Advisory 一种方式，删掉邮件那条。