# Attribution

Interview cadence, glossary format, ADR gates, and the `/grill-with-docs`
name are adapted from [Matt Pocock's skills](https://github.com/mattpocock/skills)
(`grilling`, `domain-modeling`, `grill-with-docs`).

MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Govtools house changes, which are not upstream:

- The skill is self-contained. Pocock's `grill-with-docs` is one line that
  tells the agent to load `grilling` and `domain-modeling`; that delegation
  often fails and the interview improvises. This copy inlines both.
- Default cadence is one question per turn. Pocock's grilling asks a frontier
  round; he documents one-at-a-time as a supported opt-out.
- Contexts follow `GLOSSARY-MAP.md` so Mr North, realtor-agent, and TrueHold
  Wellness never share a glossary.
