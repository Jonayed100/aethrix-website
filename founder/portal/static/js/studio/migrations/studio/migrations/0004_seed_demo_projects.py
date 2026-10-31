"""Adds the first two demo projects to the database.

Runs once, on your computer and on Render. Projects that already exist (same
web address name) are left alone, so editing them in the founder dashboard is safe.
"""
from django.db import migrations

PROJECTS = [
    {
        "slug": "floodlit",
        "title": "Floodlit",
        "category": "website",
        "summary": "An online booking platform for football turfs in Dhaka.",
        "description": (
            "We built Floodlit (a static website for demo), an online booking platform "
            "for football turfs in Dhaka."
        ),
        "features_title": "What it does",
        "features": "\n".join([
            "Live slot availability across multiple turfs",
            'Smart search: type "7-a-side in Mirpur tomorrow after 9pm" and it filters for you',
            "10-minute slot hold, so no slot gets double-booked",
            "Split the cost with your squad and pay by bKash, Nagad or card",
            "QR match pass with Google Calendar and WhatsApp sharing",
            "Owner dashboard with today's schedule, walk-ins, revenue charts and live pricing",
        ]),
        "roadmap_title": "",
        "roadmap": "",
        "roadmap_note": "",
        "closing_title": "Want one for your business?",
        "closing": (
            "Run a turf, gym, badminton court, or any business that takes bookings? "
            "We can build this for you, with real payments."
        ),
        "live_url": "https://floodlit-turf-demo.onrender.com/",
        "tech_stack": "",
        "sort_order": 1,
    },
    {
        "slug": "banglish-be",
        "title": "Banglish (BE)",
        "category": "product",
        "summary": "An evolving programming language with Banglish-inspired syntax, developed under Project Aethrix.",
        "description": (
            "Introducing Banglish (BE) 3.1.0, an evolving programming language developed under Project Aethrix.\n\n"
            "Our mission is to bring a different approach to programming through familiar, Banglish-inspired "
            "syntax while building an ecosystem where developers can learn, experiment and create."
        ),
        "features_title": "What Banglish BE offers right now",
        "features": "\n".join([
            "Banglish-Inspired Syntax — Write code using familiar keywords such as dekhao, dhoro, jodi, nahole and kaj.",
            "Variables & Operations — Store information, perform calculations and work with data.",
            "Conditional Statements — Make decisions using jodi and nahole.",
            "Loops — Automate repetitive tasks with looping structures.",
            "Functions — Create reusable blocks of code.",
            "Interactive Applications — Build simple applications with windows, buttons, text, input fields and other interface elements.",
            "Random Number Generation — Add randomness to your programs and games.",
            "Online Playground — Write and run Banglish BE code directly in your browser.",
            "Interpreter & Runtime — Execute programs through the Banglish BE environment.",
            "Examples & Documentation — Explore code examples and learning resources to understand the language.",
        ]),
        "roadmap_title": "What's coming in the future?",
        "roadmap": "\n".join([
            "More powerful language features and improved performance.",
            "Expanded website development capabilities.",
            "Mobile application development support.",
            "AI and machine learning integrations.",
            "Database connectivity and backend development tools.",
            "More advanced game development capabilities.",
            "Developer tools, libraries and package management.",
            "Expanded documentation, tutorials and community contributions.",
        ]),
        "roadmap_note": "These are future development goals, not features currently available.",
        "closing_title": "Our vision",
        "closing": (
            "We want Banglish BE to grow beyond a programming language into a complete development ecosystem.\n\n"
            "From learning the fundamentals to building real-world software, we want to make the journey more "
            "approachable for the next generation of developers.\n\n"
            "This is only the beginning. The journey continues.\n\n"
            "BANGLISH (BE) — Code with familiarity. Build without limits."
        ),
        "live_url": "https://banglish-be.onrender.com/",
        "tech_stack": "",
        "sort_order": 2,
    },
]


def add_projects(apps, schema_editor):
    Project = apps.get_model("studio", "Project")
    for data in PROJECTS:
        if not Project.objects.filter(slug=data["slug"]).exists():
            Project.objects.create(is_published=True, **data)


def remove_projects(apps, schema_editor):
    Project = apps.get_model("studio", "Project")
    Project.objects.filter(slug__in=[p["slug"] for p in PROJECTS]).delete()


class Migration(migrations.Migration):
    dependencies = [("studio", "0003_project_details")]
    operations = [migrations.RunPython(add_projects, remove_projects)]