# django_admin_merge/admin.py
from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path, reverse


def merge_entries_action(modeladmin, request, queryset):
    """
    Global admin action that can be used with any model.
    """
    if queryset.count() < 2:
        modeladmin.message_user(
            request, "Select at least two entries to merge.", level=messages.ERROR
        )
        return

    model = queryset.model
    selected = queryset.values_list("pk", flat=True)

    # Build the merge URL for this specific model using reverse

    try:
        # Try to build the URL using the custom URL name pattern
        base_url = reverse(
            f"admin:{model._meta.app_label}_{model._meta.model_name}_merge"
        )
        merge_url = f'{base_url}?ids={",".join(map(str, selected))}'
    except:
        # Fallback to the relative URL pattern
        merge_url = f'merge/?ids={",".join(map(str, selected))}'

    return redirect(merge_url)


merge_entries_action.short_description = "Merge selected entries"


class MergeMixin:
    """
    Mixin class to add merge functionality to any ModelAdmin.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add the merge action to the admin's actions
        actions = getattr(self, "actions", None)
        if actions is None:
            actions = []
        elif isinstance(actions, tuple):
            actions = list(actions)
        if merge_entries_action not in actions:
            actions.append(merge_entries_action)
        self.actions = actions

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "merge/",
                self.admin_site.admin_view(self.merge_view),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_merge",
            ),
        ]
        return custom_urls + urls

    def merge_view(self, request):

        ids = request.GET.get("ids", "").split(",")
        model = self.model
        objects = model.objects.filter(pk__in=ids)

        # Debug: Check if we have objects
        if not objects.exists():
            self.message_user(
                request, "No objects found with the provided IDs.", level=messages.ERROR
            )
            # Use reverse to get the correct admin URL
            list_url = reverse(
                f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
            )
            return redirect(list_url)

        related_map = {}
        for obj in objects:
            related_map[obj.pk] = []
            # ForeignKey relations
            for related in model._meta.related_objects:
                if related.field.many_to_many:
                    continue
                rel_model = related.related_model
                fk_name = related.field.name
                rel_objs = rel_model.objects.filter(**{fk_name: obj})
                for rel_obj in rel_objs:
                    try:
                        # Use reverse to get the correct admin URL
                        url = reverse(
                            f"admin:{rel_model._meta.app_label}_{rel_model._meta.model_name}_change",
                            args=[rel_obj.pk],
                        )
                        related_map[obj.pk].append((str(rel_obj), url))
                    except:
                        # Fallback if reverse fails
                        related_map[obj.pk].append((str(rel_obj), "#"))
            # ManyToMany relations
            for field in model._meta.get_fields():
                if field.many_to_many and not field.auto_created:
                    m2m_objs = getattr(obj, field.name).all()
                    for m2m_obj in m2m_objs:
                        try:
                            # Use reverse to get the correct admin URL
                            url = reverse(
                                f"admin:{m2m_obj._meta.app_label}_{m2m_obj._meta.model_name}_change",
                                args=[m2m_obj.pk],
                            )
                            related_map[obj.pk].append((str(m2m_obj), url))
                        except:
                            # Fallback if reverse fails
                            related_map[obj.pk].append((str(m2m_obj), "#"))

        if request.method == "POST":
            keep_id = request.POST.get("keep")
            keep_obj = model.objects.get(pk=keep_id)
            remove_ids = [obj.pk for obj in objects if str(obj.pk) != keep_id]
            with transaction.atomic():
                # Update all FK relations in other models
                for related in model._meta.related_objects:
                    if related.field.many_to_many:
                        continue
                    rel_model = related.related_model
                    fk_name = related.field.name
                    rel_qs = rel_model.objects.filter(**{f"{fk_name}__in": remove_ids})
                    rel_qs.update(**{fk_name: keep_obj})
                # Update ManyToMany relations
                for field in model._meta.get_fields():
                    if field.many_to_many and not field.auto_created:
                        m2m_field = getattr(keep_obj, field.name)
                        for obj in objects:
                            if obj.pk != keep_obj.pk:
                                m2m_values = getattr(obj, field.name).all()
                                m2m_field.add(*m2m_values)
                # Delete unwanted objects
                model.objects.filter(pk__in=remove_ids).delete()
            self.message_user(
                request, f"Merged entries into '{keep_obj}'.", level=messages.SUCCESS
            )
            # Redirect to model listview using reverse
            list_url = reverse(
                f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
            )
            return redirect(list_url)

        # Try to render the template, fallback to simple HTML if template not found
        try:
            return render(
                request,
                "admin/merge_entries.html",
                {
                    "objects": objects,
                    "opts": model._meta,
                    "related_map": related_map,
                    "title": f"Merge {model._meta.verbose_name_plural}",
                },
            )
        except Exception as e:
            # Fallback: render a simple inline template if the package template isn't found
            from django.http import HttpResponse
            from django.middleware.csrf import get_token

            csrf_token = get_token(request)
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Merge Entries</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    label {{ display: block; margin: 10px 0; }}
                    input[type="radio"] {{ margin-right: 10px; }}
                    ul {{ margin-left: 20px; }}
                    button {{ padding: 10px 20px; background: #007cba; color: white; border: none; cursor: pointer; }}
                    button:hover {{ background: #005a87; }}
                </style>
            </head>
            <body>
                <h1>Merge {model._meta.verbose_name_plural}</h1>
                <form method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                    <p>Select the entry to keep:</p>
            """
            for i, obj in enumerate(objects):
                checked = "checked" if i == 0 else ""
                html += f'<label><input type="radio" name="keep" value="{obj.pk}" {checked}> {obj}</label>'

                # Show related objects
                rels = related_map.get(obj.pk, [])
                if rels:
                    html += "<ul>"
                    for rel, url in rels:
                        html += f'<li><a href="{url}" target="_blank">{rel}</a></li>'
                    html += "</ul>"
                else:
                    html += "<ul><li>No related objects</li></ul>"
                html += "<br>"

            html += """
                    <button type="submit">Merge</button>
                    <br><br>
                    <a href="javascript:history.back()">← Back to list</a>
                </form>
            </body>
            </html>
            """
            return HttpResponse(html)


class MergeModelAdmin(MergeMixin, admin.ModelAdmin):
    """
    ModelAdmin class with merge functionality built-in.
    Use this as a base class for your model admins.
    """

    pass


# Auto-apply merge functionality to ALL registered admins
def auto_register_merge_action(exclude_models=None, exclude_apps=None):
    """
    Automatically add merge functionality to all currently registered ModelAdmin classes.
    Call this function after all your apps have been loaded.

    Args:
        exclude_models (list): List of model classes or model names to exclude.
                              Can be Model classes, 'app_label.ModelName' strings,
                              or just 'ModelName' strings.
        exclude_apps (list): List of app labels to exclude entirely.
                            For example: ['auth', 'contenttypes', 'sessions']

    Examples:
        # Exclude specific models
        auto_register_merge_action(exclude_models=[User, 'auth.Group', 'MyModel'])

        # Exclude entire apps
        auto_register_merge_action(exclude_apps=['auth', 'contenttypes'])

        # Exclude both
        auto_register_merge_action(
            exclude_models=['myapp.SensitiveModel'],
            exclude_apps=['auth', 'sessions']
        )
    """
    from django.contrib.admin import site

    if exclude_models is None:
        exclude_models = []
    if exclude_apps is None:
        exclude_apps = []

    # Normalize exclude_models to a set of model classes
    excluded_model_classes = set()
    for exclude_item in exclude_models:
        if isinstance(exclude_item, str):
            # Handle string formats like 'app_label.ModelName' or 'ModelName'
            if "." in exclude_item:
                app_label, model_name = exclude_item.split(".", 1)
                # Find the model by app_label and model_name
                for model, admin_class in list(site._registry.items()):
                    if (
                        model._meta.app_label == app_label
                        and model._meta.model_name.lower() == model_name.lower()
                    ):
                        excluded_model_classes.add(model)
            else:
                # Just model name, search across all apps
                for model, admin_class in list(site._registry.items()):
                    if model._meta.model_name.lower() == exclude_item.lower():
                        excluded_model_classes.add(model)
        else:
            # Assume it's a model class
            excluded_model_classes.add(exclude_item)

    for model, admin_class in list(site._registry.items()):
        # Skip if model is in excluded models
        if model in excluded_model_classes:
            continue

        # Skip if model's app is in excluded apps
        if model._meta.app_label in exclude_apps:
            continue

        # Check if the admin class already has merge functionality
        if not isinstance(admin_class, MergeMixin):
            # Create a new admin class that inherits from both MergeMixin and the current admin
            new_admin_class = type(
                f"Merge{admin_class.__class__.__name__}",
                (MergeMixin, admin_class.__class__),
                {},
            )

            # Unregister the old admin and register the new one
            site.unregister(model)
            site.register(model, new_admin_class)
