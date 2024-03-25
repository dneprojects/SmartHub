import struct
import const
import asyncio
from asyncio.streams import StreamReader, StreamWriter

from const import RT_CMDS, API_CATEGS
import logging
from logging.handlers import RotatingFileHandler
from messages import ApiMessage
from data_hdlr import DataHdlr
from settings_hdlr import SettingsHdlr
from actions_hdlr import ActionsHdlr
from forward_hdlr import ForwardHdlr
from files_hdlr import FilesHdlr
from setup_hdlr import SetupHdlr
from admin_hdlr import AdminHdlr
from router import HbtnRouter
from event_server import EventServer

# GPIO23, Pin 16: switch input, unpressed == 1
# GPIO13, Pin 33: red
# GPIO19, Pin 35: green
# GPIO26, Pin 37: blue


class ApiServer:
    """Holds shared data, base router, event handler, and serial interface"""

    def __init__(self, loop, sm_hub, rt_serial) -> None:
        self.loop = loop
        self.sm_hub = sm_hub
        self.logger = logging.getLogger(__name__)
        self._rt_serial: tuple[StreamReader, StreamWriter] = rt_serial
        self._opr_mode: bool = True  # Allows explicitly setting operate mode off
        self.routers = []
        self.routers.append(HbtnRouter(self, 1))
        self.api_msg = ApiMessage(self, const.def_cmd, const.def_len)
        self._running = True
        self._client_ip: str = ""
        self._hass_ip: str = ""
        self.is_addon: bool = False
        self.mirror_mode_enabled: bool = True
        self.event_mode_enabled: bool = True
        self._api_cmd_processing: bool = False  # Blocking of config server io requests
        self._netw_blocked: bool = False  # Blocking of network api server request
        self._auto_restart_opr: bool = False  # Automatic restart of Opr after api call
        self._init_mode: bool = True
        self._first_api_cmd: bool = True
        self.is_offline: bool = False

    async def get_initial_status(self):
        """Starts router object and reads complete system status"""
        self.hdlr = DataHdlr(self)
        self.evnt_srv = EventServer(self)
        await self.set_initial_server_mode()
        await self.routers[0].get_full_system_status()
        self.logger.info(
            f"API server, router, and {len(self.routers[0].modules)} modules initialized"
        )
        self._init_mode = False

    async def handle_api_command(
        self, ip_reader: StreamReader, ip_writer: StreamWriter
    ):
        """Network server handler to receive api commands."""
        self.ip_writer = ip_writer
        rt = 1

        while self._running:
            self._api_cmd_processing = False
            self._auto_restart_opr = False
            block_time = 0
            while self._netw_blocked | self.evnt_srv.busy_starting:
                # wait for end of block
                await asyncio.sleep(1)
                block_time += 1
            if block_time > 0:
                self.logger.debug(
                    f"Waited for {block_time} seconds in blocked API mode"
                )

            # Read api command from network
            pre = await ip_reader.readexactly(3)
            self._api_cmd_processing = True
            c_len = int(pre[2] << 8) + int(pre[1])
            request = await ip_reader.readexactly(c_len - 3)

            # Block api commands until everthing is setup the first time
            if self._first_api_cmd:
                self._netw_blocked = True
                self._first_api_cmd = False
                self.logger.debug("Network blocked for first initialization")

            # Create and process message object
            self.api_msg = ApiMessage(self, pre + request, c_len)
            success = True
            if self.api_msg._crc_ok:
                # self._netw_blocked = True
                rt = self.api_msg.get_router_id()
                self.logger.debug(
                    f"Processing network API command: {self.api_msg._cmd_grp} {struct.pack('<h', self.api_msg._cmd_spec)[1]} {struct.pack('<h', self.api_msg._cmd_spec)[0]}  Module: {self.api_msg._cmd_p5}  Args: {self.api_msg._cmd_data}"
                )
                match self.api_msg._cmd_grp:
                    case API_CATEGS.DATA:
                        self.hdlr = DataHdlr(self)
                        self._auto_restart_opr = True
                    case API_CATEGS.SETTINGS:
                        self.hdlr = SettingsHdlr(self)
                        self._auto_restart_opr = True
                    case API_CATEGS.ACTIONS:
                        self.hdlr = ActionsHdlr(self)
                        await self.set_operate_mode(rt)
                    case API_CATEGS.FILES:
                        self.hdlr = FilesHdlr(self)
                        await self.set_server_mode(rt)
                    case API_CATEGS.SETUP:
                        self.hdlr = SetupHdlr(self)
                        await self.set_server_mode(rt)
                    case API_CATEGS.ADMIN:
                        self.hdlr = AdminHdlr(self)
                        await self.set_server_mode(rt)
                    case API_CATEGS.FORWARD:
                        self.hdlr = ForwardHdlr(self)
                    case _:
                        response = f"Unknown API command group: {self.api_msg._cmd_grp}"
                        success = False
                await self.hdlr.process_message()
            else:
                response = "Network crc error"
                success = False

            if success:
                response = self.hdlr.response
                self.logger.debug(f"API call returned: {response}")
            else:
                self.logger.warning(f"API call failed: {response}")
            await self.respond_client(response)  # Aknowledge the api command at last
            if self._auto_restart_opr & (not self._opr_mode) & (not self._init_mode):
                await self.set_operate_mode(rt)
            if self._netw_blocked:
                self._netw_blocked = False
                self.logger.debug("Network block released")
            await asyncio.sleep(0)  # pause for other processes to be scheduled

        self.sm_hub.restart_hub(False)

    async def shutdown(self, rt, restart_flg):
        """Terminating all tasks and self."""
        await self.sm_hub.conf_srv.runner.cleanup()
        await self.set_server_mode(rt)
        await self.routers[rt - 1].flush_buffer()
        self.sm_hub.q_srv._q_running = False
        self._running = False
        self._auto_restart_opr = False

    async def respond_client(self, response):
        """Send api command response"""

        self.api_msg.resp_prepare_std(response)
        self.logger.debug(f"API network response: {self.api_msg._rbuffer}")
        self.ip_writer.write(self.api_msg._rbuffer)
        await self.ip_writer.drain()

    async def send_status_to_client(self):
        """Send api status response"""

        self.logger.debug(f"API network response: {self.api_msg._rbuffer}")
        self.ip_writer.write(self.api_msg._rbuffer)
        await self.ip_writer.drain()

    async def block_network_if(self, rt_no, set_block):
        """Set or reset API mode pause."""

        if self._opr_mode & set_block:
            api_time = 0
            while self._api_cmd_processing:
                # wait for end of api command handling
                await asyncio.sleep(0.2)
                api_time += 0.2
            self._netw_blocked = True
            if api_time > 0:
                self.logger.debug(
                    f"Waited for {api_time} seconds for finishing API command"
                )
            await self.set_server_mode(rt_no)
            self.logger.debug("Block API mode")
        if not set_block:
            self._netw_blocked = False
            await self.set_operate_mode(rt_no)
            self.logger.debug("Release API mode block")

    async def set_operate_mode(self, rt_no=1) -> bool:
        """Turn on operate mode: enable router events."""
        # Client ip needed for event handling;
        # method "get_extra_info" is only implemented for writer object
        if self._init_mode:
            self.logger.debug("Skipping set Operate mode due to init_mode")
            return True
        if "ip_writer" not in self.__dir__():
            # no command received yet
            self._opr_mode = False
            return False
        self._client_ip = self.ip_writer.get_extra_info("peername")[0]
        self.is_addon = self._client_ip == self.sm_hub.get_host_ip()
        # SmartHub running with Home Assistant, use internal websocket
        if self._opr_mode & self.evnt_srv.running():
            return True
        if self._opr_mode:
            self.logger.debug("Already in Operate mode, recovering event server")
            await self.evnt_srv.start()
            await asyncio.sleep(0.1)
            return self._opr_mode
        # Send command to router
        m_chr = chr(int(self.mirror_mode_enabled))
        e_chr = chr(int(self.event_mode_enabled))
        cmd = RT_CMDS.SET_OPR_MODE.replace("<mirr>", m_chr).replace("<evnt>", e_chr)
        await self.hdlr.handle_router_cmd_resp(rt_no, cmd)
        # if self.hdlr.rt_msg._resp_code == 133:
        self.logger.info("--- Switched to Operate mode")
        self._opr_mode = True
        # Start event handler
        await self.evnt_srv.start()
        await asyncio.sleep(0.1)
        return self._opr_mode

    async def reinit_opr_mode(self, rt_no, mode) -> str:
        """Force stop operate mode and restart."""
        if not mode:
            # Start of re-init with mode == 0
            self._init_mode = True
            self.logger.info("--- Starting intialization")
            self.logger.debug(
                "Stopping EventSrv task, setting Srv mode for initialization, doing rollover"
            )
            await asyncio.sleep(0.1)
            root_file_hdlr: RotatingFileHandler = logging.root.handlers[1]  # type: ignore
            root_file_hdlr.doRollover()  # Open new log file
            self.logger.debug(
                "Stopping EventSrv task, setting Srv mode for initialization, rollover done"
            )
            await asyncio.sleep(0.5)  # wait for anything async to complete
            await self.set_initial_server_mode()
            return "Init mode set"
        else:
            # finishing re-init with mode == 1
            self._init_mode = False
            self.logger.debug("Re-initializing EventSrv task")
            # await self.evnt_srv.stop()
            # await self.evnt_srv.close_websocket()
            # self.logger.debug("Websocket entry deleted for reinit")
            await self.evnt_srv.start()
            await asyncio.sleep(0.1)
            await self.set_operate_mode(rt_no)
            self.logger.info("--- Initialization finished")
            return "Init mode reset"

    async def set_server_mode(self, rt_no=1) -> bool:
        """Turn on client/server mode: disable router events"""
        if not (self._opr_mode):
            return True
        if self._init_mode:
            self.logger.debug("Skipping set Client/Server mode due to init_mode")
            return True

        # Disable mirror first, then stop event handler
        # Serial reader still used by event server
        await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.SET_SRV_MODE)
        await self.evnt_srv.stop()
        self._opr_mode = False
        self.logger.info("--- Switched to Client/Server mode")
        return not self._opr_mode

    async def set_initial_server_mode(self, rt_no=1) -> None:
        """Turn on server mode: disable router events"""
        self._init_mode = True
        self._opr_mode = False
        await self.hdlr.handle_router_cmd_resp(rt_no, RT_CMDS.SET_SRV_MODE)
        await self.evnt_srv.stop()
        self.logger.debug("API mode turned off initially")


class ApiServerMin(ApiServer):
    """Holds shared data, base router, event handler, and serial interface"""

    def __init__(self, loop, sm_hub) -> None:
        self.loop = loop
        self.sm_hub = sm_hub
        self.logger = logging.getLogger(__name__)
        self._rt_serial: None = None
        self._opr_mode: bool = False  # Always off
        self.hdlr = []
        self.routers = []
        self.routers.append(HbtnRouter(self, 1))
        self.is_addon: bool = False
        self.mirror_mode_enabled: bool = True
        self.event_mode_enabled: bool = True
        self._api_cmd_processing: bool = False  # Blocking of config server io requests
        self._netw_blocked: bool = True  # Blocking of network api server request
        self._auto_restart_opr: bool = False  # Automatic restart of Opr after api call
        self._init_mode: bool = True
        self._first_api_cmd: bool = True
        self.is_offline = True  # Always offline

    async def shutdown(self, rt, restart_flg):
        """Terminating all tasks and self."""
        await self.sm_hub.conf_srv.runner.cleanup()
        self._running = False
        self._auto_restart_opr = False
        self.sm_hub.tg._abort()

    async def start_opr_mode(self, rt_no):
        """Turn on operate mode: enable router events."""
        return self._opr_mode

    async def stop_opr_mode(self, rt_no):
        """Turn on server mode: disable router events"""
        return True

    async def set_initial_srv_mode(self, rt_no):
        """Turn on config mode: disable router events"""
        return
