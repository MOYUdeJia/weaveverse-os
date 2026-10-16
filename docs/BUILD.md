# 打包 Weaveverse OS

绿色版和安装包都从仓库根目录运行。用户数据在 `%APPDATA%\WeaveverseOS\`，两种包共用这一份。

## 绿色版

```powershell
cd D:\weaveverse-os
.\build.ps1
```

产物：`dist\WeaveverseOS\WeaveverseOS.exe`。旁边的目录要一起带走。带控制台排查时用 `.\build.ps1 -Console`。

需要本机已装 WebView2。这个包不含 faster-whisper / torch，本地语音识别仍用 `python main.py`。

## 安装包

用 Inno Setup 6，不用 NSIS。脚本短，卸载默认不会去删 `{userappdata}`，所以 `%APPDATA%\WeaveverseOS` 会留下来。

1. 安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)。`ISCC.exe` 可以在 Program Files，也可以在 `%LOCALAPPDATA%\Programs\Inno Setup 6\`。
2. 运行：

```powershell
cd D:\weaveverse-os
.\build-installer.ps1
```

脚本会先跑 `build.ps1`，再编译 `installer.iss`。产物：`dist\WeaveverseOS-Setup.exe`。

安装时可选目录，默认 `C:\Program Files\WeaveverseOS\`。开始菜单有快捷方式。桌面图标是可选项，默认不勾。卸载只删安装目录和快捷方式。
