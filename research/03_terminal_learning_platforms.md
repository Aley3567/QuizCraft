# 竞品研究: 终端闯关式学习平台

> Exa Agent Run 3 - high effort - 2026-06-23

## 平台对比

| 平台 | 沙箱类型 | 验证方式 | 开源 | 适合参考 |
|------|---------|---------|------|---------|
| OverTheWire | SSH 共享主机 | 密码/flag | 否 | 低 |
| HackTheBox | VPN + 云 VM/Pwnbox | CTF flag | 否 | 低 |
| TryHackMe | AttackBox + VPN | flag/答案 | 否 | 低 |
| **KillerCoda** | **KubeVirt VM** | **check.sh exit code** | 否(场景开源) | **高** |
| Katacoda(已停) | 云端环境 | check.sh + Cypress | 否 | 高(设计模式) |
| **Instruqt** | 容器/VM/云账号 | **lifecycle scripts** | 否 | **高(最完整)** |
| Play with Docker | DinD | 手动 | **是** | 中 |
| Codecademy | xterm.js + Monaco | 测试/输出比对 | 否 | 中 |
| Exercism | Docker per-language | test runner + analyzer | **是** | 中 |
| **iximiuz Labs** | **Firecracker microVM** | **check DAG in-VM** | 否 | **高(架构)** |
| **pwn.college DOJO** | Docker + CTFd | flag | **是(BSD)** | **高(全栈参考)** |

## 沙箱技术选型

| 技术 | 隔离级别 | 启动速度 | 适合场景 | 复杂度 |
|------|---------|---------|---------|-------|
| **Docker 容器** | 中(共享内核) | <1秒 | **MVP/个人/内部** | **低** |
| DinD | 中 | 秒级 | 教 Docker 本身 | 中 |
| gVisor/runsc | 中高 | 秒级 | 多租户容器 | 中 |
| KubeVirt | 高(VM) | 慢 | 生产 Linux 实验室 | 高 |
| Firecracker | 高(microVM) | 快(对 VM) | 不可信代码 | 高 |
| WebAssembly | 浏览器级 | 即时 | JS/Node 练习 | 低 |

**QuizCraft 选择**: Docker 容器（个人使用场景，复杂度最低）

## 终端 UI 方案

| 工具 | 描述 | 使用者 |
|------|------|--------|
| **xterm.js** | 浏览器终端模拟器，唯一正选 | VS Code, Codecademy, iximiuz |
| ttyd | C 轻量 Web 终端服务 | 嵌入式/原型 |
| WeTTY | Node.js Web 终端 | SSH 桥接 |
| GoTTY | Go Web 终端 | CLI 暴露 |

## 验证模式

| 模式 | 描述 | 适用 | QuizCraft 用否 |
|------|------|------|---------------|
| Flag/密码 | 发现 flag 提交 | CTF 安全挑战 | 否 |
| **exit-code check.sh** | **脚本返回 0=通过** | **Linux/DevOps 实操** | **主要** |
| 状态检查 DAG | 代理检查文件/进程/服务 | 复杂基础设施 | 后续 |
| 单元测试/OJ | 编译运行比对输出 | 编程练习 | 补充 |
| **LLM 判断** | 命令历史+环境送 LLM | **脚本无法验证时** | **备用** |

## 架构建议

1. **MVP**: xterm.js + WebSocket + ttyd/node-pty + Docker 容器(非特权, --network none, cgroups, TTL)
2. 用 KillerCoda/Katacoda 创作模式：Markdown 指令 + check.sh + setup.sh + cleanup.sh
3. 交互终端和代码判题分开：终端需会话生命周期，代码提交用无状态 worker
4. AI 从教材生成实操题 + 验证脚本，但需人工审核后再发布
