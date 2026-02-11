# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

django-admin-merge is a reusable Django package that adds merge functionality to the Django admin interface. It allows users to select multiple duplicate entries and merge them into one, automatically handling ForeignKey and ManyToMany relationship transfers within an atomic transaction.

## Build & Install

```bash
pip install -e .
```

No test suite exists yet. No linter or formatter is configured.

## Architecture

The entire package lives in `django_admin_merge/` with a single core module (`admin.py`) and no Django models.

### admin.py — Core Logic (~300 lines)

Four public exports:

- **`merge_entries_action(modeladmin, request, queryset)`** — Standalone admin action function. Validates >=2 selected entries, then redirects to the merge view with object IDs as query params.
- **`MergeMixin`** — ModelAdmin mixin that injects the merge action and registers a custom `merge/` URL via `get_urls()`. The `merge_view` method handles GET (display candidates with related objects) and POST (atomic merge: reassign FKs, merge M2M, delete duplicates).
- **`MergeModelAdmin`** — Convenience class combining `MergeMixin` + `admin.ModelAdmin`.
- **`auto_register_merge_action(exclude_models=None, exclude_apps=None)`** — Dynamically wraps all registered ModelAdmin classes with `MergeMixin` by unregistering and re-registering them. Supports exclusion by model class, `'app_label.ModelName'` string, model name string, or app label.

### Merge flow

1. User selects entries in admin changelist → `merge_entries_action` redirects to `<model>/merge/?ids=1,2,3`
2. `merge_view` GET: queries objects, builds `related_map` (dict of pk → list of `(str, admin_url)` tuples) by inspecting `model._meta.related_objects` (FK) and `model._meta.get_fields()` (M2M)
3. `merge_view` POST: inside `transaction.atomic()`, updates FK references, adds M2M relations to kept object, deletes duplicates

### Template & Fallback

- `templates/admin/merge_entries.html` extends `admin/base_site.html` and uses a custom `get_item` template filter from `templatetags/get_item.py` to look up dict values by key in templates
- If the template fails to load, `merge_view` falls back to inline HTML rendering

### Integration methods (in order of scope)

1. `auto_register_merge_action()` — all admins at once (call in `urls.py` after apps load)
2. `MergeModelAdmin` as base class
3. `MergeMixin` mixed into existing admin
4. `merge_entries_action` added to a ModelAdmin's `actions` list (note: this alone won't register the merge URL, so it only works if the mixin is also present or URL is otherwise available)
