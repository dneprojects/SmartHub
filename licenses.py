import json
import os
from aiohttp import web
from const import DATA_FILES_ADDON_DIR, LICENSE_PAGE, LICENSE_PATH
from config_commons import get_html
import urllib.request

known_licenses = {
    "AFL": "AFL_license.txt",
    "AGPL": "AGPL_license.txt",
    "Apache 2.0": "Apache_2_0.txt",
    "Artistic": "Artistic.txt",
    "BSD": "BSD_3_license.txt",
    "BSD 2": "BSD_2_license.txt",
    "BSD 3": "BSD_3_license.txt",
    "EPL 1.0": "EPL1_license.txt",
    "EPL 2.0": "EPL2_license.txt",
    "bzip2": "bzip2_license.txt",
    "curl": "curl_license.txt",
    "GPL": "GPL_license.txt",
    "GPL 2.0": "GPL_2_0_license.txt",
    "LGPL": "LGPL_license.txt",
    "LGPL 2.1": "LGPL_2_1_license.txt",
    "MPL": "MPL_license.txt",
    "Nmap": "Nmap_license.txt",
    "Info-ZIP": "IZIP_license.txt",
    "ISC": "ISC_license.txt",
    "MIT": "MIT_license.txt",
    "OpenSSH": "OpenSSH_license.txt",
    "PSF": "PSF_license.txt",
    "RPL": "repoze_license.txt",
    "sqlite": "sqlite_license.txt",
    "sudo": "sudo_license.txt",
    "T Brown": "lic_tablesort5.3.0.txt",
    "Unlicense": "un_license.txt",
    "VIM": "VIM_license.txt",
    "X11": "X11_license.txt",
    "zsh": "zsh_license.txt",
    "zlib": "zlib_license.txt",
}

std_license_names = {
    "academic free license": "AFL",
    "artistic-1.0-per": "Artistic",
    "artistic-2.0": "Artistic",
    "afl-2": "AFL",
    "afl-2.": "AFL",
    "afl-2.0": "AFL",
    "afl-2.1": "AFL",
    "apache software license": "Apache 2.0",
    "apache software license 2.0": "Apache 2.0",
    "apache software 2.0": "Apache 2.0",
    "apache version 2.0": "Apache 2.0",
    "apache license 2.0": "Apache 2.0",
    "apache license version 2.0": "Apache 2.0",
    "apache license, version 2.0": "Apache 2.0",
    "apache-2.0": "Apache 2.0",
    "apache-2.": "Apache 2.0",
    "apache-2": "Apache 2.0",
    "apache 2": "Apache 2.0",
    "apache": "Apache 2.0",
    "apache license": "Apache 2.0",
    "bsd license": "BSD",
    "simplified bsd": "BSD 2",
    "bsd-2-clause": "BSD 2",
    "bsd-2-claus": "BSD 2",
    "2-clause bsd license": "BSD 2",
    "bsd-3-clause": "BSD 3",
    "bsd-3-claus": "BSD 3",
    "3-clause bsd license": "BSD 3",
    "bzip2-1.0.6": "bzip2",
    "cc0 1.0 universal": "CC0",
    "epl-1.": "EPL 1.0",
    "epl": "EPL 2.0",
    "eclipse public license": "EPL 2.0",
    "eclipse public license v2.0": "EPL 2.0",
    "gnu affero general public license": "AGPL",
    "gnu affero general public": "AGPL",
    "gnu general public license": "GPL",
    "gnu library or lesser general public license": "GPL",
    "gnu general public v3": "GPL",
    "gnu general public license v3": "GPL",
    "gnu-2.0": "GPL",
    "gpl-2.0": "GPL",
    "gplv2": "GPL",
    "gnu-3.0": "GPL",
    "gpl-3.0": "GPL",
    "gplv3": "GPL",
    "gplv3+": "GPL",
    "iscl": "ISCL",
    "isc": "ISCL",
    "isc license (iscl)": "ISCL",
    "gnu lesser general public license": "LGPL",
    "historical permission notice and disclaimer (hpndlicense": "HPND",
    "lesser general public license": "LGPL",
    "lgpl v3": "LGPL",
    "lgplv3+": "LGPL",
    "lgplv3": "LGPL",
    "mit license": "MIT",
    "the mit": "MIT",
    "the mit license": "MIT",
    "the mit license (mit)": "MIT",
    "mpl2": "MLP",
    "mpl-2.": "MPL",
    "mpl-2.0": "MPL",
    "mozilla public license": "MPL",
    "python software foundation license": "PSF",
    "psf-2.0": "PSF",
    "public-domain": "Public Domain",
    "ssh-openssh": "OpenSSH",
    "the unlicense (unlicense)": "Unlicense",
    "unlicense.org": "Unlicense",
    "public domain": "Unlicense",
    "vim": "VIM",
    "other/proprietary license": "Other/Proprietary",
    "unknown": "Other/Proprietary",
    "?": "Other/Proprietary",
    "zlib/libpng license": "zlib",
    "zlib": "zlib",
    "zope public license": "ZPL",
}


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
        # hbtn_intgtn_packages = "PyYAML voluptuous "
        # os.system(
        #     f"pip-licenses --output-file ./{LICENSE_PATH}license_info_hai.json --format json --with-authors --with-urls --with-license-file --packages {hbtn_intgtn_packages}"
        # )
        lic_data = read_lic_data("license_info_hai.json")
        table_str += build_lic_table(lic_data, "hai")

        lic_data = read_lic_data("license_info_core.json")
        table_str += build_lic_table(lic_data, "core")

    if os.path.isfile(LICENSE_PATH + "license_info_os.lst"):
        lic_data = parse_apk_info(LICENSE_PATH + "license_info_os.lst")
        table_str += build_lic_table(lic_data, "os")
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
    elif spec == "os":
        header_line = "<h3>Home Assistant OS</h3>\n"
    else:
        header_line = ""

    tr_line = '        <tr id="lic-tr">\n'
    tre_line = "        </tr>\n"
    td_line = "            <td></td>\n"
    tablesort_lines = (
        '    <tr id="lic-tr">\n'
        + "      <td>tablesort</td>\n"
        + "      <td>5.3.0</td>\n"
        + "      <td><a href=lic_tablesort5.3.0.txt>Other/Proprietary</a></td>\n"
        + "      <td>Tristen Brown</td>\n"
        + "      <td>https://github.com/tristen/tablesort</td>\n"
        + "    </tr>\n"
    )

    thead_lines = (
        f'<table id="lic-{spec}-table">\n'
        + "    <thead>\n"
        + "        <tr>\n"
        + "            <th>Name</th>\n"
        + '            <th data-sort-method="none">Vers.</th>\n'
        + "            <th>License</th>\n"
    )
    if spec != "os":
        thead_lines += '            <th data-sort-method="none">Author</th>\n'
    thead_lines += (
        '            <th data-sort-method="none">URL</th>\n'
        + "        </tr>\n"
        + "    </thead>\n"
        + "    <tbody>\n"
    )
    tend_lines = "  </tbody>\n</table>\n"

    table_str = header_line + thead_lines
    for lic_entry in lic_data:
        lic_entry["License"] = get_std_license_name(lic_entry["License"])
        table_str += tr_line
        table_str += td_line.replace("><", f">{lic_entry['Name']}<")
        table_str += td_line.replace("><", f">{lic_entry['Version']}<")
        table_str += td_line.replace("><", f">{get_license_link(lic_entry)}<")
        if spec != "os":
            table_str += td_line.replace("><", f">{lic_entry['Author']}<")
        table_str += td_line.replace("><", f">{lic_entry['URL']}<")
        table_str += tre_line
    if spec == "hub":
        table_str += tablesort_lines
    table_str += tend_lines
    return html_text_to_link(table_str, True)


def get_std_license_name(lic_name: str) -> str:
    """Return unique license name."""

    lic_name = lic_name.replace("  ", " ").strip()

    if lic_name.lower().find("-or-late") > 0:
        lic_name = lic_name.split("-")[0]
    if lic_name.lower().find("-only") > 0:
        lic_name = lic_name.replace("-only", "").replace("-", " ")
    if lic_name.lower() not in std_license_names.keys():
        return lic_name  # .replace(" License", "")
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


def parse_apk_info(lic_file: str) -> list[dict[str, str]]:
    """Read apk info file and return dict."""

    lic_data: list[dict[str, str]] = []
    l_no = 0
    with open(lic_file) as fid:
        while line := fid.readline():
            if l_no % 4 == 0:
                lic_entry: dict[str, str] = {}
                parts = line.split(" ")
                name_version = parts[0].split("-")
                lic_entry["Name"] = "-".join(name_version[:-2])
                lic_entry["Version"] = name_version[-2]
                lic_entry["License"] = parts[3][1:-1]
            elif l_no % 4 == 2:
                lic_entry["URL"] = line.strip()[1:-1]
                if lic_entry["URL"][-1] == "/":
                    lic_entry["URL"] = line.strip()[1:-2]
                lic_entry["LicenseText"] = "UNKNOWN"
                lic_data.append(lic_entry)
            l_no += 1
    return lic_data


def get_license_link(lic_entry: dict[str, str]) -> str:
    """Try several options to get license text and return file link."""

    lic_file_list = ["LICENSE", "LICENSE.md", "LICENSE.txt"]
    lic_filename = "lic_" + lic_entry["Name"] + lic_entry["Version"] + ".txt"
    if lic_entry["URL"].lower().find("adelielinux.org") >= 0:
        lic_entry["License"] = "NCSA"
        lic_filename = "lic_adelie_linux.txt"
        lic_link = f'<a href="{lic_filename}">{lic_entry["License"]}</a>'
        return lic_link
    if os.path.isfile(LICENSE_PATH + lic_filename):
        return f'<a href="{lic_filename}">{get_license_id_from_text(lic_entry)}</a>'
    if lic_entry["LicenseText"] != "UNKNOWN":
        with open(LICENSE_PATH + lic_filename, "w") as fid:
            fid.write(lic_entry["LicenseText"])
        lic_link = f'<a href="{lic_filename}">{get_license_id_from_text(lic_entry)}</a>'
        return lic_link
    if lic_entry["URL"] != "UNKNOWN":
        if lic_entry["URL"].lower().find("repoze.org") >= 0:
            lic_entry["License"] = "RPL"
            return set_default_license_link(lic_entry["License"])
        if lic_entry["URL"].lower().find("nmap.org") >= 0:
            lic_entry["License"] = "Nmap"
            return set_default_license_link(lic_entry["License"])
        if lic_entry["URL"].lower().find("sqlite.org") >= 0:
            lic_entry["License"] = "sqlite"
            return set_default_license_link(lic_entry["License"])
        if lic_entry["URL"].lower().find("sudo.ws") >= 0:
            lic_entry["License"] = "sudo"
            return set_default_license_link(lic_entry["License"])
        if lic_entry["URL"].lower().find("tmux.github.io") >= 0:
            lic_filename = "tmux_license.txt"
            lic_link = f'<a href="{lic_filename}">{lic_entry["License"]}</a>'
            return lic_link
        if lic_entry["URL"].lower().find("zsh.org") >= 0:
            lic_entry["License"] = "zsh"
            return set_default_license_link(lic_entry["License"])
        if lic_entry["URL"].lower().find("info-zip.org") >= 0:
            lic_entry["License"] = "Info-ZIP"
            return set_default_license_link(lic_entry["License"])
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
        if lic_id in known_licenses.keys():
            lic_entry["License"] = lic_id
        else:
            lic_entry["License"] = "Other/Proprietary"
    return lic_entry["License"]


def set_default_license_link(entry: str) -> str:
    """Check for know license and set html link to local text file."""

    for l_key in known_licenses.keys():
        if entry.strip() == l_key:
            entry = entry.replace(
                l_key, f'<a href="{known_licenses[l_key]}">{l_key}</a>'
            )
            break
    return entry


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
