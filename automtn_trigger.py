EventCodes = {
    0: "---",
    6: "Merker/Logik",
    10: "Ausgangsänderung",
    23: "IR-Befehl kurz",
    24: "IR-Befehl lang",
    25: "IR-Befehl lang Ende",
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
    253: "Direktbefehl"
}

EventCodesNew = {
    0: "---",
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
    169: "Ekey",
    170: "Timer",
    203: "Außenhelligkeit",
    204: "Wind",
    205: "Regen",
    215: "Feuchte",
    221: "Klima Sensor intern",
    222: "Klima Sensor extern",
    253: "Direktbefehl"
}

EventArgsLogic = {
    1: "Merker lokal",
    33: "Merker global",
    81: "Logikausgang", # 1 to 10 for each unit
    96: "Counterwert", # 16 for each counter x 10 .. 255
    
}

class AutomationTrigger:
    """Object for trigger part of habitron automations."""
    
    def __init__(self, autmn, atm_def: bytes, autmn_dict):
        self.automation = autmn
        if atm_def is None:
            self.src_rt = 0
            self.src_mod = 0
            self.event_code = 0
            self.event_arg1 = 0
            self.event_arg2 = 0
        else:
            self.src_rt = int(atm_def[0])
            self.src_mod = int(atm_def[1])
            self.event_code = int(atm_def[2])
            self.event_arg1 = int(atm_def[3])
            self.event_arg2 = int(atm_def[4])
        self.autmn_dict = autmn_dict
        self.name = self.event_name()


    def event_name(self) -> str:
        """Return event name."""
        try:
            evnt_name = EventCodes[self.event_code]
        except:
            evnt_name = "unknown event"
        return evnt_name

    def get_dict_entry(self, key, arg) -> str:
        """Lookup dict and return value, if found."""
        if key in self.autmn_dict.keys():
            if arg in self.autmn_dict[key].keys():
                return self.autmn_dict[key][arg]
        return f"{arg}"

    
    def description(self) -> str:
        """Parse event arguments and return readable string."""
        try:
            event_arg = self.event_arg1
            self.event_arg_name = f"{event_arg}"
            event_desc = self.event_arg_name
            if self.event_code in range(149,155):
                if self.name[:5] == "Dimmb":
                    trig_command = self.name
                    event_desc = ""
                else:
                    event_desc = (
                        self.name.replace("Taste", "").replace("Schalter", "").strip()
                    )
                    trig_command = self.name.replace(event_desc, "").strip()
                    if event_arg < 9:
                        trig_command += f" {self.get_dict_entry('buttons', event_arg)}"
                    else:
                        trig_command += f" {self.get_dict_entry('inputs',event_arg - 8)}"
            elif self.name == "Merker/Logik":
                if event_arg == 0:
                    set_str = "rückgesetzt"
                else:
                    set_str = "gesetzt"
                event_arg += self.event_arg2  # one is always zero
                event_arg2 = ""
                if event_arg in range(1, 17):
                    self.event_arg_name = self.get_dict_entry("flags", event_arg)
                    trig_command = f"Lokaler Merker {self.event_arg_name}"
                    event_desc = set_str
                elif event_arg in range(33, 49):
                    event_arg -= 32
                    self.event_arg_name = self.get_dict_entry("glob_flags", event_arg)
                    trig_command = f"Globaler Merker {self.event_arg_name}"
                    event_desc = set_str
                elif event_arg in range(81, 91):
                    event_arg -= 80
                    self.event_arg_name = self.get_dict_entry("logic", event_arg)
                    trig_command = f"Logikausgang {self.event_arg_name}"
                    event_desc = set_str
                else:
                    for cnt_i in range(10):
                        if event_arg in range(96 + cnt_i * 16, 96 + (cnt_i + 1) * 16):
                            event_arg2 = event_arg - 95 - cnt_i * 16
                            event_arg = cnt_i + 1
                            self.event_arg_name = self.get_dict_entry("logic", event_arg)
                            trig_command = f"Counter {self.event_arg_name}"
                            event_desc = f"Wert {event_arg2} erreicht"
                            break
            elif self.name == "Modusänderung":
                trig_command = "Modus neu: "
                trig_command += self.automation.get_mode_desc(self.event_arg1)
                event_desc = ""
            elif self.name == "Sammelereignis":
                self.event_arg_name = self.get_dict_entry("coll_cmds", event_arg)
                trig_command = f"Sammelereignis {self.event_arg_name}"
                event_desc = ""
            elif self.name[:5] == "Klima":
                trig_command = self.name
                if self.event_arg1 == 1:
                    event_desc = "heizen"
                else:
                    event_desc = "kühlen"
            elif self.name == "Ausgangsänderung":
                trig_command = self.name
                if self.event_arg1:
                    event_desc = f"{self.automation.get_output_desc(self.event_arg1)} an"
                else:
                    event_desc = f"{self.automation.get_output_desc(self.event_arg2)} aus"
            elif self.name[:9] == "IR-Befehl":
                trig_command = f"IR-Befehl: '{self.event_arg1} | {self.event_arg2}'"
                if self.event_code == 23:
                    event_desc = "kurz"
                if self.event_code == 24:
                    event_desc = "lang"
                if self.event_code == 25:
                    event_desc = "lang Ende"
            elif self.name == "Direktbefehl":
                trig_command = self.name + f" {self.event_arg1}: '{self.get_dict_entry('dir_cmds', self.event_arg1)}'"
            else:
                return f"{trig_command}: {self.event_code} / {self.event_arg1} / {self.event_arg2}"
            return trig_command + chr(32) + event_desc
        except Exception as err_msg:
            self.automation.settings.logger.error(f"Could not handle event code:  {self.event_code} / {self.event_arg1} / {self.event_arg2}, Error: {err_msg}")
            return f"{self.name}: {self.event_code} / {self.event_arg1} / {self.event_arg2}"
