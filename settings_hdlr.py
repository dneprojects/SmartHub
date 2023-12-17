import struct
from itertools import chain
from const import API_SETTINGS as spec
from const import RT_CMDS
from hdlr_class import HdlrBase


class SettingsHdlr(HdlrBase):
    """Handling of all settings messages."""

    async def process_message(self):
        """Parse message, prepare and send router command"""

        rt = self._p4
        match self._spec:
            case spec.CONN_TST:
                self.logger.debug("Connection test")
                self._rt_command = ""
                self.response = "OK"
                return

            case spec.MD_SETTINGS:
                module = self.api_srv.routers[rt - 1].get_module(self._p5)
                self.response = module.get_settings()

            case spec.DTQUEST:
                self.check_router_no(rt)
                if self.args_err:
                    return
                await self.api_srv.stop_opr_mode(rt)

                self._rt_command = RT_CMDS.GET_DATE.replace("<rtr>", chr(rt))
                await self.handle_router_cmd_resp(rt, self._rt_command)
                date = self.rt_msg._resp_buffer[-5:-2]
                self._rt_command = RT_CMDS.GET_TIME.replace("<rtr>", chr(rt))
                await self.handle_router_cmd_resp(rt, self._rt_command)
                time = self.rt_msg._resp_buffer[-4:-1]
                self.response = date[::-1] + time[::-1]

            case spec.DTSET:
                self.check_router_no(rt)
                if self.args_err:
                    return
                await self.api_srv.stop_opr_mode(rt)
                self._rt_command = (
                    RT_CMDS.SET_DATE.replace("<rtr>", chr(rt))
                    .replace("<yr>", chr(self._args[0]))
                    .replace("<mon>", chr(self._args[1]))
                    .replace("<day>", chr(self._args[2]))
                )
                await self.handle_router_cmd_resp(rt, self._rt_command)
                self._rt_command = (
                    RT_CMDS.SET_TIME.replace("<rtr>", chr(rt))
                    .replace("<hr>", chr(self._args[3]))
                    .replace("<min>", chr(self._args[4]))
                    .replace("<sec>", chr(self._args[5]))
                )
                await self.handle_router_cmd_resp(rt, self._rt_command)
                self.response = self.rt_msg._resp_msg

            case spec.MDQUEST:  # 02 01: Query mode
                self.check_router_no(rt)
                self.check_arg(
                    self._p5,
                    chain(range(64), [255]),
                    "Error: group no out of range 0..63, 255",
                )
                if self.args_err:
                    return
                await self.api_srv.stop_opr_mode(rt)
                self.response = await self.api_srv.routers[rt - 1].hdlr.get_mode(
                    self._p5
                )
                if self._p5 == 0xFF:
                    self.response = (
                        chr(self.api_srv.routers[rt - 1].mode0).encode("iso8859-1")
                        + self.response
                    )
                    response = chr(65).encode()
                    for g_i in range(65):
                        response += (
                            chr(g_i).encode("iso8859-1") + self.response[g_i : g_i + 1]
                        )
                    self.response = response
                    self.logger.debug("Read all group modes: ")
                elif len(self.response) > 1:
                    self.logger.debug(f"Read mode of group {self._p5}: {self.response}")
                elif len(self.response) == 0:
                    pass
                else:
                    self.logger.debug(
                        f"Read mode of group {self._p5}: 0x{ord(self.response):2X}"
                    )
                    self.response = b"\1" + chr(self._p5).encode() + self.response

            case spec.MDSET:  # 02 02: Set mode
                self.check_router_no(rt)
                self.check_arg(
                    self._p5,
                    chain(range(64), [255]),
                    "Error: group no out of range 0..63, 255",
                )
                if self.args_err:
                    return

                if self._p5 == 0xFF:
                    self.check_arg(
                        self._args[0],
                        [64],
                        "Error: No of modes must be 64",
                    )
                    if self.args_err:
                        return
                    # send all 64 group modes
                    await self.api_srv.stop_opr_mode(rt)
                    self.response = await self.api_srv.routers[rt - 1].hdlr.set_mode(
                        self._p5, self._args[1:]
                    )

                else:
                    await self.api_srv.stop_opr_mode(rt)
                    self.response = await self.api_srv.routers[rt - 1].hdlr.set_mode(
                        self._p5, self._args[2]
                    )
                    self.logger.debug(
                        f"Set mode of group {self._p5}: 0x{ord(self.response):2X}"
                    )

            case spec.VERQUEST:  # 30 00: Get version
                self.logger.debug("Get version")
                self.response = self.api_srv.sm_hub.get_version()
                return

            case spec.MIRRSTART:
                # self.check_router_no(rt)
                rt = 1  # Smart Config doesn't set router
                # if self.args_err:
                #     self.response = self.err_msg
                #     return
                self.api_srv.mirror_mode = True
                await self.api_srv.start_opr_mode(rt)
                self.response = "OK"
                self.logger.debug(f"Mirror mode started on router {rt}")

            case spec.MIRRSTOP:
                # self.check_router_no(rt)
                rt = 1  # Smart Config doesn't set router
                # if self.args_err:
                #     self.response = self.err_msg
                #     return
                self.api_srv.mirror_mode = False
                await self.api_srv.stop_opr_mode(rt)
                self.response = "OK"
                self.logger.debug(f"Mirror mode stopped on router {rt}")
                self.api_srv._auto_restart_opr = False

            case spec.EVENTSTART:
                # self.check_router_no(rt)
                rt = 1  # Smart Config doesn't set router
                # if self.args_err:
                #     self.response = self.err_msg
                #     return
                self.api_srv.event_mode = True
                await self.api_srv.start_opr_mode(rt)
                self.response = "OK"
                self.logger.debug(f"Event mode started on router {rt}")

            case spec.EVENTSTOP:
                # self.check_router_no(rt)
                rt = 1  # Smart Config doesn't set router
                # if self.args_err:
                #     self.response = self.err_msg
                #     return
                self.api_srv.event_mode = False
                await self.api_srv.stop_opr_mode(rt)
                self.response = "OK"
                self.logger.debug(f"Event mode stopped on router {rt}")
                self._auto_restart_opr = False

            case _:
                self.response = f"Unknown API settings command: {self.msg._cmd_grp} {struct.pack('<h', self._spec)[1]} {struct.pack('<h', self._spec)[0]}"
                self.logger.warning(self.response)
                return
