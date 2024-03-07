from automtn_condition import CondCodes
from const import MirrIdx
from const import FingerNames

EventCodes = {
    0: "---",
    6: "Merker/Logik",
    10: "Ausgangsänderung",
    12: "Netzspannung",
    23: "IR-Befehl kurz",
    24: "IR-Befehl lang",
    25: "IR-Befehl lang Ende",
    30: "Prozentübergabe Nummer",
    31: "Visualisierungsbefehl",
    40: "Bewegung Innenlicht",
    41: "Bewegung Außenlicht",
    50: "Sammelereignis",
    101: "Systemfehler",
    137: "Modusänderung",
    149: "Dimmbefehl",
    150: "Taste kurz",
    151: "Taste lang",
    152: "Schalter ein",
    153: "Schalter aus",
    154: "Taste lang Ende",
    169: "Ekey",
    170: "Timer",
    201: "Außentemperatur",
    202: "Luftfeuchtigkeit außen",
    203: "Außenhelligkeit",
    204: "Wind",
    205: "Regen",
    206: "Wind Peak",
    213: "Innentemperatur",
    215: "Luftfeuchtigkeit innen",
    216: "Helligkeit innen",
    217: "Luftqualität",
    218: "A/D Eingang 1",
    219: "A/D Eingang 2",
    221: "Klima Sensor intern",
    222: "Klima Sensor extern",
    249: "Modulstart",
    253: "Direktbefehl",
}

EventCodesSel = {
    150: "Taster",
    151: "Taster",
    152: "Schalter",
    153: "Schalter",
    149: "Dimmen",
    10: "Ausgangsänderung",
    253: "Direktbefehl",
    50: "Sammelbefehl",
    31: "Visualisierungsbefehl",
    6: "Merker",
    137: "Modusänderung",
    40: "Bewegung",
    41: "Bewegung",
    201: "Sensor",
    202: "Sensor",
    203: "Sensor",
    204: "Sensor",
    205: "Sensor",
    213: "Sensor",
    215: "Sensor",
    216: "Sensor",
    217: "Sensor",
    218: "AD1",
    219: "AD2",
    220: "Klima",
    221: "Klima",
    222: "Klima",
    170: "Zeit",
    249: "System",
}

EventArgsLogic = {
    1: "Merker lokal",
    33: "Merker global",
    81: "Logikausgang",  # 1 to 10 for each unit
    96: "Zählerwert",  # 16 for each counter x 10 .. 255
}

SelTrgCodes = {
    "logic": 6,
    "count": 9,
    "output": 10,
    "remote": 23,
    "viscmd": 31,
    "move": 40,
    "collcmd": 50,
    "mode": 137,
    "dimm": 149,
    "button": 150,
    "switch": 152,
    "ekey": 169,
    "time": 170,
    "sensor": 203,
    "climate": 220,
    "system": 249,
    "dircmd": 253,
}

EventsSets = {
    6: [6],
    9: [9],
    10: [10],
    23: [23],
    31: [31],
    40: [40, 41],
    50: [50],
    137: [137],
    149: [149],
    150: [150, 151, 154],
    152: [152, 153],
    169: [169],
    170: [170],
    203: [201, 202, 203, 204, 205, 206, 213, 214, 215, 216, 217, 218, 219],
    220: [220, 221, 222],
    249: [12, 101, 249],
    253: [253],
}
SelSensCodes = {
    "temp_ext": 201,
    "humid_ext": 202,
    "light_ext": 203,
    "wind": 204,
    "rain": 205,
    "wind_peak": 206,
    "temp_int": 213,
    "humid_int": 215,
    "light_int": 216,
    "airqual": 217,
    "ad_1": 218,
    "ad_2": 219,
}
SensorUnit = {
    201: "°C",
    202: "%",
    203: "Lux",
    204: "m/s",
    205: "",
    206: "m/s",
    213: "°C",
    215: "%",
    216: "Lux",
    217: "%",
    218: "V",
    219: "V",
}

Weekdays = {
    50: "Sonntag",
    51: "Montag",
    52: "Dienstag",
    53: "Mittwoch",
    54: "Donnerstag",
    55: "Freitag",
    56: "Samstag",
}

Months = {
    1: "Januar",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember",
}


class AutomationTrigger:
    """Object for trigger part of habitron automations."""

    def __init__(self, autmn, settings, atm_def: bytes):
        self.automation = autmn
        self.settings = settings
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
        self.get_trigger_dict()
        self.name = self.event_name()
        self.parse()

    def event_name(self) -> str:
        """Return event name."""
        return EventCodes.get(self.event_code, "unknown event")

    def get_trigger_dict(self):
        """Build dict structure for automation names."""
        if self.automation.src_rt == 0:
            self.autmn_dict = self.automation.autmn_dict
            return
        settings = self.settings
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

    def get_dict_entry(self, key, arg) -> str:
        """Lookup dict and return value, if found."""
        if key in self.autmn_dict.keys():
            if arg in self.autmn_dict[key].keys():
                return f"{arg}: '{self.autmn_dict[key][arg]}'"
            else:
                return f"'{arg}'"
        return f"{arg}"

    def get_selector_triggers(self, internal):
        """Return available triggers for given module."""

        if internal:
            mod_typ = self.settings.module._typ
        else:
            mod_typ = (
                self.settings.module.api_srv.routers[self.src_rt - 1]
                .get_module(self.src_mod)
                ._typ
            )

        if mod_typ[0] == 1:
            self.triggers_dict = {
                SelTrgCodes["button"]: "Taster",
                SelTrgCodes["switch"]: "Schalter",
                SelTrgCodes["dimm"]: "Dimmen",
                SelTrgCodes["remote"]: "IR-Fernbedienung",
                SelTrgCodes["output"]: "Ausgangsänderung",
                SelTrgCodes["climate"]: "Klimaregelung",
                SelTrgCodes["dircmd"]: "Direktbefehl",
                SelTrgCodes["collcmd"]: "Sammelbefehl",
                SelTrgCodes["viscmd"]: "Visualisierungsbefehl",
                SelTrgCodes["logic"]: "Merker",
                SelTrgCodes["mode"]: "Modusänderung",
                SelTrgCodes["move"]: "Bewegung",
                SelTrgCodes["sensor"]: "Sensor",
                SelTrgCodes["count"]: "Zählerwert",
                SelTrgCodes["time"]: "Zeit",
                SelTrgCodes["system"]: "System",
            }
            self.sensors_dict = {
                SelSensCodes["ad_1"]: "A/D-Kanal 1",
                SelSensCodes["ad_2"]: "A/D-Kanal 2",
                SelSensCodes["temp_ext"]: "Temperatur außen",
                SelSensCodes["temp_int"]: "Temperatur innen",
                SelSensCodes["humid_ext"]: "Feuchte außen",
                SelSensCodes["humid_int"]: "Feuchte innen",
                SelSensCodes["light_ext"]: "Helligkeit außen",
                SelSensCodes["light_int"]: "Helligkeit innen",
                SelSensCodes["airqual"]: "Luftqualität",
                SelSensCodes["rain"]: "Regen",
                SelSensCodes["wind_peak"]: "Wind",
            }
        if mod_typ == b"\x32\x01":
            self.triggers_dict = {
                SelTrgCodes["button"]: "Taster",
                SelTrgCodes["switch"]: "Schalter",
                SelTrgCodes["dimm"]: "Dimmen",
                SelTrgCodes["output"]: "Ausgangsänderung",
                SelTrgCodes["climate"]: "Klimaregelung",
                SelTrgCodes["dircmd"]: "Direktbefehl",
                SelTrgCodes["collcmd"]: "Sammelbefehl",
                SelTrgCodes["viscmd"]: "Visualisierungsbefehl",
                SelTrgCodes["logic"]: "Merker",
                SelTrgCodes["mode"]: "Modusänderung",
                SelTrgCodes["move"]: "Bewegung",
                SelTrgCodes["sensor"]: "Sensor",
                SelTrgCodes["count"]: "Zählerwert",
                SelTrgCodes["time"]: "Zeit",
            }
            self.sensors_dict = {
                SelSensCodes["ad_1"]: "A/D-Kanal 1",
                SelSensCodes["ad_2"]: "A/D-Kanal 2",
                SelSensCodes["temp_ext"]: "Temperatur außen",
                SelSensCodes["temp_int"]: "Temperatur innen",
                SelSensCodes["humid_ext"]: "Feuchte außen",
                SelSensCodes["humid_int"]: "Feuchte innen",
                SelSensCodes["light_ext"]: "Helligkeit außen",
                SelSensCodes["light_int"]: "Helligkeit innen",
                SelSensCodes["airqual"]: "Luftqualität",
                SelSensCodes["rain"]: "Regen",
                SelSensCodes["wind_peak"]: "Wind",
            }
        if mod_typ[0] == 10:
            self.triggers_dict = {
                SelTrgCodes["output"]: "Ausgangsänderung",
                SelTrgCodes["collcmd"]: "Sammelbefehl",
                SelTrgCodes["viscmd"]: "Visualisierungsbefehl",
                SelTrgCodes["logic"]: "Merker",
                SelTrgCodes["mode"]: "Modusänderung",
                SelTrgCodes["sensor"]: "Sensor",
                SelTrgCodes["count"]: "Zählerwert",
                SelTrgCodes["time"]: "Zeit",
            }
            self.sensors_dict = {
                SelSensCodes["temp_ext"]: "Temperatur außen",
                SelSensCodes["humid_ext"]: "Feuchte außen",
                SelSensCodes["light_ext"]: "Helligkeit außen",
                SelSensCodes["rain"]: "Regen",
                SelSensCodes["wind_peak"]: "Wind",
            }
        if mod_typ[0] == 0x0B:
            self.triggers_dict = {
                SelTrgCodes["button"]: "Taster",
                SelTrgCodes["switch"]: "Schalter",
                SelTrgCodes["dimm"]: "Dimmen",
                SelTrgCodes["collcmd"]: "Sammelbefehl",
                SelTrgCodes["mode"]: "Modusänderung",
            }
            self.sensors_dict = {
                SelSensCodes["temp_ext"]: "Temperatur außen",
                SelSensCodes["humid_ext"]: "Feuchte außen",
                SelSensCodes["light_ext"]: "Helligkeit außen",
                SelSensCodes["rain"]: "Regen",
                SelSensCodes["wind_peak"]: "Wind",
            }
        if mod_typ == b"\x1e\x01":
            self.triggers_dict = {
                SelTrgCodes["ekey"]: "Fingerprint",
                SelTrgCodes["collcmd"]: "Sammelbefehl",
                SelTrgCodes["viscmd"]: "Visualisierungsbefehl",
                SelTrgCodes["logic"]: "Merker",
                SelTrgCodes["mode"]: "Modusänderung",
            }
            self.sensors_dict = {
                SelSensCodes["temp_ext"]: "Temperatur außen",
                SelSensCodes["humid_ext"]: "Feuchte außen",
                SelSensCodes["light_ext"]: "Helligkeit außen",
                SelSensCodes["rain"]: "Regen",
                SelSensCodes["wind_peak"]: "Wind",
            }
        if mod_typ[0] == 0x50:
            self.triggers_dict = {
                SelTrgCodes["move"]: "Bewegung",
            }
            self.sensors_dict = {
                SelSensCodes["light_int"]: "Helligkeit",
            }

        return self.triggers_dict, self.sensors_dict

    def parse(self) -> str:
        """Parse event arguments and return readable string."""
        try:
            self.unit = None
            self.value = None
            self.event_id = None
            event_arg = self.event_arg1
            self.event_arg_name = f"{event_arg}"
            event_desc = self.event_arg_name
            if self.event_code in range(149, 155):
                if self.event_code in EventsSets[SelTrgCodes["dimm"]]:
                    trig_command = self.name + " Taste"
                    self.name = ""
                    event_desc = ""
                else:
                    event_desc = (
                        self.name.replace("Taste", "").replace("Schalter", "").strip()
                    )
                    trig_command = self.name.replace(event_desc, "").strip()
                if event_arg < 9:
                    trig_command += f" {self.get_dict_entry('buttons', event_arg)}"
                    self.unit = event_arg
                else:
                    trig_command += f" {self.get_dict_entry('inputs',event_arg - 8)}"
                    self.unit = event_arg - 8
            elif self.event_code in EventsSets[SelTrgCodes["logic"]]:
                if event_arg == 0:
                    set_str = "rückgesetzt"
                    self.value = 0
                else:
                    set_str = "gesetzt"
                    self.value = 1
                event_arg += self.event_arg2  # one is always zero
                event_arg2 = ""
                if event_arg in range(1, 17):
                    self.unit = event_arg
                    self.event_arg_name = self.get_dict_entry("flags", self.unit)
                    trig_command = f"Lokaler Merker {self.event_arg_name}"
                    event_desc = set_str
                elif event_arg in range(33, 49):
                    # self.event_id = 7  # modify code for later separation
                    self.unit = event_arg - 32
                    self.event_arg_name = self.get_dict_entry("glob_flags", self.unit)
                    trig_command = f"Globaler Merker {self.event_arg_name}"
                    event_desc = set_str
                elif event_arg in range(81, 91):
                    # self.event_id = 8
                    self.unit = event_arg - 80
                    self.event_arg_name = self.get_dict_entry("logic", self.unit)
                    trig_command = f"Logikausgang {self.event_arg_name}"
                    event_desc = set_str
                else:
                    # range(96,256)
                    for cnt_i in range(10):
                        if event_arg in range(96 + cnt_i * 16, 96 + (cnt_i + 1) * 16):
                            self.event_id = 9  # modify code for later separation
                            self.unit = cnt_i + 1
                            self.value = event_arg - 95 - cnt_i * 16
                            event_arg = cnt_i + 1
                            self.event_arg_name = self.get_dict_entry(
                                "logic", event_arg
                            )
                            trig_command = f"Counter {self.event_arg_name}"
                            event_desc = f"Wert {self.value} erreicht"
                            break
            elif self.event_code in EventsSets[SelTrgCodes["mode"]]:
                trig_command = (
                    f"Modus neu: '{self.automation.get_mode_desc(self.event_arg2)}'"
                )
                event_desc = ""
            elif self.event_code in EventsSets[SelTrgCodes["collcmd"]]:
                self.event_arg_name = self.get_dict_entry("coll_cmds", event_arg)
                trig_command = f"Sammelereignis {self.event_arg_name}"
                event_desc = ""
            elif self.event_code in EventsSets[SelTrgCodes["viscmd"]]:
                self.event_arg_name = self.get_dict_entry(
                    "vis_cmds", self.event_arg1 + 256 * self.event_arg2
                )
                trig_command = f"Visualisierungsereignis {self.event_arg_name}"
                event_desc = ""
            elif self.event_code in EventsSets[SelTrgCodes["climate"]]:
                trig_command = self.name
                if self.event_arg1 == 1:
                    event_desc = "heizen"
                else:
                    event_desc = "kühlen"
                self.value = self.event_arg1
            elif self.event_code in EventsSets[SelTrgCodes["output"]]:
                trig_command = self.name
                self.unit = self.event_arg1 + self.event_arg2
                if self.event_arg1:
                    event_desc = f"{self.get_output_desc(self.unit, False)} an"
                    self.value = 1
                else:
                    event_desc = f"{self.get_output_desc(self.unit, False)} aus"
                    self.value = 0
            elif self.event_code in EventsSets[SelTrgCodes["remote"]]:
                trig_command = f"IR-Befehl: '{self.event_arg1} | {self.event_arg2}'"
                if self.event_code == 23:
                    event_desc = "kurz"
                if self.event_code == 24:
                    event_desc = "lang"
                if self.event_code == 25:
                    event_desc = "lang Ende"
            elif self.event_code in EventsSets[SelTrgCodes["dircmd"]]:
                trig_command = (
                    self.name + f" {self.get_dict_entry('dir_cmds', self.event_arg1)}"
                )
                event_desc = ""
            elif self.event_code in EventsSets[SelTrgCodes["move"]]:
                trig_command = f"Bewegung: Intensität {self.event_arg1},"
                if self.event_code == 40:
                    event_desc = "innen "
                else:
                    event_desc = "außen "
                if self.event_arg2 == 0:
                    event_desc = "immer"
                else:
                    event_desc += f"dunkler als {self.event_arg2 * 10} Lux"
            elif self.event_code in EventsSets[SelTrgCodes["time"]]:
                trig_command = f"Um {self.src_rt - 200}:{self.src_mod:02d} Uhr"
                event_desc = ""
                if self.event_arg1 + self.event_arg2 > 0:
                    trig_command += " jeden"
                if self.event_arg1 in range(1, 32):
                    event_desc += f"{self.event_arg1}."
                    if self.event_arg2 > 0:
                        event_desc += f" {Months[self.event_arg2]}"
                    else:
                        event_desc += " im Monat"
                elif self.event_arg1 in range(50, 57):
                    event_desc += f"{Weekdays[self.event_arg1]}"
                    if self.event_arg2 > 0:
                        event_desc += f" im {Months[self.event_arg2]}"
                    else:
                        event_desc += " im Monat"
                else:
                    if self.event_arg2 > 0:
                        event_desc += f"Tag im {Months[self.event_arg2]}"
            elif self.event_code in EventsSets[SelTrgCodes["sensor"]]:
                unit = SensorUnit[self.event_code]
                if self.event_code == SelSensCodes["rain"]:
                    if self.event_arg1 == 74:
                        trig_command = "Bei Regen"
                    else:
                        trig_command = "Kein Regen"
                elif self.event_code in [
                    SelSensCodes["temp_ext"],
                    SelSensCodes["temp_int"],
                ]:
                    trig_command = f"{EventCodes[self.event_code]} zwischen {self.u2sign7(self.event_arg1)} und {self.u2sign7(self.event_arg2)} {unit}"
                elif self.event_code in [SelSensCodes["ad_1"], SelSensCodes["ad_2"]]:
                    trig_command = f"{EventCodes[self.event_code]} zwischen {self.event_arg1 / 25} und {self.event_arg2 / 25} {unit}"
                elif self.event_code in [
                    SelSensCodes["light_ext"],
                    SelSensCodes["light_int"],
                ]:
                    trig_command = f"{EventCodes[self.event_code]} zwischen {self.event_arg1 * 10} und {self.event_arg2 * 10} {unit}"
                else:
                    trig_command = f"{EventCodes[self.event_code]} zwischen {self.event_arg1} und {self.event_arg2} {unit}"
                event_desc = ""
            elif self.event_code in EventsSets[SelTrgCodes["ekey"]]:
                id = self.event_arg1
                if id == 255:
                    trig_command = "Fingerprint: Fehler oder unbekannter Nutzer"
                else:
                    user = self.autmn_dict["users"].get(id, "unbekannter Nutzer")
                    trig_command = (
                        f"{FingerNames[self.event_arg2 - 1]} von '{user}' erkannt"
                    )
                event_desc = ""
            elif self.event_code == 30:
                trig_command = self.name
                event_desc = f"{self.event_arg1}"
            elif self.event_code == 12:
                trig_command = self.name
                if self.event_arg1 == 74:
                    event_desc = "aktiv"
                else:
                    event_desc = "inaktiv"
            elif self.event_code == 249:
                trig_command = self.name
                event_desc = ""
            elif self.event_code == 101:
                trig_command = self.name
                event_desc = f"{self.event_arg1 * 256 + self.event_arg2}"
            else:
                trig_command = "Unknown event"
                self.description = f"Unknown event: {self.event_code} / {self.event_arg1} / {self.event_arg2}"
                return
            self.description = trig_command + chr(32) + event_desc
            if self.event_id == None:
                self.event_id = self.event_code
            return
        except Exception as err_msg:
            self.settings.logger.error(
                f"Could not handle event code:  {self.event_code} / {self.event_arg1} / {self.event_arg2}, Error: {err_msg}"
            )
            self.description = f"{self.name}: {self.event_code} / {self.event_arg1} / {self.event_arg2}"
            return

    def prepare_trigger_lists(self, app, page: str, step: int) -> str:
        """Replace options part of select boxes for edit automation."""
        sel_triggers, sel_sensors = self.get_selector_triggers(step == 0)
        opt_str = '<option value="">-- Auslösendes Ereignis wählen --</option>\n'
        for key in sel_triggers:
            opt_str += f'<option value="{key}">{sel_triggers[key]}</option>\n'
        page = page.replace(
            '<option value="">-- Auslösendes Ereignis wählen --</option>', opt_str
        )
        opt_str = '<option value="">-- Sensor wählen --</option>\n'
        for key in sel_sensors:
            opt_str += f'<option value="{key}">{sel_sensors[key]}</option>\n'
        page = page.replace('<option value="">-- Sensor wählen --</option>', opt_str)

        opt_str = '<option value="">-- Taster wählen --</option>'
        for butt in self.settings.buttons:
            if len(butt.name.strip()) > 0:
                opt_str += f'<option value="{butt.nmbr}">{butt.name}</option>\n'
        no_buttons = len(self.settings.buttons)
        for inp in self.settings.inputs:
            if (inp.type == 1) & (len(inp.name.strip()) > 0):
                opt_str += (
                    f'<option value="{inp.nmbr+no_buttons}">{inp.name}</option>\n'
                )
        page = page.replace('<option value="">-- Taster wählen --</option>', opt_str)

        opt_str = '<option value="">-- Schalter wählen --</option>'
        no_switches = 0
        for inp in self.settings.inputs:
            if (inp.type > 1) & (len(inp.name.strip()) > 0):
                no_switches += 1
                opt_str += (
                    f'<option value="{inp.nmbr+no_buttons}">{inp.name}</option>\n'
                )
        page = page.replace('<option value="">-- Schalter wählen --</option>', opt_str)
        if no_switches == 0:
            page = page.replace(
                '<select name="trigger_switch"',
                '<select name="trigger_switch" disabled',
            )

        opt_str = '<option value="">-- Ausgang oder LED wählen --</option>'
        for outp in self.settings.outputs:
            if len(outp.name.strip()) > 0:
                opt_str += f'<option value="{outp.nmbr}">{outp.name}</option>'
        for led in self.settings.leds:
            if led.nmbr == 0:
                opt_str += f'<option value="16">{led.name}</option>'
            elif len(led.name.strip()) > 0:
                opt_str += f'<option value="{led.nmbr + 16}">LED {led.name}</option>'
            else:
                opt_str += f'<option value="{led.nmbr + 16}">LED {led.nmbr}</option>'
        page = page.replace(
            '<option value="">-- Ausgang oder LED wählen --</option>', opt_str
        )

        opt_str = '<option value="">-- Modus wählen --</option>'
        md_lst = self.get_modes()
        for mod in md_lst:
            if self.event_code == 137:
                opt_str += f'<option value="{mod}">{md_lst[mod]}</option>'
            else:
                opt_str += f'<option value="{mod}">{md_lst[mod]}</option>'
        page = page.replace('<option value="">-- TrModus wählen --</option>', opt_str)
        opt_str = '<option value="">-- Merker wählen --</option>'
        for flg in self.settings.flags:
            if (self.event_code == 6) & (self.event_arg1 + self.event_arg2 == flg.nmbr):
                opt_str += f'<option value="{flg.nmbr}" selected>{flg.name}</option>\n'
            else:
                opt_str += f'<option value="{flg.nmbr}">{flg.name}</option>\n'
        for flg in self.settings.glob_flags:
            if (self.event_code == 6) & (
                self.event_arg1 + self.event_arg2 == flg.nmbr + 32
            ):
                opt_str += (
                    f'<option value="{flg.nmbr + 32}" selected>{flg.name}</option>\n'
                )
            else:
                opt_str += f'<option value="{flg.nmbr + 32}">{flg.name}</option>\n'
        page = page.replace('<option value="">-- TrMerker wählen --</option>', opt_str)
        if self.event_code == 6:
            if self.event_arg1 > self.event_arg2:
                page = page.replace(
                    '<option value="1">gesetzt</option>',
                    '<option value="1" selected>gesetzt</option>',
                )
            else:
                page = page.replace(
                    '<option value="2">rückgesetzt</option>',
                    '<option value="2" selected>rückgesetzt</option>',
                )

        opt_str = '<option value="">-- Befehl wählen --</option>'
        if len(self.settings.vis_cmds) > 0:
            for cmd in self.settings.vis_cmds:
                opt_str += f'<option value="{cmd.nmbr}">{cmd.name}</option>\n'
            page = page.replace(
                '<option value="">-- VKommando wählen --</option>', opt_str
            )
        elif SelTrgCodes["viscmd"] in self.triggers_dict.keys():
            page = page.replace(
                f'<option value="{SelTrgCodes["viscmd"]}">{self.triggers_dict[SelTrgCodes["viscmd"]]}',
                f'<option value="{SelTrgCodes["viscmd"]}" disabled>{self.triggers_dict[SelTrgCodes["viscmd"]]}',
            )

        opt_str = '<option value="">-- Befehl wählen --</option>'
        for cmd in self.settings.coll_cmds:
            opt_str += f'<option value="{cmd.nmbr}">{cmd.name}</option>\n'
        page = page.replace(
            '<option value="">-- TrCKommando wählen --</option>', opt_str
        )
        opt_str = '<option value="">-- Befehl wählen --</option>'
        if len(self.settings.dir_cmds) > 0:
            for cmd in self.settings.dir_cmds:
                opt_str += f'<option value="{cmd.nmbr}">{cmd.name}</option>\n'
            page = page.replace(
                '<option value="">-- DKommando wählen --</option>', opt_str
            )
        elif SelTrgCodes["dircmd"] in self.triggers_dict.keys():
            page = page.replace(
                f'<option value="{SelTrgCodes["dircmd"]}">{self.triggers_dict[SelTrgCodes["dircmd"]]}',
                f'<option value="{SelTrgCodes["dircmd"]}" disabled>{self.triggers_dict[SelTrgCodes["dircmd"]]}',
            )

        opt_str = '<option value="">-- Benutzer wählen --</option>'
        if len(self.settings.users) > 0:
            for usr in self.settings.users:
                if self.event_arg1 == usr.nmbr:
                    opt_str += f'<option value="{usr.nmbr}-{usr.type}" selected>{usr.name}</option>\n'
                else:
                    opt_str += (
                        f'<option value="{usr.nmbr}-{usr.type}">{usr.name}</option>\n'
                    )
            opt_str += f'<option value="255">Benutzer unbekannt / Fehler</option>\n'
            page = page.replace(
                '<option value="">-- Benutzer wählen --</option>', opt_str
            )
        elif SelTrgCodes["ekey"] in self.triggers_dict.keys():
            page = page.replace(
                f'<option value="{SelTrgCodes["ekey"]}">{self.triggers_dict[SelTrgCodes["ekey"]]}',
                f'<option value="{SelTrgCodes["ekey"]}" disabled>{self.triggers_dict[SelTrgCodes["ekey"]]}',
            )

        opt_str = '<option value="">-- Zähler wählen --</option>'
        max_cnt = []
        no_counters = 0
        for cnt in self.settings.logic:
            if cnt.type == 5:
                no_counters += 1
                max_cnt.append(self.settings.status[MirrIdx.LOGIC - 2 + cnt.nmbr * 3])
                if self.unit == cnt.nmbr:
                    opt_str += (
                        f'<option value="{cnt.nmbr}" selected>{cnt.name}</option>\n'
                    )
                else:
                    opt_str += f'<option value="{cnt.nmbr}">{cnt.name}</option>\n'
        page = page.replace('<option value="">-- TrZähler wählen --</option>', opt_str)
        page = page.replace(
            "max_count = [16, 16, 16, 16, 16, 16, 16, 16, 16, 16]",
            f"max_count = {max_cnt}",
        )
        if (no_counters == 0) & (SelTrgCodes["count"] in self.triggers_dict.keys()):
            page = page.replace(
                f'<option value="{SelTrgCodes["count"]}">{self.triggers_dict[SelTrgCodes["count"]]}',
                f'<option value="{SelTrgCodes["count"]}" disabled>{self.triggers_dict[SelTrgCodes["count"]]}',
            )
        page = self.activate_ui_elements(page, step)
        return page

    def activate_ui_elements(self, page: str, step: int) -> str:
        """Set javascript values according to sel automation."""
        if self.event_id == None:
            self.event_id = self.event_code
        page = page.replace("const trg_code = 0;", f"const trg_code = {self.event_id};")
        page = page.replace(
            "const trg_arg1 = 0;", f"const trg_arg1 = {self.event_arg1};"
        )
        page = page.replace(
            "const trg_arg2 = 0;", f"const trg_arg2 = {self.event_arg2};"
        )
        if self.event_id == 170:
            page = page.replace(
                'const trg_time = "";',
                f'const trg_time = "{self.src_rt - 200:02d}:{self.src_mod:02d}";',
            )
        return page

    def save_changed_automation(self, app, form_data, step):
        """Extract and set trigger part from edit form."""
        self.event_id = None
        if step == 0:
            self.src_rt = 0
            self.src_mod = 0
        self.event_code = self.automation.get_sel(form_data, "trigger_sel")
        if self.event_code in EventsSets[SelTrgCodes["logic"]]:
            if form_data["trigger_flag2"][0] == "1":
                self.event_arg1 = self.automation.get_sel(form_data, "trigger_flag")
                self.event_arg2 = 0
            else:
                self.event_arg1 = 0
                self.event_arg2 = self.automation.get_sel(form_data, "trigger_flag")
        elif self.event_code in EventsSets[SelTrgCodes["button"]]:
            self.event_arg1 = self.automation.get_sel(form_data, "trigger_button")
            self.event_arg2 = 0
            if form_data["trigger_shortlong"][0] == "1":
                self.event_code = 150
            elif form_data["trigger_shortlong"][0] == "2":
                self.event_code = 151
            else:
                self.event_code = 154
        elif self.event_code in EventsSets[SelTrgCodes["switch"]]:
            self.event_arg1 = self.automation.get_sel(form_data, "trigger_switch")
            self.event_arg2 = 0
            if form_data["trigger_onoff"][0] == "1":
                self.event_code = 152
            else:
                self.event_code = 153
        elif self.event_code in EventsSets[SelTrgCodes["dimm"]]:
            self.event_code = 149
            self.event_arg1 = self.automation.get_sel(form_data, "trigger_button")
            self.event_arg2 = 0
        elif self.event_code in EventsSets[SelTrgCodes["output"]]:
            self.event_code = 10
            if int(form_data["trigger_onoff"][0]) == 1:
                self.event_arg1 = self.automation.get_sel(form_data, "trigger_output")
                self.event_arg2 = 0
            else:
                self.event_arg1 = 0
                self.event_arg2 = self.automation.get_sel(form_data, "trigger_output")
        elif self.event_code in EventsSets[SelTrgCodes["dircmd"]]:
            self.event_code = 253
            self.event_arg1 = self.automation.get_sel(form_data, "trigger_dircmd")
            self.event_arg2 = 0
        elif self.event_code in EventsSets[SelTrgCodes["remote"]]:
            self.event_arg1 = self.automation.get_sel(form_data, "ir_high")
            self.event_arg2 = self.automation.get_sel(form_data, "ir_low")
        elif self.event_code in EventsSets[SelTrgCodes["collcmd"]]:
            self.src_rt = 250
            self.event_code = 50
            self.event_arg1 = self.automation.get_sel(form_data, "trigger_collcmd")
            self.event_arg2 = 0
        elif self.event_code in EventsSets[SelTrgCodes["viscmd"]]:
            self.src_rt = 199
            self.event_code = 31
            self.event_arg1 = int(form_data["trigger_viscmd"][0]) >> 8
            self.event_arg2 = int(form_data["trigger_viscmd"][0]) & 0xFF
        elif self.event_code in EventsSets[SelTrgCodes["mode"]]:
            self.src_rt = 250
            self.event_code = 137
            self.event_arg1 = 69
            self.event_arg2 = self.automation.get_sel(
                form_data, "trigger_mode"
            ) + self.automation.get_sel(form_data, "trigger_mode2")
        elif self.event_code in EventsSets[SelTrgCodes["move"]]:
            self.event_code = 40
            if self.automation.get_sel(form_data, "trigger_mov") == 2:
                self.event_code = 41
            self.event_arg1 = self.automation.get_sel(form_data, "sens_low_mov")
            if self.automation.get_sel(form_data, "trigger_mov") == 0:
                self.event_arg2 = 0
            else:
                self.event_arg2 = int(
                    self.automation.get_sel(form_data, "sens_high_mvl") / 10
                )
        elif self.event_code in EventsSets[SelTrgCodes["count"]]:
            self.event_id = 9
            self.event_code = 6
            cnt_no = self.automation.get_sel(form_data, "trigger_counter")
            self.event_arg1 = (
                95
                + (cnt_no - 1) * 16
                + self.automation.get_sel(form_data, "count_vals")
            )
            self.event_arg2 = 0
        elif self.event_code in EventsSets[SelTrgCodes["sensor"]]:
            self.event_code = self.automation.get_sel(form_data, "trigger_sensor")
            if self.event_code in [SelSensCodes["ad_1"], SelSensCodes["ad_2"]]:
                self.event_arg1 = self.automation.get_val(form_data, "sens_low_ad") * 25
                self.event_arg2 = (
                    self.automation.get_val(form_data, "sens_high_ad") * 25
                )
            if self.event_code in [SelSensCodes["temp_ext"], SelSensCodes["temp_int"]]:
                self.event_arg1 = self.sign2u7(
                    self.automation.get_sel(form_data, "sens_low_temp")
                )
                self.event_arg2 = self.sign2u7(
                    self.automation.get_sel(form_data, "sens_high_temp")
                )
            if self.event_code in [
                SelSensCodes["humid_ext"],
                SelSensCodes["humid_int"],
                SelSensCodes["airqual"],
            ]:
                self.event_arg1 = self.automation.get_sel(form_data, "sens_low_perc")
                self.event_arg2 = self.automation.get_sel(form_data, "sens_high_perc")
            if self.event_code in [
                SelSensCodes["wind"],
                SelSensCodes["wind_peak"],
            ]:
                self.event_arg1 = self.automation.get_sel(form_data, "sens_low_wind")
                self.event_arg2 = self.automation.get_sel(form_data, "sens_high_wind")
            if self.event_code in [
                SelSensCodes["light_ext"],
                SelSensCodes["light_int"],
            ]:
                self.event_arg1 = (
                    self.automation.get_sel(form_data, "sens_low_lux") / 10
                )
                self.event_arg2 = (
                    self.automation.get_sel(form_data, "sens_high_lux") / 10
                )
            if self.event_code in [SelSensCodes["rain"]]:
                self.event_arg1 = self.automation.get_sel(form_data, "trigger_rain")
                self.event_arg2 = 0

        elif self.event_code in EventsSets[SelTrgCodes["ekey"]]:
            self.event_arg1 = int(form_data["trigger_ekey"][0].split("-")[0])
            if self.event_arg1 == 255:
                self.event_arg2 = 255
            else:
                self.event_arg2 = self.automation.get_sel(form_data, "trigger_finger")
        elif self.event_code in EventsSets[SelTrgCodes["time"]]:
            self.value = form_data["time_vals"][0]
            time = self.value.split(":")
            self.src_rt = 200 + int(time[0])
            self.src_mod = int(time[1])
            day = self.automation.get_sel(form_data, "day_vals")
            month = self.automation.get_sel(form_data, "month_vals")
            self.event_arg1 = day
            self.event_arg2 = month
        elif self.event_code in EventsSets[SelTrgCodes["climate"]]:
            self.event_code += self.automation.get_sel(form_data, "clim_sens_select")
            self.event_arg1 = self.automation.get_sel(form_data, "clim_mode_select")
            self.event_arg2 = 0
        elif self.event_code in EventsSets[SelTrgCodes["system"]]:
            self.event_code = self.automation.get_sel(form_data, "trigger_sys")
            if self.event_code == 249:
                self.event_arg1 = 1
                self.event_arg2 = 0
            elif self.event_code == 12:
                self.event_arg1 = self.automation.get_sel(form_data, "supply_select")
                self.event_arg2 = 0
            elif self.event_code == 101:
                err_no = self.automation.get_sel(form_data, "syserr_no")
                self.event_arg1 = err_no >> 8
                self.event_arg2 = err_no & 0xFF
        if self.event_id == None:
            self.event_id = self.event_code
        self.automation.src_rt = self.src_rt
        self.automation.src_mod = self.src_mod
        self.automation.event_code = self.event_code
        self.name = self.event_name()
        self.parse()
        return

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

    def get_modes(self):
        """Return modes with user modes."""
        m1, m2 = self.automation.condition.get_selector_conditions()
        del m1[1]
        del m1[160]
        del m1[191]
        del m1[207]
        for md in m1:
            m1[md] = m1[md].replace("Modus '", "").replace("'", "")
        return m1

    def u2sign7(self, uint_in: int) -> int:
        """Transform unsigned to signed int7."""
        if uint_in > 60:
            return uint_in - 128
        return uint_in

    def sign2u7(self, sint_in: int) -> int:
        """Transform signed int7 to unsigned."""
        if sint_in < 0:
            return sint_in + 128
        return sint_in
