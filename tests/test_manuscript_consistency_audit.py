from __future__ import annotations

import copy
import unittest

from tools.audit_manuscript_consistency import (
    as_rank,
    exact_mcnemar,
    semantic_notebook_sha,
    wilson_interval,
)


class ManuscriptConsistencyAuditTests(unittest.TestCase):
    def test_nonpositive_rank_is_missing(self) -> None:
        self.assertIsNone(as_rank("0"))
        self.assertIsNone(as_rank(""))
        self.assertEqual(as_rank("3"), 3)

    def test_exact_mcnemar_matches_registered_examples(self) -> None:
        self.assertEqual(exact_mcnemar(5, 4), 1.0)
        self.assertEqual(exact_mcnemar(3, 2), 1.0)
        self.assertAlmostEqual(exact_mcnemar(8, 3), 0.2265625)

    def test_wilson_interval_matches_frozen_table_basis(self) -> None:
        low, high = wilson_interval(98, 100)
        self.assertAlmostEqual(low, 0.929988209271456)
        self.assertAlmostEqual(high, 0.9944980324498376)

    def test_notebook_semantic_hash_ignores_metadata(self) -> None:
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {"colab": {"name": "example"}},
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('ok')\n"],
                    "execution_count": 1,
                    "outputs": [{"output_type": "stream", "text": ["ok\n"]}],
                    "metadata": {"id": "cell-id", "outputId": "tool-id"},
                }
            ],
        }
        sanitized = copy.deepcopy(notebook)
        sanitized["metadata"] = {}
        sanitized["cells"][0]["metadata"] = {}
        self.assertEqual(
            semantic_notebook_sha(notebook), semantic_notebook_sha(sanitized)
        )

    def test_notebook_semantic_hash_detects_source_change(self) -> None:
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {},
            "cells": [{"cell_type": "code", "source": ["x = 1\n"], "outputs": []}],
        }
        changed = copy.deepcopy(notebook)
        changed["cells"][0]["source"] = ["x = 2\n"]
        self.assertNotEqual(
            semantic_notebook_sha(notebook), semantic_notebook_sha(changed)
        )


if __name__ == "__main__":
    unittest.main()
