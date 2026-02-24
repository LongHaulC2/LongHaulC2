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


# ==============================================================================
# "Yellow Techno Sphere" EASTER EGG COMPONENT
# ==============================================================================
def run_yellow_techno_sphere():
    # 1. CSS for the "Chomp" and the "Movement"
    ui.add_css(
        """
        /* The container for the whole sequence */
        .pacman-sequence {
            position: fixed;
            bottom: 20px;
            left: -200px;
            display: flex;
            align-items: center;
            z-index: 9999;
            animation: move-across 12s linear forwards;
            pointer-events: none;
        }

        /* The Yellow Techno Sphere Body */
        .pacman {
            width: 40px;
            height: 40px;
            background: #FFFF00;
            border-radius: 50%;
            position: relative;
        }

        /* The Mouth (using clip-path to animate the "pie slice") */
        .pacman::after {
            content: "";
            display: block;
            width: 40px;
            height: 40px;
            background: #0a0a0a; /* Match your dashboard background */
            clip-path: polygon(100% 50%, 50% 50%, 100% 0, 100% 100%);
            animation: chomp 0.3s ease-in-out infinite;
        }

        /* The Dots */
        .dot {
            width: 8px;
            height: 8px;
            background: #FFB8AE;
            border-radius: 50%;
            margin-left: 40px;
        }

        @keyframes chomp {
            0%, 100% { clip-path: polygon(100% 50%, 50% 50%, 100% 0, 100% 100%); }
            50% { clip-path: polygon(100% 50%, 50% 50%, 100% 50%, 100% 50%); }
        }

        @keyframes move-across {
            0% { left: -200px; }
            100% { left: 120%; }
        }
    """
    )

    async def run_sequence():
        # Create the Yellow Techno Sphere and dots
        with ui.element("div").classes("pacman-sequence") as container:
            ui.element("div").classes("pacman")
            ui.element("div").classes("dot")
            ui.element("div").classes("dot")
            ui.element("div").classes("dot")
            ui.element("div").classes("dot")

        # Clean up after the 12s animation finishes
        await asyncio.sleep(13)
        container.delete()

    # Start the timer when the function is called
    ui.timer(0, run_sequence, once=True)
