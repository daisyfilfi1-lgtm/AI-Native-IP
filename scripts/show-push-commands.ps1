# Prints the exact git commands for this repo — no magic, no wrong remote.
# Usage: .\scripts\show-push-commands.ps1
# After you commit, run the lines that match what you changed.

$branch = git branch --show-current 2>$null
if (-not $branch) { $branch = "<your-branch>" }

Write-Host ""
Write-Host "=== AI-Native IP — push map (read once, copy what you need) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1) Monorepo integration branch (GitHub backup / PR):" -ForegroundColor Yellow
Write-Host "   git push origin $branch"
Write-Host ""
Write-Host "2) Netlify (repo: ai-native-ip-frontend, branch: main):" -ForegroundColor Yellow
Write-Host "   git push frontend ${branch}:main"
Write-Host ""
Write-Host "3) Railway backend (repo: AI-Native-IP, branch: main — typical):" -ForegroundColor Yellow
Write-Host "   # Backend lives under backend/; main must contain those commits."
Write-Host "   git checkout main && git pull origin main"
Write-Host "   # Then bring backend changes: merge, cherry-pick, or:"
Write-Host "   #   git checkout $branch -- backend/app/routers/creator.py"
Write-Host "   git add backend && git commit -m \"...\" && git push origin main"
Write-Host "   git checkout $branch"
Write-Host ""
Write-Host "Current branch: $branch" -ForegroundColor Green
Write-Host ""
