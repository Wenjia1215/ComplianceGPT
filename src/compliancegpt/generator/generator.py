# -*- coding: utf-8 -*-
"""
generator.py — ComplianceGPT Answerer v0 (Defense Grade) — Generator v3.4 (Option A-ready)

This generator implements the **Selector Contract** (provably extractive mode):

- The LLM selects ONLY evidence IDs (`source_id`).
- The generator MUST NOT write an answer or copy evidence text.
- The pipeline deterministically fills verbatim `span_text` from the canonical CCS
  and constructs final `answer_text`, applies ODP policy, and sets final `status`.

Key contract reference: citation_contract_80053.md

Public API:
- ComplianceGenerator
- load_org_profile
- normalize_contract

Option A alignment:
- Generator sets PARAMS_REQUIRED if selected evidence contains ODP placeholders
  ({{ insert: param, <token> }}). The pipeline may override status after applying
  resolution_policy (ASK / FILL_FROM_PROFILE / PRESERVE).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from transformers import GenerationConfig


# -----------------------------
# Org profile loader
# -----------------------------
def load_org_profile(filepath: str) -> Dict[str, Any]:
    """
    Loads org_profile YAML.

    Supports either:
      - flat mapping: { "<odp_id>": "<value>", ... }
      - nested: { "odp_values": { "<odp_id>": "<value>", ... }, ... }
    """
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
    Ensures the selector contract always has:
      - answer_text: str (must be "")
      - evidence_spans: List[{source_id:str, span_text:str}]  (span_text must be "")
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
                sid = str(span.get("source_id", "")).strip()
                spans_out.append({"source_id": sid, "span_text": ""})
            elif isinstance(span, str):
                sid = span.strip()
                if sid:
                    spans_out.append({"source_id": sid, "span_text": ""})

    contract["evidence_spans"] = spans_out

    status = str(raw.get("status", "OK")).strip().upper()
    contract["status"] = status if status in ALLOWED_STATUS else "ERROR"

    odp_in = raw.get("odp_required_list", [])
    odp_out: List[str] = []
    if isinstance(odp_in, list):
        odp_out = [str(x).strip() for x in odp_in if str(x).strip()]
    elif isinstance(odp_in, str):
        # allow comma/newline separated
        parts: List[str] = []
        for line in odp_in.replace("\r\n", "\n").split("\n"):
            parts.extend([p.strip() for p in line.split(",")])
        odp_out = [p for p in parts if p]
    contract["odp_required_list"] = odp_out

    return contract


# -----------------------------
# ODP extraction (curly placeholder IDs only)
# -----------------------------
# Canonical placeholder: {{ insert: param, <token> }}
_ODP_CURLY_RE = re.compile(
    r"\{\{\s*insert\s*:\s*param\s*,\s*([^\s}]+)\s*\}\}",
    re.IGNORECASE,
)


def _extract_odp_ids(text: str) -> List[str]:
    """
    Extract unique ODP/PRM tokens from canonical curly placeholders.
    Returns stable, first-seen order.
    """
    if not text:
        return []
    out: List[str] = []
    seen = set()
    for m in _ODP_CURLY_RE.finditer(text):
        tok = (m.group(1) or "").strip()
        if not tok:
            continue
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tok)
    return out


# -----------------------------
# Prompt template
# -----------------------------
def _load_contract_snippet() -> str:
    """
    Best-effort: embed the project's contract text in the prompt (for alignment).
    Falls back to a minimal embedded spec if file not found.
    """
    here = Path(__file__).resolve().parent
    candidates = [
        here / "citation_contract_80053.md",
        here.parent / "citation_contract_80053.md",
        Path.cwd() / "citation_contract_80053.md",
    ]
    for p in candidates:
        if p.exists():
            try:
                txt = p.read_text(encoding="utf-8")
                # Keep only the Selector Contract portion to reduce prompt size.
                m = re.search(r"## 2\.\s*Generator Output.*?(?=## 3\.)", txt, flags=re.DOTALL | re.IGNORECASE)
                if m:
                    return m.group(0).strip()
                return txt.strip()[:4000]
            except Exception:
                break

    return (
        "Selector Contract (summary):\n"
        "- Output a single JSON object only.\n"
        '- answer_text MUST be "".\n'
        "- evidence_spans is a list of {source_id, span_text:\"\"}.\n"
        "- status in {OK, NO_EVIDENCE, PARAMS_REQUIRED, ERROR}.\n"
        "- If selected evidence contains {{ insert: param, <token> }}, set PARAMS_REQUIRED and list tokens.\n"
        "- If no evidence selected: status=NO_EVIDENCE and evidence_spans=[].\n"
    )


SYSTEM_PROMPT_TEMPLATE = r"""
You are ComplianceGPT, a strict compliance evidence selector.

You will be given a set of CONTEXT items. Each item has:
- an ID (source_id), and
- its TEXT.

TASK:
Select the MINIMUM set of source IDs whose TEXT directly answers the QUERY.

IMPORTANT:
- Do NOT paraphrase and do NOT write a new answer.
- Do NOT copy evidence text. span_text MUST be "" for every span.
- Select ONLY from IDs that appear in CONTEXT.

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


# -----------------------------
# Generator (ID selector)
# -----------------------------
class ComplianceGenerator:
    def __init__(self, model, tokenizer, max_new_tokens: int = 512, max_parse_retries: int = 2):
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
            max_new_tokens=self.max_new_tokens,
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
        Returns a Selector Contract dict.
        The pipeline should call normalize_contract() and then deterministically fill span_text.
        """
        # Build context
        ctx_parts: List[str] = []
        allowed_ids: List[str] = []
        for d in docs:
            did = str(d.get("id", "")).strip()
            dtx = str(d.get("text", "")).strip()
            if did:
                allowed_ids.append(did)
                ctx_parts.append(f"ID: {did}\nTEXT: {dtx}")
        context_str = "\n\n".join(ctx_parts)

        contract_snippet = _load_contract_snippet()

        prompt = (
            f"{SYSTEM_PROMPT_TEMPLATE}\n\n"
            f"---\nPROJECT CONTRACT SNIPPET (for alignment):\n{contract_snippet}\n---\n\n"
            f"### CONTEXT\n{context_str}\n\n"
            f"### QUERY\n{query}\n"
        )

        messages = [
            {"role": "system", "content": "JSON-only compliance evidence selector. Output ONLY a JSON object."},
            {"role": "user", "content": prompt},
        ]

        raw_text = self._call_model(messages)
        parsed = self._parse_contract(raw_text)

        if not parsed and self.max_parse_retries > 0:
            for _ in range(self.max_parse_retries):
                messages.append({"role": "assistant", "content": raw_text})
                messages.append({"role": "user", "content": "Error: invalid JSON. Output ONLY the JSON object."})
                raw_text = self._call_model(messages)
                parsed = self._parse_contract(raw_text)
                if parsed:
                    break

        if not parsed:
            # Contract-faithful failure: do NOT fabricate citations on parse failure.
            return {
                "answer_text": "",
                "evidence_spans": [],
                "status": "ERROR",
                "odp_required_list": [],
                "raw_output": raw_text,
            }

        contract = normalize_contract(parsed)

        # Enforce provably-extractive selector mode
        contract["answer_text"] = ""
        for s in contract.get("evidence_spans", []):
            if isinstance(s, dict):
                s["span_text"] = ""

        # Filter unknown IDs (must be selected from provided CONTEXT)
        allowed = set(i.strip() for i in allowed_ids if i.strip())
        filtered_spans: List[Dict[str, str]] = []
        for s in contract.get("evidence_spans", []):
            sid = str(s.get("source_id", "")).strip()
            if sid and sid in allowed:
                filtered_spans.append({"source_id": sid, "span_text": ""})
        contract["evidence_spans"] = filtered_spans

        # If model tried to return ERROR, honor it but keep selector-safe structure
        status_in = str(contract.get("status", "OK")).strip().upper()
        if status_in == "ERROR":
            contract["evidence_spans"] = []
            contract["odp_required_list"] = []
            contract["raw_output"] = raw_text
            return contract

        # Coerce status based on selection + ODPs from selected TEXT
        if not contract.get("evidence_spans"):
            contract["status"] = "NO_EVIDENCE"
            contract["odp_required_list"] = []
        else:
            text_by_id = {str(d.get("id", "")).strip(): str(d.get("text", "")).strip() for d in docs if str(d.get("id", "")).strip()}
            selected_ids = [str(s.get("source_id", "")).strip() for s in contract.get("evidence_spans", []) if str(s.get("source_id", "")).strip()]

            odp_ids: List[str] = []
            for sid in selected_ids:
                odp_ids.extend(_extract_odp_ids(text_by_id.get(sid, "")))

            # Stable de-dup
            seen = set()
            odp_ids_unique: List[str] = []
            for x in odp_ids:
                k = x.lower()
                if k in seen:
                    continue
                seen.add(k)
                odp_ids_unique.append(x)

            if odp_ids_unique:
                contract["status"] = "PARAMS_REQUIRED"
                contract["odp_required_list"] = odp_ids_unique
            else:
                contract["status"] = "OK"
                contract["odp_required_list"] = []

        contract["raw_output"] = raw_text
        return contract

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        import torch  # local import (avoid hard dependency for static analysis)

        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt", return_attention_mask=True).to(self.model.device)
        with torch.inference_mode():
            gen = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                generation_config=self._deterministic_cfg,
            )
        return self.tokenizer.decode(gen[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)


# End of generator.py
