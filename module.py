import logging
from pymodbus.utilities import checkCRC as ModbusCheckCRC
from pymodbus.utilities import computeCRC as ModbusComputeCRC
from const import MirrIdx, SMGIdx, MStatIdx, MODULE_CODES, CStatBlkIdx
from configuration import ModuleSettings


class HbtnModule:
    """Habitron module object, holds complete status."""

    def __init__(self, mod_id: int, hdlr, rt) -> None:
        self._id: int = mod_id
        self.logger = logging.getLogger(__name__)
        self._name = ""
        self._typ: bytes = b""
        self._type = ""
        self.rt = rt
        self.api_srv = rt.api_srv
        self.hdlr = hdlr

        self.status: bytes = b""  # full mirror, holds module settings
        self.compact_status: bytes = b""  # compact status, subset
        self.smg_upload: bytes = b""  # buffer for SMG upload
        self.smg_crc = 0
        self.list: bytes = b""  # SMC information: labels, commands
        self.list_upload: bytes = b""  # buffer for SMC upload

    def __del__(self):
        """Clean up."""
        del self.logger
        del self.api_srv
        del self.hdlr

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

        self.logger.debug(f"Module {self._name} at {self._id} initialized")

    def get_serial(self):
        """Get serial no from status"""
        serial = (
            self.status[MirrIdx.MOD_SERIAL : MirrIdx.MOD_SERIAL + 16]
            .decode("iso8859-1")
            .strip()
        )
        if serial[0] == "\x00":
            return ""
        return serial

    def get_sw_version(self):
        """Get software version."""
        return (
            self.status[MirrIdx.SW_VERSION : MirrIdx.SW_VERSION + 22]
            .decode("iso8859-1")
            .strip()
        )

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
        """Return status, if direct == False: compacted"""
        if direct:
            return self.status
        compact_status = b""
        for i0, i1 in CStatBlkIdx:
            compact_status += self.status[i0:i1]
        return compact_status

    def get_module_code(self) -> bytes:
        """Return Habitron module code"""
        return self._typ

    def get_settings(self):
        """Return settings part of mirror"""
        return self.status[MirrIdx.T_SHORT : MirrIdx.T_SHORT + 17]

    def compare_status(self, stat1: str, stat2: str) -> list:
        """Find updates fields"""
        diff_idx = []
        idx = 0
        for x, y in zip(stat1, stat2):
            if x != y:
                diff_idx.append(idx)
            idx += 1
        return diff_idx

    def update_status(self, new_status: bytes):
        """Saves new mirror status and returns differences"""
        block_list = []
        update_info = ""

        # print(f"Module update {self._id}")
        if self._type in ["Smart Nature", "FanGSM", "FanM-Bus"]:
            pass
        else:
            if self._type in [
                "Smart Out 8/R",
                "Smart Out 8/R-1",
                "Smart Out 8/R-2",
                "Smart Out 8/T",
            ]:
                i0 = MirrIdx.OUT_1_8
                i1 = MirrIdx.OUT_1_8 + 1
            elif self._type in [
                "Smart In 8/24V",
                "Smart In 8/24V-1",
                "Smart In 8/230V",
            ]:
                i0 = MirrIdx.INP_1_8
                i1 = MirrIdx.INP_1_8 + 1
                i_diff = self.compare_status(self.status[i0:i1], new_status[i0:i1])
                if i_diff != []:
                    self.logger.info("Input change detected!")
            elif self._type in [
                "Smart Detect 180",
                "Smart Detect 180-2",
                "Smart Detect 360",
            ]:
                i0 = MirrIdx.LUM
                i1 = MirrIdx.MOV + 1
            elif self._type in ["Fanekey"]:
                i0 = MirrIdx.IR_H
                i1 = MirrIdx.SMKEY_STAT + 1
            else:  # Controller modules
                block_list = [
                    MirrIdx.MOV,
                    MirrIdx.LUM,
                    MirrIdx.TEMP_ROOM,
                    MirrIdx.TEMP_PWR,
                    MirrIdx.TEMP_EXT,
                ]
                i0 = MirrIdx.INP_1_8
                i1 = MirrIdx.T_SHORT
            i_diff = self.compare_status(self.status[i0:i1], new_status[i0:i1])
            for i_d in i_diff:
                if not (i_d + i0 in block_list):
                    update_info += (
                        chr(self._id)
                        + chr(i_d + i0)
                        + chr(self.status[i_d + i0])
                        + chr(new_status[i_d + i0])
                    )
                    self.logger.info(
                        f"Update in module {self._id}: {self._name}: Byte {i_d+i0} - new: {new_status[i_d+i0]}"
                    )
        if len(new_status) > 100:
            self.status = new_status
            self.comp_status = self.get_status(False)
        else:
            self.comp_status = new_status
        self.logger.debug(f"Status of module {self._id} updated")
        return update_info.encode("iso8859-1")

    def build_smg(self) -> bytes:
        """Pick smg values from full module status."""

        smg_data = b""
        for si in SMGIdx[0:4]:
            smg_data += self.status[si : si + 1]
        smg_data += self.calc_cover_times()
        for si in SMGIdx[36:]:
            smg_data += self.status[si : si + 1]
        return smg_data

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
        return ModbusComputeCRC(upl) != self.calc_SMG_crc(smg)

    def calc_cover_times(self) -> bytes:
        """Calculate interpolation of times for 8 covers and 8 blinds"""
        cv_times = ""
        bl_times = ""
        for ci in range(8):
            try:
                t_cover = round(
                    self.status[MirrIdx.COVER_T + ci]
                    * self.status[MirrIdx.COVER_INTERP + ci]
                    / 10
                )
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
            except Exception as err_msg:
                self.logger.error(f"Error calculating cover times of module {self._id} no {ci}: {err_msg}")
                cv_times += chr(0) + chr(0)
                bl_times += chr(0) + chr(0)

        return cv_times.encode("iso8859-1") + bl_times.encode("iso8859-1")

    def encode_cover_settings(self, t_a: int, t_b: int) -> (int, int, int):
        """Create cover settings from cover times"""
        pos_polarity = (t_a >= 0) & (t_b == 0)
        neg_polarity = (t_a == 0) & (t_b >= 0)
        if not (pos_polarity | neg_polarity):
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
        self.set_smc_crc(ModbusComputeCRC(smc_buf))

    def calc_SMG_crc(self, smg_buf: bytes) -> None:
        """Calculate and store crc of SMG data."""
        self.smg_crc = ModbusComputeCRC(smg_buf)
        return self.smg_crc

    def get_module_settings(self):
        """Collect all settings and prepare for config server."""
        self.settings = ModuleSettings(self, self.rt)
        return self.settings

    async def set_settings(self, settings: ModuleSettings):
        """Restore changed settings from config server into module and re-initialize."""
        self.settings = settings
        self.status = settings.set_module_settings(self.status)
        self.list = settings.set_list()
        self.list_upload = self.list
        self.smg_upload = self.build_smg()
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

    def get_io_properties(self) -> dict:
        """Return number of inputs, outputs, etc."""
        type_code = self._typ
        props: dict = {}
        match type_code[0]:
            case 1:
                props["buttons"] = 8
                props["leds"] = 8
                props["inputs"] = 10
                props["inputs_230V"] = 4
                props["inputs_24V"] = 6
                props["outputs"] = 15
                props["outputs_230V"] = 10
                props["outputs_dimm"] = 2
                props["outputs_24V"] = 2
                props["outputs_relais"] = 1
                props["leds"] = 8
                props["covers"] = 5
                props["logic"] = 10
                props["flags"] = 16
                props["dir_cmds"] = 25
                props["vis_cmds"] = 16
            case 10:
                match type_code[1]:
                    case 1 | 50 | 51:
                        props["buttons"] = 0
                        props["leds"] = 0
                        props["inputs"] = 0
                        props["inputs_230V"] = 0
                        props["inputs_24V"] = 0
                        props["outputs"] = 8
                        props["outputs_230V"] = 0
                        props["outputs_dimm"] = 0
                        props["outputs_24V"] = 0
                        props["outputs_relais"] = 8
                        props["covers"] = 4
                        props["logic"] = 10
                        props["flags"] = 16
                        props["dir_cmds"] = 0
                        props["vis_cmds"] = 16
                    case 2:
                        props["buttons"] = 0
                        props["leds"] = 0
                        props["inputs"] = 0
                        props["inputs_230V"] = 0
                        props["inputs_24V"] = 0
                        props["outputs"] = 8
                        props["outputs_230V"] = 8
                        props["outputs_dimm"] = 0
                        props["outputs_24V"] = 0
                        props["outputs_relais"] = 0
                        props["covers"] = 4
                        props["logic"] = 10
                        props["flags"] = 16
                        props["dir_cmds"] = 0
                        props["vis_cmds"] = 16
                    case 20 | 21 | 22:
                        props["buttons"] = 0
                        props["leds"] = 0
                        props["inputs"] = 0
                        props["inputs_230V"] = 0
                        props["inputs_24V"] = 0
                        props["outputs"] = 4
                        props["outputs_230V"] = 0
                        props["outputs_dimm"] = 4
                        props["outputs_24V"] = 0
                        props["outputs_relais"] = 0
                        props["covers"] = 0
                        props["logic"] = 10
                        props["flags"] = 16
                        props["dir_cmds"] = 0
                        props["vis_cmds"] = 16
            case 11:
                match type_code[1]:
                    case 1:
                        props["buttons"] = 0
                        props["leds"] = 0
                        props["inputs"] = 8
                        props["inputs_230V"] = 8
                        props["inputs_24V"] = 0
                        props["outputs"] = 0
                        props["outputs_230V"] = 0
                        props["outputs_dimm"] = 0
                        props["outputs_24V"] = 0
                        props["outputs_relais"] = 0
                        props["covers"] = 0
                        props["logic"] = 0
                        props["flags"] = 0
                        props["dir_cmds"] = 0
                        props["vis_cmds"] = 0
                    case 30 | 31:
                        props["buttons"] = 0
                        props["leds"] = 0
                        props["inputs"] = 8
                        props["inputs_230V"] = 0
                        props["inputs_24V"] = 8
                        props["outputs"] = 0
                        props["outputs_230V"] = 0
                        props["outputs_dimm"] = 0
                        props["outputs_24V"] = 0
                        props["outputs_relais"] = 0
                        props["covers"] = 0
                        props["logic"] = 0
                        props["flags"] = 0
                        props["dir_cmds"] = 0
                        props["vis_cmds"] = 0
            case 20:
                props["buttons"] = 0
                props["leds"] = 0
                props["inputs"] = 0
                props["inputs_230V"] = 0
                props["inputs_24V"] = 0
                props["outputs"] = 0
                props["outputs_230V"] = 0
                props["outputs_dimm"] = 0
                props["outputs_24V"] = 0
                props["outputs_relais"] = 0
                props["covers"] = 0
                props["logic"] = 0
                props["flags"] = 0
                props["dir_cmds"] = 0
                props["vis_cmds"] = 0
            case 30:
                props["buttons"] = 0
                props["leds"] = 0
                props["inputs"] = 0
                props["inputs_230V"] = 0
                props["inputs_24V"] = 0
                props["outputs"] = 0
                props["outputs_230V"] = 0
                props["outputs_dimm"] = 0
                props["outputs_24V"] = 0
                props["outputs_relais"] = 0
                props["covers"] = 0
                props["logic"] = 0
                props["flags"] = 0
                props["dir_cmds"] = 0
                props["vis_cmds"] = 0
            case 50:
                props["buttons"] = 2
                props["leds"] = 4
                props["inputs"] = 4
                props["inputs_230V"] = 0
                props["inputs_24V"] = 4
                props["outputs"] = 2
                props["outputs_230V"] = 0
                props["outputs_dimm"] = 0
                props["outputs_24V"] = 2
                props["outputs_relais"] = 0
                props["covers"] = 0
                props["logic"] = 10
                props["flags"] = 16
                props["dir_cmds"] = 0
                props["vis_cmds"] = 16
            case 80:
                props["buttons"] = 0
                props["leds"] = 0
                props["inputs"] = 0
                props["inputs_230V"] = 0
                props["inputs_24V"] = 0
                props["outputs"] = 0
                props["outputs_230V"] = 0
                props["outputs_dimm"] = 0
                props["outputs_24V"] = 0
                props["outputs_relais"] = 0
                props["covers"] = 0
                props["logic"] = 0
                props["flags"] = 0
                props["dir_cmds"] = 0
                props["vis_cmds"] = 0
                props["logic"] = 0
                props["flags"] = 0
                props["dir_cmds"] = 0
                props["vis_cmds"] = 0

        keys = [
            "buttons",
            "leds",
            "inputs",
            "outputs",
            "covers",
            "logic",
            "flags",
            "dir_cmds",
        ]
        no_keys = 0
        for key in keys:
            if props[key] > 0:
                no_keys += 1
        props["no_keys"] = no_keys

        return props, keys
