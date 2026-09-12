# Image safety scope (v1) — operator notes

Draft for the final documentation pass. Not user-facing.

## Implemented (v1)

| Layer | Scope |
|-------|--------|
| Text prompts | Keyword blocklist in `general_data.json`; validated on MIC / TTI / IDWM before BFL |
| BFL provider | `safety_tolerance` on all submit payloads; poll/submit failures logged; generic client errors |
| Uploads | MIME allowlist, magic-byte check, min/max file size, min/max image dimensions |
| Rate limits | Upload + submit + validate aligned in `config_file.json` (see backend README) |

## Not implemented (v1)

| Gap | Notes |
|-----|--------|
| Image content moderation | Garment/selfie bytes are **not** scanned for hate symbols, nudity, etc. |
| Vision classifier | No third-party moderation API on uploads |
| Hash blocklist | No known-bad image hash database |

Abuse via images may still reach BFL; provider safety and rate limits are partial mitigation.

## Future options (Phase 6+)

1. Pre-flight vision moderation API on uploaded bytes (garment + selfie) before MIC.
2. Perceptual hash blocklist for known bad images.
3. Human review queue for reported try-on results.
4. Metrics gate: enable (1) only if `bfl_poll_reject` / complaints stay high while `content_policy_keyword` stays low.

## Rate limit bundle (try-on)

One try-on ≈ `validate_prompt` + `upload/images` (2 files) + `mic` + polling + `download`.

Configured defaults (per minute): upload **10**, MIC **6**, validate **10**, polling **30**, download **30**.
