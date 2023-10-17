import logging
import asyncio
from math import ceil
from const import (
    RT_CMDS,
    API_RESPONSE,
    MODULE_CODES,
    RtStatIIdx,
    RT_RESP,
    RT_STAT_CODES,
    SYS_MODES,
)
from hdlr_class import HdlrBase
from messages import RtResponse


class RtHdlr(HdlrBase):
    """Handling of incoming router messages."""

    def __init__(self, rtr, api_srv) -> None:
        """Creates handler object with msg infos and serial interface"""
        self.rtr = rtr
        self.api_srv = api_srv
        self.ser_if = self.api_srv._rt_serial
        self.rt_id = rtr._id
        self.logger = logging.getLogger(__name__)

    def __del__(self):
        """Clean up."""
        del self.logger
        del self.api_srv
        del self.rtr

    async def rt_reboot(self):
        """Initiates a router reboot"""
        self.logger.info(f"Router {self.rt_id} will be rebooted, please wait...")
        await self.handle_router_cmd(self.rt_id, RT_CMDS.RT_REBOOT)
        router_running = False
        print("Reboot")
        # while not (router_running):
        #     # Ask for mode 0, if returned, router is up
        #     # await self.rt_msg.get_router_response()
        #     ret_msg = await self.get_mode(0)
        #     router_running = len(ret_msg) > 0
        print("")

    async def set_mode(self, group: int, new_mode):
        """Changes system or group mode to new_mode"""
        if group == 0:
            # System mode
            rt_cmd = RT_CMDS.SET_GLOB_MODE
            rt_cmd = rt_cmd.replace("<md>", chr(new_mode))
            await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
            self.rtr._in_config_mode = new_mode != SYS_MODES.Config
            return self.rt_msg._resp_buffer[-2:-1]
        if group == 255:
            # All groups but 0
            grps_modes = ""
            rt_cmd = RT_CMDS.SET_GRPS_MODE
            for nm in new_mode:
                grps_modes += chr(nm)
            rt_cmd = rt_cmd.replace("<mds>", grps_modes)
            await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
            return self.rt_msg._resp_buffer[6:-1]
        else:
            rt_cmd = RT_CMDS.SET_GRP_MODE.replace("<grp>", chr(group))
            rt_cmd = rt_cmd.replace("<md>", chr(new_mode))
            await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
            return self.rt_msg._resp_buffer[-2:-1]

    async def get_mode(self, group):
        """Changes system or group mode to new_mode"""
        if group == 0:
            # System mode
            rt_cmd = RT_CMDS.GET_GLOB_MODE
        elif group == 255:
            # All groups but 0
            rt_cmd = RT_CMDS.GET_GRPS_MODE
        else:
            rt_cmd = RT_CMDS.GET_GRP_MODE.replace("<grp>", chr(group))
        await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
        if group == 0:
            self.rtr.mode0 = ord(self.rt_msg._resp_msg)
        return self.rt_msg._resp_msg

    async def get_rt_channels(self) -> bytes:
        """Get router channels."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_CHANS)
        self.rtr.channels = self.rt_msg._resp_msg
        return self.rtr.channels

    async def get_rt_timeout(self) -> bytes:
        """Get router timeout."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_TIMEOUT)
        self.rtr.timeout = self.rt_msg._resp_msg[-1:]
        return self.rtr.timeout

    async def get_rt_group_no(self) -> bytes:
        """Get router group no."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_GRPNO)
        grps = self.rt_msg._resp_msg
        self.rtr.groups = chr(len(grps)).encode("iso8859-1") + grps
        return self.rtr.groups

    async def get_rt_group_deps(self) -> bytes:
        """Get router mode dependencies."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_GRPMODE_DEP)
        grps = self.rt_msg._resp_msg
        self.rtr.mode_dependencies = chr(len(grps)).encode("iso8859-1") + grps
        return self.rtr.mode_dependencies

    async def get_rt_name(self) -> bytes:
        """Get router name."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_NAME)
        name = self.rt_msg._resp_msg
        self.rtr.name = chr(len(name)).encode("iso8859-1") + name
        self.rtr._name = name.decode("iso8859-1").strip()
        return self.rtr.name

    async def get_mode_names(self) -> bytes:
        """Get user mode names 1 and 2."""
        await self.handle_router_cmd_resp(
            self.rt_id, RT_CMDS.GET_RT_MODENAM.replace("<umd>", "\x01")
        )
        umode_name_1 = self.rt_msg._resp_msg[1:]
        await self.handle_router_cmd_resp(
            self.rt_id, RT_CMDS.GET_RT_MODENAM.replace("<umd>", "\x02")
        )
        umode_name_2 = self.rt_msg._resp_msg[1:]
        nm_len = chr(len(umode_name_1)).encode("iso8859-1")
        self.rtr.user_modes = nm_len + umode_name_1 + nm_len + umode_name_2
        return self.rtr.user_modes

    async def get_rt_serial(self) -> bytes:
        """Get full router serial number."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_SERNO)
        serial = self.rt_msg._resp_msg
        self.rtr.serial = chr(len(serial)).encode("iso8859-1") + serial
        return self.rtr.serial

    async def get_rt_day_night_changes(self) -> bytes:
        """Get full router settings for day night changes."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_DAYNIGHT)
        self.rtr.day_night = b"\x46" + self.rt_msg._resp_msg
        return self.rtr.day_night

    async def get_rt_sw_version(self) -> bytes:
        """Get router software version."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_SW_VERSION)
        self.rtr.version = self.rt_msg._resp_msg
        self.rtr._version = self.rtr.version[1:].strip().decode("iso8859-1")
        return self.rtr.version

    async def get_date(self) -> bytes:
        """Get date settings."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_DATE)
        self.rtr.date = self.rt_msg._resp_buffer[5:9]
        return self.rtr.date

    async def get_grp_mode_status(self) -> bytes:
        """Get router group mode status."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_GRPMOD_STAT)
        return self.rt_msg._resp_msg

    async def get_rt_full_status(self):
        """Get full router status."""
        # Create continuous status byte array and indices
        stat_idx = [0]
        rt_stat = chr(self.rt_id).encode()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_channels()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_timeout()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_group_no()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_group_deps()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_name()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_mode_names()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_serial()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_day_night_changes()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_sw_version()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_date()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_grp_mode_status()
        stat_idx.append(len(rt_stat))
        self.rtr.grp_mode_status = rt_stat[stat_idx[-2] : stat_idx[-1]]
        self.rtr.status_idx = stat_idx

        return rt_stat

    async def query_rt_status(self):
        """Get router system status. Used in api mode"""
        await self.handle_router_cmd(self.rt_id, RT_CMDS.GET_RT_STATUS)
        return "OK"

    async def get_rt_status(self):
        """Get router system status."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_STATUS)
        if len(self.rt_msg._resp_msg) < 40:
            # Something went wrong, return buffer as is
            self.logger.warning(
                f"Router channel status with wrong length {len(self.rt_msg._resp_msg)}, return stored value"
            )
            return self.rtr.chan_status
        # Deal with option "L", makes 1 byte difference
        if self.rt_msg._resp_buffer[-42] != 0:
            return self.rt_msg._resp_buffer[-43:-1]
        self.logger.warning("Router channel status with mode=0, return stored value")
        return self.rtr.chan_status

    async def get_rt_modules(self):
        """Get all modules connected to router."""
        await self.rt_msg.api_hdlr.api_srv.stop_api_mode(1)
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_MODULES)
        return self.rt_msg._resp_msg

    async def send_rt_channels(self):
        """Send router channels."""
        idx1 = self.rtr.self.status_idx[RtStatIIdx.CHANNELS]
        idx2 = self.rtr.self.status_idx[RtStatIIdx.CHANNELS + 1]
        rt_channels = self.rtr.smr_upload[idx1:idx2]
        cmd_str = RT_CMDS.SEND_RT_CHANS + rt_channels.decode("iso8859-1") + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_rt_timeout(self):
        """Send router timeout."""
        idx1 = self.rtr.self.status_idx[RtStatIIdx.TIMEOUT]
        idx2 = self.rtr.self.status_idx[RtStatIIdx.TIMEOUT + 1]
        tout = self.rtr.smr_upload[idx1].decode("iso8859-1")
        cmd_str = RT_CMDS.SEND_RT_TIMEOUT.replace("<tout>", tout)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_rt_group_no(self):
        """Send router group no."""
        idx1 = self.rtr.self.status_idx[RtStatIIdx.GROUPS]
        idx2 = self.rtr.self.status_idx[RtStatIIdx.GROUPS + 1]
        rt_groups = self.rtr.smr_upload[idx1:idx2]
        cmd_str = RT_CMDS.SEND_RT_GRPNO + rt_groups.decode("iso8859-1") + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_rt_group_deps(self):
        """Send router mode dependencies."""
        idx1 = self.rtr.self.status_idx[RtStatIIdx.GROUP_DEPEND]
        idx2 = self.rtr.self.status_idx[RtStatIIdx.GROUP_DEPEND + 1]
        rt_groupdep = self.rtr.smr_upload[idx1:idx2]
        cmd_str = RT_CMDS.SEND_RT_GRPMODE_DEP + rt_groupdep.decode("iso8859-1") + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_rt_name(self):
        """Send router name."""
        idx1 = self.rtr.self.status_idx[RtStatIIdx.NAME]
        idx2 = self.rtr.self.status_idx[RtStatIIdx.NAME + 1]
        rt_name = self.rtr.smr_upload[idx1:idx2]
        cmd_str = RT_CMDS.SEND_RT_NAME + rt_name.decode("iso8859-1") + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_mode_names(self):
        """Send user mode names."""
        idx1 = self.rtr.self.status_idx[RtStatIIdx.UMODE_NAMES]
        idx2 = self.rtr.self.status_idx[RtStatIIdx.UMODE_NAMES + 1]
        umd_names = self.rtr.smr_upload[idx1:idx2]
        cmd_str = RT_CMDS.SEND_RT_MODENAM + umd_names.decode("iso8859-1") + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_rt_day_night_changes(self):
        """Send day night settings."""
        idx1 = self.rtr.self.status_idx[RtStatIIdx.DAY_NIGHT]
        idx2 = self.rtr.self.status_idx[RtStatIIdx.DAY_NIGHT + 1]
        day_night = self.rtr.smr_upload[idx1:idx2]
        cmd_str = RT_CMDS.SEND_RT_DAYNIGHT + day_night.decode("iso8859-1") + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_rt_full_status(self):
        """Get full router status."""
        await self.send_rt_channels()
        await self.send_rt_timeout()
        await self.send_rt_group_no()
        await self.send_rt_group_deps()
        await self.send_rt_name()
        await self.send_mode_names()
        await self.send_rt_day_night_changes()

    async def upload_router_firmware(self, rt_type) -> bool:
        """Upload router firmware to router, returns True for success."""
        fw_buf = self.rtr.fw_upload
        fw_len = len(fw_buf)
        stat_msg = API_RESPONSE.rtfw_flash_stat.replace("<rtr>", chr(self.rt_id))
        cmd_str = RT_CMDS.SET_ISP_MODE.replace("<lenl>", chr(fw_len & 0xFF)).replace(
            "<lenh>", chr(fw_len >> 8)
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        await asyncio.sleep(3)
        self.logger.warning("Router set into update mode")

        cmd_org = RT_CMDS.UPDATE_RT_PKG
        pkg_len = 13
        if fw_len > 0:
            no_pkgs = int(fw_len / pkg_len)
            rest_len = fw_len - no_pkgs * pkg_len
            stat_msg = stat_msg.replace("<pkgs>", chr(no_pkgs + 1))
            if rest_len > 0:
                no_pkgs += 1
            for pi in range(no_pkgs):
                pkg_low = (pi + 1) & 0xFF
                pkg_high = (pi + 1) >> 8
                if pi < no_pkgs - 1:
                    cmd_str = (
                        cmd_org.replace("<len>", chr(pkg_len + 8))
                        .replace("<pno>", chr(pkg_low))
                        .replace(
                            "<buf>",
                            fw_buf[pi * pkg_len : (pi + 1) * pkg_len].decode(
                                "iso8859-1"
                            ),
                        )
                    )
                else:
                    cmd_str = (
                        cmd_org.replace("<len>", chr(rest_len + 8))
                        .replace("<pno>", chr(pkg_low))
                        .replace("<buf>", fw_buf[pi * pkg_len :].decode("iso8859-1"))
                    )
                await self.handle_router_cmd_resp(self.rt_id, cmd_str)
                await self.api_srv.hdlr.send_api_response(
                    stat_msg.replace("<pkgl>", chr(pkg_low)).replace(
                        "<pkgh>", chr(pkg_high)
                    ),
                    RT_STAT_CODES.PKG_OK,
                )
            self.logger.info(f"Successfully uploaded and flashed router firmware")
            await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
            return "OK"
        self.logger.error(f"Failed to upload / flash router")
        return "ERROR"

    async def upload_module_firmware(self, mod_type: bytes) -> bool:
        """Upload firmware to router, returns True for success."""
        fw_buf = self.rtr.fw_upload
        fw_len = len(fw_buf)
        cmd_org = RT_CMDS.UPDATE_MOD_PKG
        stat_msg = API_RESPONSE.bin_upload_stat.replace("<rtr>", chr(self.rt_id))
        pkg_len = 246
        if fw_len > 0:
            no_pkgs = int(fw_len / pkg_len)
            rest_len = fw_len - no_pkgs * pkg_len
            stat_msg = stat_msg.replace("<pkgs>", chr(no_pkgs + 1))
            if rest_len > 0:
                no_pkgs += 1
            for pi in range(no_pkgs):
                if pi < no_pkgs - 1:
                    cmd_str = (
                        cmd_org.replace("<len>", chr(pkg_len + 8))
                        .replace("<pno>", chr(pi + 1))
                        .replace("<pcnt>", chr(no_pkgs))
                        .replace("<blen>", chr(pkg_len))
                        .replace(
                            "<buf>",
                            fw_buf[pi * pkg_len : (pi + 1) * pkg_len].decode(
                                "iso8859-1"
                            ),
                        )
                    )
                else:
                    cmd_str = (
                        cmd_org.replace("<len>", chr(rest_len + 8))
                        .replace("<pno>", chr(pi + 1))
                        .replace("<pcnt>", chr(no_pkgs))
                        .replace("<blen>", chr(rest_len))
                        .replace("<buf>", fw_buf[pi * pkg_len :].decode("iso8859-1"))
                    )
                await self.handle_router_cmd_resp(self.rt_id, cmd_str)
                if self.rt_msg._resp_buffer[5] == RT_STAT_CODES.PKG_OK:
                    await self.api_srv.hdlr.send_api_response(
                        stat_msg.replace("<pkg>", chr(pi + 1)), RT_STAT_CODES.PKG_OK
                    )
                else:
                    await self.api_srv.hdlr.send_api_response(
                        stat_msg.replace("<pkg>", chr(pi + 1)), RT_STAT_CODES.PKG_ERR
                    )
                    break  # abort upload
            if (self.rt_msg._resp_buffer[4] == pi + 1) & (
                self.rt_msg._resp_buffer[5] == RT_STAT_CODES.PKG_OK
            ):
                self.logger.debug(
                    f"Successfully uploaded firmware type {mod_type[0]:02d}_{mod_type[1]:02d}"
                )
                return True
        self.logger.error(
            f"Failed to upload firmware type {mod_type[0]:02d}_{mod_type[1]:02d}"
        )
        return False

    async def flash_module_firmware(self, mod_list) -> bool:
        """Update module with uploaded firmware."""

        for mod in mod_list:
            cmd_str = RT_CMDS.FLASH_MOD_FW.replace("<mod>", chr(mod))
            await self.handle_router_cmd_resp(self.rt_id, cmd_str)
            while await self.in_program_mode():
                await asyncio.sleep(0.5)
                await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.MOD_FLASH_STAT)
                await self.send_fw_update_protocol(
                    mod, self.rt_msg._resp_msg.decode("iso8859-1")
                )

            await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.MOD_FLASH_STAT)
            await self.send_fw_update_protocol(
                mod, self.rt_msg._resp_msg.decode("iso8859-1")
            )
            self.logger.info(f"Update of module {mod} finished")
        return "OK"

    async def send_fw_update_protocol(self, mod, protocol):
        """Send update status protocol to ip client."""
        plen_l = len(protocol) & 0xFF
        plen_h = len(protocol) >> 8
        stat_msg = (
            API_RESPONSE.modfw_flash_stat.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(mod))
            .replace("<lenl>", chr(plen_l))
            .replace("<lenh>", chr(plen_h))
            .replace("<protocol>", protocol)
        )
        await self.api_srv.hdlr.send_api_response(stat_msg, 1)

    async def in_program_mode(self) -> bool:
        """Return True while in program mode."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_GLOB_MODE)
        return self.rt_msg._resp_msg[0] == SYS_MODES.Update

    def parse_event(self, rt_resp: bytes):
        """Handle router responses in API mode to seperate events"""
        resp_msg = RtResponse(self, rt_resp)
        if not (resp_msg._crc_ok):
            self.logger.warning(
                f"Invalid router message crc, message: {resp_msg.resp_data}"
            )
            return
        if resp_msg.resp_cmd == RT_RESP.MIRR_STAT:
            mod_id = resp_msg.resp_data[0]
            return self.rtr.get_module(mod_id).update_status(resp_msg.resp_data)
