import json
import os
from aiohttp import web
from const import LICENSE_PAGE, LICENSE_PATH
from config_commons import get_html
import urllib.request


def get_package_licenses() -> str:
    """Call pip-licenses."""
    with open("./requirements.txt") as fid:
        smhub_packages = fid.read().replace("\n", " ")
    os.system(
        f"pip-licenses --output-file ./{LICENSE_PATH}license_info.json --format json --with-authors --with-urls --with-license-file --packages {smhub_packages}"
    )
    lic_data = read_lic_data("license_info.json")
    table_str = build_lic_table(lic_data, "hub")

    if os.path.isfile(LICENSE_PATH + "license_info_core.json"):
        hbtn_intgtn_packages = "PyYAML voluptuous"
        os.system(
            f"pip-licenses --output-file ./{LICENSE_PATH}license_info_hai.json --format json --with-authors --with-urls --with-license-file --packages {hbtn_intgtn_packages}"
        )
        lic_data = read_lic_data("license_info_hai.json")
        table_str += build_lic_table(lic_data, "hai")

        lic_data = read_lic_data("license_info_core.json")
        table_str += build_lic_table(lic_data, "core")
    return table_str


def read_lic_data(license_file: str) -> list[dict[str, str]]:
    """Read license json file."""
    with open(LICENSE_PATH + license_file) as fid:
        lic_data = json.load(fid)
    len_d = len(lic_data) - 1
    for ld_i in range(len_d):
        if (
            lic_data[len_d - ld_i]["Name"] == lic_data[len_d - ld_i]["Name"]
            and lic_data[len_d - ld_i]["Version"]
            == lic_data[len_d - ld_i - 1]["Version"]
        ):
            del lic_data[len_d - ld_i]

        if len(lic_data[len_d - ld_i - 1]["License"]) > 30:
            idx = lic_data[len_d - ld_i - 1]["License"].lower().find("license")
            lic_data[len_d - ld_i - 1]["License"] = (
                lic_data[len_d - ld_i - 1]["License"][:idx] + "License"
            )
    return lic_data


def build_lic_table(lic_data: list[dict[str, str]], spec: str) -> str:
    """Build html table string from table line list."""

    if spec == "hai":
        header_line = "<h3>Habitron Custom Component für Home Assistant</h3>\n"
    elif spec == "core":
        header_line = "<h3>Home Assistant Core</h3>\n"
    else:
        header_line = ""

    thead_lines = (
        f'<table id="lic-{spec}-table">\n'
        + "    <thead>\n"
        + "        <tr>\n"
        + "            <th>Name</th>\n"
        + '            <th data-sort-method="none">Vers.</th>\n'
        + "            <th>License</th>\n"
        + '            <th data-sort-method="none">Author</th>\n'
        + '            <th data-sort-method="none">URL</th>\n'
        + "        </tr>\n"
        + "    </thead>\n"
        + "    <tbody>\n"
    )
    tr_line = "        <tr>\n"
    td_line = "            <td></td>\n"
    tablesort_lines = (
        "    <tr>\n"
        + "      <td>tablesort</td>\n"
        + "      <td>5.3.0</td>\n"
        + set_default_license_link("      <td>T Brown License</td>\n")
        + "      <td>Tristen Brown</td>\n"
        + "      <td>https://github.com/tristen/tablesort</td>\n"
        + "    </tr>\n"
    )
    tend_lines = "  </tbody>\n</table>\n"
    table_str = header_line + thead_lines
    for lic_entry in lic_data:
        lic_entry["License"] = get_std_license_name(lic_entry["License"])
        table_str += tr_line
        table_str += td_line.replace("><", f">{lic_entry['Name']}<")
        table_str += td_line.replace("><", f">{lic_entry['Version']}<")
        table_str += td_line.replace("><", f">{get_license_link(lic_entry)}<")
        table_str += td_line.replace("><", f">{lic_entry['Author']}<")
        table_str += td_line.replace("><", f">{lic_entry['URL']}<")
        table_str += tr_line.replace("<tr>", "</tr>")
    if spec == "hub":
        table_str += tablesort_lines
    table_str += tend_lines
    return html_text_to_link(table_str, True)


def get_std_license_name(lic_name: str) -> str:
    """Return unique license name."""

    lic_name = lic_name.replace("  ", " ").strip()
    std_license_names = {
        "apache software license": "Apache 2.0",
        "apache software 2.0": "Apache 2.0",
        "apache version 2.0": "Apache 2.0",
        "apache license, version 2.0": "Apache 2.0",
        "apache-2.0": "Apache 2.0",
        "apache-2": "Apache 2.0",
        "apache 2": "Apache 2.0",
        "apache": "Apache 2.0",
        "apache license": "Apache 2.0",
        "gnu affero general public license": "AGPL",
        "gnu affero general public": "AGPL",
        "gnu general public license": "GPL",
        "gnu library or lesser general public license": "GPL",
        "gnu general public v3": "GPL",
        "gnu-2.0": "GPL",
        "gpl-2.0": "GPL",
        "gplv2": "GPL",
        "gnu-3.0": "GPL",
        "gpl-3.0": "GPL",
        "gplv3": "GPL",
        "gplv3+": "GPL",
        "isc": "ISCL",
        "isc (iscl)": "ISCL",
        "gnu lesser general public license": "LGPL",
        "lesser general public license": "LGPL",
        "lgpl v3": "LGPL",
        "lgplv3+": "LGPL",
        "lgplv3": "LGPL",
        "mit license": "MIT",
        "the unlicense (unlicense)": "Unlicense",
        "the mit": "MIT",
        "the mit license": "MIT",
        "the mit (mit)": "MIT",
        "mpl2": "MLP",
        "mpl-2.0": "MPL",
        "mozilla public license": "MPL",
    }

    if lic_name.lower() not in std_license_names.keys():
        return lic_name.replace(" License", "")
    return std_license_names[lic_name.lower()]


def html_text_to_link(txt_str: str, shorten: bool) -> str:
    """Search for written html links and convert to html syntax links."""
    txt_lines = txt_str.split("\n")
    txt_str = ""
    for line in txt_lines:
        if (i_l := line.find("https://")) > 0:
            http_str = "https"
        elif (i_l := line.find("http://")) > 0:
            http_str = "http"
        if i_l > 0:
            h_link = line[i_l:].split()[0].split("<")[0]
            short_link = h_link
            if shorten:
                short_link = h_link.replace(f"{http_str}://", "")
                if short_link[-1] == "/":
                    short_link = short_link[:-1]
            txt_str += (
                line.replace(h_link, f'<a href="{h_link}">{short_link}</a>') + "\n"
            )
        else:
            txt_str += line + "\n"
    return txt_str


def get_license_link(lic_entry: dict[str, str]) -> str:
    """Try several options to get license text and return file link."""

    lic_file_list = ["LICENSE", "LICENSE.md", "LICENSE.txt"]
    lic_filename = "lic_" + lic_entry["Name"] + lic_entry["Version"] + ".txt"
    if os.path.isfile(LICENSE_PATH + lic_filename):
        return f'<a href="{lic_filename}">{get_license_id_from_text(lic_entry)}</a>'
    if lic_entry["LicenseText"] != "UNKNOWN":
        with open(LICENSE_PATH + lic_filename, "w") as fid:
            fid.write(lic_entry["LicenseText"])
        lic_link = f'<a href="{lic_filename}">{get_license_id_from_text(lic_entry)}</a>'
        return lic_link
    if lic_entry["URL"] != "UNKNOWN":
        for lic_fn in lic_file_list:
            try:
                link = (
                    lic_entry["URL"].replace(
                        "/github.com/", "/raw.githubusercontent.com/"
                    )
                    + "/master/"
                    + lic_fn
                )
                with urllib.request.urlopen(link) as f:
                    lic_txt = f.read().decode()
                with open(LICENSE_PATH + lic_filename, "w") as fid:
                    fid.write(lic_txt)
                lic_entry["LicenseText"] = lic_txt
                lic_link = f'<a href="{lic_filename}">{get_license_id_from_text(lic_entry)}</a>'
                return lic_link
            except Exception:
                pass
    lic_link = set_default_license_link(lic_entry["License"])
    return lic_link


def get_license_id_from_text(lic_entry: dict[str, str]) -> str:
    """Try to pick license id from license text."""

    exception_list = [
        "unknown",
        "other/proprietary",
        "license.txt",
        "license",
        "type",
        "zlib/libpng",
        "?",
    ]
    if (
        lic_entry["License"].lower() in exception_list
        and len(lic_entry["LicenseText"]) > 30
    ):
        # try to pick license name from text
        idx = lic_entry["LicenseText"].lower().find("license")
        lic_id = get_std_license_name(
            lic_entry["LicenseText"][:idx].strip() + " License"
        )
        if lic_id in ["Apache 2.0", "BSD", "GPL", "LGPL", "MIT"]:
            lic_entry["License"] = lic_id
        else:
            lic_entry["License"] = "Other/Proprietary"
    return lic_entry["License"]


def set_default_license_link(line: str) -> str:
    """Check for know license and set html link to local text file."""

    known_licenses = {
        "AGPL": "AGPL_license.txt",
        "Apache 2.0": "Apache_2_0.txt",
        "Artistic": "Artistic.txt",
        "BSD": "BSD_license.txt",
        "GPL": "GPL_license.txt",
        "LGPL": "LGPL_license.txt",
        "ISC": "ISC_license.txt",
        "MIT": "MIT_license.txt",
        "PSF": "PSF_license.txt",
        "T Brown": "lic_tablesort5.3.0.txt",
    }

    for l_key in known_licenses.keys():
        if line.find(l_key) >= 0:
            line = line.replace(l_key, f'<a href="{known_licenses[l_key]}">{l_key}</a>')
            break
    return line


def show_license_text(request) -> web.Response:
    """Return web page with license text."""
    lic_file = open(LICENSE_PATH + request.path)
    lic_text = lic_file.read()
    lic_text = html_text_to_link(lic_text, False)
    header = lic_text.split("\n")[0].strip()
    lic_text = lic_text.replace(f"{header}\n", "").replace("\n", "<br>").strip()
    lic_file.close()
    html_str = (
        get_html(LICENSE_PAGE)
        .replace("Smart Hub", header)
        .replace("<table></table>", f"<p>{lic_text}</p>")
    )
    return web.Response(text=html_str, content_type="text/html", charset="utf-8")
