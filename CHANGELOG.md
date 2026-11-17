# Changelog

## [1.1.0] — 2026-11-17

### Added
- `tools/subset.py` — slice the dataset by scope (countries → states → counties
  → cities → postcodes) and by geography (continent, country, state), emitting
  any format. The slice is always FK-consistent.
- `SKILL.md` — packaged as an AI-agent skill (natural-key geography data with
  granular selection), with `references/` and `examples/`.
- Referential-closure guarantee on every generated subset.

## [1.0.0] — 2026-11-17

### Changed
- Natural-key data model (ISO2 + ISO 3166-2 + Wikidata QID/slug) replacing
  surrogate numeric IDs.
- `type` split into orthogonal `kind` + `type` (+ `type_local`).
- `gdp` removed; `population_year` added; `phone` is now a list; `currency` is
  a structured object.
- Single-runtime Python exporter (`tools/export.py`) replacing the PHP/MySQL/
  Node + `nmig` pipeline; batched SQL INSERTs; 12 output formats.
- `tools/validate.py` integrity checks (key uniqueness + FK referential
  integrity).
- Rewritten docs; monetization and paid-API references removed; ODbL
  attribution and per-source notices retained.

### Data
- 250 countries · 5,327 states · 14,058 counties · 171,338 cities ·
  728,545 postcodes (117 countries) · 6 regions · 22 subregions ·
  19 languages.
