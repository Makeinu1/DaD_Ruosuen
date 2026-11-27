---
name: google-ai-pro-flow-studio
description: Zero-extra-spend (0 JPY) image and video production workflow within a Google AI Pro subscription using Antigravity's built-in image generation (generate_image) and official interactive browser operation on Google Flow (https://flow.google.com/). Covers Nano Banana Pro image generation, reference-image/previs video creation (Omni Flash 1.2 / Veo 3.1), local asset saving, strict quota/credit guardrails, ToS-compliant user login handoff, and full JSONL + sidecar provenance logging.
---

# Google AI Pro Zero-Extra-Spend Flow Studio (`0円追加支出` 制作スキル)

Use this skill to run an end-to-end **image + video production workflow strictly inside a Google AI Pro subscription** with **zero paid API calls, zero credit top-ups, and full reproducibility logging**.

---

## Hard Constraints (NEVER Violate)

1. **追加支出は 0 円（Zero Extra Spend）**：
   - **NEVER** call paid Gemini Developer API / Vertex AI endpoints (`GEMINI_API_KEY` / billable `client.interactions.create`).
   - **NEVER** purchase AI credit top-up packs or click upgrade/billing buttons inside Google Flow or Google One.
   - **STOP IMMEDIATELY** when daily image quota or remaining Google AI Pro Flow credits (`1,000/month + 50/day`) cannot cover the next generation.
2. **規約順守・認証保護（ToS & Auth Safety）**：
   - **NEVER** use unofficial/reverse-engineered APIs, extract browser cookies/tokens, or bypass CAPTCHA/2FA/login gates.
   - Use ONLY Antigravity's built-in `generate_image` tool and **official interactive browser control** (e.g., Antigravity Browser Subagent in local Antigravity IDE, or clean handoff to the user's own browser when running in a remote cloud VM without a browser tool).
3. **ログイン・操作許可は必ずユーザーへ引き継ぐ（Mandatory User Handoff）**：
   - Whenever Google account sign-in, 2FA, Terms acceptance, or a credit-spending click is required on `https://flow.google.com/`, pause and hand off explicitly to the user.

---

## Environment Capability Check (Run FIRST!)

Before starting, check which tools exist in the active session:
- **Built-in Image Generation (`generate_image`)**: Available directly -> use for ¥0-extra-spend model sheets, drafts, and reference paintings (pair with `gemini-consistent-image` rules).
- **Official Interactive Browser Tool (`browser_subagent` / Antigravity Browser)**:
  - **If available (local Antigravity IDE)**: Open `https://flow.google.com/` in the official browser -> hand off Google AI Pro sign-in to the user -> once signed in, operate the Flow UI step-by-step with user confirmation before each credit-consuming video generation -> download PNG/MP4 directly into `studio/images/` and `studio/videos/`.
  - **If NOT available (remote headless Linux VM)**: Do NOT attempt headless Google login or scrape auth. Instead: (a) generate/verify local assets via `generate_image`, (b) prepare exact prompts & ≤15s previs clips, (c) verify remaining quota via `scripts/studio_log.py check`, (d) surface `https://flow.google.com/` to the user to run the Flow UI step in their signed-in browser, and (e) register the downloaded PNG/MP4 back into `studio/` via `scripts/studio_log.py record`.

---

## Step-by-Step Production Workflow

### Step 1: Initialize Local Studio & Check Quota (`0円ガード`)
```bash
python3 scripts/studio_log.py status
python3 scripts/studio_log.py check --media-type video --model gemini-omni-1.2-flash --duration 8 --resolution 720p
```
- Local studio layout:
  - `studio/images/` — saved PNG/JPG outputs + `<file>.meta.json` sidecars
  - `studio/videos/` — saved MP4 outputs + `<file>.meta.json` sidecars
  - `studio/logs/generation_log.jsonl` — append-only provenance ledger
  - `studio/logs/quota_budget.json` — Google AI Pro monthly/daily quota & credit tracker

### Step 2: Asset Sheets & Keyframes (0 Flow Credits!)
1. **Option A (Antigravity `generate_image`)**: Generate locked model sheets (`Sheet A`, `Sheet B`) & keyframes directly inside Antigravity (`¥0` extra spend), then visually inspect every pixel with `view_file`.
2. **Option B (Google Flow `https://flow.google.com/` -> Nano Banana Pro)**:
   - On Google AI Pro, Nano Banana Pro image generation uses **0 Flow credits** (up to **100 images/day** + **1,000 Nano Banana 2.1/2 Lite images/day**; see `references/flow-quota-and-runbook.md`).
   - Follow `gemini-consistent-image` sequential reference chaining (Sheet A + Sheet B + previs layout PNG + previous approved frame).
   - Download the approved PNG into `studio/images/`.
3. **Record every generation immediately**:
   ```bash
   python3 scripts/studio_log.py record \
     --media-type image \
     --surface google-flow-browser \
     --model nano-banana-pro \
     --source /path/to/downloaded.png \
     --name KF-G1.png \
     --ref studio/images/SheetA_whale_pcs.jpg \
     --ref studio/images/SheetB_flower_arch.jpg \
     --prompt-file /path/to/prompt.txt \
     --credits 0 \
     --qa-status needs_review
   ```

### Step 3: Reference-Driven Video Generation on Google Flow -> Save MP4
1. Open `https://flow.google.com/` (hand off login/2FA to user if not already signed in).
2. Confirm remaining Flow credits on screen AND via `studio_log.py check` before clicking Generate.
3. **Draft-cheap, finish-clean strategy (stretches 1,000 monthly credits!)**:
   - Test tricky motion/camera beats at **Omni Flash 1.2 `360p`** (`1 credit/sec` up to 10s, `2 credits/sec` for 11–15s) or **Veo 3.1 Lite** (`10 credits` flat for 4/6/8s).
   - Once camera & consistency are locked, generate final at **Omni Flash 1.2 `720p`** (`3 credits/sec` up to 10s, `6 credits/sec` for 11–15s) + **0-credit `1080p` upscale** (for clips 1–10s; +1 cr/extra sec for 11–15s).
   - Follow `gemini-previs-video` natural-language media binding (upload ≤15s previs MP4 + up to 6 locked reference images; NO `@Video1` or `<IMAGE_REF_0>` tags).
4. Download the finished `.mp4` and register it into `studio/videos/`:
   ```bash
   python3 scripts/studio_log.py record \
     --media-type video \
     --surface google-flow-browser \
     --model gemini-omni-1.2-flash \
     --source /path/to/downloaded.mp4 \
     --name final_G1.mp4 \
     --ref studio/images/KF-G1.png \
     --ref studio/images/SheetA_whale_pcs.jpg \
     --prompt-file /path/to/video_prompt.txt \
     --duration 12 \
     --resolution 720p \
     --qa-status needs_review
   ```
5. Verify MP4 specs (resolution, 24fps, duration, SHA-256) automatically written into `studio/videos/<name>.mp4.meta.json` and `studio/logs/generation_log.jsonl`.

## Bundled Resources

- `references/flow-quota-and-runbook.md` — Verified Nov 2026 Google AI Pro Flow credit table, daily image quotas, browser UI handoff checklist, and exact stop conditions.
- `scripts/studio_log.py` — Zero-dependency provenance ledger (`generation_log.jsonl` + `.meta.json`) and hard credit-limit guard.
