---
description: "Fix the OpenWeather geocoding ingestion flow"
name: "Fix geocoding ingestion"
argument-hint: "Target files, API endpoint, and expected payload contract"
agent: "agent"
---
Review the ingestion pipeline and ensure the geocoding flow matches the OpenWeather Geocoding API contract.

Requirements:
- Inspect the extractor, validator, transformer, and main pipeline entry points for stale source assumptions.
- Update the API calls to the geocoding endpoint and align the function signature with the real call pattern in the app.
- Validate the geocoding payload shape and ensure this data is transformed into the expected record format.
- Keep the fix minimal and focused on the active ingestion path.
- Use the smallest relevant test command to confirm the fix and show the exact pass/fail evidence.

Output:
- Summarize the root cause and each code change.
- Include the verification command and the result.
- Note any remaining cleanup that is outside the active ingestion path.
