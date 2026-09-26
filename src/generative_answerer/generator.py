# -*- coding: utf-8 -*-
"""
Baseline generative answerer for RQ2.

Design goal:
- Reuse the same retrieved evidence window as ComplianceGPT.
- Let the LLM write the final answer in free form.
- Still require machine-parseable source-id citations so the result can be audited.

This is intentionally not deterministic assembly. It is the comparison system for RQ2.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

try:
    from transformers import GenerationConfig
except ImportError:  # Allow dependency-light imports for utility/unit tests.
    GenerationConfig = None  # type: ignore[assignment]


ALLOWED_STATUS = {"OK", "NO_EVIDENCE", "PARAMS_REQUIRED", "ERROR"}


def _as_list_of_strings(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    if isinstance(value, str):
        parts: List[str] = []
        for chunk in value.replace("\r\n", "\n").split("\n"):
            parts.extend([p.strip() for p in chunk.split(",")])
        return [p for p in parts if p]
    s = str(value).strip()
    return [s] if s else []


def build_system_prompt() -> str:
    return (
        "Role: compliance QA assistant for NIST SP 800-53.\n\n"
        "You will be given a query and a retrieved evidence set.\n"
        "Answer ONLY from the provided evidence. Do not use outside knowledge.\n\n"
        "Output exactly one JSON object with these keys:\n"
        "- status: one of OK, NO_EVIDENCE, PARAMS_REQUIRED, ERROR\n"
        "- answer_text: a concise free-form answer grounded only in the evidence\n"
        "- cited_source_ids: list of source_id values taken only from the provided context\n"
        "- odp_required_list: list of required ODP/parameter ids if unresolved, else []\n\n"
        "Rules:\n"
        "1) Use ONLY evidence in the provided context. Never use outside knowledge.\n"
        "2) Every material claim in answer_text must be supported by cited_source_ids.\n"
        "3) If the evidence is insufficient for a grounded answer, return status=NO_EVIDENCE, answer_text='', cited_source_ids=[], odp_required_list=[].\n"
        "4) If the answer depends on unresolved organization-defined parameters, return status=PARAMS_REQUIRED and include the unresolved parameter ids in odp_required_list.\n"
        "5) Never invent a source_id. Only cite ids that appear in the context.\n"
        "6) If you cannot satisfy these rules, return status=ERROR with answer_text='' and empty lists.\n"
        "7) Output JSON only. No markdown fences. No prose before or after the JSON.\n"
    )


class BaselineGenerativeAnswerer:
    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        max_new_tokens: int = 640,
        max_parse_retries: int = 2,
    ) -> None:
        if GenerationConfig is None:
            raise ImportError(
                "BaselineGenerativeAnswerer requires the optional 'transformers' dependency."
            )
        self.model = model
        self.tokenizer = tokenizer
        self.max_new_tokens = int(max_new_tokens)
        self.max_parse_retries = int(max_parse_retries)
        self.system_prompt = build_system_prompt()

        pad_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id
        self._deterministic_cfg = GenerationConfig(
            do_sample=False,
            num_beams=1,
            repetition_penalty=1.05,
            max_new_tokens=self.max_new_tokens,
            pad_token_id=pad_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )

    def _parse_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

        starts = [i for i, ch in enumerate(cleaned) if ch == "{"][:50]
        for start in starts:
            depth = 0
            in_str = False
            escaped = False
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
                        candidate = cleaned[start : i + 1]
                        try:
                            obj = json.loads(candidate)
                            return obj if isinstance(obj, dict) else None
                        except Exception:
                            break
        return None

    def _normalize_output(self, raw: Dict[str, Any], docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        valid_ids = {
            str(d.get("id", "")).strip()
            for d in docs
            if str(d.get("id", "")).strip()
        }

        status = str(raw.get("status", "ERROR") or "ERROR").strip().upper()
        if status not in ALLOWED_STATUS:
            status = "ERROR"

        answer_text = str(raw.get("answer_text", "") or "").strip()

        cited_source_ids: List[str] = []
        seen_ids = set()
        for sid in _as_list_of_strings(raw.get("cited_source_ids", [])):
            if sid in valid_ids and sid not in seen_ids:
                seen_ids.add(sid)
                cited_source_ids.append(sid)

        odp_required_list: List[str] = []
        seen_odp = set()
        for pid in _as_list_of_strings(raw.get("odp_required_list", [])):
            key = pid.lower()
            if key and key not in seen_odp:
                seen_odp.add(key)
                odp_required_list.append(pid)

        # Fail-closed normalization for semantic consistency.
        if status == "NO_EVIDENCE":
            answer_text = ""
            cited_source_ids = []
            odp_required_list = []
        elif status == "PARAMS_REQUIRED":
            if not odp_required_list:
                status = "ERROR"
                answer_text = ""
                cited_source_ids = []
                odp_required_list = []
        elif status == "OK":
            if not answer_text or not cited_source_ids:
                status = "ERROR"
                answer_text = ""
                cited_source_ids = []
                odp_required_list = []
        else:  # ERROR
            answer_text = ""
            cited_source_ids = []
            odp_required_list = []

        return {
            "status": status,
            "answer_text": answer_text,
            "cited_source_ids": cited_source_ids,
            "odp_required_list": odp_required_list,
        }

    def generate(self, query: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        ctx_parts: List[str] = []
        for d in docs:
            did = str(d.get("id", "")).strip()
            dtx = str(d.get("text", "")).strip()
            if did and dtx:
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
        parsed = self._parse_json_object(raw_text)

        if not parsed and self.max_parse_retries > 0:
            for _ in range(self.max_parse_retries):
                messages.append({"role": "assistant", "content": raw_text})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Invalid output. Return ONLY one JSON object with keys: "
                            "status, answer_text, cited_source_ids, odp_required_list. "
                            "If evidence is insufficient use NO_EVIDENCE. If unresolved ODPs are required use PARAMS_REQUIRED with odp_required_list."
                        ),
                    }
                )
                raw_text = self._call_model(messages)
                parsed = self._parse_json_object(raw_text)
                if parsed:
                    break

        if not parsed:
            return {
                "status": "ERROR",
                "answer_text": "",
                "cited_source_ids": [],
                "odp_required_list": [],
                "raw_output": raw_text,
            }

        out = self._normalize_output(parsed, docs)
        out["raw_output"] = raw_text
        return out

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        import torch

        chat = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(chat, return_tensors="pt", return_attention_mask=True).to(self.model.device)

        with torch.inference_mode():
            gen = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                generation_config=self._deterministic_cfg,
            )

        new_tokens = gen[0][inputs["input_ids"].shape[1] :]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
