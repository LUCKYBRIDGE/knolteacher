param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [string]$Path = "release/user-facing-notes.md"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path)) {
    throw "User-facing release notes file is missing: $Path"
}

$notes = (Get-Content -LiteralPath $Path -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($notes)) {
    throw "User-facing release notes must not be empty."
}

$expectedTitle = "놀티쳐 v$Version 업데이트"
if (-not $notes.StartsWith($expectedTitle, [System.StringComparison]::Ordinal)) {
    throw "User-facing release notes must start with '$expectedTitle'."
}

$developerTerms = @(
    '(?i)\bPR\s*#?\d+',
    '(?i)pull request',
    '(?i)\bcommit\b',
    '(?i)\bSHA-?256\b',
    '(?i)\bworkflow\b',
    '(?i)\bXAML\b',
    '(?i)\.cs\b',
    '(?i)\brefactor(?:ing)?\b',
    '리팩터링',
    '커밋',
    '풀 리퀘스트',
    '내부 구현'
)

foreach ($pattern in $developerTerms) {
    if ($notes -match $pattern) {
        throw "User-facing release notes contain developer-oriented wording matching: $pattern"
    }
}

$designImitationTerms = @(
    '디자인.{0,12}(따라|모방|카피|복제)',
    '(따라|모방|카피|복제).{0,12}디자인',
    '디자인.{0,12}참고(?:했|한|하여|해서)',
    '(?i)inspired by',
    '(?i)based on.{0,30}design',
    '(?i)clone of'
)

foreach ($pattern in $designImitationTerms) {
    if ($notes -match $pattern) {
        throw "User-facing release notes must not describe design imitation or design-source references."
    }
}

$bulletCount = ([regex]::Matches($notes, '(?m)^[-•]\s+')).Count
if ($bulletCount -lt 2) {
    throw "User-facing release notes should contain at least two concise user-facing bullet points."
}

if ($notes.Length -gt 5000) {
    throw "User-facing release notes are too long for the in-app update dialog. Keep them concise."
}

Write-Host "User-facing release notes validated for v$Version ($bulletCount bullet points)."
