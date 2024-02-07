from const import MirrIdx

ActionNames = {
    1: "Ausgang ein",
    2: "Ausgang aus",
    3: "Ausgang wechseln",
    6: "Counter",
    7: "Rollladenbefehl",
    9: "Zeitfunktion",
    10: "Summton",
    17: "Rollladenbefehl",
    18: "Rollladenbefehl auf Zeit",
    20: "Dimmwert",
    22: "Dimmcount start",
    23: "Dimmcount stop",
    24: "Dimmen komplett",
    30: "Prozentwert anzeigen",
    31: "Prozentwert in Register",
    35: "RGB-Licht",
    50: "Sammelbefehl",
    55: "Alarmmeldung auslösen",
    56: "Meldung setzen",
    57: "Meldung zurücksetzen",
    58: "Meldung auf Zeit",
    64: "Modus setzen",
    111: "Merker setzen",
    112: "Merker rücksetzen",
    113: "Merker wechseln",
    114: "Zeitfunktion Merker",
    118: "Zähler hoch zählen",
    119: "Zähler abwärts zählen",
    220: "Temperatursollwert",
    221: "Klimaregelung interner Sensor",
    222: "Klimaregelung externer Sensor",
    240: "Modulbeleuchtung",
}

TempTargetCodes = {
    1: "Temperatursollwert 1 setzen",
    21: "Temperatursollwert 2 setzen",
    2: "Temperatursollwert 1 temporär setzen",
    22: "Temperatursollwert 2 temporär setzen",
    3: "Temperatursollwert 1 rücksetzen",
    23: "Temperatursollwert 2 rücksetzen",
    11: "Heizmodus setzen",
    12: "Kühlmodus setzen",
    13: "Heiz-/Kühlmodus setzen",
    14: "Regelung auschalten",
}
SelActCodes = {
    "output": 1,
    "led": 2,
    "counter": 6,
    "buzzer": 10,
    "cover": 17,
    "dimm": 20,
    "rgb": 35,
    "collcmd": 50,
    "mode": 64,
    "flag": 111,
    "climate": 220,
    "ambient": 240,
}

ActionsSets = {
    1: [
        1,
        2,
        3,
        9,
        101,
        102,
        103,
    ],
    2: [
        1,
        2,
        3,
        9,
        101,
        102,
        103,
    ],
    6: [6, 118, 119],
    10: [10],
    17: [17, 18],
    20: [20, 22, 23, 24],
    35: [35],
    50: [50],
    64: [64],
    111: [111, 112, 113, 114],
    220: [220, 221, 222],
    240: [240],
}


class AutomationAction:
    """Object for action part of habitron automations."""

    def __init__(self, autmn, atm_def: bytes):
        self.automation = autmn
        if atm_def is None:
            self.src_rt = 0
            self.src_mod = 0
            self.action_code = 0
            self.action_args = []
        else:
            self.src_rt = int(atm_def[0])
            self.src_mod = int(atm_def[1])
            self.action_code = int(atm_def[7])
            self.action_args = []
            for a in atm_def[8:]:
                self.action_args.append(int(a))
        self.autmn_dict = autmn.autmn_dict
        self.name = self.action_name()
        self.parse()

    def action_name(self) -> str:
        """Return action name."""
        return ActionNames.get(self.action_code, "unknown action")

    def get_dict_entry(self, key, arg) -> str:
        """Lookup dict and return value, if found."""
        if key in self.autmn_dict.keys():
            if arg in self.autmn_dict[key].keys():
                return f"{arg}: '{self.autmn_dict[key][arg]}'"
            else:
                return f"'{arg}'"
        return f"{arg}"

    def get_selector_actions(self):
        """Return available actions for given module settings."""
        typ = self.automation.settings.typ
        if typ[0] == 1:
            actions_dict = {
                SelActCodes["output"]: "Ausgang",
                SelActCodes["dimm"]: "Dimmen",
                SelActCodes["cover"]: "Rollladen/Jalousie",
                SelActCodes["led"]: "LED",
                SelActCodes["climate"]: "Klima",
                SelActCodes["collcmd"]: "Sammelbefehl",
                SelActCodes["flag"]: "Merker",
                SelActCodes["mode"]: "Modus",
                SelActCodes["counter"]: "Zähler",
                SelActCodes["ambient"]: "Modulbeleuchtung",
                SelActCodes["buzzer"]: "Summton",
            }
        elif typ == b"\x32\x01":  # Smart Controller Mini
            actions_dict = {
                SelActCodes["output"]: "Ausgang",
                SelActCodes["led"]: "LED",
                SelActCodes["rgb"]: "RGB",
                SelActCodes["climate"]: "Klima",
                SelActCodes["collcmd"]: "Sammelbefehl",
                SelActCodes["flag"]: "Merker",
                SelActCodes["mode"]: "Modus",
                SelActCodes["counter"]: "Zähler",
                SelActCodes["buzzer"]: "Summton",
            }
        elif (typ[0] == 10) & (typ[1] in [20, 21, 22]):  # dimm output modules
            actions_dict = {
                SelActCodes["output"]: "Ausgang",
                SelActCodes["dimm"]: "Dimmen",
                SelActCodes["climate"]: "Klima",
                SelActCodes["collcmd"]: "Sammelbefehl",
                SelActCodes["flag"]: "Merker",
                SelActCodes["mode"]: "Modus",
                SelActCodes["counter"]: "Zähler",
            }
        elif typ[0] == 10:  # other output modules
            actions_dict = {
                SelActCodes["output"]: "Ausgang",
                SelActCodes["cover"]: "Rollladen/Jalousie",
                SelActCodes["climate"]: "Klima",
                SelActCodes["collcmd"]: "Sammelbefehl",
                SelActCodes["flag"]: "Merker",
                SelActCodes["mode"]: "Modus",
                SelActCodes["counter"]: "Zähler",
            }
        else:
            actions_dict = {}
        return actions_dict

    def parse(self):
        """Parse action arguments and return description."""
        try:
            self.unit = None
            self.value = None
            actn_target = self.action_name()
            actn_desc = ""
            for actn_arg in self.action_args:
                actn_desc += chr(actn_arg)
            if self.action_code in [1, 2, 3]:  # set/reset/toggle of outputs/leds/flags
                self.unit = self.action_args[0]
                actn_desc = actn_target.replace("Ausgang", "").strip()
                actn_target = self.automation.get_output_desc(
                    self.action_args[0], False
                )
            elif actn_target[:6] == "Zähler":
                actn_desc = actn_target.replace("Zähler ", "")
                self.unit = int((self.action_args[0] - 165) / 8) + 1
                actn_target = f"Zähler {self.get_dict_entry('logic', self.unit)}"
            elif self.action_code in [9]:  # time dependant set functions
                self.unit = self.action_args[3]
                actn_target = self.automation.get_output_desc(self.unit, True)
                if self.action_args[2] == 255:
                    actn_desc = (
                        f"mit {self.action_args[1]} <unit> Verzögerung einschalten"
                    )
                    time_unit = self.action_args[0]
                else:
                    actn_target += f" {self.action_args[2]}x"
                    if self.action_args[0] > 20:
                        actn_desc = (
                            f"mit {self.action_args[1]} <unit> Verzögerung ausschalten"
                        )
                        time_unit = self.action_args[0] - 20
                    elif self.action_args[0] > 10:
                        actn_desc = (
                            f"für {self.action_args[1]} <unit> einschalten (o.Ä.)"
                        )
                        time_unit = self.action_args[0] - 10
                    else:
                        actn_desc = f"für {self.action_args[1]} <unit> einschalten"
                        time_unit = self.action_args[0]
                if time_unit == 1:
                    actn_desc = actn_desc.replace("<unit>", "Sek.")
                else:
                    actn_desc = actn_desc.replace("<unit>", "Min.")
            elif actn_target[:4] == "Dimm":
                self.unit = self.action_args[0]
                if self.automation.settings.typ[0] == 1:
                    outp_no = self.action_args[0] + 10
                else:
                    outp_no = self.action_args[0]
                out_desc = self.get_dict_entry("outputs", outp_no)
                if actn_target == "Dimmwert":
                    actn_desc = f"{self.action_args[1]}%"
                else:
                    actn_desc = actn_target.split()[1]
                actn_target = f"{actn_target.split()[0]} {out_desc}"
            elif actn_target == "Counter":
                self.unit = self.action_args[0]
                actn_target = (
                    f"Zähler {self.get_dict_entry('logic', self.action_args[0])}"
                )
                actn_desc = f"auf {self.action_args[2]} setzen"
            elif actn_target[:6] == "Sammel":
                actn_target = f"{actn_target.split()[0]} {self.get_dict_entry('coll_cmds',self.action_args[0])}"
                actn_desc = ""
            elif actn_target[:4] == "Meld":
                actn_target = (
                    f"Meldung {self.get_dict_entry('messages',self.action_args[0])}"
                )
                if self.action_code == 58:
                    actn_desc = f"für {self.action_args[1]} Min. setzen"
                else:
                    actn_desc = ""
            elif actn_target[:5] == "Modus":
                actn_desc = "setzen"
                txt_high = self.automation.get_mode_desc(self.action_args[1])
                if self.action_args[0] == 1:
                    txt_low = ", 'Alarm ein'"
                elif self.action_args[0] == 2:
                    txt_low = ", 'Alarm aus'"
                elif self.action_args[0] == 3:
                    txt_low = ", 'Tag'"
                elif self.action_args[0] == 4:
                    txt_low = ", 'Nacht'"
                else:
                    txt_low = ""
                actn_target = f"Modus für Gruppe {self.automation.settings.rtr.groups[self.automation.mod_addr-1]} auf '{txt_high}'{txt_low}"
                actn_target = actn_target.replace("'Immer', ", "")

            elif actn_target[:6] == "Temper":
                strings = TempTargetCodes[self.action_args[0]].split()
                if self.action_args[0] in [11, 12, 13, 14]:
                    actn_target = TempTargetCodes[self.action_args[0]]
                    actn_desc = ""
                elif self.action_args[0] in [2, 22]:
                    value = self.action_args[1] / 10
                    actn_target = f"{strings[0]} {strings[1]}"
                    actn_desc = f"{strings[2]} {strings[3]}"
                else:
                    value = self.action_args[1] / 10
                    actn_target = f"{strings[0]} {strings[1]}"
                    actn_desc = f"{strings[2]}"
                if self.action_args[0] in [1, 21, 2, 22]:
                    actn_desc = actn_desc.replace("setzen", f"auf {value} °C setzen")
            elif actn_target[:5] == "Rolll":
                self.unit = self.action_args[1]
                cover_desc = f"{self.get_dict_entry('covers', self.action_args[1])}"
                if self.action_args[2] == 255:
                    pos_str = "inaktiv"
                else:
                    pos_str = f"auf {self.action_args[2]}%"
                if self.action_code == 18:
                    temp_desc = f"für {self.action_args[1]} Min. "
                else:
                    temp_desc = ""
                if self.action_args[0] > 10:
                    self.action_args[0] -= 10
                    actn_desc = f"{cover_desc} {temp_desc} {pos_str} setzen"
                else:
                    actn_desc = f"{cover_desc} {temp_desc} {pos_str} setzen"
                if self.action_args[0] == 1:
                    actn_target = "Rollladen"
                else:
                    actn_target = "Lamellen"
            elif actn_target[:5] == "Klima":
                actn_target += f", Offset {self.action_args[0]}"
                actn_desc = (
                    f"Ausgang {self.get_dict_entry('outputs', self.action_args[1])}"
                )
            elif actn_target[:4] == "Summ":
                actn_target += f" {self.action_args[2]}x:"
                actn_desc = f"Höhe {self.action_args[0]}, Dauer {self.action_args[1]}"
            elif self.action_code == 35:  # RGB-LED
                task = self.action_args[0]
                task2 = self.action_args[1]
                led_id = self.action_args[2]
                if led_id in range(1, 9):
                    actn_desc = f"#{led_id} "
                elif led_id in range(41, 45):
                    actn_desc = f"Ecke {led_id - 40} "
                elif led_id == 100:
                    actn_desc = f"gesamt "
                else:
                    actn_desc = f"Farbe unverändert "
                if task == 1:
                    actn_desc += "setzen"
                elif task == 2:
                    actn_desc += "ausschalten"
                elif task == 3:
                    actn_desc += "temporär setzen"
                elif task == 5:
                    actn_desc += "zurück setzen"
                if len(self.action_args) > 5:
                    red = self.action_args[3]
                    green = self.action_args[4]
                    blue = self.action_args[5]
                    actn_desc += f" - rot: {red}, grün: {green}, blau: {blue}"
            elif self.action_code == 240:
                actn_target += f" für {self.action_args[0]} s"
                actn_desc = ""
            else:
                self.description = (
                    f"{actn_target}: {self.action_code} / {self.action_args}"
                )
                return
            self.description = actn_target + chr(32) + actn_desc
            return
        except Exception as err_msg:
            self.automation.settings.logger.error(
                f"Could not handle action code:  {self.action_code} / {self.action_args}, Error: {err_msg}"
            )
            self.description = (
                actn_target + chr(32) + f"{self.action_code} / {self.action_args}"
            )
            return

    def prepare_action_lists(self, app, page: str) -> str:
        """Replace options part of select boxes for edit automation."""
        sel_atm = self.automation
        opt_str = '<option value="">-- Aktion wählen --</option>\n'
        sel_actions = self.get_selector_actions()
        self.action_id = self.action_code
        if self.action_code in [1, 2, 3]:
            if self.action_args[0] > 100:
                self.action_id = self.action_code + 110
        elif self.action_code == 9:
            if self.action_args[3] > 24:
                self.action_id = 114
        for act_key in sel_actions:
            if self.action_id in ActionsSets[act_key]:
                if act_key in [1, 2]:
                    if ((act_key == 1) & (self.unit < 16)) | (
                        (act_key == 2) & (self.unit in range(17, 25))
                    ):
                        opt_str += f'<option value="{act_key}" selected>{sel_actions[act_key]}</option>\n'
                    else:
                        opt_str += (
                            f'<option value="{act_key}">{sel_actions[act_key]}</option>'
                        )
                else:
                    opt_str += f'<option value="{act_key}" selected>{sel_actions[act_key]}</option>'
            else:
                opt_str += f'<option value="{act_key}">{sel_actions[act_key]}</option>'
        page = page.replace('<option value="">-- Aktion wählen --</option>', opt_str)

        opt_str = '<option value="">-- Ausgang wählen --</option>'
        for outp in app["settings"].outputs:
            opt_str += f'<option value="{outp.nmbr}">{outp.name}</option>\n'
        page = page.replace('<option value="">-- AcAusgang wählen --</option>', opt_str)
        opt_str = '<option value="">-- Ausgang wählen --</option>'
        for outp in app["settings"].outputs:
            opt_str += f'<option value="{outp.nmbr}">{outp.name}</option>\n'
        page = page.replace('<option value="">-- ClAusgang wählen --</option>', opt_str)
        opt_str = '<option value="">-- Dimm-Ausgang wählen --</option>'
        for dimm in sel_atm.settings.dimmers:
            opt_str += f'<option value="{dimm.nmbr}">{dimm.name}</option>'
        page = page.replace(
            '<option value="">-- Dimm-Ausgang wählen --</option>', opt_str
        )

        opt_str = '<option value="">-- Rollladen/Jalousie wählen --</option>'
        no_covs = 0
        for cov in sel_atm.settings.covers:
            if cov.type > 0:
                opt_str += f'<option value="{cov.nmbr}">{cov.name}</option>'
                no_covs += 1
        if no_covs == 0:
            page = page.replace(
                f'<option value="{SelActCodes["cover"]}">',
                f'<option value="{SelActCodes["cover"]}" disabled>',
            )
        page = page.replace(
            '<option value="">-- Rollladen/Jalousie wählen --</option>', opt_str
        )
        opt_str = '<option value="">-- LED wählen --</option>'
        for led in app["settings"].leds:
            opt_str += f'<option value="{led.nmbr + 16}">{led.name}</option>\n'
        page = page.replace('<option value="">-- LED wählen --</option>', opt_str)

        if (sel_atm.settings.typ[0] != 1) & (sel_atm.settings.typ != b"\x32\x01"):
            page = page.replace(
                f'<option value="{SelActCodes["buzzer"]}">',
                f'<option value="{SelActCodes["buzzer"]}" disabled>',
            )
        if (
            (sel_atm.settings.typ == b"\x0a\x14")
            | (sel_atm.settings.typ == b"\x0a\x15")
            | (sel_atm.settings.typ == b"\x0a\x16")
        ):
            page = page.replace(
                f'<option value="{SelActCodes["climate"]}">',
                f'<option value="{SelActCodes["climate"]}" disabled>',
            )
            page = page.replace(
                f'<option value="{SelActCodes["cover"]}">',
                f'<option value="{SelActCodes["cover"]}" disabled>',
            )

        opt_str = '<option value="">-- Befehl wählen --</option>'
        for cmd in app["settings"].coll_cmds:
            opt_str += f'<option value="{cmd.nmbr}">{cmd.name}</option>'
        page = page.replace(
            '<option value="">-- AcCKommando wählen --</option>', opt_str
        )
        opt_str = '<option value="">-- Merker wählen --</option>'
        for flg in app["settings"].flags:
            opt_str += f'<option value="{flg.nmbr}">{flg.name}</option>\n'
        for flg in app["settings"].glob_flags:
            opt_str += f'<option value="{flg.nmbr + 32}">{flg.name}</option>\n'
        page = page.replace('<option value="">-- AcMerker wählen --</option>', opt_str)
        opt_str = '<option value="">-- Zähler wählen --</option>'
        max_cnt = []
        no_counters = 0
        for cnt in app["settings"].logic:
            if cnt.type == 5:
                no_counters += 1
                max_cnt.append(app["settings"].status[MirrIdx.LOGIC - 2 + cnt.nmbr * 3])
                if self.unit == cnt.nmbr:
                    opt_str += (
                        f'<option value="{cnt.nmbr}" selected>{cnt.name}</option>\n'
                    )
                else:
                    opt_str += f'<option value="{cnt.nmbr}">{cnt.name}</option>\n'
        page = page.replace('<option value="">-- AcZähler wählen --</option>', opt_str)
        if no_counters == 0:
            page = page.replace(
                f'<option value="{SelActCodes["counter"]}">',
                f'<option value="{SelActCodes["counter"]}" disabled>',
            )
        page = page.replace(">User1Mode<", f">{self.autmn_dict['user_modes'][1]}<")
        page = page.replace(">User2Mode<", f">{self.autmn_dict['user_modes'][2]}<")
        page = self.activate_ui_elements(page)
        return page

    def activate_ui_elements(self, page: str) -> str:
        """Set javascript values according to sel automation."""

        page = page.replace(
            "const act_code = 0;", f"const act_code = {self.action_id};"
        )
        page = page.replace(
            "const act_args = [0, 0];", f"const act_args = {self.action_args};"
        )
        return page

    def save_changed_automation(self, app, form_data, step):
        """Extract and set action part from edit form."""
        self.action_code = self.automation.get_sel(form_data, "action_sel")
        if self.action_code in [1, 2]:
            # output, needs further checks for flash options
            if self.action_code == 1:
                out_no = self.automation.get_sel(form_data, "act_output")
                self.unit = out_no
            else:
                out_no = self.automation.get_sel(form_data, "act_led")
                self.unit = out_no - 16
            outp_opt = self.automation.get_sel(form_data, "act_outopt")
            if outp_opt in [1, 2, 3]:
                self.action_code = outp_opt
                self.action_args.append(out_no)
            else:
                self.action_code = 9
                self.action_args.append(
                    self.automation.get_sel(form_data, "act_timeunit")
                )
                if outp_opt == 5:
                    self.action_args[-1] += 10
                if outp_opt == 7:
                    self.action_args[-1] += 20
                self.action_args.append(int(form_data["timeinterv_val"][0]))
                if outp_opt == 6:
                    self.action_args.append(255)
                else:
                    self.action_args.append(1)
                self.action_args.append(out_no)

        elif self.action_code in ActionsSets[SelActCodes["flag"]]:
            # flag, needs further checks for flash options
            flg_no = self.automation.get_sel(form_data, "act_flag")
            outp_opt = self.automation.get_sel(form_data, "act_outopt")
            if outp_opt in [1, 2, 3]:
                self.action_code = outp_opt
                self.action_args.append(flg_no + 100)
            else:
                self.action_code = 9
                self.action_args.append(
                    self.automation.get_sel(form_data, "act_timeunit")
                )
                if outp_opt == 5:
                    self.action_args[-1] += 10
                if outp_opt == 7:
                    self.action_args[-1] += 20
                self.action_args.append(int(form_data["timeinterv_val"][0]))
                if outp_opt == 6:
                    self.action_args.append(255)
                else:
                    self.action_args.append(1)
                if flg_no < 9:
                    flg_no += 24
                elif flg_no < 17:
                    flg_no += 16  # should not happen, only first 8 flags allowed
                self.action_args.append(flg_no)
        elif self.action_code in ActionsSets[SelActCodes["counter"]]:
            # counter (logic inputs not supported)
            counter_opt = self.automation.get_sel(form_data, "act_countopt")
            counter_no = self.automation.get_sel(form_data, "act_counter")
            if counter_opt == 1:  # count up
                self.action_code = 118
                self.action_args.append(165 + (counter_no - 1) * 8)
            elif counter_opt == 2:  # count down
                self.action_code = 119
                self.action_args.append(166 + (counter_no - 1) * 8)
            else:  # set counter value
                self.action_args.append(counter_no)
                self.action_args.append(5)
                val = self.automation.get_sel(form_data, "cnt_val")
                self.action_args.append(val)
                self.action_args.append(0)

        elif self.action_code in ActionsSets[SelActCodes["buzzer"]]:
            self.action_args.append(int(form_data["buzz_freq"][0]))
            self.action_args.append(int(form_data["buzz_dur"][0]))
            self.action_args.append(int(form_data["buzz_rep"][0]))

        elif self.action_code in ActionsSets[SelActCodes["dimm"]]:
            self.unit = self.automation.get_sel(form_data, "act_dimmout")
            self.action_code = self.automation.get_sel(form_data, "act_dimmopt")
            self.action_args.append(self.unit)
            self.action_args.append(int(form_data["perc_val"][0]))

        elif self.action_code in ActionsSets[SelActCodes["collcmd"]]:
            self.unit = self.automation.get_sel(form_data, "act_collcmd")
            self.action_args.append(self.unit)

        elif self.action_code in ActionsSets[SelActCodes["cover"]]:
            self.unit = self.automation.get_sel(form_data, "act_cover")
            self.action_args.append(self.automation.get_sel(form_data, "act_covopt"))
            self.action_args.append(self.unit)
            self.action_args.append(int(form_data["perc_val"][0]))

        elif self.action_code in ActionsSets[SelActCodes["climate"]]:
            cl_opt = self.automation.get_sel(form_data, "act_climopt")
            if cl_opt in [1, 2]:
                set_opt = self.automation.get_sel(form_data, "act_tsetopt")
                set_opt = (cl_opt - 1) * 20 + set_opt
                self.action_args.append(set_opt)
                if set_opt in [3, 23]:
                    self.action_args.append(0)
                    self.action_args.append(0)
                else:
                    self.action_args.append(int(float(form_data["tset_val"][0]) * 10))
                    self.action_args.append(0)
            elif cl_opt in [21, 22]:
                self.action_code = 200 + cl_opt
                self.unit = self.automation.get_sel(form_data, "act_climoutput")
                self.action_args.append(0)
                self.action_args.append(self.unit)
            else:
                self.action_args.append(cl_opt)
                self.action_args.append(0)
                self.action_args.append(0)

        elif self.action_code in ActionsSets[SelActCodes["mode"]]:
            md_low = self.automation.get_sel(form_data, "mode_low")
            md_high = self.automation.get_sel(form_data, "mode_high")
            self.action_args.append(md_low)
            self.action_args.append(md_high)

        elif self.action_code in ActionsSets[SelActCodes["ambient"]]:
            time = self.automation.get_sel(form_data, "modlite_time")
            self.action_args.append(time)
        self.automation.action_code = self.action_code
        self.name = self.action_name()
        self.parse()
        return
