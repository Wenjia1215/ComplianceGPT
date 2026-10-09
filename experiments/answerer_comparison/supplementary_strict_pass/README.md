# 论文补充实验的严格通过评估

统一采用 `strict-pass-v1`，条件为 `C ∧ W ∧ L ∧ U ∧ A ∧ F ∧ P`，不检查参数澄清值域，不重新生成或修补原始回答。主比较入口及记录保持不变。

```bash
python experiments/answerer_comparison/run_strict_pass.py --output-root /tmp/compliancegpt_main_scores
python experiments/answerer_comparison/run_supplementary_strict_pass.py --output-root /tmp/compliancegpt_supplementary_scores
```

补充入口评估 988 个冻结回答：无选择器 136 个、救援关闭和启用 272 个、固定门控 544 个、BF16 36 个。每个合同先复现原合同检查，再使用完整统一严格条件。缺失的来源对照记录、改动的冻结输入或不一致的上下文身份会中止评估；原 CSV 中的检查字段不回写。

无选择器和救援使用身份匹配的原窗口；门控条件使用各自归档窗口，逐条验证来源内容和校验值。Rev.5 无选择器的 85 个及 Rev.4 的 32 个原合同条件通过回答，因空 `ask_list` 不满足参数请求记录要求。Rev.5 固定 top-5 的 Q12、Q39、Q61 返回各自冻结窗口之外的来源。两类问题不涉及澄清值域。

BF16 的七条来源对照记录单独保存在 `../strict_pass_supplementary_reviews.jsonl`，其余相同回答复用主比较判定。Q17 的主体与系统执行关系不确定，留在分母中且不计通过。记录没有经过独立专家裁定；检验均是事后、未调整的探索性分析。不能用条件子集比较代替整体配对检验，也不能从整体不显著推出等价。

`results_v1/strict_pass_rows.jsonl` 给出唯一最终逐题判定；`summary.json` 给出各条件结果；`manifest.json` 固定原始输入、归档内容、评分代码和判定记录。各原实验目录的物化摘要同步使用同一最终严格结果；其他覆盖、长度、参数集合和运行时测量保持原值。原归档 ZIP 及拆分包保持冻结，作为原回答和执行身份记录。

验证包括原有 31 项相关测试、补充输入校验、逐题原合同条件复现，以及 12 个补充物化文件的逐字节复现。
