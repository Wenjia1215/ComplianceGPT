# -*- coding: utf-8 -*-
"""
compliancegpt/generator/generator.py — ComplianceGPT Answerer v0 — Generator (evidence selector)

Design (provably extractive):
- The LLM performs evidence selection only (returns source_id list).
- The pipeline fills span_text verbatim from the canonical CCS using source_id.
- The verifier checks contract consistency and verbatim grounding.

Exports (used by pipeline):
- ComplianceGenerator
- load_org_profile
- normalize_contract
- apply_odp_logic  (compat helper; pipeline is source of truth for ODP policy)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from transformers import GenerationConfig


# ==========================================================
# 0) Paths
# ==========================================================
_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_CONTRACT_PATH = _THIS_DIR / "citation_contract_80053.md"


# ==========================================================
# 1) Org profile loader
# ==========================================================
def load_org_profile(filepath: str) -> Dict[str, Any]:
    path = Path(filepath)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = yaml.safe_load(f) or {}
        return obj if isinstance(obj, dict) else {}
    except Exception as e:
        print(f"[Generator] Error loading profile: {e}")
        return {}


# ==========================================================
# 2) Contract normalization
# ==========================================================
ALLOWED_STATUS = {"OK", "NO_EVIDENCE", "PARAMS_REQUIRED", "ERROR"}


def normalize_contract(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw dict into the expected contract shape.
    """
    contract: Dict[str, Any] = {}
    contract["answer_text"] = str(raw.get("answer_text", ""))

    spans_in = raw.get("evidence_spans", [])
    spans_out: List[Dict[str, str]] = []
    if isinstance(spans_in, list):
        for span in spans_in:
            if isinstance(span, dict):
                spans_out.append(
                    {
                        "source_id": str(span.get("source_id", "")).strip(),
                        "span_text": str(span.get("span_text", "")),
                    }
                )
    contract["evidence_spans"] = spans_out

    status = str(raw.get("status", "OK")).strip().upper()
    contract["status"] = status if status in ALLOWED_STATUS else "ERROR"

    odp_in = raw.get("odp_required_list", [])
    odp_out: List[str] = []
    if isinstance(odp_in, list):
        odp_out = [str(x).strip() for x in odp_in if str(x).strip()]
    elif isinstance(odp_in, str):
        parts: List[str] = []
        for chunk in odp_in.replace("\r\n", "\n").split("\n"):
            parts.extend([p.strip() for p in chunk.split(",")])
        odp_out = [p for p in parts if p]
    contract["odp_required_list"] = odp_out

    return contract


# ==========================================================
# 3) ODP helpers (compat; pipeline is source of truth)
# ==========================================================
_PARAM_CURLY_RE = re.compile(
    r"\{+\s*insert:\s*(?:param,\s*)?([^}]+?)\s*\}+",
    re.IGNORECASE,
)
_PARAM_ASSIGNMENT_RE = re.compile(
    r"\[assignment:\s*([^\]]+?)\s*\]",
    re.IGNORECASE,
)


def _has_value(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return True
    if isinstance(val, (int, float)):
        return True
    return bool(str(val).strip())


def _extract_keys(text: str) -> List[str]:
    """
    Extract required parameter IDs from curly {{insert}} placeholders.
    If assignment placeholders exist but no curly IDs exist, return sentinel "assignment_required".
    """
    if not text:
        return []

    ids: List[str] = []
    for m in _PARAM_CURLY_RE.finditer(text):
        raw = (m.group(1) or "").strip()
        if not raw:
            continue
        base = raw.split(",")[-1].strip()
        token = base.split()[0].strip() if base else ""
        if not token or token.lower() == "param":
            continue
        ids.append(token)

    has_assignment = bool(_PARAM_ASSIGNMENT_RE.search(text))

    out: List[str] = []
    seen = set()
    for k in ids:
        lk = k.lower()
        if lk in seen:
            continue
        seen.add(lk)
        out.append(k)

    if not out and has_assignment:
        return ["assignment_required"]
    return out


def _profile_lookup(profile: Dict[str, Any], key: str) -> Any:
    if not isinstance(profile, dict):
        return None
    if key in profile:
        return profile.get(key)
    odp_values = profile.get("odp_values")
    if isinstance(odp_values, dict) and key in odp_values:
        return odp_values.get(key)
    return None


def apply_odp_logic(contract: Dict[str, Any], org_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compatibility helper (NOT used for final Answerer v0 behavior by default).
    The pipeline should handle ODP policy and final substitution decisions.
    """
    answer = str(contract.get("answer_text", ""))
    orig_status = str(contract.get("status", "OK")).strip().upper()

    required_keys = set(_extract_keys(answer))
    missing: List[str] = []

    for key in sorted(required_keys):
        val = _profile_lookup(org_profile, key)
        if _has_value(val):
            val_str = str(val)
            rep_braces = r"\{+\s*insert:\s*(?:param,\s*)?" + re.escape(key) + r"\s*\}+"
            rep_assign = r"\[assignment:\s*" + re.escape(key) + r"\s*\]"
            try:
                answer = re.sub(rep_braces, val_str, answer, flags=re.IGNORECASE)
                answer = re.sub(rep_assign, val_str, answer, flags=re.IGNORECASE)
            except re.error:
                pass
        else:
            missing.append(key)

    if orig_status in {"ERROR", "NO_EVIDENCE"}:
        contract["status"] = orig_status
        return contract

    if missing:
        contract["status"] = "PARAMS_REQUIRED"
        contract["odp_required_list"] = missing
        contract["answer_text"] = answer
    else:
        contract["status"] = "OK"
        contract["odp_required_list"] = []
        contract["answer_text"] = answer

    return contract


# ==========================================================
# 4) Prompt builder (loads Selector Contract section)
# ==========================================================
def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_selector_contract(md: str) -> str:
    """
    Keep the prompt compact but faithful:
    extract the section between '## 2.' and '## 3.' if present; otherwise return full md.
    """
    m = re.search(r"^##\s*2\..*?$([\s\S]*?)^##\s*3\.", md, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    return md.strip()


def build_system_prompt(contract_path: Optional[str] = None) -> str:
    p = Path(contract_path) if contract_path else DEFAULT_CONTRACT_PATH
    try:
        md = _read_text(p)
        selector_spec = _extract_selector_contract(md)
    except Exception as e:
        selector_spec = f"[WARN] failed to load citation contract: {e}"

    return (
        "Role: ComplianceGPT (evidence selector for NIST SP 800-53).\n\n"
        "Output: exactly one valid JSON object that follows the Selector Contract.\n"
        "No prose, no paraphrase, no evidence copying.\n"
        "Evidence selection rules:"
        "- Select a minimal but complete set of source_id values that cover the query requirements."
        "- If a requirement is expressed as an enumerated list, include the relevant list items (e.g., *_smt.a, *_smt.b), not just a header line."
        "- Prefer specific subclauses over parent clauses when available, but include the parent clause when it provides necessary context or contains required parameters."
        "- Only clause evidence kinds are eligible: statement (smt) and guidance (gdn)."
        "- Select guidance (gdn) only when it directly clarifies the question or adds required compliance meaning."
        "- Exclude parameter/objective nodes (odp/prm/obj) from evidence selection."
        "- odp_required_list must be an empty list; pipeline derives it deterministically."
        "=== Selector Contract (excerpt) ===\n"
        f"{selector_spec}\n"
        "=== End Selector Contract ===\n"
    )


# ==========================================================
# 5) Generator (ID selector)
# ==========================================================
class ComplianceGenerator:
    def __init__(
        self,
        model,
        tokenizer,
        max_new_tokens: int = 512,
        max_parse_retries: int = 2,
        contract_path: Optional[str] = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.max_new_tokens = max_new_tokens
        self.max_parse_retries = max_parse_retries
        self.system_prompt = build_system_prompt(contract_path)

        pad_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
        self._deterministic_cfg = GenerationConfig(
            do_sample=False,
            num_beams=1,
            repetition_penalty=1.05,
            max_new_tokens=self.max_new_tokens,
            pad_token_id=pad_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )

    def _parse_contract(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract the first valid JSON object from model output (robust to fences and chatter).
        """
        cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

        starts = [i for i, ch in enumerate(cleaned) if ch == "{"][:50]
        for start in starts:
            depth, in_str, escaped = 0, False, False
            for i in range(start, len(cleaned)):
                ch = cleaned[i]
                if in_str:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        cand = cleaned[start : i + 1]
                        try:
                            obj = json.loads(cand)
                            return obj if isinstance(obj, dict) else None
                        except Exception:
                            break
        return None

    def generate(self, query: str, docs: List[Dict[str, Any]], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return the Selector Contract (IDs only). Pipeline fills span_text + answer_text.
        """
        # Build context string
        ctx_parts: List[str] = []
        for d in docs:
            did = str(d.get("id", "")).strip()
            dtx = str(d.get("text", "")).strip()
            if did:
                ctx_parts.append(f"ID: {did}\nTEXT: {dtx}")
        context_str = "\n\n".join(ctx_parts)

        user_prompt = (
            "### CONTEXT\n"
            f"{context_str}\n\n"
            "### QUERY\n"
            f"{query}\n\n"
            "Return ONLY the JSON object.\n"
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_text = self._call_model(messages)
        parsed = self._parse_contract(raw_text)

        if not parsed and self.max_parse_retries > 0:
            for _ in range(self.max_parse_retries):
                messages.append({"role": "assistant", "content": raw_text})
                messages.append({"role": "user", "content": "Invalid JSON. Output ONLY the JSON object (no prose, no markdown)."})
                raw_text = self._call_model(messages)
                parsed = self._parse_contract(raw_text)
                if parsed:
                    break

        if not parsed:
            # IMPORTANT: do not fabricate evidence IDs on parse failure.
            # Let the pipeline decide any controlled fallback behavior.
            return {
                "status": "ERROR",
                "answer_text": "",
                "evidence_spans": [],
                "odp_required_list": [],
                "raw_output": raw_text,
            }

        contract = normalize_contract(parsed)

        # Force ID-only: no copied text
        for s in contract.get("evidence_spans", []):
            if isinstance(s, dict):
                s["span_text"] = ""

        # Status coherence with selection + ODP placeholders from the ORIGINAL doc texts
        if not contract.get("evidence_spans"):
            contract["status"] = "NO_EVIDENCE"
            contract["odp_required_list"] = []
        else:
            selected_ids = [str(s.get("source_id", "")).strip() for s in contract.get("evidence_spans", []) if str(s.get("source_id", "")).strip()]
            text_by_id = {str(d.get("id", "")).strip(): str(d.get("text", "")).strip() for d in docs if str(d.get("id", "")).strip()}

            odp_ids: List[str] = []
            for sid in selected_ids:
                odp_ids.extend(_extract_keys(text_by_id.get(sid, "")))

            odp_ids = list(dict.fromkeys([x for x in odp_ids if x]))  # stable de-dup
            contract["odp_required_list"] = odp_ids
            contract["status"] = "PARAMS_REQUIRED" if odp_ids else "OK"

        contract["answer_text"] = ""  # pipeline builds this
        contract["raw_output"] = raw_text
        return contract

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        import torch  # local import (keeps module import cheap)

        chat = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(chat, return_tensors="pt", return_attention_mask=True).to(self.model.device)

        with torch.inference_mode():
            gen = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                generation_config=self._deterministic_cfg,
            )
        return self.tokenizer.decode(gen[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)


# End of generator.py
