import frappe
from pathlib import Path
from .utils import create_file
import subprocess


def create_type_definition_file(doc, method=None):
    # Check if type generation is paused
    common_site_config = frappe.get_conf()

    frappe_types_pause_generation = common_site_config.get(
        "frappe_types_pause_generation", 0
    )

    if frappe_types_pause_generation:
        print("Frappe Types is paused")
        return

    doctype = doc

    if is_developer_mode_enabled() and is_valid_doctype(doctype):
        print("Generating type definition file for " + doctype.name)
        module_name = doctype.module
        app_name = frappe.db.get_value("Module Def", module_name, "app_name")

        if app_name == "frappe" or app_name == "erpnext":
            print("Ignoring core app DocTypes")
            return

        app_path: Path = Path("../apps") / app_name
        if not app_path.exists():
            print("App path does not exist - ignoring type generation")
            return

        # Fetch Json generation Settings Document
        type_generation_settings = (
            frappe.get_doc("Json generation Settings").as_dict().json_settings
        )

        # Checking if app is existed in Json generation Settings
        for type_setting in type_generation_settings:
            if app_name == type_setting.app_name:
                # Types folder is created in the app
                type_path: Path = app_path / type_setting.app_path / "jsons"

                if not type_path.exists():
                    type_path.mkdir()

                module_path: Path = type_path / module_name.replace(" ", "")
                if not module_path.exists():
                    module_path.mkdir()

                generate_type_definition_file(
                    doctype, module_path, generate_child_tables=False
                )
            else:
                return


def generate_type_definition_file(doctype, module_path, generate_child_tables=False):
    doctype_name = doctype.name.replace(" ", "")
    type_file_path = module_path / (doctype_name + ".json")
    type_file_content = generate_type_definition_content(
        doctype, module_path, generate_child_tables
    )
    create_file(type_file_path, type_file_content)


def generate_type_definition_content(doctype, module_path, generate_child_tables):
    generate_type_definition_content.imports = ""
    # print(generate_type_definition_content.imports)
    contentObject = {
        "title": doctype.name.replace(" ", ""),
        "description": "Form description",
        "type": "object",
        "required": [],
        "properties": {},
    }
    content = "export const " + doctype.name.replace(" ", "") + " = [\n"

    # Boilerplate types for all documents
    # content += ""

    for field in doctype.fields:
        if field.fieldtype in [
            "Section Break",
            "Column Break",
            "HTML",
            "Button",
            "Fold",
            "Heading",
            "Tab Break",
            "Break",
        ]:
            continue
        # content += get_field_comment(field)
        if get_optional(field):
            contentObject["properties"][field.fieldname] = get_field_type_definition(
                field, doctype, module_path, generate_child_tables
            )
        else:
            contentObject["properties"][field.fieldname] = get_field_type_definition(
                field, doctype, module_path, generate_child_tables
            )
            contentObject["required"].append(field.fieldname)

        # content += (
        #     "\t"
        #     + str(
        #         get_field_type_definition(
        #             field, doctype, module_path, generate_child_tables
        #         )
        #     )
        #     + ", \n"
        # )

    content += "]"

    content = str(contentObject)
    # print(generate_type_definition_content.imports)
    return generate_type_definition_content.imports + "\n" + content


def get_field_comment(field):
    desc = field.description
    if field.fieldtype in ["Link", "Table", "Table MultiSelect"]:
        desc = field.options + (" - " + field.description if field.description else "")
    return (
        "\t/**\t"
        + (field.label if field.label else "")
        + " : "
        + field.fieldtype
        + ((" - " + desc) if desc else "")
        + "\t*/\n"
    )


def get_field_type_definition(field, doctype, module_path, generate_child_tables):
    enum = {}
    if field.fieldtype == "Select":
        enum = get_select_field_options(field)

    if enum:
        res = {
            "title": field.fieldname,
            "type": get_field_type(field, doctype, module_path, generate_child_tables),
            "enum": enum,
        }
    else:
        res = {
            "title": field.fieldname,
            "type": get_field_type(field, doctype, module_path, generate_child_tables),
        }
    return res


def get_field_type(field, doctype, module_path, generate_child_tables):
    basic_fieldtypes = {
        "Data": "string",
        "Small Text": "string",
        "Text Editor": "string",
        "Text": "string",
        "Code": "string",
        "Link": "string",
        "Dynamic Link": "string",
        "Read Only": "string",
        "Password": "string",
        "Text Editor": "string",
        "Check": "0 | 1",
        "Int": "number",
        "Float": "number",
        "Currency": "number",
        "Percent": "number",
        "Attach Image": "string",
        "Attach": "string",
        "HTML Editor": "string",
        "Image": "string",
        "Duration": "string",
        "Small Text": "string",
        "Date": "string",
        "Datetime": "string",
        "Time": "string",
        "Phone": "string",
        "Color": "string",
        "Long Text": "string",
        "Markdown Editor": "string",
        "Select": "string",
    }

    if field.fieldtype in ["Table", "Table MultiSelect"]:
        # print(get_imports_for_table_fields(field, doctype))
        return get_imports_for_table_fields(
            field, doctype, module_path, generate_child_tables
        )

    if field.fieldtype == "Select":
        # if field.options:
        #     options = field.options.split("\n")
        #     t = ""
        #     for option in options:
        #         t += '"' + option + '" | '
        #     if t.endswith(" | "):
        #         t = t[:-3]
        #     return t
        if field.options:
            options = field.options.split("\n")
            enum_values = [
                option.strip() for option in options
            ]  # Remove leading/trailing whitespace
            # return {"enum": enum_values}
            return "string"
        else:
            return "string"

    if field.fieldtype in basic_fieldtypes:
        return basic_fieldtypes[field.fieldtype]
    else:
        return "any"


def get_select_field_options(field):
    if field.options:
        options = field.options.split("\n")
        enum_values = [
            option.strip() for option in options
        ]  # Remove leading/trailing whitespace
        return enum_values


def get_imports_for_table_fields(field, doctype, module_path, generate_child_tables):
    if field.fieldtype == "Table" or field.fieldtype == "Table MultiSelect":
        doctype_module_name = doctype.module
        table_doc = frappe.get_doc("DocType", field.options)
        table_module_name = table_doc.module
        should_import = False

        # check if table doctype type file is already generated and exists

        if doctype_module_name == table_module_name:
            table_file_path: Path = module_path / (
                table_doc.name.replace(" ", "") + ".ts"
            )
            if not table_file_path.exists():
                if generate_child_tables:
                    generate_type_definition_file(table_doc, module_path)

                    should_import = True

            else:
                should_import = True

            generate_type_definition_content.imports += (
                (
                    "import { "
                    + field.options.replace(" ", "")
                    + " } from './"
                    + field.options.replace(" ", "")
                    + "'"
                )
                + "\n"
                if should_import
                else ""
            )

        else:
            # table_module_path: Path = module_path.split(
            #     "/").pop().join("/") / table_module_name.replace(" ", "")

            table_module_path: Path = module_path.parent / table_module_name.replace(
                " ", ""
            )
            if not table_module_path.exists():
                table_module_path.mkdir()

            table_file_path: Path = table_module_path / (
                table_doc.name.replace(" ", "") + ".ts"
            )

            if not table_file_path.exists():
                if generate_child_tables:
                    generate_type_definition_file(table_doc, table_module_path)

                    should_import = True

            else:
                should_import = True

            generate_type_definition_content.imports += (
                (
                    "import { "
                    + field.options.replace(" ", "")
                    + " } from '../"
                    + table_module_name.replace(" ", "")
                    + "/"
                    + field.options.replace(" ", "")
                    + "'"
                )
                + "\n"
                if should_import
                else ""
            )

        return field.options.replace(" ", "") + "[]" if should_import else "any"
    return ""


def get_required(field):
    if field.reqd:
        return ""
    else:
        return "?"


def get_optional(field):
    if field.reqd:
        return False
    else:
        return True


def is_valid_doctype(doctype):
    if doctype.custom:
        print("Custom DocType - ignoring type generation")
        return False

    if doctype.is_virtual:
        print("Virtual DocType - ignoring type generation")
        return False

    return True


def is_developer_mode_enabled():
    if not frappe.conf.get("developer_mode"):
        print("Developer mode not enabled - ignoring type generation")
        return False
    return True


def before_migrate():
    # print("Before migrate")
    subprocess.run(
        [
            "bench",
            "config",
            "set-common-config",
            "-c",
            "frappe_types_pause_generation",
            "1",
        ]
    )


def after_migrate():
    # print("After migrate")
    subprocess.run(
        [
            "bench",
            "config",
            "set-common-config",
            "-c",
            "frappe_types_pause_generation",
            "0",
        ]
    )


@frappe.whitelist()
def generate_types_for_doctype(
    doctype, app_name, generate_child_tables=False, custom_fields=False
):
    try:
        # custom_fields True means that the generate .ts file for custom fields with original fields
        doc = (
            frappe.get_meta(doctype)
            if custom_fields
            else frappe.get_doc("DocType", doctype)
        )

        # Check if type generation is paused
        common_site_config = frappe.get_conf()

        frappe_types_pause_generation = common_site_config.get(
            "frappe_types_pause_generation", 0
        )

        if frappe_types_pause_generation:
            print("Frappe Types is paused")
            return

        if is_developer_mode_enabled() and is_valid_doctype(doc):
            print("Generating type definition file for " + doc.name)
            module_name = doc.module

            app_path: Path = Path("../apps") / app_name
            if not app_path.exists():
                print("App path does not exist - ignoring type generation")
                return

            # Fetch Json generation Settings Document
            type_generation_settings = (
                frappe.get_doc("Json generation Settings").as_dict().json_settings
            )

            # Checking if app is existed in Json generation Settings
            for type_setting in type_generation_settings:
                if app_name == type_setting.app_name:
                    # Types folder is created in the app
                    # path: Path = type_setting.app_path / "types"
                    type_path: Path = app_path / type_setting.app_path / "jsons"
                    if not type_path.exists():
                        type_path.mkdir()

                    module_path: Path = type_path / module_name.replace(" ", "")
                    if not module_path.exists():
                        module_path.mkdir()

                    generate_type_definition_file(
                        doc, module_path, generate_child_tables
                    )
                else:
                    return
    except Exception as e:
        err_msg = f": {str(e)}\n{frappe.get_traceback()}"
        print(f"An error occurred while generating type for {doctype} {err_msg}")


@frappe.whitelist()
def generate_types_for_module(module, app_name, generate_child_tables=False):
    try:
        child_tables = [
            doctype["name"]
            for doctype in frappe.get_list(
                "DocType", filters={"module": module, "istable": 1}
            )
        ]
        if len(child_tables) > 0:
            for child_table in child_tables:
                generate_types_for_doctype(child_table, app_name, generate_child_tables)

        doctypes = [
            doctype["name"]
            for doctype in frappe.get_list(
                "DocType", filters={"module": module, "istable": 0}
            )
        ]

        if len(doctypes) > 0:
            for doctype in doctypes:
                generate_types_for_doctype(doctype, app_name, generate_child_tables)
    except Exception as e:
        err_msg = f": {str(e)}\n{frappe.get_traceback()}"
        print(f"An error occurred while generating type for {module} {err_msg}")
