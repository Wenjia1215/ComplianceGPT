# -*- coding: utf-8 -*-
"""
generator.py — ComplianceGPT Answerer v0 (Defense Grade) — Generator v3.3

This generator is designed to be CONSISTENT with the pipeline's "provably extractive" mode:

- The model is asked to SELECT evidence IDs (source_id) only.
- The pipeline deterministically fills span_text from the canonical corpus (retriever docs_map).
- The pipeline deterministically computes final answer_text, ODP/status behavior, and verification.

Why:
- Prevents hallucinated "verbatim" spans.
- Makes evaluation and auditing deterministic and reproducible.

Compatibility:
- Exposes: ComplianceGenerator, load_org_profile, normalize_contract
- Keeps apply_odp_logic available (fixed), but generator.generate() does NOT substitute ODPs by default.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# transformers is imported lazily in pipeline; keep imports local-safe here too
from transformers import GenerationConfig


# -----------------------------
# Org profile loader
# -----------------------------
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


# -----------------------------
# Contract normalization
# -----------------------------
ALLOWED_STATUS = {"OK", "NO_EVIDENCE", "PARAMS_REQUIRED", "ERROR"}


def normalize_contract(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures the contract always has:
      - answer_text: str
      - evidence_spans: List[{source_id:str, span_text:str}]
      - status: str in {OK, NO_EVIDENCE, PARAMS_REQUIRED, ERROR}
      - odp_required_list: List[str]
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
        # allow comma/newline separated
        parts = []
        for chunk in odp_in.replace("\r\n", "\n").split("\n"):
            parts.extend([p.strip() for p in chunk.split(",")])
        odp_out = [p for p in parts if p]
    contract["odp_required_list"] = odp_out

    return contract


# -----------------------------
# ODP helpers (kept for compatibility; pipeline is the source of truth)
# -----------------------------
# Supports both:
#  - {{ insert: param, ac-02_odp.05 }}
#  - [assignment: organization-defined ...]   (no ID; will not yield an ID)
ODP_PATTERN = re.compile(
    r"(?:\{+\s*insert:\s*(?:param,\s*)?([^}]+?)\s*\}+|\[assignment:\s*([^\]]+?)\s*\])",
    re.IGNORECASE,
)

def _has_value(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return True  # False is a value for some params
    if isinstance(val, (int, float)):
        return True  # 0 is a value
    s = str(val).strip()
    return bool(s)

def _extract_keys(text: str) -> List[str]:
    """
    Extract ODP IDs from {{insert}} placeholders.

    IMPORTANT FIX:
      For "{{ insert: param, ac-02_odp.05 }}", the ID is the LAST comma-separated token.
      (Earlier bug extracted "param".)
    """
    if not text:
        return []
    matches = ODP_PATTERN.findall(text)
    keys: List[str] = []
    for a, b in matches:
        raw = (a or b).strip()
        if not raw:
            continue
        # Only brace style reliably encodes an ID; assignment style is free-text.
        # Still, for brace style, take last token after comma.
        base = raw.split(",")[-1].strip()
        if base:
            keys.append(base)
    # de-dup while preserving order
    out: List[str] = []
    seen = set()
    for k in keys:
        lk = k.lower()
        if lk not in seen:
            seen.add(lk)
            out.append(k)
    return out

def _profile_lookup(profile: Dict[str, Any], key: str) -> Any:
    """
    Support either:
      - flat mapping: { "ac-02_odp.05": "90 days" }
      - nested: { "odp_values": { ... } }
    """
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
    Compatibility helper.
    NOTE: In the upgraded pipeline, ODP policy + final substitution is handled in pipeline.py.
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

    # Respect status precedence
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


# -----------------------------
# Generator (ID selector)
# -----------------------------
SYSTEM_PROMPT_TEMPLATE = r"""
You are ComplianceGPT, a strict compliance evidence selector.

You will be given a set of CONTEXT items. Each item has:
- an ID (source_id), and
- its TEXT.

TASK:
Select the MINIMUM set of source IDs whose TEXT directly answers the QUERY.

IMPORTANT:
- Do NOT paraphrase and do NOT write a new answer.
- Do NOT copy evidence text. Set span_text to an empty string for every span.
- The pipeline will fill span_text deterministically from the canonical corpus.

OUTPUT FORMAT (JSON only):
{
  "answer_text": "",
  "evidence_spans": [{"source_id": "<ID>", "span_text": ""}, ...],
  "status": "OK" | "NO_EVIDENCE" | "PARAMS_REQUIRED",
  "odp_required_list": ["<odp_id>", ...]
}

ODP RULE:
If any selected TEXT contains placeholders like:
  {{ insert: param, <odp_id> }}
then set status="PARAMS_REQUIRED" and include those <odp_id> values in odp_required_list.
If no such placeholders are present in selected TEXT, set odp_required_list=[].
If none of the CONTEXT items provide evidence, set status="NO_EVIDENCE" and evidence_spans=[].
""".strip()


class ComplianceGenerator:
    def __init__(self, model, tokenizer, max_new_tokens: int = 768, max_parse_retries: int = 2):
        self.model = model
        self.tokenizer = tokenizer
        self.max_new_tokens = max_new_tokens
        self.max_parse_retries = max_parse_retries

        pad_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
        self._deterministic_cfg = GenerationConfig(
            do_sample=False,
            num_beams=1,
            repetition_penalty=1.05,
            pad_token_id=pad_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )

    def _parse_contract(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Robust JSON extractor (brace counting with string awareness).
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
        Returns a contract-like dict.
        The pipeline will call normalize_contract() and then deterministically fill span_text.
        """
        # Build context
        ctx_parts: List[str] = []
        for d in docs:
            did = str(d.get("id", "")).strip()
            dtx = str(d.get("text", "")).strip()
            if did:
                ctx_parts.append(f"ID: {did}\nTEXT: {dtx}")
        context_str = "\n\n".join(ctx_parts)

        prompt = f"{SYSTEM_PROMPT_TEMPLATE}\n\n### CONTEXT\n{context_str}\n\n### QUERY\n{query}\n"

        messages = [
            {"role": "system", "content": "JSON-only compliance evidence selector."},
            {"role": "user", "content": prompt},
        ]

        raw_text = self._call_model(messages)
        parsed = self._parse_contract(raw_text)

        if not parsed and self.max_parse_retries > 0:
            for _ in range(self.max_parse_retries):
                messages.append({"role": "assistant", "content": raw_text})
                messages.append({"role": "user", "content": "Error: Invalid JSON. Output ONLY the JSON object."})
                raw_text = self._call_model(messages)
                parsed = self._parse_contract(raw_text)
                if parsed:
                    break

        if not parsed:
            # Deterministic fallback: cite the top doc if present, else NO_EVIDENCE
            top_id = str(docs[0].get("id", "")).strip() if docs else ""
            if top_id:
                return {
                    "answer_text": "",
                    "evidence_spans": [{"source_id": top_id, "span_text": ""}],
                    "status": "OK",
                    "odp_required_list": [],
                    "raw_output": raw_text,
                }
            return {"status": "ERROR", "answer_text": "JSON Parsing Failed", "evidence_spans": [], "odp_required_list": [], "raw_output": raw_text}

        contract = normalize_contract(parsed)

        # Force "ID-only" behavior: strip any model-provided text to prevent hallucinated spans.
        for s in contract.get("evidence_spans", []):
            if isinstance(s, dict):
                s["span_text"] = ""

        # Ensure status is coherent with selection
        if not contract.get("evidence_spans"):
            contract["status"] = "NO_EVIDENCE"
            contract["odp_required_list"] = []
        else:
            # Compute ODP ids from the ORIGINAL doc texts (not from span_text, which we strip)
            selected_ids = [str(s.get("source_id", "")).strip() for s in contract.get("evidence_spans", []) if str(s.get("source_id", "")).strip()]
            text_by_id = {str(d.get("id", "")).strip(): str(d.get("text", "")).strip() for d in docs if str(d.get("id", "")).strip()}

            odp_ids: List[str] = []
            for sid in selected_ids:
                odp_ids.extend(_extract_keys(text_by_id.get(sid, "")))

            odp_ids = list(dict.fromkeys(odp_ids))  # stable de-dup
            contract["odp_required_list"] = odp_ids

            if odp_ids:
                contract["status"] = "PARAMS_REQUIRED"
            else:
                # keep model choice if it says NO_EVIDENCE, but that would be inconsistent; override to OK
                contract["status"] = "OK"

        contract["answer_text"] = ""  # pipeline builds this from canonical spans
        contract["raw_output"] = raw_text
        return contract

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        import torch  # local import
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt", return_attention_mask=True).to(self.model.device)
        with torch.inference_mode():
            gen = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=self.max_new_tokens,
                generation_config=self._deterministic_cfg,
            )
        return self.tokenizer.decode(gen[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)


# End of generator.py
