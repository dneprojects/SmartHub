import logging
from automtn_trigger import AutomationTrigger
from automtn_condition import AutomationCondition
from automtn_action import AutomationAction


class AutomationsSet:
    """Object with all automations."""

    def __init__(self, settings):
        """Initialize set of automations."""
        self.local: list(AutomationDefinition) = []
        self.external: list(AutomationDefinition) = []
        self.forward: list(AutomationDefinition) = []
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.get_autmn_dict(settings)
        self.get_automations(settings)
        self.selected = 0

    def get_autmn_dict(self, settings):
        """Build dict structure for automation names."""

        self.logger.debug("Building automation dictionary")
        self.autmn_dict = {}
        self.autmn_dict["inputs"] = {}
        self.autmn_dict["outputs"] = {}
        self.autmn_dict["covers"] = {}
        self.autmn_dict["buttons"] = {}
        self.autmn_dict["leds"] = {}
        self.autmn_dict["flags"] = {}
        self.autmn_dict["logic"] = {}
        self.autmn_dict["messages"] = {}
        self.autmn_dict["dir_cmds"] = {}
        self.autmn_dict["vis_cmds"] = {}
        self.autmn_dict["setvalues"] = {}
        self.autmn_dict["users"] = {}
        self.autmn_dict["fingers"] = {}
        self.autmn_dict["glob_flags"] = {}
        self.autmn_dict["coll_cmds"] = {}
        for a_key in self.autmn_dict.keys():
            for if_desc in getattr(settings, a_key):
                self.autmn_dict[a_key][if_desc.nmbr] = ""
                if len(if_desc.name) > 0:
                    self.autmn_dict[a_key][if_desc.nmbr] += f"{if_desc.name}"
        self.autmn_dict["user_modes"] = {1: "User1", 2: "User2"}
        self.autmn_dict["user_modes"][1] = settings.user1_name
        self.autmn_dict["user_modes"][2] = settings.user2_name

    def get_automations(self, settings):
        """Get automations of Habitron module."""

        self.logger.debug("Getting automations from list")
        list = settings.list
        no_lines = int.from_bytes(list[:2], "little")
        list = list[4 : len(list)]  # Strip 4 header bytes
        if len(list) == 0:
            return False
        for _ in range(no_lines):
            try:
                if list == b"":
                    break
                line_len = int(list[5]) + 5
                line = list[0:line_len]
                src_rt = int(line[0])
                src_mod = int(line[1])
                if ((src_rt == 0) | (src_rt == 250)) & (
                    src_mod == 0
                ):  # local automation
                    self.local.append(
                        AutomationDefinition(line, self.autmn_dict, settings)
                    )
                elif src_rt in range(200, 225):
                    # time trigger, also local automation
                    self.local.append(
                        AutomationDefinition(line, self.autmn_dict, settings)
                    )
                elif (src_rt == settings.module.rt_id) | (src_rt == 250):
                    self.external.append(
                        ExtAutomationDefinition(line, self.autmn_dict, settings)
                    )
                elif src_rt < 65:
                    self.forward.append(
                        ExtAutomationDefinition(line, self.autmn_dict, settings)
                    )
            except Exception as err_msg:
                self.logger.error(f"Error decoding automation {line}: {err_msg}")
            list = list[line_len : len(list)]  # Strip processed line
        self.local, i = self.sort_automation_list(self.local, 0)
        self.external, i = self.sort_automation_list(self.external, 0)
        self.forward, i = self.sort_automation_list(self.forward, 0)
        return True

    def save_changed_automation(self, app, form_data, step):
        """Save edited automation, add new or replace changed one."""
        tmp_automtn = AutomationDefinition(None, self.autmn_dict, self.settings)
        src_trigger = app["base_automation"].trigger
        tmp_automtn.trigger.src_rt = src_trigger.src_rt
        tmp_automtn.trigger.src_mod = src_trigger.src_mod
        tmp_automtn.trigger.settings = src_trigger.settings
        tmp_automtn.trigger.autmn_dict = src_trigger.autmn_dict
        tmp_automtn.trigger.save_changed_automation(app, form_data, step)
        tmp_automtn.condition.save_changed_automation(app, form_data, step)
        tmp_automtn.action.save_changed_automation(app, form_data, step)
        if step == 0:
            if app["atm_mode"] == "change":
                self.local[self.selected] = tmp_automtn
            else:
                self.local.append(tmp_automtn)
                self.selected = len(self.local) - 1
            self.local, self.selected = self.sort_automation_list(
                self.local, self.selected
            )
        if step == 1:
            if app["atm_mode"] == "change":
                self.external[self.selected] = tmp_automtn
            else:
                self.external.append(tmp_automtn)
                self.selected = len(self.external) - 1
            self.external, self.selected = self.sort_automation_list(
                self.external, self.selected
            )
        if step == 2:
            if app["atm_mode"] == "change":
                self.forward[self.selected] = tmp_automtn
            else:
                self.forward.append(tmp_automtn)
                self.selected = len(self.forward) - 1
            self.forward, self.selected = self.sort_automation_list(
                self.forward, self.selected
            )
        return

    def sort_automation_list(self, atm_list, sel_idx):
        """Sort all automations based on codes."""
        sort_strings = list()
        for atm in atm_list:
            sort_str = [
                atm.src_rt,
                atm.src_mod,
                atm.event_code,
                atm.trigger.event_arg1,
                atm.trigger.event_arg2,
                atm.condition.cond_code,
                atm.action_code,
            ] + atm.action.action_args
            sort_strings.append(sort_str)
        sorted_list_idx = sorted(range(len(sort_strings)), key=sort_strings.__getitem__)
        new_list = []
        for idx in sorted_list_idx:
            new_list.append(atm_list[idx])
        if len(atm_list) > 0:
            sel_idx_srtd = sorted_list_idx.index(sel_idx)
        else:
            sel_idx_srtd = sel_idx
        return new_list, sel_idx_srtd


class AutomationDefinition:
    """Object with automation data and methods."""

    def __init__(self, atm_def, autmn_dict, settings):
        """Fill all properties with automation's values."""
        self.mod_addr = settings.id
        self.autmn_dict = autmn_dict
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        if atm_def == None:
            self.src_rt = 0
            self.src_mod = 0
            self.event_code = 0
            self.action_code = 0
        else:
            self.src_rt = int(atm_def[0])
            self.src_mod = int(atm_def[1])
            self.event_code = int(atm_def[2])
            self.action_code = int(atm_def[7])
        self.logger.debug(f"Initializing trigger for automation {atm_def}")
        self.trigger = AutomationTrigger(self, settings, atm_def)
        self.condition = AutomationCondition(self, atm_def)
        self.logger.debug(f"Initializing action for automation {atm_def}")
        self.action = AutomationAction(self, atm_def)
        self.logger.debug(f"Initializing of automation done")

    def event_name(self) -> str:
        """Return event name."""
        return self.trigger.name

    def action_name(self) -> str:
        """Return action name."""
        return self.action.name

    def get_dict_entry(self, key, arg) -> str:
        """Lookup dict and return value, if found."""
        if key in self.autmn_dict.keys():
            if arg in self.autmn_dict[key].keys():
                return f"{arg}: '{self.autmn_dict[key][arg]}'"
            else:
                return f"'{arg}'"
        return f"{arg}"

    def make_automtn_copy(self):
        """Create new instance from self."""
        new_automtn = AutomationDefinition(None, self.autmn_dict, self.settings)
        new_automtn.trigger = self.trigger
        new_automtn.condition = self.condition
        new_automtn.action = self.action
        new_automtn.action_code = self.action_code
        new_automtn.event_code = self.event_code
        new_automtn.src_rt = self.src_rt
        new_automtn.src_mod = self.src_mod
        return new_automtn

    def get_output_desc(self, arg: int, time_function: bool) -> str:
        """Return string description for output arg."""
        if arg < 16:
            unit_no = arg
            out_desc = f"Ausgang {self.get_dict_entry('outputs', unit_no)}"
            return out_desc
        if arg < 25:
            unit_no = arg - 16
            out_desc = f"LED {self.get_dict_entry('leds', unit_no)}"
            return out_desc
        if time_function:
            if arg < 32:
                unit_no = arg - 24
                out_desc = f"Lok. Merker {self.get_dict_entry('flags', unit_no)}"
            elif arg < 41:
                unit_no = arg - 32
                out_desc = f"Glob. Merker {self.get_dict_entry('glob_flags', unit_no)}"
            else:
                l_inp = arg - 41
                unit_no = int(l_inp / 2) + 1
                inp_no = l_inp - (unit_no - 1) * 2 + 1
                unit_no, inp_no, l_name = self.get_counter_inputs(l_inp)
                out_desc = f"Logikeingang {inp_no} von Unit {unit_no}"
            return out_desc
        else:
            if arg < 117:
                unit_no = arg - 100
                out_desc = f"Lok. Merker {self.get_dict_entry('flags', unit_no)}"
            elif arg < 149:
                unit_no = arg - 132
                out_desc = f"Glob. Merker {self.get_dict_entry('glob_flags', unit_no)}"
            else:
                l_inp = arg - 164
                unit_no, inp_no, l_name = self.get_counter_inputs(l_inp)
                if l_name == "":
                    out_desc = f"Logikeingang {inp_no} von Unit {unit_no}"
                else:
                    if inp_no == 1:
                        out_desc = f"Zähler '{l_name}' hoch"
                    elif inp_no == 2:
                        out_desc = f"Zähler '{l_name}' runter"
                    else:
                        out_desc = f"Zähler '{l_name}' ???"
            return out_desc

    def get_counter_inputs(self, log_inp: int):
        """Return counter information, if counter input found."""
        unit_no = int(log_inp / 8)
        inp_no = log_inp - unit_no * 8
        l_units = self.settings.logic
        for lg_unit in l_units:
            if (lg_unit.type == 5) & (lg_unit.nmbr == unit_no + 1):
                return unit_no + 1, inp_no, lg_unit.name
        return unit_no + 1, inp_no, ""

    def get_mode_desc(self, md_no: int) -> str:
        """Return description for mode number."""
        md_desc = ""
        if md_no == 0:
            md_desc = "Immer"
        md_no1 = md_no & 0xF0
        if md_no1 == 16:
            md_desc = "Abwesend"
        if md_no1 == 32:
            md_desc = "Anwesend"
        if md_no1 == 48:
            md_desc = "Schlafen"
        if md_no1 == 80:
            md_desc = self.settings.user1_name
        if md_no1 == 96:
            md_desc = self.settings.user2_name
        if md_no1 == 112:
            md_desc = "Urlaub"
        if (md_no & 0x03) == 1:
            md_desc += ", Tag"
        elif (md_no & 0x03) == 2:
            md_desc += ", Nacht"
        if (md_no & 0x04) == 4:
            md_desc += ", Alarm"
        if md_desc[0] == ",":
            return md_desc[2:]
        return md_desc

    def make_definition(self) -> bytes:
        """Return definition line as bytes."""

        actn_arg_len = len(self.action.action_args)
        def_line = (
            chr(self.src_rt)
            + chr(self.src_mod)
            + chr(self.trigger.event_code)
            + chr(self.trigger.event_arg1)
            + chr(self.trigger.event_arg2)
            + chr(actn_arg_len + 3)
            + chr(self.condition.cond_code)
            + chr(self.action.action_code)
        )
        for actn_arg in self.action.action_args:
            def_line += chr(actn_arg)
        return def_line

    def set_visible(self, page, select_str: str) -> str:
        """Replace 'hidden' attribute of html element by 'visible'."""
        return page.replace(select_str + "hidden", select_str + "visible")

    def set_option(self, page, select_val, select_str: str) -> str:
        """Search line by value and/or string (use None to choose) and add 'selected'."""
        if select_val == None:
            search_str = ""
        else:
            search_str = f'<option value="{select_val}"'
        repl_str = search_str + " selected"
        if select_str != None:
            search_str += f">{select_str}<"
            repl_str += f">{select_str}<"
        return page.replace(search_str, repl_str)

    def replace_default_value(self, page, select_str: str, def_val, new_val) -> str:
        """Search string and default value by new value."""
        new_str = select_str.replace(f'value="{def_val}"', f'value="{new_val}"')
        return page.replace(select_str, new_str)

    def get_sel(self, form, key):
        """Pick selector number from form based on key, strip prefix."""
        form_entry = form[key][0]
        if form_entry.find("-") > 0:
            return int(form_entry.split("-")[1])
        return int(form_entry)

    def get_val(self, form, key):
        """Pick selector number from form based on key, strip prefix."""
        form_entry = form[key][0]
        if form_entry.find("-") > 0:
            return float(form_entry.split("-")[1])
        return float(form_entry)


class ExtAutomationDefinition(AutomationDefinition):
    """Object with automation data and methods, etras for ext. trigger."""

    def __init__(self, atm_def, autmn_dict, settings):
        super().__init__(atm_def, autmn_dict, settings)
        rtr = settings.module.get_rtr()
        if self.src_mod in rtr.mod_addrs:
            mod = rtr.get_module(self.src_mod)
            src_settings = mod.get_settings_def()
            self.trigger = AutomationTrigger(self, src_settings, atm_def)
        else:
            settings.logger.warning(
                f"Automation reference to module {self.src_mod}, module not found."
            )
            self.trigger = AutomationTrigger(self, settings, atm_def)
