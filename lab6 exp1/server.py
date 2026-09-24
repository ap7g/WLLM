"""Expt 1 - Personal Assistant Memory Server (MCP).
Exposes save_note, search_notes and delete_note tools backed by notes.json.
"""
import json
import os
from datetime import datetime

from mcp.server.mcpserver import MCPServer

NOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.json")
mcp = MCPServer("notes-server")


def load_notes():
    if not os.path.exists(NOTES_FILE):
        return []
    with open(NOTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_notes(notes):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)


@mcp.tool()
def save_note(content: str, tags: list[str] = []) -> str:
    """Save a new note with optional tags (e.g. ["project", "deadline"])."""
    notes = load_notes()
    note = {
        "id": max([n["id"] for n in notes], default=0) + 1,
        "content": content,
        "tags": [t.lower() for t in tags],
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    notes.append(note)
    write_notes(notes)
    return f"Saved note #{note['id']}: {content} (tags: {', '.join(note['tags']) or 'none'})"


@mcp.tool()
def search_notes(query: str) -> str:
    """Search saved notes by keywords. Matches words in the note content and tags."""
    words = [w.lower().strip("?,.!") for w in query.split() if len(w) > 2]
    results = []
    for note in load_notes():
        text = (note["content"] + " " + " ".join(note["tags"])).lower()
        score = sum(1 for w in words if w in text)
        if score:
            results.append((score, note))
    results.sort(key=lambda r: r[0], reverse=True)
    if not results:
        return "No matching notes found."
    return json.dumps([note for _, note in results], indent=2)


@mcp.tool()
def delete_note(note_id: int) -> str:
    """Delete a note by its id."""
    notes = load_notes()
    remaining = [n for n in notes if n["id"] != note_id]
    if len(remaining) == len(notes):
        return f"Note #{note_id} not found."
    write_notes(remaining)
    return f"Deleted note #{note_id}."


if __name__ == "__main__":
    mcp.run()  # stdio transport
