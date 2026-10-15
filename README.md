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
python workbuddy.py auto                  # 受守卫约束的完整运行（默认）
python workbuddy.py daily                 # 只跑每日功能
python workbuddy.py tasks                 # 只跑任务中心
python workbuddy.py status                # 只读：查看签到状态
python workbuddy.py doctor                # 离线检查凭据
python workbuddy.py auto --account <uid>  # 指定账号
python workbuddy.py auto --include-global # 也处理 global realm 账号
python workbuddy.py auto --force          # 跳过所有守卫
python workbuddy.py auto --dry-run        # 只显示守卫判定，不发请求
```

## 运行守卫

`auto` / `daily` / `tasks` 会先读本地状态（零成本），全部通过才发请求：

| 规则 | 默认值 |
|---|---|
| 每日成功上限 | 3 次 |
| 每日尝试上限 | 5 次（3 次成功 + 2 次重试余量） |
| 两次成功最小间隔 | 180 分钟 |
| 失败后重试间隔 | 15 分钟 |
| 网络探测 | 3 秒 TCP 连 `copilot.tencent.com:443`，不通则跳过且**不计尝试** |

状态存在 `state.json`，按本地日期自动重置。`status` / `doctor` 等只读命令不消耗次数。

## 账号

凭据放在 `auths/`，每个账号一个 JSON：

```json
{
  "account": { "uid": "...", "nickname": "..." },
  "auth": { "accessToken": "...", "domain": "www.codebuddy.cn", "realm": "cn", "refreshToken": "..." }
}
```

`global` realm 的账号默认跳过（任务中心只适用 CN 域），需要时加 `--include-global`。

## 定时任务（Windows）

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

脚本会**自动提权**（解锁触发器需要管理员权限），注册任务 `WorkBuddyAllInOne`，含 4 个触发器：

| 触发器 | 说明 |
|---|---|
| LogonTrigger | 登录后 |
| SessionStateChangeTrigger (SessionUnlock) | 每次解锁屏幕 |
| CalendarTrigger 11:00 | 每日兜底 |
| CalendarTrigger 19:00 | 每日兜底 |

配合守卫，解锁十几次也不会重复打接口。日志写入 `run.log`。

卸载：

```powershell
Unregister-ScheduledTask -TaskName "WorkBuddyAllInOne" -Confirm:$false
```

## 免责声明

非官方工具，与腾讯 / WorkBuddy 无任何关联。接口系从桌面端逆向所得，可能随时失效。使用风险自负，请遵守相关服务条款。

## 许可

MIT。`daily.py` 版权归 88lin；`scripts/task_runner.py` 等来自 Sliverkiss/workbuddy2api（MIT）。
