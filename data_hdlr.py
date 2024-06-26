import struct
import asyncio

from const import API_DATA as spec
from hdlr_class import HdlrBase
from const import MirrIdx, MStatIdx, RD_DELAY


class DataHdlr(HdlrBase):
    """Handling of all data messages."""

    async def process_message(self) -> None:
        """Parse message, prepare and send router command."""

        rt, mod = self.get_router_module()
        match self._spec:
            case spec.SMHUB_BOOTQUEST:
                self.response = b"\x01"  # bool True

            case spec.SMHUB_GETINFO:
                self.response = self.api_srv.sm_hub.get_info()

            case spec.SMHUB_UPDATE:
                self.response = self.api_srv.sm_hub.get_update()

            case spec.RT_NAME_FW_NM_PCREAD:
                rt_id = chr(rt).encode("iso8859-1")
                name = await self.api_srv.routers[rt - 1].hdlr.get_rt_name()
                fw = await self.api_srv.routers[rt - 1].hdlr.get_rt_sw_version()
                serial = await self.api_srv.routers[rt - 1].hdlr.get_rt_serial()
                self.response = rt_id + name + fw + serial

            case spec.MODOVW_DIRECT:
                # Get module overview
                self.check_router_no(rt)
                if self.args_err:
                    return
                self.response = self.api_srv.routers[rt - 1].get_modules()

            case spec.MODOVW_NEW:
                # Reload all module status infos
                self.check_router_no(rt)
                if self.args_err:
                    return
                await self.api_srv.set_server_mode(rt)
                for module in self.api_srv.routers[rt - 1].modules:
                    await module.initialize()
                self.response = "OK"

            case spec.MODOVW_FW:
                # Get module overview with firmware
                self.check_router_no(rt)
                if self.args_err:
                    return
                resp = ""
                for module in self.api_srv.routers[rt - 1].modules:
                    sw_v = module.get_sw_version()
                    resp += chr(module._id) + module._typ.decode("iso8859-1")
                    resp += chr(len(module._name)) + module._name
                    resp += chr(len(sw_v)) + sw_v
                self.response = resp

            case spec.SMGS_PCREAD:
                if mod in [254, 255]:
                    # Read all, no check for module no needed
                    self.check_router_no(rt)
                    mod_list = self.api_srv.routers[rt - 1].mod_addrs
                else:
                    self.check_router_module_no(rt, mod)
                    mod_list = [mod]
                if self.args_err:
                    return
                await self.api_srv.set_server_mode(rt)
                self.response = b""
                if mod == 255:
                    rd_delay = RD_DELAY
                else:
                    rd_delay = 0
                for md in mod_list:
                    module = self.api_srv.routers[rt - 1].get_module(md)
                    smg_buf = module.build_smg()
                    self.response = smg_buf
                    if md != mod_list[-1]:
                        await self.api_srv.respond_client(self.response)
                        await asyncio.sleep(rd_delay)

            case spec.SMCS_PCREAD:
                if mod in [254, 255]:
                    # Read all, no check for module no needed
                    self.check_router_no(rt)
                    mod_list = self.api_srv.routers[rt - 1].mod_addrs
                else:
                    self.check_router_module_no(rt, mod)
                    mod_list = [mod]
                if self.args_err:
                    return
                self.response = b""
                if mod == 255:
                    rd_delay = 0  # RD_DELAY
                else:
                    rd_delay = 0
                for md in mod_list:
                    module = self.api_srv.routers[rt - 1].get_module(md)
                    self.response = (
                        chr(md).encode("iso8859-1")
                        + module.get_module_code()
                        + module.list
                    )
                    if md != mod_list[-1]:
                        await self.api_srv.respond_client(self.response)
                        await asyncio.sleep(rd_delay)

            case spec.MOD_STAT_PCREAD | spec.MOD_CSTAT_PCREAD:
                if mod == 255:
                    # Read all, no check for module needed
                    self.check_router_no(rt)
                    mod_list = self.api_srv.routers[rt - 1].mod_addrs
                else:
                    self.check_router_module_no(rt, mod)
                    mod_list = [mod]
                if self.args_err:
                    return
                stat_buf = b""
                if self._spec == spec.MOD_STAT_PCREAD:
                    # use full module status
                    blk_len = chr(MirrIdx.END).encode("iso8859-1")
                else:
                    # use compacted module status
                    blk_len = chr(MStatIdx.END).encode("iso8859-1")
                for md in mod_list:
                    stat_buf += blk_len  # type: ignore
                    module = self.api_srv.routers[rt - 1].get_module(md)
                    stat_buf += module.get_status(self._spec == spec.MOD_STAT_PCREAD)
                self.response = stat_buf

            case spec.SMR_PCREAD:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                rtr.build_smr()
                self.response = rtr.smr

            case spec.RSTAT_PCREAD:  # 10 / 4 / 4
                self.check_router_no(rt)
                if self.args_err:
                    return
                if self.api_srv._opr_mode:
                    # return previously stored status and trigger to get update
                    self.logger.debug(
                        "Query router and return previously stored status"
                    )
                    await self.api_srv.routers[rt - 1].hdlr.query_rt_status()
                    self.response = (
                        chr(rt).encode("iso8859-1")
                        + self.api_srv.routers[rt - 1].chan_status
                    )
                else:
                    self.logger.debug("Get router status")
                    self.response = (
                        chr(rt).encode("iso8859-1")
                        + await self.api_srv.routers[rt - 1].get_status()
                    )
                self.logger.debug(f"Length of response: {len(self.response)}")

            case spec.DESC_PCREAD:
                self.response = self.api_srv.routers[rt - 1].descriptions

            case spec.RT_FW_FILE_VS:
                self.check_router_no(rt)
                if self.args_err:
                    return
                rtr = self.api_srv.routers[rt - 1]
                rtr.check_firmware()
                if rtr.update_available:
                    self.response = rtr.get_version() + "\n" + rtr.update_version
                else:
                    self.response = rtr.get_version() + "\n" + rtr.get_version()
            case spec.MOD_FW_FILE_VS:
                self.check_router_module_no(rt, mod)
                if self.args_err:
                    return
                module = self.api_srv.routers[rt - 1].get_module(mod)
                module.check_firmware()
                if module.update_available:
                    self.response = (
                        module.get_sw_version() + "\n" + module.update_version
                    )
                else:
                    self.response = (
                        module.get_sw_version() + "\n" + module.get_sw_version()
                    )
            case _:
                self.response = f"Unknown API data command: {self.msg._cmd_grp} {struct.pack('<h', self._spec)[1]} {struct.pack('<h', self._spec)[0]}"
                self.logger.warning(self.response)
                return
