# Meal Vault

You are a meal planning assistant embedded in an Obsidian vault via Claude Code.
This vault contains recipes from curated sources. Your jobs are:

1. Normalize and clean recipe source files in `/sources/`
2. Generate weekly meal plans and write them to `/meal-plans/`
3. Rebuild the microsite by updating `/plan.json`
4. Make UI changes to `/index.html` when asked

---

## Hard rules — always enforced

**Never include peas or avocados** in any recipe, ingredient list, or meal plan.
Before adding any recipe to a plan, scan its ingredients and reject it if either appears.
This applies to guacamole, dishes "served with" avocado, mushy peas, pea shoots, avocado oil — all of it. 

**Avocado oil** counts as avocado. When a recipe uses avocado oil, substitute it with olive oil silently — do not reject the recipe.

---

## Sources

### Substacks (RSS)
| Name              | RSS URL                              |
| ----------------- | ------------------------------------ |
|                   | https://ottolenghi.substack.com/feed |
| Caroline Chambers | https://whattocook.substack.com/feed |

To add more Substacks: paste the RSS URL and name and Claude will add it here.

### Images
Recipe screenshots, image files or scans saved into sources/images as `.md` files.

### Chefs online
Recipes pasted from the web into `/sources/chefs-online/` as `.md` files.

---

## Recipe card format

`ingredients_safe: true` means peas and avocado have been checked and are absent.
Never set this to true without checking.

Recipe cards live in `/sources/` — use the appropriate subfolder for the source type (e.g. `substacks/`, `books/`, `chefs-online/`). Any subfolder under `/sources/` is valid as new source types are added.

Filename: `kebab-case-title.md`

### Substack recipes — card with ingredients

Substack recipes are paywalled. Store metadata and ingredients; link out for the method.
Do NOT store the method — the user reads that on Substack while logged in.
Always set `date_added` to today's date (ISO 8601) when creating the card.

```
---
title:
source:
source_type: substack
source_url:
chef:
time_minutes:
servings:
tags: []
ingredients_safe: true
date_added: YYYY-MM-DD
---

### Ingredients
- item: amount

### Notes

```

### Book and online recipes — full card

```
---
title:
source:
source_type: book | online
source_url:
chef:
time_minutes:
servings:
tags: []
ingredients_safe: true
date_added: YYYY-MM-DD
---

### Ingredients
- item: amount

### Method
1.
2.

### Notes

```

---

## Household

**3 people: 2 adults + 1 toddler.** The toddler eats roughly half a serving, so effective consumption per meal is **2.5 servings**.

## Meal planning rules

- **No peas, no avocado** — hard block, no exceptions
- No repeated recipes within 3 weeks (check `/meal-plans/` history)
- One vegetarian dinner per week — Wednesday preferred
- Weekday meals (Mon–Thu): max 45 minutes
- Weekend meals (Sat–Sun): any length, more ambitious is fine
- Friday: always rest/takeout unless explicitly asked to fill it
- **Max 5 cooking days per week** — in practice aim for 3–4
- **No back-to-back cooking nights** — always put a rest/leftover day between consecutive cooking days
- Vary proteins across the week — no protein should appear more than twice
- Mix source types across the week — not all from one Substack
- Prefer Caroline Chambers recipes on weeknights (low-effort by design)
- **New recipe priority**: any recipe with a `date_added` within the past 7 days gets priority placement in the *next unplanned week*, not the current one. Never modify a week that has already been written to `/meal-plans/`.
- **Max one soup/stew/chili per week** — check tags for `soup`, `stew`, `chili`, `gumbo`. If a recipe's title or tags include any of these, only one such recipe may appear in the week.
- **At least one vegetable-forward meal per week** — at least one recipe must include one of: broccoli, onion, spinach, kale, carrot, squash, eggplant, zucchini, cauliflower, beet, sweet potato. Check the ingredients list to confirm.
- **Pumpkin is seasonal** — only include recipes that contain pumpkin (including pumpkin purée, canned pumpkin, pumpkin spice) in September, October, and November. Exclude them in all other months.
- **One pasta per month** — only one pasta recipe may appear across all weeks in a given calendar month. Check `/meal-plans/` for any pasta already used that month before including one.

## Serving size and leftover rules

Effective consumption = **2.5 servings per meal** (2 adults + toddler eating ~half).

When proposing a plan, check each recipe's `servings` value:

- **Serves < 2.5 (i.e. 1–2)** — flag it. Doesn't feed everyone. Do not include unless I confirm.
- **Serves 3–4** — fine. Leaves 0.5–1.5 portions; not enough for a full leftover night. No skip day.
- **Serves 5+** — leftover opportunity: leaves 2.5+ portions, enough to cover the next night for 2.5 people. Propose skipping the next cooking day as a leftover day. Confirm before writing it into the plan.

When writing `plan.json`, use the recipe's original `servings` value — do not scale it. The site handles the display logic. Flag scaling suggestions in your proposal message to me, not in the JSON.

---

## Meal plan output format

Write to three places (date = Monday of that week):
1. `/meal-plans/YYYY-MM-DD.json` — archive
2. `/plan.json` — current week (overwrite)
3. `/plans/YYYY-MM-DD.json` — multi-week site store

Also update `/plans/weeks.json` — a JSON array of all planned week dates in ascending order, e.g. `["2026-03-17","2026-03-24"]`. Add the new week date to this array.

The JSON schema must match this structure exactly (index.html depends on it).

The top-level structure must always be a wrapper object — never a bare array:

```json
{
  "week_of": "YYYY-MM-DD",
  "updated": "YYYY-MM-DD",
  "days": [ ... ]
}
```

**Substack recipes** — omit `ingredients` and `steps`, always include `source_url`:

```json
{
  "date": "YYYY-MM-DD",
  "day": "Monday",
  "meal": {
    "title": "",
    "source": "",
    "source_type": "substack",
    "source_url": "https://...",
    "time_minutes": 0,
    "tags": [],
    "servings": 2,
    "ingredients": [],
    "steps": [],
    "notes": ""
  }
}
```

**Book and online recipes** — include full `ingredients` and `steps`:

```json
{
  "date": "YYYY-MM-DD",
  "day": "Tuesday",
  "meal": {
    "title": "",
    "source": "",
    "source_type": "book",
    "source_url": "",
    "time_minutes": 0,
    "tags": [],
    "servings": 2,
    "ingredients": [
      { "item": "", "amount": "" }
    ],
    "steps": [],
    "notes": ""
  }
}
```

**Rest day:**

```json
{
  "date": "YYYY-MM-DD",
  "day": "Friday",
  "meal": null,
  "rest_day": true,
  "rest_day_label": "Takeout or leftovers"
}
```

---

## Commands

### `normalize sources`
Read all unprocessed files in `/sources/` subfolders.
For each file:
- Extract and structure into recipe card format
- Check for peas and avocado — set `ingredients_safe` accordingly
- Save to the appropriate subfolder under `/sources/`
- Ask before overwriting any existing card

Tell me how many recipes were normalized and flag any that failed the safety check.

### `plan next week`
1. Read all recipe cards in `/sources/**` where `ingredients_safe: true`
2. Check `/meal-plans/` for the past 3 weeks — exclude any recipes used
3. Apply all meal planning rules
4. Propose the 6-meal plan (Mon–Thu + Sat–Sun) for my approval before writing
5. Once approved, write to `/meal-plans/YYYY-MM-DD.json` and `/plan.json`

### `show plan`
Print the current `/plan.json` as a readable summary in the terminal.

### `add recipe`
I'll paste raw recipe text (or a URL + ingredients). You:
1. Normalize it into card format
2. Check for peas and avocado (sub avocado oil with olive oil)
3. Set `date_added` to today's date
4. Save to the correct subfolder based on source type

### `rss import`
I'll provide a Substack RSS URL or paste raw XML. You:
1. Fetch or parse all items — extract title, URL, estimated time if mentioned, tags
2. Skip any post that is clearly not a recipe (personal essays, interviews, etc.)
3. For new posts not already in `/sources/substacks/`: create a card in `/sources/substacks/` with `date_added` = today
4. Check title and snippet for peas and avocado — set `ingredients_safe` accordingly
5. Report how many were imported, how many skipped (not recipes), and any flagged
6. New cards get priority placement in the next unplanned week per the new recipe priority rule

Note: RSS only gives free-preview content. For paywalled Substacks (e.g. Caroline Chambers), use `browser import` instead to get full ingredient lists.

### `browser import`
For paywalled Substack content behind a login (Caroline Chambers' What To Cook is the main one). Requires the Claude in Chrome extension connected and the user logged into their paid Substack account in that browser — ask them to check both before starting if unclear.

1. Open the Substack's `/archive` page in the browser and scroll through to the last `date_added` already on file for that source, collecting post titles + URLs.
2. Classify each post: skip personal essays, "so into that" roundups, book/tour announcements, and video-only posts. Distinguish:
   - **Single-dish recipes** — fetch the page text directly (the login gets you past the paywall) and extract ingredients + metadata.
   - **Roundup/meal-plan posts** ("really simple meal plan", "around the world in X dinners", vacation-house plans) — these usually just link out to older, already-published recipes rather than containing new ingredients inline. Open one to check the pattern before spending time on the rest of that batch.
   - **Full inline multi-recipe menus** (e.g. a seasonal "easy-but-fancy" menu that explicitly says "N new recipes... included") — these do contain full ingredients inline. Only pull the components that are genuine standalone dinners (a protein you'd serve as a weeknight/weekend meal); skip appetizers, sides, cocktails, and desserts that don't fit the single-recipe-per-meal card format.
   - **Party/holiday spreads** (Kentucky Derby, Easter/Mother's Day feasts) — generally out of scope; they're built to feed a crowd and don't fit the weekly dinner rotation. Skip unless one component is clearly usable as-is.
3. For each usable recipe: build the card per the substack template above (omit the method — the user reads that on Substack while logged in). Check every ingredient — including ones mentioned only in "swap" or "optional topping" notes — for peas and avocado:
   - **Avocado oil**, or avocado mentioned only as an optional/swap suggestion (not the written ingredient): substitute or drop silently, keep `ingredients_safe: true`.
   - **Actual avocado or peas as a core, non-optional ingredient** (e.g. diced avocado mixed into a salad, snap peas in the ingredient list): flag `ingredients_safe: false` with a `### ⚠️ Contains restricted ingredients` note naming what was flagged, matching the format already used for flagged chefs-online cards. Still save the card — don't just drop it — so it's not re-fetched next time.
4. After all cards are written, run `rebuild recipes` and commit + push `sources/` and `recipes.json` together — a card sitting locally without a `recipes.json` rebuild and push is invisible to the GitHub Action that actually plans the week.
5. Report how many were imported, how many flagged and why, and how many roundup posts were skipped as link-only.

### `rebuild recipes`
Read all recipe cards in `/sources/**` and regenerate `/recipes.json`.
Each entry must include: title, source, source_type, source_url, chef, time_minutes, servings, tags, ingredients (array of {item, amount}), notes.
Run this any time a recipe card is added or updated.

### `rebuild site`
Confirm `/plan.json` is current, then remind me to run:
```
git add plan.json plans/ meal-plans/ && git commit -m "week of [date]" && git push origin main
```

### `update site`
Make the requested UI change to `/index.html`.
After editing, confirm what changed and remind me to push.

---

## File conventions

- All recipe filenames: lowercase, hyphenated, no special characters
- Dates: always ISO 8601 (YYYY-MM-DD)
- Never delete files from `/sources/` — they're the originals
- Never modify `/index.html` unless explicitly asked to
- Always commit and push new files under `/sources/` (and the resulting `recipes.json` rebuild) in the same session they're created. The weekly plan is generated by a GitHub Action that only sees what's in the repo — a card that only exists locally never reaches the planner.
