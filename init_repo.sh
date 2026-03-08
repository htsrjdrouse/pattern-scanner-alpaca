#!/bin/bash
# Initialize git repository for pattern_scanner_alpaca

cd /Users/richard/Documents/stocks/pattern_scanner_alpaca

# Initialize git if not already done
if [ ! -d .git ]; then
    git init
    echo "✓ Initialized git repository"
fi

# Add all files
git add .

# Commit with the prepared message
git commit -F COMMIT_MESSAGE.txt

echo ""
echo "✓ Repository initialized and committed"
echo ""
echo "Next steps:"
echo "1. Create a new repository on GitHub"
echo "2. Run: git remote add origin <your-github-url>"
echo "3. Run: git push -u origin main"
echo ""
echo "Example:"
echo "  git remote add origin https://github.com/yourusername/pattern-scanner-alpaca.git"
echo "  git branch -M main"
echo "  git push -u origin main"
