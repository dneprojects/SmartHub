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
from messages import RtMessage, RtResponse


class RtHdlr(HdlrBase):
    """Handling of incoming router messages."""

    def __init__(self, rtr, api_srv) -> None:
        """Creates handler object with msg infos and serial interface"""
        self.rtr = rtr
        self.api_srv = api_srv
        self.ser_if = self.api_srv._rt_serial
        self.rt_id = rtr._id
        self.logger = logging.getLogger(__name__)
        self.rt_msg = RtMessage(self, 0, "   ")  # initialize empty object

    async def rt_reboot(self):
        """Initiates a router reboot"""
        self.logger.info(f"Router {self.rt_id} will be rebooted, please wait...")
        await self.handle_router_cmd(self.rt_id, RT_CMDS.RT_REBOOT)
        router_running = False
        await asyncio.sleep(2)
        # while not (router_running):
        #     # Ask for mode 0, if returned, router is up
        #     # await self.rt_msg.get_router_response()
        #     ret_msg = await self.get_mode(0)
        #     router_running = len(ret_msg) > 0
        self.logger.info(f"Router {self.rt_id} rebooted")

    async def set_mode(self, group: int, new_mode):
        """Changes system or group mode to new_mode"""
        if group == 0:
            # System mode
            rt_cmd = RT_CMDS.SET_GLOB_MODE
            rt_cmd = rt_cmd.replace("<md>", chr(new_mode))
            await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
            self.rtr._in_config_mode = new_mode == SYS_MODES.Config
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

        if (len(self.rt_msg._resp_msg) > 1) & (group != 255):
            self.logger.warning(
                f"Response to get mode {group} command too long: {self.rt_msg._resp_buffer}"
            )
            if (b_len := len(self.ser_if[0]._buffer)) > 0:
                chunk = await self.ser_if[0].read(b_len)  # empty buffer
            other_responses = True
            while other_responses:
                await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
                other_responses = not (self.rt_msg._resp_buffer[3] == ord(rt_cmd[-2]))
                self.logger.info(f"Other response: {self.rt_msg._resp_buffer[:5]}")
        elif group == 0:
            self.rtr.mode0 = self.rt_msg._resp_msg[0]
        return self.rt_msg._resp_msg

    async def get_rt_channels(self) -> bytes:
        """Get router channels."""
        await asyncio.sleep(0.2)
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_CHANS)
        if self.rt_msg._resp_code == 133:
            # switch to Srv mode made without response, may be still in buffer
            await self.handle_router_resp(self.rt_id)
        self.rtr.channels = self.rt_msg._resp_msg
        self.rtr.mode0 = self.rtr.channels[1]
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
        await self.rt_msg.api_hdlr.api_srv.stop_opr_mode(1)
        # await asyncio.sleep(0.3)
        # await self.handle_router_cmd_resp(
        #     1, RT_CMDS.SET_GLOB_MODE.replace("<md>", chr(75))
        # )
        await asyncio.sleep(0.3)
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
        """Get router system status. Used in Opr mode"""
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
        # Deal with option "L", makes 1 byte difference: take value relative to the end
        if self.rt_msg._resp_buffer[-42] != 0:
            # mode 0 not zero, should be 'K', config while reading status
            return self.rt_msg._resp_buffer[-43:-1]
        self.logger.warning(
            "Router channel status with mode 0 = 0, return stored value"
        )
        return self.rtr.chan_status

    async def get_rt_modules(self):
        """Get all modules connected to router."""
        await self.rt_msg.api_hdlr.api_srv.stop_opr_mode(1)
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_MODULES)
        return self.rt_msg._resp_msg

    async def send_rt_channels(self, rt_channels):
        """Send router channels."""
        cmd_str = RT_CMDS.SEND_RT_CHANS + rt_channels.decode("iso8859-1") + "\xff"
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_timeout(self, rt_timeout):
        """Send router timeout."""
        tout = chr(rt_timeout)
        cmd_str = RT_CMDS.SEND_RT_TIMEOUT.replace("<tout>", tout)
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_group_no(self, rt_groups):
        """Send router group no."""
        cmd_str = RT_CMDS.SEND_RT_GRPNO + rt_groups.decode("iso8859-1") + "\xff"
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_mod_group(self, mod, grp):
        """Send module group membership."""
        cmd_str = RT_CMDS.SET_MOD_GROUP.replace("<mod>", chr(mod)).replace(
            "<grp>", chr(grp)
        )
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_group_deps(self, rt_groupdep):
        """Send router mode dependencies."""
        cmd_str = RT_CMDS.SEND_RT_GRPMODE_DEP + rt_groupdep.decode("iso8859-1") + "\xff"
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_name(self, rt_name):
        """Send router name."""
        if type(rt_name) == bytes:
            rt_name = rt_name.decode("iso8859-1")
        rt_name = rt_name + (" " * (32 - len(rt_name)))
        await self.rtr.set_config_mode(True)
        for part in range(4):
            cmd_str = (
                RT_CMDS.SEND_RT_NAME
                + chr(part * 8)
                + rt_name[part * 8 : (part + 1) * 8]
                + "\xff"
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd_str)
            await asyncio.sleep(0.2)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_mode_names(self, umd_name1, umd_name2):
        """Send user mode names."""
        if type(umd_name1) == bytes:
            umd_name1 = umd_name1.decode("iso8859-1")
        if type(umd_name2) == bytes:
            umd_name2 = umd_name2.decode("iso8859-1")
        umd_name1 = umd_name1 + (" " * (10 - len(umd_name1)))
        umd_name2 = umd_name2 + (" " * (10 - len(umd_name2)))
        cmd_str = RT_CMDS.SEND_RT_MODENAM.replace("<umd>", "\x01") + umd_name1 + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        cmd_str = RT_CMDS.SEND_RT_MODENAM.replace("<umd>", "\x02") + umd_name2 + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_rt_day_night_changes(self, day_night):
        """Send day night settings."""
        cmd_str = RT_CMDS.SEND_RT_DAYNIGHT + day_night.decode("iso8859-1") + "\xff"
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_full_status(self):
        """Send full router status from uploaded smr."""
        self.logger.debug("Starting SMR data transfer into router")
        smr_ptr = 1
        mod_cnt = []
        mod_cnt.append(self.rtr.smr_upload[1])
        mod_cnt.append(self.rtr.smr_upload[1])
        rt_channels = b""
        for ch in range(4):
            ch_count = self.rtr.smr_upload[smr_ptr]
            rt_channels += (
                int.to_bytes(ch + 1)
                + int.to_bytes(ch_count)
                + self.rtr.smr_upload[smr_ptr + 1 : smr_ptr + 1 + ch_count]
            )
            smr_ptr += 1 + ch_count
        await self.send_rt_channels(rt_channels)
        rt_tout = self.rtr.smr_upload[smr_ptr]
        smr_ptr += 1
        await self.send_rt_timeout(rt_tout)
        rt_groups, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        await self.send_rt_group_no(rt_groups)
        rt_groupdep, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        await self.send_rt_group_deps(rt_groupdep)
        rt_name, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        await self.send_rt_name(rt_name)
        umd_name1, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        umd_name2, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        await self.send_mode_names(umd_name1, umd_name2)
        rt_serial, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        rt_daynight, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        await self.send_rt_day_night_changes(rt_daynight)
        # rt_fw_version, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        self.logger.debug("SMR data transferred into router")
        await self.rt_reboot()

    def get_smr_item(self, smr_bytes: bytes, smr_ptr: int) -> (bytes, int):
        """Get one item from smr bytes."""
        item_len = smr_bytes[smr_ptr]
        item = smr_bytes[smr_ptr + 1 : smr_ptr + item_len + 1]
        smr_ptr += item_len + 1
        return item, smr_ptr

    async def restart_system(self):
        """Restart router after firmware update."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
        self.logger.info(f"Router {self.rt_id} system restarted")

    async def upload_router_firmware(self, rt_type) -> bool:
        """Upload router firmware to router, returns True for success."""
        fw_buf = self.rtr.fw_upload
        fw_len = len(fw_buf)
        if fw_len == 0:
            self.logger.error(f"Failed to upload / flash router")
            return "ERROR"

        pkg_len = 13
        no_pkgs = int(fw_len / pkg_len)
        rest_len = fw_len - no_pkgs * pkg_len
        if rest_len > 0:
            no_pkgs += 1
        self.logger.info(
            f"Updating router {self.rt_id}: length {fw_len} bytes, {no_pkgs} packages"
        )
        stat_msg = API_RESPONSE.rtfw_flash_stat.replace("<rtr>", chr(self.rt_id))
        cmd_str = RT_CMDS.SET_ISP_MODE.replace("<lenl>", chr(fw_len & 0xFF)).replace(
            "<lenh>", chr(fw_len >> 8)
        )

        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_buffer[-self.rt_msg._resp_buffer[2] + 4 : -1]
        if (resp[0] == 0x42) & (resp[1] == 0x4C) & (resp[2] == 0) & (resp[3] == 0):
            self.logger.warning("Router set into update mode")
        else:
            self.logger.error(f"Failed to enter router ISP mode")
            await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
            self.logger.info(f"Router restarted")
            return "ERROR"

        await asyncio.sleep(1)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_buffer[-self.rt_msg._resp_buffer[2] + 4 : -1]
        if (resp[0] == 0x42) & (resp[1] == 0x4C) & (resp[2] == 0) & (resp[3] == 0):
            self.logger.warning("Router starting to update")
        else:
            self.logger.error(f"Failed to enter router ISP mode")
            await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
            self.logger.info(f"Router restarted")
            return "ERROR"
        cmd_org = RT_CMDS.UPDATE_RT_PKG
        stat_msg = stat_msg.replace("<pkgs>", chr(no_pkgs + 1))
        for pi in range(no_pkgs):
            pkg_low_target = (pi + 1) & 0xFF
            pkg_high_target = (pi + 1) >> 8
            if pi < (no_pkgs - 1):
                cmd_str = (
                    cmd_org.replace("<len>", chr(pkg_len + 8))
                    .replace("<pno>", chr(pkg_low_target))
                    .replace(
                        "<buf>",
                        fw_buf[pi * pkg_len : (pi + 1) * pkg_len].decode("iso8859-1"),
                    )
                )
            else:
                # last package with < pkg_len
                cmd_str = (
                    cmd_org.replace("<len>", chr(rest_len + 8))
                    .replace("<pno>", chr(pkg_low_target))
                    .replace("<buf>", fw_buf[pi * pkg_len :].decode("iso8859-1"))
                )
            await self.handle_router_cmd_resp(self.rt_id, cmd_str)
            resp_code = self.rt_msg._resp_code
            resp_msg = self.rt_msg._resp_buffer[-self.rt_msg._resp_buffer[2] + 4 : -1]
            if (resp_code == 201) & (len(resp_msg) > 3):
                if (resp_msg[0] == 0x42) & (resp_msg[1] == 0x4C):
                    pkg_low = resp_msg[2]
                    pkg_high = resp_msg[3]
                    await self.api_srv.hdlr.send_api_response(
                        stat_msg.replace("<pkgl>", chr(pkg_low)).replace(
                            "<pkgh>", chr(pkg_high)
                        ),
                        RT_STAT_CODES.PKG_OK,
                    )
                else:
                    self.logger.error(
                        f"Failed to flash router, returned message 201: {resp_msg}"
                    )
                    await self.handle_router_cmd_resp(
                        self.rt_id, RT_CMDS.SYSTEM_RESTART
                    )
                    self.logger.info(f"Router restarted")
                    return "ERROR"
            else:
                self.logger.error(f"Failed to flash router, returned empty message 201")
                await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
                self.logger.info(f"Router restarted")
                return "ERROR"
        self.logger.info(f"Successfully uploaded and flashed router firmware")
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
        self.logger.info(f"Router restarted")
        return "OK"

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

    async def forward_message(self, src_rt: int, fwd_cmd: bytes) -> bytes:
        """Forward message from other router."""
        # insert src_rt into command
        fwd_cmd = fwd_cmd.decode("iso8859-1")
        fwd_cmd = (
            f"\x2a<rtr>\xff"
            + fwd_cmd[:4]
            + chr(self.rt_id)
            + fwd_cmd[5:7]
            + chr(src_rt)
            + fwd_cmd[8:]
        )
        await self.handle_router_cmd_resp(self.rt_id, fwd_cmd)
        return self.rt_msg._resp_msg

    def parse_event(self, rt_resp: bytes):
        """Handle router responses in API mode to seperate events"""
        resp_msg = RtResponse(self, rt_resp)
        if not (resp_msg._crc_ok):
            self.logger.warning(
                f"Invalid Opr mode router message crc, message: {resp_msg.resp_data}"
            )
            return
        if resp_msg.resp_cmd == RT_RESP.MIRR_STAT:
            mod_id = resp_msg.resp_data[0]
            if mod_id in self.rtr.mod_addrs:
                return self.rtr.get_module(mod_id).update_status(resp_msg.resp_data)
            return
