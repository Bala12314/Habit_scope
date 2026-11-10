# Uploading this project to GitHub

## Option A: command line
```bash
cd lifelens
git init -b main
git config user.name "Abhishek Kaushal"
git config user.email "<your GitHub email or noreply address>"
git add -A && git commit -m "Initial commit: LifeLens"
# create an EMPTY repo named lifelens on github.com first, then:
git remote add origin https://github.com/<your-username>/lifelens.git
git push -u origin main
```

## Option B: website only
1. github.com -> **New repository** -> name `lifelens` (no README/license, they're included).
2. **uploading an existing file** -> drag in everything from the unzipped folder (including the hidden `.github` folder and `.gitignore`) -> Commit.

After pushing, the **tests** badge in the README starts working. Fix the badge links if your repo isn't named `lifelens`.
