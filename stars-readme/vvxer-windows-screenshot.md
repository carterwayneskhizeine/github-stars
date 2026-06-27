# Windows Screenshot Skill for OpenClaw

PowerShell 实现的 Windows 屏幕截图工具，专为 OpenClaw 无头节点设计。

## 快速开始

```powershell
# 直接执行
powershell -File screenshot.ps1

# 输出：MEDIA:C:\Users\Administrator\.openclaw\media\screenshot_20260311_093000.png
```

## 集成到 OpenClaw

### 1. 通过 exec 执行截图

```bash
openclaw exec powershell -File screenshot.ps1
```

### 2. 发送到 Telegram

```bash
openclaw message send --channel telegram --target YOUR_USER_ID --media /path/to/screenshot.png
```

## 特点

✅ 无依赖 - 仅使用系统 .NET Framework  
✅ 快速 - GDI+ 硬件加速  
✅ 可靠 - 自动处理分辨率缩放  
✅ 集成 - 输出 MEDIA 前缀便于 OpenClaw 处理  

## 许可

MIT-0 (Open Source)
