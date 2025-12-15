# Publishing Guide

This guide will help you publish your OSHA Violation Analyzer to a Git repository.

## Prerequisites

1. **Git installed** - Check with: `git --version`
2. **GitHub/GitLab account** (optional, for remote hosting)
3. **Repository created** on GitHub/GitLab (if using remote)

## Step 1: Initialize Git Repository

```bash
# Already done - repository initialized
git init
```

## Step 2: Review Files to Commit

```bash
# See what files will be added
git status

# See detailed file list
git status --short
```

## Step 3: Add Files to Staging

```bash
# Add all files (respects .gitignore)
git add .

# Verify what's staged
git status
```

## Step 4: Create Initial Commit

```bash
# Create initial commit
git commit -m "Initial commit: Multi-Agency Compliance Analyzer

- Database-backed OSHA violation analyzer
- Multi-agency compliance comparison framework
- REST API with FastAPI
- Streamlit dashboard
- Environment variable configuration
- Comprehensive documentation"
```

## Step 5: Set Up Remote Repository (GitHub/GitLab)

### Option A: Create New Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `OSHA-Violation-Analyzer` (or your preferred name)
3. Description: "Multi-Agency Compliance Analyzer for OSHA, EPA, MSHA, FDA enforcement data"
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### Option B: Use Existing Repository

If you already have a repository URL, use that instead.

## Step 6: Add Remote and Push

```bash
# Add remote (replace with your repository URL)
git remote add origin https://github.com/YOUR_USERNAME/OSHA-Violation-Analyzer.git

# Or if using SSH:
# git remote add origin git@github.com:YOUR_USERNAME/OSHA-Violation-Analyzer.git

# Verify remote
git remote -v

# Push to remote
git branch -M main  # Rename default branch to 'main' (if needed)
git push -u origin main
```

## Step 7: Verify Publication

1. Visit your repository URL on GitHub/GitLab
2. Verify all files are present
3. Check that README.md displays correctly
4. Verify .gitignore is working (no sensitive files committed)

## Important Notes

### Files NOT Committed (by .gitignore)
- `.env` files (contains secrets)
- `data/*.csv` (large data files)
- `data/*.db` (database files)
- `__pycache__/` (Python cache)
- `venv/` (virtual environment)
- `*.log` (log files)

### Files That ARE Committed
- Source code (`src/`)
- Documentation (`docs/`)
- Scripts (`scripts/`)
- Configuration templates (`.env.example`, `.env.production.example`)
- Requirements (`requirements.txt`)
- Docker files
- README and documentation

## Next Steps After Publishing

1. **Add repository description** on GitHub/GitLab
2. **Add topics/tags**: `osha`, `compliance`, `safety`, `python`, `streamlit`, `data-analysis`
3. **Enable GitHub Pages** (if you want to host documentation)
4. **Set up GitHub Actions** for CI/CD (optional)
5. **Add license** (Apache 2.0 is already in LICENSE file)
6. **Create releases** for version tags

## Troubleshooting

### Authentication Issues
```bash
# If you get authentication errors, set up credentials:
# For HTTPS:
git config --global credential.helper store

# For SSH (recommended):
# Generate SSH key: ssh-keygen -t ed25519 -C "your_email@example.com"
# Add to GitHub: Settings > SSH and GPG keys
```

### Large Files
If you need to commit large files later:
```bash
# Install Git LFS
git lfs install
git lfs track "*.csv"
git add .gitattributes
git commit -m "Add Git LFS tracking for CSV files"
```

### Update Remote URL
```bash
# Change remote URL
git remote set-url origin NEW_URL
```

## Repository Settings Recommendations

1. **Branch Protection**: Protect `main` branch (Settings > Branches)
2. **Issues**: Enable issues for bug tracking
3. **Discussions**: Enable for community Q&A
4. **Wiki**: Optional, for additional documentation
5. **Actions**: Enable for CI/CD workflows

## Security Checklist

Before publishing, ensure:
- ✅ No `.env` files committed
- ✅ No API keys in code
- ✅ No passwords in code
- ✅ No database files committed
- ✅ `.gitignore` is complete
- ✅ LICENSE file included
- ✅ README.md is complete

## Need Help?

- Git documentation: https://git-scm.com/doc
- GitHub guides: https://guides.github.com
- GitLab guides: https://docs.gitlab.com
