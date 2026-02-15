# Releasing pine-voice (Python)

## Prerequisites (one-time setup)

### PyPI Trusted Publishing

Publishing uses OIDC-based trusted publishing — no PyPI tokens needed.

1. Go to **pypi.org/manage/account/publishing/**
2. Under **"Add a new pending publisher"**, fill in:
   - **PyPI project name**: `pine-voice`
   - **Owner**: `RunVid`
   - **Repository name**: `pine-voice-python`
   - **Workflow name**: `publish.yml`
   - **Environment name**: *(leave blank)*
3. Click **Add**

PyPI supports pending publishers, so the package doesn't need to exist first.

## Publishing a new version

1. **Bump the version** in both places:
   - `pyproject.toml` → `version = "<VERSION>"`
   - `src/pine_voice/__init__.py` → `__version__ = "<VERSION>"`

2. **Commit and tag**:
   ```bash
   git add pyproject.toml src/pine_voice/__init__.py
   git commit -m "release: v<VERSION>"
   git tag v<VERSION>
   ```

3. **Push with tags**:
   ```bash
   git push origin main --tags
   ```

4. **Monitor** the publish workflow at the repo's **Actions** tab on GitHub.

5. **Verify** the published package:
   ```bash
   pip index versions pine-voice
   ```

## What happens on tag push

1. The CI workflow runs (build across Python 3.9–3.13, import check, twine check)
2. If CI passes, the publish job builds sdist + wheel
3. `pypa/gh-action-pypi-publish` exchanges a GitHub OIDC token with PyPI
4. Package is published to PyPI

## Notes

- The `RELEASING.md` file is not included in the PyPI package (hatchling only includes `src/` by default)
- Remember to bump version in **both** `pyproject.toml` and `__init__.py`
- Trusted publishing eliminates the need for stored PyPI tokens or API keys
- Only tag pushes matching `v*` trigger the publish workflow
