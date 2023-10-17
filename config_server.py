from math import copysign
from aiohttp import web
from urllib.parse import parse_qs
from multidict import MultiDict
from pymodbus.utilities import computeCRC as ModbusComputeCRC
from module import HbtnModule
import logging
import pathlib
import re
from const import (
    WEB_FILES_DIR,
    SIDE_MENU_FILE,
    CONFIG_TEMPLATE_FILE,
    SETTINGS_TEMPLATE_FILE,
    CONF_PORT,
    MirrIdx,
    IfDescriptor,
)

routes = web.RouteTableDef()
root_path = pathlib.Path(__file__).parent
routes.static("/configurator_files", root_path.joinpath("web/configurator_files"))


class HubSettings:
    """Object with all module settings and changes."""

    def __init__(self, hub):
        """Fill all properties with module's values."""
        self.name = hub._name
        self.typ = hub._typ


class RouterSettings:
    """Object with all module settings and changes."""

    def __init__(self, router):
        """Fill all properties with module's values."""
        self.id = router._id
        self.name = router._name
        self.descriptions = router.descriptions
        self.channels = router.channels
        self.timeout = router.timeout
        self.groups = router.groups
        self.mode_dependencies = router.mode_dependencies
        self.user_modes = router.user_modes
        self.day_night = router.day_night


class ConfigServer:
    """Web server for basic configuration tasks."""

    def __init__(self, smip):
        self.smip = smip
        self._ip = smip._host_ip
        self._port = CONF_PORT
        self.logger = logging.getLogger(__name__)
        self.conf_running = False
        self.app: web.Application = []

    async def initialize(self):
        """Initialize config server."""
        self.app = web.Application()
        self.app["smip"] = self.smip
        self.app.add_routes(routes)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self._ip, self._port)
        self.app["logger"] = self.logger

    async def prepare(self):
        """Second initialization after api_srv is initialized."""
        self.api_srv = self.smip.api_srv
        self.side_menu = adjust_side_menu(self.api_srv.routers[0].modules)
        self.app["api_srv"] = self.api_srv
        self.app["side_menu"] = self.side_menu

    @routes.get("/")
    async def root(request: web.Request) -> web.Response:
        return html_response("configurator.html")

    @routes.get("/router")
    async def root(request: web.Request) -> web.Response:
        return show_router_overview(request.app)

    @routes.get("/hub")
    async def root(request: web.Request) -> web.Response:
        api_srv = request.app["api_srv"]
        hub_name = api_srv.smip._host
        html_str = get_html("hub.html").replace("HubTitle", f"Smart Hub '{hub_name}'")
        html_str = html_str.replace(
            "Overview", "Smart Hub - Systemzentrale und Schnittstelle zum Netzwerk"
        )
        html_str = html_str.replace(
            "ContentText",
            "<h3>Eigenschaften</h3>\n<p>"
            + api_srv.smip.info.replace(" ", "&nbsp;&nbsp;").replace("\n", "</p>\n<p>")
            + "</p>",
        )
        return web.Response(text=html_str, content_type="text/html")

    @routes.get("/modules")
    async def root(request: web.Request) -> web.Response:
        return show_modules(request.app)

    @routes.get("/module-{mod_addr}")
    async def root(request: web.Request) -> web.Response:
        mod_addr = int(request.match_info["mod_addr"])
        return show_module_overview(request.app, mod_addr)

    @routes.get("/settings")
    async def root(request: web.Request) -> web.Response:
        args = request.query_string.split("=")
        if args[0] == "ModSettings":
            mod_addr = int(args[1])
            return show_settings(request.app, mod_addr)
        elif args[0] == "RtrSettings":
            return show_settings(request.app, 0)
        elif args[0] == "ConfigFiles":
            return show_popup("Not yet implemented.")

    @routes.get("/settings_step")
    async def root(request: web.Request) -> web.Response:
        args = request.query_string.split("=")
        return await show_next_prev(request, args[1])

    @routes.post("/settings")
    async def root(request: web.Request) -> web.Response:
        resp = await request.text()
        form_data = parse_qs(resp)
        key = "name"
        settings = request.app["settings"]
        i = 0
        for form_key in list(form_data.keys())[:-1]:
            idx = int(form_key.replace("data[", "").replace("]", ""))
            if i == 0:
                settings.__setattr__(key, form_data[form_key][0])
            i += 1
        request.app["settings"] = settings
        args = form_data["ModSettings"][0]
        return await show_next_prev(request, args)

    @routes.post("/settings_step")
    async def root(request: web.Request) -> web.Response:
        resp = await request.text()
        form_data = parse_qs(resp)
        parse_response_form(request.app, form_data)
        args = form_data["ModSettings"][0]
        return await show_next_prev(request, args)

    @routes.get("/download")
    async def root(request: web.Request) -> web.Response:
        file_name = request.query["file"]
        file_name = file_name.split(".")[0]
        addr_str = request.query["ModDownload"]
        if addr_str == "ModAddress":
            mod_addr = 0
        else:
            mod_addr = int(addr_str)
        if mod_addr > 0:
            # module
            settings = (
                request.app["api_srv"]
                .routers[0]
                .get_module(mod_addr)
                .get_module_settings()
            )
            file_name = file_name + ".smm"
            str_data = format_smm(settings.smg, settings.list)
        else:
            # router
            settings = request.app["api_srv"].routers[0].get_router_settings()
            file_content = settings.smr
            file_name = file_name + ".smr"
            str_data = ""
            for byt in file_content:
                str_data += f"{byt};"
        return web.Response(
            headers=MultiDict(
                {"Content-Disposition": f"Attachment; filename = {file_name}"}
            ),
            body=str_data,
        )

    @routes.post("/upload")
    async def root(request: web.Request) -> web.Response:
        data = await request.post()
        config_file = data["file"].file
        content = config_file.read()
        content_str = content.decode()
        if data["ModUpload"] == "ModAddress":
            # router upload
            request.app["logger"].info(f"Router configuration file uploaded")
            await send_to_router(request.app, content_str)
        else:
            mod_addr = int(data["ModUpload"])
            if data["ModUpload"] == content_str.split(";")[0]:
                await send_to_module(request.app, content_str, mod_addr)
                request.app["logger"].info(
                    f"Module configuration file for module {mod_addr} uploaded"
                )
            else:
                request.app["logger"].warning(
                    f"Module configuration file does not fit to module number {mod_addr}, upload aborted"
                )
                web.AppendChild
        return web.HTTPNoContent()


def get_html(html_file) -> str:
    with open(WEB_FILES_DIR + html_file, mode="r") as pg_id:
        return pg_id.read()


def html_response(html_file) -> web.Response:
    with open(WEB_FILES_DIR + html_file, mode="r") as pg_id:
        text = pg_id.read()
    return web.Response(text=text, content_type="text/html")


def adjust_side_menu(modules) -> str:
    """Load side_menu and adjust module entries."""
    mod_lines: list(str) = []
    with open(WEB_FILES_DIR + SIDE_MENU_FILE, mode="r") as smf_id:
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
    return "".join(first_lines) + "".join(mod_lines) + "".join(last_lines)


async def show_next_prev(request, args):
    """Do the step logic and prepare next page."""

    args1 = args.split("-")
    button = args1[0]
    mod_addr = int(args1[1])
    step = int(args1[2])
    if button == "cancel":
        if mod_addr > 0:
            return show_module_overview(request.app, mod_addr)
        else:
            return show_router_overview(request.app)
    settings = request.app["settings"]
    # Apply changes of form to settings
    request.app["settings"] = settings

    if button == "save":
        if mod_addr > 0:
            await return_module_settings(request.app, mod_addr)
            return show_module_overview(request.app, mod_addr)
        else:
            # Save settings in router
            return show_router_overview(request.app)
    props = settings.properties
    request.app["props"] = props
    io_keys = settings.prop_keys
    request.app["io_keys"] = io_keys
    no_props = props["no_keys"]
    if button == "next":
        if step < no_props:
            step += 1
    elif button == "back":
        if step > 0:
            step -= 1
    return show_setting_step(request.app, mod_addr, step)


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
    return web.Response(text=page, content_type="text/html")


def show_router_overview(app) -> web.Response:
    """Prepare overview page of module."""
    api_srv = app["api_srv"]
    rtr = api_srv.routers[0]
    side_menu = activate_side_menu(app["side_menu"], ">Router<")
    type_desc = "Smart Router - Kommunikationsschnittstelle zwischen den Modulen"
    props = "<h3>Eigenschaften</h3>"
    props += f"Hardware:&nbsp;&nbsp;&nbsp;{rtr.serial.decode('iso8859-1')[1:]}<br>"
    props += f"Firmware:&nbsp;&nbsp;&nbsp;{rtr.version.decode('iso8859-1')[1:]}<br>"
    mode0 = rtr.mode0
    day_mode = mode0 & 0x7
    mode0 = mode0 & 0xF8
    if mode0 == 75:
        mode_str = "Konfig"
    elif mode0 == 112:
        mode_str = "Urlaub"
    elif mode0 == 96:
        mode_str = "User2"
    elif mode0 == 80:
        mode_str = "User1"
    elif mode0 == 48:
        mode_str = "Schlafen"
    elif mode0 == 32:
        mode_str = "Anwesend"
    elif mode0 == 16:
        mode_str = "Abwesend"
    if day_mode == 1:
        mode_str += ", Tag"
    elif day_mode == 2:
        mode_str += ", Nacht"
    if day_mode >= 4:
        mode_str += ", Alarm"
    props += (
        f"Mode:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        + mode_str
        + "<br>"
    )
    if rtr.mirror_running():
        props += f"Spiegel:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;aktiv"
    else:
        props += f"Spiegel:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;gestoppt"

    def_filename = f"router.smr"
    page = fill_page_template(
        f"Router '{rtr._name}'", type_desc, props, side_menu, "router.jpg", def_filename
    )
    page = adjust_settings_button(page, "rtr", f"{0}")
    return web.Response(text=page, content_type="text/html")


def show_module_overview(app, mod_addr) -> web.Response:
    """Prepare overview page of module."""
    api_srv = app["api_srv"]
    module = api_srv.routers[0].get_module(mod_addr)
    side_menu = activate_side_menu(app["side_menu"], ">Module<")
    side_menu = activate_side_menu(side_menu, f"module-{module._id}")
    mod_image, type_desc = get_module_image(module._typ)
    mod_description = get_module_properties(module)
    def_filename = f"module_{mod_addr}.smm"
    page = fill_page_template(
        f"Modul '{module._name}'",
        type_desc,
        mod_description,
        side_menu,
        mod_image,
        def_filename,
    )
    page = adjust_settings_button(page, "mod", f"{mod_addr}")
    return web.Response(text=page, content_type="text/html")


def fill_page_template(
    title, subtitle, content, menu, image, download_file: str
) -> str:
    """Prepare config web page with content, image, and menu."""
    with open(WEB_FILES_DIR + CONFIG_TEMPLATE_FILE, mode="r") as tplf_id:
        page = tplf_id.read()
    page = (
        page.replace("ContentTitle", title)
        .replace("ContentSubtitle", subtitle)
        .replace("ContentText", content)
        .replace("<!-- SideMenu -->", menu)
        .replace("controller.jpg", image)
        .replace("my_module.smm", download_file)
    )
    return page


def show_settings(app, mod_addr) -> web.Response:
    """Prepare settings page of module."""
    if mod_addr > 0:
        settings = app["api_srv"].routers[0].get_module(mod_addr).get_module_settings()
        title_str = f"Modul '{settings.name}'"
    else:
        settings = app["api_srv"].routers[0].get_router_settings()
        title_str = f"Router '{settings.name}'"
    app["settings"] = settings
    app["key"] = ""
    page = fill_settings_template(app, title_str, "Grundeinstellungen", 0, settings, "")
    return web.Response(text=page, content_type="text/html")


def show_setting_step(app, mod_addr, step) -> web.Response:
    """Prepare overview page of module."""
    mod_settings = app["settings"]
    if mod_addr > 0:
        title_str = f"Modul '{mod_settings.name}'"
    else:
        title_str = f"Router '{mod_settings.name}'"
    if step > 0:
        key, header, prompt = get_property_kind(app["props"], app["io_keys"], step)
        app["prompt"] = prompt
        app["key"] = key
        page = fill_settings_template(app, title_str, header, step, mod_settings, key)
    else:
        page = fill_settings_template(
            app, title_str, "Grundeinstellungen", 0, mod_settings, ""
        )
    return web.Response(text=page, content_type="text/html")


def show_popup(message) -> web.Response:
    """Open popup window."""
    page = f'<div class="popup" onclick="myFunction()">Click me!<span class="popuptext" id="myPopup">{message}</span></div>'
    return web.Response(text=page, content_type="text/html")


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


def adjust_settings_button(page, type, addr: str) -> str:
    """Specify button."""
    if type.lower() == "gtw":
        page = page.replace("ModSettings", "GtwSettings")
    elif type.lower() == "rtr":
        page = page.replace("ModSettings", "RtrSettings")
    else:
        page = page.replace("ModAddress", addr)
    return page


def get_module_image(type_code: bytes) -> (str, str):
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
    return mod_image, type_desc


def get_module_properties(mod) -> str:
    """Return module properties, like firmware."""
    props = "<h3>Eigenschaften</h3>"
    props += f"Adresse:   {mod._id}<br>"
    ser = mod.get_serial()
    if len(ser) > 0:
        props += f"Hardware:   {mod.get_serial()}<br>"
    props += f"Firmware:   {mod.get_sw_version()}<br>"
    return props


def fill_settings_template(app, title, subtitle, step, settings, key: str) -> str:
    """Return settings page."""
    with open(WEB_FILES_DIR + SETTINGS_TEMPLATE_FILE, mode="r") as tplf_id:
        page = tplf_id.read()
    mod_image, mod_type = get_module_image(settings.typ)
    page = (
        page.replace("ContentTitle", title)
        .replace("ContentSubtitle", subtitle)
        .replace("controller.jpg", mod_image)
        .replace("ModAddress", f"{settings.id}-{step}")
    )
    if step == 0:
        page = disable_button("zurück", page)
        # page = page.replace('form="settings_table"', "")
        settings_form = prepare_basic_settings(app, settings.id, mod_type)

    else:
        if step == app["props"]["no_keys"]:
            page = disable_button("weiter", page)
        settings_form = prepare_table(app, settings.id, key)
    page = page.replace("<p>ContentText</p>", settings_form)
    return page


def indent(level):
    """Return sequence of tabs according to level."""
    return "\t" * level


def disable_button(key: str, page) -> str:
    return page.replace(f">{key}<", f" disabled>{key}<")


def prepare_basic_settings(app, mod_addr, mod_type):
    """Prepare settings page for basic settings, e.g. name."""
    settings = app["settings"]
    tbl = indent(4) + f'<form id="settings_table" action="settings" method="post">\n'
    tbl += "\n" + indent(5) + "<table>\n"
    id_name = "mname"
    if mod_addr > 0:
        prompt = "Modulname"
    else:
        prompt = "Routername"
    tbl += (
        indent(7)
        + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[0]" type="text" id="{id_name}" value="{settings.name}"/></td></tr>\n'
    )
    if settings.type in [
        "Smart Controller XL-1",
        "Smart Controller XL-2",
        "Smart Controller Mini",
    ]:
        id_name = "displ_contr"
        prompt = "Display-Kontrast"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[1]" type="text" id="{id_name}" value="{settings.status[MirrIdx.DISPL_CONTR]}"/></td></tr>\n'
        )
        id_name = "displ_time"
        prompt = "Display-Leuchtzeit"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[1]" type="text" id="{id_name}" value="{settings.status[MirrIdx.MOD_LIGHT_TIM]}"/></td></tr>\n'
        )
        id_name = "temp_ctl"
        prompt = "Temperatur-Regelverhalten"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[1]" type="text" id="{id_name}" value="{settings.status[MirrIdx.CLIM_SETTINGS]}"/></td></tr>\n'
        )
        id_name = "temp_1_2"
        prompt = "Temperatursensor"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[1]" type="text" id="{id_name}" value="{settings.status[MirrIdx.TMP_CTL_MD]}"/></td></tr>\n'
        )
    if settings.type in ["Smart Controller XL-1", "Smart Controller XL-2"]:
        id_name = "supply"
        prompt = "Versorgungspriorität 230V / 24V"
        if settings.status[MirrIdx.SUPPLY_PRIO] == 66:
            sply_str = "24V"
        else:
            sply_str = "230V"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[2]" type="text" id="{id_name}" value="{sply_str}"/></td></tr>\n'
        )
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


def prepare_table(app, mod_addr, key) -> str:
    """Prepare settings table with form of edit fields."""
    # action="settings_update-{mod_addr}-{key}"
    key_prompt = app["prompt"]
    covers = getattr(app["settings"], "covers")
    tbl_data = getattr(app["settings"], key)
    tbl = (
        indent(4) + f'<form id="settings_table" action="settings_step" method="post">\n'
    )
    tbl += "\n" + indent(5) + "<table>\n"
    for ci in range(len(tbl_data)):
        id_name = key[:-1] + str(ci)
        prompt = key_prompt + f" {tbl_data[ci].nmbr}"
        if key in ["leds", "buttons", "dir_cmds"]:
            maxl = 18
        else:
            maxl = 32
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[{ci},0]" type="text" id="{id_name}" maxlength="{maxl}" value="{tbl_data[ci].name[:maxl].strip()}"></td>'
        )
        if key in ["leds", "buttons", "dir_cmds"]:
            tbl += f'<td></td><td><input name="data[{ci},1]" type="text" id="{id_name}" maxlength="14" value="{tbl_data[ci].name[18:].strip()}"></td>'
        elif key == "inputs":
            if tbl_data[ci].type == 1:
                btn_checked = "checked"
                sw_checked = ""
            elif tbl_data[ci].type == 2:
                btn_checked = ""
                sw_checked = "checked"
            tbl += f'<td><label for="{id_name}_sw">Schalter</label><input type="radio" name="data[{ci},1]" id="{id_name}_sw" value = "sw" {sw_checked}></td>'
            tbl += f'<td><label for="{id_name}_btn">Taster</label><input type="radio" name="data[{ci},1]" id="{id_name}_btn" value = "btn" {btn_checked}></td>'
        elif key == "outputs":
            if (ci < 2 * len(covers)) & ((ci % 2) == 0):
                if tbl_data[ci].type == -10:
                    out_chkd = ""
                    cvr_chkd = "checked"
                else:
                    out_chkd = "checked"
                    cvr_chkd = ""
                tbl += f'<td><label for="{id_name}_out">Ausgang</label><input type="radio" name="data[{ci},1]" id="{id_name}_out" value="out" {out_chkd}></td>'
                tbl += f'<td><label for="{id_name}_cvr">Rollladen</label><input type="radio" name="data[{ci},1]" id="{id_name}_cvr" value="cvr" {cvr_chkd}></td>'
        elif (key == "covers") & (covers[ci].type != 0):
            cov_t = app["settings"].cover_times
            bld_t = app["settings"].blade_times
            if tbl_data[ci].type > 0:
                ipol_chkd = "checked"
            else:
                ipol_chkd = ""
            tbl += f'<td></td><td><input name="data[{ci},1]" type="text" id="{id_name}_tc" maxlength="4" placeholder="Verfahrzeit in s" value = {cov_t[ci]} style="width: 40px;"></td>'
            tbl += f'<td></td><td><input name="data[{ci},2]" type="text" id="{id_name}_tb" maxlength="4" placeholder="Jalousiezeit in s (0 falls Rollladen)" value = {bld_t[ci]} style="width: 40px;"></td>'
            tbl += f'<td><input type="checkbox" name="data[{ci},3]" value="pol_nrm" id="{id_name}_pinv" {ipol_chkd}><label for="{id_name}_pinv">Polarität, Ausg. A: auf</label></td>'
        tbl += "</tr>\n"
    if key in ["glob_flags", "flags", "groups", "dir_cmds", "coll_cmds"]:
        # Add additional line to append
        prompt = "Zusatz" + key_prompt[:1].lower() + key_prompt[1:]
        id_name = key[:-1] + str(ci + 1)
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[{ci},1000]" type="text" placeholder="Nummer eintragen" id="{id_name}"/></td></tr>\n'
        )
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


def parse_response_form(app, form_data):
    """Parse configuration input form and store results in settings."""
    key = app["key"]
    settings = app["settings"]
    for form_key in list(form_data.keys())[:-1]:
        indices = form_key.replace("data[", "").replace("]", "").split(",")
        indices[0] = int(indices[0])
        indices[1] = int(indices[1])
        if len(indices) == 1:
            settings.__getattribute__(key)[int(indices[0])].name = form_data[form_key][
                0
            ]
        elif indices[1] == 0:
            settings.__getattribute__(key)[int(indices[0])].name = form_data[form_key][
                0
            ]
        elif indices[1] == 1000:
            # add element
            settings.__getattribute__(key).append(
                IfDescriptor("New", int(form_data[form_key][0]), 0)
            )
        if (len(indices) > 1) & (indices[1] != 1000):
            match app["key"]:
                case "inputs":
                    if form_data[form_key][0] == "sw":
                        settings.inputs[indices[0]].type = 2
                    else:
                        settings.inputs[indices[0]].type = 1
                case "outputs":
                    covers = getattr(app["settings"], "covers")
                    if form_data[form_key][0] == "cvr":
                        settings.outputs[indices[0]].type = -10
                        settings.outputs[indices[0] + 1].type = -10
                        if settings.covers[int(indices[0] / 2)].type == 0:
                            # needs new setting (polaritiy, blades)
                            settings.covers[int(indices[0] / 2)].type = 1
                            cvr_name = (
                                settings.outputs[indices[0]]
                                .name.replace("auf", "")
                                .replace("ab", "")
                                .replace("hoch", "")
                                .replace("runter", "")
                                .replace("zu", "")
                                .replace("up", "")
                                .replace("down", "")
                            )
                            settings.covers[int(indices[0] / 2)].name = cvr_name
                    elif form_data[form_key][0] == "out":
                        settings.outputs[indices[0]].type = 1
                        settings.outputs[indices[0] + 1].type = 1
                        settings.covers[int(indices[0] / 2)].type = 0
                        settings.covers[int(indices[0] / 2)].name = ""
                case "covers":
                    if indices[1] == 0:
                        # look for 'missing' checkbox entry
                        if not f"data[{indices[0]},3]" in form_data.keys():
                            settings.covers[indices[0]].type = abs(
                                settings.covers[indices[0]].type
                            ) * (-1)
                    elif indices[1] == 1:
                        settings.cover_times[indices[0]] = float(form_data[form_key][0])
                    elif indices[1] == 2:
                        settings.blade_times[indices[0]] = float(form_data[form_key][0])
                        if float(form_data[form_key][0]) > 0:
                            settings.covers[indices[0]].type = int(
                                copysign(2, settings.covers[indices[0]].type)
                            )
                    elif indices[1] == 3:
                        if form_data[form_key][0] == "pol_nrm":
                            settings.covers[indices[0]].type = abs(
                                settings.covers[indices[0]].type
                            )
                        else:
                            settings.covers[indices[0]].type = abs(
                                settings.covers[indices[0]].type
                            ) * (-1)
                case "leds" | "buttons" | "dir_cmds":
                    if indices[1] == 0:
                        # use only first part for parsing and look for second
                        if f"data[{indices[0]},1]" in form_data.keys():
                            name = form_data[form_key][0]
                            name += " " * (18 - len(name))
                            name += form_data[f"data[{indices[0]},1]"][0]
                            name += " " * (32 - len(name))
                        else:
                            name = form_data[form_key][0]
                            name += " " * (32 - len(name))
                        settings.__getattribute__(key)[indices[0]].name = name
    app["settings"] = settings


async def return_module_settings(app, mod_addr: int):
    """Collect modified settings and return them to modules."""
    settings = app["settings"]
    rtr = app["api_srv"].routers[0]
    module = rtr.get_module(mod_addr)
    logger = app["logger"]

    settings.status[MirrIdx.MOD_NAME : MirrIdx.MOD_NAME + 32] = (
        settings.name + " " * (32 - len(settings.name))
    ).encode("iso8859-1")
    # settings.status[MirrIdx.DISPL_CONTR] = int.to_bytes(settings.displ_contr)
    if settings.supply_prio == "24V":
        settings.status[MirrIdx.SUPPLY_PRIO] = b"B"
    else:
        settings.status[MirrIdx.SUPPLY_PRIO] = b"A"
    module.status = settings.status
    # module.smg_upload = module.build_smg()
    # await rtr.set_config_mode(True)
    # await module.hdlr.send_module_smg(mod_addr)
    # await rtr.set_config_mode(False)

    list_lines = format_smc(settings.list).split("\n")
    new_list = []
    new_line = ""
    for lchr in list_lines[0].split(";")[:-1]:
        new_line += chr(int(lchr))
    new_list.append(new_line)
    for line in list_lines[1:]:
        if len(line) > 0:
            tok = line.split(";")
            if (tok[0] != "253") & (tok[0] != "255"):
                new_line = ""
                for lchr in line.split(";")[:-1]:
                    new_line += chr(int(lchr))
                new_list.append(new_line)
    for dir_cmd in settings.dir_cmds:
        desc = dir_cmd.name
        if len(desc.strip()) > 0:
            desc += " " * (32 - len(desc))
            new_list.append(f"\xfd\0\xeb{dir_cmd.nmbr}\1\x23\0\xeb" + desc)
    for btn in settings.buttons:
        desc = btn.name
        if len(desc.strip()) > 0:
            desc += " " * (32 - len(desc))
            new_list.append(f"\xff\0\xeb{9 + btn.nmbr}\1\x23\0\xeb" + desc)
    for led in settings.leds:
        desc = led.name
        if len(desc.strip()) > 0:
            desc += " " * (32 - len(desc))
            new_list.append(f"\xff\0\xeb{17 + led.nmbr}\1\x23\0\xeb" + desc)
    for inpt in settings.inputs:
        desc = inpt.name
        if len(desc.strip()) > 0:
            desc += " " * (32 - len(desc))
            new_list.append(f"\xff\0\xeb{39 + inpt.nmbr}\1\x23\0\xeb" + desc)
    for outpt in settings.outputs:
        desc = outpt.name
        if len(desc.strip()) > 0:
            desc += " " * (32 - len(desc))
            new_list.append(f"\xff\0\xeb{59 + outpt.nmbr}\1\x23\0\xeb" + desc)
    for lgc in settings.logic:
        desc = lgc.name
        desc += " " * (32 - len(desc))
        new_list.append(f"\xff\0\xeb{109 + lgc.nmbr}\1\x23\0\xeb" + desc)
    for flg in settings.flags:
        desc = flg.name
        desc += " " * (32 - len(desc))
        new_list.append(f"\xff\0\xeb{119 + flg.nmbr}\1\x23\0\xeb" + desc)
    no_lines = len(new_list) - 1
    no_chars = 0
    for line in new_list[1:]:
        no_chars += len(line)
    new_list[
        0
    ] = f"{chr(no_lines & 0xFF)}{chr(no_lines >> 8)}{chr(no_chars & 0xFF)}{chr(no_chars >> 8)}"

    list_bytes = ""
    for line in new_list:
        list_bytes += line
    list_bytes = list_bytes.encode("iso8859-1")

    module.list_upload = list_bytes
    if ModbusComputeCRC(module.list_upload) != module.get_smc_crc():
        await rtr.set_config_mode(True)
        await module.hdlr.send_module_list(mod_addr)
        await rtr.set_config_mode(False)
        logger.info(f"Changed configuration list stored in module {mod_addr}")
    else:
        logger.debug(f"No changes in configuration list for module {mod_addr}")
    module.list_upload = b""


def get_property_kind(props, io_keys, step):
    """Return header of property kind."""
    if step == 0:
        return "", "Grundeinstellungen"
    cnt = 0
    for key in io_keys:
        if props[key] > 0:
            cnt += 1
        if cnt == step:
            break
    match key:
        case "buttons":
            header = "Tasterbeschriftung"
            prompt = "Taste"
        case "leds":
            header = "LED-Beschriftung"
            prompt = "LED"
        case "inputs":
            header = "Eingänge"
            prompt = "Eingang"
        case "outputs":
            header = "Ausgänge"
            prompt = "Ausgang"
        case "covers":
            header = "Rollladen"
            prompt = "Rollladen"
        case "logic":
            header = "Logik-Bausteine"
            prompt = "Logik-Baustein"
        case "flags":
            header = "Lokale Merker"
            prompt = "Merker"
        case "dir_cmds":
            header = "Direktbefehle"
            prompt = "Direktbefehl"
        case "vis_cmds":
            header = "Visualisierungsbefehle"
            prompt = "Visualisierungsbefehl"
        case "glob_flags":
            header = "Globale Merker"
            prompt = "Merker"
        case "coll_cmds":
            header = "Sammelbefehle"
            prompt = "Sammelbefehl"
        case "groups":
            header = "Gruppen"
            prompt = "Gruppe"
    return key, header, prompt


def format_smc(buf: bytes) -> str:
    """Parse line structure and add ';' and linefeeds."""
    no_lines = int.from_bytes(buf[:2], "little")
    str_data = ""
    for byt in buf[:4]:
        str_data += f"{byt};"
    str_data += "\n"
    ptr = 4  # behind header with no of lines/chars
    for l_idx in range(no_lines):
        l_len = buf[ptr + 5] + 5
        for byt in buf[ptr : ptr + l_len]:
            str_data += f"{byt};"  # dezimal values, seperated with ';'
        str_data += "\n"
        ptr += l_len
    return str_data


def format_smg(buf: bytes) -> str:
    """Parse structure and add ';' and final linefeed."""
    str_data = ""
    for byt in buf:
        str_data += f"{byt};"
    str_data += "\n"
    return str_data


def format_smm(status, list: bytes) -> str:
    """Generate single module data file."""
    smg_str = format_smg(status)
    smc_str = format_smc(list)
    return smg_str + smc_str


def seperate_upload(upload_str: str) -> (bytes, bytes):
    """Seperate smg and list from data, remove ';' and lf, and convert to bytes"""
    lines = upload_str.split("\n")
    smg_bytes = b""
    for byt in lines[1].split(";"):
        smg_bytes += int.to_bytes(int(byt))
    smc_bytes = b""
    for line in lines[2:]:
        for byt in line.split(";"):
            smc_bytes += int.to_bytes(int(byt))
    return smg_bytes, smc_bytes


async def send_to_router(app, content: str):
    """Send uploads to module."""
    rtr = app["api_srv"].routers[0]
    await rtr.set_config_mode(True)
    await rtr.hdlr.send_rt_full_status()
    # Routerstatus neu lesen
    # Weiterleitung neu starten
    rtr.smr_upload = b""
    await rtr.set_config_mode(False)


async def send_to_module(app, content: str, mod_addr: int):
    """Send uploads to module."""
    rtr = app["api_srv"].routers[0]
    module = rtr.get_module(mod_addr)
    module.smg_upload, module.list_upload = seperate_upload(content)
    if ModbusComputeCRC(module.list_upload) != module.get_smc_crc():
        await rtr.set_config_mode(True)
        await module.hdlr.send_module_list(mod_addr)
        await rtr.set_config_mode(False)
    if module.different_smg_crcs():
        await rtr.set_config_mode(True)
        await module.hdlr.send_module_smg(module._id)
        await module.hdlr.get_module_status(module._id)
        await rtr.set_config_mode(False)
    module.smg_upload = b""
    module.list_upload = b""
