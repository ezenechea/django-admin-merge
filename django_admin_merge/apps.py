# django_admin_merge/apps.py
from django.apps import AppConfig


class DjangoAdminMergeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_admin_merge"
    verbose_name = "Django Admin Merge"

    def ready(self):
        """
        This method is called when Django starts up.
        We can use it to automatically add merge functionality to all admin classes.
        """
        pass
