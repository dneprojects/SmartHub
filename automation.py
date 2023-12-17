EventCodes = {
    6: "Merker/Logik",
    10: "Ausgangsänderung",
    23: "IR-Befehl",
    40: "Bewegung Innenlicht",
    41: "Bewegung Außenlicht",
    50: "Sammelereignis",
    137: "Modusänderung",
    149: "Dimmbefehl",
    150: "Taste kurz",
    151: "Taste lang",
    152: "Schalter ein",
    153: "Schalter aus",
    154: "Taste lang Ende",
    169: "Ekey",
    170: "Timer",
    203: "Außenhelligkeit",
    204: "Wind",
    205: "Regen",
    215: "Feuchte",
    221: "Klima Sensor intern",
    222: "Klima Sensor extern",
}

ActionCodes = {
    1: "Ausgang ein",
    2: "Ausgang aus",
    3: "Ausgang wechseln",
    6: "Logik",
    9: "Zeitfunktion",
    10: "Summton",
    17: "Rollladenbefehl",
    22: "Dimmcount start,",
    23: "Dimmcount stop",
    24: "Dimmen komplett",
    30: "Prozentwert anzeigen",
    31: "Prozentwert in Register",
    35: "RGB-LED",
    50: "Sammelbefehl",
    55: "Alarmmeldung auslösen",
    56: "Meldung setzen",
    57: "Meldung zurücksetzen",
    64: "Modus setzen",
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


class AutomationsSet:
    """Object with all automations."""

    def __init__(self, settings):
        """Initialize set of automations."""
        self.local: list(AutomationDefinition) = []
        self.external: list(AutomationDefinition) = []
        self.forward: list(AutomationDefinition) = []
        self.get_autmn_dict(settings)
        self.get_automations(settings)
        self.selected = 0

    def get_autmn_dict(self, settings):
        """Build dict structure for automation names."""
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
                self.autmn_dict[a_key][if_desc.nmbr] = f"{if_desc.nmbr}"
                if len(if_desc.name) > 0:
                    self.autmn_dict[a_key][if_desc.nmbr] += f": '{if_desc.name}'"

    def get_automations(self, settings):
        """Get automations of Habitron module."""

        list = settings.list
        no_lines = int.from_bytes(list[:2], "little")
        list = list[4 : len(list)]  # Strip 4 header bytes
        if len(list) == 0:
            return False
        for _ in range(no_lines):
            if list == b"":
                break
            line_len = int(list[5]) + 5
            line = list[0:line_len]
            src_rt = int(line[0])
            src_mod = int(line[1])
            if ((src_rt == 0) | (src_rt == 250)) & (src_mod == 0):  # local automation
                self.local.append(AutomationDefinition(line, self.autmn_dict, settings))
            elif (src_rt == settings.module.rt._id) | (src_rt == 250):
                self.external.append(
                    AutomationDefinition(line, self.autmn_dict, settings)
                )
            elif src_rt < 65:
                self.forward.append(
                    AutomationDefinition(line, self.autmn_dict, settings)
                )
            list = list[line_len : len(list)]  # Strip processed line
        return True


class AutomationDefinition:
    """Object with automation data and methods."""

    def __init__(self, atm_def, autmn_dict, settings):
        """Fill all properties with automation's values."""
        if isinstance(atm_def, bytes):
            self.mod_addr = settings.id
            self.autmn_dict = autmn_dict
            self.settings = settings
            self.src_rt = int(atm_def[0])
            self.src_mod = int(atm_def[1])
            self.event_code = int(atm_def[2])
            self.event_arg1 = int(atm_def[3])
            self.event_arg2 = int(atm_def[4])
            self.condition = int(atm_def[6])
            self.action_code = int(atm_def[7])
            self.action_args = []
            for a in atm_def[8:]:
                self.action_args.append(int(a))

    def event_name(self) -> str:
        """Return event name."""
        return EventCodes[self.event_code]

    def action_name(self) -> str:
        """Return action name."""
        return ActionCodes[self.action_code]

    def get_dict_entry(self, key, arg) -> str:
        """Lookup dict and return value, if found."""
        if arg in self.autmn_dict[key].keys():
            return self.autmn_dict[key][arg]
        return f"{arg}"

    def event_description(self) -> str:
        """Parse event arguments and return 2 readable fields."""
        event_trig = self.event_name()
        event_arg = self.event_arg1
        self.event_arg_name = f"{event_arg}"
        event_desc = self.event_arg_name
        if event_trig[:5] in ["Taste", "Schal", "Dimmb"]:
            if event_trig[:5] == "Dimmb":
                event_desc = ""
            else:
                event_desc = (
                    event_trig.replace("Taste", "").replace("Schalter", "").strip()
                )
                event_trig = event_trig.replace(event_desc, "").strip()
                if event_arg < 9:
                    event_trig += f" {self.get_dict_entry('buttons', event_arg)}"
                else:
                    event_trig += f" {self.get_dict_entry('inputs',event_arg - 8)}"
        elif event_trig == "Merker/Logik":
            if event_arg == 0:
                set_str = "rückgesetzt"
            else:
                set_str = "gesetzt"
            event_arg += self.event_arg2  # one is always zero
            event_arg2 = ""
            if event_arg in range(1, 17):
                self.event_arg_name = self.get_dict_entry("flags", event_arg)
                event_trig = f"Lokaler Merker {self.event_arg_name}"
                event_desc = set_str
            elif event_arg in range(33, 49):
                event_arg -= 32
                self.event_arg_name = self.get_dict_entry("glob_flags", event_arg)
                event_trig = f"Globaler Merker {self.event_arg_name}"
                event_desc = set_str
            elif event_arg in range(81, 91):
                event_arg -= 80
                self.event_arg_name = self.get_dict_entry("counters", event_arg)
                event_trig = f"Logikausgang {self.event_arg_name}"
                event_desc = set_str
            else:
                for cnt_i in range(10):
                    if event_arg in range(96 + cnt_i * 16, 96 + (cnt_i + 1) * 16):
                        event_arg2 = event_arg - 95 - cnt_i * 16
                        event_arg = cnt_i + 1
                        self.event_arg_name = self.get_dict_entry("counters", event_arg)
                        event_trig = f"Counter {self.event_arg_name}"
                        event_desc = f"Wert {event_arg2} erreicht"
                        break
        elif event_trig == "Modusänderung":
            event_trig = "Modus neu: "
            if self.event_arg2 == 1:
                event_trig += "Tag"
            elif self.event_arg2 == 2:
                event_trig += "Nacht"
            elif self.event_arg2 == 4:
                event_trig += "Alarm"
            elif self.event_arg2 == 16:
                event_trig += "Abwesend"
            if self.event_arg2 == 32:
                event_trig += "Anwesend"
            if self.event_arg2 == 48:
                event_trig += "Schlafen"
            if self.event_arg2 == 80:
                event_trig += "Sommer"
            if self.event_arg2 == 96:
                event_trig += "User1"
            if self.event_arg2 == 112:
                event_trig += "User2"
            event_desc = ""
        elif event_trig == "Sammelereignis":
            self.event_arg_name = self.get_dict_entry("coll_cmds", event_arg)
            event_trig = f"Sammelereignis {self.event_arg_name}"
            event_desc = ""
        elif event_trig[:5] == "Klima":
            if self.event_arg1 == 1:
                event_desc = "heizen"
            else:
                event_desc = "kühlen"
        return event_trig + chr(32) + event_desc

    def action_description(self) -> str:
        """Parse action arguments and return 2 readable fields."""
        actn_target = self.action_name()
        actn_desc = ""
        for actn_arg in self.action_args:
            actn_desc += chr(actn_arg)
        if actn_target[:7] == "Ausgang":
            if self.action_args[0] < 17:
                actn_desc = actn_target.replace("Ausgang", "").strip()
                actn_target = (
                    f"Ausgang {self.get_dict_entry('outputs', self.action_args[0])}"
                )
            else:
                actn_desc = actn_target.replace("Ausgang", "").strip()
                actn_target = (
                    f"LED {self.get_dict_entry('leds', self.action_args[0 -16])}"
                )
        elif actn_target[:4] == "Dimm":
            actn_desc = actn_target.split()[1]
            if self.settings.typ[0] == 1:
                outp_no = self.action_args[0] + 10
            else:
                outp_no = self.action_args[0]
            actn_target = (
                f"{actn_target.split()[0]} {self.get_dict_entry('outputs',outp_no)}"
            )
        elif actn_target[:6] == "Sammel":
            actn_target = f"{actn_target.split()[0]} {self.get_dict_entry('coll_cmds',self.action_args[0])}"
            actn_desc = ""
        elif actn_target[:6] == "Temper":
            value = self.action_args[1] / 10
            strings = TempTargetCodes[self.action_args[0]].split()
            if self.action_args[0] in [11, 12, 13, 14]:
                actn_target = TempTargetCodes[self.action_args[0]]
                actn_desc = ""
            elif self.action_args[0] in [2, 22]:
                actn_target = f"{strings[0]} {strings[1]}"
                actn_desc = f"{strings[2]} {strings[3]}"
            else:
                actn_target = f"{strings[0]} {strings[1]}"
                actn_desc = f"{strings[2]}"
        elif actn_target[:5] == "Klima":
            actn_target += f", Offset {self.action_args[0]}"
            actn_desc = f"Ausgang {self.get_dict_entry('outputs', self.action_args[1])}"
        return actn_target + chr(32) + actn_desc

    def make_definition(self) -> bytes:
        """Return definition line as bytes."""
        def_line = (
            chr(self.src_rt)
            + chr(self.src_mod)
            + chr(self.event_code)
            + chr(self.event_arg1)
            + chr(self.event_arg2)
            + chr(len(self.action_args) + 8)
            + chr(self.condition)
            + chr(self.action_code)
        )
        for actn_arg in self.action_args:
            def_line += chr(actn_arg)
        return def_line.encode("iso8859-1")
