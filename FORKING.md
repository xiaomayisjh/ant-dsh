# Fork 维护指南：同步上游 + 二开

本 fork（`xiaomayisjh/ant-dsh`）跟踪上游官方仓库 `deepseek-ai/deepseek-harness`，在其上叠加本地二开。本文档说明分支约定、一键脚本和二开流程。这是本 fork 的维护者文档，不属于上游协作文档体系（不适用 `docs/` 双语配对与 Agent Note 门禁）。

## 分支约定

| 分支 | 职责 | 规则 |
|---|---|---|
| `master` | 镜像上游稳定分支 | 只快进（`--ff-only`），不产生合并提交，不夹带本地改动 |
| `dev` | 二开分支 | 每次同步把 `master` 合进来；所有二开提交都落在这里 |

原则：`master` 永远干净地跟踪上游，二开全部进 `dev`，两者不互相污染，同步时不会和本地改动缠在一起。

## 一键脚本

仓库根提供三个等价脚本，行为一致，任选其一：

| 脚本 | 环境 |
|---|---|
| `sync-upstream.bat` | Windows cmd / 双击 |
| `sync-upstream.ps1` | PowerShell 7+（可能需要 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`） |
| `sync-upstream.sh` | bash（Linux / macOS / WSL / Git Bash） |

每个脚本按顺序执行，任一步失败即停：

1. 拒绝脏工作区——有未提交改动直接退出，防止合并覆盖本地工作。
2. 没有 `upstream` remote 时自动添加（指向上游官方仓库）。
3. `master` 快进到 `upstream/master`，推回 `origin`（你的 fork）。
4. 切到 `dev`（首次运行自动从 `master` 创建），把 `master` 合入，推回 `origin`。
5. 合并冲突时停下并打印手动解决指令，不硬来。

脚本顶部三个变量可改：`UPSTREAM_URL`、`DEV_BRANCH`、`STABLE_BRANCH`。`.ps1` 版本还支持 `-DevBranch` / `-StableBranch` 参数覆盖。

## 日常流程

**同步上游**（上游有更新时跑一次）：

```powershell
.\sync-upstream.ps1        # 或 .bat / .sh
```

**做二开**（在 `dev` 上改）：

```powershell
git checkout dev
# ... 改代码 ...
git add .
git commit -m "feat: ..."
git push origin dev
```

**从干净检出恢复**（换机器）：

```powershell
git clone https://github.com/xiaomayisjh/ant-dsh.git
cd ant-dsh
git checkout dev            # dev 已在远端，直接切
```

## 从源码运行

环境要求 Node `^22.19 || >=24`、pnpm `11.7.0`。

```powershell
pnpm install     # 首次
pnpm run build   # 构建库 + Web 前端产物
pnpm dsh web     # 启动 Web UI，默认 http://127.0.0.1:3080
```

`start-web.bat` 是上述流程的一键封装：自动补装依赖、按需构建、启动并打开浏览器。模型调用需要 `DEEPSEEK_API_KEY`（系统环境变量或仓库根 `.env`）。

同步上游后建议重新 `pnpm install && pnpm run build`，因为依赖和构建产物可能随上游变化。

## 同步冲突时

脚本在 `dev` 合并 `master` 遇冲突会退出并停在冲突状态。手动解决：

```powershell
# 编辑冲突文件，解决标记 <<<<<<< ======= >>>>>>>
git add .
git merge --continue
git push origin dev
```

放弃本次合并、回到合并前状态：`git merge --abort`。

## 上游仓库地址变更

上游迁移或换了默认分支时，改脚本顶部变量，或手动调整 remote：

```powershell
git remote set-url upstream <新地址>
```