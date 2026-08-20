# Conventions

Rules this repository follows. They are rules rather than preferences: if something here reads as merely stylistic, the reason it is a rule is written next to it.

## Language

**English only.** Documentation, code comments, docstrings, strings printed to the user, error and hint text raised through `SystemExit`, argparse help, commit messages, changelog entries. All of it.

Commit messages are included in that list and are the easiest part of it to forget, because a commit message is not in any file you reopen later. It is documentation that outlives the diff it describes, so it follows the same rule the documentation does.

This rule was adopted on 2026-08-20. The repository grew out of a Vietnamese-language report project, so a large amount of Vietnamese prose is still in `src/` and `docs/`. That backlog is scheduled for one planned translation pass and is deliberately **not** fixed piecemeal while doing other work, because a half-translated file is harder to read than a consistently Vietnamese one. Anything **newly written** is English from the start.

One thing this rule does not touch: the **id slugs** in a brief are Vietnamese without diacritics, because they are made from the process step names the author wrote, and `task-user-lap-ke-hoach` is the name of a real step rather than a piece of English prose. The convention that produces them is documented in [`docs/naming.md`](docs/naming.md).

## Naming and description

**Be as descriptive as the name will allow**, in prose and in code. A name that says what the thing does saves a line of comment; a vague name is not rescued by three lines of comment. This applies to functions, parameters, variables, modules, CLI flags, and section headings.

Two naming layers exist here and they should not be confused:

- **Python names** follow ordinary Python style: `snake_case` for functions and variables, `UPPER_SNAKE` for module-level tables such as `MARKER_CANON` and `CONTAINERS`, a leading underscore for a helper nobody outside the module should call.
- **BPMN element ids** follow the repository's own id convention, `<type>-<subtype>-<subsubtype>-<name>`, which is a closed grammar checked by `bpmn-id` and `bpmn-lint`. It is specified in [`docs/naming.md`](docs/naming.md) and must not be invented against.

A console script is named for the noun it produces or the verb it performs, `bpmn-brief`, `bpmn-lint`, `bpmn-id`, `bpmn2yaml`, `bpmn-rotate`. A new one joins that family or it does not get added.

## Punctuation

**No em-dash.** Replace it by meaning, not mechanically: a semicolon when it joins two independent clauses, a colon when it opens an explanation or attaches a label, parentheses when a pair of them brackets an aside. Replacing every one with a comma produces comma splices and four-comma sentences where the main clause is no longer findable.

This applies to strings printed to the user as much as to prose, which is where it matters most: a user reads a hint once and acts on it.

En-dash in a numeric range is fine.

## Markdown source

**One paragraph is one line.** No manual wrapping at 80 or 100 columns. Wrapping makes `git diff` claim a whole paragraph changed when one word did, and it makes every search-and-replace slip past strings that happen to straddle a line break.

Python source still wraps normally; the diff problem does not apply there.

## Changelog

**Every change is logged in [`docs/changelogs.md`](docs/changelogs.md)**, not only the large ones. One entry per tagged version, newest first. A completed item moves out of [`docs/TODO.md`](docs/TODO.md) and into the changelog entry for the version that shipped it, so `TODO.md` only ever holds open work.

Entries explain rather than list: what changed, why it was needed, and what was considered and dropped. `git log` already does the listing.

## Dependencies must be stated

Every dependency is either synchronised automatically or described explicitly at the point that needs it: which version, where it comes from, and what breaks when it drifts.

- **Runtime**: `pyyaml` only, declared in `pyproject.toml`. Everything else is the standard library, and it should stay that way: this package is installed straight from a git tag by a consumer's CI, so every added dependency is a new way for that install to fail.
- **The version number lives in exactly one place**, `src/bpmn_generator/_version.py`. `__init__.py` and `build.py` both import it from there, so the `exporterVersion` attribute written into a generated `.bpmn` cannot drift from the installed package. `pyproject.toml` carries the same number and is the one copy that has to be updated by hand at release time.
- **Downstream**: [typst-bpmn](https://github.com/sam-uit/typst-bpmn) calls `bpmn2yaml` in `just convert`, `just check`, `just demo` and `just lint`, and its CI installs this package from GitHub **pinned to a tag**. Two consequences. A release is not usable downstream until it is both pushed and tagged, a local commit is invisible to that CI. And a change to the converter's output can move typst-bpmn's golden manifest, which is why the pin is a tag and not a branch: the update has to be a decision somebody made, not a red build nobody caused.

## Before committing

```bash
for t in tests/*.py; do PYTHONPATH=src python3 "$t"; done
```

The six files are `test_ids.py` (id convention, 24 assertions), `test_markers.py` (activity markers, 17), `test_message_routes.py` (message flow geometry, 20), `test_rotate.py` (orientation transpose, 19), `test_roundtrip.py` (yaml to bpmn to yaml is lossless, 24) and `test_vertical.py` (the vertical layout mode, 21). They are plain scripts with no test-runner dependency, so `PYTHONPATH=src python3` is enough and `uv run` is not required; each prints a count and exits non-zero if any of its cases failed.

The round-trip test is the one that guards the workflow itself. The improvement loop only works while `.yaml` to `.bpmn` to `.yaml` comes back byte-identical apart from `source`; the moment a coordinate is dropped, the author's manual work in the modeler is silently lost on the next pass.

Commits are atomic: one logical change each, with a body that explains **why**, including the alternatives that were considered and dropped.
