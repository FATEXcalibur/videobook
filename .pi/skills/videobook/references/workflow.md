# VideoBook 完整工作流手册（reference）

> 本文是 SKILL.md 的详细展开，供需要处理边缘情况时按需阅读。
> 工作目录始终为本仓库根目录，所有相对路径（`output/<video_id>/...`）均相对它解析。

## 触发条件

用户发来一条包含 YouTube (`youtube.com`, `youtu.be`) 或 B站 (`bilibili.com`) 视频链接的消息，并表示希望将其生成为电子书/教程/指南。

## 网络线路（重要）

本环境全局挂了代理（如 `http://172.18.128.1:7897`）。B 站是国内站点，**必须直连**（绕过代理），否则字幕/播放接口会报 `HTTP Error 502: Bad Gateway`；YouTube 等海外视频则必须走代理。

- **B 站**（`dump_transcript.py`、`capture_frames.py`、`capture_frames.py --setup-profile`）→ 直连，命令前加：

  ```bash
  env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY
  ```

- **YouTube** → 保持代理（不要去掉环境变量）。
- **症状对照**：B 站走代理 → yt-dlp 报 `Unable to download JSON metadata: HTTP Error 502`；B 站直连 → 约 0.x 秒返回 `code=0`。

## 第一步：提取字幕

```bash
python src/dump_transcript.py "<VIDEO_URL>"
```

- 脚本自动检测平台，抓取字幕并保存为 `output/<video_id>/transcript.json`。
- **B 站登录态自动获取**：专用配置 `.capture-profile/` 存在登录态时，脚本自动导出 cookies（系统临时目录、用完即删）。该过程启动无头 Chrome，**需沙箱外执行**。
- 若提示专用配置无登录态：请用户先运行 `python src/capture_frames.py --setup-profile` 登录一次，再重试。
- 可选参数：`--cookies-from-profile <dir>`、`--cookies-file <path>`（Netscape cookies 文件）、`--cookies-from <browser>`（旧方式，Windows 主 Chrome 新版加密通常不可用，勿默认使用）。
- **覆盖率自检**：成功时打印“字幕覆盖率”。低于 50% 会以退出码 3 结束并打印修复提示——不得进入第二步，先按提示解决（通常是登录态）。
- **transcript.json 结构**：含 `segments`、`duration`（总时长秒）、`chapters`（平台官方章节，可能为空）。第二步必须利用 `duration` 与 `chapters`。
- 失败则告知用户可能原因（无字幕、需代理、需登录）并停止。海外视频终端需走代理；B 站需直连（见「网络线路」）。

## 第二步：阅读字幕 + 生成电子书

1. 阅读 `output/<video_id>/transcript.json`。
2. 阅读 `prompts/stitcher_system.md` 获取排版指令。
3. 按 Stitcher Prompt 要求，将字幕重构为结构化 Markdown 技术指南。
4. 写入 `output/<video_id>/book.md`。

**关键要求：**
- 逐字保留讲者原话与语序（口语化表达不改成书面语），只做最小整理（短句拼接、分章、标时间戳）。
- 必须分章节，使用 `##` 标题，段落用 `> **[MM:SS–MM:SS]**` 标注时间范围。
- 必须在关键界面/操作步骤处插入截图占位符：`![场景描述](SCREENSHOT:HH:MM:SS)`。
- 仅当原字幕不是中文时才忠实翻译为中文（忠于原意，不润色不概括）。
- **官方章节仅供参考**：`chapters` 往往较粗，只辅助定位内容与选截图时间戳；顶层分章按内容自身逻辑组织，不要求与官方章节一一对应；`SCREENSHOT:` 时间戳落在所属内容时间区间内即可。
- **容忍 ASR 噪声**：先结合标题与 chapters 建立术语表，统一规范化同音错词（如“深圳市软件工程”→生成式、“威尔法/WIFI”→verifier、“KIMIK3”→Kimi K3、“chain of salt”→chain of thought）；口语梗保留原意。
- **产出修正版字幕对照稿**：`python src/make_corrected.py <video_id>`（或 `--all`）生成 `output/<video_id>/transcript.corrected.txt`——与 transcript.txt 同格式（`[MM:SS] 原文`、逐段不合并），保留讲师原始字词与顺序，仅做两类修改：ASR 错词替换（脚本内 MAP，按视频扩充）与口癖清理（纯语气词段删除、句尾语气词剥离、单字口吃折叠）；不改写为书面语、不概括。随后由 AI 通读做一轮行级订正（仅修明显错词/截断词/不通顺处，保留逐段结构与讲师原词，可委派子代理产出 old→new 清单后脚本应用；订正原则：少识别字词类错误必修，讲师有意为之的强调式重复原样保留）；生成后抽查若干行确认无过改；该文件随发布上传 pages。
- **截图时间戳选择**：优先章节边界、新幻灯片出现时刻、演示画面时刻；结合前后字幕语义定位，格式 `HH:MM:SS`。

## 第三步：截帧并替换占位符

画面必须直接来自平台播放器、使用已登录账号的高画质；本步任何方式都**不得下载视频/音频文件**。按以下优先级执行，**上一级全部失败才进入下一级**。

### 优先级 0（桌面环境首选）：Chrome 扩展（@Chrome）

仅当运行在 Codex/ChatGPT 桌面应用内、且 ChatGPT 浏览器扩展已安装并连接时使用：

- 逐个 `SCREENSHOT:` 时间戳（取自 `book.md` 或 `book.tagged.md`），在用户真实已登录的 Chrome 中打开平台播放器页，等待画面渲染后对标签页截图，保存为 `output/<video_id>/images/shot_HH_MM_SS.png`。
  - B 站：`https://player.bilibili.com/player.html?bvid=<video_id>&t=<秒>&autoplay=1&high_quality=1&danmaku=0`
  - YouTube：`https://www.youtube.com/embed/<video_id>?start=<秒>&autoplay=1&high_quality=1`
- 特点：登录态画质、后台运行、不接管屏幕。
- 全部截完后执行物化：`python src/capture_frames.py <video_id> --materialize-only`。
- 扩展未连接 / 失败 / 非桌面环境时进入优先级 1。

### 优先级 1：专用截帧配置（v2 管线，通用）

Chrome 136+ 禁止对**默认**用户数据目录做远程调试，脚本改用专用数据目录（默认 `.capture-profile/`）。

**一次性初始化（登录一次，长期复用）：**

```bash
python src/capture_frames.py --setup-profile
```

- 用专用配置启动 Chrome 窗口，登录所需平台后关闭。Cookies 持久化在 `.capture-profile/`，此后截帧自动带登录态画质。**会员等级决定截图清晰度上限**。

**日常截帧：**

```bash
python src/capture_frames.py <video_id> "<VIDEO_URL>"
```

v2 管线自动完成（Agent 无需也不应手工干预）：
- **无头运行**，失败自动回退有头；
- **权益探针**：抓前查询顶档原生分辨率，viewport 1:1 设置（不放大不糊，换账号/视频自动适配）；
- **流锁定**：拦截 playurl 响应，强制首帧即顶档最高码率流（根除自动档从 360P 起播导致的糊图）；
- **纯净帧**：CSS 隐藏播放器 UI，仅对 `<video>` 元素截图，无黑边；嵌入播放器优先，失败降级主站观看页；
- **精确帧**：`seek(目标秒)→等 seeked→pause` 后截图；
- **QA 自检**：文件过小判黑帧自动偏移重试；只截缺失帧；
- **增量友好**：占位符清单始终读自 `book.tagged.md`（若存在），物化后重跑也能正确补帧。

本步启动 Chrome，**需沙箱外执行**。更换配置目录：`--profile-dir <path>`。Cookie 过期时重新 `--setup-profile` 登录。

**Agent QA 习惯**：截帧后抽查 1–2 张图（一张幻灯片帧、一张演示帧）。整体发糊通常是账号档位问题——请用户在专用配置登录大会员账号后重跑。

### 兜底：下载视频源 + ffmpeg 抽帧

仅当所有浏览器方式失败（`capture_frames.py` 非零退出且提示 "All browser capture methods failed"）或无浏览器环境时：

```bash
python src/extract_frames.py <video_id> "<VIDEO_URL>"
```

- 若 `output/<video_id>/video_source.mp4` 不存在，自动用 yt-dlp 下载未登录最高 avc1 档（未登录画质，仅兜底）。需更高清晰度时先自行下载同名文件，脚本会跳过下载。
- `video_source.mp4` 属大媒体文件：中途保留，流程结束问用户是否删除。

### 明确排除的方式（不要使用）

- 内置浏览器（@Browser）：独立配置，无平台登录态。
- Playwright 干净 Chromium：无登录态。
- 对主 Chrome 默认数据目录的任何远程调试（CDP/Playwright 管道）：Chrome 136+ 禁止。
- win32 屏幕截取：接管用户屏幕，已移除。
- `--cookies-from chrome` 读主 Chrome：Windows 新版 App-Bound 加密，yt-dlp 无法解密。

### 完成标志

- `images/` 下每个时间戳都有 `shot_HH_MM_SS.png`，`book.md` 无 `SCREENSHOT:` 占位符。
- 第四步 HTML 中截图卡片内置点击放大（lightbox）：点击放大、点击空白处或 Esc 关闭。

## 第四步：转换 HTML + 启动预览

```bash
python src/post_process.py "<VIDEO_URL>" output/<video_id>/book.md
python -m http.server 8080 --directory output/<video_id>
```

纯本地步骤，沙箱内即可。预览地址 **http://localhost:8080/book.html**。

## 第五步：告知用户

1. ✅ Markdown：`output/<video_id>/book.md`
2. ✅ HTML 预览：http://localhost:8080/book.html
3. 提醒：YouTube 需浏览器代理；B 站直连；`Ctrl+C` 停服。
4. 若有 `video_source.mp4` / `audio.m4a` 等大媒体文件，问用户是否删除，确认后再删。
5. 截图清晰度说明：当前账号顶档纯视频帧（非大会员通常 720P）；需更高清晰度，在专用配置登录大会员账号后重跑 `capture_frames.py <video_id> <url>`。

## 注意事项

- 所有 Python 命令用 `python`（不用 `pip`，用 `python -m pip`）。
- 外部工具（yt-dlp）通过 `sys.executable -m yt_dlp` 调用。
- **沙箱/提权**：`dump_transcript.py`（B 站）、`capture_frames.py`、`capture_frames.py --setup-profile` 需沙箱外；`post_process.py`、`http.server` 沙箱内。
- **cookies 安全**：自动导出的 cookies 写系统临时目录、用完即删；不要在仓库手放 `cookies.txt`。
- **网络线路**：B 站直连（命令加 `env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY` 前缀），YouTube 走代理；B 站走代理会报 502（见「网络线路」）。
- **可重跑性**：各步幂等。`output/<video_id>` 被清理后重跑第一步恢复字幕；只要 `book.tagged.md` 还在，重跑第三步即可恢复截图。
- HTML 文本/背景对比度需符合 WCAG AA（≥ 4.5:1）。

## 第六步（可选）：发布到 pages 分支

```bash
python src/publish.py <video_id>   # 或 python src/publish.py --all
git push origin pages
```

- 将 book.html / book.md / images/ 及（若存在）transcript.corrected.txt 提交到独立 orphan 分支 `pages`，目录名 = 视频标题；落地页对含对照稿的书自动附“字幕对照”入口；不触碰 `output/` 与 main 工作区；内容无变化自动跳过提交。
- 纯本地 git 操作，沙箱内可跑；push 需网络。
- 首次推送后在 GitHub 仓库 Settings → Pages 一次性启用（分支 `pages`、目录 `/ (root)`），之后每次 push 自动部署。
