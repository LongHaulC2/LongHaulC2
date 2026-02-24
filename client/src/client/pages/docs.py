from pathlib import Path

import structlog
from nicegui import ui

from client.src.client.pages.menu import setup_menu

server_log = structlog.getLogger("server")

# ==============================================================================
#   DOCUMENTATION UTILITIES
# ==============================================================================

# Path Logic: Assumes this file is in client/src/client/pages/
# So .parent.parent is client/src/client/
DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"


def load_docs_tree(path: Path = DOCS_ROOT) -> list:
    """
    Recursively builds a tree structure for ui.tree from the file system.
    """
    if not path.exists():
        server_log.warning(f"Docs path not found: {path}")
        return []

    tree = []

    # Sort: Directories first, then files, both alphabetical
    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

    for item in items:
        if item.name.startswith("."):
            continue  # Skip hidden files (.git, .DS_Store)

        # Create the Node
        # ID = Relative path (e.g., "01/test.md") used for loading content
        # Label = Clean name (e.g., "01" -> "01", "test.md" -> "Test")
        node = {
            "id": str(item.relative_to(DOCS_ROOT)),
            "label": item.stem.replace("_", " ").title(),
        }

        if item.is_dir():
            # Recursion for folders
            children = load_docs_tree(item)
            if children:
                node["children"] = children
                tree.append(node)
        elif item.suffix.lower() == ".md":
            # Add Markdown files
            tree.append(node)

    return tree


def load_doc_content(relative_path: str) -> str:
    """
    Safely loads markdown content given a relative path from the tree ID.
    """
    try:
        if not relative_path:
            return "# Welcome\nSelect a topic from the navigation tree."

        target_path = (DOCS_ROOT / relative_path).resolve()

        # Security Check: Prevent directory traversal
        if not str(target_path).startswith(str(DOCS_ROOT.resolve())):
            return "# 403 Forbidden\nAccess denied."

        if target_path.is_dir():
            return f"# {target_path.name}\nSelect a document within this folder."

        if target_path.exists():
            return target_path.read_text(encoding="utf-8")

        return f"# 404 Not Found\nDocument `{relative_path}` does not exist."

    except Exception as e:
        return f"# Error\nCould not load document: {e}"


# ==============================================================================
#   PAGE LOGIC
# ==============================================================================


@ui.page("/docs")
async def docs_page():
    # 1. Page Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    # 2. Inject CSS for Markdown Styling
    ui.add_head_html(
        """
        <style>
            .doc-content { font-family: 'Inter', sans-serif; color: #d4d4d4; line-height: 1.6; }
            .doc-content h1, .doc-content h2, .doc-content h3 {
                font-family: 'Roboto Mono', monospace; color: #ffffff;
                margin-top: 1.5em; margin-bottom: 0.5em; letter-spacing: -0.02em;
            }
            .doc-content h1 { font-size: 2.25rem; border-bottom: 1px solid rgba(255,255,255,0.1);
              padding-bottom: 0.5rem; color: #10b981; }
            .doc-content h2 { font-size: 1.5rem; color: #34d399; }
            .doc-content h3 { font-size: 1.25rem; color: #6ee7b7; }
            .doc-content p { margin-bottom: 1em; }
            .doc-content code {
                background-color: rgba(0,0,0,0.3); color: #10b981;
                padding: 0.2em 0.4em; border-radius: 4px;
                font-family: 'Roboto Mono', monospace; font-size: 0.85em;
            }
            .doc-content pre {
                background-color: #0a0a0a !important; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 1rem; overflow-x: auto; margin-bottom: 1.5em;
            }
            .doc-content pre code { background-color: transparent; color: #e5e5e5; padding: 0; }
            .doc-content blockquote {
                border-left: 4px solid #f59e0b; background-color: rgba(245, 158, 11, 0.1);
                padding: 1rem; margin: 1.5em 0; font-style: italic; color: #fbbf24;
            }
            .doc-content table { width: 100%; border-collapse: collapse; margin: 1.5em 0; font-size: 0.9em; }
            .doc-content th {
                text-align: left; padding: 12px; background-color: rgba(255,255,255,0.05);
                color: #10b981; font-family: 'Roboto Mono', monospace; border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            .doc-content td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        </style>
    """
    )

    setup_menu("Documentation")

    # Load Tree Data Once
    docs_tree_data = load_docs_tree()

    await docs_view(docs_tree_data)


async def docs_view(tree_data: list):
    # --- LAYOUT CONTAINER ---
    with ui.row().classes("w-full h-full gap-0 tech-glass-panel"):
        # ======================================================================
        #   LEFT SIDEBAR: NAVIGATION TREE
        # ======================================================================
        with ui.column().classes("w-72 h-full border-r border-white/5 bg-black/20 flex-shrink-0"):
            # Header
            with ui.row().classes("w-full p-4 items-center gap-2 border-b border-white/5"):
                ui.icon("library_books", color="emerald-500")
                ui.label("KNOWLEDGE_BASE").classes("tech-label-title text-xs")

            # Search
            with ui.row().classes("w-full px-4 py-2"):
                ui.input(placeholder="SEARCH TOPICS...").props(
                    "outlined dense dark color=emerald input-class=text-xs"
                ).classes("w-full")

            # Tree Navigation
            with ui.scroll_area().classes("w-full flex-grow p-2"):
                if not tree_data:
                    ui.label("No docs found in client/src/client/docs").classes("text-xs text-red-400 font-mono p-4")
                else:
                    # Tree Component
                    docs_tree = (
                        ui.tree(
                            tree_data,
                            label_key="label",
                            on_select=lambda e: update_content(e.value),
                        )
                        .props("dark dense no-connectors selected-color=emerald expand-icon=chevron_right")
                        .classes("text-neutral-400 font-mono text-xs")
                    )

                    # Expand all folders by default for better visibility
                    docs_tree.expand()

            # Footer
            with ui.row().classes("w-full p-3 border-t border-white/5 bg-white/5"):
                ui.label("LOCAL_FS_MODE").classes("text-[9px] font-mono text-neutral-600")

        # ======================================================================
        #   RIGHT SIDEBAR: CONTENT READER
        # ======================================================================
        with ui.column().classes("flex-grow h-full relative"):
            # --- Breadcrumbs Bar ---
            with ui.row().classes("w-full p-4 border-b border-white/5 bg-black/10 items-center justify-between"):
                # Dynamic Breadcrumbs Container
                breadcrumbs_container = ui.element("q-breadcrumbs").classes("text-xs font-mono text-neutral-500")
                with breadcrumbs_container:
                    with ui.element("q-breadcrumbs-el").props("icon=home label=DOCS"):
                        pass
                    # Placeholder until something is selected
                    with ui.element("q-breadcrumbs-el").props('label="SELECT TOPIC"').classes("text-emerald-500"):
                        pass

                # maybe change to a download button
                # with ui.row().classes("gap-2"):
                #     ui.button("EDIT", icon="edit").props(
                #         "flat dense color=grey size=sm"
                #     )

            # --- Markdown Content Area ---
            with ui.scroll_area().classes("w-full flex-grow p-8"):  # noqa: SIM117
                with ui.column().classes("w-full max-w-4xl mx-auto pb-20"):
                    # Markdown Container
                    markdown_view = ui.markdown("# Welcome\nSelect a document from the navigation tree.").classes(
                        "doc-content w-full"
                    )

                    ui.separator().classes("bg-white/10 my-8")

    # --- EVENT HANDLER ---
    def update_content(node_id):
        if not node_id:
            return

        # 1. Load Content
        content = load_doc_content(node_id)
        markdown_view.content = content

        # 2. Update Breadcrumbs (Simple visual update)
        breadcrumbs_container.clear()
        with breadcrumbs_container:
            with ui.element("q-breadcrumbs-el").props("icon=home label=DOCS"):
                pass

            # Convert ID "01/test.md" -> ["01", "Test"]
            parts = Path(node_id).parts
            for i, part in enumerate(parts):
                is_last = i == len(parts) - 1
                clean_label = Path(part).stem.replace("_", " ").upper()

                color_class = "text-emerald-500" if is_last else ""
                with ui.element("q-breadcrumbs-el").props(f'label="{clean_label}"').classes(color_class):
                    pass
