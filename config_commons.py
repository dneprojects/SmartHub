from aiohttp import web
import re
from const import (
    WEB_FILES_DIR,
    SIDE_MENU_FILE,
    CONFIG_TEMPLATE_FILE,
)


def get_html(html_file) -> str:
    with open(WEB_FILES_DIR + html_file, mode="r", encoding="utf-8") as pg_id:
        return pg_id.read()


def html_response(html_file) -> web.Response:
    with open(WEB_FILES_DIR + html_file, mode="r", encoding="utf-8") as pg_id:
        text = pg_id.read()
    return web.Response(text=text, content_type="text/html", charset="utf-8")


def adjust_side_menu(modules, is_offline) -> str:
    """Load side_menu and adjust module entries."""
    mod_lines = []
    with open(WEB_FILES_DIR + SIDE_MENU_FILE, mode="r", encoding="utf-8") as smf_id:
        side_menu = smf_id.read().splitlines(keepends=True)
    for sub_line in side_menu:
        if sub_line.find("modules sub") > 0:
            sub_idx = side_menu.index(sub_line)
            break
    first_lines = side_menu[:sub_idx]
    last_lines = side_menu[sub_idx + 1 :]
    for module in modules:
        mod_lines.append(
            sub_line.replace("module-1", f"module-{module._id}").replace(
                "ModuleName", module._name
            )
        )
    page = "".join(first_lines) + "".join(mod_lines) + "".join(last_lines)
    if is_offline:
        page = page.replace(
            '<a href="hub" title="Hub" class="submenu modules">Hub</a>',
            '<a href="hub" title="Hub" class="submenu modules">Home</a>',
        )
    return page


def init_side_menu(app):
    """Setup side menu."""
    side_menu = adjust_side_menu(app["api_srv"].routers[0].modules, app["is_offline"])
    app["side_menu"] = side_menu


def show_modules(app) -> web.Response:
    """Prepare modules page."""
    side_menu = activate_side_menu(app["side_menu"], ">Module<")
    page = get_html("modules.html").replace("<!-- SideMenu -->", side_menu)
    images = ""
    modules = app["api_srv"].routers[0].modules
    for module in modules:
        pic_file, title = get_module_image(module._typ)
        images += f'<div class="figd_grid"><a href="module-{module._id}"><div class="fig_grid"><img src="configurator_files/{pic_file}" alt="{module._name}"><p>{module._name}</p></div></a></div>\n'
    page = page.replace("<!-- ImageGrid -->", images)
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def fill_page_template(
    title, subtitle, content, menu, image, download_file: str
) -> str:
    """Prepare config web page with content, image, and menu."""
    with open(
        WEB_FILES_DIR + CONFIG_TEMPLATE_FILE, mode="r", encoding="utf-8"
    ) as tplf_id:
        page = tplf_id.read()
    if download_file == "":
        ext = ""
    else:
        ext = download_file.split(".")[1]
    page = (
        page.replace("ContentTitle", title)
        .replace("ContentSubtitle", subtitle)
        .replace("ContentText", content)
        .replace("<!-- SideMenu -->", menu)
        .replace("controller.jpg", image)
        .replace("my_module.hmd", download_file)
        .replace('accept=".hmd"', f'accept=".{ext}"')
    )
    return page


def activate_side_menu(menu: str, entry: str) -> str:
    """Mark menu entry as active."""
    side_menu = menu.splitlines(keepends=True)
    for sub_line in side_menu:
        if sub_line.find(entry) > 0:
            sub_idx = side_menu.index(sub_line)
            break
    side_menu[sub_idx] = re.sub(
        r"title=\"[a-z,A-z,0-9,\-,\"]+ ", "", side_menu[sub_idx]
    )
    side_menu[sub_idx] = side_menu[sub_idx].replace('class="', 'class="active ')
    return "".join(side_menu)


def get_module_image(type_code: bytes) -> tuple[str, str]:
    """Return module image based on type code bytes."""
    match type_code[0]:
        case 0:
            mod_image = "router.jpg"
            type_desc = (
                "Smart Router - Kommunikationsschnittstelle zwischen den Modulen"
            )
        case 1:
            mod_image = "controller.jpg"
            type_desc = "Smart Controller - Raumzentrale mit Sensorik und Aktorik"
        case 10:
            match type_code[1]:
                case 1 | 50 | 51:
                    mod_image = "smart-out-8-R.jpg"
                    type_desc = "Smart-Out 8/R - 8fach Binärausgang (potentialfrei)"
                case 2:
                    mod_image = "smart-out-8-T.jpg"
                    type_desc = "Smart-Out 8/T - 8fach Binärausgang (potentialgebunden)"
                case 20 | 21 | 22:
                    mod_image = "dimm.jpg"
                    type_desc = "Smart Dimm - 4fach Dimmer"
        case 11:
            match type_code[1]:
                case 1:
                    mod_image = "smart-In-8-230V.jpg"
                    type_desc = "Smart-Input 8/230V - 8fach 230 V-Binäreingang"
                case 30 | 31:
                    mod_image = "smart-In-8-24V.jpg"
                    type_desc = "Smart-Input 8/230V - 8fach 24 V-Binäreingang"
        case 20:
            mod_image = "smart-nature.jpg"
            type_desc = "Smart Nature - Externe Wetterstation"
        case 30:
            mod_image = "mod_smartkey.jpg"
            type_desc = "Smart Key - Zugangskontroller über Fingerprint"
        case 31:
            mod_image = "finger_numbers.jpg"
            type_desc = "Smart Key - Zugangskontroller über Fingerprint"
        case 50:
            mod_image = "scc.jpg"
            type_desc = "Smart Controller compakt - Controller mit Sensorik und 24 V Anschlüssen"
        case 80:
            match type_code[1]:
                case 100 | 102:
                    mod_image = "smart-detect-1802.jpg"
                    type_desc = "Smart Detect 180 - Bewegungsmelder"
                case 101:
                    mod_image = "smart-detect-360.jpg"
                    type_desc = "Smart Detect 360 - Bewegungsmelder für Deckeneinbau"
        case 200:
            mod_image = "smart-ip.jpg"
            type_desc = "Smart Hub - Systemzentrale und Schnittstelle zum Netzwerk"
        case 201:
            mod_image = "smart-center.jpg"
            type_desc = "Smart Hub - Systemzentrale und Schnittstelle zum Netzwerk"
        case 202:
            mod_image = "smart-center.jpg"
            type_desc = "Smart Center - Habitron Home Assistant Zentrale"
    return mod_image, type_desc


def indent(level):
    """Return sequence of tabs according to level."""
    return "\t" * level


def adjust_settings_button(page, type, addr: str) -> str:
    """Specify button."""
    if type.lower() == "gtw":
        page = page.replace("ModSettings", "GtwSettings")
    elif type.lower() == "rtr":
        page = page.replace("ModSettings", "RtrSettings")
    elif type == "":
        page = page.replace(">Einstellungen", " disabled >Einstellungen")
        page = page.replace(">Konfigurationsdatei", " disabled >Konfigurationsdatei")
    else:
        page = page.replace("ModAddress", addr)
    return page


def adjust_automations_button(page: str) -> str:
    """Enable edit automations button."""
    page = page.replace("<!--<button", "<button").replace("</button>-->", "</button>")
    return page


def disable_button(key: str, page) -> str:
    return page.replace(f">{key}<", f" disabled>{key}<")
