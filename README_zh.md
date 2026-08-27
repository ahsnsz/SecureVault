# SecureVault——中文说明与完整打包指南

[English README](README.md)

**University of Liverpool | COMP390 FYP 2025/26**  
**作者：** Zhouyang Shen（201850515）

SecureVault 是一款使用 Python 和 CustomTkinter 开发的本地桌面密码管理器。保险库文件使用 AES-256-GCM 加密，密钥通过 Argon2id 从主密码派生。macOS 用户还可以为每个保险库单独启用 Touch ID 解锁。

本文档使用系统自带的命令行工具完成环境配置、测试、打包、验收和分发。macOS 使用 **Terminal（终端）**，Windows 使用 **PowerShell** 或 **Command Prompt（命令提示符）**，不要求安装 PyCharm 或其他 IDE。

## 目录

- [项目功能](#项目功能)
- [打包前准备](#打包前准备)
- [在终端中配置 Python 环境](#在终端中配置-python-环境)
- [安装依赖](#安装依赖)
- [打包前测试](#打包前测试)
- [打包 macOS 应用](#打包-macos-应用)
- [检查并运行打包结果](#检查并运行打包结果)
- [打包后的完整验收](#打包后的完整验收)
- [制作可分发的 ZIP](#制作可分发的-zip)
- [应用图标、签名和公证](#应用图标签名和公证)
- [Windows 打包说明](#windows-打包说明)
- [常见问题](#常见问题)

## 项目功能

- 创建、打开、切换、锁定和删除加密的 `.svdb` 保险库。
- 添加、搜索、编辑、复制和删除密码记录。
- 使用安全随机数生成密码，并确保包含用户选择的字符类型。
- 创建保险库或修改主密码时执行统一的主密码规则。
- 保险库无操作 5 分钟后自动锁定。
- 应用复制密码 30 秒后，在不覆盖其他应用新剪贴板内容的情况下自动清除。
- 在支持的 Mac 上使用保险库级别的 Touch ID 解锁。
- 原子化保存保险库，并维护 `.bak` 恢复副本。
- 兼容早期版本 SecureVault 创建的保险库文件。

## 打包前准备

### 系统要求

- Python 3.10 或更高版本。
- macOS Terminal：系统自带，用于生成 `SecureVault.app` 并测试 Touch ID。
- Windows PowerShell 或 Command Prompt：系统自带，用于生成 Windows `.exe`。

> PyInstaller 不是跨平台编译器。在 macOS 上打包 macOS 应用，在 Windows 上打包 Windows 应用。不能直接在 Mac 上生成可正式使用的 Windows `.exe`。

### 确认项目目录

打开系统终端，并进入整个 SecureVault 项目目录。

当前项目在这台 Mac 上可以使用：

```bash
cd /Users/zhouyangshen/Desktop/SecureVault
```

其他用户需要把路径替换为自己保存项目的位置，例如：

```bash
cd /path/to/SecureVault
```

项目根目录至少应该包含：

```text
SecureVault/
├── app/
├── tests/
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── SecureVault.spec
├── README.md
└── README_zh.md
```

后续命令都要从这个项目根目录开始执行。不要进入 `app/` 后再打包，否则入口文件、规格文件和模块导入路径可能不正确。

### 不要打包个人保险库

保险库数据默认保存在：

```text
~/Documents/SecureVault_Data/
```

打包前请确认没有把以下内容添加到 PyInstaller 的 `datas` 配置中：

- `.svdb` 保险库文件；
- `.bak` 保险库备份；
- 主密码或测试密码；
- `my_vaults/` 中的个人数据；
- macOS Keychain 中的凭据。

当前 `SecureVault.spec` 的 `datas=[]`，不会主动把这些个人文件打包进应用。

## 在终端中配置 Python 环境

为避免系统 Python 和其他项目的依赖互相影响，建议在项目中创建 `.venv` 虚拟环境。创建操作只需要执行一次；以后每次重新打开终端时，再激活它即可。

### macOS Terminal

1. 按 `Command + Space` 打开 Spotlight，输入 `Terminal` 并打开终端。
2. 进入项目根目录：

   ```bash
   cd /Users/zhouyangshen/Desktop/SecureVault
   ```

3. 确认 Python 版本：

   ```bash
   python3 --version
   ```

4. 首次使用时创建虚拟环境：

   ```bash
   python3 -m venv .venv
   ```

5. 激活虚拟环境：

   ```bash
   source .venv/bin/activate
   ```

激活成功后，终端提示符前通常会出现 `(.venv)`。

### Windows PowerShell

1. 打开开始菜单，搜索并打开 **PowerShell**。
2. 进入项目根目录，把示例路径换成自己的路径：

   ```powershell
   cd C:\path\to\SecureVault
   ```

3. 确认 Python 版本并创建虚拟环境：

   ```powershell
   python --version
   python -m venv .venv
   ```

   如果系统找不到 `python`，可以把 Windows 命令中的 `python` 换成 `py`。

4. 激活虚拟环境：

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

如果 PowerShell 的执行策略阻止激活脚本，可以改用 Command Prompt，或者在后续命令中直接使用 `.venv\Scripts\python.exe`。

### Windows Command Prompt

在命令提示符中进入项目并激活环境：

```bat
cd /d C:\path\to\SecureVault
python -m venv .venv
.venv\Scripts\activate.bat
```

### 确认解释器和工作目录

macOS Terminal：

```bash
python --version
python -c "import sys; print(sys.executable)"
pwd
```

Windows PowerShell：

```powershell
python --version
python -c "import sys; print(sys.executable)"
Get-Location
```

解释器路径应该位于项目的 `.venv` 中，工作目录应该是包含 `main.py`、`requirements-dev.txt` 和 `SecureVault.spec` 的 SecureVault 项目根目录。不要在一个 Python 环境中安装依赖，再用另一个环境打包。

## 安装依赖

首先升级 pip：

```bash
python -m pip install --upgrade pip
```

然后安装运行、测试和打包依赖：

```bash
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` 会同时安装 `requirements.txt` 中的运行依赖，以及 pytest 和 PyInstaller。

macOS 上还会安装 Touch ID 所需的：

- `keyring`；
- `pyobjc-framework-LocalAuthentication`。

这些包带有 macOS 平台条件，因此 Windows 会自动跳过它们。

确认关键依赖：

```bash
python -m pip show pyinstaller customtkinter cryptography argon2-cffi
```

macOS 还可以检查：

```bash
python -m pip show keyring pyobjc-framework-LocalAuthentication
```

## 打包前测试

### 1. 先运行源代码

```bash
python main.py
```

确认登录界面能够正常显示，再关闭应用继续后面的步骤。

### 2. 运行完整自动化测试

```bash
python -m pytest tests -v
```

测试应该全部通过。如果出现失败，请先修复失败，不要直接发布打包结果。

当前测试范围包括：

- AES-256-GCM 加密和文件篡改检测；
- Argon2id 密钥派生；
- 旧保险库格式兼容；
- 原子保存和备份恢复；
- 主密码规则；
- 密码生成；
- 记录 ID 稳定性；
- 剪贴板所有权和自动清除；
- 使用模拟 macOS 服务测试 Touch ID 行为。

## 打包 macOS 应用

项目已经提供 `SecureVault.spec`。它声明了入口文件、无控制台窗口模式，以及 Touch ID 和 macOS Keychain 的延迟导入。

不要重新执行会覆盖规格文件的 `pyi-makespec`。在项目根目录直接运行：

```bash
python -m PyInstaller --clean --noconfirm SecureVault.spec
```

参数作用：

- `--clean`：在构建前清理 PyInstaller 缓存和临时构建文件；
- `--noconfirm`：重新构建时直接替换已有输出，不等待终端确认；
- `SecureVault.spec`：使用项目已经维护好的打包配置。

构建期间终端会输出分析、依赖收集、可执行文件生成和应用 Bundle 创建过程。出现普通的可选模块警告不一定表示失败；最终必须看到构建成功信息，并且 `dist/SecureVault.app` 存在。

### 构建输出

打包完成后会生成：

```text
build/                         # PyInstaller 临时分析和构建文件
dist/SecureVault/              # onedir 运行目录
dist/SecureVault.app/          # 最终 macOS 应用
```

需要运行或分发的是：

```text
dist/SecureVault.app
```

不要只复制 `dist/SecureVault/SecureVault`，因为它依赖同目录中的 `_internal` 文件。

## 检查并运行打包结果

### 1. 从 Terminal 启动应用

```bash
open dist/SecureVault.app
```

也可以在 Finder 中打开 `dist`，双击 `SecureVault.app`。

### 2. 如果应用打开后立即退出

因为正式应用隐藏了控制台，可以先运行 onedir 目录中的可执行文件查看错误：

```bash
./dist/SecureVault/SecureVault
```

终端中通常会显示缺少模块、文件路径或导入失败的具体信息。

### 3. macOS 阻止未签名应用

当前 `SecureVault.spec` 使用：

```text
codesign_identity=None
bundle_identifier=None
icon=None
```

因此当前构建主要适合本机测试和课程演示。首次打开时，macOS 可能阻止未签名应用。

对于自己刚刚构建且确认可信的应用，可以在 Finder 中右键点击 `SecureVault.app`，选择“打开”，然后再次确认；也可以进入：

```text
System Settings → Privacy & Security
```

在安全提示中允许打开。不要对来源不明的应用绕过安全检查。

## 打包后的完整验收

不要只确认窗口能够打开。建议创建一个专门的测试保险库，依次检查：

1. 启动 `dist/SecureVault.app`。
2. 创建新的测试保险库。
3. 检查过短或过弱的主密码是否被拒绝。
4. 使用合格主密码创建并打开保险库。
5. 添加、搜索、编辑、复制和删除一条密码记录。
6. 关闭应用后重新打开保险库，确认数据仍然存在。
7. 检查错误主密码不能解锁保险库。
8. 检查锁定、退出登录和切换保险库功能。
9. 等待剪贴板自动清除，确认不会覆盖后来从其他应用复制的内容。
10. 在支持 Touch ID 的 Mac 上启用 Touch ID。
11. 关闭应用后重新启动，使用同一个保险库测试 Touch ID 解锁。
12. 修改主密码后，再次确认密码解锁和 Touch ID 都能正常工作。
13. 删除测试保险库，并确认对应的 Touch ID 凭据被清除。

请勿用唯一的重要保险库完成第一次打包验收。

## 制作可分发的 ZIP

macOS 应用是一个目录结构，不建议使用普通文件复制方式随意拆分。验收完成后，在项目根目录运行：

```bash
ditto -c -k --sequesterRsrc --keepParent \
  dist/SecureVault.app \
  SecureVault-macOS.zip
```

生成文件：

```text
SecureVault-macOS.zip
```

计算 SHA-256 校验值：

```bash
shasum -a 256 SecureVault-macOS.zip
```

提交作业或发布版本时，可以同时提供 ZIP 和校验值。解压后应再次启动应用做一次最终检查。

### 处理器架构

当前 `SecureVault.spec` 的 `target_arch=None`，默认使用当前 Python 和 Mac 的架构。

查看当前 Mac 架构：

```bash
uname -m
```

- `arm64`：Apple Silicon（M 系列芯片）；
- `x86_64`：Intel Mac。

如果需要同时支持两种架构，应分别在目标架构环境中构建和测试，或者使用同时支持两种架构的 Python 与依赖制作 universal2 版本。不能只修改文件名来改变应用架构。

## 应用图标、签名和公证

### 添加应用图标

当前项目还没有 `.icns` 图标，因此 `SecureVault.spec` 中是：

```python
icon=None
```

准备好例如 `assets/SecureVault.icns` 后，可以改为：

```python
icon='assets/SecureVault.icns'
```

然后重新执行完整测试和打包命令。不要使用普通 PNG 文件直接替代 macOS 的 `.icns` 文件。

### 本机或课程演示

如果应用只在自己的 Mac 上运行，或者在明确允许未签名应用的课程环境中演示，可以使用当前未签名构建。

### 正式公开发布

如果要把应用公开分发给其他 Mac 用户，建议完成：

1. 加入 Apple Developer Program。
2. 创建并安装 `Developer ID Application` 证书。
3. 为应用设置稳定的 Bundle ID，例如 `com.example.securevault`。
4. 使用 Developer ID 对应用及其内部可执行代码签名。
5. 启用 Hardened Runtime 和安全时间戳。
6. 使用 Apple `notarytool` 提交公证。
7. 公证成功后把票据 stapling 到应用或分发包。
8. 在另一台干净的 Mac 上测试下载、解压和首次启动流程。

签名身份、Team ID、Bundle ID 和 Apple 账户凭据因开发者账户而异，不应直接复制他人的值，也不要把 Apple 密码或私钥写进仓库。Apple 已停止使用旧的 `altool` 公证流程，正式发布应使用当前的 `notarytool` 流程。

相关官方资料：

- [PyInstaller 使用说明](https://pyinstaller.org/en/stable/usage.html)
- [PyInstaller Spec 文件说明](https://pyinstaller.org/en/stable/spec-files.html)
- [Apple：Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)

## Windows 打包说明

PyInstaller 不能在 macOS 上直接生成 Windows `.exe`。Windows 版本必须在 Windows 系统或 Windows 虚拟机中构建和测试。

当前 `SecureVault.spec` 包含 macOS `.app` Bundle 和 Touch ID 隐藏导入，主要用于 macOS。下面的 Windows 流程会在独立的 `windows-build` 目录中生成临时 spec，避免覆盖项目现有的 macOS `SecureVault.spec`。

### 使用 PowerShell 完整打包

打开 PowerShell，进入项目根目录：

```powershell
cd C:\path\to\SecureVault
```

首次打包时创建并激活虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖并运行测试：

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest tests -v
```

为 Windows 构建创建独立目录：

```powershell
New-Item -ItemType Directory -Force windows-build | Out-Null
Set-Location windows-build
```

然后从控制台生成无黑色命令行窗口的 onedir 应用：

```powershell
python -m PyInstaller --clean --noconfirm --windowed --onedir `
  --name SecureVault `
  --distpath ..\dist `
  --workpath build `
  ..\main.py
```

回到项目根目录并启动打包结果：

```powershell
Set-Location ..
.\dist\SecureVault\SecureVault.exe
```

最终需要分发整个目录：

```text
dist\SecureVault\
```

不能只发送 `SecureVault.exe`，因为它还需要同一目录中的依赖文件。

PowerShell 可以把完整目录压缩成分发包并计算校验值：

```powershell
Compress-Archive -Path .\dist\SecureVault -DestinationPath .\SecureVault-Windows.zip -Force
Get-FileHash .\SecureVault-Windows.zip -Algorithm SHA256
```

生成的分发文件是：

```text
SecureVault-Windows.zip
```

### 使用 Command Prompt

如果使用 Command Prompt，可以执行：

```bat
cd /d C:\path\to\SecureVault
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest tests -v
if not exist windows-build mkdir windows-build
cd windows-build
python -m PyInstaller --clean --noconfirm --windowed --onedir --name SecureVault --distpath ..\dist --workpath build ..\main.py
cd ..
dist\SecureVault\SecureVault.exe
```

Windows 不提供 macOS Touch ID 功能。`requirements.txt` 中带 macOS 平台条件的依赖会被自动跳过，不影响密码解锁和其他跨平台功能。

正式交付 Windows 版本前，也需要在 Windows 上完成创建保险库、保存、重新打开、剪贴板和锁定功能验收。

## 常见问题

### `No module named PyInstaller`

说明当前解释器没有安装开发依赖：

```bash
python -m pip install -r requirements-dev.txt
```

然后确认 `python -m pip` 和 `python -m PyInstaller` 使用的是同一个 Python。

### 找不到 `SecureVault.spec`

说明终端不在项目根目录。macOS Terminal 可以先进入项目：

```bash
cd /Users/zhouyangshen/Desktop/SecureVault
```

再执行打包命令。

### Touch ID 在源代码模式可用，但打包后不可用

依次检查：

1. 打包使用的解释器是否安装了 `keyring` 和 `pyobjc-framework-LocalAuthentication`。
2. 是否使用项目现有的 `SecureVault.spec`。
3. `hiddenimports` 中是否仍然包含 `LocalAuthentication` 和 `keyring.backends.macOS`。
4. macOS 是否已经录入 Touch ID。
5. 当前用户是否允许应用访问 macOS Keychain。

### 应用能打开，但找不到以前的保险库

打包不会把个人保险库放进应用。默认数据目录仍然是：

```text
~/Documents/SecureVault_Data/
```

也可以从登录界面手动选择原来的 `.svdb` 文件。

### 修改代码后应用没有变化

保存所有文件，然后重新运行：

```bash
python -m pytest tests -v
python -m PyInstaller --clean --noconfirm SecureVault.spec
```

确认启动的是最新的 `dist/SecureVault.app`，而不是之前复制到其他位置的旧版本。

### 是否需要提交 `build/` 和 `dist/` 到 GitHub

通常不需要。`build/` 是临时文件，`dist/` 是可重新生成的打包结果。源代码仓库应主要保留代码、测试、依赖文件、spec 文件和文档。正式发布包可以通过 GitHub Releases 单独上传。

## 最短打包命令清单

### macOS Terminal

首次打包时，在 Terminal 中依次运行：

```bash
cd /Users/zhouyangshen/Desktop/SecureVault
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests -v
python -m PyInstaller --clean --noconfirm SecureVault.spec
open dist/SecureVault.app
```

测试通过后制作 ZIP：

```bash
ditto -c -k --sequesterRsrc --keepParent \
  dist/SecureVault.app \
  SecureVault-macOS.zip
```

以后重新打包时，只需要重新进入项目、激活 `.venv`，然后从测试命令开始执行。

### Windows PowerShell

首次打包时，在 PowerShell 中依次运行：

```powershell
cd C:\path\to\SecureVault
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest tests -v
New-Item -ItemType Directory -Force windows-build | Out-Null
Set-Location windows-build
python -m PyInstaller --clean --noconfirm --windowed --onedir `
  --name SecureVault `
  --distpath ..\dist `
  --workpath build `
  ..\main.py
Set-Location ..
.\dist\SecureVault\SecureVault.exe
Compress-Archive -Path .\dist\SecureVault -DestinationPath .\SecureVault-Windows.zip -Force
```

最终交付前，请在目标系统上重新解压对应 ZIP，并完成一次完整功能验收。
