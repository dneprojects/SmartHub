CondCodes = {
    0: "Immer",
    1: "Tag",
    2: "Nacht",
    4: "Alarm",
    16: "Abwesend",
    32: "Anwesend",
    48: "Schlafen",
    80: "User1",
    96: "User2",
    112: "Urlaub",
}


class AutomationCondition:
    """Object for condition part of habitron automations."""

    def __init__(self, autmn, atm_def: bytes):
        self.automation = autmn
        if atm_def is None:
            self.src_rt = 0
            self.src_mod = 0
            self.cond_code = 0
        else:
            self.src_rt = int(atm_def[0])
            self.src_mod = int(atm_def[1])
            self.cond_code = int(atm_def[6])
        self.autmn_dict = autmn.autmn_dict
        self.name, self.cond_arg = self.parse()

    def parse(self) -> tuple[str, int]:
        """Return condition name and argument."""
        if self.cond_code in range(160, 184):  # time 0 .. 24
            cond_name = f"Uhrzeit: {self.cond_code - 160}h"
            return cond_name, self.cond_code - 160
        if self.cond_code in range(192, 208):  # local flag not set
            cond_name = (
                f'{self.get_dict_entry("flags", self.cond_code - 191)} rückgesetzt'
            )
            return cond_name, self.cond_code - 191
        if self.cond_code in range(208, 224):  # local flag set
            cond_name = f'{self.get_dict_entry("flags", self.cond_code - 207)} gesetzt'
            return cond_name, self.cond_code - 207
        if self.cond_code in range(224, 240):  # global flag not set
            cond_name = (
                f'{self.get_dict_entry("glob_flags", self.cond_code - 223)} rückgesetzt'
            )
            return cond_name, self.cond_code - 223 + 32
        if self.cond_code in range(240, 256):  # global flag set
            cond_name = (
                f'{self.get_dict_entry("glob_flags", self.cond_code - 239)} gesetzt'
            )
            return cond_name, self.cond_code - 239 + 32
        cond_name = CondCodes.get(self.cond_code, "Not found")
        if cond_name == "Not found":
            cond_name = CondCodes.get(self.cond_code & 0xF8, "Not found")
            cond_name += f', {CondCodes.get(self.cond_code & 0x07, "Not found")}'
        cond_name = cond_name.replace(
            "User1", self.autmn_dict["user_modes"][1]
        ).replace("User2", self.autmn_dict["user_modes"][2])
        return cond_name, self.cond_code & 0x07

    def get_dict_entry(self, key, arg) -> str:
        """Lookup dict and return value, if found."""
        if key in self.autmn_dict.keys():
            if arg in self.autmn_dict[key].keys():
                return self.autmn_dict[key][arg]
        return f"{arg}"

    def get_selector_conditions(self):
        """Return available triggers for given module settings."""
        conditions_dict1 = {
            0: "Immer",
            207: "Merker gesetzt",
            191: "Merker rückgesetzt",
            160: "Uhrzeit",
            16: "Modus 'Abwesend'",
            32: "Modus 'Anwesend'",
            48: "Modus 'Schlafen'",
            80: f"Modus '{self.automation.settings.user1_name}'",
            96: f"Modus '{self.automation.settings.user2_name}'",
            112: "Modus 'Urlaub'",
            1: "Modus 'Tag'/'Nacht'/'Alarm'",
        }
        conditions_dict2 = {
            0: "Immer",
            1: "Modus 'Tag'",
            2: "Modus 'Nacht'",
            4: "Modus 'Alarm'",
        }
        return conditions_dict1, conditions_dict2

    def prepare_condition_lists(self, app, page: str) -> str:
        """Replace options part of select boxes for edit automation."""

        opt_str = '<option value="">-- Bedingung wählen --</option>\n'
        cond_dict, mode2_dict = self.get_selector_conditions()
        for key in cond_dict:
            opt_str += f'<option value="{key}">{cond_dict[key]}</option>\n'
        page = page.replace('<option value="">-- Bedingung wählen --</option>', opt_str)

        opt_str = ""
        for key in mode2_dict:
            opt_str += f'<option value="{key}">{mode2_dict[key]}</option>\n'
        page = page.replace('<option value="">-- cond_2_sel --</option>', opt_str)

        opt_str = '<option value="">-- Zeitspanne wählen --</option>'
        for hour in range(24):
            opt_str += f'<option value="{hour}">von {hour} bis {hour+1} Uhr</option>'
        page = page.replace('<option value="">-- cond_time_sel --</option>', opt_str)

        opt_str = '<option value="">-- Merker wählen --</option>'
        for flag in app["settings"].flags:
            opt_str += f'<option value="{flag.nmbr}">{flag.name}</option>'
        for flag in app["settings"].glob_flags:
            opt_str += f'<option value="{flag.nmbr+32}">{flag.name}</option>'
        page = page.replace('<option value="">-- cond_flag_sel --</option>', opt_str)
        page = self.activate_ui_elements(page)
        return page

    def activate_ui_elements(self, page: str) -> str:
        """Set javascript values according to sel automation."""
        page = page.replace(
            "const cnd_code = 0;", f"const cnd_code = {self.cond_code};"
        )
        return page

    def save_changed_automation(self, app, form_data, step):
        """Extract and set condition part from edit form."""
        cond_sel = self.automation.get_sel(form_data, "condition_sel")
        if cond_sel == 1:
            self.cond_code = self.automation.get_sel(form_data, "condition_mode2")
        elif cond_sel >= 191:
            self.cond_code = cond_sel + self.automation.get_sel(
                form_data, "condition_flag"
            )
        elif cond_sel == 160:
            self.cond_code = cond_sel + self.automation.get_sel(
                form_data, "condition_time"
            )
        else:
            self.cond_code = cond_sel + self.automation.get_sel(
                form_data, "condition_mode2"
            )
        self.name, self.cond_arg = self.parse()
        return
