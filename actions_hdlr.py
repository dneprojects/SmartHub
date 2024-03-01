import struct
from const import API_ACTIONS as spec
from const import RT_CMDS
from hdlr_class import HdlrBase


class ActionsHdlr(HdlrBase):
    """Handling of all actions messages."""

    async def process_message(self):
        """Parse message, prepare and send router command"""

        rt, mod = self.get_router_module()
        match self._spec:
            case spec.OUT_ON:
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[2], range(1, 25), "Error: output out of range 1..24"
                )
                if self.args_err:
                    return
                outp_bit = 1 << (self._args[2] - 1)
                self._rt_command = (
                    RT_CMDS.SET_OUT_ON.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<outl>", chr(outp_bit & 0xFF))
                    .replace("<outm>", chr((outp_bit >> 8) & 0xFF))
                    .replace("<outh>", chr((outp_bit >> 16) & 0xFF))
                )

                self.logger.debug(
                    f"Router {rt}, module {mod}: turn output {self._args[2]} on"
                )

            case spec.OUT_OFF:
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[2], range(1, 25), "Error: output out of range 1..24"
                )
                if self.args_err:
                    return
                outp_bit = 1 << (self._args[2] - 1)
                self._rt_command = (
                    RT_CMDS.SET_OUT_OFF.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<outl>", chr(outp_bit & 0xFF))
                    .replace("<outm>", chr((outp_bit >> 8) & 0xFF))
                    .replace("<outh>", chr((outp_bit >> 16) & 0xFF))
                )
                self.logger.debug(
                    f"Router {rt}, module {mod}: turn output {self._args[2]} off"
                )

            case spec.DIMM_SET:
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[2], range(1, 5), "Error: output out of range 1..4"
                )
                self.check_arg(
                    self._args[3], range(0, 101), "Error: output out of range 0..100"
                )
                if self.args_err:
                    return
                self._rt_command = (
                    RT_CMDS.SET_DIMM_VAL.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<out>", chr(self._args[2]))
                    .replace("<val>", chr(self._args[3]))
                )
                self.logger.debug(
                    f"Router {rt}, module {mod}: set dimm value output {self._args[2]} to {self._args[3]}"
                )

            case spec.COVR_SET:
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[2],
                    range(1, 3),
                    "Error: shutter/blind mode out of range 1..2",
                )
                self.check_arg(
                    self._args[3], range(1, 6), "Error: cover out of range 1..5"
                )
                self.check_arg(
                    self._args[4], range(0, 101), "Error: output out of range 0..100"
                )
                if self.args_err:
                    return
                val = self._args[4]
                if val in range(1, 99):
                    # Fix, otherwise position is always wrong
                    val -= 1
                self._rt_command = (
                    RT_CMDS.SET_COVER_POS.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<sob>", chr(self._args[2]))
                    .replace("<out>", chr(self._args[3]))
                    .replace("<val>", chr(val))
                )
                self.logger.debug(
                    f"Router {rt}, module {mod}: set cover {self._args[3]} position to {self._args[4]}"
                )

            case spec.TEMP_SET:
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[2],
                    (1, 2, 100),
                    "Error: control selector out of range 1,2,100",
                )
                if self.args_err:
                    return
                if self._args[2] == 1:  # temperature 1
                    sel = 83
                elif self._args[2] == 2:  # temperature 1
                    sel = 87
                else:
                    sel = 100
                self._rt_command = (
                    RT_CMDS.SET_TEMP.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<sel>", chr(sel))
                    .replace("<tmpl>", chr(self._args[3]))
                    .replace("<tmph>", chr(self._args[4]))
                )
                self.logger.debug(
                    f"Router {rt}, module {mod}: set temperature set value of control {self._args[2]} to {(self._args[3]+256*self._args[4])/10}"
                )

            case spec.VIS_CMD:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                self._rt_command = (
                    RT_CMDS.CALL_VIS_CMD.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<cmdl>", chr(self._args[2]))
                    .replace("<cmdh>", chr(self._args[3]))
                )
                self.logger.debug(
                    f"Router {rt}, module {mod}: visualization command {self._args[2]+256*self._args[3]}"
                )

            case spec.COLL_CMD:
                self.check_router_no(self._p4)
                self.check_arg(
                    self._p5, range(1, 256), "Error: command no out of range 1..255"
                )
                if self.args_err:
                    return
                self._rt_command = RT_CMDS.CALL_COLL_CMD.replace(
                    "<rtr>", chr(self._p4)
                ).replace("<cmd>", chr(self._p5))
                self.logger.debug(f"Router {rt}, collective command {self._p5}")

            case spec.FLAG_SET | spec.FLAG_RESET:
                self.check_router_no(self._p4)
                self.check_arg(
                    self._p5, range(0, 251), "Error: module no out of range 0..250"
                )
                self.check_arg(
                    self._args[0],
                    range(17),
                    "Error: flag out of range 1..16",
                )
                flg_msk = 1 << (self._args[0] - 1)
                if self._spec == spec.FLAG_SET:
                    if self._p5:
                        cmd = RT_CMDS.SET_FLAG_ON
                    else:
                        cmd = RT_CMDS.SET_GLB_FLAG_ON
                else:
                    if self._p5:
                        cmd = RT_CMDS.SET_FLAG_OFF
                    else:
                        cmd = RT_CMDS.SET_GLB_FLAG_OFF
                self._rt_command = (
                    cmd.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<flgl>", chr(flg_msk & 0xFF))
                    .replace("<flgh>", chr(flg_msk >> 8))
                )

            case spec.LOGIC_RESET | spec.LOGIC_SET | spec.COUNTR_UP | spec.COUNTR_DOWN:
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[0],
                    range(1, 10),
                    "Error: logic element out of range 1..10",
                )
                if self._spec in [spec.LOGIC_RESET, spec.LOGIC_SET]:
                    self.check_arg(
                        self._args[1],
                        range(1, 8),
                        "Error: logic input out of range 1..8",
                    )
                if self.args_err:
                    return
                if self._spec == spec.COUNTR_UP:
                    inp_no = 1
                elif self._spec == spec.COUNTR_DOWN:
                    inp_no = 2
                else:
                    inp_no = self._args[1]
                if self._spec == spec.LOGIC_RESET:
                    rs_val = 2
                    sr_str = "reset"
                else:
                    rs_val = 1
                    sr_str = "set"
                inp_cnt = 164 + 8 * (self._args[0] - 1) + inp_no

                self._rt_command = (
                    RT_CMDS.SET_LOGIC_INP.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<sr>", chr(rs_val))
                    .replace("<inp>", chr(inp_cnt))
                )
                self.logger.info(
                    f"Router {rt}, module {mod}: {sr_str} input {inp_no} of logic block {self._args[0]}"
                )
            case spec.COUNTR_VAL:
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[0],
                    range(1, 10),
                    "Error: logic element out of range 1..10",
                )
                if self.args_err:
                    return
                self._rt_command = (
                    RT_CMDS.SET_COUNTER_VAL.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<lno>", chr(self._args[0]))
                    .replace("<val>", chr(self._args[1]))
                )
                self.logger.info(
                    f"Router {rt}, module {mod}: set value of counter {self._args[0]} to {self._args[1]}"
                )

            case spec.OUTP_RBG_OFF | spec.OUTP_RBG_ON:
                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[0],
                    [1, 2, 3, 4, 5],
                    "Error: led no out of range 1..8, corners 41..44, all 100",
                )
                if self.args_err:
                    return
                inp_code = self._args[0]
                if self._spec == spec.OUTP_RBG_OFF:
                    rt_cmd = RT_CMDS.SWOFF_RGB_CORNR
                    if inp_code == 5:
                        rt_cmd = RT_CMDS.SWOFF_RGB_AMB
                elif inp_code == 5:
                    rt_cmd = RT_CMDS.SET_RGB_AMB_COL
                else:
                    rt_cmd = RT_CMDS.SET_RGB_CORNR
                rt_cmd = (
                    rt_cmd.replace("<r>", chr(30))
                    .replace("<g>", chr(30))
                    .replace("<b>", chr(30))
                )
                if inp_code < 5:
                    inp_code += 40
                elif inp_code == 5:
                    inp_code = 100
                self._rt_command = (
                    rt_cmd.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<cnr>", chr(inp_code))
                )

            case spec.OUTP_RBG_VAL:

                self.check_router_module_no(rt, mod)
                self.check_arg(
                    self._args[0],
                    [1, 2, 3, 4, 5],
                    "Error: led no out of range 1..8, corners 41..44, all 100",
                )
                if self.args_err:
                    return
                task = 0x01
                inp_code = self._args[0]
                if inp_code < 5:
                    inp_code += 40
                elif inp_code == 5:
                    inp_code = 100
                self._rt_command = (
                    RT_CMDS.SET_RGB_LED.replace("<rtr>", chr(rt))
                    .replace("<mod>", chr(mod))
                    .replace("<tsk>", chr(task))
                    .replace("<inp>", chr(inp_code))
                    .replace("<md>", chr(2))
                    .replace("<r>", chr(self._args[1]))
                    .replace("<g>", chr(self._args[2]))
                    .replace("<b>", chr(self._args[3]))
                    .replace("<tl>", chr(3))
                    .replace("<th>", chr(0))
                )
                self.logger.debug(
                    f"Router {rt}, module {mod}, led {inp_code}: turn LED to R:{self._args[1]} G:{self._args[2]} B:{self._args[3]}"
                )

            case _:
                self.response = f"Unknown API data command: {self.msg._cmd_grp} {struct.pack('<h', self._spec)[1]} {struct.pack('<h', self._spec)[0]}"
                self.logger.warning(self.response)
                return

        # Send command to router
        await self.handle_router_cmd(rt, self._rt_command)
        self.response = "OK"
