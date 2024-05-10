from aiohttp import web
from urllib.parse import parse_qs
from config_settings import get_module_properties
from configuration import ModuleSettings
from config_commons import (
    get_module_image,
    disable_button,
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
    CONF_PORT,
    MODULE_TYPES,
)

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
    async def get_list(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        return show_modules(main_app)


def show_modules(app) -> web.Response:
    """Prepare modules page."""
    side_menu = activate_side_menu(app["side_menu"], ">Setup<", app["is_offline"])
    page = get_html("modules.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>Module", "<h1>Module einrichten")
    page = page.replace("Übersicht", "Mögliche Modultypen")
    page = page.replace(
        "Wählen Sie ein Modul aus", "Wählen Sie einen Modultyp zum Anlegen aus"
    )
    images = ""
    for m_item in MODULE_TYPES.items():
        m_type = m_item[0]
        pic_file, title = get_module_image(m_type.encode())
        images += f'<div class="figd_grid"><a href="module-{m_type}"><div class="fig_grid"><img src="configurator_files/{pic_file}" alt="{MODULE_TYPES[m_type]}"><p class="mod_subtext">{MODULE_TYPES[m_type]}</p></div></a></div>\n'
    page = page.replace("<!-- ImageGrid -->", images)
    return web.Response(text=page, content_type="text/html", charset="utf-8")
