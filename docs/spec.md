# BarneyCat: v1 spec

A Claude Code plugin that reads a meeting recording and delivers a consolidated report of what was discussed and what needs to be done.

## Goal

An agent already working on something else gets a request like "look at this meeting using barneycat: `<path>`". It runs BarneyCat and answers with the context of the conversation it is in. The same install works on macOS, Windows and Linux.

## Decisions

| Topic | Decision |
| --- | --- |
| Input | A file path, always explicit. The plugin does not look for recordings. |
| Typical format | A TedCat recording, but any video or audio that ffmpeg reads is accepted. |
| Transcription | Local only in v1. No cloud code. The engine sits behind an interface, so others can be added later. |
| Report | Written by the agent that called the plugin, with no API key. |
| Repository | Public, `irobson/barneycat`, with no personal data. |
| Language | Code and docs in English. |

## Division of work

The script does the heavy lifting and interprets nothing. The agent reads the result and writes the report. This way the report uses what the agent already knows about the task at hand, and the plugin needs no LLM integration of its own.

## Repository layout

```text
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
skills/barneycat/SKILL.md            instructions and triggers, in English and Portuguese
skills/barneycat/report-template.md  report structure
scripts/barneycat.py                 entry point, inline dependencies (PEP 723)
scripts/engines/                     one module per transcription engine
tests/                               synthetic audio only
assets/logo.png
```

Install:

```bash
claude plugin marketplace add irobson/barneycat
claude plugin install barneycat@barneycat
```

## Pipeline

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/barneycat.py" prepare "<path>" [--language pt] [--glossary <name>] [--engine auto] [--force]
```

1. **Inspect.** Reads the file's duration and tracks. If the name follows `TedCat YYYY-MM-DD at HH.MM.SS`, it extracts the start time. TedCat uses the same format on Mac and Windows.
2. **Audio.** Extracts a 16 kHz mono WAV.
3. **Transcription.** Produces text with word-level timestamps and applies the glossary.
4. **Speakers.** Runs local diarization and labels `Speaker 1`, `Speaker 2`.
5. **Frames.** Samples the video every few seconds, compares small grayscale copies, keeps the frames that changed from the last one kept, and guarantees one frame per fixed interval, with a cap per meeting. ffmpeg's scene score is too coarse for a screen share, where a new slide changes only a small share of the pixels. Audio-only files skip this step.
6. **Output.** Writes everything to a folder next to the file.

Each step caches its result, so an interrupted run resumes where it stopped. The original file is never changed. Long meetings run in the background.

```text
<recording>.barneycat/
  info.json         duration, start time, engine, model, language
  transcript.md     what the agent reads, with timestamps and speakers
  transcript.json   segments and words
  frames/           frames named by offset, plus index.json
  report.md         written by the agent
  report.pdf        generated from report.md
  actions.json      actions in structured form
```

## Transcription engines

| Machine | Default | Also available |
| --- | --- | --- |
| Apple Silicon | `whisper-mlx`, large-v3-turbo | `parakeet-mlx` |
| NVIDIA GPU | `whisper-faster`, large-v3-turbo | `parakeet-sherpa` |
| CPU only | `whisper-faster`, large-v3-turbo, int8 | `parakeet-sherpa` |

`--engine auto` picks by hardware. The defaults come from a test on real recordings, one in English and one in Portuguese, comparing errors on names and technical terms, run time and memory. Public benchmarks are not enough, because nearly all come from vendors and have little Portuguese data. The audio, transcripts and results of that test stay out of the repository.

Whisper won because it got names right more often and it is the only family that takes a vocabulary hint. All engines did well on plain Portuguese speech. Parakeet was about three times faster on Apple Silicon, and `parakeet-sherpa` was the fastest on CPU but the weakest on names, so both stay available for when speed matters more. This rests on two recordings on one machine, so revisit it with more data.

Diarization uses sherpa-onnx, which needs no third-party token. It finds the main speakers but tends to split one person into extra labels and to merge short replies into the previous speaker, so the agent treats labels as hints and checks them against the frames.

## Dependencies

- `uv` is the only prerequisite. If it is missing, `SKILL.md` shows the install command for each system.
- The system ffmpeg is used when present. Otherwise the binary from the `imageio-ffmpeg` package is used. That package has no ffprobe, so inspection relies on ffmpeg alone.
- The first run downloads the model and tells the user.

## What the agent does

1. Runs `prepare` and reads `transcript.md`.
2. Looks at the frames for the moments that matter: a change of topic, or speech like "here on the screen". It does not need to read them all. Claude reads images directly, with no OCR.
3. Names the speakers from what the frames show, such as the active speaker highlight or the names on the call. Without evidence, it keeps `Speaker N`.
4. Reads earlier reports, if history is configured.
5. Writes `report.md` and `actions.json`, generates the PDF, and summarizes the result in the conversation, tying the meeting to the task at hand.

## Report

Sections, in this order:

1. **Header:** date, duration, attendees, what appeared on screen, and what the recording missed.
2. **For you:** what matters to the user and to the current task.
3. **After you left:** only present if the user left before the end. It comes from a goodbye in the speech, absence from the frames, or what the user reports, and it is marked as inference when not explicit.
4. **Timeline:** real time, when known, and position in the video.
5. **Topics:** one section per topic, with screenshots and quotes.
6. **Earlier open items:** what this meeting answered from the history.
7. **Actions:** a checklist with owners.

The report text follows the language of the conversation. Quotes stay in their original language.

**Evidence is mandatory.** Every action and every important claim carries a timestamp and a quote. Anything without a direct source is marked as inference. The agent never invents a timestamp, a name or a deadline.

## Memory across meetings

With `reports_dir` configured, the agent copies `report.md` and `actions.json` there. At the next meeting it reads the open actions and the latest reports from the same series, and marks what was answered. Without `reports_dir`, this step does not run.

## Local configuration

It lives in `~/.barneycat/`, outside the repository. All of it is optional.

```toml
# ~/.barneycat/config.toml
name = "Jane Example"
aliases = ["Jane"]
language = "en"
reports_dir = "~/meetings"
notes = """
QA on the data team. My tile on calls has no name on it.
"""
```

```toml
# ~/.barneycat/glossaries/example-project.toml
vocabulary = ["Acme", "XY-123"]

[corrections]
"a cme" = "Acme"
```

`notes` is free text for the agent: the user's role, how they appear on a call, what they care about. Without `name`, the "For you" section is written in general terms.

## Privacy

- The recording and the audio stay on the machine.
- The transcript text and the frames the agent opens go to the model provider, as in any conversation with the agent. The README says so explicitly.
- Only the model download uses the network.

## Public repository rules

- No real names of people, companies, clients or projects in code, examples, tests, commits or docs.
- Examples use fictional data. Tests use synthetic audio.
- `.gitignore` blocks video, audio and `*.barneycat/`.
- Commits use the GitHub noreply email.
- Before the first push, a scan of the repository and its history looks for personal names and terms.

## Out of scope for v1

- Cloud transcription.
- Ticket creation by the plugin. The agent can already do this with its own tools if the user asks.
- Live recording, download by URL, and automatic lookup of the latest recording.

## Definition of done

- It installs from the marketplace and triggers from a session in another project with a natural-language request alone.
- A real TedCat recording produces a report on par with the hand-made ones.
- CI runs on macOS, Windows and Linux with synthetic audio and a small model.
- Paths with spaces work on all three systems.
- The personal data scan passes.
- The logo is in the README: a skinny yellow cat with green eyes.
