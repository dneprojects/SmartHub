from messages import calc_crc
from os.path import isfile
from const import (
    RT_STAT_CODES,
    DATA_FILES_DIR,
    DATA_FILES_ADDON_DIR,
    RT_CMDS,
)
from router_hdlr import RtHdlr
from module import HbtnModule
from configuration import RouterSettings


class HbtnRouter:
    """Router object, holds status."""

    def __init__(self, api_srv, id: int) -> None:
        self._ready = False
        self._id = id
        self._name = "Router"
        self._in_config_mode: bool = False
        self.recent_mode: int = 0x20
        self.api_srv = api_srv
        self.logger = api_srv.logger
        self.status = b""
        self.status_upload = b""
        self.chan_status = b""
        self.status_idx = []
        self.mod_addrs = []
        self.modules = []
        self.hdlr = RtHdlr(self, self.api_srv)
        self.descriptions: str = ""
        self.smr: bytes = b""
        self.smr_crc: int = 0
        self.smr_upload: bytes = b""
        self.fw_upload: bytes = b""
        self.name: bytes = b""
        self.channels: bytes = b""
        self.channel_list: dict[int, list[int]] = {}
        self.timeout: bytes = b""
        self.groups: bytes = b""
        self.mode_dependencies: bytes = b""
        self.mode0 = 0
        self.user_modes: bytes = b""
        self.serial: bytes = b""
        self.day_night: bytes = b""
        self.version: bytes = b""
        self.date: bytes = b""
        self.settings = []
        self.properties, self.prop_keys = self.get_properties()

    def mirror_running(self) -> bool:
        """Return mirror status based on chan_status."""
        if len(self.chan_status) > 40:
            return self.chan_status[-1] == RT_STAT_CODES.MIRROR_ACTIVE
        return False

    async def get_full_status(self):
        """Load full router status."""
        await self.set_config_mode(True)
        self.status = await self.hdlr.get_rt_full_status()
        self.chan_status = await self.hdlr.get_rt_status()
        self.build_smr()
        self.logger.info("Router initialized")
        modules = await self.hdlr.get_rt_modules()
        return modules

    async def get_full_system_status(self):
        """Startup procedure: wait for router #1, get router info, start modules."""
        from module_hdlr import ModHdlr

        await self.hdlr.waitfor_rt_booted()
        modules = await self.get_full_status()
        self.load_descriptions()

        self.logger.info("Setting up modules...")
        for m_idx in range(modules[0]):
            self.mod_addrs.append(modules[m_idx + 1])
        self.mod_addrs.sort()
        mods_to_remove = []
        for mod_addr in self.mod_addrs:
            try:
                self.modules.append(
                    HbtnModule(
                        mod_addr,
                        self.get_channel(mod_addr),
                        self._id,
                        ModHdlr(mod_addr, self.api_srv),
                        self.api_srv,
                    )
                )
                self.logger.debug(f"   Module {mod_addr} instantiated")
                await self.modules[-1].initialize()
                self.logger.info(f"   Module {mod_addr} initialized")
            except Exception as err_msg:
                self.logger.error(f"   Failed to setup module {mod_addr}: {err_msg}")
                self.modules.remove(self.modules[-1])
                mods_to_remove.append(mod_addr)
                self.logger.warning(f"   Module {mod_addr} removed")
        for mod_addr in mods_to_remove:
            self.mod_addrs.remove(mod_addr)

    async def get_status(self) -> bytes:
        """Returns router channel status"""
        await self.api_srv.set_server_mode(self._id)
        self.chan_status = await self.hdlr.get_rt_status()
        return self.chan_status

    def get_module(self, mod_id: int) -> HbtnModule | None:
        """Return module object."""
        md_idx = self.mod_addrs.index(mod_id)
        if md_idx >= len(self.modules):
            return None
        return self.modules[md_idx]

    def get_modules(self) -> str:
        """Return id, type, and name of all modules."""
        mod_str = ""
        for mod in self.modules:
            mod_str += chr(mod._id) + mod._typ.decode("iso8859-1")
            mod_str += chr(len(mod._name)) + mod._name
        return mod_str

    def get_module_list(self) -> list:
        """Return id, type, and name of all modules in a list."""

        class Mdle:
            """Class for module defs."""

            def __init__(self, id: int, typ: bytes, name: str, fw: str):
                self.id: int = id
                self.typ: bytes = typ
                self.name: str = name
                self.fw: str = fw

        mod_list = []
        for mod in self.modules:
            mod_list.append(Mdle(mod._id, mod._typ, mod._name, mod.get_sw_version()))
        return mod_list

    def get_channel(self, mod_addr: int) -> int:
        """Return router channel of module."""
        for ch_i in range(4):
            if mod_addr in self.channel_list[ch_i + 1]:
                return ch_i + 1
        return 0

    def build_smr(self) -> None:
        """Build SMR file content from status."""
        st_idx = self.status_idx  # noqa: F841
        chan_buf = self.channels
        self.logger.debug(f"self.channels: {chan_buf}")
        chan_list = b""
        ch_idx = 1
        for ch_i in range(4):
            cnt = chan_buf[ch_idx]
            chan_list += chan_buf[ch_idx : ch_idx + cnt + 1]
            ch_idx += cnt + 2

        self.smr = (
            chr(self._id).encode("iso8859-1")
            + chan_list
            + self.timeout
            + self.groups
            + self.mode_dependencies
            + self.name
            + self.user_modes
            + self.serial
            + self.day_night
            + self.version
        )
        self.calc_SMR_crc(self.smr)

    def calc_SMR_crc(self, smr_buf: bytes) -> None:
        """Calculate and store crc of SMR data."""
        self.smr_crc = calc_crc(smr_buf)

    async def set_config_mode(self, set_not_reset: bool) -> None:
        """Switches to config mode and back."""
        if self.api_srv._init_mode:
            return
        if set_not_reset:
            if not self.api_srv._opr_mode:
                # already in Srv mode, config mode is set in router
                return
            if self.api_srv._opr_mode:
                self.logger.error("Not in Srv mode when switching to config mode!")
                await self.api_srv.set_server_mode(self._id)
        return

    async def get_boot_stat(self) -> bytes:
        """Ask for boot errors."""
        rt_command = RT_CMDS.GET_RT_BOOTSTAT
        await self.hdlr.handle_router_cmd_resp(self._id, rt_command)
        return self.hdlr.rt_msg._resp_msg

    async def flush_buffer(self) -> None:
        """Empty router buffer."""
        await self.hdlr.handle_router_cmd(self._id, RT_CMDS.CLEAR_RT_SENDBUF)

    async def set_module_group(self, mod: int, grp: int) -> None:
        """Store new module group setting into router."""
        self.groups = self.groups[:mod] + int.to_bytes(grp) + self.groups[mod + 1 :]
        await self.set_config_mode(True)
        await self.hdlr.send_rt_mod_group(mod, grp)
        await self.set_config_mode(False)

    def pack_descriptions(self) -> str:
        """Pack descriptions to string with lines."""
        out_buf = ""
        desc_buf = self.descriptions.encode("iso8859-1")
        desc_no = int.from_bytes(desc_buf[0:2], "little")
        for ptr in range(4):
            out_buf += f"{desc_buf[ptr]};"
        out_buf += "\n"
        ptr = 4
        for desc_i in range(desc_no):
            l_len = desc_buf[ptr + 8] + 9
            line = desc_buf[ptr : ptr + l_len]
            for li in range(l_len):
                out_buf += f"{line[li]};"
            out_buf += "\n"
            ptr += l_len
        return out_buf

    def save_descriptions(self) -> None:
        """Save descriptions to file."""
        file_name = f"Rtr_{self._id}_descriptions.smb"
        file_path = DATA_FILES_ADDON_DIR
        if not isfile(file_path + file_name):
            file_path = DATA_FILES_DIR
            self.logger.debug(f"Add-on config path not found, using {file_path}")
        try:
            fid = open(file_path + file_name, "w")
            desc_buf = self.pack_descriptions()
            fid.write(desc_buf)
            fid.close()
            self.logger.info(f"Descriptions saved to {file_path + file_name}")
        except Exception as err_msg:
            self.logger.error(
                f"Error saving description to file {file_path + file_name}: {err_msg}"
            )
            fid.close()

    def load_descriptions(self) -> None:
        """Load descriptions from file."""
        self.descriptions = ""
        file_name = f"Rtr_{self._id}_descriptions.smb"
        file_path = DATA_FILES_ADDON_DIR
        if not isfile(file_path + file_name):
            file_path = DATA_FILES_DIR
            self.logger.debug(f"Add-on config path not found, using {file_path}")
        if isfile(file_path + file_name):
            try:
                fid = open(file_path + file_name, "r")
                line = fid.readline().split(";")
                for ci in range(len(line) - 1):
                    self.descriptions += chr(int(line[ci]))
                desc_no = int(line[0]) + 256 * int(line[1])
                for li in range(desc_no):
                    line = fid.readline().split(";")
                    for ci in range(len(line) - 1):
                        self.descriptions += chr(int(line[ci]))
                fid.close()
                self.logger.info(f"Descriptions loaded from {file_path + file_name}")
            except Exception as err_msg:
                self.logger.error(
                    f"Error loading description to file {file_path + file_name}: {err_msg}"
                )
                fid.close()
        else:
            self.logger.warning(f"Descriptions file {file_path + file_name} not found")

    def unpack_descriptions(self, lines: str) -> None:
        """Load descriptions from string."""
        line = lines[0].split(";")
        for ci in range(len(line) - 1):
            self.descriptions += chr(int(line[ci]))
        desc_no = int(line[0]) + 256 * int(line[1])
        for li in range(desc_no):
            line = lines[li + 1].split(";")
            for ci in range(len(line) - 1):
                self.descriptions += chr(int(line[ci]))
        self.logger.info("Descriptions restored")

    def save_firmware(self, bin_data) -> None:
        "Save firmware binary to file and fw_data buffer."
        file_path = DATA_FILES_DIR
        file_name = f"Firmware_{bin_data[0]:02d}_{bin_data[1]:02d}.bin"
        fid = open(file_path + file_name, "wb")
        fid.write(bin_data)
        fid.close()
        self.fw_upload = bin_data
        self.logger.debug(f"Firmware file {file_path + file_name} saved")

    def load_firmware(self, mod_type) -> bool:
        "Load firmware binary from file to fw_data buffer."
        if isinstance(mod_type, str):
            mod_type = mod_type.encode("iso8859-1")
        file_path = DATA_FILES_DIR
        file_name = f"Firmware_{mod_type[0]:02d}_{mod_type[1]:02d}.bin"
        if isfile(file_path + file_name):
            fid = open(file_path + file_name, "rb")
            self.fw_upload = fid.read()
            fid.close()
            self.logger.debug(f"Firmware file {file_path + file_name} loaded")
            return True
        self.fw_upload = b""
        self.logger.error(
            f"Failed to load firmware file 'Firmware_{mod_type[0]:02d}_{mod_type[1]:02d}.bin'"
        )
        return False

    def get_router_settings(self) -> RouterSettings:
        """Collect all settings and prepare for config server."""
        self.settings = RouterSettings(self)
        return self.settings

    async def set_settings(self, settings: RouterSettings) -> None:
        """Store settings into router."""
        self.settings = settings
        if self.api_srv.is_offline:
            self._name = settings.name
            self.user_modes = (
                b"\n"
                + settings.user1_name.encode("iso8859-1")
                + b"\n"
                + settings.user2_name.encode("iso8859-1")
            )
            self.mode_dependencies = settings.mode_dependencies
        else:
            await self.api_srv.block_network_if(self._id, True)
            await self.hdlr.send_rt_name(settings.name)
            await self.hdlr.send_mode_names(settings.user1_name, settings.user2_name)
            await self.hdlr.send_rt_group_deps(settings.mode_dependencies[1:])
            # await self.hdlr.rt_reboot()
            # await asyncio.sleep(6)
            await self.get_full_status()
            await self.api_srv.block_network_if(self._id, False)

    def set_descriptions(self, settings: RouterSettings) -> None:
        """Store names into router descriptions."""
        # groups, group names, mode dependencies
        self.descriptions = settings.set_glob_descriptions()
        self.save_descriptions()

    def get_properties(self) -> tuple[dict[str, int], list[str]]:
        """Return number of flags, commands, etc."""

        props: dict = {}
        props["groups"] = 16
        props["glob_flags"] = 16
        props["coll_cmds"] = 16

        keys = ["groups", "glob_flags", "coll_cmds"]
        no_keys = 0
        for key in keys:
            if props[key] > 0:
                no_keys += 1
        props["no_keys"] = no_keys

        return props, keys

    async def cleanup_descriptions(self) -> None:
        """If descriptions in desc file, store them into router and remove them from file."""
        self.logger.info("Description storage in router not yet implemented")
        pass
