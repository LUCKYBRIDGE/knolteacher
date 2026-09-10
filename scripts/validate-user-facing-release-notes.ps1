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

# Public update notes should describe KnolTeacher itself, not point to an external
# product, web page, or implementation lineage as the basis of a change.
$externalReferencePatterns = @(
    '(?i)https?://',
    '(?i)\bwww\.',
    '(?i)\b[a-z0-9-]+\.(com|net|org|io|kr)\b',
    '외부 (제품|서비스).{0,30}(구현 출처|유사성|비교 기준)'
)

foreach ($pattern in $externalReferencePatterns) {
    if ($notes -match $pattern) {
        throw "User-facing release notes must describe KnolTeacher itself without external product or source references."
    }
}

$bulletCount = ([regex]::Matches($notes, '(?m)^[-•]\s+')).Count
if ($bulletCount -lt 2) {
    throw "User-facing release notes should contain at least two concise user-facing bullet points."
}

if ($notes.Length -gt 5000) {
    throw "User-facing release notes are too long for the in-app update dialog. Keep them concise."
}

# External commands executed before this script can leave a non-zero LASTEXITCODE in the
# shared PowerShell runspace. A successful validation must explicitly clear that stale state.
$global:LASTEXITCODE = 0
Write-Host "User-facing release notes validated for v$Version ($bulletCount bullet points)."
