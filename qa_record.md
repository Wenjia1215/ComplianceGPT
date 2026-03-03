1:
我把你这份 **`D3_Presentation_Wen_Spring2026.pptx`** 逐页读完了（包括 speaker notes）。总体评价：**主线方向是对的**，但现在这套 slide 还达不到“导师听明白、听满意”的标准，主要因为：**核心贡献没有被“早、清、硬”地打出来**，以及有几处会被导师/committee 直接抓住问到你尴尬的地方（甚至看起来像“没准备好”）。

下面我先给你一个“导师满意的标准”，然后给你 **必须立刻修的 8 个硬问题**，最后是 **逐页审查（每页：问题/怎么改/建议讲法）**。

---

## 导师满意的标准（你要让他听到这 5 件事）

1. **你在解决一个高价值且明确的问题**（为什么 compliance QA 跟普通 QA 不一样）。
2. **你提出的“研究贡献”不是工程堆料**：至少 2–3 个可被论文定义/验证的贡献。
3. **你有可验证的定义与指标**（“verifiable”到底怎么被 verifier 检查）。
4. **你已经有可复现的 preliminary evidence**（哪怕只是 retrieval + contract validity 的一部分），并且 **没有自相矛盾**。
5. **你清楚知道接下来一年做什么、怎么写章、怎么 defense**（timeline + milestones）。

---

## 现在这套 deck 的 8 个硬问题（必须改）

1. **Slide 8 架构图是空的**（写着 “(Diagram) here”）。这是致命缺口。
2. **Results 区域有两页插了 FIU 大 logo（Slide 20/21）**，等于“结果页坏了”。这在导师眼里是“你没检查就拿来”。
3. **Error Bank 的定义/方法叙述与真实数据不一致**：你 slide 写“Top-10 discarding”，但你 repo 的 `error_bank_v1.csv` 里大量样本 BM25 其实 Top-10 能命中，只是 **Top-1 永远不命中**（构造条件是 Recall@1=0）。这会被问爆。
4. **Error Bank 数量写错**：你 slide 写 39，但当前文件是 **37** 条。
5. **Option A 约束没落实**：Limitations notes 里仍写 “HIPAA/PCI future work”。必须删掉（你已经明确不要提）。
6. **你没有一页正式的 RQs/Hypotheses slide**（proposal defense 必须有），现在只在 form 文本里有。
7. **你把“论文贡献”讲得过偏 retrieval**：Contract/Verifier/ODP 是你 dissertation 的硬贡献，但 deck 里呈现不够“硬”，没有一个可视化例子。
8. **slide 太长、taxonomy 占比太高**（10–13 四页讲 error bank taxonomy），容易让导师觉得你在“讲细节”，但 proposal 的“研究问题—方法—计划”反而不够突出。

---

## 逐页审查（按你当前页码）

### Slide 1（Title）

**问题**：标题没有锁定 NIST 范围；notes 里“多框架”叙述容易让人以为你还做 crosswalk。
**怎么改**：标题改成包含 scope：

* “ComplianceGPT: Mechanically Verifiable, Version-Aware RAG for **NIST SP 800-53 Rev4/Rev5**”
  **建议讲法（开场 20 秒）**：
* 一句话：**“我的 thesis 目标是把 compliance QA 从‘看起来对’变成‘审计可验’。”**
* 立刻补 scope：**“本 dissertation 只评估 NIST 800-53 Rev4/Rev5。”**
* 然后再说 motivation 可以提 “现实有多框架压力”，但强调“本论文先把 NIST 做到可验”。

---

### Slide 2（Outline）

**问题**：outline 很长、顺序对导师不友好。导师最想先看到：RQ/贡献/方法/计划。
**怎么改**：改成 6 段：

1. Problem & Why compliance is different
2. Key idea: Contract + Verifier + CCS
3. Research Questions & Hypotheses
4. Methods & Datasets (frozen + hashes)
5. Preliminary results (retrieval + diagnostics)
6. Plan/timeline + limitations/future work
   **讲法**：别解释“auditable”太长；一句话定义即可。

---

### Slide 3（Motivation）

**问题**：写“multiple frameworks simultaneously”可以，但你必须补一句避免 scope confusion。
**怎么改**：末尾加一行：

* “**This dissertation evaluates NIST SP 800-53 Rev4/Rev5 only.**”
  **讲法**：加一个具体痛点例子更好：审计时需要“条款 ID + 证据 span”。

---

### Slide 4（Why LLMs）

**问题**：总体 OK，但缺一个一眼懂的例子。
**怎么改**：加一行例子：

* Query: “account review frequency” vs Control: “AC-2(1) … review … at organization-defined frequency”
  **讲法**：强调 LLM 的价值是 “semantic gap”，但立刻转折：**不能让它自由生成**。

---

### Slide 5（Why RAG）

**问题**：notes 只有一句 “What problem RAG solves”，等于没稿；slide 文案也有语法问题（by retrieve）。
**怎么改**：

* 文案： “helps by **retrieving evidence** before answering”
* 加一个小图：Query → Retriever → Evidence → LLM
  **讲法（两句够）**：RAG 解决“无依据瞎编”的一部分，但 compliance 需要更强保证。

---

### Slide 6（Problem: Triple Failures）

**问题**：这一页很好，是你的核心 problem framing。缺点是没有“例子”。
**怎么改**：每个 failure 后加 1 行微例子：

* Version-blindness: Rev4 vs Rev5 wording mismatch
* ODP: “organization-defined frequency” must not be guessed
* Citation fidelity: weak evidence → must say NO_EVIDENCE
  **讲法**：你 notes 写得很好，但可缩短 30%（避免长段落）。

---

### Slide 7（Proposal: ComplianceGPT）

**问题**：缺少 “contract + verifier” 的关键词，会被当成“RAG + rules”。
**怎么改**：加一条：

* “**Contract + Verifier enforcement (mechanically checkable)**”
  **讲法**：一句话把 novelty 打出来：**LLM 只做 evidence selection，答案与证据由 pipeline 机械生成并验证。**

---

### Slide 8（System Architecture）

**问题**：现在是空白占位符。导师一定会不满意。
**怎么改（必须做）**：画一个极简框图：

* Input question
  → Retriever (S1–S7)
  → Selector LLM (outputs evidence IDs + ODP required list)
  → Deterministic filler (pull verbatim spans from CCS)
  → Verifier (checks contract)
  → Output: OK / PARAMS_REQUIRED / NO_EVIDENCE + evidence spans
  旁边两个数据源：**CCS**、**Org Profile（optional for FILL_FROM_PROFILE）**。
  **讲法**：30 秒讲完，不要讲实现细节。

---

### Slide 9（CCS counts）

**优点**：你写的 6,831 / 6,563 是对的（这是 smt+gdn+obj 的总数）。
**问题**：导师可能会问 “ODP/param 记录呢？”
**怎么改**：加一句脚注：

* “Clause parts count = smt+gdn+obj; ODP/PRM records stored separately for ODP handling.”
  **讲法**：强调 CCS 的意义：**条款级可引用、可复现 span**。

---

### Slide 10（Error Bank v1）

**问题（必须改）**：

* 写 “Top-10 discard” 与现有数据不一致；
* 写 “BM25 = 0.0”含糊；
* 写 39 queries，但实际是 37。
  **怎么改**：把方法改成与你现有 `error_bank_v1.csv` 一致：
* “Construction: queries where **BM25 Recall@1 = 0 by design** (gold not ranked #1).”
* “N=37 (rev5=24, rev4=13).”
* 删除 “Top-10 discard” 那条，除非你真的要重建数据集。
  **讲法**：强调这是 diagnostic set，不是替代 gold set。

---

### Slide 11–13（Taxonomy + decision procedure + fix mapping）

**问题**：现在占了 3–4 页，太多。proposal 主线会被稀释。
**怎么改（建议压缩）**：

* Slide 11 保留 3 类定义（Terminology / Generic / Semantic）
* Slide 13 保留 “Failure class → Fix” 表（很有用）
* Slide 12（decision procedure）移到 **backup**
  **讲法**：把重点放在“为何它能解释 ablation”。

---

### Slide 14（Citation Contract acceptance criteria）

**问题**：缺一个“可视化例子”。只写 criteria，导师会问：contract 长什么样？
**怎么改**：加一个小框：展示 6 行 JSON 示例（status、evidence_spans、odp_required_list）。
**讲法**：一句话定义 “verifiable”：**能被 verifier 自动判定 pass/fail**。

---

### Slide 15（Answerer pipeline design）

**问题**：还是偏抽象。
**怎么改**：用“3-step”流程替代文字：

1. Selector contract
2. Fill verbatim evidence
3. Verify + output status
   **讲法**：强调“safe refusal”不是软策略，是 contract 的一部分。

---

### Slide 16（Retrieval ladder）

**问题**：你的 outline 写 S1–S8，但这里是 S1–S7。会让人怀疑你混乱。
**怎么改**：两种选一：

* 如果主讲只讲到 S7：把所有地方统一成 **S1–S7**
* 如果你要提 S8：在最后加 “S8 (ongoing)” 并说明不作为当前主结果
  **讲法**：强调“为什么 S7 是 compliance 特化”：**safe/no-harm gating**。

---

### Slide 17（Query Rewrite）

**问题**：这一页几乎是空的（只有 “Principles”）。
**怎么改**：要么补成一页真正有内容的 slide：

* 3 条原则 + 一个 before/after rewrite 例子
  要么删掉（把 rewrite 当成 ladder 中一环即可）。
  **讲法**：不要讲太久，最多 45 秒。

---

### Slide 18（Metrics）

**问题**：文字很多。导师其实懂；你只需要表明“为什么这些指标适合 compliance”。
**怎么改**：保留定义 + 加一句：

* “Compliance cares about top-1 evidence because auditors rarely read beyond first citation.”
  **讲法**：缩短到 30 秒。

---

### Slide 19–21（Results）

**问题（严重）**：Slide 20/21 目前是 FIU 大 logo，占位/错误图片。导师看到会直接扣分。
**怎么改（最低要求）**：

* Slide 19 作为结果 section title 可以保留
* Slide 20：放 **总体（Rev5/Rev4/ODP/ErrorBank）Recall@1** 的对比图（柱状/表格）
* Slide 21：放 **MRR@10 或 nDCG@10**（或者 ErrorBank 专页）
  并且每页加一个“takeaway sentence”：
* “S7 improves hard-set ranking while avoiding reranker regressions.”（示意）
  **讲法**：讲结果要“结论先行”：先说 1 句 takeaway，再给数字。

---

### Slide 22（Error-mode analysis）

**优点**：思路对。
**问题**：没有图。
**怎么改**：加一张 per-mode breakdown 图（按三类分别画 Recall@1 或 MRR@10）。
**讲法**：把它和贡献绑定：你不是只报数，你解释“为什么改进”。

---

### Slide 23（Contributions）

**问题**：贡献写得不错，但缺 “ODP policies 作为可测贡献”。
**怎么改**：建议改成三条更硬的 dissertation contribution：

1. **Contract + verifier** for mechanically verifiable compliance QA
2. **CCS + ODP-safe policy semantics** (ASK/PRESERVE/FILL)
3. **Reliability-focused retriever + ErrorBank diagnostic evaluation**
   **讲法**：明确 “这三条将对应 dissertation 章节”。

---

### Slide 24–26（Artifacts）

**问题**：太散、且 ErrorBank 数量写错；错误标签描述也不一致。
**怎么改**：合并成 1 页即可：

* “Frozen datasets + hashes in ARTIFACTS.md”
* 列 5–6 个关键文件名（不要长清单）
  并更新：ErrorBank v1 = **37 queries**，label = 3 类 taxonomy。
  **讲法**：强调 reproducibility：hashes 防 baseline drift（导师会喜欢这一点）。

---

### Slide 27（Limitations）

**问题**：notes 里提 HIPAA/PCI（违反 Option A），必须删。
**怎么改**：Future work 只保留两项：

* delta-aware editing hooks（明确“未实现”）
* atomic obligation decomposition（明确“未实现”）
  **讲法**：limitations 要“诚实但不自毁”：讲限制 + 你怎么 mitigate。

---

### Slide 28（Dissertation Plan）

**问题**：现在写 “Phase 2 future: end-to-end answerer + verifier”，听起来像你 thesis 只做 retrieval。
**怎么改**：把 Phase 2 写成 thesis 的核心：

* Phase 1 (done): retrieval reliability + datasets
* Phase 2 (next): **end-to-end contract validity + ODP policy evaluation**
* Phase 3: writing/defense
  并加 month/year timeline（和你 form 对齐）。
  **讲法**：导师要听到“我能按计划毕业”。

---

### Slide 29（Thank you）

OK。

---

### Slide 30–33（Oracle micro-ablation + latency）

**建议**：全部标注为 **Backup**，不要主讲占太多时间。

* Slide 33 应该加标题 “Latency overhead”
* Slide 34 “P” 是垃圾页，删掉。

---

## 你现在最省力、最有效的改法（按优先级）

1. 立刻修：Slide 8 架构图、Slide 20/21 结果图、Slide 10 ErrorBank 定义/数量、Slide 27 删除 HIPAA/PCI、删 Slide 34。
2. 加一页：Research Questions/Hypotheses（proposal 必须有）。
3. 压缩：ErrorBank taxonomy 从 4 页压到 2 页（其余放 backup）。
4. 贡献重写：把 ODP policy + contract/verifier 放到最硬的位置。
5. 把“多框架”只当 motivation，并在早期明确 scope = NIST only。

---

如果你愿意，我可以直接帮你把这份 PPTX **改到可交导师版本**：

* 自动替换 ErrorBank 数字/文案（37、Recall@1=0 by construction）
* 删除 HIPAA/PCI future work
* 删除 slide 34、给 slide 33 加 title
* 把“RQs/Hypotheses”加成一页
* 但结果图（Slide 20/21）我需要你告诉我你想展示哪几张：**总体 Recall@1** + **ErrorBank per-mode**（我也可以从你 repo 的 ablation outputs 里自动生成图再塞回 PPT）。


2:

你这个教授的思路非常适合 **D3 proposal**：**Hook → Gap → Specific Problem → Aim**。它的强点是：把“为什么值得 PhD”从工程细节拉回到**目标函数不同**（compliance 的正确性/可审计性 vs 通用 QA 的流畅性/有用性）。我建议你保留这个结构，但做 4 个“更委员会友好”的加固点（否则容易被抓漏洞）。

---

## 你教授的框架哪里特别好

1. **把“不可容错”讲清楚**：在 compliance 场景里，错误不是“用户体验差”，而是**审计风险**、甚至合规声明错误。
2. **把 ODP 变成“Unknown boundary”**：这比泛泛讲 hallucination 强很多，因为它是标准文本的结构性事实。
3. **把“必须用 LLM，但不能让它说话”**变成 thesis 核心张力：LLM 做语义桥接/聚合，但要限制为 selector，这是你的研究钩子。
4. **Auditability** 角度最关键：你不是做“回答更好”，而是做“输出可作为审计证据链的一部分”。

---

## 我建议你再加固的 4 个点（委员会最爱问）

### A) 把“高价值问题”写成**可验证的定义**

很多学生会说“我们要 trustworthy”，委员会会追问：trustworthy 怎么测？
你要把目标定义成一句可检验的话：

> **合规 QA 的输出不是一段文字，而是一个可审计的 artifact：每个结论都必须能指回特定版本的 clause ID + verbatim evidence span，并且对 ODP 明确输出 PARAMS_REQUIRED 而非猜测。**

这能把你 thesis 从“RAG 做得更好”拉升到“**可验证输出规范（contract）**”。

### B) “Fluency vs Fidelity”要避免过度绝对化

你教授说“一字不差”很有冲击力，但委员会可能会抬杠：不是所有合规回答都必须逐字复述。
你可以改成更稳的表述：

> 在合规中，**证据必须逐字可追溯**；答案表述可以简洁，但其支撑证据必须是 verbatim、可定位、可复现。

这更符合你系统（answer_text 可以有，但 evidence_spans 必须 verbatim）。

### C) “为什么不能只做检索”要用你自己的研究设计闭环

教授的“三层论证”很好，但最好加一句：
你不是否定检索，你是在做：**检索 + 语义桥接 + 受约束的证据选择 + 机械验证**。
并且可以引用“citation correctness ≠ faithfulness”的研究来说明：仅有引用不够，还要验证引用是否真的支撑生成内容。([ACM Digital Library][1])

### D) 给 1 个极短的“语义鸿沟例子”

委员会最吃这个：一眼懂为什么 BM25/Ctrl+F 不够。
例子模板（你可换成你熟的 query）：

* User: “BYOD 个人 MacBook 办公怎么合规？”
* Standard: “AC-19 Access Control for Mobile Devices …” + 相关 enhancements
  解释：用户用场景语言，标准用抽象控制语言；传统检索依赖词面匹配，召回不稳；而 LLM 可做 rewrite/聚合，但必须受约束。

可以顺带引用法律/法条检索领域对“公式化法律语言下 lexical vs semantic 检索差异”的研究，来支撑“领域文本有特殊性”。([ACM Digital Library][2])

---

## 你可以直接用的 Hook→Gap→Problem→Aim（英文版，适合放进 Statement，≈200–230 words）

> **Hook:** Organizations rely on cybersecurity standards such as NIST SP 800-53 to design controls and pass audits. Yet these documents are large, technical, and written in formal control language, creating a semantic gap between practical security questions and the text engineers must cite during audits.
> **Gap:** Retrieval-augmented generation (RAG) and LLM assistants can bridge this semantic gap by rewriting queries and synthesizing content, but their default objective—fluent generation—conflicts with compliance requirements. Prior work shows that citation presence alone does not guarantee faithfulness: generated statements may not be truly supported by the cited sources.([ACM Digital Library][1])
> **Specific Problem:** Compliance QA is high-stakes and evidence-driven. Outputs must be traceable to a specific version of the standard, and must respect “unknown boundaries” such as Organization-Defined Parameters (ODPs), where guessing values is unacceptable.
> **Aim:** This dissertation proposes ComplianceGPT, a contract-based, mechanically verifiable compliance QA pipeline for NIST SP 800-53 Rev4/Rev5. It restricts the LLM to an evidence-selection role (IDs only), deterministically fills verbatim evidence spans from a canonical clause store derived from OSCAL, and uses an automated verifier to check citation resolvability, verbatim grounding, and status logic (OK / NO_EVIDENCE / PARAMS_REQUIRED). The goal is to produce audit-ready artifacts—not just plausible answers.

（其中 “citation correctness ≠ faithfulness” 的支撑点来自上述论文。）

---

## 回答“为什么必须是 AI/LLM，而不是纯检索？”的最强 30 秒版本

你教授的三层论证我建议浓缩成这段（面试/答辩直接背）：

> 纯检索解决的是“找文档”，但合规 QA 的瓶颈是 **semantic gap + cognitive load**：问题是业务口语，标准是控制语言，BM25/Ctrl+F 依赖词面匹配，在领域文本上经常召回失败；法律检索研究也显示 lexical/semantic 模型在公式化法律语言下存在明显表现差异。([ACM Digital Library][2])
> LLM 的价值在于 **理解意图、重写查询、跨条款聚合**。但它的风险是自由生成会不忠实。我们的贡献就是“封口不封脑”：让 LLM 只做证据选择，答案证据由系统从 canonical corpus 机械构造，并由 verifier 自动检查。([GitHub][3])

（我额外引用了 Attributed QA 方向作为“答案+归因”这一任务设定的学术背景。([GitHub][3])）

---

## 你这套叙事在 slides 里怎么落地（建议放在前 3 页）

* **Slide 1（Hook）**：1 句话 + 1 个真实场景问题
* **Slide 2（Gap）**：一句“LLM 能桥接语义鸿沟，但 citation≠faithfulness” + 1 个示意图（RAG 可能引用但不支撑）
* **Slide 3（Aim）**：你的“封口不封脑”框图：Selector-only → deterministic filler → verifier → audit-ready artifact

---

如果你愿意，我可以把你这段对话内容直接“压缩成你的 D3 开场 45 秒讲稿 + Slide 1–3 的三页文字（每页一句 takeaway + 3 bullet）”，保证导师一听就知道你 thesis 的核心闭环在哪里。

[1]: https://dl.acm.org/doi/10.1145/3731120.3744592?utm_source=chatgpt.com "Correctness is not Faithfulness in Retrieval Augmented ..."
[2]: https://dl.acm.org/doi/full/10.1145/3769126.3769205?utm_source=chatgpt.com "Assessing the performance gap between lexical and ..."
[3]: https://github.com/google-research-datasets/Attributed-QA?utm_source=chatgpt.com "google-research-datasets/Attributed-QA"
