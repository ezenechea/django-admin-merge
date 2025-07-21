from setuptools import find_packages, setup

setup(
    name="django-admin-merge",
    version="0.1.0",
    description="Reusable Django admin action for merging duplicated entries.",
    author="Ezequiel Aurtenechea",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["django"],
    license="MIT",
    # Add this to make the package importable as django_admin_merge
    py_modules=[],
)
