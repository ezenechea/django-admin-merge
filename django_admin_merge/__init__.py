"""
Django Admin Merge - Reusable Django admin action for merging duplicated entries.
"""

__version__ = "0.1.0"

# Configure the default app config
default_app_config = "django_admin_merge.apps.DjangoAdminMergeConfig"

# Make key classes easily importable
from .admin import (
    MergeMixin,
    MergeModelAdmin,
    auto_register_merge_action,
    merge_entries_action,
)

__all__ = [
    "MergeModelAdmin",
    "MergeMixin",
    "merge_entries_action",
    "auto_register_merge_action",
]
