---
name: videobook
description: 把 YouTube 或 Bilibili 视频链接自动生成图文技术电子书（Markdown + 可交互 HTML）。流水线含：字幕抓取（yt-dlp / transcript-api）、AI 按 Stitcher 规范忠实整理字幕为带时间戳的 Markdown、浏览器截帧替换 SCREENSHOT 占位符、渲染暗色主题 HTML、本地 HTTP 预览、发布到 pages 分支。当用户提供 B 站/YouTube 视频链接并要求生成电子书/教程/图文指南/整理讲稿时使用。
compatibility: Python >= 3.12；截帧与字幕抓取需 Chrome（Playwright），部分命令需沙箱外执行；B 站直连、海外视频走代理。
---

# VideoBook 视频转电子书

把一段 YouTube / Bilibili 视频自动整理成图文电子书：
- `output/<video_id>/book.md` —— 忠实于原话的 Markdown 技术指南（逐字保留讲者原话，带时间戳与截图）
- `output/<video_id>/book.html` —— 暗色主题在线交互页（内嵌视频卡片、截图点击放大、Mermaid 交互）

## 触发条件

用户发来 YouTube (`youtube.com` / `youtu.be`) 或 B 站 (`bilibili.com`) 视频链接，并表示要生成电子书 / 教程 / 图文指南 / 整理讲稿。

## 运行前提

- **工作目录 = 本仓库根目录**。所有 `src/…`、`output/…`、`prompts/…`、`.capture-profile/` 均相对它解析。
- 依赖已安装（`.venv` 或 `pip install -r requirements.txt`）；命令用 `python` 执行，外部工具用 `sys.executable -m yt_dlp` 调用。
- B 站高画质截帧需登录态：首次运行 `python src/capture_frames.py --setup-profile` 登录一次（扫码即可，长期复用）。
- **网络线路**：B 站是国内站点，必须**直连**（绕过代理），否则字幕/播放接口报 502；YouTube 等海外视频必须**走代理**。B 站相关命令统一加前缀 `env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY`。

## 工作流

### 第 1 步：抓字幕

```bash
python src/dump_transcript.py "<VIDEO_URL>"
```

- 产出 `output/<video_id>/transcript.json`（含 `segments`、`duration`、`chapters`）。
- **覆盖率自检**：脚本打印字幕覆盖率，< 50% 会以退出码 3 结束——先按提示解决（通常是登录态），不得进入第 2 步。
- **线路**：YouTube 等海外视频需走代理；B 站必须**直连**（B 站命令加 `env -u *_proxy` 前缀，见运行前提），否则 502。B 站会自动从 `.capture-profile/` 导 cookies（写系统临时目录、用完即删）。
- 失败时告知用户可能原因（无字幕 / 需代理 / 需登录）并停止。

### 第 2 步：读字幕 + 生成 book.md

1. 读 `output/<video_id>/transcript.json` 和 `prompts/stitcher_system.md`。
2. 按 Stitcher 规范整理字幕：逐字保留讲者原话与语序、按内容逻辑分章、段落用 `> **[MM:SS–MM:SS]**` 标注时间戳。
3. 在关键界面/演示处插入截图占位符 `![画面描述](SCREENSHOT:HH:MM:SS)`。
4. 写入 `output/<video_id>/book.md`。
5. 生成修正版字幕对照稿：`python src/make_corrected.py <video_id>`（产出 `transcript.corrected.txt`，随发布上传供人工对照）。

### 第 3 步：截帧 + 替换占位符

画面必须直接来自平台播放器（登录态高画质），**不下载视频/音频**。默认专用截帧配置：

```bash
python src/capture_frames.py <video_id> "<VIDEO_URL>"
```

- 无头运行、顶档原生分辨率、流锁定、精确 `seek→pause` 截图、QA 自检、只截缺失帧。
- 完成后 `book.md` 不再有 `SCREENSHOT:` 占位符，`images/shot_HH_MM_SS.png` 齐全。
- 截帧后抽查 1–2 张（一张幻灯片帧、一张演示帧）确认清晰无遮挡。
- 全部浏览器方式失败才兜底：`python src/extract_frames.py <video_id> "<VIDEO_URL>"`（会下载视频，流程结束问用户是否删除）。

### 第 4 步：渲染 HTML + 本地预览

```bash
python src/post_process.py "<VIDEO_URL>" output/<video_id>/book.md
cd output/<video_id> && python -m http.server 8080
```

预览地址：**http://localhost:8080/book.html**（务必走 HTTP，勿用 `file://`，否则内嵌视频被拒载）。

### 第 5 步：交付

告知用户：
1. ✅ Markdown 文件：`output/<video_id>/book.md`
2. ✅ HTML 预览：http://localhost:8080/book.html
3. 提醒：YouTube 需浏览器代理、B 站直连；停服按 `Ctrl+C`。

### 第 6 步（可选）：发布 pages

```bash
python src/publish.py <video_id>   # 或 python src/publish.py --all
git push origin pages
```

## 沙箱 / 提权

- **需沙箱外执行**（Codex 中 require_escalated）：`dump_transcript.py`（B 站）、`capture_frames.py`、`capture_frames.py --setup-profile`。
- **沙箱内可跑**：`post_process.py`、`http.server`、`make_corrected.py`、`publish.py`（push 需网络）。
- **线路**：B 站直连（`env -u *_proxy` 前缀）；YouTube 走代理。

## 安全与幂等

- 导出的 cookies 落系统临时目录、用完即删；不要在仓库手放 `cookies.txt`。
- 各步幂等、可重跑；`book.tagged.md` 保留原始占位稿，物化后重跑仍能按占位符清单补帧。
- 生成/修改 HTML 时保持文本与背景对比度符合 WCAG AA（≥ 4.5:1）。

## 详细文档

完整手册（截帧三级优先级、修正稿订正规则、术语表与 ASR 噪声容忍、发布细节、踩坑指南）见 [references/workflow.md](references/workflow.md)。
