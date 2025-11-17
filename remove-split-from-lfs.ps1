# Remove split files from LFS and re-add as regular files

Write-Host "Removing split files from LFS cache..."

# Remove from LFS cache
git rm --cached data-export/chatgpt-export/split/3-6-months.json
git rm --cached data-export/chatgpt-export/split/6-12-months.json
git rm --cached data-export/chatgpt-export/split/last-3-months.json
git rm --cached data-export/chatgpt-export/split/older.json

git rm --cached data-export/claude-export/split/3-6-months.json
git rm --cached data-export/claude-export/split/6-12-months.json
git rm --cached data-export/claude-export/split/last-3-months.json
git rm --cached data-export/claude-export/split/older.json

Write-Host "Re-adding split files as regular files..."

# Re-add as regular files
git add data-export/chatgpt-export/split/3-6-months.json
git add data-export/chatgpt-export/split/6-12-months.json
git add data-export/chatgpt-export/split/last-3-months.json
git add data-export/chatgpt-export/split/older.json

git add data-export/claude-export/split/3-6-months.json
git add data-export/claude-export/split/6-12-months.json
git add data-export/claude-export/split/last-3-months.json
git add data-export/claude-export/split/older.json

Write-Host "Staging .gitattributes..."
git add .gitattributes

Write-Host "Committing changes..."
git commit -m "Remove split files from LFS"

Write-Host "Pushing to GitHub..."
git push origin main

Write-Host "Done!"

