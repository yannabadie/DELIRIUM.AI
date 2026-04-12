# Coral Orchestration for DELIRIUM.AI

This branch does not claim DELIRIUM.AI is already a finished product.
It adds the execution substrate to let Coral iterate on the repo toward a concrete milestone: `Delirium Core`.

## Design choices

- Keep upstream Coral unchanged.
- Materialize a private Coral runtime outside the repository before launch.
- Expose only `product/` to Coral agents.
- Keep grader assets private under Coral's hidden eval directory.
- Force Codex agents to `gpt-5.4` with `xhigh` reasoning through Coral config.

## Files

- `materialize_task.py`: builds `~/.local/share/delirium-coral/delirium-coral/`
- `task.template.yaml`: reference Coral task config
- `eval/grader.py`: deterministic pytest gate + optional Codex judge
- `eval/judge.py`: canonical source loader and prompt builder
- `scripts/bootstrap_coral_ubuntu.sh`: installs Coral prerequisites in `coral-ubuntu`
- `scripts/run_delirium_coral.sh`: materializes and launches the task in WSL
- `scripts/run_delirium_coral.ps1`: Windows entrypoint into `coral-ubuntu`

## Expected prerequisites

- WSL2 distro named `coral-ubuntu`
- `OPENAI_API_KEY` available in that distro for Codex
- `MINIMAX_API_KEY` available if you want live behavior tests to execute instead of skip
- `codex` CLI already installed and authenticated in that distro

## Launch

Inside `coral-ubuntu`:

```bash
bash orchestration/coral/scripts/bootstrap_coral_ubuntu.sh
bash orchestration/coral/scripts/run_delirium_coral.sh
```

From Windows PowerShell:

```powershell
powershell -File orchestration/coral/scripts/run_delirium_coral.ps1
```

## Judge intent

The grader optimizes for the repo's current realistic milestone:

- a local-first Delirium Core
- behavioral fidelity to `CDC_COMPORTEMENTAL.md`
- safe and privacy-bounded progression
- no drift toward OmniArxiv phase-6 scope
