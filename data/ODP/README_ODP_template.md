# ComplianceGPT: Organization Profile & ODP Template Files

**Date:** November 18, 2025  
**Scope:** `answerer_v0/generator/ODP/`  

---

## 1. What are these files?

Compliance regulations (such as NIST SP 800-53) are not “one size fits all.”  
They contain **blanks** that each organization must fill in according to its own risk tolerance. NIST calls these blanks **Organization-Defined Parameters (ODPs)**.

- The regulation says:  
  > “Accounts must be disabled after **[Assignment: organization-defined time period]** of inactivity.”

- The organization decides:  
  > “We choose **35 days**.”

This folder contains the **templates and profiles** that manage those blanks for ComplianceGPT. The engine reads these files and either:

- fills in the blanks automatically when values are present, or  
- stops and asks for missing values when they are not.

:contentReference[oaicite:0]{index=0}

---

## 2. “Rev 4” vs “Rev 5” (Why we need two sets)

NIST changed its control set and ODP naming scheme between:

- **Revision 4 (2013)** and  
- **Revision 5 (2020)**.

The ODP identifiers are different:

- **Rev 4 style:** keys like `ac-2_prm_3`  
- **Rev 5 style:** keys like `ac-02_odp.05`

Because these keys do not match, we **cannot share profiles between revisions**:

- Rev 4 questions must use a **Rev 4 profile**.
- Rev 5 questions must use a **Rev 5 profile**.

To keep this separation explicit, we maintain two subfolders:

- `ODP/rev4/` → legacy audits and Rev 4 experiments  
- `ODP/rev5/` → modern audits and Rev 5 experiments (default)

If you mix a Rev 4 question with a Rev 5 profile (or vice versa), the engine will look for keys that do not exist and treat them as missing parameters.

:contentReference[oaicite:1]{index=1}

---

## 3. File Inventory & Purpose

All ODP-related files live under `answerer_v0/generator/ODP/`.

Below is the structure for **Rev 5** (Rev 4 mirrors the same pattern with Rev 4–style keys):

| File Name                        | Purpose                                        | Technical Role                                                 |
|----------------------------------|-----------------------------------------------|----------------------------------------------------------------|
| `odp_registry_rev5.csv`          | Master list of all Rev 5 ODP “blanks”.        | Drives analysis and can be used to auto-generate UI forms.     |
| `org_profile_blank_rev5.yaml`    | Empty organization profile template.          | Given to new users to fill in; used as a starting point.       |
| `org_profile_example_rev5.yaml`  | Example filled-out profile for testing.       | Used in unit tests (e.g., “90 days” for `ac-02_odp.05`).       |

The Rev 4 directory (`ODP/rev4/`) contains the same kinds of files, but with Rev 4–style identifiers such as `ac-2_prm_3`.

odp_registry_rev5/4.csv is generated from the NIST SP 800-53 Rev 5/4 source (NIST_SP-800-53_rev5/4_catalog.jsonl) by a separate preprocessing script in the ComplianceGPT data pipeline.

---

## 4. How the Engine Uses These Files

The Generator treats the organization profile as a **state object** that can be updated by a future UI or API. The high-level workflow is:

1. **User asks a question**  
   Example:  
   > “How often do we review accounts?”

2. **Retriever fetches the relevant control**  
   Example context snippet:  
   > “The organization reviews accounts `{{ insert: ac-02_odp.05 }}`.”

3. **Generator checks the loaded profile**  

   - **Scenario A – Value present**  
     - The profile YAML (e.g., `org_profile_example_rev5.yaml`) defines  
       `ac-02_odp.05: "90 days"`.  
     - The engine substitutes this value into `answer_text` and returns:  
       > “The organization reviews accounts every **90 days**.”  
     - `status` is set to `"OK"`, and `odp_required_list` is empty.

   - **Scenario B – Value missing**  
     - The profile does not define `ac-02_odp.05`.  
     - The engine does **not** guess a value.  
     - It returns:  
       - `status: "PARAMS_REQUIRED"`  
       - `odp_required_list: ["ac-02_odp.05"]`  
     - A UI can then ask the user:  
       > “Please define the frequency for Account Reviews.”

4. **Future UI or API**  
   - When the user supplies a value (e.g., `"90 days"`), the UI updates the YAML-backed profile.
   - On the next run, the same question will follow Scenario A and produce a complete answer.

:contentReference[oaicite:3]{index=3}

---

## 5. Why YAML and CSV?

For Phase 1 and Phase 2 experiments, we use static YAML and CSV files for three reasons:

1. **Reproducibility**  
   - Every experiment can be rerun with the exact same ODP configuration.

2. **Automation**  
   - Evaluation scripts can load the same profile and automatically check whether answers correctly apply or request ODP values.

3. **Future UI Integration**  
   - In a production system, these files can be replaced (or backed) by a database or configuration service.
   - The YAML shape is deliberately simple so it can be edited by humans, generated by scripts, or synchronized with a UI.

---

## 6. Summary

- The `ODP/` folder defines the **configuration surface** for all NIST ODPs used by ComplianceGPT.  
- The **registry** files enumerate what needs to be configured.  
- The **profile** files store an organization’s chosen values.  
- The Generator consumes these profiles to decide when to:

  - fill in parameters directly (FILL_FROM_PROFILE), or  
  - stop and request missing values (PARAMS_REQUIRED).

Together, these templates are the bridge between abstract NIST controls and concrete, organization-specific policies.
