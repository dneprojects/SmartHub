import struct
from pymodbus.utilities import computeCRC as ModbusComputeCRC
import math
import os
from const import API_FILES as spec
from const import API_RESPONSE, MODULE_CODES, DATA_FILES_DIR
from hdlr_class import HdlrBase


class FilesHdlr(HdlrBase):
    """Handling of all files messages."""

    async def process_message(self):
        """Parse message, prepare and send router command"""

        rt, mod = self.get_router_module()
        match self._spec:
            case spec.SMB_SEND:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                desc_buf = self.msg._cmd_data
                rtr.descriptions = desc_buf.decode("iso8859-1")
                rtr.save_descriptions()
                self.response = "OK"
                return
            case spec.SMB_QUEST:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                self.response = rtr.read_desriptions()
                return
            case spec.SMM_SEND:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                self.api_srv.routers[rt - 1].get_module(
                    mod
                ).smg_upload = self.msg._cmd_data[:156]
                self.api_srv.routers[rt - 1].get_module(
                    mod
                ).smc_upload = self.msg._cmd_data[156:]
                self.response = "OK"
                return
            case spec.SMM_TO_MOD:
                self.check_router_no(rt)
                if self.args_err:
                    return
                summary = await self.send_smgs(rt)
                summary += await self.send_smcs(rt)
                await self.api_srv.respond_client(summary)
                self.response = summary
            case spec.SMM_DISC:
                self.check_router_no(rt)
                if self.args_err:
                    return
                for module in self.api_srv.routers[rt - 1].modules:
                    module.smg_upload = b""
                    module.smc_upload = b""
                self.response = "OK"
            case spec.SMG_SEND:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                self.api_srv.routers[rt - 1].get_module(
                    mod
                ).smg_upload = self.msg._cmd_data
                self.response = "OK"
                return
            case spec.SMG_TO_MOD:
                self.check_router_no(rt)
                if self.args_err:
                    return
                summary = await self.send_smgs(rt)
                self.response = summary
            case spec.SMG_DISC:
                self.check_router_no(rt)
                if self.args_err:
                    return
                for module in self.api_srv.routers[rt - 1].modules:
                    module.smg_upload = b""
                self.response = "OK"
            case spec.SMC_SEND:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                self.api_srv.routers[rt - 1].get_module(
                    mod
                ).list_upload = self.msg._cmd_data
                self.response = "OK"
                return
            case spec.SMC_TO_MOD:
                self.check_router_no(rt)
                if self.args_err:
                    return
                summary = await self.send_smcs(rt)
                self.response = summary
            case spec.SMC_DISC:
                self.check_router_no(rt)
                if self.args_err:
                    return
                for module in self.api_srv.routers[rt - 1].modules:
                    module.list_upload = b""
                self.response = "OK"
            case spec.SMR_SEND:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                smr_buf = self.msg._cmd_data
                old_smr_crc = rtr.smr_crc
                rtr.calc_SMR_crc(smr_buf)
                if old_smr_crc == rtr.smr_crc:
                    self.response = "OK"
                    return
                rtr.smr_upload = smr_buf  # smr updated, but status still as in router
                self.response = "OK"
                return
            case spec.SMR_TO_RT:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                # API return 40/3/4 Wert 1
                stat_msg = API_RESPONSE.smr_upload_stat.replace("<rtr>", chr(rt))
                await self.send_api_response(stat_msg, 1)  # file transfer started
                await rtr.set_config_mode(True)
                await rtr.hdlr.send_rt_full_status()
                # Routerstatus neu lesen
                # Weiterleitung neu starten
                rtr.smr_upload = b""
                await rtr.set_config_mode(False)
                self.response = "OK"
                return
            case spec.SMR_DISC:
                self.check_router_no(rt)
                if self.args_err:
                    return
                self.api_srv.routers[rt - 1].smr_upload = b""
                self.response = "OK"
            case spec.SMG_SMC_MOD:
                self.check_router_no(rt)
                if self.args_err:
                    return
                summary = await self.send_smgs(rt)
                summary += await self.send_smcs(rt)
                await self.api_srv.respond_client(summary)
                self.response = summary
            case spec.BIN_SEND:
                self.check_router_no(rt)
                self.check_arg_bounds(
                    self.msg._dlen, 11, math.inf, "Firmware file length too short."
                )
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                rtr.save_firmware(self.msg._cmd_data)
                self.response = "OK"
                return
            case spec.BIN_MOD:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                update_ptr = 0
                while self.msg._dlen >= update_ptr + 3:
                    mod_type = self.msg._cmd_data[update_ptr : update_ptr + 2]
                    no_mods = self.msg._cmd_data[update_ptr + 2]
                    mod_list = self.msg._cmd_data[
                        update_ptr + 3 : update_ptr + 3 + no_mods
                    ]
                    await rtr.set_config_mode(True)
                    if mod_type == b"\x04\x02":
                        await self.update_router(rtr, mod_type)
                    else:
                        await self.update_module_type(rtr, mod_type, mod_list)
                    await rtr.set_config_mode(False)
                    update_ptr += no_mods + 3
                self.response = "OK"
                return
            case spec.BIN_DISC:
                self.check_router_no(rt)
                if self.args_err:
                    return
                for file_name in os.listdir(DATA_FILES_DIR):
                    if file_name.endswith(".bin"):
                        os.remove(DATA_FILES_DIR + file_name)
                        self.logger.debug(
                            "Firmware file deleted: " + DATA_FILES_DIR + file_name
                        )
                self.api_srv.routers[rt - 1].fw_upload = b""
                self.response = "OK"
                return
            case spec.BIN_AUTO_MOD:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                type_list = []
                for module in rtr.modules:
                    m_typ = module._typ
                    i_typ = int.from_bytes(m_typ, "little")
                    if not (i_typ in type_list):
                        mod_list = []
                        type_list.append(i_typ)
                        for mod in rtr.modules:
                            if mod._typ == m_typ:
                                mod_list.append(mod.id)
                        await rtr.set_config_mode(True)
                        self.update_module_type(rtr, m_typ, mod_list)
                        await rtr.set_config_mode(False)
                self.response = "OK"
                return
            case spec.LOG_QUEST:
                self.check_arg(
                    self._p4,
                    range(4),
                    "Logging file version must be in 0..3.",
                )
                if self.args_err:
                    return
                if self._p4 == 0:
                    postfix = ""
                else:
                    postfix = f".{self._p4}"
                log_file = open(f"smhub.log{postfix}", "r")
                self.response = log_file.read()
                log_file.close()
                return
            case _:
                self.response = f"Unknown API files command: {self.msg._cmd_grp} {struct.pack('<h', self._spec)[1]} {struct.pack('<h', self._spec)[0]}"
                self.logger.warning(self.response)
                return

    async def send_smgs(self, rt):
        """Send all uploaded smg data to modules"""
        summary = ""
        no_uploads = 0
        rtr = self.api_srv.routers[rt - 1]
        for module in self.api_srv.routers[rt - 1].modules:
            if len(module.smg_upload) > 0:
                no_uploads += 1
                if module.different_smg_crcs() | (self._p5 != 0):
                    await rtr.set_config_mode(True)
                    await module.hdlr.send_module_smg(module._id)
                    summary += chr(module._id) + chr(1)
                    await module.hdlr.get_module_status(module._id)
                else:
                    summary += chr(module._id) + chr(0)
                module.smg_upload = b""
        await rtr.set_config_mode(False)
        return chr(no_uploads) + summary

    async def send_smcs(self, rt):
        """Send all uploaded smc data to modules"""
        summary = ""
        no_uploads = 0
        rtr = self.api_srv.routers[rt - 1]
        for module in self.api_srv.routers[rt - 1].modules:
            if len(module.list_upload) > 0:
                no_uploads += 1
                if ModbusComputeCRC(module.list_upload) != module.get_smc_crc() | (
                    self._p5 != 0
                ):
                    await rtr.set_config_mode(True)
                    stat_msg = API_RESPONSE.smc_upload_stat.replace(
                        "<rtr>", chr(rt)
                    ).replace("<mod>", chr(module._id))

                    await module.hdlr.send_module_list(module._id)
                    # = bytes, content changed
                    summary += (
                        chr(module._id)
                        + chr(module.list_upload[0])
                        + chr(module.list_upload[1])
                        + chr(0)
                    )

                else:
                    # = bytes, content unchanged
                    summary += chr(module._id) + chr(0) + chr(0) + chr(1)
                module.list = module.list_upload  # take current list
                module.list_upload = b""  # clear list buffer after transfer
                module.set_smc_crc(ModbusComputeCRC(module.list))
        await rtr.set_config_mode(False)
        return chr(no_uploads) + summary

    async def update_router(self, rtr, rt_type) -> bool:
        """Upload and flash firmware for one router"""
        if rtr.load_firmware(rt_type):
            return await rtr.hdlr.upload_router_firmware(rt_type)
        return False

    async def update_module_type(self, rtr, mod_type, mod_list) -> bool:
        """Upload and flash firmware for one module type"""
        if rtr.load_firmware(mod_type):
            if await rtr.hdlr.upload_module_firmware(mod_type):
                return await rtr.hdlr.flash_module_firmware(mod_list)
        return False
