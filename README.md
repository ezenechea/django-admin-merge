# django-admin-merge

Reusable Django admin action for merging duplicated entries. This package provides multiple ways to add merge functionality to your Django admin interface.

## Installation

1. Install the package:
```bash
poetry add git+https://github.com/ezenechea/django-admin-merge.git
```

2. Add to your Django settings:
```python
INSTALLED_APPS = [
    # ... other apps
    'django_admin_merge',
]
```

## Usage

There are several ways to add merge functionality to your admin:

### Method 1: Auto-apply to ALL registered admins (with exclusions)

If you want to add merge functionality to ALL your model admins automatically, you can call this function with optional exclusions:

```python
# In your main urls.py (after all apps are loaded)
from django_admin_merge import auto_register_merge_action

# Add to ALL registered model admins
auto_register_merge_action()

# Or exclude specific models
from django.contrib.auth.models import User, Group
auto_register_merge_action(exclude_models=[User, Group])

# Or exclude by model name strings
auto_register_merge_action(exclude_models=['auth.User', 'auth.Group', 'MyModel'])

# Or exclude entire apps
auto_register_merge_action(exclude_apps=['auth', 'contenttypes', 'sessions'])

# Or combine both exclusions
auto_register_merge_action(
    exclude_models=['myapp.SensitiveModel'],
    exclude_apps=['auth', 'sessions']
)
```



### Method 2: Using MergeModelAdmin (Recommended for new admins)

```python
from django.contrib import admin
from django_admin_merge.admin import MergeModelAdmin
from .models import YourModel

@admin.register(YourModel)
class YourModelAdmin(MergeModelAdmin):
    list_display = ['name', 'email']  # your fields
    # ... other admin configuration
```

### Method 3: Using MergeMixin (For existing admins)

```python
from django.contrib import admin
from django_admin_merge.admin import MergeMixin
from .models import YourModel

@admin.register(YourModel)
class YourModelAdmin(MergeMixin, admin.ModelAdmin):
    list_display = ['name', 'email']  # your fields
    # ... your existing admin configuration
```

### Method 4: Adding merge action to specific admins

```python
from django.contrib import admin
from django_admin_merge.admin import merge_entries_action
from .models import YourModel

@admin.register(YourModel)
class YourModelAdmin(admin.ModelAdmin):
    actions = [merge_entries_action]  # Add this line
    list_display = ['name', 'email']  # your fields
    # ... your existing admin configuration
```




## How it works

1. Select multiple entries in the Django admin list view
2. Choose "Merge selected entries" from the Actions dropdown
3. On the merge page, select which entry to keep
4. The system will:
   - Move all foreign key relationships to the kept entry
   - Merge many-to-many relationships
   - Delete the duplicate entries
   - Redirect back to the model list

## Features

- ✅ Handles ForeignKey relationships automatically
- ✅ Handles ManyToMany relationships automatically  
- ✅ Shows related objects before merging
- ✅ Provides links to edit related objects
- ✅ Transaction-safe (all or nothing)
- ✅ Works with any Django model
- ✅ Multiple integration methods

## Requirements

- Django 3.2+
- Python 3.8+
