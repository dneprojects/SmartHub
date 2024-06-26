import time
import struct
from const import API_ADMIN as spec
from const import RT_CMDS, DATA_FILES_ADDON_DIR, DATA_FILES_DIR
from hdlr_class import HdlrBase


class AdminHdlr(HdlrBase):
    """Handling of all admin messages."""

    async def process_message(self) -> None:
        """Parse message, prepare and send router command"""

        rt = self._p4
        mod = self._p5
        match self._spec:
            # case spec.SMHUB_READY:
            #     self.response = "OK"
            case spec.SMHUB_REINIT:
                self.response = await self.api_srv.reinit_opr_mode(rt, self._p5)
            case spec.SMHUB_INFO:
                self.response = self.api_srv.sm_hub.get_info()
            case spec.SMHUB_RESTART:
                self.response = "Smart Hub will be restarted"
                await self.api_srv.shutdown(rt, self._p5)
            case spec.SMHUB_REBOOT:
                self.response = "Smart Hub will be rebooted"
                time.sleep(3)
                self.api_srv.sm_hub.reboot_hub()
            case spec.SMHUB_NET_INFO:
                await self.api_srv.set_server_mode(rt)
                ip_len = self._args[0]
                self.api_srv._hass_ip = self._args[1 : ip_len + 1].decode("iso8859-1")
                # tok_len = self._args[ip_len + 1]
                ip_len = len(self.api_srv._client_ip)
                cl_ip_str = (chr(ip_len) + self.api_srv._client_ip).encode("iso8859-1")
                self.save_id(cl_ip_str + self._args)
                self.response = "OK"
            case spec.SMHUB_LOG_LEVEL:
                self.check_arg(
                    self._p4, range(2), "Parameter 4 must be 0 (console) or 1 (file)."
                )
                self.check_arg(
                    self._p5,
                    range(51),
                    "Parameter 5 must be 0..50 (notset .. critical).",
                )
                if self.args_err:
                    return
                self.logger.root.handlers[self._p4].setLevel(self._p5)
                if self._p4 == 0:
                    self.logger.info(
                        f"Logging level for console handler set to {self._p5}"
                    )
                else:
                    self.logger.info(
                        f"Logging level for file handler set to {self._p5}"
                    )
                self.response = "OK"
            case spec.RT_RESTART:
                self.check_router_no(rt)
                if self.args_err:
                    return
                await self.handle_router_cmd_resp(rt, RT_CMDS.RT_REBOOT)
                self.response = self.rt_msg._resp_buffer
            case spec.RT_SYS_RESTART:
                self.check_router_no(rt)
                if self.args_err:
                    return
                await self.handle_router_cmd_resp(rt, RT_CMDS.SYSTEM_RESTART)
                self.response = self.rt_msg._resp_buffer
            case spec.RT_START_FWD:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                mod_list = self.api_srv.routers[rt - 1].mod_addrs
                for md in mod_list:
                    rt_command = RT_CMDS.START_RT_FORW_MOD.replace("<mod>", md)
                    await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_buffer
                return
            case spec.RT_FWD_SET:
                mod = self._args[1]
                cmd = self._args[2]
                t_rt = self._args[3]
                t_mod = self._args[4]
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    t_rt, range(1, 65), "Error: target router no out of range 1..64"
                )
                self.check_arg(
                    t_mod, range(1, 251), "Error: target module no out of range 1..250"
                )
                if self.args_err:
                    return
                rt_command = (
                    RT_CMDS.RT_FORW_SET.replace("<mod_src>", chr(mod))
                    .replace("<cmd_src>", chr(cmd))
                    .replace("<rt_trg>", chr(t_rt))
                    .replace("<mod_trg>", chr(t_mod))
                )
                await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_buffer
                return
            case spec.RT_FWD_DEL | spec.RT_FWD_DELALL:
                if self._args[1] == 255 or self._spec == spec.RT_FWD_DELALL:
                    self.check_router_no(rt)
                    if self.args_err:
                        return
                    rt_command = RT_CMDS.RT_FORW_DEL_ALL
                    await self.handle_router_cmd_resp(rt, rt_command)
                    self.response = self.rt_msg._resp_buffer
                    return
                else:
                    mod = self._args[1]
                    cmd = self._args[2]
                    t_rt = self._args[3]
                    t_mod = self._args[4]
                    self.check_router_module_no(rt, mod)
                    self.check_arg(
                        t_rt, range(1, 65), "Error: target router no out of range 1..64"
                    )
                    self.check_arg(
                        t_mod,
                        range(1, 251),
                        "Error: target module no out of range 1..250",
                    )
                    if self.args_err:
                        return
                    rt_command = (
                        RT_CMDS.RT_FORW_DEL_1.replace("<mod_src>", chr(mod))
                        .replace("<cmd_src>", chr(cmd))
                        .replace("<rt_trg>", chr(t_rt))
                        .replace("<mod_trg>", chr(t_mod))
                    )
                    await self.handle_router_cmd_resp(rt, rt_command)
                    self.response = self.rt_msg._resp_buffer
                    return
            case spec.RT_RD_MODERRS:
                self.check_router_no(rt)
                if self.args_err:
                    return
                await self.handle_router_cmd_resp(rt, RT_CMDS.GET_MD_COMMSTAT)
                self.response = self.rt_msg._resp_msg
                return
            case spec.RT_LAST_MODERR:
                self.check_router_no(rt)
                if self.args_err:
                    return
                await self.handle_router_cmd_resp(rt, RT_CMDS.GET_MD_LASTERR)
                self.response = self.rt_msg._resp_msg
                return
            case spec.RT_BOOT_STAT:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                self.response = await rtr.get_boot_stat()
                return
            case spec.RT_COMM_STAT:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                rt_command = RT_CMDS.GET_MD_COMMSTAT.replace("<mod>", chr(mod))
                await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_buffer[5:-1]
                return
            case spec.RT_RST_COMMERR:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                rt_command = RT_CMDS.RST_MD_COMMSTAT.replace("<mod>", chr(mod))
                await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_msg
                return
            case spec.RT_CHAN_SET | spec.RT_CHAN_RST:
                self.check_router_no(rt)
                if self.args_err:
                    return
                chan_mask = self._p5
                if chan_mask == 0:
                    rt_command = RT_CMDS.GET_RT_CHAN_STAT
                elif self._spec == spec.RT_CHAN_SET:
                    rt_command = RT_CMDS.SET_RT_CHAN.replace("<msk>", chr(chan_mask))
                elif self._spec == spec.RT_CHAN_RST:
                    rt_command = RT_CMDS.RES_RT_CHAN.replace("<msk>", chr(chan_mask))
                await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_msg
                if len(self.response) == 0:
                    self.response = "OK"
                return
            case spec.MD_CHAN_SET | spec.MD_CHAN_RST:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                rt_chan = rtr.get_channel(mod) - 1
                chan_mask = (1 << (2 * rt_chan)) + (1 << ((2 * rt_chan) + 1))
                if self._spec == spec.MD_CHAN_SET:
                    rt_command = RT_CMDS.SET_RT_CHAN.replace("<msk>", chr(chan_mask))
                elif self._spec == spec.MD_CHAN_RST:
                    rt_command = RT_CMDS.RES_RT_CHAN.replace("<msk>", chr(chan_mask))
                await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_msg
                if len(self.response) == 0:
                    self.response = "OK"
                return

            case spec.RT_SET_MODADDR:
                if rt == 0:
                    rt = self._args[0]
                self.check_router_no(rt)
                self.check_arg(
                    self._p5,
                    range(3),
                    "Error: mode argument out of range 0..2",
                )
                if self._p5 == 2:
                    self.check_arg(
                        self._args[1],
                        range(1, 251),
                        "Error: module no out of range 1..250",
                    )
                else:
                    self.check_arg(
                        self._args[1],
                        range(1, 5),
                        "Error: channel no out of range 1..4",
                    )
                self.check_arg(
                    self._args[2],
                    range(1, 251),
                    "Error: module no out of range 1..250",
                )
                if self.args_err:
                    return
                self.response = await self.api_srv.routers[
                    rt - 1
                ].hdlr.set_module_address(self._p5, self._args[1], self._args[2])
                return
            case spec.RT_RST_MODADDR:
                rt = self._p4
                mod = self._p5
                self.check_router_no(rt)
                self.check_arg(
                    mod,
                    [*range(1, 251), 255],
                    "Error: module no out of range 1..250",
                )
                if self.args_err:
                    return
                if mod == 255:
                    mod_list = self.api_srv.routers[rt - 1].mod_addrs
                else:
                    mod_list = [mod]
                for mod in mod_list:
                    await self.handle_router_cmd_resp(
                        rt, RT_CMDS.DEL_MD_ADDR.replace("<mod>", chr(mod))
                    )
                self.response = self.rt_msg._resp_msg
                return
            case spec.DO_FW_UPDATE:
                rtr = self.api_srv.routers[rt - 1]
                if mod == 0:
                    self.check_router_no(rt)
                    if self.args_err:
                        return
                    self.logger.info("Firmware update for router starting")
                    await rtr.update_firmware()
                    rtr.update_available = False
                    self.response = rtr.get_version()
                else:
                    self.check_router_module_no(rt, mod)
                    if self.args_err:
                        return
                    module = rtr.get_module(mod)
                    self.logger.info(f"Firmware update starting for module {mod}")
                    await module.update_firmware()
                    module.update_available = False
                    self.response = module.get_sw_version()
                return
            case spec.MD_RESTART:
                self.check_router_no(rt)
                self.check_arg(
                    mod,
                    [*range(1, 251), 255],
                    "Error: module no out of range 1..250",
                )
                if self.args_err:
                    return
                if mod == 255:
                    for mdl in self.api_srv.routers[rt - 1].get_module_list():
                        module = self.api_srv.routers[rt - 1].get_module(mdl.id)
                        await module.hdlr.mod_reboot()
                    return
                module = self.api_srv.routers[rt - 1].get_module(mod)
                return await module.hdlr.mod_reboot()
            case spec.RT_WRAPPER_SEND:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rt_command = self.msg._cmd_data
                await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_buffer
                return
            case spec.RT_WRAPPER_RECV:
                self.check_router_no(rt)
                if self.args_err:
                    return
                await self.handle_router_resp(rt)
                self.response = self.rt_msg._resp_buffer
                return
            case _:
                self.response = f"Unknown API admin command: {self.msg._cmd_grp} {struct.pack('<h', self._spec)[1]} {struct.pack('<h', self._spec)[0]}"
                self.logger.warning(self.response)
                return

    def save_id(self, id: bytes):
        """Save id in local file."""
        if self.api_srv.is_addon:
            data_file_path = DATA_FILES_ADDON_DIR
        else:
            data_file_path = DATA_FILES_DIR
        with open(data_file_path + "settings.set", mode="wb") as fid:
            fid.write(id)
        fid.close()
