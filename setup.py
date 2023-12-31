from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in frappe_json/__init__.py
from frappe_json import __version__ as version

setup(
	name="frappe_json",
	version=version,
	description="A Frappe app to generate Json of doctypes automatically for react forms",
	author="Sameed Hasan",
	author_email="sameedh41@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
