# Design Language 

I'm not a UI expert, however I try my best to adhear to a 60 30 10 color setup. 

## Colors

These are the colors currently used in the project:

| Color Code | Color Name | Where Used |
|---|---|---|
| `#09090b` | <span style={{color:'#3f3f46'}}><span style={{background:'#09090b', padding:'2px 6px', border:'1px solid #3f3f46'}}>Zinc-950</span></span> | Body background |
| `#27272a` | <span style={{color:'#71717a'}}><span style={{background:'#27272a', padding:'2px 6px', border:'1px solid #3f3f46'}}>Zinc-800</span></span> | Background dot grid pattern |
| `#e4e4e7` | <span style={{color:'#e4e4e7'}}>Zinc-200</span> | Default body text, data text, table body cells, hover text |
| `#a1a1aa` | <span style={{color:'#a1a1aa'}}>Zinc-400</span> | Labels, sub-labels, headers, button text, input text, table heads |
| `#ffffff` | <span style={{color:'#ffffff'}}>White</span> | Bold data values, ghost button hover, text selection |
| `#3f3f46` | <span style={{color:'#3f3f46'}}>Zinc-600</span> | Scrollbar thumb, switch track (off state) |
| `#52525b` | <span style={{color:'#52525b'}}>Zinc-500</span> | Scrollbar thumb hover |
| `#737373` | <span style={{color:'#737373'}}>Neutral-500</span> | Ghost button text (idle) |
| `#18181b` | <span style={{color:'#71717a'}}><span style={{background:'#18181b', padding:'2px 6px', border:'1px solid #3f3f46'}}>Zinc-900</span></span> | Dialog backgrounds (tech-dialog, confirm-dialog) |
| `#121212` | <span style={{color:'#71717a'}}><span style={{background:'#121212', padding:'2px 6px', border:'1px solid #3f3f46'}}>Near-Black</span></span> | Select dropdown menu background |
| `#0f0f0f` | <span style={{color:'#71717a'}}><span style={{background:'#0f0f0f', padding:'2px 6px', border:'1px solid #3f3f46'}}>Off-Black</span></span> | Table header bg, expanded expansion bg |
| `rgba(23,23,23,…)` | <span style={{color:'#71717a'}}><span style={{background:'#171717', padding:'2px 6px', border:'1px solid #3f3f46'}}>Zinc-900 (alpha)</span></span> | Glass panels, inputs, selects, toggles, expansions, tooltips |
| `rgba(16,185,129,0.15)` | <span style={{color:'#10b981'}}>Emerald-500/15%</span> | Body radial glow, active toggle tint |
| `rgba(16,185,129,0.3)` | <span style={{color:'#10b981'}}>Emerald-500/30%</span> | Action button border, text selection bg, dialog/tooltip border |
| `rgba(16,185,129,0.1)` | <span style={{color:'#10b981'}}>Emerald-500/10%</span> | Action button bg, select hover/active bg, table row hover |
| `rgba(16,185,129,0.4)` | <span style={{color:'#10b981'}}>Emerald-500/40%</span> | Input focus border, switch track (on state) |
| `#34d399` | <span style={{color:'#34d399'}}>Emerald-400</span> | Active select option text, active toggle text, switch thumb (on) |
| `rgba(16,185,129,0.7)` | <span style={{color:'rgba(16,185,129,0.7)'}}>Emerald-500/70%</span> | Expansion header text |
| `rgba(52,211,153,0.2)` | <span style={{color:'#34d399'}}>Emerald-400/20%</span> | Dialog border, select menu border |
| `#a16ae8` | <span style={{color:'#a16ae8'}}>Lavender</span> | Logo accent, doc inline code text, secondary badges |
| `rgba(239,68,68,0.3)` | <span style={{color:'#ef4444'}}>Red-500/30%</span> | Destructive button border, confirm dialog border |
| `rgba(239,68,68,0.1)` | <span style={{color:'#ef4444'}}>Red-500/10%</span> | Destructive button background |
| `#f87171` | <span style={{color:'#f87171'}}>Red-400</span> | Destructive button text |
| `#fca5a5` | <span style={{color:'#fca5a5'}}>Red-300</span> | Destructive button text (hover) |
| `rgba(255,255,255,0.05)` | <span style={{color:'rgba(255,255,255,0.4)'}}>White/5%</span> | Glass border, header bar border, input border, expansion border |
| `rgba(255,255,255,0.08)` | <span style={{color:'rgba(255,255,255,0.4)'}}>White/8%</span> | Secondary button border, outlined input border |
| `rgba(255,255,255,0.1)` | <span style={{color:'rgba(255,255,255,0.5)'}}>White/10%</span> | Table container border, toggle border, table header bottom border |
| `rgba(255,255,255,0.04)` | <span style={{color:'rgba(255,255,255,0.3)'}}>White/4%</span> | Secondary button background |
| `rgba(255,255,255,0.02)` | <span style={{color:'rgba(255,255,255,0.3)'}}>White/2%</span> | Stat pill background, expansion header hover bg |

## Buttons:

The following classes are commonly used with buttons:

| Class | Usage |
|---|---|
| `tech-btn-action` | Primary actions (start, create, save) |
| `tech-btn-action-2` | Toolbar / secondary actions |
| `tech-btn-secondary` | Neutral actions (refresh, export) |
| `tech-btn-destructive` | Destructive actions (delete, stop) |
| `tech-btn-ghost` | Invisible until hover |

### Button Icons:

Most buttons have a correlating icon. This should be relevant to the button's function. 

#### "+" Buttons:
Any button with a `add` icon denotes opening a new "thing". Currently, this is a `ui.dialogue` window.

For Example:

##### Operations:
 - "+ PAYLOAD": Opens the payload builder window
 - "+ LISTENER": Opens the listener builder window

#### Icon Reference:

Icons can be found at [fonts.google.com](https://fonts.google.com/icons)

| Icon | Purpose | Button Class |
|---|---|---|
| `add` | Create / open builder dialog | `tech-btn-action` |
| `play_arrow` | Start a listener or render a profile | `tech-btn-action` |
| `restart_alt` | Restart a listener or service | `tech-btn-action` |
| `save` / `save_as` | Save / save-as (profiles) | `tech-btn-action` |
| `send` | Send a chat message | `tech-btn-action` |
| `upload` | Upload a file | `tech-btn-action` |
| `login` | Navigate to login | `tech-btn-action` |
| `terminal` | Open terminal for selected implant | `tech-btn-action-2` |
| `open_in_new` | Open detail page for selected | `tech-btn-action-2` |
| `present_to_all` | Upload file to host/memstore | `tech-btn-action-2` |
| `upload_file` | Upload a file or profile | `tech-btn-action-2` |
| `refresh` | Refresh current data | `tech-btn-secondary` |
| `download` / `cloud_download` | Download file or export data | `tech-btn-secondary` |
| `code` | View source | `tech-btn-secondary` |
| `inventory_2` | View package | `tech-btn-secondary` |
| `bug_report` | Report an issue | `tech-btn-secondary` |
| `stop` | Stop a listener or service | `tech-btn-destructive` |
| `delete` | Delete selected items | `tech-btn-destructive` |
| `delete_sweep` | Close all terminal tabs | `tech-btn-destructive` |
| `help_outline` | Toggle syntax help sidebar | `tech-btn-ghost` |
| `close` | Close a dialog or tab | `tech-btn-ghost` |
| `arrow_back` | Back navigation | `tech-btn-ghost` |
| `first_page` / `last_page` | Jump to first/last page | — (pagination) |
| `chevron_left` / `chevron_right` | Previous/next page | — (pagination) |

#### Navigation Sidebar Icons:

| Icon | Page |
|---|---|
| `terminal` | Operations |
| `device_hub` | Engagement Map |
| `layers` | Payloads |
| `headphones` | Listeners |
| `folder` | Filestore |
| `tune` | Profiles |
| `chat` | Chat |
| `policy` | Audit Log |
| `arrow_circle_up` | Status |
| `settings` | Settings |
| `exit_to_app` | Disconnect |
| `open_in_new` | Docs (external link) |

