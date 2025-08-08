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
        # Import here to avoid circular imports
        from .admin import auto_register_merge_action

        # Uncomment and customize one of the following lines:
        # Option 1: Add merge to ALL admins
        # auto_register_merge_action()
        # Option 2: Add merge to all admins except specific models
        # auto_register_merge_action(exclude_models=['auth.User', 'auth.Group'])
        # Option 3: Add merge to all admins except specific apps
        # auto_register_merge_action(exclude_apps=['auth', 'contenttypes', 'sessions'])
        # Option 4: Combine both exclusions
        # auto_register_merge_action(
        #     exclude_models=['myapp.SensitiveModel'],
        #     exclude_apps=['auth', 'sessions']
        # )

        pass
