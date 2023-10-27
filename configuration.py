import logging
from pymodbus.utilities import checkCRC as ModbusCheckCRC
from pymodbus.utilities import computeCRC as ModbusComputeCRC
from const import IfDescriptor, MirrIdx, MirrIdx, SMGIdx, MODULE_CODES, CStatBlkIdx


class ModuleSettings:
    """Object with all module settings."""

    def __init__(self, module, rtr):
        """Fill all properties with module's values."""
        self.id = module._id
        self.name = module._name
        self.typ = module._typ
        self.type = module._type
        self.list = module.list
        self.status = module.status
        self.smg = module.build_smg()
        self.desc = rtr.descriptions
        self.logger = logging.getLogger(__name__)
        self.properties: dict = module.io_properties
        self.prop_keys = module.io_prop_keys
        self.cover_times = [0, 0, 0, 0, 0]
        self.blade_times = [0, 0, 0, 0, 0]
        self.get_io_interfaces()
        self.get_names()
        self.get_settings()
        self.get_descriptions()

    def get_io_interfaces(self):
        """Parse config files to extract names, etc."""
        self.leds = [IfDescriptor("", i + 1, 1) for i in range(self.properties["leds"])]
        self.buttons = [
            IfDescriptor("", i + 1, 1) for i in range(self.properties["buttons"])
        ]
        self.inputs = [
            IfDescriptor("", i + 1, 1) for i in range(self.properties["inputs"])
        ]
        self.outputs = [
            IfDescriptor("", i + 1, 1) for i in range(self.properties["outputs"])
        ]
        self.covers = [
            IfDescriptor("", i + 1, 0) for i in range(self.properties["covers"])
        ]
        self.dimmers = [
            IfDescriptor("", i + 1, -1) for i in range(self.properties["outputs_dimm"])
        ]
        self.flags: list[IfDescriptor] = []
        self.logic: list[IfDescriptor] = []
        self.messages: list[IfDescriptor] = []
        self.dir_cmds: list[IfDescriptor] = []
        self.vis_cmds: list[IfDescriptor] = []
        self.setvalues: list[IfDescriptor] = []
        self.ids: list[IfDescriptor] = []

    def get_settings(self) -> bool:
        """Get settings of Habitron module."""
        conf = self.status
        if conf == "":
            return False

        self.hw_version = (
            conf[MirrIdx.MOD_SERIAL : MirrIdx.MOD_SERIAL + 16]
            .decode("iso8859-1")
            .strip()
        )
        self.sw_version = (
            conf[MirrIdx.SW_VERSION : MirrIdx.SW_VERSION + 22]
            .decode("iso8859-1")
            .strip()
        )
        self.supply_prio = conf[MirrIdx.SUPPLY_PRIO]
        self.displ_contr = conf[MirrIdx.DISPL_CONTR]
        self.displ_time = conf[MirrIdx.MOD_LIGHT_TIM]
        inp_state = int.from_bytes(
            conf[MirrIdx.SWMOD_1_8 : MirrIdx.SWMOD_1_8 + 3], "little"
        )
        for inp in self.inputs:
            if inp_state & (0x01 << (inp.nmbr - 1)) > 0:
                inp.type *= 2  # switch

        # pylint: disable-next=consider-using-enumerate
        for c_idx in range(len(self.covers)):
            cm_idx = c_idx
            if self.type[:16] == "Smart Controller":
                cm_idx -= 2
                if cm_idx < 0:
                    cm_idx += 5
            if (
                conf[MirrIdx.COVER_SETTINGS] & (0x01 << cm_idx) > 0
            ):  # binary flag for shutters
                self.cover_times[c_idx] = int(conf[MirrIdx.COVER_T + cm_idx]) / 10
                self.blade_times[c_idx] = int(conf[MirrIdx.BLAD_T + cm_idx]) / 10
                polarity = (conf[MirrIdx.COVER_POL] & (0x01 << cm_idx) == 0) * 2 - 1
                tilt = 1 + (self.blade_times[c_idx] > 0)
                pol = polarity * tilt  # +-1 for shutters, +-2 for blinds
                cname = self.outputs[2 * c_idx].name.strip()
                cname = cname.replace("auf", "")
                cname = cname.replace("ab", "")
                cname = cname.replace("auf", "")
                cname = cname.replace("zu", "")
                self.covers[c_idx] = IfDescriptor(cname.strip(), c_idx + 1, pol)
                self.outputs[2 * c_idx].type = -10  # disable light output
                self.outputs[2 * c_idx + 1].type = -10
        return True

    def set_settings(self, status):
        """Restore settings to module."""
        status = replace_bytes(
            status,
            (self.name + " " * (32 - len(self.name))).encode("iso8859-1"),
            MirrIdx.MOD_NAME,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.displ_contr)),
            MirrIdx.DISPL_CONTR,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.displ_time)),
            MirrIdx.MOD_LIGHT_TIM,
        )
        if self.supply_prio == "24V":
            byte_supply = b"B"
        else:
            byte_supply = b"A"
        status = replace_bytes(
            status,
            byte_supply,
            MirrIdx.SUPPLY_PRIO,
        )
        inp_state = 0
        for inp in self.inputs:
            if abs(inp.type) > 1:  # switch
                inp_state = inp_state | (0x01 << (inp.nmbr - 1))
        inp_bytes = (
            chr(inp_state & 0xFF)
            + chr((inp_state >> 8) & 0xFF)
            + chr((inp_state >> 16) & 0xFF)
        ).encode("iso8859-1")
        status = replace_bytes(
            status,
            inp_bytes,
            MirrIdx.SWMOD_1_8,
        )
        return status

    def get_names(self) -> bool:
        """Get summary of Habitron module."""
        conf = self.list
        no_lines = int.from_bytes(conf[:2], "little")
        conf = conf[4 : len(conf)]  # Strip 4 header bytes
        if len(conf) == 0:
            return False
        for _ in range(no_lines):
            if conf == b"":
                break
            line_len = int(conf[5]) + 5
            line = conf[0:line_len]
            event_code = int(line[2])
            if event_code == 235:  # Beschriftung
                text = line[8:-1]
                text = text.decode("iso8859-1")
                text = text.strip()
                arg_code = int(line[3])
                if int(line[0]) == 252:
                    # Finger ids
                    self.ids.append(IfDescriptor(text, arg_code, 0))
                elif int(line[0]) == 253:
                    # Description of commands
                    self.dir_cmds.append(IfDescriptor(text, arg_code, 0))
                elif int(line[0]) == 254:
                    # Description of messages
                    self.messages.append(IfDescriptor(text, arg_code, 0))
                elif int(line[0]) == 255:
                    try:
                        if arg_code in range(10, 18):
                            if self.type == "Smart Controller Mini":
                                if arg_code in range(11, 12):
                                    self.buttons[arg_code - 10] = IfDescriptor(
                                        text, arg_code - 9, 1
                                    )
                            elif self.type[:16] == "Smart Controller":
                                # Description of module buttons
                                self.buttons[arg_code - 10] = IfDescriptor(
                                    text, arg_code - 9, 1
                                )
                            else:
                                self.inputs[arg_code - 10].name = text
                                self.inputs[arg_code - 10].nmbr = arg_code - 9
                        elif arg_code in range(18, 26):
                            # Description of module LEDs
                            self.leds[arg_code - 18] = IfDescriptor(
                                text, arg_code - 17, 0
                            )
                        elif arg_code in range(40, 50):
                            # Description of Inputs
                            if self.type == "Smart Controller Mini":
                                if arg_code >= 44:
                                    self.inputs[arg_code - 44].name = text
                                    self.inputs[arg_code - 44].nmbr = arg_code - 43
                            else:
                                self.inputs[arg_code - 40].name = text
                                self.inputs[arg_code - 40].nmbr = arg_code - 39
                        elif arg_code in range(110, 120):
                            # Description of logic units
                            self.logic.append(IfDescriptor(text, arg_code - 109, 5))
                        elif arg_code in range(120, 136):
                            # Description of flags
                            self.flags.append(IfDescriptor(text, arg_code - 119, 0))
                        elif self.type[0:9] == "Smart Out":
                            # Description of outputs in Out modules
                            self.outputs[arg_code - 60] = IfDescriptor(
                                text, arg_code - 59, 1
                            )
                        else:
                            # Description of outputs
                            self.outputs[arg_code - 60].name = text
                    except Exception as err_msg:
                        self.logger.error(
                            f"Parsing of names for module {self.name} failed: {err_msg}: Code {arg_code}, Text {text}"
                        )

            conf = conf[line_len : len(conf)]  # Strip processed line
        if self.type == "Smart Controller Mini":
            return True
        if self.type[:16] == "Smart Controller":
            self.dimmers[0].name = self.outputs[10].name
            self.dimmers[1].name = self.outputs[11].name
            self.outputs[10].type = 2
            self.outputs[11].type = 2
        return True

    def get_descriptions(self) -> str | None:
        """Get descriptions of commands, etc."""
        resp = self.desc.encode("iso8859-1")

        no_lines = int.from_bytes(resp[:2], "little")
        resp = resp[4:]
        for _ in range(no_lines):
            if resp == b"":
                break
            line_len = int(resp[8]) + 9
            line = resp[:line_len]
            content_code = int.from_bytes(line[1:3], "little")
            entry_no = int(line[3])
            entry_name = line[9:line_len].decode("iso8859-1").strip()
            if content_code == 767:  # FF 02: global flg (Merker)
                pass
            elif content_code == 1023:  # FF 03: collective commands (Sammelbefehle)
                pass
            elif content_code == 2303:  # FF 08: alarm commands
                pass
            elif self.id == line[1]:
                # entry for local module
                if int(line[2]) == 1:
                    # local flag (Merker)
                    self.flags.append(IfDescriptor(entry_name, entry_no, 0))
                elif int(line[2]) == 4:
                    # local visualization command
                    entry_no = int.from_bytes(resp[3:5], "little")
                    self.vis_cmds.append(IfDescriptor(entry_name, entry_no, 0))
                elif int(line[2]) == 5:
                    # logic element, if needed to fix unexpected error
                    self.logic.append(IfDescriptor(entry_name, entry_no, 0))
                # 6: Logik input: line[3] logic unit, line[4] input no
                # elif int(line[2]) == 7:
                # Group name
            resp = resp[line_len:]
        if (len(self.logic) > 0) & (not ("logic" in self.prop_keys)):
            self.properties["logic"] = len(self.logic)
            self.properties["no_keys"] += 1
            self.prop_keys.append("logic")
        if (len(self.flags) > 0) & (not ("flags" in self.prop_keys)):
            self.properties["flags"] = len(self.flags)
            self.properties["no_keys"] += 1
            self.prop_keys.append("flags")
        if (len(self.dir_cmds) > 0) & (not ("dir_cmds" in self.prop_keys)):
            self.properties["dir_cmds"] = len(self.dir_cmds)
            self.properties["no_keys"] += 1
            self.prop_keys.append("dir_cmds")
        if (len(self.vis_cmds) > 0) & (not ("vis_cmds" in self.prop_keys)):
            self.properties["vis_cmds"] = len(self.vis_cmds)
            self.properties["no_keys"] += 1
            self.prop_keys.append("vis_cmds")


class RouterSettings:
    """Object with all router settings."""

    def __init__(self, rtr):
        """Fill all properties with module's values."""
        self.id = rtr._id
        self.name = rtr._name
        self.type = "Smart Router"
        self.status = rtr.status
        self.smr = rtr.smr
        self.desc = rtr.descriptions
        self.logger = logging.getLogger(__name__)
        self.channels = rtr.channels
        self.timeout = rtr.timeout
        self.groups = rtr.groups
        self.mode_dependencies = rtr.mode_dependencies
        self.user_modes = rtr.user_modes
        self.serial = rtr.serial
        self.day_night = rtr.day_night
        self.version = rtr.version
        self.glob_flags: list[IfDescriptor] = []
        self.groups: list[IfDescriptor] = []
        self.coll_cmds: list[IfDescriptor] = []
        self.chan_list = []
        self.module_grp = []
        self.max_group = 0
        self.get_definitions()
        self.get_glob_descriptions()
        self.properties: dict = rtr.properties
        self.prop_keys = rtr.prop_keys

    def get_definitions(self) -> None:
        """Parse router smr info and set values."""
        # self.group_list = []
        ptr = 1
        max_mod_no = 0
        for ch_i in range(4):
            count = self.smr[ptr]
            self.chan_list.append(sorted(self.smr[ptr + 1 : ptr + count + 1]))
            # pylint: disable-next=nested-min-max
            if count > 0:
                max_mod_no = max(max_mod_no, *self.chan_list[ch_i])
            ptr += 1 + count
        ptr += 2
        grp_cnt = self.smr[ptr - 1]
        self.max_group = max(list(self.smr[ptr : ptr + grp_cnt]))
        # self.group_list: list[int] = [[]] * (max_group + 1)
        for mod_i in range(max_mod_no):
            grp_no = int(self.smr[ptr + mod_i])
            self.module_grp.append(grp_no)
        ptr += 2 * grp_cnt + 1  # groups, group dependencies, timeout
        str_len = self.smr[ptr]
        self.name = self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()
        ptr += str_len + 1
        str_len = self.smr[ptr]
        self.user1_name = (
            self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()
        )
        ptr += str_len + 1
        str_len = self.smr[ptr]
        self.user2_name = (
            self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()
        )
        ptr += str_len + 1
        str_len = self.smr[ptr]
        self.serial = self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()
        ptr += str_len + 71  # Korr von Hand, vorher 71 + 1
        str_len = self.smr[ptr]
        self.version = self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()

    def get_glob_descriptions(self) -> str | None:
        """Get descriptions of commands, etc."""
        resp = self.desc.encode("iso8859-1")

        no_lines = int.from_bytes(resp[:2], "little")
        resp = resp[4:]
        for _ in range(no_lines):
            if resp == b"":
                break
            line_len = int(resp[8]) + 9
            line = resp[:line_len]
            content_code = int.from_bytes(line[1:3], "little")
            entry_no = int(line[3])
            entry_name = line[9:line_len].decode("iso8859-1").strip()
            if content_code == 767:  # FF 02: global flg (Merker)
                self.glob_flags.append(IfDescriptor(entry_name, entry_no, 0))
            elif content_code == 1023:  # FF 03: collective commands (Sammelbefehle)
                self.coll_cmds.append(IfDescriptor(entry_name, entry_no, 0))
            elif content_code == 2047:  # FF 07: group names
                self.groups.append(IfDescriptor(entry_name, entry_no, 0))
            elif content_code == 2303:  # FF 08: alarm commands
                pass
            resp = resp[line_len:]


def replace_bytes(in_bytes: bytes, repl_bytes: bytes, idx: int) -> bytes:
    """Replaces bytes array from idx:idx+len(in_bytes)."""
    return in_bytes[:idx] + repl_bytes + in_bytes[idx + len(repl_bytes) :]
