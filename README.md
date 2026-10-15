# WorkBuddy All-in-One

把两个独立项目合并成**一个入口**的 WorkBuddy 自动化工具：每日积分 + 成长任务中心，一次跑完。

## 合并来源

| 模块 | 功能 | 上游 |
|---|---|---|
| `daily.py` | 签到、猫猫旅行、断登补签、连登兑换、盲盒抽奖 | [88lin/workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin) |
| `scripts/task_runner.py` | 任务中心自动完成（专家召唤、模板使用、技能尝鲜、桌面对话链等） | [bbb2bb/workbuddy-task-helper](https://github.com/bbb2bb/workbuddy-task-helper) |

两个上游各管一半：前者做每日功能但不能完成任务本身，后者能完成任务但不做每日功能。本项目把它们拼在一起，共用同一份登录凭据。

## 用法

```bash
python workbuddy.py auto                  # 全部账号：每日功能 + 任务中心
python workbuddy.py daily                 # 只跑每日功能
python workbuddy.py tasks                 # 只跑任务中心
python workbuddy.py status                # 只读：查看签到状态
python workbuddy.py doctor                # 离线检查凭据
python workbuddy.py auto --account 1d07e826   # 指定账号
```

## 账号

凭据放在 `auths/` 目录，每个账号一个 JSON 文件，格式与 WorkBuddy2API 一致：

```json
{
  "account": { "uid": "...", "nickname": "..." },
  "auth": { "accessToken": "...", "domain": "www.codebuddy.cn", "realm": "cn", "refreshToken": "..." }
}
```

`auto` / `daily` / `tasks` 默认遍历 `auths/` 里的全部账号。`global` realm 的账号会被自动跳过（任务中心只适用 CN 域）。

## 定时任务（Windows）

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

- `WorkBuddyAllInOne`：每天 00:05，全量执行
- `WorkBuddyAllInOnePoll`：每 4 小时，补跑每日功能

日志写入 `run.log`。

## 免责声明

非官方工具，与腾讯 / WorkBuddy 无任何关联。接口系从桌面端逆向所得，可能随时失效。使用风险自负，请遵守相关服务条款。

## 许可

MIT。`daily.py` 版权归 88lin；`scripts/task_runner.py` 等来自 Sliverkiss/workbuddy2api（MIT）。
