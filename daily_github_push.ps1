# This script picks 3 files that haven't been pushed to GitHub yet, commits them, and pushes them.

# 1. Get the status of files in the git repository
$gitStatus = git status --porcelain -uall

# 2. Check if there is anything left to push
if (-not $gitStatus) {
    Write-Host "Success: Everything is up to date! All files have been pushed to GitHub." -ForegroundColor Green
    exit
}

# 3. Get the first 3 files from the list
$filesToPush = $gitStatus | Select-Object -First 3

Write-Host "Adding the following 3 files for today's contribution:" -ForegroundColor Cyan
foreach ($line in $filesToPush) {
    # Extract the file path (ignoring the first 3 characters which are status codes like '?? ' or ' M ')
    $filePath = $line.Substring(3).Trim()
    Write-Host "- $filePath" -ForegroundColor Yellow
    
    # Put the file path in quotes in case there are spaces
    git add "`"$filePath`""
}

# 4. Commit and push
Write-Host "`nCommitting to GitHub..." -ForegroundColor Cyan
git commit -m "Daily project progress update"

Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
git push -u origin main

Write-Host "`nDone! You've got your GitHub green square for today!" -ForegroundColor Green

