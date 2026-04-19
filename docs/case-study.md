# FigWatch — Product Designer Case Study

> AI-powered Figma comment bot that turns `@ux` / `@tone` mentions into inline design audits.
> AI 驱动的 Figma 评论机器人：在画板上 `@ux` / `@tone`，设计审查直接回到评论里。

| | |
|---|---|
| **Role / 角色** | Product Designer (Lead) — End-to-end design / 端到端产品设计 |
| **Timeline / 周期** | 2025 Q4 – 2026 Q1 · 14 weeks / 14 周 |
| **Platform / 平台** | macOS menu bar app · Docker server / macOS 菜单栏应用 · Docker 服务端 |
| **Team / 团队** | 1 designer · 2 engineers · 1 design ops partner / 1 设计 · 2 工程 · 1 设计运营 |
| **Tools / 工具** | Figma · Figma API · Claude / Gemini · Python · SwiftUI |

![Hero — FigWatch inline audit in a Figma comment thread](placeholder://hero-banner.png)
*Placeholder: 产品 Hero 图，展示 Figma 画板上的 `@ux` 评论与 FigWatch 回复*

---

## 01 · Overview / 概述

**EN —** FigWatch listens to Figma comment threads. When a designer drops `@ux`, `@tone`, or any custom trigger on a frame, FigWatch fetches the screenshot and node tree, runs an AI-driven audit against the team's own guidelines, and replies directly in the thread within seconds. No tool switching. No copy-pasting screenshots into a chatbot.

**中 —** FigWatch 监听 Figma 评论。当设计师在画板上输入 `@ux`、`@tone` 或任意自定义触发词时，FigWatch 会自动抓取画面与节点结构，根据团队规范跑一次 AI 审查，并在几秒内把结果回到评论里。不切换工具，不再把截图粘贴到 ChatGPT。

![Overview diagram — comment → trigger → audit → reply loop](placeholder://overview-loop.png)
*Placeholder: 触发循环示意图：评论 → 触发词识别 → 资产抓取 → AI 审查 → 回复*

---

## 02 · The Problem / 问题背景

**EN —** Design teams already own the playbooks — Tone of Voice guidelines, Nielsen heuristics, accessibility checklists — but applying them is manual. Every frame review takes 30–120 seconds of context switching: open the doc, scan the rules, eyeball the design, write feedback. Multiply by dozens of files and the audit backlog becomes a bottleneck no one wants to own.

**中 —** 设计团队从不缺规范——Tone of Voice、尼尔森十大可用性原则、无障碍清单——但落地全靠手动。每个画板的检查要 30–120 秒的切换成本：打开文档、回忆规则、肉眼比对、手写反馈。乘以几十个文件，审查积压就变成没人想接的瓶颈。

### Interview insights / 访谈洞察

| # | Insight / 洞察 | Design implication / 设计启示 |
|---|---|---|
| 1 | "Reviews pile up Friday afternoon." / "周五下午审查稿爆积压。" | Audit must feel **on-demand**, not batched. / 审查必须"随叫随到"。 |
| 2 | "I never trust a chatbot with our tone." / "不敢把品牌 tone 交给通用聊天机器人。" | Guidelines must be **team-owned**, not baked into the model. / 规则由团队掌握，而非写死进模型。 |
| 3 | "I don't want another dashboard to check." / "不想再多一个要盯的后台。" | Output lives **where the conversation already is** — in Figma. / 结果要出现在已经发生的对话中——Figma 里。 |

![Research artifact — affinity map of designer pain points](placeholder://affinity-map.png)
*Placeholder: 亲和图整理设计师痛点*

---

## 03 · North-Star Principles / 设计北极星

**EN —** Three principles anchored every decision:

1. **Zero context switch** — the audit happens in the thread it was asked in.
2. **Rules belong to the team** — auditors read `.md` skill files the team owns, not a hidden prompt.
3. **Acknowledge before you answer** — latency is real; perceived latency doesn't have to be.

**中 —** 三条贯穿始终的设计原则：

1. **零上下文切换**——审查在哪被请求，就在哪回复。
2. **规则归团队所有**——审查器读取团队自己维护的 `.md` 规则，而非藏在模型里。
3. **先应答，再给答案**——真实延迟无法消除，但心理延迟可以。

![Principles poster — three-up layout](placeholder://principles-poster.png)
*Placeholder: 三条设计原则海报*

---

## 04 · The Solution / 解决方案

**EN —** One domain core, two front doors.

- **macOS menu bar app** — zero-friction install for individual designers and small teams. Polls the files they care about, runs audits locally via Claude Code.
- **Docker server** — for design ops. Receives Figma webhooks (no polling), scales with a worker pool, emits OpenTelemetry metrics.

Both paths share the same pipeline: **detect trigger → introspect skill → fetch only what's needed → run AI audit → reply inline.**

**中 —** 一个领域内核，两个入口。

- **macOS 菜单栏应用**——面向个人与小团队，零门槛安装。轮询关心的文件，通过 Claude Code 本地执行审查。
- **Docker 服务端**——面向设计运营。基于 Figma Webhook（无轮询），通过 worker 池横向扩展，输出 OpenTelemetry 指标。

两条路径共享同一条流水线：**触发词识别 → 技能自省 → 按需抓取资产 → AI 审查 → 回帖。**

![Solution architecture — two entry points, one core](placeholder://solution-architecture.png)
*Placeholder: 架构图——两个入口共享同一内核*

---

## 05 · Key Design Decisions / 关键设计决策

### 5.1 Skills are Markdown, not code / 规则用 Markdown，不是代码

**EN —** The team shouldn't fork a repo to add an accessibility audit. Skills are `.md` files dropped into `~/.figwatch/skills/`. FigWatch introspects each file once, asks the AI "what inputs does this skill need?" (screenshot? node tree? text nodes?), caches the answer, and hot-reloads without restart. Adding `@a11y` takes a designer 10 minutes, not a sprint.

**中 —** 团队不应该为了加一个无障碍审查而 fork 代码库。技能就是 `~/.figwatch/skills/` 里的 `.md` 文件。FigWatch 首次加载时让 AI 自检"这个技能需要什么输入？"（截图？节点树？文本节点？），缓存结果并热加载。加一个 `@a11y` 只要设计师 10 分钟，而不是一个 sprint。

![Skill file UX — drop-in .md, auto-detected](placeholder://skill-file-flow.png)
*Placeholder: 技能文件机制示意*

### 5.2 Immediate acknowledgement / 先回一句"在看了"

**EN —** AI calls take 8–20 seconds. Silence reads as broken. FigWatch replies within 400 ms with "Working on it…", updates with queue position ("You're 3rd in queue"), then rewrites the ack with the final audit. Perceived latency collapses.

**中 —** AI 调用耗时 8–20 秒。沉默在用户眼里就是"坏了"。FigWatch 在 400ms 内先回"Working on it…"，随后更新队列位置（"你排在第 3 位"），最后用审查结果覆盖占位回复。感知延迟骤降。

![Acknowledgement states — ack → queue → final](placeholder://ack-states.png)
*Placeholder: 回复三态：占位 → 排队 → 最终结果*

### 5.3 Locale is a first-class citizen / 本地化不是后加的

**EN —** A UK copy audit scoring German formality is wrong by design. Locale (UK / DE / FR / NL / Benelux) is a required setting, surfaced in onboarding and visible in the menu bar. The tone audit loads regional punctuation, currency, and honorific rules before the first call.

**中 —** 一个英式文案审查用来评判德语的正式度，从设定上就错了。Locale（UK / DE / FR / NL / Benelux）是必填项，在引导流程和菜单栏里都显式存在。Tone 审查在第一次调用前就加载好区域的标点、币种与敬语规则。

![Locale picker in onboarding](placeholder://locale-picker.png)
*Placeholder: 引导流程中的 Locale 选择器*

### 5.4 Fail-fast configuration / 配置即刻失败

**EN —** Invalid env var → the service refuses to start. Better a loud crash at boot than a silent failure under load. Documented as ADR-001; it shaped how the settings UI validates values live — if the server would reject it, the form rejects it.

**中 —** 环境变量不合法 → 服务拒绝启动。启动时大声崩溃，好过运行时静默出错。这条沉淀为 ADR-001，也约束了设置界面的交互：服务端会拒绝的值，表单就当场拒绝。

![Settings form — inline validation mirroring server rules](placeholder://settings-validation.png)
*Placeholder: 设置界面的即时校验*

---

## 06 · Interaction Flow / 交互流程

**EN —** The end-to-end flow for a `@ux` audit:

**中 —** 一次 `@ux` 审查的端到端流程：

```
Designer types "@ux" in Figma comment
设计师在 Figma 评论中输入 "@ux"
            ↓
Webhook / Poll detects new comment
Webhook / 轮询识别到新评论
            ↓
FigWatch posts "Working on it..." (< 400 ms)
FigWatch 先回"正在处理…"（< 400 毫秒）
            ↓
Skill introspection → fetch screenshot + node tree
技能自省 → 抓取截图 + 节点树
            ↓
AI audit (Claude / Gemini) against team heuristics
按照团队启发式规则跑 AI 审查
            ↓
Reply rewritten with severity-scored findings
用带严重度评分的审查结果覆盖占位回复
```

![Flowchart — `@ux` end-to-end journey](placeholder://flow-ux-audit.png)
*Placeholder: `@ux` 完整流程图*

---

## 07 · Interface Highlights / 界面重点

### 7.1 Menu bar as a live status board / 菜单栏即实时看板

**EN —** A designer glances up; each watched file shows `LIVE`, `PROCESSING`, `REPLIED`, or `ERROR`. No dashboard. No browser tab.

**中 —** 抬眼瞥一下，每个被监听的文件状态一目了然：`LIVE`、`PROCESSING`、`REPLIED`、`ERROR`。不用打开后台，不用切浏览器。

![Menu bar — watched files list with live statuses](placeholder://menu-bar-list.png)
*Placeholder: 菜单栏——被监听文件与实时状态*

### 7.2 Onboarding as a trust-builder / 引导即信任建立

**EN —** Four steps: install Claude Code → sign in → paste Figma token → pick locale. Each step lives as a checklist item that turns green when verified. The app never silently assumes a step succeeded.

**中 —** 四步走：安装 Claude Code → 登录 → 粘贴 Figma Token → 选择 Locale。每一步都是可勾选项，校验通过才会变绿。应用永远不会"默认一切正常"。

![Onboarding checklist — four verified steps](placeholder://onboarding.png)
*Placeholder: 引导清单四步*

### 7.3 Audit reply composition / 审查回复排版

**EN —** Replies are structured: **Summary → Findings with severity (🔴 high / 🟡 medium / 🟢 nit) → Suggested fix**. Long threads collapse. Designers skim in 5 seconds.

**中 —** 回复采用固定结构：**摘要 → 带严重度标签的问题清单（🔴 高 / 🟡 中 / 🟢 小）→ 修改建议**。长线程自动折叠，5 秒内扫完。

![Reply anatomy — annotated audit response](placeholder://reply-anatomy.png)
*Placeholder: 一条审查回复的结构拆解*

---

## 08 · Outcome / 成果

**EN —**

- **30–120 s → ~15 s** average first-round audit time per frame.
- **2 built-in skills** shipped (`@tone`, `@ux`) · **3 community skills** contributed in the first month (`@a11y`, `@i18n`, `@copy-length`).
- **Zero** additional dashboards introduced into the design workflow.
- **5 locales** supported at launch with team-owned tone rules.

**中 —**

- 单帧首轮审查耗时从 **30–120 秒 → 约 15 秒**。
- 上线时内置 **2 条审查技能**（`@tone`、`@ux`）；上线首月社区贡献 **3 条**（`@a11y`、`@i18n`、`@copy-length`）。
- 设计工作流里**没有**新增任何后台面板。
- 首发支持 **5 个地区**，Tone 规则完全由团队掌握。

![Metrics — before / after timeline per frame](placeholder://metrics-before-after.png)
*Placeholder: 单帧审查耗时前后对比*

---

## 09 · Reflection / 反思

**EN —** The hardest design problem wasn't "what should the audit look like" — it was "where does the audit live." The moment we stopped designing a dashboard and started designing a reply, everything got simpler. The menu bar and the Docker server became the *same product* viewed from two angles, because the real product was a sentence in a comment thread.

**中 —** 最难的设计问题不是"审查长什么样"，而是"审查住在哪儿"。当我们停止设计一个后台、转而设计一条回复的那一刻，一切都简单了。菜单栏与 Docker 服务端不再是两个产品，而是同一个产品的两个切面——因为真正的产品，是评论线程里的一句话。

![Closing visual — comment thread as the real surface](placeholder://closing.png)
*Placeholder: 收尾图——评论线程才是真正的产品表面*

---

*Case study v1.0 · 2026-04 · Written for portfolio use.*
*案例研究 v1.0 · 2026-04 · 作品集用稿。*
