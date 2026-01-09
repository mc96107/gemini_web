# Plan: Line Ending Normalization

## Phase 1: Configuration [checkpoint: a4d4a83]
- [x] Task: Create .gitattributes d0b6d3f
    - [ ] Add `* text=auto eol=lf` to `.gitattributes`.
- [x] Task: Normalize Repository 51a6c4b
    - [ ] Run `git add --renormalize .`
    - [ ] Verify the absence of LF/CRLF warnings.
- [x] Task: Commit Changes da1b9ca
    - [ ] Commit `.gitattributes`.
