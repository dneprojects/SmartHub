import struct
from const import API_RESPONSE
from const import API_SETUP as spec
from hdlr_class import HdlrBase


class SetupHdlr(HdlrBase):
    """Handling of all setup messages."""

    async def process_message(self):
        """Parse message, prepare and send router command"""

        rt, mod = self.get_router_module()

        match self._spec:
            case spec.KEY_TEACH:
                self.check_router_module_no(rt, mod)
                self.check_user_finger()
                self.check_arg(
                    self._args[2], range(1, 181), "Error: time out of range 1..180"
                )
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                self.response = await (
                    self.api_srv.routers[rt - 1]
                    .get_module(mod)
                    .hdlr.set_ekey_teach_mode(
                        self._args[0], self._args[1], self._args[2]
                    )
                )
                await self.api_srv.routers[rt - 1].set_config_mode(False)
                return
            case spec.KEY_DEL:
                self.check_router_module_no(rt, mod)
                self.check_user_finger()
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                self.response = await (
                    self.api_srv.routers[rt - 1]
                    .get_module(mod)
                    .hdlr.del_ekey_entry(self._args[0], self._args[1])
                )
                await self.api_srv.routers[rt - 1].set_config_mode(False)
                return
            case spec.KEY_DEL_LIST:
                self.check_router_module_no(rt, mod)
                self.check_user_finger()
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                self.response = await (
                    self.api_srv.routers[rt - 1]
                    .get_module(mod)
                    .hdlr.del_ekey_list(self._args[0], self._args)
                )
                await self.api_srv.routers[rt - 1].set_config_mode(False)
                return
            case spec.KEY_DEL_ALL:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                self.response = await (
                    self.api_srv.routers[rt - 1]
                    .get_module(mod)
                    .hdlr.del_ekey_all_users(self._args[0], self._args[1])
                )
                await self.api_srv.routers[rt - 1].set_config_mode(False)
                return
            case spec.KEY_PAIR:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                self.response = await (
                    self.api_srv.routers[rt - 1].get_module(mod).hdlr.set_ekey_pairing()
                )
                await self.api_srv.routers[rt - 1].set_config_mode(False)
                return
            case spec.KEY_STAT:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                self.response = await (
                    self.api_srv.routers[rt - 1].get_module(mod).hdlr.get_ekey_status()
                )
                await self.api_srv.routers[rt - 1].set_config_mode(False)
                return
            case spec.KEY_VERS:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                self.response = await (
                    self.api_srv.routers[rt - 1]
                    .get_module(mod)
                    .hdlr.switch_ekey_version(self._args[0])
                )
                await self.api_srv.routers[rt - 1].set_config_mode(False)
                return
            case spec.KEY_LOG_DEL:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                self.response = await (
                    self.api_srv.routers[rt - 1].get_module(mod).hdlr.ekey_log_delete()
                )
                await self.api_srv.routers[rt - 1].set_config_mode(False)
                return
            case spec.KEY_LOG_RD:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return

                await self.api_srv.routers[rt - 1].set_config_mode(True)
                stat_msg = API_RESPONSE.keylog_upload_stat.replace(
                    "<rtr>", chr(rt)
                ).replace("<mod>", chr(mod))
                await self.send_api_response(stat_msg, 1)  # file transfer started
                self.response = await (
                    self.api_srv.routers[rt - 1].get_module(mod).hdlr.ekey_log_read()
                )
                await self.send_api_response(stat_msg, 2)  # file transfer finished
                await self.api_srv.routers[rt - 1].set_config_mode(False)
            case _:
                self.response = f"Unknown API setup command: {self.msg._cmd_grp} {struct.pack('<h', self._spec)[1]} {struct.pack('<h', self._spec)[0]}"
                self.logger.warning(self.response)
                return

    def check_user_finger(self):
        """Check user no and finger number."""
        self.check_arg(self._args[0], range(1, 201), "Error: user out of range 1..200")
        self.check_arg(
            self._args[1], [*range(1, 11), 255], "Error: finger out of range 1..10"
        )
