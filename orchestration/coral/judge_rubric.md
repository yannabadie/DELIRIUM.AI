# Delirium Core Judge Rubric

Score the candidate codebase against the current DELIRIUM.AI milestone:

1. Behavioral fidelity
   The code and prompts stay aligned with `CDC_COMPORTEMENTAL.md`.
   No assistant-like obedience, no retrospective blame, no S2 leakage, no unsafe crisis tone.

2. Productization quality
   The repo moves toward a local-first, testable Delirium Core vertical slice.
   Favor reliable onboarding, conversation loop integrity, persistence, and operational clarity.

3. Safety and privacy
   Do not weaken danger handling, consent boundaries, or data minimization.
   Raw sensitive artifacts must not be retained casually.

4. Delivery discipline
   The changes should be coherent with the current codebase, not a disconnected rewrite.
   Prefer working software, tests, and docs over speculative architecture.

5. Scope discipline
   Do not drift into OmniArxiv or undocumented future phases unless the current milestone requires it.

Return JSON with:
- `score`: float between 0 and 1
- `summary`: one short paragraph
- `strengths`: array of short strings
- `risks`: array of short strings
