# 📚 技术文档索引

欢迎来到 WeChat SendMsg 的技术文档中心！这里包含了项目的详细技术实现、配置说明和开发指南。

**GitHub地址：https://github.com/xlight/wechat-sendmsg**

## 📖 文档列表

### 🚀 快速开始
- **[QUICK_START.md](QUICK_START.md)** - 快速安装和配置指南
- **[AVOID_BAN.md](AVOID_BAN.md)** - 防封号使用指南

### 🔧 技术实现
- **[TECHNICAL_IMPLEMENTATION.md](TECHNICAL_IMPLEMENTATION.md)** - 完整的技术实现文档
  - 核心实现原理
  - 技术架构详解
  - 功能特点技术细节
  - 安全与合规性说明

### 🛠️ 高级功能
- **[ANTI_BAN_GUIDE.md](ANTI_BAN_GUIDE.md)** - 防封号系统详细说明
- **[WINDOW_DETECTION_FIXES.md](WINDOW_DETECTION_FIXES.md)** - 窗口检测技术改进
- **[TRAY_RECOVERY_IMPROVEMENT.md](TRAY_RECOVERY_IMPROVEMENT.md)** - 系统托盘恢复技术

### 📦 编译打包
- **[nuitka/README.md](nuitka/README.md)** - Nuitka 编译打包指南

## 🎯 技术架构概览

### 核心组件
1. **MCP服务器** (`mcp_server.py`)
   - 基于 FastMCP SDK 实现
   - 支持 stdio 和 HTTP 双传输模式
   - 与 HTTP API 共享同一应用

2. **微信控制器** (`wechat_controller.py`)
   - 采用 Mixin 模式设计
   - 包含窗口查找、托盘管理、GUI操作等模块
   - 支持微信 NT 框架版本

3. **消息队列系统**
   - SQLite 持久化存储
   - 优先级队列管理
   - 自动重试机制

### 技术特性
- ✅ **纯GUI自动化** - 模拟键盘鼠标操作，无逆向工程
- ✅ **剪贴板输入** - 避免输入法干扰
- ✅ **智能窗口管理** - 自动恢复托盘窗口
- ✅ **防封号保护** - 多层防护机制
- ✅ **异步处理** - 不阻塞调用方

## 🔒 安全与合规

### 重要声明
本项目采用**纯GUI自动化技术**，绝无任何逆向工程或侵害行为：

1. **纯用户操作模拟** - 仅通过模拟键盘快捷键和鼠标点击操作微信
2. **无逆向工程** - 不涉及微信客户端逆向、内存读取、协议分析
3. **无数据窃取** - 不读取微信聊天记录、联系人信息等用户数据
4. **无协议破解** - 不分析或破解微信通信协议
5. **隐私保护** - 所有消息处理均在本地完成

### 技术合规性
- 仅使用公开的 Windows API 和 GUI 自动化技术
- 符合技术研究规范
- 所有操作均在用户界面层面完成

## 📁 项目结构

```
docs/
├── 📄 README.md                    # 本文档（技术文档索引）
├── 📄 QUICK_START.md               # 快速开始指南
├── 📄 AVOID_BAN.md                 # 防封号使用指南
├── 📄 TECHNICAL_IMPLEMENTATION.md  # 技术实现文档
├── 📄 ANTI_BAN_GUIDE.md            # 防封号系统详细说明
├── 📄 WINDOW_DETECTION_FIXES.md    # 窗口检测技术改进
├── 📄 TRAY_RECOVERY_IMPROVEMENT.md # 系统托盘恢复技术
└── 📂 nuitka/                      # 编译打包相关
    └── 📄 README.md                # Nuitka 编译指南
```

## 🛠️ 开发指南

### 环境要求
- Python 3.10+
- Windows 10/11 系统
- 微信 4.0+ NT 框架版本

### 依赖安装
```bash
pip install -r requirements.txt
```

### 代码结构
- `src/` - 源代码目录
  - `mcp_server.py` - MCP 服务器主文件
  - `wechat_controller.py` - 微信控制器
  - `window_finder.py` - 窗口查找模块
  - `tray_manager.py` - 托盘管理模块
  - `gui_operations.py` - GUI 操作模块
  - `anti_ban/` - 防封号系统

### 配置说明
详细配置参数请参考 `TECHNICAL_IMPLEMENTATION.md` 中的配置文件技术参数部分。

## 🤝 贡献指南

欢迎开发者贡献代码！请参考：
1. 阅读技术实现文档了解架构
2. 遵循现有代码风格
3. 添加适当的测试和文档
4. 提交 Pull Request

## 📞 技术支持

- **GitHub Issues**: 报告问题和功能建议
- **QQ群**: 技术交流和支持
- **文档**: 先查阅相关技术文档

## 📄 许可证

本项目采用 MIT 许可证开源。详见项目根目录的 LICENSE 文件。

---

*本文档最后更新：2026年*
*更多技术细节请查阅各子文档*

**GitHub地址：https://github.com/xlight/wechat-sendmsg**