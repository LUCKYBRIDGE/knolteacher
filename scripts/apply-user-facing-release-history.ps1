param(
    [string]$Path = "release/public-release-history.json",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path)) {
    throw "Release history manifest is missing: $Path"
}

$entries = @(Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
if ($entries.Count -eq 0) {
    throw "Release history manifest is empty."
}

$seen = @{}
$forbiddenPatterns = @(
    '(?i)\bPR\s*#?\d+',
    '(?i)pull request',
    '(?i)\bcommit\b',
    '(?i)\bSHA-?256\b',
    '(?i)\bworkflow\b',
    '(?i)\bXAML\b',
    '(?i)\brefactor(?:ing)?\b',
    '(?i)\bSSOT\b',
    '(?i)\blifecycle\b',
    '(?i)\bConfigService\b',
    '(?i)\bWidgetRegistry\b',
    '리팩터링',
    '커밋',
    '풀 리퀘스트',
    '내부 구현',
    '스타일',
    '따라했',
    '따라한',
    '따라 하',
    '참고했',
    '참고한',
    '모방',
    '카피',
    '(?i)inspired by',
    '(?i)based on.{0,30}design',
    '(?i)clone of'
)

foreach ($entry in $entries) {
    $tag = [string]$entry.tag
    $title = [string]$entry.title
    $body = [string]$entry.body

    if ($tag -notmatch '^v\d+\.\d+\.\d+$') {
        throw "Invalid release tag in history manifest: '$tag'"
    }
    if ($seen.ContainsKey($tag)) {
        throw "Duplicate release tag in history manifest: '$tag'"
    }
    $seen[$tag] = $true

    $expectedTitle = "놀티쳐 $tag 업데이트"
    if ($title -ne $expectedTitle) {
        throw "Release '$tag' title must be exactly '$expectedTitle'."
    }
    if ([string]::IsNullOrWhiteSpace($body) -or -not $body.StartsWith($expectedTitle, [System.StringComparison]::Ordinal)) {
        throw "Release '$tag' body must begin with its user-facing title."
    }

    $bulletCount = ([regex]::Matches($body, '(?m)^[-•]\s+')).Count
    if ($bulletCount -lt 2) {
        throw "Release '$tag' must contain at least two user-facing bullet points."
    }

    foreach ($pattern in $forbiddenPatterns) {
        if ($title -match $pattern -or $body -match $pattern) {
            throw "Release '$tag' contains developer-oriented or imitation wording matching: $pattern"
        }
    }
}

Write-Host "Validated $($entries.Count) user-facing historical release entries."

if (-not $Apply) {
    $global:LASTEXITCODE = 0
    return
}

if ([string]::IsNullOrWhiteSpace($env:GH_TOKEN) -or [string]::IsNullOrWhiteSpace($env:GITHUB_REPOSITORY)) {
    throw "GH_TOKEN and GITHUB_REPOSITORY are required to apply release history."
}

$published = @(gh api "repos/$env:GITHUB_REPOSITORY/releases?per_page=100" | ConvertFrom-Json | Where-Object { $_.draft -ne $true })
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list existing GitHub Releases."
}

$publishedTags = @($published | ForEach-Object { [string]$_.tag_name })
$missingFromManifest = @($publishedTags | Where-Object { -not $seen.ContainsKey($_) })
$missingOnGitHub = @($entries | Where-Object { $_.tag -notin $publishedTags } | ForEach-Object { [string]$_.tag })
if ($missingFromManifest.Count -gt 0) {
    throw "Published releases missing from manifest: $($missingFromManifest -join ', ')"
}
if ($missingOnGitHub.Count -gt 0) {
    throw "Manifest releases missing on GitHub: $($missingOnGitHub -join ', ')"
}

foreach ($entry in $entries) {
    $tag = [string]$entry.tag
    $release = gh api "repos/$env:GITHUB_REPOSITORY/releases/tags/$tag" | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $null -eq $release.id) {
        throw "Unable to resolve published release '$tag'."
    }
    if ($release.draft -eq $true) {
        throw "Refusing to rewrite draft release '$tag'."
    }

    $payload = @{
        name = [string]$entry.title
        body = [string]$entry.body
    } | ConvertTo-Json -Compress

    $payload | gh api --method PATCH "repos/$env:GITHUB_REPOSITORY/releases/$($release.id)" --input - | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to rewrite release '$tag'."
    }

    $verified = gh api "repos/$env:GITHUB_REPOSITORY/releases/$($release.id)" | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $verified.name -ne [string]$entry.title -or $verified.body -ne [string]$entry.body) {
        throw "Release '$tag' did not match the requested user-facing title/body after update."
    }
    Write-Host "Updated release: $tag"
}

$global:LASTEXITCODE = 0
Write-Host "Rewrote $($entries.Count) published releases without changing tags or assets."
