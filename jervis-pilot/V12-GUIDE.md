# Jarvis v12
Close Jarvis from the system tray before upgrading. This unsigned Windows x64 pilot uses the existing CPU Qwen2.5 1.5B model, Whisper base.en and Windows speech voice.

Say **What can you do?** to see commands and the exact Data folder on your computer.

## Local documents
Add TXT, Markdown, CSV, JSON, text PDFs or DOCX files to the Data folder. Subfolders are supported. Ask **What do my files say about supplier delivery?**
Answers include numbered file, page or paragraph references. A persistent local SQLite index refreshes changed files and removes deleted files on the next query. It does not upload documents. File matching uses full-text retrieval, not semantic embeddings.

Limits: up to 500 files in 200 traversed directories, 6 MB per file, 60 PDF pages, 262,144 characters per plain-text file, 1,200 chunks per document and six retrieved excerpts. Images and scanned PDFs need OCR before import. Protected or unreadable documents are reported. First indexing may take longer than subsequent searches.

## CSV analysis
Use exact column names and put the CSV directly in Data.
- Analyze sales.csv
- Total Amount in sales.csv by Region
- Average Amount in sales.csv
- Count rows in sales.csv
- Max Amount in sales.csv

Calculations use decimal arithmetic, with a 10,000-record limit and up to 100 groups. Blank and nonnumeric values are excluded and counted. Numeric formats supported are plain decimal numbers and US-style comma-grouped thousands. Currency symbols and locale-dependent decimals need normalization. Average division uses Python Decimal precision.

## Public research
- Search the web for upcoming events in Tampa
- Find information about warehouse scheduling
- Compare my documents about valve deliveries with web research about public supplier lead times

The comparison command returns two labeled evidence sections. Only the public query after “web research about” is sent to search. Search still uses public result excerpts, not exhaustive page reading. Next-month and this-month queries resolve to calendar dates. Internet access is required for current public research. Saved research retains source links and dates through the existing local memory workflow.

## Business workflow
Operations still require Data/jobs.json with records containing id, title and status. Optional fields are due (YYYY-MM-DD), blocker, evidence, owner, next_step and public_query.
- What needs my attention today?
- Open job J-17
- Why is it delayed?
- Draft an update
- Approve drafts for job J-17
- Cancel drafts

Drafts are saved locally after approval. They are not emailed or written to a CRM. If jobs.json changes after drafting, approval is refused until the draft is regenerated. An optional public_query is sent online during the relevant workflow, so use only terms intended for public search.

## What this does not add
No new neural voice, larger reasoning model, OCR, live CRM connector, autonomous email sending or unrestricted computer control is added by this update. Model-generated prose still needs source verification for consequential decisions. Hindsight memory models and database binaries download automatically on first use.
