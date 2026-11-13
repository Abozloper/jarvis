# Jarvis Windows master installer

Use the Jarvis Windows Master Installer release on Windows x64. Close any running Jervis or Jarvis from the system tray before installing. Run the single setup executable. It includes the managed CPU Ollama runtime, Qwen2.5 1.5B, and English Whisper. Speech output uses an installed Windows system voice.

After installation, allow microphone access for desktop apps if Windows has it disabled. Say **Hey Jarvis**, wait for the greeting, then say **Explain why the sky is blue in one sentence**. The response should appear on screen and play aloud. This also works with Wi-Fi off.

- **Remember that I promised to call Dan Friday** saves a note.
- **Give me my daily brief** reads the five newest notes.
- **Draft lead follow-ups** uses the sample inbox or exported text files and saves drafts for review. It does not send email.

Use `%APPDATA%\Jarvis\Pilot` for sample inputs and draft output. If something stops, collect `window.log`, `crash.log` (if present), and `ollama.log` from the app's `logs` folder. The prior Jervis build may have stored data in `%APPDATA%\Jervis`.

The master package targets English voice and local text workflows. Connected services and optional model features have their own setup or network requirements.

## Business operations

Put a UTF-8 JSON array in `%APPDATA%\Jarvis\Pilot\Data\jobs.json`. Each job needs a unique `id`, `title`, and `status`. Optional fields are `due` (YYYY-MM-DD), `blocker`, `evidence`, `owner`, and `next_step`. Example:

```json
[{"id":"J-17","title":"Equipment install","status":"delayed","due":"2026-11-12","blocker":"Part on backorder","evidence":"Vendor confirmed the backorder on Nov 12","owner":"Sam","next_step":"Confirm the replacement date"}]
```

Say “Brief me on today's operations,” “Open the delayed job J-17,” then “Draft the customer update and an internal follow-up task.” Review the preview and say “Approve drafts for job J-17” to save both to the local Pilot/Approved folder.
