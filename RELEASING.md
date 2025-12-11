# Releasing a New Version

This project uses `bump-my-version` for version management.

## Prerequisites

Install dev dependencies:
```bash
uv pip install -e ".[dev]"
```

## Version Bump Commands

**Patch release** (0.1.0 → 0.1.1) - Bug fixes, minor changes:
```bash
bump-my-version bump patch
```

**Minor release** (0.1.0 → 0.2.0) - New features, backward compatible:
```bash
bump-my-version bump minor
```

**Major release** (0.1.0 → 1.0.0) - Breaking changes:
```bash
bump-my-version bump major
```

## What Happens Automatically

When you run `bump-my-version bump <part>`:

1. ✅ Updates version in `pyproject.toml` (single source of truth)
2. ✅ Creates a git commit with message: `Bump version: X.Y.Z → X.Y.Z`
3. ✅ Creates a git tag: `vX.Y.Z`

**Note:** Version is read dynamically from `pyproject.toml` at runtime using `importlib.metadata`.

## Release Process

### 1. Prepare the Release

```bash
# Make sure you're on master with latest changes
git checkout master
git pull

# Check status - should be clean
git status
```

### 2. Bump the Version

```bash
# For a patch release (bug fixes)
bump-my-version bump patch

# For a minor release (new features)
bump-my-version bump minor

# For a major release (breaking changes)
bump-my-version bump major
```

### 3. Push the Release

```bash
# Push the commit and tag
git push
git push --tags
```

### 4. Build and Publish

```bash
# Build the package
python -m build

# Upload to PyPI (requires PyPI account and token)
python -m twine upload dist/*
```

### 5. Create GitHub Release

1. Go to https://github.com/YOUR_USERNAME/xtctool/releases
2. Click "Draft a new release"
3. Select the tag you just pushed (e.g., `v0.2.0`)
4. Generate release notes from commits
5. Publish release

## Dry Run (Test Without Committing)

To see what would change without making changes:

```bash
bump-my-version bump --dry-run --verbose patch
```

## Manual Version Check

Current version:
```bash
python -c "import xtctool; print(xtctool.__version__)"
```

## Version Scheme

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New features (backward compatible)
- **PATCH** version: Bug fixes (backward compatible)

### Pre-1.0.0 Releases

During initial development (0.x.x):
- Breaking changes → Minor version bump (0.1.0 → 0.2.0)
- New features → Minor version bump
- Bug fixes → Patch version bump (0.1.0 → 0.1.1)

### Post-1.0.0 Releases

After stable release (1.0.0+):
- Breaking changes → Major version bump (1.0.0 → 2.0.0)
- New features → Minor version bump (1.0.0 → 1.1.0)
- Bug fixes → Patch version bump (1.0.0 → 1.0.1)

## Troubleshooting

**Uncommitted changes error:**
```bash
# Commit your changes first
git add .
git commit -m "Your changes"

# Then bump version
bump-my-version bump patch
```

**Wrong version bumped:**
```bash
# Reset the commit and tag
git reset --hard HEAD~1
git tag -d vX.Y.Z

# Bump again with correct part
bump-my-version bump <correct-part>
```

**Tag already exists:**
```bash
# Delete the tag
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z

# Bump again
bump-my-version bump patch
```
