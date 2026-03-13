# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd


STATUS_ORDER = {
    'OK': 0,
    'PARAMS_REQUIRED': 1,
    'NO_EVIDENCE': 2,
    'ERROR': 3,
}


def _safe_json_load(x: Any) -> Dict[str, Any]:
    if not isinstance(x, str) or not x.strip():
        return {}
    try:
        obj = json.loads(x)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _split_pipe_or_newline(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, float) and np.isnan(x):
        return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    s = str(x).strip()
    if not s or s.lower() == 'nan':
        return []
    if s.startswith('[') and s.endswith(']'):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [str(v).strip() for v in arr if str(v).strip()]
        except Exception:
            pass
    parts = s.split('|') if '|' in s else s.splitlines()
    return [p.strip() for p in parts if p.strip()]


def _rate(mask: Iterable[Any]) -> float:
    s = pd.Series(list(mask))
    if len(s) == 0:
        return 0.0
    return float(s.fillna(False).astype(bool).mean())


def _nanmean(series: pd.Series) -> float:
    if len(series) == 0:
        return float('nan')
    return float(np.nanmean(pd.to_numeric(series, errors='coerce').values))


def _status_sort_value(x: Any) -> tuple[int, str]:
    s = '' if pd.isna(x) else str(x)
    return (STATUS_ORDER.get(s, 99), s)


def attach_gold_odp_fields(df: pd.DataFrame, gold_df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    gold = gold_df.copy()
    if 'id' in gold.columns and 'query_id' not in gold.columns:
        gold['query_id'] = gold['id'].astype(str)
    gold['query_id'] = gold['query_id'].astype(str)
    gold['gold_has_odp'] = gold['odp_required'].apply(lambda x: len(_split_pipe_or_newline(x)) > 0)
    keep = [
        c for c in ['query_id', 'gold_has_odp', 'odp_required', 'resolution_policy', 'answer']
        if c in gold.columns
    ]
    out['query_id'] = out['query_id'].astype(str)
    return out.merge(gold[keep], on='query_id', how='left', suffixes=('', '_gold'))


def committee_metric_table(eval_df: pd.DataFrame, system_name: str) -> pd.DataFrame:
    """
    Committee-facing metric table.

    In the current no-profile RQ2 comparison setting, ODP correct handling means:
    - the row is an ODP-bearing gold question, and
    - the system surfaces the unresolved ODP condition by returning PARAMS_REQUIRED.
    """
    df = eval_df.copy()
    if 'gold_has_odp' not in df.columns:
        df['gold_has_odp'] = False
    if 'odp_required_list' not in df.columns:
        df['odp_required_list'] = ''
    if 'status' not in df.columns:
        df['status'] = ''

    odp_mask = df['gold_has_odp'].fillna(False).astype(bool)
    has_odp_list = df['odp_required_list'].apply(lambda x: len(_split_pipe_or_newline(x)) > 0)
    status_is_params_required = df['status'].eq('PARAMS_REQUIRED')
    status_is_ok = df['status'].eq('OK')

    row = {
        'system': system_name,
        'n_questions': int(len(df)),
        'audit_ready_answer_rate': _rate(df.get('verifier_pass', pd.Series(dtype=bool))),
        'right_control_found_rate': _rate(df.get('control_hit_any', pd.Series(dtype=bool))),
        'right_clause_found_rate': _rate(df.get('doc_hit_any', pd.Series(dtype=bool))),
        'full_gold_clause_coverage_rate': _rate(df.get('doc_full_recall', pd.Series(dtype=bool))),
        'answer_has_supporting_evidence_rate': _rate(df.get('has_evidence_spans', pd.Series(dtype=bool))),
        'average_supporting_span_count': float(pd.to_numeric(df.get('evidence_span_count', 0), errors='coerce').fillna(0).mean()) if len(df) else 0.0,
        'strict_verbatim_grounding_rate': _nanmean(df.get('verbatim_strict_pass_rate', pd.Series(dtype=float))),
        'normalized_verbatim_grounding_rate': _nanmean(df.get('verbatim_normalized_pass_rate', pd.Series(dtype=float))),
        'n_odp_questions': int(odp_mask.sum()),
        'odp_correct_handling_rate': _rate(status_is_params_required[odp_mask]) if odp_mask.any() else float('nan'),
        'odp_false_complete_rate': _rate(status_is_ok[odp_mask]) if odp_mask.any() else float('nan'),
        'odp_unresolved_detected_rate': _rate((status_is_params_required | has_odp_list)[odp_mask]) if odp_mask.any() else float('nan'),
        'odp_unresolved_hidden_rate': _rate((~status_is_params_required & ~has_odp_list)[odp_mask]) if odp_mask.any() else float('nan'),
    }
    return pd.DataFrame([row])


def build_status_matrix(baseline_eval: pd.DataFrame, compliance_eval: pd.DataFrame) -> pd.DataFrame:
    left = baseline_eval[['query_id', 'status']].rename(columns={'status': 'baseline_status'}).copy()
    right = compliance_eval[['query_id', 'status']].rename(columns={'status': 'compliancegpt_status'}).copy()
    left['query_id'] = left['query_id'].astype(str)
    right['query_id'] = right['query_id'].astype(str)
    merged = left.merge(right, on='query_id', how='inner')
    if merged.empty:
        return pd.DataFrame(columns=['baseline_status', 'compliancegpt_status', 'n'])
    out = merged.groupby(['baseline_status', 'compliancegpt_status'], dropna=False).size().reset_index(name='n')
    out['_baseline_sort'] = out['baseline_status'].map(lambda x: _status_sort_value(x))
    out['_cgpt_sort'] = out['compliancegpt_status'].map(lambda x: _status_sort_value(x))
    out = out.sort_values(['_baseline_sort', '_cgpt_sort']).drop(columns=['_baseline_sort', '_cgpt_sort']).reset_index(drop=True)
    return out


def build_head_to_head_failure_table(baseline_eval: pd.DataFrame, compliance_eval: pd.DataFrame) -> pd.DataFrame:
    b = baseline_eval.copy()
    c = compliance_eval.copy()
    b['query_id'] = b['query_id'].astype(str)
    c['query_id'] = c['query_id'].astype(str)
    merged = b.merge(c, on=['query_id', 'framework_version', 'question'], how='inner', suffixes=('_baseline', '_compliancegpt'))
    if merged.empty:
        return pd.DataFrame([{
            'n_compared_questions': 0,
            'compliancegpt_strict_win_rate': float('nan'),
            'generative_false_complete_vs_compliancegpt_safe_warning_rate': float('nan'),
            'generative_missed_right_control_vs_compliancegpt_rate': float('nan'),
            'same_final_status_rate': float('nan'),
        }])

    row = {
        'n_compared_questions': int(len(merged)),
        'compliancegpt_strict_win_rate': _rate((~merged['verifier_pass_baseline'].fillna(False)) & (merged['verifier_pass_compliancegpt'].fillna(False))),
        'generative_false_complete_vs_compliancegpt_safe_warning_rate': _rate(merged['status_baseline'].eq('OK') & merged['status_compliancegpt'].eq('PARAMS_REQUIRED')),
        'generative_missed_right_control_vs_compliancegpt_rate': _rate((~merged['control_hit_any_baseline'].fillna(False)) & (merged['control_hit_any_compliancegpt'].fillna(False))),
        'same_final_status_rate': _rate(merged['status_baseline'] == merged['status_compliancegpt']),
    }
    return pd.DataFrame([row])


def build_failure_examples(
    baseline_eval: pd.DataFrame,
    compliance_eval: pd.DataFrame,
    baseline_contracts: pd.DataFrame,
    compliance_contracts: pd.DataFrame,
    top_n: int = 20,
) -> pd.DataFrame:
    b_eval = baseline_eval.copy()
    c_eval = compliance_eval.copy()
    b_con = baseline_contracts.copy()
    c_con = compliance_contracts.copy()
    for df in (b_eval, c_eval, b_con, c_con):
        df['query_id'] = df['query_id'].astype(str)
    merged = b_eval.merge(c_eval, on=['query_id', 'framework_version', 'question'], how='inner', suffixes=('_baseline', '_compliancegpt'))
    merged = merged.merge(b_con[['query_id', 'contract_json']].rename(columns={'contract_json': 'contract_json_baseline'}), on='query_id', how='left')
    merged = merged.merge(c_con[['query_id', 'contract_json']].rename(columns={'contract_json': 'contract_json_compliancegpt'}), on='query_id', how='left')

    rows = []
    for _, r in merged.iterrows():
        is_false_complete = (r.get('status_baseline') == 'OK') and bool(r.get('gold_has_odp_baseline'))
        lost_to_cg = (not bool(r.get('verifier_pass_baseline'))) and bool(r.get('verifier_pass_compliancegpt'))
        if not (is_false_complete or lost_to_cg):
            continue
        bc = _safe_json_load(r.get('contract_json_baseline', ''))
        cc = _safe_json_load(r.get('contract_json_compliancegpt', ''))
        rows.append({
            'query_id': r.get('query_id'),
            'framework_version': r.get('framework_version'),
            'question': r.get('question'),
            'gold_has_odp': bool(r.get('gold_has_odp_baseline')),
            'baseline_status': r.get('status_baseline'),
            'compliancegpt_status': r.get('status_compliancegpt'),
            'baseline_verifier_pass': bool(r.get('verifier_pass_baseline')),
            'compliancegpt_verifier_pass': bool(r.get('verifier_pass_compliancegpt')),
            'baseline_primary_citation': r.get('primary_citation_baseline', ''),
            'compliancegpt_primary_citation': r.get('primary_citation_compliancegpt', ''),
            'baseline_answer_preview': str(bc.get('answer_text', '') or '')[:320],
            'compliancegpt_answer_preview': str(cc.get('answer_text', '') or '')[:320],
        })
    ex = pd.DataFrame(rows)
    if ex.empty:
        return ex
    ex['sort_key'] = (
        ex['gold_has_odp'].astype(int) * 100
        + (~ex['baseline_verifier_pass']).astype(int) * 10
        + ex['baseline_status'].eq('OK').astype(int)
    )
    return ex.sort_values(['sort_key', 'query_id'], ascending=[False, True]).drop(columns=['sort_key']).head(int(top_n)).reset_index(drop=True)


def compare_answerers(
    *,
    baseline_eval: pd.DataFrame,
    baseline_contracts: pd.DataFrame,
    compliance_eval: pd.DataFrame,
    compliance_contracts: pd.DataFrame,
    gold_df: pd.DataFrame,
    framework_version: str,
    output_dir: str | Path | None = None,
    ts: str | None = None,
) -> dict[str, pd.DataFrame]:
    b_eval = attach_gold_odp_fields(baseline_eval, gold_df)
    c_eval = attach_gold_odp_fields(compliance_eval, gold_df)

    system_table = pd.concat(
        [
            committee_metric_table(c_eval, 'ComplianceGPT'),
            committee_metric_table(b_eval, 'Generative RAG baseline'),
        ],
        ignore_index=True,
    )
    head_to_head = build_head_to_head_failure_table(b_eval, c_eval)
    status_matrix = build_status_matrix(b_eval, c_eval)
    examples = build_failure_examples(b_eval, c_eval, baseline_contracts, compliance_contracts)

    outputs = {
        'system_table': system_table,
        'head_to_head': head_to_head,
        'status_matrix': status_matrix,
        'failure_examples': examples,
        'baseline_eval_augmented': b_eval,
        'compliance_eval_augmented': c_eval,
    }

    if output_dir is not None:
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        stamp = ts or 'manual'
        for name, df in outputs.items():
            if isinstance(df, pd.DataFrame):
                df.to_csv(outdir / f'{framework_version}_{name}_{stamp}.csv', index=False)

        lines = [
            f'# RQ2 Answerer Comparison Report ({framework_version})',
            '',
            '## Metric guide',
            '',
            '- **audit_ready_answer_rate**: strict verifier pass rate.',
            '- **right_control_found_rate**: correct gold control was found anywhere in the retrieved/cited result set.',
            '- **right_clause_found_rate**: correct gold clause/document path was found.',
            '- **full_gold_clause_coverage_rate**: all required gold clause paths were recovered.',
            '- **answer_has_supporting_evidence_rate**: answer includes supporting evidence spans.',
            '- **odp_correct_handling_rate**: on ODP questions in this no-profile setting, the system correctly returned `PARAMS_REQUIRED`.',
            '- **odp_false_complete_rate**: on ODP questions, the system returned `OK` even though unresolved parameters remained.',
            '- **odp_unresolved_detected_rate**: unresolved ODP condition was surfaced either by `PARAMS_REQUIRED` or an explicit ODP list.',
            '- **odp_unresolved_hidden_rate**: unresolved ODP condition was not surfaced.',
            '- **compliancegpt_strict_win_rate**: generative baseline failed strict validity while ComplianceGPT passed.',
            '- **generative_false_complete_vs_compliancegpt_safe_warning_rate**: baseline said `OK` while ComplianceGPT correctly said `PARAMS_REQUIRED`.',
            '',
            '## System-level comparison',
            '',
            system_table.to_markdown(index=False),
            '',
            '## Head-to-head failure rates',
            '',
            head_to_head.to_markdown(index=False),
            '',
            '## Baseline status vs ComplianceGPT status',
            '',
            status_matrix.to_markdown(index=False) if not status_matrix.empty else '(No overlapping rows.)',
            '',
            '## Failure examples',
            '',
            examples.to_markdown(index=False) if not examples.empty else '(No failure examples selected.)',
            '',
        ]
        (outdir / f'{framework_version}_answerer_comparison_{stamp}.md').write_text('\n'.join(lines), encoding='utf-8')
    return outputs
