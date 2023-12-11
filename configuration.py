import logging
from copy import deepcopy as dpcopy
from pymodbus.utilities import checkCRC as ModbusCheckCRC
from pymodbus.utilities import computeCRC as ModbusComputeCRC
from const import (
    IfDescriptor,
    MirrIdx,
    MirrIdx,
    SMGIdx,
    MODULE_CODES,
    CStatBlkIdx,
    RtStatIIdx,
    FingerNames,
)
from automation import AutomationDefinition, AutomationsSet


class ModuleSettings:
    """Object with all module settings."""

    def __init__(self, module, rtr):
        """Fill all properties with module's values."""
        self.id = module._id
        self.module = module
        self.name = dpcopy(module._name)
        self.typ = module._typ
        self.type = module._type
        self.list = dpcopy(module.list)
        self.status = dpcopy(module.status)
        self.smg = dpcopy(module.build_smg())
        self.desc = dpcopy(rtr.descriptions)
        self.logger = logging.getLogger(__name__)
        self.properties: dict = module.io_properties
        self.prop_keys = module.io_prop_keys
        self.cover_times = [0, 0, 0, 0, 0]
        self.blade_times = [0, 0, 0, 0, 0]
        self.get_io_interfaces()
        self.get_names()
        self.get_settings()
        self.get_descriptions()
        self.automtns_def = AutomationsSet(self)
        self.group = dpcopy(rtr.groups[self.id])

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
        self.users: list[IfDescriptor] = []
        self.fingers: list[IfDescriptor] = []
        self.glob_flags: list[IfDescriptor] = []
        self.coll_cmds: list[IfDescriptor] = []

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
        if self.displ_time == 0:
            if self.type == "Smart Controller Mini":
                self.displ_time = 100
        self.temp_ctl = conf[MirrIdx.CLIM_SETTINGS]
        self.temp_1_2 = conf[MirrIdx.TMP_CTL_MD]
        self.t_short = self.status[MirrIdx.T_SHORT] * 10
        self.t_long = self.status[MirrIdx.T_LONG] * 10
        self.t_dimm = self.status[MirrIdx.T_DIM]
        inp_state = int.from_bytes(
            conf[MirrIdx.SWMOD_1_8 : MirrIdx.SWMOD_1_8 + 3], "little"
        )
        for inp in self.inputs:
            nmbr = inp.nmbr - 1 + len(self.buttons)
            if inp_state & (0x01 << (nmbr)) > 0:
                inp.type *= 2  # switch

        # pylint: disable-next=consider-using-enumerate
        covr_pol = int.from_bytes(
            conf[MirrIdx.COVER_POL : MirrIdx.COVER_POL + 2], "little"
        )
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
                # polarity defined per output, 2 per cover
                polarity = (covr_pol & (0x01 << (2 * cm_idx)) == 0) * 2 - 1
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
        for l_idx in range(10):
            if conf[MirrIdx.LOGIC + 3 * l_idx] == 5:
                # counter found
                self.logic.append(IfDescriptor(f"Counter_{l_idx + 1}", l_idx + 1, 5))
        return True

    def set_module_settings(self, status: bytes) -> bytes:
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
        status = replace_bytes(
            status,
            int.to_bytes(int(self.temp_ctl)),
            MirrIdx.CLIM_SETTINGS,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.temp_1_2)),
            MirrIdx.TMP_CTL_MD,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(float(self.t_short) / 10)),
            MirrIdx.T_SHORT,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(float(self.t_long) / 10)),
            MirrIdx.T_LONG,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.t_dimm)),
            MirrIdx.T_DIM,
        )
        if self.supply_prio == "230":
            byte_supply_prio = b"N"
        else:
            byte_supply_prio = b"B"
        status = replace_bytes(
            status,
            byte_supply_prio,
            MirrIdx.SUPPLY_PRIO,
        )
        inp_state = 0
        no_btns = len(self.buttons)
        for inp in self.inputs:
            if abs(inp.type) > 1:  # switch
                inp_state = inp_state | (0x01 << (inp.nmbr + no_btns - 1))
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
        outp_state = 0
        covr_pol = 0
        for c_idx in range(len(self.covers)):
            cm_idx = c_idx
            if self.type[:16] == "Smart Controller":
                cm_idx -= 2
                if cm_idx < 0:
                    cm_idx += 5
            if self.outputs[2 * c_idx].type == -10:
                outp_state = outp_state | (0x01 << cm_idx)
            status = replace_bytes(
                status,
                int.to_bytes(int(self.cover_times[c_idx] * 10)),
                MirrIdx.COVER_T + cm_idx,
            )
            status = replace_bytes(
                status,
                int.to_bytes(int(self.blade_times[c_idx] * 10)),
                MirrIdx.BLAD_T + cm_idx,
            )
            # Todo: Polaritiy bei RC, Cover 0 kommt nicht an, Cover 2-4 OK
            if self.covers[c_idx].type < 0:
                covr_pol = covr_pol | (0x01 << (2 * cm_idx))
            else:
                covr_pol = covr_pol | (0x01 << (2 + cm_idx + 1))

        outp_bytes = (chr(outp_state & 0xFF)).encode("iso8859-1")
        status = replace_bytes(
            status,
            outp_bytes,
            MirrIdx.COVER_SETTINGS,
        )
        status = replace_bytes(
            status,
            f"{chr(covr_pol & 0xFF)}{chr(covr_pol >> 8)}".encode("iso8859-1"),
            MirrIdx.COVER_POL,
        )

        # Clear all logic entries mode
        for l_idx in range(10):
            status = replace_bytes(
                status,
                b"\0",
                MirrIdx.LOGIC + 3 * l_idx,
            )
        for lgk in self.logic:
            status = replace_bytes(
                status,
                int.to_bytes(lgk.type),
                MirrIdx.LOGIC + 3 * (lgk.nmbr - 1),
            )
        return status

    def get_names(self) -> bool:
        """Get summary of Habitron module."""

        self.all_fingers = {}
        list = self.list
        no_lines = int.from_bytes(list[:2], "little")
        list = list[4 : len(list)]  # Strip 4 header bytes
        if len(list) == 0:
            return False
        for _ in range(no_lines):
            if list == b"":
                break
            line_len = int(list[5]) + 5
            line = list[0:line_len]
            event_code = int(line[2])
            if event_code == 235:  # Beschriftung
                text = line[8:]
                text = text.decode("iso8859-1")
                text = text.strip()
                arg_code = int(line[3])
                if int(line[0]) == 252:
                    # Finger users: user, bitmap of fingers as type
                    user_id = int(line[1])
                    f_map = int(line[4]) * 256 + int(line[3])
                    self.users.append(IfDescriptor(text, user_id, f_map))
                    self.all_fingers[user_id]: list[IfDescriptor] = []
                    for fi in range(10):
                        if f_map & (1 << fi):
                            self.all_fingers[user_id].append(
                                IfDescriptor(FingerNames[fi], fi + 1, user_id)
                            )
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
                                if arg_code in range(10, 12):
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
                            if self.type[0:9] != "Smart Out":
                                self.leds[arg_code - 18] = IfDescriptor(
                                    text, arg_code - 17, 0
                                )
                        elif arg_code in range(40, 50):
                            # Description of Inputs
                            if self.type == "Smart Controller Mini":
                                if arg_code in range(44, 48):
                                    self.inputs[arg_code - 44].name = text
                                    self.inputs[arg_code - 44].nmbr = arg_code - 43
                            else:
                                self.inputs[arg_code - 40].name = text
                                self.inputs[arg_code - 40].nmbr = arg_code - 39
                        elif arg_code in range(110, 120):
                            # Description of logic units
                            for lgc in self.logic:
                                if lgc.nmbr == arg_code - 109:
                                    lgc.name = text
                                    break
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

            list = list[line_len : len(list)]  # Strip processed line

        if self.type == "Smart Controller Mini":
            return True
        if self.type[:16] == "Smart Controller":
            self.dimmers[0].name = self.outputs[10].name
            self.dimmers[1].name = self.outputs[11].name
            self.outputs[10].type = 2
            self.outputs[11].type = 2
            return True
        if self.type == "Fanekey":
            self.users_sel = 0
            self.module.org_fingers = dpcopy(
                self.all_fingers
            )  # stores the active settings
            if len(self.users) > 0:
                self.fingers = self.all_fingers[self.users[self.users_sel].nmbr]
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
                self.glob_flags.append(IfDescriptor(entry_name, entry_no, 0))
            elif content_code == 1023:  # FF 03: collective commands (Sammelbefehle)
                self.coll_cmds.append(IfDescriptor(entry_name, entry_no, 0))
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
                    # logic element, needed if not stored in smc
                    for lgc in self.logic:
                        if lgc.nmbr == entry_no:
                            lgc.name = entry_name
                            break
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
        if (len(self.users) > 0) & (not ("users" in self.prop_keys)):
            self.properties["users"] = len(self.users)
            self.properties["no_keys"] += 1
            self.prop_keys.append("users")

    def format_smc(self, buf: bytes) -> str:
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

    async def update_ekey_entries(self):
        """Check for differences in users/fingers and delete if needed."""
        if not ("org_fingers" in dir(self.module)):
            self.module.org_fingers = {}
        org_fingers = self.module.org_fingers
        new_fingers = self.all_fingers
        usr_nmbrs = []
        for u_i in range(len(self.users)):
            usr_nmbrs.append(self.users[u_i].nmbr)
        for usr_id in org_fingers.keys():
            if not usr_id in new_fingers.keys():
                self.response = await self.module.hdlr.del_ekey_entry(usr_id, 255)
                self.logger.info(f"User {usr_id} deleted from ekey data base")
        for usr_id in org_fingers.keys():
            new_usr_fngr_ids = []
            for fngr_id in range(len(new_fingers[usr_id])):
                new_usr_fngr_ids.append(new_fingers[usr_id][fngr_id].nmbr)
            for fngr_id in range(len(org_fingers[usr_id])):
                org_finger = org_fingers[usr_id][fngr_id].nmbr
                if not org_finger in new_usr_fngr_ids:
                    self.response = await self.module.hdlr.del_ekey_entry(
                        usr_id, org_finger
                    )
                    self.logger.info(
                        f"Finger {org_finger} of user {usr_id} deleted from ekey data base"
                    )
        for usr_id in new_fingers.keys():
            f_msk = 0
            for fngr in new_fingers[usr_id]:
                f_msk = f_msk | 1 << (fngr.nmbr - 1)
            self.users[usr_nmbrs.index(usr_id)].type = f_msk

    async def set_list(self):
        """Store config entries to list and send to module."""
        list_lines = self.format_smc(self.list).split("\n")
        if self.module._typ == b"\x1e\x01":
            await self.update_ekey_entries()

        new_list = []
        new_line = ""
        for lchr in list_lines[0].split(";")[:-1]:
            new_line += chr(int(lchr))
        new_list.append(new_line)
        for line in list_lines[1:]:
            if len(line) > 0:
                tok = line.split(";")
                if (tok[0] != "252") & (tok[0] != "253") & (tok[0] != "255"):
                    new_line = ""
                    for lchr in line.split(";")[:-1]:
                        new_line += chr(int(lchr))
                    new_list.append(new_line)
        for dir_cmd in self.dir_cmds:
            desc = dir_cmd.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                new_list.append(f"\xfd\0\xeb{chr(dir_cmd.nmbr)}\1\x23\0\xeb" + desc)
        for btn in self.buttons:
            desc = btn.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                new_list.append(f"\xff\0\xeb{chr(9 + btn.nmbr)}\1\x23\0\xeb" + desc)
        for led in self.leds:
            desc = led.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                new_list.append(f"\xff\0\xeb{chr(17 + led.nmbr)}\1\x23\0\xeb" + desc)
        for inpt in self.inputs:
            desc = inpt.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                new_list.append(f"\xff\0\xeb{chr(39 + inpt.nmbr)}\1\x23\0\xeb" + desc)
        for outpt in self.outputs:
            desc = outpt.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                new_list.append(f"\xff\0\xeb{chr(59 + outpt.nmbr)}\1\x23\0\xeb" + desc)
        for lgc in self.logic:
            desc = lgc.name
            desc += " " * (32 - len(desc))
            new_list.append(f"\xff\0\xeb{chr(109 + lgc.nmbr)}\1\x23\0\xeb" + desc)
        for flg in self.flags:
            desc = flg.name
            desc += " " * (32 - len(desc))
            new_list.append(f"\xff\0\xeb{chr(119 + flg.nmbr)}\1\x23\0\xeb" + desc)
        for uid in self.users:
            desc = uid.name
            fgr_low = abs(uid.type) & 0xFF
            fgr_high = abs(uid.type) >> 8
            desc += " " * (32 - len(desc))
            new_list.append(
                f"\xfc{chr(uid.nmbr)}\xeb{chr(fgr_low)}{chr(fgr_high)}\x23\0\xeb" + desc
            )
        no_lines = len(new_list) - 1
        no_chars = 0
        for line in new_list:
            no_chars += len(line)
        new_list[
            0
        ] = f"{chr(no_lines & 0xFF)}{chr(no_lines >> 8)}{chr(no_chars & 0xFF)}{chr(no_chars >> 8)}"
        list_bytes = ""
        for line in new_list:
            list_bytes += line
        list_bytes = list_bytes.encode("iso8859-1")
        return list_bytes

    async def teach_new_finger(self, app, user_id, finger_id):
        """Teach new finger and add to fingers."""
        settings = app["settings"]
        res = await settings.module.hdlr.set_ekey_teach_mode(user_id, finger_id, 30)
        if res == "OK":
            settings.all_fingers[user_id].append(
                IfDescriptor(FingerNames[finger_id - 1], finger_id, user_id)
            )
            app["settings"] = settings


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
        # self.groups = rtr.groups
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

    def set_glob_descriptions(self) -> str | None:
        """Add new descriptions into description string."""
        resp = self.desc.encode("iso8859-1")
        desc = resp[:4].decode("iso8859-1")
        no_lines = int.from_bytes(resp[:2], "little")
        line_no = 0
        resp = resp[4:]
        # Remove all global flags, coll commands, and group names
        # Leave rest unchanged
        for _ in range(no_lines):
            if resp == b"":
                break
            line_len = int(resp[8]) + 9
            line = resp[:line_len]
            content_code = int.from_bytes(line[1:3], "little")
            if not (content_code in [767, 1023, 2047]):
                desc += line.decode("iso8859-1")
                line_no += 1
            resp = resp[line_len:]
        for flg in self.glob_flags:
            desc += f"\x01\xff\x02{chr(flg.nmbr)}\x00\x00\x00\x00{chr(len(flg.name))}{flg.name}"
            line_no += 1
        for cmd in self.coll_cmds:
            desc += f"\x01\xff\x03{chr(cmd.nmbr)}\x00\x00\x00\x00{chr(len(cmd.name))}{cmd.name}"
            line_no += 1
        for grp in self.groups:
            desc += f"\x01\xff\x07{chr(grp.nmbr)}\x00\x00\x00\x00{chr(len(grp.name))}{grp.name}"
            line_no += 1
        return chr(line_no & 0xFF) + chr(line_no >> 8) + desc[2:]


def replace_bytes(in_bytes: bytes, repl_bytes: bytes, idx: int) -> bytes:
    """Replaces bytes array from idx:idx+len(in_bytes)."""
    return in_bytes[:idx] + repl_bytes + in_bytes[idx + len(repl_bytes) :]
