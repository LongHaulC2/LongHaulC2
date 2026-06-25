from nicegui import ui


async def build_syntax_sidebar():
    with ui.drawer(side="right", value=False).classes("tech-glass-panel border-l border-emerald-500/20 p-6") as drawer:
        with ui.column().classes("w-full gap-2"):
            with ui.row().classes("w-full items-center justify-between pb-2 border-b border-emerald-500/30"):
                ui.label("LUCENE SYNTAX").classes("tech-label-header-bold text-emerald-500")
                ui.button(icon="close", on_click=drawer.toggle).props("flat round dense").classes(
                    "tech-btn-ghost hover:text-emerald-400"
                )

            ui.label("OPERATIONAL QUERY LANGUAGE").classes("tech-label-sub text-emerald-500/70")
            ui.label("All searchbars use Lucene as a query language").classes("tech-data-mono opacity-80")

            ui.label("BASIC OPERATORS").classes("tech-label-sub mt-4")

            syntax_items = [
                ("WILDCARD", "admin*", "Matches 'admin', 'administrator'"),
                ("FUZZY", "rryan~1", "Matches 'ryan' (1 character off)"),
                ("BOOLEAN", "win AND admin", "Matches nodes with both terms"),
                ("EXCLUSION", "win NOT server", "Matches windows but not servers"),
                ("GROUPING", "(dc OR sql) AND active", "Complex logic grouping"),
                ("FIELDS", "hostname:ws*", "Target specific properties"),
            ]

            for title, cmd, desc in syntax_items:
                with ui.column().classes("gap-0 mb-2 w-full"):
                    ui.label(title).classes("text-[10px] text-emerald-500/50 font-mono tracking-tighter")
                    ui.label(cmd).classes(
                        "tech-data-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 border border-emerald-500/20"
                    )
                    ui.label(desc).classes("text-[11px] text-neutral-500 italic mt-1")

            ui.separator().classes("bg-emerald-500/10 my-4")

            # ui.label("OPERATOR TIPS").classes("tech-label-sub")
            # with ui.column().classes("gap-1"):
            #     ui.markdown("""
            #     - **IP Ranges:** `internal_ip:192.168.1.*`
            #     - **Exact Match:** `"lsass.exe"`
            #     - **Escape Chars:** Use `\\` before `/ [ ] :`
            #     """).classes("tech-data-mono text-neutral-300")

        ui.space()

        # could add button to lucene docs too
        with ui.column().classes("w-full gap-1 opacity-50 mb-2"):
            ui.separator().classes("bg-white/10 mb-2")
            ui.label("LONGHAULC2 //").classes("text-[12px] font-mono text-neutral-600 w-full text-center mt-1")

    return drawer
