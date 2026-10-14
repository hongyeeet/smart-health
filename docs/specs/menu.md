# Meal suggestions menu (E9)

Decided by Hong Yi on 2026-10-14. A menu-style page, like a food-delivery app, of dishes for one meal. The mock-up is the artifact "Meal suggestions delivery mockup".
It replaces the old "Lunch ideas" cards as the place to browse ideas (E8 stays for the reminder link). The care-team rating page K11 is now "Rate the meal ideas" on the Log tab.

## What the person sees
- Tabs Breakfast, Lunch, Dinner, Snack (first tab by the time of day in Singapore). Filters: Lower salt, Lower carbs, Hawker stall, Home cooked.
- Three sections, up to 4 dishes each: **From your own meals** (their own meals of this kind with a lower measured rise than their typical meal, eaten at least twice),
  **Lighter than your usual** (a swap for a food habit the memory loop noticed; lunch and dinner only), **Worth a try** (database dishes; general, not personal).
- A dish card: picture, badge (Measured on you, seen N times, or Estimate), name, serving, kcal, carbs, salt, why, and the glucose rise.
- "Your picks": up to three dishes; "Log when I eat" stamps them as picked and opens the meal log. (A "Remind me" button was in the mock and is not built.)

## Numbers (all in code, `app/services/menu.py`)
- A rise is **measured** only for the person's own meals. For other dishes it is an **estimate**: the dish's carbohydrate times the person's own median rise per gram of
  carbohydrate (from their own meals with 10 g of carbs or more), shown as a range of plus or minus 0.5 mmol/L. With no such history there is **no number** ("Glucose rise not known yet").
- kcal for their own meals is worked out from the logged macros (4, 4 and 9 kcal per gram); for database dishes it is the published value.
- Tag cut-offs are **placeholders pending the clinical owner**: lower salt at or below 700 mg, lower carbs at or below 45 g. A person's own meals have no hawker or home tag (not known).
- The typical time on the active tab is the median time the person logs that meal (last 20, needs 5), otherwise 7:30 am, 12:15 pm, 6:30 pm, 4:00 pm.

## Pictures (`app/services/food_images.py`)
- One picture per DISH, shared by every person. `food_images.dish_key` is the dish name lower-cased, letters and digits joined by dashes.
- A dish seen for the first time gets a `pending` row. A background job (every minute, at most 3 pictures) and the menu request itself make it with **`gemini-2.5-flash-image`** on Vertex
  (the project's existing Vertex key works; no extra credentials). The result is shrunk to an 800 by 600 JPEG and stored in the **private** bucket `food-images`; the app loads it through
  `GET /api/v1/nutrition/food-image/{key}` with a one-year immutable cache header.
- A `ready` dish is **never generated again**, and opening the page never generates a picture: it only reads the row. A failed one is retried after 15 minutes, at most 3 times in all.
  A daily cap `AI_CAP_VERTEX_IMAGE` (default 60) stops the worker; the dish keeps a plain placeholder until the next day. The page asks again every 8 seconds, up to 10 times, while pictures are waiting.
- Only the dish name is sent to the model (a fixed prompt: overhead photo, plain light background, no text, no people). The page tells the person the pictures are AI-made and only a guide.

## Data (Alembic 0039)
- `food_images` (Reference): `dish_key` primary key, `name`, `status` (pending, generating, ready, failed), `storage_key`, `model`, `prompt_hash`, `attempts`, `last_error` (a code, no private detail), timestamps.
- `food_suggestions` (App): what was shown to one person for one meal on one day (`user_id`, `day`, `meal`, `suggestion_key`, `section`, `dish_key`, `name`, `payload` jsonb), and `picked_at`. Unique per person, day, meal and key.

## Endpoints
`GET /api/v1/nutrition/menu?meal=` (builds, stores, queues missing pictures), `GET /api/v1/nutrition/food-image/{key}` (public picture, immutable), `POST /api/v1/nutrition/menu/pick` (stamps `picked_at` and counts the suggestion as acted on).

## Settings
`FOOD_IMAGE_MODEL` (default `gemini-2.5-flash-image`), `FOOD_IMAGE_BUCKET` (default `food-images`), `AI_CAP_VERTEX_IMAGE` (default 60).

## Not built
A "Remind me" button; a Quick filter (it cannot be worked out from the data); pictures of dishes in other languages; removing or replacing a bad picture (set the row back to `pending` and `attempts` to 0 to make a new one).
