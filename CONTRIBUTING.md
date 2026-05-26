# Contributing

Thanks for helping make Shorts Clipper a better open-source AI clipping system.

## Development principles

- Keep changes incremental and easy to review.
- Preserve existing behavior unless the change explicitly documents a migration.
- Prefer typed, modular, testable code over clever shortcuts.
- Add tests for pure logic and bug fixes.
- Keep dependencies minimal and justified.
- Avoid broad rewrites without a plan.
- Do not commit generated media, local models, virtualenvs, or credentials.

## Local setup

```bash
python -m venv env
source env/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Install development hooks:

```bash
pip install pre-commit
pre-commit install
```

## Checks

Run before opening a pull request:

```bash
python -m unittest discover -v
python -m compileall -q .
pre-commit run --all-files
```

## Commit style

Use clear conventional-style commits when possible:

```text
feat: add transcript cache manifest
fix: validate provider timestamp output
docs: improve Docker quickstart
test: cover crop geometry edge cases
```

## Good first areas

- Improve docs and examples.
- Add tests around existing script behavior.
- Move legacy script logic into package modules while keeping wrappers.
- Add provider adapters behind the existing provider interface.
- Improve ffmpeg rendering while preserving output compatibility.

## Pull request checklist

- [ ] Change is focused and incremental.
- [ ] Tests pass locally.
- [ ] New behavior is documented.
- [ ] No secrets, media outputs, virtualenvs, or model files committed.
- [ ] Existing CLI behavior still works or migration is documented.
