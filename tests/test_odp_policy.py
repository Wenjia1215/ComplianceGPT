import unittest

from compliancegpt.pipeline.odp_policy import (
    ASSIGNMENT_REQUIRED_SENTINEL,
    ODP_POLICY_PATCH_ID,
    ODP_POLICY_VERSION,
    apply_odp_policy_to_answer,
)


class ODPPolicyRegressionTests(unittest.TestCase):
    def test_patch_identity_is_explicit(self):
        self.assertEqual(ODP_POLICY_VERSION, "1.1")
        self.assertEqual(ODP_POLICY_PATCH_ID, "2026-10-03-preserve-status-v1.1")

    def test_preserve_keeps_parameter_placeholder_and_requires_parameters(self):
        text = "Notify within {{ insert: param, ac-02_odp.07 }}."

        actual_text, required, status = apply_odp_policy_to_answer(
            text,
            "PRESERVE",
            {},
        )

        self.assertEqual(actual_text, text)
        self.assertEqual(required, ["ac-02_odp.07"])
        self.assertEqual(status, "PARAMS_REQUIRED")

    def test_preserve_keeps_assignment_marker_and_requires_parameters(self):
        text = "Notify [Assignment: organization-defined personnel]."

        actual_text, required, status = apply_odp_policy_to_answer(
            text,
            "PRESERVE",
            {},
        )

        self.assertEqual(actual_text, text)
        self.assertEqual(required, [ASSIGNMENT_REQUIRED_SENTINEL])
        self.assertEqual(status, "PARAMS_REQUIRED")

    def test_preserve_without_placeholder_is_ok(self):
        text = "No organization-defined value appears here."

        actual_text, required, status = apply_odp_policy_to_answer(
            text,
            "PRESERVE",
            {},
        )

        self.assertEqual(actual_text, text)
        self.assertEqual(required, [])
        self.assertEqual(status, "OK")


if __name__ == "__main__":
    unittest.main()
