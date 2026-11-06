<p align="center">
  <img src="assets/logo.png" width="160" alt="BarneyCat logo: a skinny yellow cat with green eyes, wearing headphones, on a blue background">
</p>

<h1 align="center">BarneyCat</h1>

<p align="center">A Claude Code plugin that reads a meeting recording and tells you what was discussed and what needs to be done.</p>

---

You are working on a feature and someone sends you a recording. Tell the agent:

> look at this meeting using barneycat: `~/Movies/TedCat/TedCat 2026-01-15 at 09.09.13.mp4`

It transcribes the audio on your machine, looks at what was on screen, and writes a report tied to the work at hand. The agent that is already helping you writes the report, so it knows what matters for your task.

## Install

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). Everything else installs on first use.

```bash
claude plugin marketplace add irobson/barneycat
claude plugin install barneycat@barneycat
```

Works on macOS, Windows and Linux. The first run downloads the models, which takes a few minutes.

## What you get

A folder next to the recording:

```text
<recording>.barneycat/
  report.pdf        the report
  report.md         same report, in Markdown
  actions.json      actions in structured form
  transcript.md     transcript with timestamps and speakers
  transcript.json   segments and words
  frames/           what was on screen
  info.json         duration, engine, language
```

The report has:

- **For you:** what matters to you and to your current task.
- **After you left:** what happened if you dropped off the call early.
- **Timeline:** real time and position in the video.
- **Topics:** what was said, with screenshots and quotes.
- **Earlier open items:** what this meeting answered from past meetings.
- **Actions:** a checklist with owners.

Every action and important claim carries a timestamp and a quote. Anything without a direct source is marked as inference.

Any video or audio that ffmpeg reads works. Recordings from [TedCat](https://github.com/irobson/tedcat) also get real clock times, taken from the file name.

## Configuration

All optional, and it stays on your machine in `~/.barneycat/`.

```toml
# ~/.barneycat/config.toml
name = "Jane Example"          # who "you" is in the report
aliases = ["Jane"]
language = "en"
reports_dir = "~/meetings"     # turns on memory across meetings
```

A glossary fixes the names and terms your team uses:

```toml
# ~/.barneycat/glossaries/example-project.toml
vocabulary = ["Acme", "XY-123"]

[corrections]
"a cme" = "Acme"
```

Ask for it by name: "use the example-project glossary". Whisper engines use `vocabulary` as a hint. Every engine applies `corrections`.

## Engines

Transcription is local. BarneyCat picks an engine for your machine, and you can ask for another one.

| Engine | Runs on | Notes |
| --- | --- | --- |
| `whisper-mlx` | Apple Silicon | Default there |
| `whisper-faster` | NVIDIA GPU or CPU | Default everywhere else |
| `parakeet-mlx` | Apple Silicon | About 3x faster, less accurate on names, no vocabulary hint |
| `parakeet-sherpa` | Any CPU | Fastest on CPU, weakest on names, no vocabulary hint |

Speaker labels are hints: separation can split one person in two or merge short replies. The agent checks them against what the frames show.

## Privacy

- The recording and the audio stay on your machine.
- The transcript text and the frames the agent opens go to the model provider, as in any conversation with the agent. Do not use BarneyCat on a recording whose content cannot reach that provider.
- The network is used only to download models.

## Development

```bash
uv run --no-project --python 3.12 --with pytest --with numpy --with imageio-ffmpeg --with sherpa-onnx --with certifi pytest tests
```

The design is in [docs/spec.md](docs/spec.md). Tests use generated media only. Never commit a real recording, transcript or report.

## License

[MIT](LICENSE)
