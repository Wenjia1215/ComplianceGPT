Entrypoints (Colab)

1) Single_Run_Demo.ipynb
   Runs a single freeform query end-to-end and prints a demo-safe view of the Final Answer Contract.
   (No gold-set dependencies, no QUR, no verifier.)

2) Single_Run_Dev.ipynb
   Developer notebook for debugging: supports freeform vs gold queries, optional QUR, and optional verifier
   (verifier runs only when gold labels are present).

3) Single_Run_Verify_Gold.ipynb
   Evaluation notebook: runs a single gold-set query with verifier enabled to validate contract and citation invariants.
