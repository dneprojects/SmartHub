from math import copysign
from aiohttp import web
from urllib.parse import parse_qs
from multidict import MultiDict
from pymodbus.utilities import computeCRC as ModbusComputeCRC
from configuration import RouterSettings
import asyncio
import logging
import pathlib
import re
from const import (
    WEB_FILES_DIR,
    SIDE_MENU_FILE,
    CONFIG_TEMPLATE_FILE,
    SETTINGS_TEMPLATE_FILE,
    AUTOMATIONS_TEMPLATE_FILE,
    CONF_PORT,
    SYS_MODES,
    FingerNames,
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


class ConfigServer:
    """Web server for basic configuration tasks."""

    def __init__(self, sm_hub):
        self.sm_hub = sm_hub
        self._ip = sm_hub._host_ip
        self._port = CONF_PORT
        self.logger = logging.getLogger(__name__)
        self.conf_running = False
        self.app: web.Application = []

    async def initialize(self):
        """Initialize config server."""
        self.app = web.Application()
        self.app["smhub"] = self.sm_hub
        self.app.add_routes(routes)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self._ip, self._port)
        self.app["logger"] = self.logger

    async def prepare(self):
        """Second initialization after api_srv is initialized."""
        self.api_srv = self.sm_hub.api_srv
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
        hub_name = api_srv.sm_hub._host
        html_str = get_html("hub.html").replace("HubTitle", f"Smart Hub '{hub_name}'")
        html_str = html_str.replace(
            "Overview", "Smart Hub - Systemzentrale und Schnittstelle zum Netzwerk"
        )
        html_str = html_str.replace(
            "ContentText",
            "<h3>Eigenschaften</h3>\n<p>"
            + api_srv.sm_hub.info.replace(" ", "&nbsp;&nbsp;").replace(
                "\n", "</p>\n<p>"
            )
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
        if args[0] == "EditAutomtns":
            mod_addr = int(args[1])
            request.app["step"] = 0
            return build_show_automations(request.app, mod_addr, 0)
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
        settings = request.app["settings"]
        for form_key in list(form_data.keys())[:-1]:
            settings.__setattr__(form_key, form_data[form_key][0])
        request.app["settings"] = settings
        args = form_data["ModSettings"][0]
        return await show_next_prev(request, args)

    @routes.post("/settings_step")
    async def root(request: web.Request) -> web.Response:
        resp = await request.text()
        form_data = parse_qs(resp)
        args = parse_response_form(request.app, form_data)
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

    @routes.get("/teach")
    async def root(request: web.Request) -> web.Response:
        args = request.query_string.split("=")
        return await show_next_prev(request, args[1])

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
            return show_router_overview(request.app)
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
            return show_module_overview(request.app, mod_addr)  # web.HTTPNoContent()

    @routes.post("/automtns")
    async def root(request: web.Request) -> web.Response:
        resp = await request.text()
        form_data = parse_qs(resp)
        if "ModSettings" in form_data.keys():
            args = form_data["ModSettings"][0].split("-")
            action = args[0]
            mod_addr = int(args[1])
            step = int(args[2])
            match action:
                case "save":
                    request.app["logger"].warning(
                        "Save of automations not yet implemented"
                    )
                    return show_module_overview(request.app, mod_addr)
                case "next":
                    step += 1
                case "back":
                    step -= 1
            request.app["step"] = step
            return show_automations(request.app, step)
        else:
            # delete selected automation
            settings = request.app["settings"]
            sel_automtn = int(form_data["atmn_tbl"][0])
            request.app["automations_def"].selected = sel_automtn
            # request.app["logger"].warning(
            #     f"Delete of automation {sel_automtn} not yet implemented"
            # )
            if request.app["step"] == 0:
                del request.app["automations_def"].local[sel_automtn]
            else:
                l_ext = len(request.app["automations_def"].external)
                if sel_automtn < l_ext:
                    del request.app["automations_def"].external[sel_automtn]
                else:
                    del request.app["automations_def"].forward[sel_automtn - l_ext]
            return show_automations(request.app, request.app["step"])

    @routes.get(path="/{key:.*}")
    async def _(request):
        request.app["logger"].warning("Route not yet implemented")
        return web.HTTPNoContent()

    @routes.post(path="/{key:.*}")
    async def _(request):
        request.app["logger"].warning("Route not yet implemented")
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
    settings = request.app["settings"]
    if button == "new_finger":
        step = 2
        user_id = settings.users_sel + 1
        finger_id = int(args1[2])
        await settings.teach_new_finger(request.app, user_id, finger_id)
        return show_setting_step(request.app, mod_addr, step)
    else:
        step = int(args1[2])
    if button == "cancel":
        if mod_addr > 0:
            return show_module_overview(request.app, mod_addr)
        else:
            return show_router_overview(request.app)

    if button == "save":
        logger = request.app["logger"]
        if mod_addr > 0:
            module = settings.module
            router = module.rt
            await request.app["api_srv"].block_network_if(module.rt._id, True)
            try:
                await module.set_settings(settings)
                request.app["side_menu"] = adjust_side_menu(router.modules)
                if settings.group != int(settings.group_member):
                    # group membership changed, update in router
                    router = request.app["api_srv"].routers[0]
                    await router.set_module_group(mod_addr, int(settings.group_member))
            except Exception as err_msg:
                logger.error(f"Error while saving module settings: {err_msg}")
            await request.app["api_srv"].block_network_if(module.rt._id, False)
            return show_module_overview(request.app, mod_addr)
        else:
            # Save settings in router
            router = request.app["api_srv"].routers[0]
            await request.app["api_srv"].block_network_if(router._id, True)
            try:
                await router.set_settings(settings)
                router.set_descriptions(settings)
                request.app["side_menu"] = adjust_side_menu(
                    request.app["api_srv"].routers[0].modules
                )
            except Exception as err_msg:
                logger.error(f"Error while saving router settings: {err_msg}")
            await request.app["api_srv"].block_network_if(router._id, False)
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
    if rtr.settings == []:
        page = fill_page_template(
            f"Router", type_desc, "Router not found", side_menu, "router.jpg", ""
        )
        page = adjust_settings_button(page, "", f"{0}")
        return web.Response(text=page, content_type="text/html")
    props = "<h3>Eigenschaften</h3>"
    props += (
        f"Hardware:&nbsp;&nbsp;&nbsp;&nbsp;{rtr.serial.decode('iso8859-1')[1:]}<br>"
    )
    props += (
        f"Firmware:&nbsp;&nbsp;&nbsp;&nbsp;{rtr.version.decode('iso8859-1')[1:]}<br>"
    )
    mode0 = rtr.mode0
    config_mode = mode0 == SYS_MODES.Config
    day_mode = mode0 & 0x3
    alarm_mode = mode0 & 0x4
    mode0 = mode0 & 0xF8
    mode_str = ""
    if config_mode:
        mode_str = "Konfig"
    elif mode0 == 112:
        mode_str = "Urlaub"
    elif mode0 == 96:
        mode_str = rtr.user_modes[12:].decode("iso8859-1").strip()
    elif mode0 == 80:
        mode_str = rtr.user_modes[1:11].decode("iso8859-1").strip()
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
    if alarm_mode == 4:
        mode_str += ", Alarm"
    if mode_str[0] == ",":
        mode_str = mode_str[2:]
    props += (
        f"Mode:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        + mode_str
        + "<br>"
    )
    if api_srv._opr_mode:
        props += f"Betriebsart:&nbsp;&nbsp;Operate<br>"
    else:
        props += f"Betriebsart:&nbsp;&nbsp;Client/Server<br>"
    if api_srv.mirror_mode_enabled & api_srv._opr_mode:
        props += f"Spiegel:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;aktiv<br>"
    else:
        props += f"Spiegel:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;inaktiv<br>"
    if api_srv.event_mode_enabled & api_srv._opr_mode:
        props += (
            f"Events:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;aktiv<br>"
        )
    else:
        props += f"Events:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;inaktiv<br>"

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
    if module.has_automations():
        page = adjust_automations_button(page)
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


def build_show_automations(app, mod_addr, step) -> web.Response:
    """Prepare automations page of module."""
    settings = app["api_srv"].routers[0].get_module(mod_addr).get_module_settings()
    app["automations_def"] = settings.automtns_def
    app["settings"] = settings
    return show_automations(app, step)


def show_automations(app, step) -> web.Response:
    """Prepare automations page of module."""
    title_str = f"Modul '{app['settings'].name}'"
    if step == 0:
        subtitle = "Lokale Automatisierungen"
    else:
        subtitle = "Externe Automatisierungen"
    page = fill_automations_template(app, title_str, subtitle, step)
    return web.Response(text=page, content_type="text/html")


def show_setting_step(app, mod_addr, step) -> web.Response:
    """Prepare overview page of module."""
    mod_settings = app["settings"]
    if mod_addr > 0:
        title_str = f"Modul '{mod_settings.name}'"
    else:
        title_str = f"Router '{mod_settings.name}'"
    if step > 0:
        key, header, prompt = get_property_kind(app, step)
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
    elif type == "":
        page = page.replace(">Einstellungen"," disabled >Einstellungen")
        page = page.replace(">Konfigurationsdatei"," disabled >Konfigurationsdatei")
    else:
        page = page.replace("ModAddress", addr)
    return page


def adjust_automations_button(page: str) -> str:
    """Enable edit automations button."""
    page = page.replace("<!--<button", "<button").replace("</button>-->", "</button>")
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
    return mod_image, type_desc


def get_module_properties(mod) -> str:
    """Return module properties, like firmware."""
    props = "<h3>Eigenschaften</h3>"
    props += f"Adresse:&nbsp;&nbsp;&nbsp;{mod._id}<br>"
    ser = mod.get_serial()
    if len(ser) > 0:
        props += f"Hardware:&nbsp;&nbsp;{mod.get_serial()}<br>"
    props += f"Firmware:&nbsp;&nbsp;{mod.get_sw_version()}<br>"
    return props


def fill_settings_template(app, title, subtitle, step, settings, key: str) -> str:
    """Return settings page."""
    with open(WEB_FILES_DIR + SETTINGS_TEMPLATE_FILE, mode="r") as tplf_id:
        page = tplf_id.read()
    if key == "fingers":
        mod_image, mod_type = get_module_image(b"\x1f")
    else:
        mod_image, mod_type = get_module_image(settings.typ)
    page = (
        page.replace("ContentTitle", title)
        .replace("ContentSubtitle", subtitle)
        .replace("controller.jpg", mod_image)
        .replace("ModAddress", f"{settings.id}-{step}")
    )
    if key == "fingers":
        finger_dict_str = "var fngrNames = {\n"
        for f_i in range(10):
            finger_dict_str += f'  {f_i+1}: "{FingerNames[f_i]}",\n'
        finger_dict_str += "}\n"
        page = page.replace("var fngrNames = {}", finger_dict_str)
    if step == 0:
        page = disable_button("zurück", page)
        # page = page.replace('form="settings_table"', "")
        settings_form = prepare_basic_settings(app, settings.id, mod_type)

    else:
        if step == app["props"]["no_keys"]:
            page = disable_button("weiter", page)
        settings_form = prepare_table(app, settings.id, step, key)
    page = page.replace("<p>ContentText</p>", settings_form)
    return page


def fill_automations_template(app, title, subtitle, step) -> str:
    """Return automations page."""
    with open(WEB_FILES_DIR + AUTOMATIONS_TEMPLATE_FILE, mode="r") as tplf_id:
        page = tplf_id.read()
    mod_image, mod_type = get_module_image(app["settings"].typ)
    page = (
        page.replace("ContentTitle", title)
        .replace("ContentSubtitle", subtitle)
        .replace("controller.jpg", mod_image)
        .replace("ModAddress", f'{app["settings"].id}-{step}')
    )
    if step == 0:
        page = disable_button("zurück", page)
        if (len(app["automations_def"].external) == 0) & (
            len(app["automations_def"].forward) == 0
        ):
            page = disable_button("weiter", page)
    else:
        page = disable_button("weiter", page)
    settings_form = prepare_automations_list(app, step)
    page = page.replace("<p>ContentText</p>", settings_form)
    return page


def indent(level):
    """Return sequence of tabs according to level."""
    return "\t" * level


def disable_button(key: str, page) -> str:
    return page.replace(f">{key}<", f" disabled>{key}<")


def prepare_automations_list(app, step):
    """Prepare automations list page."""
    curr_mod = 0
    if step == 0:
        automations = app["automations_def"].local
    else:
        automations = app["automations_def"].external
    tbl = indent(4) + f'<form id="automations_table" action="automtns" method="post">\n'
    tbl += indent(5) + "<table>\n"
    for at_i in range(len(automations)):
        if step > 0:
            src_mod = automations[at_i].src_mod
            if src_mod != curr_mod:
                tbl += (
                    indent(6)
                    + f"<tr><td><b>Von Router {automations[at_i].src_rt}, Modul {src_mod}</b></td></tr>\n"
                )
        tbl += indent(6) + "<tr>\n"
        evnt_desc = automations[at_i].event_description()
        actn_desc = automations[at_i].action_description()
        id_name = f"atmn_tbl"
        sel_chkd = ""
        if at_i == app["automations_def"].selected:
            sel_chkd = "checked"
        tbl += (
            indent(7)
            + f"<td>{evnt_desc}</td><td align=center>&nbsp;&nbsp;&rArr;&nbsp;&nbsp;</td>\n"
        )
        tbl += indent(7) + f"<td>{actn_desc}</td>\n"
        tbl += f'<td><input type="radio" name="{id_name}" id="{id_name}" value="{at_i}" {sel_chkd}></td>'
        tbl += indent(6) + "</tr>\n"
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


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
        + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="name" type="text" maxlength="32" id="{id_name}" value="{settings.name}"/></td></tr>\n'
    )
    if mod_addr > 0:
        # Module
        id_name = "group_member"
        prompt = "Gruppenzugehörigkeit"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><select name="{id_name}" id="{id_name}">\n'
        )
        rtr = app["api_srv"].routers[0]
        groups = rtr.groups
        rt_settings = RouterSettings(rtr)
        grps = rt_settings.groups
        for grp in grps:
            if grp.nmbr == settings.group:
                tbl += (
                    indent(8)
                    + f'<option value="{grp.nmbr}" selected>{grp.name}</option>\n'
                )
            else:
                tbl += indent(8) + f'<option value="{grp.nmbr}">{grp.name}</option>\n'
        tbl += indent(7) + "/select></td></tr>\n"
    else:
        # Router
        id_name = "user1_name"
        prompt = "Benutzer Modus 1"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" type="text" maxlength="10" id="{id_name}" value="{settings.user1_name}"/>\n'
        )
        id_name = "user2_name"
        prompt = "Benutzer Modus 2"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" type="text" maxlength="10" id="{id_name}" value="{settings.user2_name}"/>\n'
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
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" type="number" min="0" max="50" id="{id_name}" value="{settings.displ_contr}"/></td></tr>\n'
        )
        id_name = "displ_time"
        prompt = "Display-Leuchtzeit"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" type="number" min="1" max="240" id="{id_name}" value="{settings.displ_time}"/></td></tr>\n'
        )
    if mod_addr > 0:
        if len(settings.inputs) > 0:
            id_name = "t_short"
            prompt = "Tastendruck kurz [ms]"
            tbl += (
                indent(7)
                + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" type="number" min="10" max="250" id="{id_name}" value="{settings.t_short}"/></td></tr>\n'
            )
            id_name = "t_long"
            prompt = "Tastendruck lang [ms]"
            tbl += (
                indent(7)
                + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" type="number" min="100" max="2500" id="{id_name}" value="{settings.t_long}"/></td></tr>\n'
            )
    if settings.type in [
        "Smart Controller XL-1",
        "Smart Controller XL-2",
        "Smart Dimm",
        "Smart Dimm-1",
        "Smart Dimm-2",
    ]:
        id_name = "t_dimm"
        prompt = "Dimmgeschwindigkeit"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" type="number" min="1" max="10" id="{id_name}" value="{settings.t_dimm}"/></td></tr>\n'
        )
    if settings.type in [
        "Smart Controller XL-1",
        "Smart Controller XL-2",
        "Smart Controller Mini",
    ]:
        id_name = "temp_ctl"
        prompt = "Temperatur-Regelverhalten"
        cl1_checked = ""
        cl2_checked = ""
        cl3_checked = ""
        cl4_checked = ""
        match settings.status[MirrIdx.CLIM_SETTINGS]:
            case 1:
                cl1_checked = "checked"
            case 2:
                cl2_checked = "checked"
            case 3:
                cl3_checked = "checked"
            case 4:
                cl4_checked = "checked"
        tbl += (
            indent(7)
            + f'<td style="vertical-align: top;">{prompt}</td>'
            + f'<td><div><label for="{id_name}_cl1">Heizen</label><input type="radio" name="{id_name}" id="{id_name}_cl1" value = "1" {cl1_checked}></div>'
            + f'<div><label for="{id_name}_cl2">Kühlen</label><input type="radio" name="{id_name}" id="{id_name}_cl2" value = "2" {cl2_checked}></div>'
            + f'<div><label for="{id_name}_cl3">Heizen / Kühlen</label><input type="radio" name="{id_name}" id="{id_name}_cl3" value = "3" {cl3_checked}></div>'
            + f'<div><label for="{id_name}_cl4">Aus</label><input type="radio" name="{id_name}" id="{id_name}_cl4" value = "4" {cl4_checked}></div></td></tr>\n'
        )
        id_name = "temp_1_2"
        prompt = "Temperatursensor"
        if settings.status[MirrIdx.TMP_CTL_MD] == 1:
            s1_checked = "checked"
            s2_checked = ""
        else:
            s1_checked = ""
            s2_checked = "checked"
        tbl += (
            indent(7)
            + f'<td style="vertical-align: top;">{prompt}</td>'
            + f'<td><div><label for="{id_name}_s1">Sensor 1</label><input type="radio" name="{id_name}" id="{id_name}_s1" value = "1" {s1_checked}></div>'
            + f'<div><label for="{id_name}_s2">Sensor 2</label><input type="radio" name="{id_name}" id="{id_name}_s2" value = "2" {s2_checked}></div></td></tr>\n'
        )
    if settings.type in ["Smart Controller XL-1", "Smart Controller XL-2"]:
        id_name = "supply_prio"
        prompt = "Versorgungspriorität"
        if settings.status[MirrIdx.SUPPLY_PRIO] == 66:
            v230_checked = ""
            v24_checked = "checked"
        else:
            v230_checked = "checked"
            v24_checked = ""
        tbl += (
            indent(7)
            + f'<td style="vertical-align: top;">{prompt}</td>'
            + f'<td><div><label for="{id_name}_230">230V</label><input type="radio" name="{id_name}" id="{id_name}_230" value = "230" {v230_checked}></div>'
            + f'<div><label for="{id_name}_24">24V</label><input type="radio" name="{id_name}" id="{id_name}_24" value = "24" {v24_checked}></div></td></tr>\n'
        )
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


def prepare_table(app, mod_addr, step, key) -> str:
    """Prepare settings table with form of edit fields."""
    # action="settings_update-{mod_addr}-{key}"
    key_prompt = app["prompt"]
    if hasattr(app["settings"], "covers"):
        covers = getattr(app["settings"], "covers")
    tbl_data = getattr(app["settings"], key)
    tbl = (
        indent(4) + f'<form id="settings_table" action="settings_step" method="post">\n'
    )
    tbl += "\n" + indent(5) + "<table>\n"

    tbl_enries = dict()
    for ci in range(len(tbl_data)):
        if key == "fingers":
            user_id = app["settings"].users[app["settings"].users_sel].nmbr
            if tbl_data[ci].type == user_id:
                f_nmbr = tbl_data[ci].nmbr
                tbl_enries.update({f_nmbr: ci})
        else:
            tbl_enries.update({tbl_data[ci].nmbr: ci})
    tbl_enries = sorted(tbl_enries.items())
    ci = 0
    for entry in tbl_enries:
        ci = entry[1]
        id_name = key[:-1] + str(ci)
        prompt = key_prompt + f"&nbsp;{tbl_data[ci].nmbr}"
        if key in ["leds", "buttons", "dir_cmds"]:
            maxl = 18
        else:
            maxl = 32
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[{ci},0]" type="text" id="{id_name}" maxlength="{maxl}" value="{tbl_data[ci].name[:maxl].strip()}"></td>'
        )
        if key in ["leds", "buttons", "dir_cmds"]:
            tbl += f'<td><input name="data[{ci},1]" type="text" id="{id_name}" maxlength="14" value="{tbl_data[ci].name[18:].strip()}"></td>'
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
        elif key == "covers":
            if covers[ci].type != 0:
                cov_t = app["settings"].cover_times
                bld_t = app["settings"].blade_times
                if tbl_data[ci].type > 0:
                    ipol_chkd = "checked"
                else:
                    ipol_chkd = ""
                tbl += f'<td></td><td><input name="data[{ci},1]" type="text" id="{id_name}_tc" maxlength="4" placeholder="Verfahrzeit in s" value = {cov_t[ci]} style="width: 40px;"></td>'
                tbl += f'<td></td><td><input name="data[{ci},2]" type="text" id="{id_name}_tb" maxlength="4" placeholder="Jalousiezeit in s (0 falls Rollladen)" value = {bld_t[ci]} style="width: 40px;"></td>'
                tbl += f'<td><input type="checkbox" name="data[{ci},3]" value="pol_nrm" id="{id_name}_pinv" {ipol_chkd}><label for="{id_name}_pinv">Polarität, Ausg. A: auf</label></td>'
        elif key == "groups":
            if tbl_data[ci].nmbr != 0:
                id_name = "group_dep"
                prompt = "Abhängig von Gruppe 0"
                tbl += (
                    indent(7)
                    + f'<td><label for="{id_name}" style="margin-left: 10px;">{prompt}</label></td><td><select name="data[{ci},1]" id="{id_name}">\n'
                )
                dep_names = ["Keine", "Tag/Nacht", "Alarm", "Tag/Nacht, Alarm"]
                for dep in range(4):
                    if dep == app["settings"].mode_dependencies[tbl_data[ci].nmbr]:
                        tbl += (
                            indent(8)
                            + f'<option value="{dep}" selected>{dep_names[dep]}</option>\n'
                        )
                    else:
                        tbl += (
                            indent(8)
                            + f'<option value="{dep}">{dep_names[dep]}</option>\n'
                        )
                tbl += indent(7) + "/select></td>\n"
        elif key == "users":
            # add radio buttons to select user
            id_name = "users_sel"
            if ci == app["settings"].users_sel:
                sel_chkd = "checked"
            else:
                sel_chkd = ""
            tbl += f'<td><label for="{id_name}">Auswahl</label><input type="radio" name="{id_name}" id="{id_name}" value="{ci}" {sel_chkd}></td>'
        tbl += "</tr>\n"
    if key in [
        "glob_flags",
        "flags",
        "groups",
        "dir_cmds",
        "coll_cmds",
        "logic",
        "users",
        "fingers",
    ]:
        # Add additional line to append or delete element
        prompt = key_prompt
        id_name = key[:-1] + str(ci + 1)
        elem_nmbrs = []
        for elem in tbl_data:
            elem_nmbrs.append(elem.nmbr)
        elem_nmbrs = sorted(elem_nmbrs)
        if len(elem_nmbrs) > 0:
            min_new = 1
            for n_idx in range(len(elem_nmbrs)):
                if (elem_nmbrs[n_idx]) == min_new:
                    min_new = elem_nmbrs[n_idx] + 1
                else:
                    break
            min_del = min(elem_nmbrs)
            max_del = max(elem_nmbrs)
        else:
            min_new = 1
            min_del = 1
            max_del = 0
        if key in ["glob_flags", "flags"]:
            max_new = 16
        elif key in ["dir_cmds"]:
            max_new = 25
        elif key in ["groups"]:
            max_new = 80
            min_del = max(1, min_del)
        elif key in ["coll_cmds", "users"]:
            max_new = 255
        elif key in ["fingers"]:
            max_new = 10
        elif key in ["logic"]:
            max_new = 10
        tbl += indent(7) + "<tr><td>&nbsp;</td></tr>"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="new_entry" type="number" min="{min_new}" max="{max_new}" placeholder="Neue Nummer eintragen" id="{id_name}"/></td>\n'
        )
        tbl += (
            indent(7)
            + f'<td><button name="ModSettings" class="new_button" id="config_button" type="submit" form="settings_table" value="new-{mod_addr}-{step}">anlegen</button></td>\n'
            + indent(7)
            + "</tr>\n"
        )
        if key in ["fingers"]:
            tbl = tbl.replace(
                '<button name="ModSettings" class="new_button" id="config_button" type="submit" ',
                '<button name="TeachNewFinger" class="new_button" id="config_button" type="button" ',
            )
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="del_entry" type="number" min="{min_del}" max="{max_del}" placeholder="Existierende Nummer eintragen" id="{id_name}"/></td>\n'
        )
        tbl += (
            indent(7)
            + f'<td><button name="ModSettings" class="new_button" id="config_button" type="submit" form="settings_table" value="del-{mod_addr}-{step}">entfernen</button></td>\n'
            + indent(7)
            + "</tr>\n"
        )
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


def parse_response_form(app, form_data):
    """Parse configuration input form and store results in settings."""
    key = app["key"]
    settings = app["settings"]
    for form_key in list(form_data.keys())[:-1]:
        if form_key == "new_entry":
            # add element
            entry_found = False
            for elem in settings.__getattribute__(key):
                if elem.nmbr == int(form_data[form_key][0]):
                    entry_found = True
                    break
            if not entry_found:
                if key == "fingers":
                    settings.__getattribute__(key).append(
                        IfDescriptor(
                            FingerNames[int(form_data[form_key][0]) - 1],
                            int(form_data[form_key][0]),
                            settings.users[settings.users_sel].nmbr,
                        )
                    )
                else:
                    if key == "users":
                        settings.all_fingers[int(form_data[form_key][0])]: list[
                            IfDescriptor
                        ] = []
                        if not ("users_sel" in dir(settings)):
                            settings.users_sel = 0
                    settings.__getattribute__(key).append(
                        IfDescriptor(
                            f"{key}_{int(form_data[form_key][0])}",
                            int(form_data[form_key][0]),
                            0,
                        )
                    )
        elif form_key == "del_entry":
            # remove element
            idx = 0
            for elem in settings.__getattribute__(key):
                if elem.nmbr == int(form_data[form_key][0]):
                    del settings.__getattribute__(key)[idx]
                    if key == "users":
                        del settings.all_fingers[int(form_data[form_key][0])]
                    break
                idx += 1
        elif form_key == "users_sel":
            settings.users_sel = int(form_data[form_key][0])
        else:
            indices = form_key.replace("data[", "").replace("]", "").split(",")
            indices[0] = int(indices[0])
            indices[1] = int(indices[1])
            if len(indices) == 1:
                settings.__getattribute__(key)[int(indices[0])].name = form_data[
                    form_key
                ][0]
            elif indices[1] == 0:
                settings.__getattribute__(key)[int(indices[0])].name = form_data[
                    form_key
                ][0]
            if len(indices) > 1:
                match app["key"]:
                    case "inputs":
                        if form_data[form_key][0] == "sw":
                            settings.inputs[indices[0]].type = 2
                        else:
                            settings.inputs[indices[0]].type = 1
                    case "outputs":
                        if form_data[form_key][0] == "cvr":
                            settings.outputs[indices[0]].type = -10
                            settings.outputs[indices[0] + 1].type = -10
                            if settings.covers[int(indices[0] / 2)].type == 0:
                                # needs new setting (polarity, blades)
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
                            # names
                            settings.covers[indices[0]].name = form_data[form_key][0]
                            if (
                                settings.outputs[2 * indices[0]].name[
                                    : len(form_data[form_key][0])
                                ]
                                != form_data[form_key][0]
                            ):
                                if settings.covers[indices[0]].type > 0:
                                    settings.outputs[2 * indices[0]].name = (
                                        form_data[form_key][0] + " auf"
                                    )
                                    settings.outputs[2 * indices[0] + 1].name = (
                                        form_data[form_key][0] + " ab"
                                    )
                                else:
                                    settings.outputs[2 * indices[0]].name = (
                                        form_data[form_key][0] + " ab"
                                    )
                                    settings.outputs[2 * indices[0] + 1].name = (
                                        form_data[form_key][0] + " auf"
                                    )
                        elif indices[1] == 1:
                            settings.cover_times[indices[0]] = float(
                                form_data[form_key][0]
                            )
                        elif indices[1] == 2:
                            settings.blade_times[indices[0]] = float(
                                form_data[form_key][0]
                            )
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
                    case "groups":
                        if (indices[0] > 0) & (indices[1] == 1):
                            if indices[0] == 1:
                                # Empty dependencies
                                settings.mode_dependencies = b"P" + b"\0" * 80
                            grp_nmbr = settings.__getattribute__(key)[
                                int(indices[0])
                            ].nmbr
                            settings.mode_dependencies = (
                                settings.mode_dependencies[:grp_nmbr]
                                + int.to_bytes(int(form_data[form_key][0]))
                                + settings.mode_dependencies[grp_nmbr + 1 :]
                            )

    if key == "fingers":
        settings.all_fingers[settings.users[settings.users_sel].nmbr] = settings.fingers
        if "TeachNewFinger" in list(form_data.keys()):
            form_data["ModSettings"] = form_data["TeachNewFinger"]
    app["settings"] = settings
    return form_data["ModSettings"][0]


def get_property_kind(app, step):
    """Return header of property kind."""
    if step == 0:
        return "", "Grundeinstellungen"
    cnt = 0
    props = app["props"]
    io_keys = app["io_keys"]
    settings = app["settings"]
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
        case "users":
            header = "Benutzerverwaltung"
            prompt = "Benutzer"
            if len(settings.users) == 0:
                # disable fingers
                props["no_keys"] = 1
            else:
                # enable fingers
                props["no_keys"] = 2
        case "fingers":
            user_id = settings.users[settings.users_sel].name
            header = f"Fingerabdrücke von '{user_id}'"
            prompt = "Finger"
            if settings.users[settings.users_sel].nmbr in settings.all_fingers.keys():
                settings.fingers = settings.all_fingers[
                    settings.users[settings.users_sel].nmbr
                ]
            else:
                settings.fingers = []
            app["settings"] = settings
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
    for byt in lines[0].split(";"):
        if len(byt) > 0:
            smg_bytes += int.to_bytes(int(byt))
    smc_bytes = b""
    for line in lines[1:]:
        for byt in line.split(";"):
            if len(byt) > 0:
                smc_bytes += int.to_bytes(int(byt))
    return smg_bytes, smc_bytes


async def send_to_router(app, content: str):
    """Send uploads to module."""
    rtr = app["api_srv"].routers[0]
    await rtr.api_srv.block_network_if(rtr._id, True)
    try:
        await rtr.hdlr.send_rt_full_status()
        # Routerstatus neu lesen
        # Weiterleitung neu starten
        rtr.smr_upload = b""
    except Exception as err_msg:
        app["logger"].error(f"Error while uploading router settings: {err_msg}")
    await rtr.api_srv.block_network_if(rtr._id, False)


async def send_to_module(app, content: str, mod_addr: int):
    """Send uploads to module."""
    rtr = app["api_srv"].routers[0]
    module = rtr.get_module(mod_addr)
    module.smg_upload, module.list_upload = seperate_upload(content)
    list_update = ModbusComputeCRC(module.list_upload) != module.get_smc_crc()
    stat_update = module.different_smg_crcs()
    if list_update | stat_update:
        await rtr.api_srv.block_network_if(rtr._id, True)
    try:
        if list_update:
            await module.hdlr.send_module_list(mod_addr)
            module.list = await module.hdlr.get_module_list(
                mod_addr
            )  # module.list_upload
            module.calc_SMC_crc(module.list)
            app["logger"].debug("Module list upload from configuration server finished")
        else:
            app["logger"].debug(
                "Module list upload from configuration server finished: Same CRC"
            )
        if stat_update:
            await module.hdlr.send_module_smg(module._id)
            await module.hdlr.get_module_status(module._id)
            app["logger"].debug(
                "Module status upload from configuration server finished"
            )
        else:
            app["logger"].debug(
                "Module status upload from configuration server finished: Same CRC"
            )
    except Exception as err_msg:
        app["logger"].error(f"Error while uploading module settings: {err_msg}")
    if list_update | stat_update:
        await rtr.api_srv.block_network_if(rtr._id, False)
    module.smg_upload = b""
    module.list_upload = b""
