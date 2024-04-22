from os import path
from aiohttp import web
from urllib.parse import parse_qs
from multidict import MultiDict
from config_settings import (
    ConfigSettingsServer,
    show_router_overview,
    show_module_overview,
)
import json
from config_automations import ConfigAutomationsServer
from config_commons import (
    adjust_settings_button,
    fill_page_template,
    get_html,
    get_module_image,
    init_side_menu,
    show_modules,
    show_update_router,
    show_update_modules,
    client_not_authorized,
    show_not_authorized,
)
from messages import calc_crc
from module import HbtnModule
from module_hdlr import ModHdlr
import asyncio
import logging
import pathlib
from const import (
    MODULE_CODES,
    SMHUB_INFO,
    WEB_FILES_DIR,
    HOMEPAGE,
    LICENSE_PAGE,
    LICENSE_PATH,
    LICENSE_TABLE,
    CONF_HOMEPAGE,
    HUB_HOMEPAGE,
    OWN_INGRESS_IP,
    CONF_PORT,
    INGRESS_PORT,
    MirrIdx,
)

routes = web.RouteTableDef()
root_path = pathlib.Path(__file__).parent
routes.static("/configurator_files", "./web/configurator_files")


class HubSettings:
    """Object with all module settings and changes."""

    def __init__(self, hub):
        """Fill all properties with module's values."""
        self.name = hub._name
        self.typ = hub._typ


class ConfigServer:
    """Web server for basic configuration tasks."""

    def __init__(self, api_srv):
        self.api_srv = api_srv
        if api_srv.is_addon:
            self._ip = OWN_INGRESS_IP  # api_srv.sm_hub._host_ip
            self._port = INGRESS_PORT
        else:
            self._ip = api_srv.sm_hub._host_ip
            self._port = CONF_PORT
        self.conf_running = False

    async def initialize(self):
        """Initialize config server."""

        @web.middleware
        async def ingress_middleware(request: web.Request, handler) -> web.Response:  # type: ignore

            response = await handler(request)
            if (
                request.app["api_srv"].is_addon
                and request.headers["Accept"].find("text/html") >= 0
                and "body" in response.__dir__()
                and response.status == 200
            ):
                ingress_path = request.headers["X-Ingress-Path"]
                request.app.logger.debug(f"Request path: {request.path_qs}")
                request.app.logger.debug(
                    f"Response status: {response.status} , Body type: {type(response.body)}"
                )
                if isinstance(response.body, bytes):
                    response.body = (
                        response.body.decode("utf_8")
                        .replace(
                            '<base href="/">',
                            f'<base href="{ingress_path}/">',
                        )
                        .encode("utf_8")
                    )
            return response

        self.app = web.Application(middlewares=[ingress_middleware])
        self.app.logger = logging.getLogger(__name__)
        self.settings_srv = ConfigSettingsServer(self.app, self.api_srv)
        self.app.add_subapp("/settings", self.settings_srv.app)
        self.automations_srv = ConfigAutomationsServer(self.app, self.api_srv)
        self.app.add_subapp("/automations", self.automations_srv.app)
        self.app.add_routes(routes)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self._ip, self._port)

    async def prepare(self):
        """Second initialization after api_srv is initialized."""
        self.app["api_srv"] = self.api_srv
        self.app["is_offline"] = self.api_srv.is_offline
        init_side_menu(self.app)

    @routes.get("/")
    async def get_root(request: web.Request) -> web.Response:  # type: ignore
        page = get_html(HOMEPAGE)
        if request.app["is_offline"]:
            page = page.replace(">Hub<", ">Home<")
        return web.Response(text=page, content_type="text/html", charset="utf-8")

    @routes.get("/licenses")
    async def get_licenses(request: web.Request) -> web.Response:  # type: ignore
        return show_license_table(request.app)

    @routes.get("/exit")
    async def get_exit(request: web.Request) -> web.Response:  # type: ignore
        page = get_html(HOMEPAGE)
        if request.app["is_offline"]:
            page = page.replace(">Hub<", ">Home<")
            page = page.replace(
                "Passen Sie hier die Grundeinstellungen des Systems an.", "Beendet."
            )
        api_srv = request.app["api_srv"]
        # async with api_srv.sm_hub.tg:
        api_srv.sm_hub.tg.create_task(terminate_delayed(api_srv))
        return web.Response(text=page, content_type="text/html", charset="utf-8")

    @routes.get("/router")
    async def get_router(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        return show_router_overview(request.app)

    @routes.get("/hub")
    async def get_hub(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        return show_hub_overview(request.app)

    @routes.get("/modules")
    async def get_modules(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        return show_modules(request.app)

    @routes.get("/module-{mod_addr}")
    async def get_module_addr(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        mod_addr = int(request.match_info["mod_addr"])
        return show_module_overview(request.app, mod_addr)

    @routes.get("/download")
    async def get_download(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        file_name = request.query["file"]
        file_name = file_name.split(".")[0]
        rtr = request.app["api_srv"].routers[0]
        separator = "---\n"
        if "SysDownload" in request.query.keys():
            # System backup
            file_name += ".hcf"
            settings = rtr.get_router_settings()
            file_content = settings.smr
            str_data = ""
            for byt in file_content:
                str_data += f"{byt};"
            str_data += "\n"
            str_data += rtr.pack_descriptions()
            str_data += separator
            for mod in rtr.modules:
                settings = mod.get_module_settings()
                str_data += format_hmd(settings.smg, settings.list)
                str_data += separator
        else:
            # Module download
            addr_str = request.query["ModDownload"]
            if addr_str == "ModAddress":
                mod_addr = 0
            else:
                mod_addr = int(addr_str)
            if mod_addr > 0:
                # module
                settings = rtr.get_module(mod_addr).get_module_settings()
                file_name += ".hmd"
                str_data = format_hmd(settings.smg, settings.list)
            else:
                # router
                settings = rtr.get_router_settings()
                file_content = settings.smr
                file_name += ".hrt"
                str_data = ""
                for byt in file_content:
                    str_data += f"{byt};"
                str_data += "\n"
                str_data += rtr.pack_descriptions()
        return web.Response(
            headers=MultiDict(
                {"Content-Disposition": f"Attachment; filename = {file_name}"}
            ),
            body=str_data,
        )

    @routes.post("/upload")
    async def get_upload(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        data = await request.post()
        config_file = data["file"].file  # type: ignore
        content = config_file.read()
        content_str = content.decode()
        if "SysUpload" in data.keys():
            content_parts = content_str.split("---\n")
            app.logger.info("Router configuration file uploaded")
            await send_to_router(app, content_parts[0])
            for mod_addr in app["api_srv"].routers[0].mod_addrs:
                for cont_part in content_parts[1:]:
                    if mod_addr == int(cont_part.split(";")[0]):
                        break
                await send_to_module(app, cont_part, mod_addr)
                app.logger.info(
                    f"Module configuration file for module {mod_addr} uploaded"
                )
            init_side_menu(app)
            return show_modules(app)
        elif data["ModUpload"] == "ModAddress":
            # router upload
            app.logger.info("Router configuration file uploaded")  # noqa: F541
            await send_to_router(app, content_str)
            init_side_menu(app)
            return show_router_overview(app)
        else:
            mod_addr = int(str(data["ModUpload"]))
            if data["ModUpload"] == content_str.split(";")[0]:
                await send_to_module(app, content_str, mod_addr)
                app.logger.info(
                    f"Module configuration file for module {mod_addr} uploaded"
                )
            else:
                app.logger.warning(
                    f"Module configuration file does not fit to module number {mod_addr}, upload aborted"
                )
            init_side_menu(app)
            return show_module_overview(app, mod_addr)  # web.HTTPNoContent()

    @routes.post("/upd_upload")
    async def get_upd_upload(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        api_srv = app["api_srv"]
        rtr = api_srv.routers[0]
        data = await request.post()
        # fw_filename = data["file"].filename
        rtr.fw_upload = data["file"].file.read()  # type: ignore
        upd_type = str(data["SysUpload"])
        if upd_type == "rtr":
            fw_vers = rtr.fw_upload[-27:-5].decode()
            app.logger.info(f"Firmware file for router {rtr._name} uploaded")
            return show_update_router(rtr, fw_vers)
        elif upd_type == "mod":
            mod_type = rtr.fw_upload[:2]
            mod_type_str = MODULE_CODES[mod_type.decode()]
            fw_vers = rtr.fw_upload[-27:-5].decode().strip()
            app.logger.info(
                f"Firmware file v. {fw_vers} for '{MODULE_CODES[mod_type.decode()]}' modules uploaded"
            )
            mod_list = rtr.get_module_list()
            upd_list = []
            for mod in mod_list:
                if mod.typ == mod_type:
                    upd_list.append(mod)
            return show_update_modules(upd_list, fw_vers, mod_type_str)
        else:
            mod_type = rtr.fw_upload[:2]
            mod_type_str = MODULE_CODES[mod_type.decode()]
            fw_vers = rtr.fw_upload[-27:-5].decode().strip()
            mod_addr = int(upd_type)
            module = rtr.get_module(mod_addr)
            if module is None:
                app.logger.error(f"Could not find module {mod_addr}")
                return show_hub_overview(app)
            elif module._typ == mod_type:
                app.logger.info(f"Firmware file for module {module._name} uploaded")
                return show_update_modules([module], fw_vers, mod_type_str)
            else:
                app.logger.error(
                    f"Firmware file for {MODULE_CODES[mod_type.decode()]} uploaded, not compatible with module {module._name}"
                )
                return show_hub_overview(app)

    @routes.post("/update_router")
    async def get_update_router(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        api_srv = app["api_srv"]
        rtr = api_srv.routers[0]
        resp = await request.text()
        form_data = parse_qs(resp)
        if form_data["UpdButton"][0] == "cancel":
            return show_hub_overview(app)
        rtr.hdlr.upd_stat_dict = {"modules": [0], "upload": 100}
        rtr.hdlr.upd_stat_dict["mod_0"] = {
            "progress": 0,
            "errors": 0,
            "success": "OK",
        }
        await rtr.hdlr.upload_router_firmware(None, rtr.hdlr.log_rtr_fw_update_protocol)
        return show_hub_overview(app)

    @routes.post("/update_modules")
    async def get_update_modules(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        api_srv = app["api_srv"]
        rtr = api_srv.routers[0]
        resp = await request.text()
        form_data = parse_qs(resp)
        if form_data["UpdButton"][0] == "cancel":
            return show_hub_overview(app)
        if len(form_data.keys()) == 1:
            # nothing selected
            return show_hub_overview(app)

        mod_type = rtr.fw_upload[:2]
        mod_list = []
        for checked in list(form_data.keys())[:-1]:
            mod_list.append(int(form_data[checked][0]))
        rtr.hdlr.upd_stat_dict = {"modules": mod_list, "upload": 0}
        for md in mod_list:
            rtr.hdlr.upd_stat_dict[f"mod_{md}"] = {
                "progress": 0,
                "errors": 0,
                "success": "OK",
            }
        app.logger.info(f"Update of Modules {mod_list}")
        await api_srv.block_network_if(rtr._id, True)
        if await rtr.hdlr.upload_module_firmware(
            mod_type, rtr.hdlr.log_mod_fw_upload_protocol
        ):
            app.logger.info("Firmware uploaded to router successfully")
            await rtr.hdlr.flash_module_firmware(
                mod_list, rtr.hdlr.log_mod_fw_update_protocol
            )
            for mod in mod_list:
                await rtr.get_module(mod).initialize()
        else:
            app.logger.info("Firmware upload to router failed, update terminated")
        await api_srv.block_network_if(rtr._id, False)
        return show_hub_overview(app)

    @routes.get("/update_status")
    async def get_update_status(request: web.Request) -> web.Response:  # type: ignore
        app = request.app
        stat = app["api_srv"].routers[0].hdlr.upd_stat_dict
        return web.Response(
            text=json.dumps(stat), content_type="text/plain", charset="utf-8"
        )

    @routes.get(path="/{key:.*}.txt")
    async def get_license_text(request: web.Request) -> web.Response:  # type: ignore
        return show_license_text(request)


@routes.get(path="/{key:.*}")
async def _(request):
    app = request.app
    warning_txt = f"Route '{request.path}' not yet implemented"
    app.logger.warning(warning_txt)
    mod_image, type_desc = get_module_image(app["module"]._typ)
    page = fill_page_template(
        f"Modul '{app['module']._name}'",
        type_desc,
        warning_txt,
        app["side_menu"],
        mod_image,
        "",
    )
    page = adjust_settings_button(page, "", f"{0}")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


@routes.post(path="/{key:.*}")
async def _(request):
    app = request.app
    warning_txt = f"Route '{request.path}' not yet implemented"
    app.logger.warning(warning_txt)
    mod_image, type_desc = get_module_image(app["settings"]._typ)
    page = fill_page_template(
        f"Modul '{app['settings'].name}'",
        type_desc,
        warning_txt,
        app["side_menu"],
        mod_image,
        "",
    )
    page = adjust_settings_button(page, "", f"{0}")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_hub_overview(app) -> web.Response:
    """Show hub overview page."""
    api_srv = app["api_srv"]
    smhub = api_srv.sm_hub
    smhub_info = smhub.get_info()
    hub_name = smhub._host
    if api_srv.is_offline:
        pic_file, subtitle = get_module_image(b"\xc9\x00")
        html_str = get_html(CONF_HOMEPAGE).replace(
            "Version: x.y.z", f"Version: {SMHUB_INFO.SW_VERSION}"
        )
    elif api_srv.is_addon:
        pic_file, subtitle = get_module_image(b"\xca\x00")
        html_str = get_html(HUB_HOMEPAGE).replace(
            "HubTitle", f"Smart Center '{hub_name}'"
        )
        smhub_info = smhub_info.replace("type: Smart Hub", "type:  Smart Hub Add-on")
    else:
        pic_file, subtitle = get_module_image(b"\xc9\x00")
        html_str = get_html(HUB_HOMEPAGE).replace("HubTitle", f"Smart Hub '{hub_name}'")
    html_str = html_str.replace("Overview", subtitle)
    html_str = html_str.replace("smart-Ip.jpg", pic_file)
    html_str = html_str.replace(
        "ContentText",
        "<h3>Eigenschaften</h3>\n<p>"
        + smhub_info.replace("  ", "&nbsp;&nbsp;&nbsp;&nbsp;")
        .replace(": ", ":&nbsp;&nbsp;")
        .replace("\n", "</p>\n<p>")
        + "</p>",
    )
    return web.Response(text=html_str, content_type="text/html", charset="utf-8")


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


def format_hmd(status, list: bytes) -> str:
    """Generate single module data file."""
    smg_str = format_smg(status)
    smc_str = format_smc(list)
    return smg_str + smc_str


def seperate_upload(upload_str: str) -> tuple[bytes, bytes]:
    """Seperate smg and list from data, remove ';' and lf, correct counts, and convert to bytes"""
    lines = upload_str.split("\n")
    l_l = len(lines)
    for l_i in range(l_l):
        # count backwards to keep line count after deletion
        if lines[l_l - l_i - 1].strip() == "":
            del lines[l_l - l_i - 1]
    smg_bytes = b""
    for byt in lines[0].split(";"):
        if len(byt) > 0:
            smg_bytes += int.to_bytes(int(byt))
    no_list_lines = len(lines) - 2
    no_list_chars = 0
    smc_bytes = b""
    for line in lines[1:]:
        for byt in line.split(";"):
            if len(byt) > 0:
                smc_bytes += int.to_bytes(int(byt))
                no_list_chars += 1
    if len(lines) > 1:
        smc_bytes = (
            chr(no_list_lines & 0xFF)
            + chr(no_list_lines >> 8)
            + chr(no_list_chars & 0xFF)
            + chr(no_list_chars >> 8)
        ).encode("iso8859-1") + smc_bytes[4:]
    return smg_bytes, smc_bytes


async def send_to_router(app, content: str):
    """Send uploads to module."""
    rtr = app["api_srv"].routers[0]
    await rtr.api_srv.block_network_if(rtr._id, True)
    try:
        lines = content.split("\n")
        buf = b""
        for byt in lines[0].split(";")[:-1]:
            buf += int.to_bytes(int(byt))
        rtr.smr_upload = buf
        if app["api_srv"].is_offline:
            rtr.hdlr.set_rt_full_status()
        else:
            await rtr.hdlr.send_rt_full_status()
        rtr.smr_upload = b""
        desc_lines = lines[1:]
        if len(desc_lines) > 0:
            rtr.unpack_descriptions(desc_lines)
    except Exception as err_msg:
        app.logger.error(f"Error while uploading router settings: {err_msg}")
    await rtr.api_srv.block_network_if(rtr._id, False)


async def send_to_module(app, content: str, mod_addr: int):
    """Send uploads to module."""
    rtr = app["api_srv"].routers[0]
    if app["api_srv"].is_offline:
        rtr.modules.append(
            HbtnModule(mod_addr, rtr._id, ModHdlr(mod_addr, rtr.api_srv), rtr.api_srv)
        )
        module = rtr.modules[-1]
        module.smg_upload, module.list = seperate_upload(content)
        module.calc_SMG_crc(module.smg_upload)
        module.calc_SMC_crc(module.list)
        module._name = module.smg_upload[52 : 52 + 32].decode("iso8859-1").strip()
        module._typ = module.smg_upload[1:3]
        module._type = MODULE_CODES[module._typ.decode("iso8859-1")]
        module.status = b"\0" * MirrIdx.END
        module.build_status(module.smg_upload)
        module.io_properties, module.io_prop_keys = module.get_io_properties()
        return

    module = rtr.get_module(mod_addr)
    module.smg_upload, module.list_upload = seperate_upload(content)
    list_update = calc_crc(module.list_upload) != module.get_smc_crc()
    stat_update = module.different_smg_crcs()
    if list_update or stat_update:
        await rtr.api_srv.block_network_if(rtr._id, True)
    try:
        if list_update:
            await module.hdlr.send_module_list(mod_addr)
            module.list = await module.hdlr.get_module_list(
                mod_addr
            )  # module.list_upload
            module.calc_SMC_crc(module.list)
            app.logger.info("Module list upload from configuration server finished")
        else:
            app.logger.info(
                "Module list upload from configuration server skipped: Same CRC"
            )
        if stat_update:
            await module.hdlr.send_module_smg(module._id)
            await module.hdlr.get_module_status(module._id)
            app.logger.info("Module status upload from configuration server finished")
        else:
            app.logger.info(
                "Module status upload from configuration server skipped: Same CRC"
            )
    except Exception as err_msg:
        app.logger.error(f"Error while uploading module settings: {err_msg}")
    if list_update or stat_update:
        await rtr.api_srv.block_network_if(rtr._id, False)
    module.smg_upload = b""
    module.list_upload = b""


async def terminate_delayed(api_srv):
    """suspend for a time limit in seconds"""
    await asyncio.sleep(0.5)
    # execute the other coroutine
    await api_srv.shutdown(None, False)


def show_license_table(app):
    """Return html page with license table."""
    page = get_html(LICENSE_PAGE)
    table = get_html(LICENSE_TABLE).split("\n")
    table_str = build_lic_table(table, "hub")
    table_end = "  </tbody>\n</table>\n"
    tablesort_str = (
        "    <tr>\n"
        + "      <td>tablesort</td>\n"
        + "      <td>5.3.0</td>\n"
        + set_license_link("      <td>T Brown License</td>\n")
        + "      <td>Tristen Brown</td>\n"
        + '      <td><a href="https://github.com/tristen/tablesort">github.com/tristen/tablesort</a></td>\n'
        + "      <td>A small & simple sorting component for tables written in JavaScript</td>\n"
        + "    </tr>\n"
    )
    table_str = table_str.replace(table_end, tablesort_str + table_end)
    if path.isfile(WEB_FILES_DIR + "license_table_haint.html"):
        table = get_html("license_table_haint.html").split("\n")
        new_table = "<br><br>\n<h3>Home Assistant / Habitron Integration</h3>"
        table_str += new_table + build_lic_table(table, "hai")
    if app["is_offline"]:
        page = page.replace("Smart Hub", "Smart Configurator")
    elif app["api_srv"].is_addon:
        page = page.replace("Smart Hub", "Smart Center")
    page = page.replace("<table></table>", table_str)
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def build_lic_table(table, spec) -> str:
    """Build html table string from table line list."""

    table_str = ""
    for line in table:
        if line.find("<table>") >= 0:
            line = line.replace("<table>", f'<table id="lic-{spec}-table">')
        elif line.find("<th>Version") > 0:
            line = line.replace("<th>Version", '<th data-sort-method="none">V.')
        elif line.find("<th>Author") > 0:
            line = line.replace("<th>", '<th data-sort-method="none">')
        elif line.find("<th>URL") > 0:
            line = line.replace("<th>", '<th data-sort-method="none">')
        elif line.find("<th>Description") > 0:
            line = line.replace("<th>", '<th data-sort-method="none">')
        elif line.find("Artistic License") > 0:
            line = line[: line.find("<td>")] + "<td>Artistic License</td>"
        line = line.replace(">Apache Software License<", ">Apache License 2.0<")
        line = line.replace(">Apache-2.0<", ">Apache License 2.0<")
        line = line.replace(">MIT<", ">MIT License<")
        line = line.replace("Python Software Foundation License", "PSF License")
        line = set_license_link(line)
        table_str += line + "\n"
    return html_text_to_link(table_str, True)


def set_license_link(line: str) -> str:
    """Check for know license and set html link to local text file."""

    known_licenses = {
        "Apache License 2.0": "Apache_2_0.txt",
        "Artistic License": "Artistic.txt",
        "BSD License": "BSD_license.txt",
        "MIT License": "MIT_license.txt",
        "PSF License": "PSF_license.txt",
        "T Brown License": "Tristen_Brown.txt",
    }

    for l_key in known_licenses.keys():
        if line.find(l_key) > 0:
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
