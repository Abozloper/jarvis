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

## Online business research

Add an optional `public_query` string to each job, for example `"public_query": "Acme pump X100 availability"`. Use public supplier names, product identifiers or city-level weather queries. Jarvis automatically searches this query during the operations briefing, investigation and draft preparation, and includes source links in the preview and approved local output. Search queries are sent to DuckDuckGo. Other job fields remain local. Search excerpts provide external context and do not establish the cause of a private job delay. Internet access is required. Without a public query, the job uses local evidence. Questions asking for latest/current public information also route to web search.

## Hindsight memory in v10

The installer includes Hindsight 1.2.1 and its own Python runtime. On first use, remain connected to the internet while Hindsight automatically downloads its embedding model, reranker and embedded database binaries. Ask "memory status" to see progress.

Successful web research is saved immediately in `Pilot/Memory/research.sqlite3`, including the question, answer, source links and retrieval date. A background worker indexes the saved research in Hindsight and retries failed ingestion. The Hindsight database persists in the Windows user's default Hindsight data directory. Original research remains in the SQLite archive even while indexing is pending.

Ask "search my memory for [topic]", "recall research about [topic]" or "what do you remember about [topic]". Relevant Hindsight facts are also supplied to ordinary conversational answers. Stored facts can become outdated. Current-information questions continue to use web search.

Hindsight runs on this PC and uses the bundled Ollama model. First-time indexing can compete with conversation for CPU resources. Close Jarvis from the tray before upgrades. The memory service listens on loopback port 8899. Startup diagnostics are in `Pilot/Memory/hindsight.log`. Restart Jarvis to retry a failed startup.
