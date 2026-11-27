# github-binary-artifact-transfer (Python + connector bridge v1.1)

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
No source bytes means no upload. UTF-8-only file writes are not a binary transfer primitive. Use the v1.1 CSV bridge only with an actual binary-capable create_blob and verified exported CSV readback. No Gmail workaround unless separately authorized. No secret extraction. No `git push --force`, no `gh pr merge`, no accidental main-branch writes. Never claim GitHub.com remote verification from local-only tests.
## v1.1: CSV bridge for split Python/connector environments (2026-11-28)

If Python can read originals but cannot reach GitHub, and the agent has a binary-capable GitHub connector plus a file-reader capable of exact CSV text retrieval, use the following fallback **without Gmail or another external store**. Normal direct Git/gh remains the preferred route.

1. Obtain approved original bytes; run existing plan checks. ZIP manifests require both assets and variants arrays, including an empty variants array.
2. Run `python3 connector_packet.py ORIGINAL.png PACKET.csv` once per original. It writes numbered Base64 rows and emits only lengths and hashes. Use the actual exported packet file reference (never invent an ID); do not paste Base64 into the conversation.
3. Use `connector_bridge.js` in the agent host with real tool adapters, repository, exported file ID and trusted local manifest. Reassemble rows in index order, reject duplicate/missing/truncated rows and wrong lengths. Pass directly to create_blob with encoding=base64. Require exact local Git blob SHA-1 equality. The 10 MiB local cap is not a claim about connector limits.
4. Read current PR head, inspect tree and existing paths, create a tree from the current tree using verified blob SHA values; create a commit with current head as parent; advance ref non-forced with expected head. Re-fetch branch tree and require path, byte size and blob SHA equality for all files. Do not commit packets or Base64 text; do not use Gmail without specific authorization.
5. Distinguish blob_created, tree_verified and remote_verified. The last requires independent raw-byte readback SHA-256 and size (direct GitHub raw fetch or independently checked-out remote commit). GitHub fetch_blob may reject binary as UTF-8 and fetch_file base64 may return an empty string for large files; neither is successful raw verification. Preserve state and stop if no raw readback is available. Never mark a PR ready or merge automatically.
6. Keep packet artifacts transient in the authorized conversation; do not publish or persist them in external storage. Avoid logging encoded data. A failed handoff is not authorization to create email drafts.

Verified: local packet generation/roundtrip for 3 KiB fixture and two 2.4–2.7 MB PNGs; refusal of overwrite and invalid PNG; fixture and both actual PNG Git blob SHA-1 matched using the CSV/Files/create_blob route, and both PNGs were found at the intended remote branch paths with exact sizes. Raw independent SHA-256 verification is a separate step; do not conflate these. No network access from Python was needed for transfer. No guarantee for other sizes or host capabilities.
