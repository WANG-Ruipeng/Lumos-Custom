# UniLumos BSS Official-Protocol Smoke

This folder contains the local code-only scaffold for a UniLumos Boundary-Split
Sampling (BSS) smoke experiment.

The intended execution target is Google Colab with model weights stored on
Google Drive. Local work in this branch is limited to code, manifests,
schedule validation, metrics utilities, reports, and the Colab notebook.

Strict scope:

- Do not train.
- Do not modify model weights.
- Do not modify UniLumos conditioning, prompt processing, checkpoint loading,
  resolution, VAE, dataset preprocessing, or architecture.
- Preserve the official uniform schedule path.
- Add only inference-time schedule controls and experiment utilities.

Primary smoke:

- `uniform8`
- `uniform10`
- `bss10 = base8 + split first/last`
- `reference = uniform25`

The high-step/default reference is an evaluation reference, not ground truth.
The first result should be described as cross-model smoke evidence, not a
generality claim.
