"""Claude step framework (GÖREV-13; Housing Atlas's stages, `atlas/ai/stages.py`, made generic).

A step has: a key and Turkish title; instruction files (on the destination side, common file first); a JSON schema (in the core,
`studio/ai/schemas/`); its tools; an input builder (the program copies or produces the input files into the run's folder); the task text; an
output check (schema, then meaning); and a Markdown writer (Claude writes only JSON; the program writes the readable Markdown).

Tools: reading inside the run folder (`Read`, `Glob`, `Grep`; Claude Code applies a Read rule to Glob and Grep) and writing the one output file
(`Write` is allowed only through an `Edit(./file)` rule, as Housing Atlas verified live). No web search, no Bash, nothing else: with
`--permission-mode dontAsk` every call outside the rules is refused and written to the run record.

Combined instructions = the destination's common instruction file + the step's file + the step's JSON schema as filled for this run (the
schema is in the core, the destination's lists, e.g. content families and regions, are filled in for the run), so Claude does not need to open
files outside its folder.
"""
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import schema as schema_check

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
READ_TOOLS = ("Read", "Glob", "Grep")
WRITE_TOOLS = ("Write", "Edit")
NOTE_START, NOTE_END = "--- not başı ---", "--- not sonu ---"


class StepError(ValueError):
    """User-facing reason a step cannot run."""


@dataclass
class RunContext:
    """Everything a step needs during one run."""
    db: object
    profile: object
    destination: dict
    run_id: str
    folder: Path
    params: dict
    regions: list
    log: object = None
    correction: dict | None = None
    packs: dict = field(default_factory=dict)        # input file -> stored pack record
    pack_rows: dict = field(default_factory=dict)    # input file -> {K id: row}
    previous: list = field(default_factory=list)     # earlier proposals (for the duplicate check)
    inputs: list = field(default_factory=list)

    def say(self, text):
        if self.log:
            self.log(text)


@dataclass(frozen=True)
class Step:
    key: str
    title: str
    instructions: tuple
    schema: str
    output: str
    markdown: str
    prepare: object
    task: object
    fill_schema: object
    check: object
    render: object
    tools: tuple = READ_TOOLS + WRITE_TOOLS

    @property
    def allowed(self):
        """`--allowedTools`: reading in the run folder, writing only the JSON output (`Edit(...)` is what lets Write through)."""
        return ("Read(./**)", f"Write(./{self.output})", f"Edit(./{self.output})")

    def instruction_paths(self, profile):
        folder = getattr(profile, "CLAUDE_INSTRUCTIONS", None)
        if folder is None:
            raise StepError("Bu destinasyonun Claude talimatları yok.")
        return [Path(folder) / name for name in self.instructions]

    def schema_path(self):
        return SCHEMAS_DIR / self.schema

    def load_schema(self):
        return schema_check.load(self.schema_path())


def run_schema(step, ctx):
    """The step's schema as filled for this run (lists of the destination)."""
    return step.fill_schema(ctx, copy.deepcopy(step.load_schema()))


def combined_instructions(step, ctx, schema):
    parts = [path.read_text(encoding="utf-8-sig").strip() for path in step.instruction_paths(ctx.profile)]
    parts.append(f"# Çıktı şeması: `{step.output}`\n\n`{step.output}` bu JSON şemasına (JSON Schema 2020-12) uymalı. Şema dosyası: "
                 f"`studio/ai/schemas/{step.schema}`; destinasyonun listeleri (içerik aileleri, bölgeler) bu çalışma için doldurulmuştur.\n\n"
                 f"```json\n{json.dumps(schema, ensure_ascii=False, indent=1)}\n```")
    return "\n\n".join(parts) + "\n"


def note_block(note):
    return [NOTE_START, note.strip(), NOTE_END]


STEPS = {}


def register(step):
    STEPS[step.key] = step
    return step


def get(key):
    if key not in STEPS:
        raise StepError("Böyle bir Claude adımı yok.")
    return STEPS[key]
