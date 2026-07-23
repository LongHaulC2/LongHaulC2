# Profile Builder (POC)

**Location:** `development/.dev_testing/profile_editor/concept/concept_v3.py`  
**Run:** `python development/.dev_testing/profile_editor/concept/concept_v3.py` (port 8090)

---

## Architecture

The builder uses a **model-driven** pattern. One dict (`profile_model`) is the single source of truth. The UI reads from it and writes back to it.

```
profile_model (dict)
    ↕ sync_model_from_ui()       ← pulls current UI edits into the model
    ↕ editor_panel.refresh()     ← rebuilds all UI elements from the model
    ↓ build_toml()               → generates TOML string from the model
    ↑ parse_toml()               ← parses TOML string into the model
```

### Why model-driven

The original concept (v1) stored state inside NiceGUI elements — you had to walk card children to extract transforms. That works for build-only, but breaks when you need to load a profile: you can't populate UI elements that were created inline during a one-shot render.

The model lets us: parse TOML into a dict, then call `editor_panel.refresh()` to rebuild the entire UI from that dict. Same path for new profiles, loaded files, and future API integration.

---

## Data Model

```python
profile_model = {
    "name": "My Custom Profile",
    "author": "",
    "proto": "tcp",                         # shared across GET and POST
    "get": {
        "body": "<METADATA>",               # [raw.get] body template
        "client_transforms": [              # [raw.get.client.metadata] transforms
            {"op": "base64url"},
            {"op": "prepend", "val": "GET /update?sid="},
        ],
        "server_body": "<OUTPUT>",          # [raw.get.server] body
        "server_transforms": [],            # [raw.get.server.output] transforms
    },
    "post": {
        "body": "<OUTPUT>",                 # [raw.post] body template
        "client_transforms": [],            # [raw.post.client.output] transforms
        "server_body": "",                  # [raw.post.server] body (ACK, no transforms)
    },
}
```

Transform entries always use `{"op": ..., "val": ...}` internally, even for `symcrypt` (whose TOML field is `key`). The TOML generator maps `val` back to the correct field name (`val` or `key`) based on the `TRANSFORMS` dict.

---

## Key Globals

| Name | Type | Purpose |
|---|---|---|
| `profile_model` | `dict` | Canonical profile state. Everything reads/writes here. |
| `ui_refs` | `dict` | Maps string keys to live NiceGUI elements (inputs, cards). Cleared on each `editor_panel.refresh()`. |
| `toml_text` | `dict` | Holds the generated TOML string for the right-panel codemirror. |
| `TRANSFORMS` | `dict` | Transform metadata: description, field name, wire types, hints. |

---

## Data Flow

### Build (GUI -> TOML)

1. User edits fields in the GUI
2. Clicks "Build Profile"
3. `sync_model_from_ui()` reads all `ui_refs` elements and card children back into `profile_model`
4. `build_toml()` generates the TOML string from `profile_model`
5. `preview_panel.refresh()` updates the codemirror

### Load (TOML -> GUI)

1. User clicks "Load" -> picks a file, built-in profile, or pastes TOML
2. `parse_toml(text)` parses via `tomllib` and populates a new `profile_model`
3. `editor_panel.refresh()` rebuilds the entire left panel from the model
4. Pre-populated transforms are added via `add_transform(card, op, val)`

---

## TOML String Handling

This is the part most likely to cause bugs. The rules:

| Field | TOML string type | `\xNN` | `\r\n` | In the GUI |
|---|---|---|---|---|
| `body` | Basic `"..."` | Not valid in TOML | Parsed to real CR+LF | Shown as actual newlines in textarea |
| `val` / `key` | Literal `'...'` | Stays as literal text | Stays as literal text | Shown as-is in input field |

**Body round-trip:** TOML `\r\n` -> parser -> real newlines -> textarea displays them -> `_escape_toml_body()` converts real newlines back to `\r\n` in the output. User-typed `\xNN` and `\r\n` literal sequences are protected from double-escaping via sentinel substitution.

**Transform val round-trip:** TOML `'\xNN'` -> parser -> literal text `\xNN` -> input shows it as-is -> `_format_transform_val()` wraps in single quotes as-is. No conversion needed.

---

## Sortable Gotcha

`card.make_sortable(handle=".drag-handle")` must be called **after** pre-populating transforms into the card. SortableJS initializes on the DOM element — if called on an empty card before children are added in the same render batch, drag handles on pre-populated items won't bind. Transforms added later via button click work either way because SortableJS re-scans on mutation.

---

## Files

| File | What |
|---|---|
| `concept.py` | Original v0 POC — drag-sortable transforms only |
| `concept_v1.py` | Added TOML generation, body fields, right-panel preview |
| `concept_v3.py` | Model-driven rewrite with TOML loading, file upload, refreshable panels |
