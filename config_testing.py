from aiohttp import web
from urllib.parse import parse_qs
from automation import AutomationDefinition
from automtn_trigger import AutomationTrigger
from configuration import ModuleSettings
from config_commons import (
    get_module_image,
    disable_button,
    indent,
    client_not_authorized,
    show_not_authorized,
)
from config_settings import show_module_overview
from const import (
    WEB_FILES_DIR,
    AUTOMATIONS_TEMPLATE_FILE,
    AUTOMATIONEDIT_TEMPLATE_FILE,
    CONF_PORT,
)

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

    @routes.get("/list")
    async def get_list(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        args = request.query_string.split("=")
        mod_addr = int(args[1])
        main_app = request.app["parent"]
        main_app["step"] = 0
        return build_show_automations(main_app, mod_addr, 0)

    @routes.post("/automtns")
    async def post_automtns(request: web.Request) -> web.Response:  # type: ignore
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        resp = await request.text()
        form_data = parse_qs(resp)
        main_app = request.app["parent"]
        if "ModSettings" in form_data.keys():
            args = form_data["ModSettings"][0].split("-")
            action = args[0]
            mod_addr = int(args[1])
            step = int(args[2])
            match action:
                case "cancel":
                    return show_module_overview(main_app, mod_addr)
                case "save":
                    settings = main_app["settings"]
                    module = settings.module
                    await main_app["api_srv"].block_network_if(module.rt_id, True)
                    try:
                        await module.set_automations(settings)
                    except Exception as err_msg:
                        main_app.logger.error(
                            f"Error while saving module automations: {err_msg}"
                        )
                    await main_app["api_srv"].block_network_if(module.rt_id, False)
                    return show_module_overview(main_app, mod_addr)
                case "next":
                    step += 1
                case "back":
                    step -= 1
            main_app["step"] = step
            return show_automations(main_app, step)
        else:
            settings = main_app["settings"]
            if "EditAutomtn" in form_data.keys():
                atm_mode = form_data["EditAutomtn"][0]
            elif "NewAutomtn" in form_data.keys():
                atm_mode = form_data["NewAutomtn"][0]
            elif "src_module" in form_data.keys():
                atm_mode = "new"
            else:
                atm_mode = "delete"
            if "atmn_tbl" in form_data.keys():
                automtn_selctn = int(form_data["atmn_tbl"][0])
            elif "sel_automtn" in form_data.keys():
                automtn_selctn = int(form_data["sel_automtn"][0].split("-")[1])
            else:
                automtn_selctn = None
            main_app["automations_def"].selected = automtn_selctn
            main_app["atm_mode"] = atm_mode

            if atm_mode == "delete":
                if automtn_selctn is not None:
                    if main_app["step"] == 0:
                        del main_app["automations_def"].local[automtn_selctn]
                    else:
                        l_ext = len(main_app["automations_def"].external)
                        if automtn_selctn < l_ext:
                            del main_app["automations_def"].external[automtn_selctn]
                        else:
                            del main_app["automations_def"].forward[
                                automtn_selctn - l_ext
                            ]
                return show_automations(main_app, main_app["step"])

            if automtn_selctn is None:
                if atm_mode == "change":
                    return show_automations(main_app, main_app["step"])
                else:
                    sel_atmtn = AutomationDefinition(
                        None, main_app["automations_def"].autmn_dict, settings
                    )
            elif main_app["step"] == 0:
                if len(main_app["automations_def"].local) > 0:
                    sel_atmtn = main_app["automations_def"].local[automtn_selctn]
                    if atm_mode == "new":
                        sel_atmtn = sel_atmtn.make_automtn_copy()
            else:
                if (
                    (main_app["step"] == 1)
                    and (len(main_app["automations_def"].external) == 0)
                ) or (
                    (main_app["step"] == 2)
                    and (len(main_app["automations_def"].forward) == 0)
                ):
                    sel_atmtn = AutomationDefinition(
                        None, main_app["automations_def"].autmn_dict, settings
                    )
                else:
                    l_ext = len(main_app["automations_def"].external)
                    if automtn_selctn < l_ext:
                        sel_atmtn = main_app["automations_def"].external[automtn_selctn]
                    else:
                        sel_atmtn = main_app["automations_def"].forward[
                            automtn_selctn - l_ext
                        ]
                if "src_module" in form_data.keys():
                    src_mod = int(form_data["src_module"][0].split("-")[1])
                    if sel_atmtn.src_rt == 0:
                        # first automation
                        sel_atmtn.src_rt = 1
                else:
                    src_mod = sel_atmtn.src_mod
                sel_atmtn = sel_atmtn.make_automtn_copy()
                if atm_mode == "new":
                    src_rt = sel_atmtn.src_rt
                    rtr = main_app["api_srv"].routers[src_rt - 1]
                    sel_atmtn = prepare_src_mod_trigger(sel_atmtn, rtr, src_mod)

            main_app["base_automation"] = sel_atmtn
            return show_edit_automation(
                main_app,
                sel_atmtn,
                automtn_selctn,
                atm_mode,
                main_app["step"],
            )

    @routes.post("/automtn_def")
    async def post_automtn_def(request: web.Request) -> web.Response:  # type: ignore
        resp = await request.text()
        form_data = parse_qs(resp)
        main_app = request.app["parent"]
        if "cancel_atm_edit" in form_data.keys():
            # Cancel
            return show_automations(main_app, main_app["step"])
        elif "ok_result" in form_data.keys():
            if form_data["ok_result"][0] == "ok":
                main_app["automations_def"].save_changed_automation(
                    main_app, form_data, main_app["step"]
                )
                return show_automations(main_app, main_app["step"])
            else:
                return web.HTTPNoContent()
        elif "trigger_sel" in form_data.keys():
            return web.HTTPNoContent()
        elif "action_sel" in form_data.keys():
            return web.HTTPNoContent()
        else:
            return web.HTTPNoContent()


def build_show_automations(main_app, mod_addr, step) -> web.Response:
    """Prepare automations page of module."""
    settings = main_app["api_srv"].routers[0].get_module(mod_addr).get_module_settings()
    main_app["automations_def"] = settings.automtns_def
    main_app["settings"] = settings
    return show_automations(main_app, step)


def show_automations(main_app, step) -> web.Response:
    """Prepare automations page of module."""
    title_str = f"Modul '{main_app['settings'].name}'"
    if step == 0:
        subtitle = "Lokale Automatisierungen"
    elif step == 1:
        subtitle = "Externe Automatisierungen"
    else:
        subtitle = "Weiterleitungsautomatisierungen"
    page = fill_automations_template(main_app, title_str, subtitle, step)
    return web.Response(text=page, content_type="text/html")


def show_edit_automation(main_app, sel_automtn, sel, mode, step) -> web.Response:
    """Prepare automations page of module."""
    title_str = f"Modul '{main_app['settings'].name}'"
    if mode == "new":
        subtitle = "Neue Automatisierung anlegen"
    else:
        subtitle = "Automatisierung ändern"
    with open(
        WEB_FILES_DIR + AUTOMATIONEDIT_TEMPLATE_FILE, mode="r", encoding="utf-8"
    ) as tplf_id:
        page = tplf_id.read()
    mod_image, mod_type = get_module_image(main_app["settings"].typ)
    page = (
        page.replace("ContentTitle", title_str)
        .replace("ContentSubtitle", subtitle)
        .replace("controller.jpg", mod_image)
        .replace("ModAddress", f'{main_app["settings"].id}-{step}')
    )
    if step > 0:
        src_mod = sel_automtn.src_mod
        if src_mod in main_app["api_srv"].routers[sel_automtn.src_rt - 1].mod_addrs:
            src_mod_name = sel_automtn.trigger.settings.name
            page = page.replace(
                "<h3>Auslöser</h3>",
                f"<h3>Auslöser von Modul {src_mod}: '{src_mod_name}'</h3>",
            )
        else:
            page = page.replace(
                "<h3>Auslöser</h3>",
                f"<h3>Fehler: Modul {src_mod} unbekannt!<br>Abbruch.<br><br><br></h3>",
            )
            page = page.replace('<div id="trigger_frame"', '<!--div id="trigger_frame"')
            page = page.replace("<!-- MainContentEnd -->", "<-- MainContentEnd -->")

            page = page.replace('id="ok_button"', 'disabled id="ok_button"')
            return web.Response(text=page, content_type="text/html")

    page = sel_automtn.trigger.prepare_trigger_lists(main_app, page, step)
    page = sel_automtn.condition.prepare_condition_lists(main_app, page)
    page = sel_automtn.action.prepare_action_lists(main_app, page)
    return web.Response(text=page, content_type="text/html")


def fill_automations_template(main_app, title, subtitle, step) -> str:
    """Return automations page."""
    with open(
        WEB_FILES_DIR + AUTOMATIONS_TEMPLATE_FILE, mode="r", encoding="utf-8"
    ) as tplf_id:
        page = tplf_id.read()
    mod_image, mod_type = get_module_image(main_app["settings"].typ)
    page = (
        page.replace("ContentTitle", title)
        .replace("ContentSubtitle", subtitle)
        .replace("controller.jpg", mod_image)
        .replace("ModAddress", f'{main_app["settings"].id}-{step}')
    )
    if step == 0:
        page = disable_button("zurück", page)
    if step == 1:
        page = enable_new_popup(main_app["settings"], page)
        if len(main_app["api_srv"].routers) < 2:
            page = disable_button("weiter", page)
    if step == 2:
        # if (len(app["automations_def"].external) == 0) and (
        #     len(app["automations_def"].forward) == 0
        # ):
        page = disable_button("weiter", page)
    settings_form = prepare_automations_list(main_app, step)
    page = disable_chg_del_button(main_app, step, page)
    page = page.replace("<p>ContentText</p>", settings_form)
    return page


def enable_new_popup(settings, page: str) -> str:
    """Enable html code for module selection popup."""
    page = page.replace(
        '<!--button name="NewExtAutomtn"', '<button name="NewExtAutomtn"'
    )
    page = page.replace('"newext">Neu</button-->', '"newext">Neu</button>')
    page = page.replace('<button name="NewAutomtn"', '<!--button name="NewAutomtn"')
    page = page.replace('value="new">Neu</button>', 'value="new">Neu</button-->')
    rtr = settings.module.get_rtr()
    opt_str = '<option value="">-- Modul wählen --</option>'
    for mod in rtr.modules:
        if (mod._id != settings.id) and (mod._typ[0] != 20):
            # not self module, no Smart Nature
            opt_str += (
                f'<option value="modad-{mod._id}">{mod._id}: {mod._name}</option>'
            )
    page = page.replace('<option value="">-- Modul wählen --</option>', opt_str)
    return page


def disable_chg_del_button(main_app, step, page: str) -> str:
    """Disable buttons 'change' 'delete' if list empty."""
    if (step == 0) and (len(main_app["automations_def"].local) > 0):
        return page
    if (step == 1) and (len(main_app["automations_def"].external) > 0):
        return page
    if (step == 2) and (len(main_app["automations_def"].forward) > 0):
        return page
    page = page.replace('id="change_button"', 'id="change_button" disabled')
    page = page.replace('id="del_button"', 'id="del_button" disabled')
    return page


def prepare_automations_list(main_app, step):
    """Prepare automations list page."""
    curr_mod = 0
    if step == 0:
        automations = main_app["automations_def"].local
    else:
        automations = main_app["automations_def"].external
        last_source_header = ""
    tbl = (
        indent(4)
        + '<form id="automations_table" action="automations/automtns" method="post">\n'
    )
    for at_i in range(len(automations)):
        if step > 0:
            src_mod = automations[at_i].src_mod
            if at_i == 0:
                tbl += indent(5) + '<table id="atm-table">\n'
                tbl += indent(6) + "<thead>\n"
            if src_mod != curr_mod:
                rtr = main_app["api_srv"].routers[0]
                if src_mod in rtr.mod_addrs:
                    smod_name = rtr.modules[rtr.mod_addrs.index(src_mod)]._name
                    source_header = f"von Modul {src_mod}: '{smod_name}'"
                else:
                    source_header = f"von Modul {src_mod}"
                if source_header != last_source_header:
                    last_source_header = source_header
                    tbl += indent(6) + "</tbody>\n"
                    tbl += indent(6) + "<thead>\n"
                    tbl += (
                        indent(6)
                        + f'<tr id="atm-th" data-sort-method="none"><th><b>Auslöser {source_header}</b></th><th><b>Bedingung</b></th><th data-sort-method="none"></th><th><b>Aktion</b></th><th data-sort-method="none"></th></tr>\n'
                    )
                    tbl += indent(6) + "</thead>\n"
                    tbl += indent(6) + "<tbody>\n"

        else:
            if at_i == 0:
                tbl += indent(5) + '<table id="atm-table">\n'
                tbl += indent(6) + "<thead>\n"
                tbl += (
                    indent(6)
                    + '<tr id="atm-th" data-sort-method="none"><th><b>Auslöser</b></th><th><b>Bedingung</b></th><th data-sort-method="none"></th><th><b>Aktion</b></th><th data-sort-method="none"></th></tr>\n'
                )
                tbl += indent(6) + "</thead>\n"
                tbl += indent(6) + "<tbody>\n"
        tbl += indent(6) + '<tr id="atm-tr">\n'
        evnt_desc = automations[at_i].trigger.description
        cond_desc = automations[at_i].condition.name
        actn_desc = automations[at_i].action.description
        id_name = "atmn_tbl"
        sel_chkd = ""
        if at_i == main_app["automations_def"].selected:
            sel_chkd = "checked"
        tbl += (
            indent(7)
            + f"<td>{evnt_desc}</td><td>{cond_desc}</td><td align=center>&nbsp;&nbsp;&rArr;&nbsp;&nbsp;</td>\n"
        )
        tbl += indent(7) + f"<td>{actn_desc}</td>\n"
        tbl += f'<td><input type="radio" name="{id_name}" id="{id_name}" value="{at_i}" {sel_chkd}></td>'
        tbl += indent(6) + "</tr>\n"
    tbl += indent(6) + "</tbody>\n"
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


def prepare_src_mod_trigger(automtn, rtr, src_mod):
    """Init empty trigger into given automation."""
    automtn.src_mod = src_mod
    mod = rtr.get_module(src_mod)
    src_settings = ModuleSettings(mod)
    automtn.trigger = AutomationTrigger(automtn, src_settings, None)
    automtn.event_code = 0
    automtn.trigger.src_mod = automtn.src_mod
    automtn.trigger.src_rt = automtn.src_rt
    return automtn
