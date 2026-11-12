# Jervis Windows pilot

Built from TheJarvis-App/jarvis-app v1.0.5. Use the Jervis Windows pilot workflow artifact, extract it, and run Jervis Setup.exe. Initial model setup needs internet access. Keep the upstream default local model and English voice for this pilot.

Wake Jervis first, then say:
- Remember that I promised to call Dan Friday.
- Give me my daily brief.
- Draft lead follow-ups.

The brief reads the five most recent notes. Lead drafting creates sample inputs on first use. Edit inbox.txt and company-notes.txt under %APPDATA%\Jervis\Pilot to try your own exported text. The last successful draft is saved to lead-drafts.txt there. No mailbox is connected. Jervis does not send these drafts.
