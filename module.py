import logging
import datetime
from copy import deepcopy as dpcopy
from const import MirrIdx, SMGIdx, MODULE_CODES, CStatBlkIdx, HA_EVENTS
from configuration import ModuleSettings, ModuleSettingsLight
from messages import calc_crc


class HbtnModule:
    """Habitron module object, holds complete status."""

    def __init__(self, mod_id: int, chan: int, rt_id: int, hdlr, api_srv) -> None:
        self._id: int = mod_id
        self._channel: int = chan
        self.rt_id = rt_id
        self.logger = logging.getLogger(__name__)
        self._name = ""
        self._typ: bytes = b""
        self._type = ""
        self._serial: str = ""
        self.api_srv = api_srv
        self.hdlr = hdlr

        self.status: bytes = b""  # full mirror, holds module settings
        self.compact_status: bytes = b""  # compact status, subset
        self.smg_upload: bytes = b""  # buffer for SMG upload
        self.smg_crc = 0
        self.list: bytes = b""  # SMC information: labels, commands
        self.list_upload: bytes = b""  # buffer for SMC upload
        self.settings = None

    async def initialize(self):
        """Get full module status"""
        self.hdlr.initialize(self)
        await self.hdlr.get_module_status(self._id)
        self.comp_status = self.get_status(False)
        self.calc_SMG_crc(self.build_smg())

        self._name = (
            self.status[MirrIdx.MOD_NAME : MirrIdx.MOD_NAME + 32]
            .decode("iso8859-1")
            .strip()
        )
        self._typ = self.status[MirrIdx.MOD_DESC : MirrIdx.MOD_DESC + 2]
        self._type = MODULE_CODES[self._typ.decode("iso8859-1")]

        self.list = await self.hdlr.get_module_list(self._id)
        self.calc_SMC_crc(self.list)
        self.io_properties, self.io_prop_keys = self.get_io_properties()
        self._serial = await self.get_serial()
        await self.cleanup_descriptions()

        self.logger.debug(f"Module {self._name} at {self._id} initialized")

    async def get_serial(self):
        """Get serial no from status, if not available, generate and set."""
        serial = (
            self.status[MirrIdx.MOD_SERIAL : MirrIdx.MOD_SERIAL + 16]
            .decode("iso8859-1")
            .strip()
        )
        if len(serial) == 0 or serial[0] == "\x00":
            serial = await self.hdlr.get_module_serial()
            if len(serial) > 0:
                return serial
            cont_serial = self._id + 800000
            year = datetime.date.today().year - 2000
            week = datetime.datetime.now().isocalendar().week
            serial = (
                f"{self._typ[0]:03}{self._typ[1]:03}{year:02}{week:02}{cont_serial:06}"
            )
            # set serial in module
            await self.hdlr.set_module_serial(serial)
        return serial

    def get_sw_version(self):
        """Get software version."""
        return (
            self.status[MirrIdx.SW_VERSION : MirrIdx.SW_VERSION + 22]
            .decode("iso8859-1")
            .strip()
        )

    def get_rtr(self):
        """Return router object."""
        return self.api_srv.routers[self.rt_id - 1]

    def get_group(self) -> int:
        """Return own group from router."""
        return self.get_rtr().groups[self._id]

    def get_group_name(self) -> str:
        """Return own group from router."""
        rtr = self.get_rtr()
        return rtr.get_group_name(rtr.groups[self._id])

    def get_smc_crc(self) -> int:
        """Return smc crc from status."""
        return int.from_bytes(self.status[MirrIdx.SMC_CRC : MirrIdx.SMC_CRC + 2], "big")

    def set_smc_crc(self, crc: int):
        """Store new smc crc into status."""
        crc_str = (chr((crc - (crc & 0xFF)) >> 8) + chr(crc & 0xFF)).encode("iso8859-1")
        self.status = (
            self.status[: MirrIdx.SMC_CRC]
            + crc_str
            + self.status[MirrIdx.SMC_CRC + 2 :]
        )

    def get_status(self, direct: bool) -> bytes:
        """Return status, if direct == False: compacted."""
        if direct:
            return self.status
        compact_status = b""
        for i0, i1 in CStatBlkIdx:
            compact_status += self.status[i0:i1]
        return compact_status

    def get_module_code(self) -> bytes:
        """Return Habitron module code."""
        return self._typ

    def get_settings(self):
        """Return settings part of mirror"""
        return self.status[MirrIdx.T_SHORT : MirrIdx.T_SHORT + 17]

    def has_automations(self) -> bool:
        """Return True if automations are allowed."""
        return (self._typ[0] in [1, 10]) or (self._typ == b"\x32\x01")

    def swap_mirr_cover_idx(self, mirr_idx: int) -> int:
        """Return cover index from mirror index (0..2 -> 2..4)."""
        cvr_idx = mirr_idx
        if self._typ[0] != 1:
            return cvr_idx
        cvr_idx += 2
        if cvr_idx > 4:
            cvr_idx -= 5
        return cvr_idx

    def compare_status(
        self, stat1: bytes, stat2: bytes, diff_idx: list[int], idx: int
    ) -> list[int]:
        """Find updates fields."""
        for x, y in zip(stat1, stat2):
            if x != y:
                diff_idx.append(idx)
            idx += 1
        return diff_idx

    def update_status(self, new_status: bytes):
        """Saves new mirror status and returns differences."""

        if self.status == new_status:
            return []
        block_list = []
        update_info = []
        i_diff = []

        # print(f"Module update {self._id}")
        if self._type in [
            "Smart Nature",
            "FanGSM",
            "FanM-Bus",
            "Smart In 8/24V",
            "Smart In 8/24V-1",
            "Smart In 8/230V",
            "Fanekey",
        ]:
            pass  # Don't track update changes for these modules
        else:
            if self._type in [
                "Smart Detect 180",
                "Smart Detect 180-2",
                "Smart Detect 360",
            ]:
                i0 = MirrIdx.LUM
                i1 = MirrIdx.MOV + 1
            elif self._type in [
                "Smart Out 8/R",
                "Smart Out 8/R-1",
                "Smart Out 8/R-2",
                "Smart Out 8/T",
            ]:
                block_list = [
                    MirrIdx.LUM,
                    MirrIdx.TEMP_ROOM,
                    MirrIdx.TEMP_PWR,
                    MirrIdx.TEMP_EXT,
                ]
                i0 = MirrIdx.DIM_1
                i1 = MirrIdx.T_SHORT  # includes BLAD_POS
            else:  # Controller modules
                block_list = [
                    MirrIdx.HUM,
                    MirrIdx.AQI,
                    MirrIdx.LUM,
                    MirrIdx.TEMP_ROOM,
                    MirrIdx.TEMP_PWR,
                    MirrIdx.TEMP_EXT,
                ]
                im0 = MirrIdx.MODE
                im1 = MirrIdx.MODE + 1
                i0 = MirrIdx.DIM_1
                i1 = MirrIdx.T_SHORT
                i2 = MirrIdx.LOGIC
                i3 = MirrIdx.FLAG_LOC + 2
                i_diff = self.compare_status(
                    self.status[i2:i3], new_status[i2:i3], i_diff, i2
                )
                i_diff = self.compare_status(
                    self.status[im0:im1], new_status[im0:im1], i_diff, im0
                )
            i_diff = self.compare_status(
                self.status[i0:i1], new_status[i0:i1], i_diff, i0
            )
            for i_d in i_diff:
                if i_d not in block_list:
                    ev_type = 0
                    ev_str = "-"
                    val = new_status[i_d]
                    if i_d in range(MirrIdx.MODE, MirrIdx.MODE + 1):
                        ev_type = HA_EVENTS.MODE
                        ev_str = "Mode"
                        idv = self.get_group()
                    elif i_d in range(MirrIdx.MOV, MirrIdx.MOV + 1):
                        ev_type = HA_EVENTS.MOVE
                        ev_str = "Movement"
                        idv = 0
                    elif i_d in range(MirrIdx.COVER_POS, MirrIdx.COVER_POS + 8):
                        ev_type = HA_EVENTS.COV_VAL
                        idv = self.swap_mirr_cover_idx(i_d - MirrIdx.COVER_POS)
                        ev_str = f"Cover {idv + 1} pos"
                    elif i_d in range(MirrIdx.BLAD_POS, MirrIdx.BLAD_POS + 8):
                        ev_type = HA_EVENTS.BLD_VAL
                        idv = self.swap_mirr_cover_idx(i_d - MirrIdx.BLAD_POS)
                        ev_str = f"Blade {idv + 1} pos"
                    elif i_d in range(MirrIdx.DIM_1, MirrIdx.DIM_4 + 1):
                        ev_type = HA_EVENTS.DIM_VAL
                        idv = i_d - MirrIdx.DIM_1
                        ev_str = f"Dimmmer {idv + 1}"
                    elif i_d in range(MirrIdx.FLAG_LOC, MirrIdx.FLAG_LOC + 2):
                        ev_type = HA_EVENTS.FLAG
                        old_val = self.status[i_d]
                        new_val = new_status[i_d]
                        chg_msk = old_val ^ new_val
                        val = new_val & chg_msk
                        for i in range(8):
                            if (chg_msk & (1 << i)) > 0:
                                break
                        idv = 1 << i
                        if idv != chg_msk:
                            # more than one flag changed, return mask and byte
                            idv = chg_msk + 1000
                            if i_d > MirrIdx.FLAG_LOC:  # upper byte
                                idv = idv + 1000
                        else:
                            # single change, return flag no and value 0/1
                            idv = i
                            if i_d > MirrIdx.FLAG_LOC:  # upper byte
                                idv = idv + 8
                            val = int(val > 0)
                        ev_str = f"Flag {idv + 1}"
                    elif i_d in range(MirrIdx.COUNTER_VAL, MirrIdx.COUNTER_VAL + 28):
                        ev_type = HA_EVENTS.CNT_VAL
                        idv = int((i_d - MirrIdx.COUNTER_VAL) / 3)
                        ev_str = f"Counter {idv + 1}"
                    if ev_type > 0:
                        update_info.append(
                            [
                                self._id,
                                ev_type,
                                idv,
                                val,
                            ]
                        )
                        self.logger.debug(
                            f"Update in module status {self._id}: {self._name}: Event {ev_str}, Byte {i_d} - new: {val}"
                        )
        if len(new_status) > 100:
            self.status = new_status
            self.comp_status = self.get_status(False)
        else:
            self.comp_status = new_status
        self.logger.debug(f"Status of module {self._id} updated")
        return update_info

    def build_smg(self) -> bytes:
        """Pick smg values from full module status."""

        smg_data = b""
        for si in SMGIdx[0:4]:
            smg_data += self.status[si : si + 1]
        smg_data += self.calc_cover_times()
        for si in SMGIdx[36:]:
            smg_data += self.status[si : si + 1]
        return smg_data

    def build_status(self, smg: bytes):
        """Insert SMG values into status"""
        for idx in range(len(SMGIdx)):
            self.status = (
                self.status[: SMGIdx[idx]]
                + smg[idx : idx + 1]
                + self.status[SMGIdx[idx] + 1 :]
            )
        polarity = 0
        for c_i in range(8):
            ta, tb, interp = self.encode_cover_settings(
                smg[4 + 2 * c_i], smg[4 + 2 * c_i + 1]
            )
            if ta > tb:
                polarity = polarity | (1 << (2 * c_i))
            else:
                polarity = polarity | (1 << (2 * c_i + 1))
            self.status = (
                self.status[: MirrIdx.COVER_T + c_i]
                + int.to_bytes(ta + tb)
                + self.status[MirrIdx.COVER_T + c_i + 1 :]
            )
            self.status = (
                self.status[: MirrIdx.BLAD_T + c_i]
                + int.to_bytes(smg[20 + 2 * c_i] + smg[20 + 2 * c_i + 1])
                + self.status[MirrIdx.BLAD_T + c_i + 1 :]
            )
            self.status = (
                self.status[: MirrIdx.COVER_INTERP + c_i]
                + int.to_bytes(interp)
                + self.status[MirrIdx.COVER_INTERP + c_i + 1 :]
            )
        self.status = (
            self.status[: MirrIdx.COVER_POL]
            + int.to_bytes(polarity, 2, "little")
            + self.status[MirrIdx.COVER_POL + 2 :]
        )

    def different_smg_crcs(self) -> bool:
        """Performs comparison, equals lengths of smg buffers."""
        # Replace "______" strings in SW_VERSION and PWR_VERSION
        upl = (
            self.smg_upload.decode("iso8859-1")
            .replace("__", chr(0) + chr(0))
            .encode("iso8859-1")
        )
        smg = self.build_smg()
        if len(smg) > len(upl):
            smg = smg[:-1]
        return calc_crc(upl) != self.calc_SMG_crc(smg)

    def calc_cover_times(self) -> bytes:
        """Calculate interpolation of times for 8 covers and 8 blinds"""
        cv_times = ""
        bl_times = ""
        try:
            prop_range = self.io_properties["covers"]
        except Exception:
            prop_range = 8
        for ci in range(8):
            try:
                if ci in range(prop_range):
                    t_cover = round(
                        self.status[MirrIdx.COVER_T + ci]
                        * self.status[MirrIdx.COVER_INTERP + ci]
                        / 10
                    )
                    if t_cover > 255:
                        t_cover = 0
                    t_blind = self.status[MirrIdx.BLAD_T + ci]

                    pol_mask = int.from_bytes(
                        self.status[MirrIdx.COVER_POL : MirrIdx.COVER_POL + 2], "little"
                    )
                    if pol_mask & (1 << (2 * ci)) > 0:
                        cv_times += chr(t_cover) + chr(0)
                        bl_times += chr(t_blind) + chr(0)
                    else:
                        cv_times += chr(0) + chr(t_cover)
                        bl_times += chr(0) + chr(t_blind)
                else:
                    cv_times += chr(0) + chr(0)
                    bl_times += chr(0) + chr(0)
            except Exception as err_msg:
                self.logger.error(
                    f"Error calculating cover times of module {self._id} no {ci}: {err_msg}"
                )
                cv_times += chr(0) + chr(0)
                bl_times += chr(0) + chr(0)

        return cv_times.encode("iso8859-1") + bl_times.encode("iso8859-1")

    def encode_cover_settings(self, t_a: int, t_b: int) -> tuple[int, int, int]:
        """Create cover settings from cover times"""
        pos_polarity = (t_a >= 0) and (t_b == 0)
        neg_polarity = (t_a == 0) and (t_b >= 0)
        if not (pos_polarity or neg_polarity):
            self.logger.error(
                f"Error with cover times in module {self._id}, one value must be zero!"
            )
            t_b = 0  # continue with t_a
        t_cover = t_a + t_b  # takes the one value
        if t_cover in range(127, 256):
            interp = 10
        elif t_cover in range(51, 127):
            interp = 5
        elif t_cover in range(25, 51):
            interp = 2
        else:
            interp = 1
        t_cover = round(t_cover * 10 / interp)
        if t_b == 0:
            return t_cover, 0, interp
        else:
            return 0, t_cover, interp

    def calc_SMC_crc(self, smc_buf: bytes) -> None:
        """Calculate and store crc of SMC data."""
        self.set_smc_crc(calc_crc(smc_buf))

    def calc_SMG_crc(self, smg_buf: bytes) -> int:
        """Calculate and store crc of SMG data."""
        self.smg_crc = calc_crc(smg_buf)
        return self.smg_crc

    def get_module_settings(self):
        """Collect all settings and prepare for config server."""
        self.settings = ModuleSettings(self)
        return self.settings

    def get_settings_def(self):
        """Return default settings object without automations."""
        return ModuleSettingsLight(self)

    async def set_settings(self, settings: ModuleSettings):
        """Restore changed settings from config server into module and re-initialize."""
        self.settings = settings
        self.status = settings.set_module_settings(self.status)
        self.list = await settings.set_list()
        self.list_upload = self.list
        self.smg_upload = self.build_smg()
        if not self.api_srv.is_offline:
            await self.hdlr.send_module_smg(self._id)
            await self.hdlr.send_module_list(self._id)
            await self.hdlr.get_module_status(self._id)
        self.comp_status = self.get_status(False)
        self.calc_SMG_crc(self.build_smg())
        self._name = (
            self.status[MirrIdx.MOD_NAME : MirrIdx.MOD_NAME + 32]
            .decode("iso8859-1")
            .strip()
        )
        # self.list = await self.hdlr.get_module_list(self._id)
        self.calc_SMC_crc(self.list)

    async def set_automations(self, settings: ModuleSettings):
        """Restore changed automations from config server into module."""
        self.settings = settings
        self.list = await settings.set_automations()
        self.list_upload = self.list
        if not self.api_srv.is_offline:
            await self.hdlr.send_module_list(self._id)
        self.comp_status = self.get_status(False)
        # self.list = await self.hdlr.get_module_list(self._id)
        self.calc_SMC_crc(self.list)

    def get_io_properties(self) -> tuple[dict[str, int], list[str]]:
        """Return number of inputs, outputs, etc."""
        type_code = self._typ
        props: dict = {}
        props["buttons"] = 0
        props["inputs"] = 0
        props["inputs_230V"] = 0
        props["inputs_24V"] = 0
        props["outputs"] = 0
        props["outputs_230V"] = 0
        props["outputs_dimm"] = 0
        props["outputs_24V"] = 0
        props["outputs_relais"] = 0
        props["leds"] = 0
        props["covers"] = 0
        props["logic"] = 0
        props["flags"] = 0
        props["dir_cmds"] = 0
        props["vis_cmds"] = 0
        props["users"] = 0
        props["fingers"] = 0
        props["messages"] = 0
        match type_code[0]:
            case 1:  # controller module
                props["buttons"] = 8
                props["inputs"] = 10
                props["inputs_230V"] = 4
                props["inputs_24V"] = 6
                props["outputs"] = 15
                props["outputs_230V"] = 10
                props["outputs_dimm"] = 2
                props["outputs_24V"] = 2
                props["outputs_relais"] = 1
                props["leds"] = 9
                props["covers"] = 5
                props["logic"] = 10
                props["flags"] = 16
                props["dir_cmds"] = 25
                props["vis_cmds"] = 65280
                props["messages"] = 100
            case 10:
                match type_code[1]:
                    case 1 | 50 | 51:  # relais module
                        props["outputs"] = 8
                        props["outputs_relais"] = 8
                        props["covers"] = 4
                        props["logic"] = 10
                        props["flags"] = 16
                        props["vis_cmds"] = 16
                    case 2:  # tronic module
                        props["outputs"] = 8
                        props["outputs_230V"] = 8
                        props["covers"] = 4
                        props["logic"] = 10
                        props["flags"] = 16
                        props["vis_cmds"] = 65280
                    case 20 | 21 | 22:  # dimm module
                        props["outputs"] = 4
                        props["outputs_dimm"] = 4
                        props["logic"] = 10
                        props["flags"] = 16
                        props["vis_cmds"] = 65280
                    case 30:  # io module
                        props["inputs"] = 2
                        props["inputs_24V"] = 2
                        props["outputs"] = 2
                        props["outputs_relais"] = 2
                        props["covers"] = 1
                        props["logic"] = 10
                        props["flags"] = 16
                        props["vis_cmds"] = 65280
            case 11:
                match type_code[1]:
                    case 1:  # in 230 module
                        props["inputs"] = 8
                        props["inputs_230V"] = 8
                    case 30 | 31:  # in 24 module
                        props["inputs"] = 8
                        props["inputs_24V"] = 8
            case 30:  # ekey module
                props["users"] = 256
                props["fingers"] = props["users"] * 10
            case 50:  # compact controller module
                props["buttons"] = 2
                props["inputs"] = 4
                props["inputs_230V"] = 0
                props["inputs_24V"] = 4
                props["outputs"] = 2
                props["outputs_24V"] = 2
                props["leds"] = 5
                props["logic"] = 10
                props["flags"] = 16
                props["dir_cmds"] = 25
                props["vis_cmds"] = 65280
                props["messages"] = 100

        keys = [
            "buttons",
            "leds",
            "inputs",
            "outputs",
            "covers",
            "logic",
            "users",
            "fingers",
            "flags",
            "dir_cmds",
            "vis_cmds",
            "messages",
        ]
        no_keys = 0
        for key in keys:
            if props[key] > 0:
                no_keys += 1
        props["no_keys"] = no_keys

        return props, keys

    async def cleanup_descriptions(self) -> None:
        """If descriptions in desc file, store them into module and remove them from file."""
        if self.api_srv.is_offline:
            return
        if self._typ[0] not in [1, 10, 50]:
            return
        # Instantiate settings and parse descriptions
        self.settings = self.get_settings_def()
        if self.settings.save_desc_file_needed:
            self.get_rtr().descriptions = dpcopy(self.settings.desc)
            self.get_rtr().save_descriptions()
        if self.settings.upload_desc_info_needed:
            self.list = await self.settings.set_list()
            self.list_upload = self.list
            await self.hdlr.send_module_list(self._id)
