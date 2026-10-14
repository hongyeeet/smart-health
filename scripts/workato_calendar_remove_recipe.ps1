# Creates (or updates) the "Medicine calendar remove" recipe in the Workato sandbox project smart-health, through Workato's developer API.
# Reads the API token from the WORKATO_API_TOKEN user environment variable and never prints it.
#
#   powershell -File scripts/workato_calendar_remove_recipe.ps1                 create the recipe (stopped)
#   powershell -File scripts/workato_calendar_remove_recipe.ps1 -RecipeId 123   update that recipe (stop it first)
#
# The recipe: a webhook receives one message per event to remove (summary, start, end). The Google Calendar "Search events" step finds the
# events whose name matches and that start inside [start, end]; "For each" of them, "Delete event" removes it. The app only ever sends the
# exact title and time window of one dose, so nothing else on the calendar is touched. Used when a medicine is removed or a dose time
# (or the learned time) changes (docs/specs/f4-calendar.md).
param([int]$RecipeId = 0, [int]$FolderId = 80758, [int]$CalendarConnectionId = 46835, [string]$Suffix = "smart-health-medicine-reminder-remove")

$ErrorActionPreference = "Stop"
$token = [Environment]::GetEnvironmentVariable("WORKATO_API_TOKEN", "User")
if (-not $token) { throw "WORKATO_API_TOKEN is not set" }
$h = @{ Authorization = "Bearer $token" }
$base = "https://app.trial.workato.com/api"

$trg = "c1d2e3f4"
$find = "d5e6f7a8"
$loop = "e9f0a1b2"
$del = "f3a4b5c6"
function Pill($line, $provider, $path) {
  $p = ($path -split "\." | ForEach-Object { '"' + $_ + '"' }) -join ","
  return '#{_dp(''{"pill_type":"output","provider":"' + $provider + '","line":"' + $line + '","path":[' + $p + ']}'')}'
}
function Field($name, $type) { return [ordered]@{ name = $name; label = $name; type = $type; control_type = "text" } }
$when = @((Field "dateTime" "string"), (Field "timeZone" "string"))
$fields = @(
  (Field "request_id" "string"), (Field "source" "string"), (Field "summary" "string"),
  [ordered]@{ name = "start"; label = "start"; type = "object"; properties = $when },
  [ordered]@{ name = "end"; label = "end"; type = "object"; properties = $when }
)
$schemaJson = ConvertTo-Json -InputObject $fields -Depth 10 -Compress

$trigger = [ordered]@{
  number = 0; provider = "workato_webhooks"; name = "new_event"; as = $trg; keyword = "trigger"
  input = [ordered]@{ request = [ordered]@{ webhook_type = "json"; payload_schema = $schemaJson }; webhook_suffix = $Suffix }
  extended_output_schema = @(
    [ordered]@{ label = "Headers"; name = "headers"; type = "object"; properties = @() },
    [ordered]@{ label = "Payload"; name = "payload"; type = "object"; properties = $fields }
  )
  uuid = [guid]::NewGuid().ToString()
}

$search = [ordered]@{
  number = 1; provider = "google_calendar"; name = "search_events"; as = $find; keyword = "action"
  dynamicPickListSelection = [ordered]@{ id = "primary" }
  input = [ordered]@{
    calendar_name = "primary"
    q = (Pill $trg "workato_webhooks" "payload.summary")
    timeMin = (Pill $trg "workato_webhooks" "payload.start.dateTime")
    timeMax = (Pill $trg "workato_webhooks" "payload.end.dateTime")
  }
  uuid = [guid]::NewGuid().ToString()
}

$delete = [ordered]@{
  number = 3; provider = "google_calendar"; name = "delete_event"; as = $del; keyword = "action"
  dynamicPickListSelection = [ordered]@{ id = "primary" }
  input = [ordered]@{
    calendar_name = "primary"
    event_id = ('#{_dp(''{"pill_type":"output","provider":"google_calendar","line":"' + $find + '","path":["events",{"path_element_type":"current_item"},"id"]}'')}')
  }
  uuid = [guid]::NewGuid().ToString()
}

$foreach = [ordered]@{
  number = 2; as = $loop; keyword = "foreach"
  repeat_mode = "simple"; clear_scope = "false"
  source = (Pill $find "google_calendar" "events")
  input = [ordered]@{}
  block = @($delete)
  uuid = [guid]::NewGuid().ToString()
}

$trigger["block"] = @($search, $foreach)

$code = ConvertTo-Json -InputObject $trigger -Depth 40 -Compress
$config = ConvertTo-Json -InputObject @(
  [ordered]@{ keyword = "application"; name = "workato_webhooks"; provider = "workato_webhooks"; skip_validation = $false; account_id = $null },
  [ordered]@{ keyword = "application"; name = "google_calendar"; provider = "google_calendar"; skip_validation = $false; account_id = $CalendarConnectionId }
) -Depth 5 -Compress

$body = ConvertTo-Json -Depth 6 -InputObject @{ recipe = @{ name = "Medicine calendar remove"; description = "Removes one dose's event from the shared Google Calendar (title and time window from the Equinox backend)."; code = $code; config = $config; folder_id = [string]$FolderId } }
if ($RecipeId -gt 0) {
  $r = Invoke-RestMethod -Method Put -Uri "$base/recipes/$RecipeId" -Headers $h -ContentType "application/json" -Body $body
} else {
  $r = Invoke-RestMethod -Method Post -Uri "$base/recipes" -Headers $h -ContentType "application/json" -Body $body
}
"recipe id: $($r.id) success: $($r.success)"
