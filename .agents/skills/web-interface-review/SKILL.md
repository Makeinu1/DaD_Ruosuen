---
name: web-interface-review
description: Review web pages for accessibility, interaction quality, layout, responsive design, and performance using the latest Vercel Web Interface Guidelines.
license: MIT
---

# Web Interface Review

Use after an interface redesign or before a release. Works on static HTML/CSS/JavaScript as well as component-based apps.

## Workflow

1. Read the **current** Vercel Web Interface Guidelines from https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md . The linked source is authoritative; do not assume a cached copy is current.
2. Inspect the actual site's source files and resulting UI when browser access is available. Check narrow/mobile and wide/desktop viewports.
3. Check semantic navigation, document heading order, alt text/decorative images, visible focus states, contrast, reduced-motion, keyboard access, and touch targets.
4. Check large images and fonts for layout shifts, relative URL handling, responsive overflow, loading failures, and broken navigation.
5. Report findings as file and line, sorted by severity. Fix actionable issues and run the checklist again. Clearly distinguish source-level checks from real browser or device verification.
6. Preserve the project's established voice and design direction; the guideline is a quality gate, not a generic visual template.

## Provenance

Adapted as a reusable quality-check workflow from [Vercel Labs Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines), licensed under MIT. The source rules are read directly at use time.
