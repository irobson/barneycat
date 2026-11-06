# Report template

Keep this order. Drop a section only where it says so. Translate the headings to the language of the conversation.

```markdown
# <Meeting topic>

<Date>, led by <person>. Prepared for <user>.

**Recording:** <file>, from <start> to <end> (<duration>). <What the recording missed, if anything.>

**Attendees:** <names, and who spoke the most>

**On screen:** <what was shared>

## For you

What matters to the user and to the current task, most important first. Each point has a stamp.

> "<short quote>" (<stamp>)

## After you left

Only if the user left before the end. Say how you know, and mark it as inference when it is not explicit.

## Timeline

| Time | In the video | Topic |
| --- | --- | --- |
| 09:12 | 3:05 | <one line> |

When the real time is unknown, drop the first column.

## 1. <Topic>   <start> – <end>

What was said and decided, with quotes.

![<what the frame shows>](frames/00-03-05.jpg)

## Earlier open items

Only with history. What this meeting answered, and what is still open.

## Actions

- [ ] <Action>, owner: <person>. "<quote>" (<stamp>)

Source: automatic transcription (<engine>) and video frames. <How speakers were identified.>
```

`actions.json`:

```json
{
  "meeting": "<topic>",
  "date": "2026-01-15",
  "actions": [
    {
      "id": "2026-01-15-1",
      "text": "<action>",
      "owner": "<person or null>",
      "due": "<only if stated, otherwise null>",
      "status": "open",
      "stamp": "00:03:05",
      "quote": "<source quote>",
      "inferred": false
    }
  ]
}
```

When a later meeting answers an action, set its `status` to `done` in the copy in `reports_dir`, and add a `resolved_by` field with that meeting's date.
