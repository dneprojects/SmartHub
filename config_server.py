from os import path
from aiohttp import web
from multidict import MultiDict
from pymodbus.utilities import computeCRC as ModbusComputeCRC
from config_settings import (
    ConfigSettingsServer,
    show_router_overview,
    show_module_overview,
)
from config_automations import ConfigAutomationsServer
from config_commons import (
    adjust_settings_button,
    fill_page_template,
    get_html,
    get_module_image,
    init_side_menu,
    show_modules,
)
from module import HbtnModule
from module_hdlr import ModHdlr
import asyncio
import logging
import pathlib
from const import (
    MODULE_CODES,
    WEB_FILES_DIR,
    HOMEPAGE,
    LICENSE_PAGE,
    LICENSE_TABLE,
    CONF_HOMEPAGE,
    HUB_HOMEPAGE,
    CONF_PORT,
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
        self._ip = api_srv.sm_hub._host_ip
        self._port = CONF_PORT
        self.conf_running = False
        self.app: web.Application = []

    async def initialize(self):
        """Initialize config server."""
        self.app = web.Application()
        self.app.add_routes(routes)
        self.settings_srv = ConfigSettingsServer(self.app, self.api_srv)
        self.app.add_subapp("/settings", self.settings_srv.app)
        self.automations_srv = ConfigAutomationsServer(self.app, self.api_srv)
        self.app.add_subapp("/automations", self.automations_srv.app)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self._ip, self._port)

    async def prepare(self):
        """Second initialization after api_srv is initialized."""
        self.app["api_srv"] = self.api_srv
        self.app["is_offline"] = self.api_srv.is_offline
        init_side_menu(self.app)

    @routes.get("/")
    async def root(request: web.Request) -> web.Response:
        page = get_html(HOMEPAGE)
        if request.app["is_offline"]:
            page = page.replace(">Hub<", ">Home<")
        return web.Response(text=page, content_type="text/html", charset="utf-8")

    @routes.get("/licenses")
    async def root(request: web.Request) -> web.Response:
        return show_license_table(request.app)

    @routes.get("/exit")
    async def root(request: web.Request) -> web.Response:
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
    async def root(request: web.Request) -> web.Response:
        return show_router_overview(request.app)

    @routes.get("/hub")
    async def root(request: web.Request) -> web.Response:
        api_srv = request.app["api_srv"]
        smhub = api_srv.sm_hub
        smhub_info = smhub.info
        hub_name = smhub._host
        if api_srv.is_offline:
            pic_file, subtitle = get_module_image(b"\xc9\x00")
            html_str = get_html(CONF_HOMEPAGE)
        elif api_srv.is_addon:
            pic_file, subtitle = get_module_image(b"\xca\x00")
            html_str = get_html(HUB_HOMEPAGE).replace(
                "HubTitle", f"Smart Center '{hub_name}'"
            )
            smhub_info = smhub_info.replace(
                "type: Smart Hub", "type:  Smart Hub Add-on"
            )
        else:
            pic_file, subtitle = get_module_image(b"\xc9\x00")
            html_str = get_html(HUB_HOMEPAGE).replace(
                "HubTitle", f"Smart Hub '{hub_name}'"
            )
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

    @routes.get("/modules")
    async def root(request: web.Request) -> web.Response:
        return show_modules(request.app)

    @routes.get("/module-{mod_addr}")
    async def root(request: web.Request) -> web.Response:
        mod_addr = int(request.match_info["mod_addr"])
        return show_module_overview(request.app, mod_addr)

    @routes.get("/download")
    async def root(request: web.Request) -> web.Response:
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
    async def root(request: web.Request) -> web.Response:
        app = request.app
        data = await request.post()
        config_file = data["file"].file
        content = config_file.read()
        content_str = content.decode()
        if "SysUpload" in data.keys():
            content_parts = content_str.split("---\n")
            app.logger.info(f"Router configuration file uploaded")
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
            app.logger.info(f"Router configuration file uploaded")
            await send_to_router(app, content_str)
            return show_router_overview(app)
        else:
            mod_addr = int(data["ModUpload"])
            if data["ModUpload"] == content_str.split(";")[0]:
                await send_to_module(app, content_str, mod_addr)
                app.logger.info(
                    f"Module configuration file for module {mod_addr} uploaded"
                )
            else:
                app.logger.warning(
                    f"Module configuration file does not fit to module number {mod_addr}, upload aborted"
                )
            return show_module_overview(app, mod_addr)  # web.HTTPNoContent()

    @routes.get(path="/{key:.*}.txt")
    async def root(request: web.Request) -> web.Response:
        lic_file = open("web/" + request.path)
        lic_text = lic_file.read()
        header = lic_text.split("\n")[0].strip()
        lic_text = lic_text.replace(f"{header}\n", "").replace("\n", "<br>").strip()
        lic_file.close()
        html_str = (
            get_html(LICENSE_PAGE)
            .replace("Smart Hub", header)
            .replace("<table></table>", f"<p>{lic_text}</p>")
        )
        return web.Response(text=html_str, content_type="text/html", charset="utf-8")


# @routes.get(path="/{key:.*}")
# async def _(request):
#     app = request.app
#     warning_txt = f"Route '{request.path}' not yet implemented"
#     app.logger.warning(warning_txt)
#     mod_image, type_desc = get_module_image(app["module"]._typ)
#     page = fill_page_template(
#         f"Modul '{app['module']._name}'",
#         type_desc,
#         warning_txt,
#         app["side_menu"],
#         mod_image,
#         "",
#     )
#     page = adjust_settings_button(page, "", f"{0}")
#     return web.Response(text=page, content_type="text/html", charset="utf-8")

# @routes.post(path="/{key:.*}")
# async def _(request):
#     app = request.app
#     warning_txt = f"Route '{request.path}' not yet implemented"
#     app.logger.warning(warning_txt)
#     mod_image, type_desc = get_module_image(app["settings"]._typ)
#     page = fill_page_template(
#         f"Modul '{app['settings'].name}'",
#         type_desc,
#         warning_txt,
#         app["side_menu"],
#         mod_image,
#         "",
#     )
#     page = adjust_settings_button(page, "", f"{0}")
#     return web.Response(text=page, content_type="text/html", charset="utf-8")


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
            app.logger.debug("Module list upload from configuration server finished")
        else:
            app.logger.info(
                "Module list upload from configuration server skipped: Same CRC"
            )
        if stat_update:
            await module.hdlr.send_module_smg(module._id)
            await module.hdlr.get_module_status(module._id)
            app.logger.debug("Module status upload from configuration server finished")
        else:
            app.logger.info(
                "Module status upload from configuration server skipped: Same CRC"
            )
    except Exception as err_msg:
        app.logger.error(f"Error while uploading module settings: {err_msg}")
    if list_update | stat_update:
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
        elif line.find("<th>Vs.") > 0:
            line = line.replace("<th>", '<th data-sort-method="none">')
        elif line.find("<th>Author") > 0:
            line = line.replace("<th>", '<th data-sort-method="none">')
        elif line.find("<th>URL") > 0:
            line = line.replace("<th>", '<th data-sort-method="none">')
        elif line.find("<th>Description") > 0:
            line = line.replace("<th>", '<th data-sort-method="none">')
        elif line.find("https://") > 0:
            h_link = line.replace("<td>", "").replace("</td>", "").strip()
            short_link = h_link.replace("https://", "")
            if short_link[-1] == "/":
                short_link = short_link[:-1]
            line = line.replace(
                f"<td>{h_link}", f'<td><a href="{h_link}">{short_link}</a>'
            )
        elif line.find("http://") > 0:
            h_link = line.replace("<td>", "").replace("</td>", "").strip()
            short_link = h_link.replace("http://", "")
            if short_link[-1] == "/":
                short_link = short_link[:-1]
            line = line.replace(
                f"<td>{h_link}", f'<td><a href="{h_link}">{short_link}</a>'
            )
        line = set_license_link(line)
        table_str += line + "\n"
    return table_str


def set_license_link(line: str) -> str:
    """Check for know license and set html link to local text file."""

    f_path = "/license_files/"
    known_licenses = {
        "Apache Software License": "Apache_2_0.txt",
        "MIT License": "MIT_license.txt",
        "BSD License": "BSD_license.txt",
        "T Brown License": "Tristen_Brown.txt",
    }

    for l_key in known_licenses.keys():
        if line.find(l_key) > 0:
            line = line.replace(
                l_key, f'<a href="{f_path}{known_licenses[l_key]}">{l_key}</a>'
            )
            break
    return line
