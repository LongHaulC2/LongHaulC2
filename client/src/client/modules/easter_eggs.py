import asyncio
import random

from nicegui import ui


def run_random_easter_egg():
    if hasattr(ui.context.client, "easter_timer_started"):
        return
    # prevents dup timers
    ui.context.client.easter_timer_started = True

    def roll_dice():
        roll = random.randint(1, 100)

        if roll <= 10:
            run_yellow_techno_sphere()

    ui.timer(60 * 10, roll_dice)


# ====================
# "Yellow Techno Sphere" EASTER EGG COMPONENT
# ====================
def run_yellow_techno_sphere():
    ui.add_css(
        """
            .pacman-sequence {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                left: -100px;
                display: flex;
                align-items: center;
                /* Changed to -1 to place it BEHIND footer text/icons */
                z-index: -1;
                animation: move-across-footer 10s linear forwards;
                pointer-events: none;
            }

            .pacman {
                width: 18px;
                height: 18px;
                background: #FFFF00;
                border-radius: 50%;
                position: relative;
            }

            .pacman::after {
                content: "";
                display: block;
                width: 18px;
                height: 18px;
                /* Use 'inherit' or a specific dark color to match your footer */
                background: #0a0a0a;
                clip-path: polygon(100% 50%, 50% 50%, 100% 0, 100% 100%);
                animation: chomp 0.2s ease-in-out infinite;
            }

            .dot {
                width: 3px;
                height: 3px;
                background: rgba(255, 184, 174, 0.4); /* Lowered opacity to make dots subtle */
                border-radius: 50%;
                margin-left: 12px;
            }

            @keyframes chomp {
                0%, 100% { clip-path: polygon(100% 50%, 50% 50%, 100% 0, 100% 100%); }
                50% { clip-path: polygon(100% 50%, 50% 50%, 100% 50%, 100% 50%); }
            }

            @keyframes move-across-footer {
                0% { left: -50px; }
                100% { left: 105%; }
            }
        """
    )

    async def run_sequence():
        # Because this is called while the footer context is active,
        # it will append itself to the footer automatically.
        with ui.element("div").classes("pacman-sequence") as container:
            ui.element("div").classes("pacman")
            for _ in range(5):
                ui.element("div").classes("dot")

        await asyncio.sleep(11)
        container.delete()

    ui.timer(0, run_sequence, once=True)
