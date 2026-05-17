# thu-calendar-sync

清华课表 → Outlook 日历 / ICS 文件同步工具

## 功能

- 通过清华统一身份认证自动登录（支持 SM2 加密、二次认证、信任设备）
- 自动获取当前学期起止日期
- 获取本科生或研究生课程表
- 生成标准 ICS 文件，可直接导入任意日历应用（Outlook、Google Calendar、Apple Calendar 等）
- 支持直接写入 Outlook 日历（Windows + Outlook 桌面版）
- 支持课前提醒设置

## 安装

```bash
git clone https://github.com/<your>/thu-calendar-sync.git
cd thu-calendar-sync
pip install .
```

### 开发安装

```bash
pip install -e ".[test]"
```

## 配置

### 方式一：环境变量（推荐）

在项目目录下创建 `.env` 文件：

```env
THU_USERNAME=你的学号
THU_PASSWORD=你的密码
```

### 方式二：配置文件

复制 `thu-cal.toml.example` 为 `thu-cal.toml` 并按需修改。

配置优先级：`.env` 中的值覆盖 `thu-cal.toml` 中留空的字段。

## 使用

### 登录测试

```bash
thu-cal login
```

### 同步课表

```bash
# 预览模式（仅显示课表，不生成文件）
thu-cal sync

# 生成 ICS 文件
thu-cal sync --execute

# 指定学期范围
thu-cal sync --execute --start 2026-02-17 --end 2026-07-01

# 设置课前提醒（20 分钟前）
thu-cal sync --execute --reminder 20
```

### 查看状态

```bash
thu-cal status
```

### 直接运行（通过 python -m）

```bash
python -m thu_calendar_sync sync --execute --reminder 20
```

## 依赖

- Python >= 3.12
- Windows + Outlook 桌面版（可选，用于直接写入日历）
- ICS 文件生成模式无需 Outlook

## 许可证

MIT
