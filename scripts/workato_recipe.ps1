# Creates or updates the "Medicine calendar reminders" recipe in the Workato sandbox project smart-health, through Workato's developer API
# (AIRO MCP is not enabled on the sandbox). Reads the API token from the WORKATO_API_TOKEN user environment variable and never prints it.
#
#   powershell -File scripts/workato_recipe.ps1                 create the recipe (stopped)
#   powershell -File scripts/workato_recipe.ps1 -RecipeId 123   update that recipe (stop it first)
#
# The recipe: a webhook receives one message per dose time (docs/specs/f4-calendar.md section 3) and calls Google Calendar's own
# "insert event" API through Workato's custom action, so the event can repeat every day and remind exactly at the dose time.
param([int]$RecipeId = 0, [int]$FolderId = 80758, [int]$ConnectionId = 46835, [string]$Step = "custom")

$ErrorActionPreference = "Stop"
$token = [Environment]::GetEnvironmentVariable("WORKATO_API_TOKEN", "User")
if (-not $token) { throw "WORKATO_API_TOKEN is not set" }
$h = @{ Authorization = "Bearer $token" }
$base = "https://app.trial.workato.com/api"

$trg = "a1b2c3d4"
$evt = "e5f6a7b8"
function Pill($path) {
  $p = ($path -split "\." | ForEach-Object { '"' + $_ + '"' }) -join ","
  return '#{_dp(''{"pill_type":"output","provider":"workato_webhooks","line":"' + $trg + '","path":["payload",' + $p + ']}'')}'
}
function Field($name, $type) { return [ordered]@{ name = $name; label = $name; type = $type; control_type = "text" } }
$when = @((Field "dateTime" "string"), (Field "timeZone" "string"))
$fields = @(
  (Field "request_id" "string"), (Field "source" "string"), (Field "schedule_id" "string"), (Field "time" "string"), (Field "event_id" "string"),
  (Field "summary" "string"), (Field "description" "string"),
  [ordered]@{ name = "start"; label = "start"; type = "object"; properties = $when },
  [ordered]@{ name = "end"; label = "end"; type = "object"; properties = $when },
  [ordered]@{ name = "recurrence"; label = "recurrence"; type = "array"; of = "string" },
  [ordered]@{ name = "reminders"; label = "reminders"; type = "object"; properties = @(
      [ordered]@{ name = "useDefault"; label = "useDefault"; type = "boolean"; control_type = "checkbox" },
      [ordered]@{ name = "overrides"; label = "overrides"; type = "array"; of = "object"; properties = @((Field "method" "string"), [ordered]@{ name = "minutes"; label = "minutes"; type = "integer"; control_type = "integer" }) }) }
)
$schemaJson = ConvertTo-Json -InputObject $fields -Depth 10 -Compress

$trigger = [ordered]@{
  number = 0; provider = "workato_webhooks"; name = "new_event"; as = $trg; keyword = "trigger"
  input = [ordered]@{ request = [ordered]@{ webhook_type = "json"; payload_schema = $schemaJson }; webhook_suffix = "smart-health-medicine-reminder" }
  extended_output_schema = @(
    [ordered]@{ label = "Headers"; name = "headers"; type = "object"; properties = @() },
    [ordered]@{ label = "Payload"; name = "payload"; type = "object"; properties = $fields }
  )
  uuid = [guid]::NewGuid().ToString()
}

$bodySchema = '[{"name":"id","type":"string"},{"name":"summary","type":"string"},{"name":"description","type":"string"},{"name":"start","type":"object","properties":[{"name":"dateTime","type":"string"},{"name":"timeZone","type":"string"}]},{"name":"end","type":"object","properties":[{"name":"dateTime","type":"string"},{"name":"timeZone","type":"string"}]},{"name":"recurrence","type":"array","of":"string"},{"name":"reminders","type":"object","properties":[{"name":"useDefault","type":"boolean"},{"name":"overrides","type":"array","of":"object","properties":[{"name":"method","type":"string"},{"name":"minutes","type":"integer"}]}]}]'
$outSchema = '[{"name":"id","type":"string"},{"name":"htmlLink","type":"string"},{"name":"status","type":"string"},{"name":"summary","type":"string"},{"name":"recurrence","type":"array","of":"string"},{"name":"reminders","type":"object","properties":[{"name":"useDefault","type":"boolean"},{"name":"overrides","type":"array","of":"object","properties":[{"name":"method","type":"string"},{"name":"minutes","type":"integer"}]}]}]'

$create = [ordered]@{
  number = 1; provider = "google_calendar"; name = "__adhoc_http_action"; as = $evt; keyword = "action"
  input = [ordered]@{
    mnemonic = "Create repeating event"; verb = "post"; action_name = "Create repeating event"
    path = "/calendar/v3/calendars/primary/events"; request_type = "json"; response_type = "json"
    input = [ordered]@{
      schema = $bodySchema
      id = (Pill "event_id"); summary = (Pill "summary"); description = (Pill "description")
      start = (Pill "start"); end = (Pill "end"); recurrence = (Pill "recurrence"); reminders = (Pill "reminders")
    }
    output = $outSchema
  }
  uuid = [guid]::NewGuid().ToString()
}
if ($Step -eq "standard") {
  # Workato's own "Create event" step (the field names come from the connector; see the notes in docs/specs/f4-calendar.md)
  $create = [ordered]@{
    number = 1; provider = "google_calendar"; name = "create_event"; as = $evt; keyword = "action"
    dynamicPickListSelection = @{ id = "primary" }
    toggleCfg = @{ sendNotifications = $true }
    input = [ordered]@{
      sendNotifications = "false"; calendar_name = "primary"
      summary = (Pill "summary"); description = (Pill "description")
      start = (Pill "start.dateTime"); end_time_new = (Pill "end.dateTime")
      recurrence = (Pill "recurrence.0")
    }
    uuid = [guid]::NewGuid().ToString()
  }
}
$trigger["block"] = @($create)

$code = ConvertTo-Json -InputObject $trigger -Depth 40 -Compress
$config = ConvertTo-Json -InputObject @(
  [ordered]@{ keyword = "application"; name = "workato_webhooks"; provider = "workato_webhooks"; skip_validation = $false; account_id = $null },
  [ordered]@{ keyword = "application"; name = "google_calendar"; provider = "google_calendar"; skip_validation = $false; account_id = $ConnectionId }
) -Depth 5 -Compress

$body = ConvertTo-Json -Depth 6 -InputObject @{ recipe = @{ name = "Medicine calendar reminders"; description = "Adds one repeating Google Calendar event per medicine dose time. Called by the Smart Health backend (docs/specs/f4-calendar.md)."; code = $code; config = $config; folder_id = [string]$FolderId } }
if ($RecipeId -gt 0) {
  $r = Invoke-RestMethod -Method Put -Uri "$base/recipes/$RecipeId" -Headers $h -ContentType "application/json" -Body $body
} else {
  $r = Invoke-RestMethod -Method Post -Uri "$base/recipes" -Headers $h -ContentType "application/json" -Body $body
}
"recipe id: $($r.id) success: $($r.success)"
