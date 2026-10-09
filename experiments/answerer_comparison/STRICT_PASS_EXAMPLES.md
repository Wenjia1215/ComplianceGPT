# Three detailed strict-pass examples

以下三个实例均取自原始 Rev5 冻结运行结果，正文未经改写。Baseline 为 Qwen2.5-7B 4-bit free-form；Gemini 为归档的 Gemini 3.5 Flash；ComplianceGPT 为 4-bit selector 配置。每个问题的三组输入使用相同的上下文与有序证据窗口。

本文采用[完整 strict-pass 标准](../../src/answerer_comparison/README.md)：`S = C AND W AND L AND U AND A AND F AND P`。每项条件均须满足；不评分澄清问题的值域类型。正确改写可以通过。

| 实例 | 问题 | ComplianceGPT | Gemini | Baseline |
| --- | --- | --- | --- | --- |
| 1 | Rev5 Q35：非组织用户认证 | Pass | Fail | Fail |
| 2 | Rev5 Q76：安全分类与批准 | Pass | Pass | Fail |
| 3 | Rev5 Q24：配置设置 | Fail | Fail | Fail |

C 为合同与 gold 条件；W 为来源与证据窗口；L 为完整参数清单和状态；U 为引用实际使用；A 为必要正文内容；F 为主张忠实性；P 为参数含义。下表中的“未评分”表示合同条件已失败，语义判定无需再进行，并不表示该项通过。

## 实例一：ComplianceGPT 通过，Gemini 与 Baseline 不通过

**问题：Rev5 Q35**

> How should organizations handle identification and authentication of non-organizational users accessing federal systems?

**原始 gold 必需引用：** `ia-8_gdn`。

**标准原文：`ia-8_smt`**

```text
Uniquely identify and authenticate non-organizational users or processes acting on behalf of non-organizational users.
```

**标准原文：`ia-8.2_gdn`**

```text
Acceptance of only NIST-compliant external authenticators applies to organizational systems that are accessible to the public (e.g., public-facing websites).
```

IA-8 的基础义务是识别并认证非组织用户。IA-8(2) 的 guidance 另行限定：只接受 NIST-compliant 外部认证器的要求适用于公众可访问的组织系统。额外引用 IA-8(2) 本身允许，但作出这项额外主张时必须保留它的适用条件。

### 三组原始答案与合同字段

**ComplianceGPT**

状态：`OK`。声明参数：空集合。

实际返回的引用 ID：`ia-8_smt`, `ia-8_gdn`。

```text
Uniquely identify and authenticate non-organizational users or processes acting on behalf of non-organizational users.

Non-organizational users include system users other than organizational users explicitly covered by [IA-2](#ia-2) . Non-organizational users are uniquely identified and authenticated for accesses other than those explicitly identified and documented in [AC-14](#ac-14) . Identification and authentication of non-organizational users accessing federal systems may be required to protect federal, proprietary, or privacy-related information (with exceptions noted for national security systems). Organizations consider many factors—including security, privacy, scalability, and practicality—when balancing the need to ensure ease of use for access to federal information and systems with the need to protect and adequately mitigate risk.
```

**Gemini**

状态：`OK`。声明参数：空集合。

实际返回的引用 ID：`ia-8_smt`, `ia-8_gdn`, `ia-8.2_smt`, `ia-8.2_gdn`。

```text
Organizations must uniquely identify and authenticate non-organizational users (or processes acting on their behalf) for accesses other than those explicitly identified and documented in AC-14. Identification and authentication of these users may be required to protect federal, proprietary, or privacy-related information. When balancing ease of use with risk mitigation, organizations must consider factors such as security, privacy, scalability, and practicality. Additionally, organizations must accept only external authenticators that are NIST-compliant (and compliant with SP 800-63B for public-facing systems) and document and maintain a list of these accepted external authenticators.
```

**Baseline**

状态：`OK`。声明参数：空集合。

实际返回的引用 ID：`ia-8_gdn`, `ia-8.2_gdn`, `ia-8.2_smt`, `ia-8.2_smt.a`, `ia-8.2_smt.b`。

```text
Non-organizational users should be uniquely identified and authenticated. This includes accepting only NIST-compliant external authenticators and maintaining a list of accepted external authenticators.
```

### 逐项判定

| 系统 | C | W | L | U | A | F | P | 最终 strict pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ComplianceGPT | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| Gemini | Pass | Pass | Pass | Pass | Pass | Fail | Pass | Fail |
| Baseline | Pass | Pass | Pass | Pass | Pass | Fail | Pass | Fail |

### 判定理由

**ComplianceGPT — Pass。** 返回 `ia-8_smt` 与 gold 所需的 `ia-8_gdn`，正文完整保留这两条原文。它表达基础认证义务、AC-14 例外以及相关安全/隐私考虑。它没有提出“所有非组织用户认证都必须只接受 NIST-compliant 外部认证器”的额外结论。因此，它并非靠补写公众可访问限定而通过，而是回答了所需范围并避免了该失真的额外断言。

**Gemini — Fail，F 不满足。** 正文写成 `must accept only external authenticators that are NIST-compliant`，再把 `for public-facing systems` 放入 SP 800-63B 的括号说明。标准原文把公众可访问限定放在“只接受 NIST-compliant 外部认证器”这项义务上。将限定移到另一项合规描述，改变了原来要求的适用范围。

**Baseline — Fail，F 不满足。** `This includes accepting only NIST-compliant external authenticators` 同样把这项要求泛化到非组织用户认证，没有保留公众可访问限定。

**合同字段与正文均须满足要求。** 三组均覆盖 gold 必需引用，附带的 evidence spans 可验证；但引用证明与正文主张的忠实性是分别需要满足的条件。失败原因是主张失真，多引用增强控制本身不构成失败。

## 实例二：ComplianceGPT 与 Gemini 通过，Baseline 不通过

**问题：Rev5 Q76**

> What steps are required to categorize a system and its information, and who must approve the decision?

**原始 gold 必需引用：** `ra-2_smt.a`, `ra-2_smt.b`, `ra-2_smt.c`。

**标准原文：`ra-2_smt.a`**

```text
Categorize the system and information it processes, stores, and transmits;
```

**标准原文：`ra-2_smt.b`**

```text
Document the security categorization results, including supporting rationale, in the security plan for the system; and
```

**标准原文：`ra-2_smt.c`**

```text
Verify that the authorizing official or authorizing official designated representative reviews and approves the security categorization decision.
```

RA-2 要求分类系统及其处理/存储/传输的信息，在安全计划中记录分类结果及其支持理由，并由授权官或其指定代表审查批准。这里的 `including supporting rationale` 是必需记录内容，而非任意背景示例。

### 三组原始答案与合同字段

**ComplianceGPT**

状态：`OK`。声明参数：空集合。

实际返回的引用 ID：`ra-2_smt.a`, `ra-2_smt.b`, `ra-2_smt.c`。

```text
Categorize the system and information it processes, stores, and transmits;

Document the security categorization results, including supporting rationale, in the security plan for the system; and

Verify that the authorizing official or authorizing official designated representative reviews and approves the security categorization decision.
```

**Gemini**

状态：`OK`。声明参数：空集合。

实际返回的引用 ID：`ra-2_smt`, `ra-2_smt.a`, `ra-2_smt.b`, `ra-2_smt.c`。

```text
To categorize a system and its information, an organization must:
1. Categorize the system and the information it processes, stores, and transmits;
2. Document the security categorization results and supporting rationale in the security plan; and
3. Ensure that the authorizing official or authorizing official designated representative reviews and approves the categorization decision.
```

**Baseline**

状态：`OK`。声明参数：空集合。

实际返回的引用 ID：`ra-2_smt`, `ra-2_smt.a`, `ra-2_smt.b`, `ra-2_smt.c`。

```text
The system and information must first be categorized, then the results must be documented in the security plan, and finally, the authorizing official or their designated representative must review and approve the categorization decision.
```

### 逐项判定

| 系统 | C | W | L | U | A | F | P | 最终 strict pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ComplianceGPT | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| Gemini | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| Baseline | Pass | Pass | Pass | Pass | Fail | Pass | Pass | Fail |

### 判定理由

**ComplianceGPT — Pass。** 返回三条 gold 必需子条款，正文逐条保留分类、包含支持理由的记录，以及授权官/指定代表的审查批准。

**Gemini — Pass。** 它使用自己的句子组织答案，并明确写出 `Document the security categorization results and supporting rationale in the security plan`。分类对象、记录内容和批准责任均保留；父条款与子条款各自对应正文中的实际内容。因此 U/A/F/P 均通过，虽然正文不是原文拼接。

**Baseline — Fail，A 不满足。** 它写了分类、记录结果与授权官批准，却只说 `the results must be documented in the security plan`，没有表达同时记录支持理由。它返回了 `ra-2_smt.b`，所以 C 通过；但该子条款的全部必要记录内容没有进入正文。U 可以通过，因为该来源仍支持“记录结果”这个已表达的命题；A 因缺少必要组成部分而失败。

**本例说明：** 引用得到实际使用，并不自动意味着该条款的必要内容完整。正确改写可以通过，引用 ID 齐全的简洁答案也可能因遗漏关键义务而失败。

## 实例三：三组全部不通过

**问题：Rev5 Q24**

> How should configuration settings be established, approved, and monitored?

**原始 gold 必需引用：** `cm-6_smt.a`, `cm-6_smt.b`, `cm-6_smt.c`, `cm-6_smt.d`。

**标准原文：`cm-6_smt`**

```text
a. Establish and document configuration settings for components employed within the system that reflect the most restrictive mode consistent with operational requirements using {{ insert: param, cm-06_odp.01 }}; b. Implement the configuration settings; c. Identify, document, and approve any deviations from established configuration settings for {{ insert: param, cm-06_odp.02 }} based on {{ insert: param, cm-06_odp.03 }} ; and d. Monitor and control changes to the configuration settings in accordance with organizational policies and procedures.
```

**标准原文：`cm-6_smt.b`**

```text
Implement the configuration settings;
```

原始 gold 要求分别返回 `cm-6_smt.a`、`.b`、`.c`、`.d`。三个未绑定参数为 `cm-06_odp.01`、`cm-06_odp.02`、`cm-06_odp.03`，原始 gold policy 为 `ASK`。关键义务包括建立/记录、实施、批准偏离，以及监控/控制变更。

### 三组原始答案与合同字段

**ComplianceGPT**

状态：`PARAMS_REQUIRED`。声明参数：`cm-06_odp.01`, `cm-06_odp.02`, `cm-06_odp.03`。

实际返回的引用 ID：`cm-6_smt`, `cm-6_smt.a`, `cm-6_smt.c`, `cm-6_smt.d`。

```text
a. Establish and document configuration settings for components employed within the system that reflect the most restrictive mode consistent with operational requirements using {{ insert: param, cm-06_odp.01 }}; b. Implement the configuration settings; c. Identify, document, and approve any deviations from established configuration settings for {{ insert: param, cm-06_odp.02 }} based on {{ insert: param, cm-06_odp.03 }} ; and d. Monitor and control changes to the configuration settings in accordance with organizational policies and procedures.

Establish and document configuration settings for components employed within the system that reflect the most restrictive mode consistent with operational requirements using {{ insert: param, cm-06_odp.01 }};

Identify, document, and approve any deviations from established configuration settings for {{ insert: param, cm-06_odp.02 }} based on {{ insert: param, cm-06_odp.03 }} ; and

Monitor and control changes to the configuration settings in accordance with organizational policies and procedures.
```

**Gemini**

状态：`PARAMS_REQUIRED`。声明参数：`cm-06_odp.01`, `cm-06_odp.02`, `cm-06_odp.03`。

实际返回的引用 ID：`cm-6_smt`, `cm-6_smt.a`, `cm-6_smt.b`, `cm-6_smt.c`, `cm-6_smt.d`。

```text
Configuration settings should be established and documented for components to reflect the most restrictive mode consistent with operational requirements using an organization-defined security configuration checklist. Deviations from these settings for organization-defined system components must be identified, documented, and approved based on organization-defined operational requirements. Finally, changes to the settings must be monitored and controlled in accordance with organizational policies and procedures.
```

**Baseline**

状态：`OK`。声明参数：空集合。

实际返回的引用 ID：`cm-6_smt`, `cm-6_smt.a`, `cm-6_smt.c`, `cm-6_smt.d`。

```text
Configuration settings should be established and documented using the most restrictive mode consistent with operational requirements. Any deviations from these settings must be identified, documented, and approved based on organizational policies and procedures. Changes to configuration settings should be monitored and controlled according to organizational policies and procedures.
```

### 逐项判定

| 系统 | C | W | L | U | A | F | P | 最终 strict pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ComplianceGPT | Fail | Pass | Pass | 未评分 | 未评分 | 未评分 | 未评分 | Fail |
| Gemini | Pass | Pass | Pass | Fail | Fail | Pass | Pass | Fail |
| Baseline | Fail | Pass | Fail | 未评分 | 未评分 | 未评分 | 未评分 | Fail |

### 判定理由

**ComplianceGPT — Fail，C 不满足。** 它的父条款正文确实包含 `Implement the configuration settings;`，且参数清单和 PARAMS_REQUIRED 状态正确。但是返回的 ID 列表只有父条款及 `.a`、`.c`、`.d`，缺少 gold 要求的 `cm-6_smt.b`。规则要求逐个必需 ID 覆盖，因此父条款含有这段文字不能补救缺失的子条款 ID。

**Gemini — Fail，U 与 A 不满足。** 它返回了 `.b`，C/W/L 均通过；正文只表达建立/记录、偏离批准和监控/控制，没有实施配置设置的动作。因此 `.b` 是已列出但未实际用于正文的引用，必要实施义务也缺失。把正确原文放在 evidence_spans 中不能补救。

**Baseline — Fail，C 与 L 不满足。** 它同样缺少 `.b`。此外，返回的父条款和其他 spans 保留三个未绑定参数，合同却声明 `OK` 和空参数集，违反 ASK/status 条件及完整参数并集条件。其语义门槛无需再评分。

**原始错误标签：**

ComplianceGPT：

```text
MissedDocIds:['cm-6_smt.b']
```

Baseline：

```text
OKButUnresolvedODPPlaceholders
GoldPolicyASKButStatusNotParamsRequired
MissedDocIds:['cm-6_smt.b']
```

**本例说明：** 三组受到同一标准约束。ComplianceGPT 即使保留了某项义务的原文，也不能绕过必需引用 ID 条件；Gemini 即使返回了正确 ID，也不能绕过正文实际表达义务的条件。

## 核验来源

原始运行数据快照：`72979835f1e05bae513468ca4074b4d43497da2c`。最终判定取自 [逐题结果](rq2_frontier_baseline_rev5/results_v1/strict_pass_rows.csv)；语义失败的精确答案/来源摘录见 [审查记录](strict_pass_reviews.jsonl)。这是一组回溯审查实例，尚未经独立专家裁定，不用于宣称任何模型普遍优于其他模型。

| 问题 | 三组共享的 evidence-window SHA-256 |
| --- | --- |
| Rev5 Q35 | `796f3610e39533a76159e28238c0b2363c843f352c7e1d73612e221a92a51c47` |
| Rev5 Q76 | `aa4d52c27844f35547a6a1b088a50be2703749fe29f22e41ebf7c08b8892b189` |
| Rev5 Q24 | `44e1f80b745b47a0c29523c9ba224f7ff9e7d42fa9a779ba1958d0884f41fe3c` |

原始合同文件：

- [ComplianceGPT](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/references/rev5_compliancegpt_4bit.csv)
- [Gemini](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/contracts/rev5_generative_frontier_api.csv)
- [Baseline](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/references/rev5_generative_baseline_4bit.csv)
- [Rev5 gold](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv)
- [Rev5 canonical clause store](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl)
