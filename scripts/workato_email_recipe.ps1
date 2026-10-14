# Creates (or updates) the "Reminder emails" recipe in the Workato sandbox project smart-health, through Workato's developer API.
# Reads the API token from the WORKATO_API_TOKEN user environment variable and never prints it.
#
#   powershell -File scripts/workato_email_recipe.ps1                 create the recipe (stopped)
#   powershell -File scripts/workato_email_recipe.ps1 -RecipeId 123   update that recipe (stop it first)
#
# The recipe (docs/specs/email-notifications.md, "Build the recipe in Workato"): a webhook receives one message per email (to, subject,
# html, text, ...) and the Gmail "Send email" step sends it as an HTML email from the connected Gmail account.
param([int]$RecipeId = 0, [int]$FolderId = 80758, [int]$GmailConnectionId = 47647)

$ErrorActionPreference = "Stop"
$token = [Environment]::GetEnvironmentVariable("WORKATO_API_TOKEN", "User")
if (-not $token) { throw "WORKATO_API_TOKEN is not set" }
$h = @{ Authorization = "Bearer $token" }
$base = "https://app.trial.workato.com/api"

$trg = "b1c2d3e4"
$mail = "f5a6b7c8"
function Pill($path) {
  $p = ($path -split "\." | ForEach-Object { '"' + $_ + '"' }) -join ","
  return '#{_dp(''{"pill_type":"output","provider":"workato_webhooks","line":"' + $trg + '","path":["payload",' + $p + ']}'')}'
}
function Field($name, $type) { return [ordered]@{ name = $name; label = $name; type = $type; control_type = "text" } }
$fields = @(
  (Field "to" "string"), (Field "toName" "string"), (Field "subject" "string"), (Field "preheader" "string"),
  (Field "text" "string"), (Field "html" "string"), (Field "idempotencyKey" "string"),
  [ordered]@{ name = "tags"; label = "tags"; type = "object"; properties = @((Field "kind" "string"), (Field "key" "string"), (Field "audience" "string")) }
)
$schemaJson = ConvertTo-Json -InputObject $fields -Depth 10 -Compress

$trigger = [ordered]@{
  number = 0; provider = "workato_webhooks"; name = "new_event"; as = $trg; keyword = "trigger"
  input = [ordered]@{ request = [ordered]@{ webhook_type = "json"; payload_schema = $schemaJson }; webhook_suffix = "smart-health-reminder-email" }
  extended_output_schema = @(
    [ordered]@{ label = "Headers"; name = "headers"; type = "object"; properties = @() },
    [ordered]@{ label = "Payload"; name = "payload"; type = "object"; properties = $fields }
  )
  uuid = [guid]::NewGuid().ToString()
}

$send = [ordered]@{
  number = 1; provider = "gmail"; name = "send_mail"; as = $mail; keyword = "action"
  input = [ordered]@{ email_type = "html"; to = (Pill "to"); subject = (Pill "subject"); body = (Pill "html") }
  uuid = [guid]::NewGuid().ToString()
}
$trigger["block"] = @($send)

$code = ConvertTo-Json -InputObject $trigger -Depth 40 -Compress
$config = ConvertTo-Json -InputObject @(
  [ordered]@{ keyword = "application"; name = "workato_webhooks"; provider = "workato_webhooks"; skip_validation = $false; account_id = $null },
  [ordered]@{ keyword = "application"; name = "gmail"; provider = "gmail"; skip_validation = $false; account_id = $GmailConnectionId }
) -Depth 5 -Compress

$body = ConvertTo-Json -Depth 6 -InputObject @{ recipe = @{ name = "Reminder emails"; description = "Sends one reminder email per message from the Equinox backend (docs/specs/email-notifications.md)."; code = $code; config = $config; folder_id = [string]$FolderId } }
if ($RecipeId -gt 0) {
  $r = Invoke-RestMethod -Method Put -Uri "$base/recipes/$RecipeId" -Headers $h -ContentType "application/json" -Body $body
} else {
  $r = Invoke-RestMethod -Method Post -Uri "$base/recipes" -Headers $h -ContentType "application/json" -Body $body
}
"recipe id: $($r.id) success: $($r.success)"
