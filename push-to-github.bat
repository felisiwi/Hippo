@echo off
echo Staging all files...
git add -A
echo.
echo Committing changes...
git commit -m "Add conversation splitter script and split conversation files"
echo.
echo Pushing to GitHub...
git push origin main
echo.
echo Done!
pause

