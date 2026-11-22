# Contributing to Signa

Signa is an experimental English audio/video-to-avatar research prototype. Start with [README.md](README.md) for the current neural pipeline and [docs/VALIDATION.md](docs/VALIDATION.md) for dated engineering observations. ASL meaning and understandability have not yet been validated with sign-language experts or Deaf users. Successful software tests do not establish translation quality.

## Useful contributions

- Reproducible bug reports for setup, media playback, cancellation, and WebM export.
- Clearer installation instructions and English/Uzbek documentation.
- Focused regression tests for timing, avatar motion, and API behavior.
- Performance measurements that include hardware, software versions, input duration, and cold/warm startup conditions.
- Proposals for evaluation with ASL experts and Deaf users, clearly distinguished from completed evaluations.

## Before changing code

Read the relevant implementation and existing tests. For a larger change, open an issue describing the problem and intended behavior before starting. Keep each pull request focused, work on a separate branch, and preserve existing user media and data. Avoid unrelated refactors, generated assets, dependency upgrades, or formatting changes.

The current README describes the neural pipeline; older sections of research and validation documents may describe historical dictionary-based behavior. If documentation conflicts, report the exact sections and distinguish current implementation from historical results rather than treating planned work as completed.

## Development setup

Follow the Windows setup in [README.md](README.md). The documented main environment uses Node.js 22+ and Python 3.12; tests that directly read TypeScript source were run with Node.js 24. The neural model uses a separate Python 3.11 environment and additional model downloads. Review setup scripts and upstream model terms before downloading dependencies.

Run commands from the repository root after setting up dependencies:

```powershell
npm.cmd test
npm.cmd run build
```

For playback changes:

```powershell
node scripts/test-playback.mjs
node scripts/test-playback-media.mjs
```

For avatar or neural motion changes:

```powershell
node scripts/test-avatar.mjs
node scripts/test-interpreter.mjs
node scripts/test-framing.mjs
node scripts/test-neural-motion.mjs
```

For export changes:

```powershell
node scripts/test-composite-export.mjs
```

Run checks relevant to the changed behavior. For documentation-only changes, verify commands, paths, and links against the repository; model downloads and runtime tests are unnecessary unless the documentation change depends on a new runtime claim. Report any check you could not run and why. Do not present historical test results as a new run.

For changes affecting playback or export, also follow the applicable manual steps in [docs/UI_REDESIGN.md](docs/UI_REDESIGN.md). Mock tests do not replace a real browser export check.

## Reporting a bug

Include:

1. Commit or branch, operating system, browser, Node.js and Python versions.
2. Exact steps and command used, expected behavior, and actual behavior.
3. Relevant error output with credentials and personal information removed.
4. For media issues: format, duration, size, and whether the issue reproduces with a bundled example.
5. For model issues: model configuration, CPU/GPU, processing time, and whether the model was already loaded.

Prefer a small synthetic or redistributable reproduction. Do not attach private recordings, personal transcripts, access tokens, local databases, or model weights to public issues.

## Pull request checklist

- Explain the concrete problem and resulting behavior.
- Link the related issue, if one exists.
- Include a focused regression test for a behavioral fix when practical.
- List checks actually performed, their results, and any remaining manual verification.
- Update documentation when behavior or setup requirements change.
- Preserve the distinction between engineering correctness and ASL linguistic evaluation.
- Identify the source and applicable permissions for any added code, data, or assets.

## Licensing and research assets

Public visibility is not a blanket permission to reuse every component. This guide does not grant a license or change existing terms. Check the applicable permissions before redistributing code or assets; ask the maintainer if the project's own code license is unclear. The README documents separate terms for upstream models and avatar assets. Do not bundle downloaded model weights or replace upstream notices.

## Evaluation evidence

Use [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) as a planning reference, with its historical limitations in mind. Record the tested commit, inputs, procedure, environment, and limitations for each new result. Synthetic fixtures, avatar rendering, or passing unit tests must not be described as expert ASL approval or evidence of real-world accessibility impact.
