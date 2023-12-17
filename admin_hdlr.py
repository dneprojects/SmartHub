import time
import struct
from const import API_ADMIN as spec
from const import RT_CMDS, DATA_FILES_DIR
from hdlr_class import HdlrBase


class AdminHdlr(HdlrBase):
    """Handling of all admin messages."""

    async def process_message(self):
        """Parse message, prepare and send router command"""

        rt = self._p4
        mod = self._p5
        match self._spec:
            case spec.SMHUB_READY:
                self.response = "OK"
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
                await self.api_srv.stop_opr_mode(rt)
                ip_len = self._args[0]
                self.api_srv._hass_ip = self._args[1 : ip_len + 1].decode("iso8859-1")
                tok_len = self._args[ip_len + 1]
                self.save_id(self._args[ip_len + 2 : ip_len + 2 + tok_len])
                self.response = "OK"
            case spec.SMHUB_LOG_LEVEL:
                self.check_arg(
                    self._p4, range(2), "Parameter 4 ust be 0 (console) or 1 (file)."
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
                self.check_router_no(rt, mod)
                if self.args_err:
                    return
                mod_list = self.api_srv.routers[rt - 1].mod_addrs
                for md in mod_list:
                    rt_command = RT_CMDS.START_RT_FORW_MOD.replace("<mod>", md)
                    await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_buffer
                return
            case spec.RT_FWD_SET:
                mod = self.args[1]
                cmd = self.args[2]
                t_rt = self.args[3]
                t_mod = self.args[4]
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
                    RT_CMDS.RT_FORW_SET.replace("<mod_src>", mod)
                    .replace("<cmd_src>", cmd)
                    .replace("<rt_trg>", t_rt)
                    .replace("<mod_trg>", t_mod)
                )
                await self.handle_router_cmd_resp(rt, rt_command)
                self.response = self.rt_msg._resp_buffer
                return
            case spec.RT_FWD_DEL:
                if self.args[1] == 255:
                    self.check_router_no(rt)
                    if self.args_err:
                        return
                    rt_command = RT_CMDS.RT_FORW_DEL_ALL
                    await self.handle_router_cmd_resp(rt, rt_command)
                    self.response = self.rt_msg._resp_buffer
                    return
                else:
                    mod = self.args[1]
                    cmd = self.args[2]
                    t_rt = self.args[3]
                    t_mod = self.args[4]
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
                        RT_CMDS.RT_FORW_DEL_1.replace("<mod_src>", mod)
                        .replace("<cmd_src>", cmd)
                        .replace("<rt_trg>", t_rt)
                        .replace("<mod_trg>", t_mod)
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
            case spec.MD_RESTART:
                self.check_router_module_no(rt, mod)
                if self.args_err:
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
        with open(DATA_FILES_DIR + "settings.set", mode="wb") as fid:
            fid.write(id)
        fid.close()
