# Errors

Command failures and integration errors.

## [ERR-20261023-EDIT] targeted source inspection

**Logged**: 2026-10-23T21:15:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tooling

### Summary
A few inspection/edit calls failed because the pattern was an invalid regular expression, a requested offset exceeded the file length, or an old literal had already changed/appeared more than once.

### Suggested Fix
Read the current narrow file range before editing; prefer literal searches or separate simple grep queries; submit only lossless JSON values and do not batch replacements that rely on stale text.

### Metadata
- Reproducible: yes
- Related Files: project source files

---

## [ERR-20261023-WEB] web_search

**Logged**: 2026-10-23T18:24:00+08:00
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
The external web-search integration could not run because its configured API returned HTTP 402.

### Error
`web_search` returned HTTP 402 (Insufficient Balance) from the configured search endpoint.

### Context
- A search for Dongguan intangible-heritage records and Aotai Academy details was attempted.
- Direct page fetch and local project evidence may still be used; no endpoint setting was changed.

### Suggested Fix
Retry after the user/provider restores search API balance or use an independently available source.

### Metadata
- Reproducible: unknown
- Related Files: none

## [ERR-20261023-GREP] grep

**Logged**: 2026-10-23T18:53:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tooling

### Summary
An unescaped `[` in a ripgrep expression caused pattern parsing to fail.

### Suggested Fix
Escape regex metacharacters or split searches into simpler expressions.

### Metadata
- Reproducible: yes
- Related Files: none

---

## [ERR-20261023-TOOLS] inspection helpers

**Logged**: 2026-10-23T23:30:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tooling

### Summary
A few bounded inspection calls failed due to invalid ripgrep metacharacters, a missing output field, or a malformed TypeScript snippet; no source files were affected by those failed calls.

### Suggested Fix
Use simpler escaped regexes or read small source ranges; keep run_code return objects fully lossless and syntax-check the wrapper before running multiple operations.

### Metadata
- Reproducible: yes
- Related Files: none

---

## [ERR-20261024-GREP] source review search

**Logged**: 2026-10-24T00:22:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tooling

### Summary
A grep query with an unescaped opening parenthesis failed during Blender source review; no source files were changed by the failed query.

### Suggested Fix
Search using a simpler literal-safe pattern, read a narrow source range, or escape regular-expression grouping characters before retrying.

### Metadata
- Reproducible: yes
- Related Files: none

---

## [ERR-20261024-JSON] run_code output serialization

**Logged**: 2026-10-24T00:24:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tooling

### Summary
A composed inspection result included `undefined` object properties, so the tool rejected it as non-lossless JSON after its read-only calls finished.

### Suggested Fix
Normalize optional output fields to `null` or omit them before returning; keep tool output strictly JSON-safe.

### Metadata
- Reproducible: yes
- Related Files: none

---

## [ERR-20261024-INSPECT] bounded source queries

**Logged**: 2026-10-24T00:53:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tooling

### Summary
A source grep with an unescaped opening parenthesis and a malformed TypeScript tuple caused two additional inspection calls to fail before any file writes.

### Suggested Fix
Use plain search tokens without parentheses, or escape regular-expression syntax; validate tuple/code syntax before executing a combined read.

### Metadata
- Reproducible: yes
- Related Files: none

---

## [ERR-20261024-NOOP] redundant patch attempt

**Logged**: 2026-10-24T09:34:00+08:00

**Priority**: low

**Status**: resolved

**Area**: tooling

### Summary

A combined patch included two no-op replacements and was rejected; the other three intended browser hardening edits completed successfully. No source content was changed by the rejected replacements.

### Suggested Fix

Do not submit identical old/new strings in multi-edit batches; reread the exact current range after each related edit.

### Metadata
- Reproducible: yes
- Related Files: main.py

---

## [ERR-20261024-ENV] bundled runtime OpenCV dependency

**Logged**: 2026-10-24T09:45:00+08:00

**Priority**: low

**Status**: resolved

**Area**: test environment

### Summary

The bundled Python runtime lacks cv2, so firmware UI smoke and an initial content probe failed at import; the host Python runtime has OpenCV 4.12 and the same UI smoke passed.

### Suggested Fix

Use the host Python runtime for OpenCV-dependent UI checks or add cv2 to the bundled test environment; keep pure content/syntax tests on the bundled runtime.

### Metadata
- Reproducible: yes
- Related Files: ui.py, relic.py

---

## [ERR-20261024-MANIFEST] path normalization

**Logged**: 2026-10-24T09:55:00+08:00

**Priority**: low

**Status**: resolved

**Area**: audio tooling

### Summary

The first manifest filtering pass normalized the wrong Windows path separator and temporarily produced an empty manifest; the original manifest was restored from HEAD, then re-filtered successfully to six current files.

### Suggested Fix

Normalize both slash styles explicitly and compare manifest paths against a relative audio-root path before writing.

### Metadata
- Reproducible: yes
- Related Files: 02_数据/audio/manifest.json

---
