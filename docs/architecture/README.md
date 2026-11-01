# AEGIS architecture figures

These diagrams describe the current `backend/aegis_v2` implementation. They are standalone, editable SVG vector graphics with accessible titles/descriptions, embedded styles, and no external fonts, images, JavaScript, or network dependencies.

| Figure | What it explains |
|---|---|
| [System overview](system-overview.svg) | Web/API, persistent controller, three model roles, target adapter, isolated components, storage, and exports. |
| [Red and provenance](red-provenance.svg) | Authorized context, actual tool results, source selection, composition, executable transforms, submission, and server-owned attribution. |
| [Verification lifecycle](verification-lifecycle.svg) | Reproduction, supported controls, development gates, freeze, paired final suites, verdicts, and eligibility. |

Arrows show conceptual information/process flow. They are not a packet-level sequence diagram or a claim of a separate service for every box. Red/Judge providers are external inference roles; local tools are registered subprocess bridges. Tool effects in the target adapter are simulated.

The attack corpus uses SQLite FTS5, while target document retrieval is lexical/BM25-like. The word “vector” here describes the graphics; these figures do not imply an embedding or vector-database implementation.

Regenerate from the repository root using Python (standard library only):

```powershell
.\.venv-win\Scripts\python.exe docs\architecture\generate.py
```

On Linux/macOS, use `.venv/bin/python docs/architecture/generate.py`. Edit [generate.py](generate.py) for consistent labels, layout, and colors, then regenerate all three figures. SVG files remain viewable directly in a browser or embeddable in Markdown, slides, and documentation.
