#!/bin/bash

# 🚀 Quick Deploy Script for Telegram Monitor
# This script helps you push your code to GitHub for deployment

echo "🚀 TELEGRAM MONITOR - DEPLOYMENT PREPARATION"
echo "============================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📝 Initializing Git repository..."
    git init
    echo "✅ Git initialized"
else
    echo "✅ Git repository already exists"
fi

# Check if we have a remote
if ! git remote get-url origin > /dev/null 2>&1; then
    echo ""
    echo "⚠️  No GitHub remote found!"
    echo "📋 Please create a GitHub repository first:"
    echo "   1. Go to https://github.com/new"
    echo "   2. Create repository: 'telegram-monitor'"
    echo "   3. Run: git remote add origin https://github.com/yourusername/telegram-monitor.git"
    echo ""
    read -p "Have you created the GitHub repo and added remote? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Please create GitHub repository first"
        exit 1
    fi
fi

# Stage all files
echo "📦 Staging files for commit..."
git add .

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "ℹ️  No changes to commit"
else
    # Commit changes
    echo "💾 Committing changes..."
    git commit -m "🚀 Prepare for deployment

- Added Railway configuration (Procfile, railway.toml)
- Added CORS configuration for production
- Added MongoDB Atlas support
- Added deployment guides and scripts
- Updated file paths for Railway compatibility
- Added production environment template"

    echo "✅ Changes committed"
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
if git push -u origin main; then
    echo "✅ Code pushed to GitHub successfully!"
else
    echo "⚠️  Push failed. Trying 'master' branch..."
    if git push -u origin master; then
        echo "✅ Code pushed to GitHub successfully!"
    else
        echo "❌ Push failed. Please check your GitHub remote URL"
        exit 1
    fi
fi

echo ""
echo "🎉 SUCCESS! Your code is now on GitHub"
echo ""
echo "📋 NEXT STEPS:"
echo "1. ✅ Code pushed to GitHub"
echo "2. 🗄️  Set up MongoDB Atlas (see DEPLOYMENT_GUIDE.md)"
echo "3. 🚄 Deploy backend to Railway"
echo "4. 🌐 Deploy frontend to Vercel"
echo "5. ⚙️  Configure environment variables"
echo ""
echo "📖 Full instructions: /app/DEPLOYMENT_GUIDE.md"
echo ""
echo "🚀 Ready for deployment!"