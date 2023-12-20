import logging
import asyncio
from const import API_DATA as spec
from const import RT_CMDS, API_ACTIONS, API_FILES
from messages import RtMessage


class HdlrBase:
    """Base class of all api handlers."""

    def __init__(self, api_srv) -> None:
        """Creates handler object with msg infos and serial interface"""
        self.api_srv = api_srv
        self.msg = api_srv.api_msg
        self._cmd_grp = self.msg._cmd_grp
        self._spec: int = self.msg._cmd_spec
        self._p4: int = self.msg._cmd_p4
        self._p5: int = self.msg._cmd_p5
        self._args = self.msg._cmd_data
        self.logger = logging.getLogger(__name__)
        self.response: str = "OK"
        self.ser_if = api_srv._rt_serial
        self.args_err: bool = False
        self.rt_msg = RtMessage(self, 0, "   ")  # initialize empty object

    def get_router_module(self) -> int:
        if (self._p4 == 0) & (len(self._args) > 0):
            return self._args[0], self._args[1]
        elif (self._cmd_grp == 30) & (self._spec >= API_ACTIONS.OUTP_OFF):
            return self._p4, self._p5
        elif self._cmd_grp == 50:
            return self._p4, self._p5
        elif self._cmd_grp == 40:
            return self._p4, self._p5
        elif len(self._args) > 0:
            return self._args[0], self._args[1]
        else:
            return self._p4, self._p5

    def check_arg(self, arg: int, rng: range, err_msg: str):
        """General function for argument checks, return False if no error found"""
        if self.args_err:
            return  # Previous check already failed
        if not (arg in rng):
            self.args_err = True
            self.response = err_msg
            self.logger.error(err_msg)

    def check_arg_bounds(self, arg: float, lower: float, upper: float, err_msg: str):
        """General function for argument checks against bounds (included), return False if no error found"""
        if self.args_err:
            return  # Previous check already failed
        if not (lower <= arg <= upper):
            self.args_err = True
            self.response = err_msg
            self.logger.error(err_msg)

    def check_router_no(self, rt_no: int) -> (bool, str):
        """Check of router no 1..64."""
        self.check_arg(
            rt_no,
            [1],
            "Error: currently only one router supported, id must be 1"
            # rt_no,range(1, 65),"Error: router no out of range 1..64"
        )

    def check_router_module_no(self, rt_no: int, mod_no: int) -> (bool, str):
        """Check of router no 1..64 and module no 1..250."""
        self.check_router_no(rt_no)
        self.check_arg(mod_no, range(1, 251), "Error: module no out of range 1..250")

    async def handle_router_cmd_resp(self, rt_no: int, cmd: RT_CMDS) -> bytes:
        """Sends router command via serial interface and get response"""
        self.rt_msg = RtMessage(self, rt_no, cmd)
        await self.rt_msg.rt_send()
        await asyncio.sleep(0.05)
        self.rt_msg._resp_msg = b"\0"
        self.rt_msg._resp_buffer = b"\0\0"
        if not self.api_srv._opr_mode:
            await self.rt_msg.rt_recv()
        else:
            # no response possible
            self.logger.warning("handle_router_cmd_resp called in Opr mode, return 0 0")
        return self.rt_msg._resp_msg

    async def handle_router_cmd(self, rt_no: int, cmd: RT_CMDS) -> None:
        """Sends router command via serial interface and get response."""
        self.rt_msg = RtMessage(self, rt_no, cmd)
        await self.rt_msg.rt_send()

    async def handle_router_resp(self, rt_no: int) -> None:
        """Waits for router response without sending."""
        self.rt_msg = RtMessage(self, rt_no, "")
        await self.rt_msg.rt_recv()
        return self.rt_msg._resp_msg

    async def send_api_response(self, msg: str, flag: int):
        """Send additional API status response."""
        resp_msg = msg.replace("<flg>", chr(flag))
        self.msg.resp_prepare_stat(resp_msg)
        await self.api_srv.send_status_to_client()
