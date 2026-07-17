# -*- coding: utf-8 -*-
"""
Baseline generative RAG pipeline for RQ2.

This pipeline reuses the same retrieval stack as ComplianceGPT but replaces
selector-only deterministic assembly with a free-form generative answerer.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set

from compliancegpt.generator.verifier.verifier import verify_answer
from compliancegpt.pipeline.pipeline import (
    ComplianceGPTPipeline,
    _apply_doc_filter_mode,
    _build_ask_list,
    _build_citation_suffix,
    _canonicalize_param_list,
    _extract_control_hints,
    _filter_docs_to_controls,
    _normalize_resolution_policy,
    _normalize_fw,
    _query_allows_enhancements,
    _verifier_result_to_dict,
    normalize_control_id,
    verify_contract_validity,
    _ASSIGNMENT_REQUIRED_SENTINEL,
)
from compliancegpt.pipeline.evidence_window import (
    assert_same_evidence_window,
    build_evidence_window,
    evidence_window_manifest,
    select_allowed_controls,
)

from .generator import BaselineGenerativeAnswerer


def _wrap_out_generative(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Return shape compatible with ComplianceGPT, but label the mode correctly."""
    c: Dict[str, Any] = dict(contract or {})

    if "selected_source_ids" not in c:
        spans = c.get("evidence_spans", []) or []
        ids: List[str] = []
        for s in spans:
            if isinstance(s, dict):
                sid = str(s.get("source_id", "")).strip()
                if sid:
                    ids.append(sid)
        c["selected_source_ids"] = ids

    ver = c.get("verification", None)
    ver_dict = _verifier_result_to_dict(ver) if ver is not None else None
    if ver is not None:
        c["verification"] = ver_dict

    c["verifier_ran"] = bool(ver is not None)

    verifier_pass = False
    verifier_errors: List[str] = []
    verifier_metrics: Dict[str, float] = {}
    if isinstance(ver_dict, dict):
        if "is_pass" in ver_dict:
            verifier_pass = bool(ver_dict.get("is_pass", False))
        elif "ok" in ver_dict:
            verifier_pass = bool(ver_dict.get("ok", False))
        verifier_errors = list(ver_dict.get("error_tags") or ver_dict.get("errors") or [])
        verifier_metrics = dict(ver_dict.get("metrics") or {})
        if not verifier_errors and ver_dict.get("error"):
            verifier_errors = [f"VerifierException:{str(ver_dict.get('error'))}"]

    c["verifier_pass"] = bool(verifier_pass)
    c["verifier_errors"] = verifier_errors
    if verifier_metrics:
        c["verifier_metrics"] = verifier_metrics

    if "answer_text_with_citation" not in c:
        c["answer_text_with_citation"] = str(c.get("answer_text_with_citations", c.get("answer_text", "")) or "")
    if "answer_text_with_citations" not in c:
        c["answer_text_with_citations"] = str(c.get("answer_text_with_citation", c.get("answer_text", "")) or "")

    c["contract_mode"] = "generative_rag_baseline"

    out: Dict[str, Any] = {"contract": c}
    out.update(c)
    return out


class BaselineGenerativeRAGPipeline(ComplianceGPTPipeline):
    """
    Same retriever/QUR/model family as ComplianceGPT, but the final answer is
    generated in free form from the retrieved evidence.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.generative_answerer = BaselineGenerativeAnswerer(self.model, self.tokenizer)

    def answer(
        self,
        query: str,
        top_k: int = 10,
        rewrites: Any = None,
        gold_row: Optional[Dict[str, Any]] = None,
        use_generator: bool = True,
        run_verify: bool = False,
        doc_filter_mode: Optional[str] = None,
        statement_only_on_param_queries: bool = True,
        prepared_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        del use_generator
        del statement_only_on_param_queries

        q = str(query or "").strip()
        if not q:
            err_contract = {
                "question": "",
                "framework_version": self.framework_version,
                "answer_text": "",
                "answer_text_with_citations": "",
                "evidence_spans": [],
                "status": "ERROR",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "debug": {"error": "empty_query"},
                "contract_mode": "generative_rag_baseline",
            }
            return _wrap_out_generative(err_contract)

        self._assert_ccs_loaded()
        context = dict(prepared_context or {})
        if context:
            context_question = str(context.get("question", "") or "").strip()
            context_revision = str(context.get("framework_version", "") or "").strip().lower()
            if context_question and context_question != q:
                raise ValueError("Prepared RQ2 context question does not match the requested question.")
            if context_revision and _normalize_fw(context_revision) != self.framework_version:
                raise ValueError("Prepared RQ2 context revision does not match the pipeline revision.")
            rewrites_used = self._resolve_rewrites(q, context.get("rewrites", []))
        else:
            rewrites_used = self._resolve_rewrites(q, rewrites)

        def _attach_contract_validity(contract_obj: Dict[str, Any]) -> Dict[str, Any]:
            try:
                vp, verrs = verify_contract_validity(
                    json_output=contract_obj,
                    corpus=self._get_verifier_corpus(),
                    org_profile=self.org_profile,
                    strict_verbatim=bool(self.verify_strict_verbatim),
                )
                contract_obj["validity_check"] = {
                    "is_pass": bool(vp),
                    "errors": list(verrs or []),
                }
            except Exception as e:
                contract_obj["validity_check"] = {
                    "is_pass": False,
                    "errors": [f"ValidityCheckException:{repr(e)}"],
                }
            return contract_obj

        top_k = max(1, int(top_k))
        retrieval_meta: Dict[str, Any] = {}
        retrieved_docs: List[Dict[str, Any]] = []
        try:
            if context:
                retrieved_docs = copy.deepcopy(list(context.get("retrieved_docs", []) or []))
                retrieval_meta = copy.deepcopy(dict(context.get("retrieval_meta", {}) or {}))
            elif hasattr(self.retriever, "retrieve_debug"):
                retrieved_docs, retrieval_meta = self.retriever.retrieve_debug(q, top_k=top_k, rewrites=rewrites_used)
            else:
                retrieved_docs = self.retriever.retrieve(q, top_k=top_k, rewrites=rewrites_used)
                retrieval_meta = dict(getattr(self.retriever, "last_meta", {}) or {})
        except Exception as e:
            err_contract = {
                "question": q,
                "framework_version": self.framework_version,
                "answer_text": "",
                "answer_text_with_citations": "",
                "evidence_spans": [],
                "status": "ERROR",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "debug": {"error": "retrieval_failed", "exception": repr(e)},
                "contract_mode": "generative_rag_baseline",
            }
            return _wrap_out_generative(err_contract)

        if not retrieved_docs:
            no_ev = {
                "question": q,
                "framework_version": self.framework_version,
                "answer_text": "",
                "answer_text_with_citations": "",
                "evidence_spans": [],
                "status": "NO_EVIDENCE",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "debug": {
                    "query_plan": {"original_query": q, "rewrites": rewrites_used},
                    "retrieval_meta": retrieval_meta,
                    "retrieved_docs": 0,
                },
                "contract_mode": "generative_rag_baseline",
            }
            no_ev = _attach_contract_validity(no_ev)
            if bool(run_verify) and gold_row is not None:
                ver = verify_answer(
                    json_output=no_ev,
                    gold_row=gold_row,
                    corpus=self._get_verifier_corpus(),
                    org_profile=self.org_profile,
                    corpus_version=self.framework_version,
                    strict_extras=bool(self.verify_strict_extras),
                    strict_verbatim=bool(self.verify_strict_verbatim),
                    strict_version=bool(self.verify_strict_version),
                )
                no_ev["verification"] = _verifier_result_to_dict(ver)
            return _wrap_out_generative(no_ev)

        try:
            topn = max(1, int(getattr(self, "gen_control_gate_topn", 1)))
        except Exception:
            topn = 1
        try:
            low2 = float(getattr(self, "gen_control_gate_lowconf_top2", 0.08))
            low3 = float(getattr(self, "gen_control_gate_lowconf_top3", 0.04))
            maxn = max(1, int(getattr(self, "gen_control_gate_lowconf_maxn", 3)))
        except Exception:
            low2, low3, maxn = 0.08, 0.04, 3
        controls, primary_control, allowed_controls, widen_tier = select_allowed_controls(
            retrieved_docs=retrieved_docs,
            retrieval_meta=retrieval_meta,
            normalize_control_id=normalize_control_id,
            topn=topn,
            lowconf_top2=low2,
            lowconf_top3=low3,
            lowconf_maxn=maxn,
        )

        doc_filter_mode_used = str(doc_filter_mode if doc_filter_mode is not None else self.doc_filter_mode).strip().lower()
        if not doc_filter_mode_used:
            doc_filter_mode_used = "prefer_smt_keep_params"
        pol_eff = _normalize_resolution_policy(self.resolution_policy)
        if pol_eff in {"ASK", "FILL_FROM_PROFILE"} and doc_filter_mode_used == "all":
            doc_filter_mode_used = "prefer_smt_keep_params"

        try:
            primary_first_min_margin = float(getattr(self, "gen_primary_first_min_margin_ratio", 0.06))
        except Exception:
            primary_first_min_margin = 0.06
        docs_for_gen, window_audit = build_evidence_window(
            retrieved_docs=retrieved_docs,
            retrieval_meta=retrieval_meta,
            allowed_controls=allowed_controls,
            primary_control=primary_control,
            doc_filter_mode=doc_filter_mode_used,
            gen_docs_k=int(getattr(self, "gen_docs_k", 24)),
            filter_docs_to_controls=_filter_docs_to_controls,
            apply_doc_filter_mode=_apply_doc_filter_mode,
            primary_first_min_margin_ratio=primary_first_min_margin,
        )
        if context.get("evidence_window") is not None:
            locked_docs = copy.deepcopy(list(context.get("evidence_window", []) or []))
            locked_manifest = evidence_window_manifest(locked_docs)
            expected_manifest = dict(context.get("evidence_window_manifest", {}) or locked_manifest)
            assert_same_evidence_window(
                window_audit.get("evidence_window", {}),
                locked_manifest,
                expected_manifest,
            )
            docs_for_gen = locked_docs
            window_audit["evidence_window"] = locked_manifest

        raw_answer = self.generative_answerer.generate(q, docs_for_gen)

        cited_ids: List[str] = []
        seen_ids = set()
        for sid in raw_answer.get("cited_source_ids", []):
            s = str(sid).strip()
            if s and s not in seen_ids:
                seen_ids.add(s)
                cited_ids.append(s)

        allow_enh = bool(_query_allows_enhancements(q)) or any("." in c for c in (_extract_control_hints(q) or []))
        if bool(getattr(self, "block_enhancements_by_default", False)) and not allow_enh:
            cited_ids = [cid for cid in cited_ids if "." not in cid.split("_", 1)[0]]

        filled_spans: List[Dict[str, str]] = []
        for sid in cited_ids:
            rec = self.retriever.record_by_id.get(sid)
            if not rec:
                continue
            kind = str(rec.get("kind", "") or "").strip().lower()
            if kind not in {"smt", "gdn"}:
                continue
            txt = str(rec.get("text", "") or "").strip()
            if not txt:
                continue
            filled_spans.append({"source_id": str(rec.get("id", sid)), "span_text": txt})

        self._ensure_param_inventory_loaded()
        param_ids = getattr(self, "_param_ids", set()) or set()
        key_map = getattr(self, "_param_key_map", {}) or {}
        odp_required_raw = raw_answer.get("odp_required_list", []) or []
        odp_final = _canonicalize_param_list(
            raw_list=odp_required_raw,
            param_ids=param_ids,
            key_map=key_map,
            assignment_sentinel=_ASSIGNMENT_REQUIRED_SENTINEL,
        )

        answer_text = str(raw_answer.get("answer_text", "") or "").strip()
        status = str(raw_answer.get("status", "ERROR") or "ERROR").strip().upper()
        if status not in {"OK", "NO_EVIDENCE", "PARAMS_REQUIRED", "ERROR"}:
            status = "ERROR"

        normalization_flags: List[str] = []
        if status == "NO_EVIDENCE":
            answer_text = ""
            filled_spans = []
            odp_final = []
            normalization_flags.append("normalized_no_evidence")
        elif status == "PARAMS_REQUIRED":
            if not odp_final:
                status = "ERROR"
                answer_text = ""
                filled_spans = []
                normalization_flags.append("params_required_without_params")
        elif status == "OK":
            if not answer_text:
                status = "ERROR"
                filled_spans = []
                normalization_flags.append("ok_without_answer_text")
            elif not filled_spans:
                status = "ERROR"
                answer_text = ""
                normalization_flags.append("ok_without_grounded_citations")
        else:
            answer_text = ""
            filled_spans = []
            odp_final = []
            normalization_flags.append("normalized_error")

        ask_list: List[Dict[str, Any]] = []
        if status == "PARAMS_REQUIRED" and pol_eff in {"ASK", "FILL_FROM_PROFILE"}:
            ask_list = _build_ask_list(odp_final, filled_spans, self.odp_registry)

        all_citations = ", ".join([s["source_id"] for s in filled_spans])
        suffix = _build_citation_suffix(self.framework_version)
        if status == "OK" and all_citations and answer_text:
            answer_text_with_citations = f"{answer_text}\n\nCitations: {all_citations} ({suffix})".strip()
        elif status == "PARAMS_REQUIRED" and all_citations and answer_text:
            answer_text_with_citations = f"{answer_text}\n\nCitations: {all_citations} ({suffix})".strip()
        elif all_citations and not answer_text:
            answer_text_with_citations = f"Citations: {all_citations} ({suffix})"
        else:
            answer_text_with_citations = answer_text

        primary_citation = filled_spans[0]["source_id"] if filled_spans else ""

        final_contract = {
            "question": q,
            "framework_version": self.framework_version,
            "answer_text": answer_text,
            "answer_text_with_citations": answer_text_with_citations,
            "evidence_spans": filled_spans,
            "status": status,
            "odp_required_list": odp_final,
            "ask_list": ask_list,
            "primary_citation": primary_citation,
            "all_citations": all_citations,
            "contract_mode": "generative_rag_baseline",
            "debug": {
                "query_plan": {"original_query": q, "rewrites": rewrites_used},
                "retrieval_meta": retrieval_meta,
                "allowed_controls": allowed_controls,
                "control_widen_tier": widen_tier,
                "primary_control": primary_control,
                "doc_filter_mode_used": doc_filter_mode_used,
                "primary_first_applied": bool(window_audit.get("primary_first_applied", False)),
                "evidence_window": window_audit.get("evidence_window", {}),
                "prepared_context_sha256": str(context.get("context_sha256", "") or ""),
                "counts": {
                    "retrieved_docs": int(len(retrieved_docs)),
                    "docs_for_gen": int(len(docs_for_gen)),
                    "evidence_spans": int(len(filled_spans)),
                },
                "status_normalization_flags": normalization_flags,
                "generative_raw": raw_answer,
            },
        }

        final_contract = _attach_contract_validity(final_contract)

        if bool(run_verify) and gold_row is not None:
            ver = verify_answer(
                json_output=final_contract,
                gold_row=gold_row,
                corpus=self._get_verifier_corpus(),
                org_profile=self.org_profile,
                corpus_version=self.framework_version,
                strict_extras=bool(self.verify_strict_extras),
                strict_verbatim=bool(self.verify_strict_verbatim),
                strict_version=bool(self.verify_strict_version),
            )
            final_contract["verification"] = _verifier_result_to_dict(ver)

        return _wrap_out_generative(final_contract)
