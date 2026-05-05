#!/usr/bin/env python3
"""Weekly meal plan generator — runs via GitHub Actions every Sunday."""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent
PLANS_DIR = ROOT / "plans"
MEAL_PLANS_DIR = ROOT / "meal-plans"

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

PASTA_WORDS = {"pasta", "spaghetti", "penne", "rigatoni", "fettuccine", "orecchiette",
               "lasagna", "linguine", "tagliatelle", "orzo", "noodle", "gnocchi"}

PEA_WORDS = {"peas", "snap pea", "snow pea", "pea shoot", "mushy pea", "pea shoots"}
AVOCADO_WORDS = {"avocado", "guacamole"}


def next_monday() -> date:
    today = date.today()
    days = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days)


def week_days(start: date) -> list[tuple[date, str]]:
    return [(start + timedelta(days=i), DAYS_OF_WEEK[i]) for i in range(7)]


def recently_used(weeks: int = 3) -> set[str]:
    if not MEAL_PLANS_DIR.exists():
        return set()
    cutoff = date.today() - timedelta(weeks=weeks)
    titles: set[str] = set()
    for f in MEAL_PLANS_DIR.glob("*.json"):
        try:
            if date.fromisoformat(f.stem) < cutoff:
                continue
        except ValueError:
            continue
        for day in json.loads(f.read_text()).get("days", []):
            m = day.get("meal")
            if m and m.get("title"):
                titles.add(m["title"])
    return titles


def pasta_used_this_month(week_start: date) -> bool:
    if not MEAL_PLANS_DIR.exists():
        return False
    for f in MEAL_PLANS_DIR.glob("*.json"):
        try:
            d = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if d.year != week_start.year or d.month != week_start.month:
            continue
        for day in json.loads(f.read_text()).get("days", []):
            m = day.get("meal")
            if not m:
                continue
            text = (m.get("title", "") + " " + " ".join(m.get("tags", []))).lower()
            if any(w in text for w in PASTA_WORDS):
                return True
    return False


def is_forbidden(recipe: dict) -> bool:
    text = " ".join(i.get("item", "") for i in recipe.get("ingredients", [])).lower()
    text += " " + recipe.get("title", "").lower()
    return any(w in text for w in PEA_WORDS) or any(w in text for w in AVOCADO_WORDS)


def is_pumpkin(recipe: dict) -> bool:
    text = (recipe.get("title", "") + " " +
            " ".join(i.get("item", "") for i in recipe.get("ingredients", []))).lower()
    return "pumpkin" in text


def filter_eligible(recipes: list, week_start: date, used: set) -> list:
    pumpkin_ok = week_start.month in (9, 10, 11)
    return [
        r for r in recipes
        if r["title"] not in used
        and not is_forbidden(r)
        and (pumpkin_ok or not is_pumpkin(r))
    ]


def slim(r: dict) -> dict:
    """Minimal recipe representation for planning — excludes steps and amounts."""
    return {
        "title": r["title"],
        "chef": r.get("chef", ""),
        "source_type": r.get("source_type", ""),
        "time_minutes": r.get("time_minutes"),
        "servings": r.get("servings"),
        "tags": r.get("tags", []),
        "ingredients": [i["item"] for i in r.get("ingredients", [])],
    }


def call_claude(week_start: date, eligible: list, pasta_ok: bool) -> dict:
    days = week_days(week_start)
    day_list = "\n".join(f"  {name} {d.isoformat()}" for d, name in days)
    pasta_rule = (
        "Pasta is allowed this week (max one pasta dish)."
        if pasta_ok else
        "PASTA ALREADY USED THIS MONTH — exclude all pasta recipes this week."
    )

    prompt = f"""Plan a week of dinners for a family of 3 (2 adults + toddler, 2.5 effective servings per meal).

WEEK:
{day_list}

RULES — apply all strictly:
- Mon–Thu: cooking meals only, max 45 min cook time
- Friday: ALWAYS a rest day — no exceptions
- Sat–Sun: any cook time, more ambitious OK
- Aim for 3–4 cooking nights total (max 5). Never schedule two cooking nights in a row.
- One vegetarian meal per week (Wednesday preferred)
- No protein appearing more than twice across the week
- Mix chefs and source types — not all from one chef
- Prefer Caroline Chambers recipes on weeknights
- Max one soup/stew/chili/gumbo per week
- At least one meal featuring a vegetable (broccoli, spinach, kale, carrot, squash, eggplant, zucchini, cauliflower, beet, sweet potato)
- Skip any recipe with servings < 2.5
- {pasta_rule}

ELIGIBLE RECIPES:
{json.dumps([slim(r) for r in eligible], indent=2)}

OUTPUT: Return JSON only — no explanation, no markdown fences. Schema:
{{
  "week_of": "{week_start.isoformat()}",
  "updated": "{date.today().isoformat()}",
  "days": [
    {{"date": "YYYY-MM-DD", "day": "Monday", "recipe_title": "Exact Recipe Title", "rest_day": false, "rest_day_label": ""}},
    {{"date": "YYYY-MM-DD", "day": "Friday", "recipe_title": null, "rest_day": true, "rest_day_label": "Takeout or leftovers"}}
  ]
}}

Use recipe_title: null and rest_day: true for all non-cooking days. Include all 7 days.
Recipe titles must match exactly from the eligible list above.
"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    return json.loads(text)


def enrich(schedule: dict, all_recipes: list) -> dict:
    """Swap recipe_title references for full recipe objects from recipes.json."""
    recipe_map = {r["title"]: r for r in all_recipes}
    full_days = []
    for day in schedule["days"]:
        title = day.get("recipe_title")
        if day.get("rest_day") or not title:
            full_days.append({
                "date": day["date"],
                "day": day["day"],
                "meal": None,
                "rest_day": True,
                "rest_day_label": day.get("rest_day_label", "Takeout or leftovers"),
            })
        else:
            recipe = recipe_map.get(title) or next(
                (r for r in all_recipes if r["title"].lower() == title.lower()), None
            )
            if not recipe:
                raise ValueError(f"Recipe not found in recipes.json: {title!r}")
            full_days.append({
                "date": day["date"],
                "day": day["day"],
                "meal": recipe,
                "rest_day": False,
                "rest_day_label": "",
            })
    return {
        "week_of": schedule["week_of"],
        "updated": schedule["updated"],
        "days": full_days,
    }


def save(plan: dict, week_start: date):
    s = week_start.isoformat()
    MEAL_PLANS_DIR.mkdir(exist_ok=True)
    (MEAL_PLANS_DIR / f"{s}.json").write_text(json.dumps(plan, indent=2))
    (PLANS_DIR / f"{s}.json").write_text(json.dumps(plan, indent=2))
    (ROOT / "plan.json").write_text(json.dumps(plan, indent=2))

    weeks_path = PLANS_DIR / "weeks.json"
    weeks = json.loads(weeks_path.read_text())
    if s not in weeks:
        weeks.append(s)
        weeks.sort()
        weeks_path.write_text(json.dumps(weeks))

    print(f"Saved plan for week of {s}")


def main():
    week_start = next_monday()
    print(f"Generating plan for week of {week_start}")

    if (PLANS_DIR / f"{week_start.isoformat()}.json").exists():
        print("Plan already exists — skipping.")
        sys.exit(0)

    recipes = json.loads((ROOT / "recipes.json").read_text())
    used = recently_used(weeks=3)
    pasta_ok = not pasta_used_this_month(week_start)
    eligible = filter_eligible(recipes, week_start, used)

    print(f"{len(recipes)} total recipes, {len(eligible)} eligible, {len(used)} recently used")
    print(f"Pasta allowed this week: {pasta_ok}")

    schedule = call_claude(week_start, eligible, pasta_ok)
    plan = enrich(schedule, recipes)

    assert len(plan["days"]) == 7, f"Expected 7 days, got {len(plan['days'])}"
    save(plan, week_start)
    print("Done.")


if __name__ == "__main__":
    main()
