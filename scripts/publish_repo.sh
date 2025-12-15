#!/bin/bash
# Helper script to publish repository to GitHub/GitLab

set -e

echo "🚀 Publishing OSHA Violation Analyzer Repository"
echo "================================================"
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not initialized. Run: git init"
    exit 1
fi

# Check current status
echo "📋 Current repository status:"
git status --short | head -10
echo ""

# Ask for confirmation
read -p "Do you want to add all files and create initial commit? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Add all files
echo "📦 Adding files to staging..."
git add .
echo "✅ Files added"
echo ""

# Show what will be committed
echo "📝 Files staged for commit:"
git status --short
echo ""

# Create commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit: Multi-Agency Compliance Analyzer

- Database-backed OSHA violation analyzer
- Multi-agency compliance comparison framework (OSHA, EPA, MSHA, FDA)
- REST API with FastAPI and OpenAPI documentation
- Interactive Streamlit dashboard
- Environment variable configuration system
- Comprehensive documentation
- Docker support for containerized deployment
- Test suite with pytest
- Code organization and quality improvements"

echo "✅ Initial commit created"
echo ""

# Check if remote exists
if git remote | grep -q "^origin$"; then
    echo "🌐 Remote 'origin' already exists:"
    git remote -v
    echo ""
    read -p "Do you want to push to remote? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Pushing to remote..."
        git branch -M main 2>/dev/null || true
        git push -u origin main
        echo "✅ Pushed to remote!"
    fi
else
    echo "🌐 No remote repository configured."
    echo ""
    echo "To add a remote repository:"
    echo "  git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git"
    echo "  git branch -M main"
    echo "  git push -u origin main"
    echo ""
    echo "Or use SSH:"
    echo "  git remote add origin git@github.com:YOUR_USERNAME/REPO_NAME.git"
    echo "  git branch -M main"
    echo "  git push -u origin main"
fi

echo ""
echo "✨ Done! Your repository is ready."
echo ""
echo "Next steps:"
echo "1. Create repository on GitHub/GitLab (if not done)"
echo "2. Add remote: git remote add origin <URL>"
echo "3. Push: git push -u origin main"
echo "4. Add repository description and topics on GitHub/GitLab"
