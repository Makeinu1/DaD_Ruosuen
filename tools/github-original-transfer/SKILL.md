# github-binary-artifact-transfer (Python executable edition)

## Trigger
Use this skill when original PNG/JPEG/WebP/GIF/media/PDF files need to be batch-transferred without changing source bytes into a GitHub feature branch, independently verified, and prepared for human PR review.

## Workflow
1. Consult the project's `AGENTS.md`, `README.md`, privacy restrictions, branch convention, review/approval state, and current open PR. Obtain source files as actual local bytes (not an image ID or expired URI).
2. Run `python3 github_originals.py plan --source ... --destination ...` and confirm file count, SHA-256 and optional source manifest. For archive inputs, enforce manifest entries and reject symlinks/path traversal.
3. Run `python3 github_originals.py upload --source ... --repo owner/name --branch feature/name --base main --destination folder [--pr N] --report report.json`. Use `--replace` only when the user explicitly agrees to replace differing bytes.
4. Check independent GitHub raw re-download SHA-256 results and Git Blob SHA-1 values. The tool creates or reuses a **Draft PR**, never merges or marks it ready.
5. Update project-specific asset ledgers only after every required image passes byte-by-byte verification and no images are missing. Never infer creative approval from an upload. Save project-specific state in the project's canonical repository, not in this generic skill.

## Files
- `github_originals.py`: fully executable standard-library Python uploader.
- `tests/test_github_originals.py`: offline unit + local Git integration tests.
- `README.md`: complete prerequisites and example commands.

## Fail-safe behaviors
No source bytes means no upload. A GitHub connector that accepts only UTF-8 text is not a file-transfer primitive. No Gmail workaround unless separately authorized. No secret extraction. No `git push --force`, no `gh pr merge`, no accidental main-branch writes. Never claim GitHub.com remote verification from local-only tests.