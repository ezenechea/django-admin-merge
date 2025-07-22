# django_admin_merge/admin.py
from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path


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

    # Build the merge URL for this specific model
    app_label = model._meta.app_label
    model_name = model._meta.model_name
    merge_url = (
        f'/admin/{app_label}/{model_name}/merge/?ids={",".join(map(str, selected))}'
    )

    return redirect(merge_url)


merge_entries_action.short_description = "Merge selected entries"


class MergeMixin:
    """
    Mixin class to add merge functionality to any ModelAdmin.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add the merge action to the admin's actions
        if not hasattr(self, "actions"):
            self.actions = []
        if isinstance(self.actions, tuple):
            self.actions = list(self.actions)
        if merge_entries_action not in self.actions:
            self.actions.append(merge_entries_action)

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
        related_map = {}
        for obj in objects:
            related_map[obj.pk] = []
            # ForeignKey relations
            for related in model._meta.related_objects:
                rel_model = related.related_model
                fk_name = related.field.name
                rel_objs = rel_model.objects.filter(**{fk_name: obj})
                for rel_obj in rel_objs:
                    url = f"/admin/{rel_model._meta.app_label}/{rel_model._meta.model_name}/{rel_obj.pk}/change/"
                    related_map[obj.pk].append((str(rel_obj), url))
            # ManyToMany relations
            for field in model._meta.get_fields():
                if field.many_to_many and not field.auto_created:
                    m2m_objs = getattr(obj, field.name).all()
                    for m2m_obj in m2m_objs:
                        url = f"/admin/{m2m_obj._meta.app_label}/{m2m_obj._meta.model_name}/{m2m_obj.pk}/change/"
                        related_map[obj.pk].append((str(m2m_obj), url))

        if request.method == "POST":
            keep_id = request.POST.get("keep")
            keep_obj = model.objects.get(pk=keep_id)
            remove_ids = [obj.pk for obj in objects if str(obj.pk) != keep_id]
            with transaction.atomic():
                # Update all FK relations in other models
                for related in model._meta.related_objects:
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
            # Redirect to model listview
            app_label = model._meta.app_label
            model_name = model._meta.model_name
            return redirect(f"/admin/{app_label}/{model_name}/")

        return render(
            request,
            "admin/merge_entries.html",
            {
                "objects": objects,
                "opts": model._meta,
                "related_map": related_map,
            },
        )


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
                for model, admin_class in site._registry.items():
                    if (
                        model._meta.app_label == app_label
                        and model._meta.model_name.lower() == model_name.lower()
                    ):
                        excluded_model_classes.add(model)
            else:
                # Just model name, search across all apps
                for model, admin_class in site._registry.items():
                    if model._meta.model_name.lower() == exclude_item.lower():
                        excluded_model_classes.add(model)
        else:
            # Assume it's a model class
            excluded_model_classes.add(exclude_item)

    for model, admin_class in site._registry.items():
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
