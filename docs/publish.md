# Publish to PyPI

This project currently uses manual PyPI uploads. The GitHub Actions workflow in `.github/workflows/main.yml` only runs tests and does not publish packages.

The example commands below use version `1.4.3`.

## Prerequisites

- PyPI maintainer access for the `secretscraper` project
- A PyPI API token from `https://pypi.org/manage/account/token/`
- A clean git worktree
- The package version updated in `pyproject.toml` and `src/secretscraper/__init__.py`

## Release Checklist

1. Confirm the version:

```shell
uv run --active --no-sync secretscraper --version
```

Expected output:

```text
1.4.3
```

2. Run tests:

```shell
tox
```

3. Commit the release change and tag it:

```shell
git add pyproject.toml src/secretscraper/__init__.py uv.lock
git commit -m "release: 1.4.3"
git tag v1.4.3
```

4. Build the distribution artifacts:

```shell
rm -rf dist/
uv build --no-sources
```

5. Dry-run the publish:

```shell
export UV_PUBLISH_TOKEN='pypi-...'
uv publish --dry-run
```

6. Upload to PyPI:

```shell
export UV_PUBLISH_TOKEN='pypi-...'
uv publish
```

7. Push the commit and tag:

```shell
git push origin main
git push origin v1.4.3
```

8. Verify the published release:

- Open `https://pypi.org/project/secretscraper/`
- Install the new version in a clean environment:

```shell
python -m pip install --upgrade secretscraper==1.4.3
```

## TestPyPI Dry Run

If you want to verify the upload flow before publishing to PyPI:

```shell
uv publish \
  --dry-run \
  --token 'pypi-...' \
  --publish-url https://test.pypi.org/legacy/ \
  --check-url https://test.pypi.org/simple/
```

## Notes

- Uploading the same version twice to PyPI will fail. If `1.4.3` has already been published, bump the version before rebuilding.
- Keep `uv.lock` in sync with the local package version so local tooling reflects the same release number.
- `uv publish` defaults to uploading `dist/*`, so you do not need to pass the artifact paths unless you want to override them.
- Long term, Trusted Publishing via GitHub Actions is preferable to API-token uploads.
