from aiohttp import web
from urllib.parse import parse_qs
from config_settings import get_module_properties
from configuration import ModuleSettings
from config_commons import (
    get_module_image,
    show_modules,
    indent,
    get_html,
    client_not_authorized,
    show_not_authorized,
    activate_side_menu,
    fill_page_template,
)
from const import (
    WEB_FILES_DIR,
    AUTOMATIONS_TEMPLATE_FILE,
    AUTOMATIONEDIT_TEMPLATE_FILE,
    MODULE_CODES,
    CONF_PORT,
    MODULE_TYPES,
)
from module import HbtnModule
from module_hdlr import ModHdlr

routes = web.RouteTableDef()


class ConfigSetupServer:
    """Web server for setup tasks."""

    def __init__(self, parent, api_srv):
        self.api_srv = api_srv
        self._ip = api_srv.sm_hub._host_ip
        self._port = CONF_PORT
        self.parent = parent
        self.app = web.Application()
        self.app.add_routes(routes)
        self.app["parent"] = self.parent

    @routes.get("/")
    async def setup_page(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        return show_setup_page(main_app)

    @routes.get("/add")
    async def type_list(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        return show_module_types(main_app)

    @routes.get("/add_type-{mod_cat}-{mod_subtype}")
    async def add_type(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        if len(rtr.modules) == 0:
            rtr._name = "NewRouter"
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        mod_type = int(request.match_info["mod_cat"])
        mod_subtype = int(request.match_info["mod_subtype"])
        mod_typ = (chr(mod_type) + chr(mod_subtype)).encode("iso8859-1")
        # popup für Kanal und Adresse
        rtr_chan = int(request.query["chan_number"])
        mod_addr = int(request.query["mod_addr"])
        mod_name = f"NewModule_{mod_addr}"
        rtr.new_module(rtr_chan, mod_addr, mod_typ, mod_name)
        return show_module_types(main_app)

    @routes.get("/remove")
    async def mod_remove(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        mod_addr = int(request.query["RemoveModule"])
        rtr.rem_module(mod_addr)
        return show_modules(main_app)


def show_setup_page(app) -> web.Response:
    """Prepare modules page."""
    side_menu = activate_side_menu(app["side_menu"], ">Einrichten<", app["is_offline"])
    page = get_html("hub.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>HubTitle", "<h1>Habitron-Geräte einrichten")
    page = page.replace("Overview", "Installationsbereich")
    page = page.replace("ContentText", "Wählen Sie aus: Modul anlegen")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_module_types(app) -> web.Response:
    """Prepare modules page."""
    api_srv = app["api_srv"]
    rtr = api_srv.routers[0]
    side_menu = activate_side_menu(app["side_menu"], ">Einrichten<", app["is_offline"])
    side_menu = activate_side_menu(side_menu, ">Modul anlegen<", app["is_offline"])
    page = get_html("modules.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>Module", "<h1>Modul anlegen")
    page = page.replace("Übersicht", "Mögliche Modultypen")
    page = page.replace(
        "Wählen Sie ein Modul aus",
        "Zum Neuanlegen eines Moduls wählen Sie den Modultyp aus",
    )
    images = ""
    for m_item in MODULE_TYPES.items():
        m_type = m_item[0]
        type_str = str(ord(m_type[0])) + "-" + str(ord(m_type[1]))
        pic_file, title = get_module_image(m_type.encode())
        images += f'<div class="figd_grid" name="add_type_img" id=add-type-{type_str}><div class="fig_grid"><img src="configurator_files/{pic_file}" alt="{MODULE_TYPES[m_type]}"><p class="mod_subtext">{MODULE_TYPES[m_type]}</p></div></a></div>\n'
    page = page.replace("<!-- ImageGrid -->", images)
    page = page.replace("const mod_addrs = [];", f"const mod_addrs = {rtr.mod_addrs};")
    return web.Response(text=page, content_type="text/html", charset="utf-8")
