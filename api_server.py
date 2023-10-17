import struct
import const
import asyncio
from asyncio import StreamReader, StreamWriter

from const import RT_CMDS, MIRROR_CYC_TIME, API_CATEGS
import logging
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

    def __init__(self, loop, smip, rt_serial) -> None:
        self.loop = loop
        self.smip = smip
        self.logger = logging.getLogger(__name__)
        self._rt_serial: (StreamReader, StreamWriter) = rt_serial
        self._api_mode: bool = True  # Allows explicitly setting API mode off
        self.hdlr = []
        self.routers = []
        self.evnt_srv = []
        self._ev_srv_task = []
        self.routers.append(HbtnRouter(self, 1))
        self.api_msg = ApiMessage(self, const.def_cmd, const.def_len)
        self._running = True
        self._client_ip = ""
        self._hass_ip = ""

    def __del__(self):
        """Clean up."""
        del self.smip
        del self.logger
        del self.hdlr
        del self.routers
        del self.evnt_srv
        del self._ev_srv_task
        del self.api_msg

    async def get_initial_status(self):
        """Starts router object and reads complete system status"""
        self.hdlr = DataHdlr(self)
        self.evnt_srv = EventServer(self)
        await self.set_initial_non_api_mode(1)
        await self.routers[0].get_full_status()
        self.logger.info("API server, router, and modules initialized")

    async def handle_api_command(self, ip_reader, ip_writer):
        """Network server handler to receive api commands."""
        self.ip_writer = ip_writer

        while self._running:
            # Read api command from network
            pre = await ip_reader.readexactly(3)
            c_len = int(pre[2] << 8) + int(pre[1])
            request = await ip_reader.readexactly(c_len - 3)

            # Client ip needed for event handling;
            # method "get_extra_info" is only implemented for writer object
            self._client_ip = self.ip_writer.get_extra_info("peername")[0]

            # Create and process message object
            self.api_msg = ApiMessage(self, pre + request, c_len)
            success = True
            if self.api_msg._crc_ok:
                rt = self.api_msg.get_router_id()
                self.logger.info(
                    f"Processing network API command: {self.api_msg._cmd_grp} {struct.pack('<h', self.api_msg._cmd_spec)[1]} {struct.pack('<h', self.api_msg._cmd_spec)[0]}"
                )
                match self.api_msg._cmd_grp:
                    case API_CATEGS.DATA:
                        self.hdlr = DataHdlr(self)
                    case API_CATEGS.SETTINGS:
                        self.hdlr = SettingsHdlr(self)
                    case API_CATEGS.ACTIONS:
                        self.hdlr = ActionsHdlr(self)
                        await self.start_api_mode(rt)
                    case API_CATEGS.FILES:
                        self.hdlr = FilesHdlr(self)
                        await self.stop_api_mode(rt)
                    case API_CATEGS.SETUP:
                        self.hdlr = SetupHdlr(self)
                        await self.stop_api_mode(rt)
                    case API_CATEGS.ADMIN:
                        self.hdlr = AdminHdlr(self)
                        await self.stop_api_mode(rt)
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

            await self.respond_client(response)

    async def shutdown(self, rt, restart_flg):
        """Terminating all tasks and slef."""
        await self.smip.conf_srv.runner.cleanup()
        await self.stop_api_mode(rt)
        await asyncio.sleep(3)
        self.smip.restart(restart_flg)
        self._running = False

    async def respond_client(self, response):
        """Send api command response"""

        self.api_msg.resp_prepare_std(response)
        self.logger.debug(f"API network response: {self.api_msg._rbuffer}")
        self.ip_writer.write(self.api_msg._rbuffer)

    async def send_status_to_client(self):
        """Send api status response"""

        self.logger.debug(f"API network response: {self.api_msg._rbuffer}")
        self.ip_writer.write(self.api_msg._rbuffer)

    async def start_api_mode(self, rt_no):
        """Turn on API mode: enable router events"""
        if self._api_mode & self.routers[rt_no - 1].mirror_running():
            if self._ev_srv_task != []:
                if self._ev_srv_task._state != "FINISHED":
                    return
        if self._api_mode:
            print("\n")
            self.logger.info("Switching to API mode, recovering mirror")
            # if self._ev_srv_task != []:
            #     self._ev_srv_task.cancel()
            #     await asyncio.sleep(0.1)
            if self._ev_srv_task == []:
                self.logger.warning(
                    "No event server registered, start event server task"
                )
                self._ev_srv_task = self.loop.create_task(
                    self.evnt_srv.watch_rt_events(self._rt_serial[0])
                )
                await asyncio.sleep(0.1)
            elif self._ev_srv_task._state == "FINISHED":
                self.logger.warning(
                    "Event server 'finished', restart event server task"
                )
                self._ev_srv_task = self.loop.create_task(
                    self.evnt_srv.watch_rt_events(self._rt_serial[0])
                )
                await asyncio.sleep(0.1)
        else:
            print("\n")
            self.logger.info("Switching to API mode")
            self._api_mode = True
        # Start event handler first, then enable mirror
        if self._ev_srv_task == []:
            self.logger.debug("Start event server task")
            self._ev_srv_task = self.loop.create_task(
                self.evnt_srv.watch_rt_events(self._rt_serial[0])
            )
            await asyncio.sleep(0.1)
        strt_mirr_cmd = RT_CMDS.START_MIRROR.replace(
            "<cyc>", chr(min(round(MIRROR_CYC_TIME * 100), 255))
        )
        await self.hdlr.handle_router_cmd(rt_no, strt_mirr_cmd)
        # await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.START_EVENTS)
        await asyncio.sleep(0.1)

    async def stop_api_mode(self, rt_no):
        """Turn on config mode: disable router events"""
        if not (self._api_mode):
            return
        self._api_mode = False

        # Disable mirror first, then stop event handler
        # await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.STOP_EVENTS)
        await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.STOP_MIRROR)
        self.evnt_srv.evnt_running = False
        await asyncio.sleep(0.5)
        self._ev_srv_task.cancel()
        self.logger.info("API mode terminated successfully")
        self._ev_srv_task = []

    async def set_initial_non_api_mode(self, rt_no):
        """Turn on config mode: disable router events"""
        self._api_mode = False
        self._ev_srv_task = []

        # Disable mirror first, then stop event handler
        await self.hdlr.handle_router_cmd_resp(rt_no, RT_CMDS.STOP_MIRROR)
        self.logger.debug("API mode turned off initially")
