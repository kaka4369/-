# 云芝画布 V1 Production Runbook

这份文档用于第一版内测上线：邀请码注册、用户中心、点数余额、后台手动充值、每用户独立存储、任务持久化、正式部署。

## 1. 发布前检查

```powershell
python -m unittest discover -s tests
node --check static\app.js
node --check static\admin.js
python -m py_compile main.py scripts\build_release_bundle.py
python scripts\build_release_bundle.py --output output\release\canvas-saas-commercial --zip
```

只部署 `output/release/canvas-saas-commercial` 或对应 zip，避免把 `.env`、`data/`、`storage/`、日志、截图和本地运行文件带到线上。

## 2. 必填生产环境变量

```text
APP_ENV=production
SESSION_SECRET=<至少 32 位随机字符串>
INVITE_CODE=<私有邀请码>
COOKIE_SECURE=1
AUTO_ADMIN_FIRST_USER=0
DEFAULT_CREDITS=0
```

API 供应商密钥放到平台的 secret manager，不要写进仓库或镜像：

```text
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
IMAGE_API_KEY=
IMAGE_GENERATION_URL=
IMAGE_MODEL=
VIDEO_API_KEY=
VIDEO_GENERATION_URL=
VIDEO_MODEL=
```

## 3. 初始化管理员

生产环境不允许第一个注册用户自动成为管理员。部署后运行一次：

```powershell
python main.py create-admin owner@example.com <strong-password>
```

如果该邮箱已存在，此命令会更新密码并提升为管理员；如果不存在，会创建管理员账号。

## 4. 数据与存储

- `data/` 保存 SQLite 数据库。
- `storage/users/<user_id>/` 保存每个用户自己的上传、输出和任务文件。
- 第一版适合内测或小流量单机。公开收费前建议迁移到 PostgreSQL、对象存储和独立任务队列。
- 每天备份 `data/` 和 `storage/`，保留至少 7 天。

## 5. 点数和充值边界

当前版本只支持后台手动充值。不要在官网上展示“自动支付已接入”，也不要开放未完成的自助付款入口。

上线后管理员流程：

1. 用户注册并登录。
2. 管理员进入后台用户列表。
3. 根据实际收款记录手动增加点数。
4. 系统记录 `credit_events`，任务失败会按已扣点数退款。

## 6. 已知边界

- SQLite 不适合多实例同时写入。
- 任务队列和租约状态保存在 SQLite，单机重启后过期任务会重新排队，不会重复扣点；上游请求同时携带稳定幂等键。
- worker 仍在应用进程内运行，适合内测或小流量单机，不适合多实例和高并发；扩大规模前应迁移到 PostgreSQL、对象存储和独立任务队列。
- 生成图片和视频会先写入 `storage/users/<user_id>/outputs` 并登记到资产库，再把任务标记为成功。
- 生产环境必须启用 HTTPS，否则 `COOKIE_SECURE=1` 下浏览器不会发送登录 Cookie。
