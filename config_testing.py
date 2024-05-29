from aiohttp import web
from asyncio import sleep
from config_commons import (
    get_module_image,
    get_html,
    client_not_authorized,
    show_not_authorized,
    fill_page_template,
)
from config_settings import activate_side_menu
from const import CONF_PORT, MirrIdx, HA_EVENTS
import json

routes = web.RouteTableDef()


class ConfigTestingServer:
    """Web server for testing tasks."""

    def __init__(self, parent, api_srv):
        self.api_srv = api_srv
        self._ip = api_srv.sm_hub._host_ip
        self._port = CONF_PORT
        self.parent = parent
        self.app = web.Application()
        self.app.add_routes(routes)
        self.app["parent"] = self.parent

    @routes.get("/modules")
    async def test_modules(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        return show_modules_overview(main_app)

    @routes.get("/start-{mod_addr}")
    async def start_test(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        mod_addr = int(request.match_info["mod_addr"])
        main_app["mod_addr"] = mod_addr
        await api_srv.set_testing_mode(True)
        return await show_module_testpage(main_app, mod_addr, True)

    @routes.get("/events")
    async def get_events(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        mod_addr = main_app["mod_addr"]
        events_dict: dict[str, list[list[int]]] = {}
        # get events
        events_buf = main_app["api_srv"].evnt_srv.get_events_buffer()
        for evnt in events_buf:
            if evnt[0] == mod_addr:
                dict_str = HA_EVENTS.EVENT_DICT[evnt[1]].replace(" ", "_")
                if dict_str in events_dict.keys():
                    events_dict[dict_str].append([evnt[2], evnt[3]])
                else:
                    events_dict[dict_str] = [[evnt[2], evnt[3]]]
        return web.Response(
            text=json.dumps(events_dict), content_type="text/plain", charset="utf-8"
        )

    @routes.get("/stop")
    async def stop_test(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        await api_srv.set_testing_mode(False)
        return show_modules_overview(main_app)

    @routes.get("/set_output")
    async def set_output(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        args = request.query_string.split("=")
        out_args = args[1].split("-")
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        mod_addr = main_app["mod_addr"]
        rtr = api_srv.routers[0]
        mod = rtr.get_module(mod_addr)
        await mod.hdlr.set_output(int(out_args[0]), int(out_args[1]))
        return await show_module_testpage(main_app, mod_addr, False)


def show_modules_overview(app) -> web.Response:
    """Prepare modules page."""
    api_srv = app["api_srv"]
    rtr = api_srv.routers[0]
    side_menu = activate_side_menu(app["side_menu"], ">Einrichten<", app["is_offline"])
    side_menu = activate_side_menu(side_menu, ">Module testen<", app["is_offline"])
    page = get_html("modules.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>Module", "<h1>Module testen")
    page = page.replace("Übersicht", "Mögliche Module")
    images = ""
    for mod in rtr.modules:
        m_type = mod._typ
        pic_file, title = get_module_image(m_type)
        images += f'<div class="figd_grid" name="test_mod_img" id=test-{mod._id}><a href="test/start-{mod._id}"><div class="fig_grid"><img src="configurator_files/{pic_file}" alt="{mod._name}"><p class="mod_subtext">{mod._name}</p></div></a></div>\n'
    page = page.replace("<!-- ImageGrid -->", images)
    page = page.replace("const mod_addrs = [];", f"const mod_addrs = {rtr.mod_addrs};")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


async def show_module_testpage(main_app, mod_addr, update: bool) -> web.Response:
    """Prepare overview page of module."""
    api_srv = main_app["api_srv"]
    module = api_srv.routers[0].get_module(mod_addr)
    mod_image, type_desc = get_module_image(module._typ)
    main_app["module"] = module
    mod_description = ""
    def_filename = f"module_{mod_addr}.hmd"
    page = fill_page_template(
        f"Modul '{module._name}'",
        "Modul Testseite",
        "Ein- und Ausgangsänderungen, sowie Events kontrollieren und Ausgänge schalten",
        mod_description,
        "",
        mod_image,
        def_filename,
    )
    page = page.replace("<!-- SetupContentStart >", "<!-- SetupContentStart -->")
    # reconfigure existing buttons
    page = page.replace(
        ">Modul entfernen<", 'style="visibility: hidden;">Modul entfernen<'
    )
    page = page.replace(">Modul testen<", 'style="visibility: hidden;">Modul testen<')
    page = page.replace(">Einstellungen<", 'style="visibility: hidden;">Einstellungen<')
    page = page.replace(
        ">Konfigurationsdatei<",
        'form="test_form" value="ModAddress">Modultest beenden<',
    )
    page = page.replace('action="test/start"', 'action="test/stop"')
    page = page.replace("ModAddress", f"{mod_addr}")
    page = page.replace(
        '<form action="automations/list" id="atm_form">',
        '<form action="test/stop" id="test_form">',
    )
    page = page.replace('id="files_button"', 'id="finish_button"')
    page = page.replace("left: 560px;", "left: 200px;")
    page = page.replace("config.js", "update_testing.js")
    tbl_str = await build_status_table(main_app, mod_addr, update)
    page = page.replace("<p></p>", tbl_str)
    return web.Response(text=page, content_type="text/html")


async def build_status_table(app, mod_addr: int, update: bool) -> str:
    """Get module status and build table."""

    table_str = ""
    tr_line = '        <tr id="inst-tr">\n'
    tre_line = "        </tr>\n"
    td_line = "            <td></td>\n"
    thead_lines = (
        '<form action="test/execute" id="table-form">\n'
        '<table id="<tbl_id>">\n'
        + "    <thead>\n"
        + '        <tr id="inst-th">\n'
        + '            <th style="width: 10%;">Nr.</th>\n'
        + "            <th>Name</th>\n"
        + '            <th style="width: 15%;">Typ</th>\n'
        + '            <th style="width: 10%;">Aktiv</th>\n'
        + "        </tr>\n"
        + "    </thead>\n"
        + "    <tbody>\n"
    )
    tbl_end_line = "  </tbody>\n</table>\n"
    form_end_line = "</form>\n"

    api_srv = app["api_srv"]
    rtr = api_srv.routers[0]
    mod = rtr.get_module(mod_addr)
    if update:
        await mod.hdlr.get_module_status(mod_addr)
        # hot fix for comm errors
        await sleep(0.1)
        await api_srv.set_operate_mode()
    settings = mod.get_module_settings()
    if settings.properties["inputs"] > 0:
        table_str += "<h3>Eingänge</h3>"
        inp_state = int.from_bytes(
            mod.status[MirrIdx.INP_1_8 : MirrIdx.INP_1_8 + 3], "little"
        )
        table_str += thead_lines.replace("<tbl_id>", "mod-inputs-table")
        for inp in settings.buttons:
            inp_nmbr = inp.nmbr
            table_str += tr_line
            table_str += td_line.replace("><", f">{inp_nmbr}<")
            table_str += td_line.replace(
                "><",
                f">{inp.name}<",
            )
            table_str += td_line.replace("><", ">Modul<")
            if inp_state & 1 << (inp_nmbr - 1):
                sel_chkd = "checked"
            else:
                sel_chkd = ""
            table_str += td_line.replace(
                "><",
                ">Taste<",
            )
            table_str += tre_line
        for inp in settings.inputs:
            inp_nmbr = inp.nmbr + len(settings.buttons)
            table_str += tr_line
            table_str += td_line.replace("><", f">{inp_nmbr}<")
            table_str += td_line.replace(
                "><",
                f">{inp.name}<",
            )
            if inp.nmbr <= settings.properties["inputs_230V"]:
                table_str += td_line.replace("><", ">230V<")
            else:
                table_str += td_line.replace("><", ">24V<")
            if inp_state & 1 << (inp_nmbr - 1):
                sel_chkd = "checked"
            else:
                sel_chkd = ""
            if inp.type == 2:
                table_str += td_line.replace(
                    "><",
                    f'><input type="checkbox" class="inp_chk" name="inp-{inp_nmbr}" {sel_chkd}><',
                )
            else:
                table_str += td_line.replace(
                    "><",
                    ">Taste<",
                )
            table_str += tre_line
        table_str += tbl_end_line
    if settings.properties["outputs"] > 0:
        table_str += "<h3>Ausgänge</h3>"
        out_state = int.from_bytes(
            mod.status[MirrIdx.OUT_1_8 : MirrIdx.OUT_1_8 + 3], "little"
        )
        table_str += thead_lines.replace("<tbl_id>", "mod-outputs-table")
        for outp in settings.outputs:
            table_str += tr_line
            table_str += td_line.replace("><", f">{outp.nmbr}<")
            table_str += td_line.replace(
                "><",
                f">{outp.name}<",
            )
            if outp.nmbr <= settings.properties["outputs_230V"]:
                table_str += td_line.replace("><", ">230V<")
            elif (
                outp.nmbr
                <= settings.properties["outputs_230V"]
                + settings.properties["outputs_dimm"]
            ):
                table_str += td_line.replace("><", ">Dimmer<")
            elif (
                outp.nmbr
                <= settings.properties["outputs_230V"]
                + settings.properties["outputs_dimm"]
                + settings.properties["outputs_24V"]
            ):
                table_str += td_line.replace("><", ">24V<")
            else:
                table_str += td_line.replace("><", ">Relais<")
            if out_state & 1 << (outp.nmbr - 1):
                sel_chkd = "checked"
            else:
                sel_chkd = ""
            table_str += td_line.replace(
                "><",
                f'><input type="checkbox" class="out_chk" name="out-{outp.nmbr}" {sel_chkd}><',
            )
            table_str += tre_line
        table_str += tbl_end_line
    table_str += "<h3>Events</h3>"
    table_str += (
        thead_lines.replace("<tbl_id>", "mod-events-table")
        .replace("Nr.", "Zeit")
        .replace("Typ", "Wert")
        .replace("Aktiv", "")
    )
    for line in range(5):
        table_str += tr_line
        table_str += td_line.replace("><", ">&nbsp;<")
        table_str += td_line.replace("><", ">&nbsp;<")
        table_str += td_line.replace("><", ">&nbsp;<")
        table_str += td_line.replace("><", ">&nbsp;<")
        table_str += tre_line
    table_str += tbl_end_line
    table_str += form_end_line

    return table_str
