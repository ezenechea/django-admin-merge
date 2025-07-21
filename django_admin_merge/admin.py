# django_admin_merge/admin.py
from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path


class MergeModelAdmin(admin.ModelAdmin):
    actions = ["merge_entries"]

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

    def merge_entries(self, request, queryset):
        if queryset.count() < 2:
            self.message_user(
                request, "Select at least two entries to merge.", level=messages.ERROR
            )
            return
        selected = queryset.values_list("pk", flat=True)
        return redirect(f'./merge/?ids={",".join(map(str, selected))}')

    merge_entries.short_description = "Merge selected entries"

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
        )        )