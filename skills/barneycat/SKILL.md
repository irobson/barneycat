---
name: barneycat
description: Read a meeting recording and deliver a report of what was discussed and what needs to be done. Use when the user gives a path to a meeting recording, a call or a video and asks to read, review, summarize, transcribe or pull the actions from it, or mentions barneycat. Also in Portuguese: "olha essa reunião", "lê essa gravação", "resume essa call", "quais as ações dessa reunião", "usa o barneycat". Works in the middle of other tasks, tying the meeting to the work at hand.
---

# BarneyCat

The script does the heavy lifting and interprets nothing. You read what it produces and write the report, using what you already know about the task at hand.

The user always gives the path. Never go looking for recordings.

## 1. Prepare

`uv` is the only prerequisite. If it is missing, ask the user to install it:

- macOS and Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

Run this in the background, because a long meeting takes minutes and the first run downloads models. Tell the user it started.

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/barneycat.py" prepare "<path>"
```

Flags:

- `--language pt`: set it when you know the language. Otherwise the engine detects it.
- `--glossary <name>`: a file in `~/.barneycat/glossaries`. Use it when one matches the project.
- `--engine`, `--model`: override the engine picked for this machine.
- `--out <folder>`: output folder, by default `<recording>.barneycat` next to the file.
- `--no-frames`, `--no-diarize`, `--force`.

If `${CLAUDE_PLUGIN_ROOT}` is not resolved in your shell, use the path two folders above this skill's base directory.

The command prints a JSON summary and resumes from cache if interrupted. Report anything under `warnings`.

## 2. Read

Read `transcript.md` from start to end. Each line carries a stamp and, usually, a speaker. Lines with `(frame: frames/...)` mark what was on screen at that moment.

Machine transcripts get names and technical terms wrong. Fix obvious errors from context when quoting and say the quote was adjusted.

Open only the frames that matter: a change of topic, speech like "here on the screen", or anything the transcript leaves unclear. Read them with your image tool, no OCR needed.

Name the speakers from the evidence: the active speaker highlight, names on the call, someone being addressed by name. Without evidence, keep `Speaker N`. A single real person can be split into two labels, or two people merged into one. Trust what you see over the label.

## 3. Check the history

If `reports_dir` is set in the summary, read the open actions in the `actions.json` files there and the latest reports of the same series. Note what this meeting answered. If it is not set, skip this step.

## 4. Write

Write `report.md` and `actions.json` in the output folder, following [report-template.md](report-template.md). Use the language of the conversation and keep quotes in their original language.

**Evidence is mandatory.** Every action and every important claim carries a stamp and a quote. Mark anything without a direct source as inference. Never invent a timestamp, a name or a deadline. If something is unclear, write that it is unclear.

`user.name` in the summary says who "you" is. Without it, write the "For you" section in general terms.

If `reports_dir` is set, copy `report.md` and `actions.json` there as `<date>-<short-topic>.md` and `<date>-<short-topic>.json`.

## 5. Deliver

Generate the PDF:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/barneycat.py" pdf "<output folder>"
```

Then answer in the conversation with what changes for the work at hand, the actions that fall to the user, and the path of the report. Do not paste the whole report.

Do not create tickets or send messages on your own. Offer it if it fits.

## Privacy

The recording and the audio stay on the machine. The transcript and the frames you open reach the model provider, as in any conversation. If the user worries about a recording, say so before reading it.
