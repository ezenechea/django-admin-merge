# django-admin-merge
Merge model entries with an action.

Add 'django_admin_merge' to INSTALLED_APPS.

from django_admin_merge.admin import MergeModelAdmin

@admin.register(City)
class CityAdmin(MergeModelAdmin):
    ...
