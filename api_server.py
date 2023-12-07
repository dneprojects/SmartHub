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

    def __init__(self, loop, sm_hub, rt_serial) -> None:
        self.loop = loop
        self.sm_hub = sm_hub
        self.logger = logging.getLogger(__name__)
        self._rt_serial: (StreamReader, StreamWriter) = rt_serial
        self._opr_mode: bool = False  # Allows explicitly setting operate mode off
        self.hdlr = []
        self.routers = []
        self.routers.append(HbtnRouter(self, 1))
        self.evnt_srv = []
        self._ev_srv_task = []
        self.api_msg = ApiMessage(self, const.def_cmd, const.def_len)
        self._running = True
        self._client_ip = ""
        self._hass_ip = ""
        self.mirror_mode_enabled = True
        self.event_mode_enabled = True
        self._api_cmd_processing = False  # For blocking of config server io requests
        self._netw_blocked = False  # For blocking of network api server request
        self._auto_restart_opr = False  # For automatic restart of Opr after api call

    async def get_initial_status(self):
        """Starts router object and reads complete system status"""
        self.hdlr = DataHdlr(self)
        self.evnt_srv = EventServer(self)
        await self.set_initial_srv_mode(1)
        await self.routers[0].get_full_system_status()
        self.logger.info(
            f"API server, router, and {len(self.routers[0].modules)} modules initialized"
        )

    async def handle_api_command(self, ip_reader, ip_writer):
        """Network server handler to receive api commands."""
        self.ip_writer = ip_writer

        while self._running:
            self._api_cmd_processing = False
            self._auto_restart_opr = False
            block_time = 0
            while self._netw_blocked:
                # wait for end of block
                await asyncio.sleep(1)
                block_time += 1
            if block_time > 0:
                self.logger.info(f"Waited for {block_time} seconds in blocked API mode")

            # Read api command from network
            pre = await ip_reader.readexactly(3)
            self._api_cmd_processing = True
            c_len = int(pre[2] << 8) + int(pre[1])
            request = await ip_reader.readexactly(c_len - 3)

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
                        self._auto_restart_opr = True
                    case API_CATEGS.SETTINGS:
                        self.hdlr = SettingsHdlr(self)
                        self._auto_restart_opr = True
                    case API_CATEGS.ACTIONS:
                        self.hdlr = ActionsHdlr(self)
                        await self.start_opr_mode(rt)
                    case API_CATEGS.FILES:
                        self.hdlr = FilesHdlr(self)
                        await self.stop_opr_mode(rt)
                    case API_CATEGS.SETUP:
                        self.hdlr = SetupHdlr(self)
                        await self.stop_opr_mode(rt)
                    case API_CATEGS.ADMIN:
                        self.hdlr = AdminHdlr(self)
                        await self.stop_opr_mode(rt)
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
            if self._auto_restart_opr & (not self._opr_mode):
                await self.start_opr_mode(rt)

    async def shutdown(self, rt, restart_flg):
        """Terminating all tasks and self."""
        await self.sm_hub.conf_srv.runner.cleanup()
        await self.stop_opr_mode(rt)
        await asyncio.sleep(3)
        self.sm_hub.restart(restart_flg)
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
                self.logger.info(
                    f"Waited for {api_time} seconds for finishing API command"
                )
            await self.stop_opr_mode(rt_no)
            self.logger.info("Block API mode")
        if not set_block:
            self._netw_blocked = False
            await self.start_opr_mode(rt_no)
            self.logger.info("Release API mode block")

    async def start_opr_mode(self, rt_no):
        """Turn on operate mode: enable router events."""
        # Client ip needed for event handling;
        # method "get_extra_info" is only implemented for writer object
        self._client_ip = self.ip_writer.get_extra_info("peername")[0]
        mirror_running = self.routers[rt_no - 1].mirror_running()
        if self._opr_mode & mirror_running:  # mirror running is old
            if self._ev_srv_task != []:
                if self._ev_srv_task._state != "FINISHED":
                    return
        if self._opr_mode:
            print("\n")
            self.logger.info("Already in Opr mode, recovering mirror")
            if self._ev_srv_task == []:
                self.logger.warning("No EventSrv registered, start event server task")
                self._ev_srv_task = self.loop.create_task(
                    self.evnt_srv.watch_rt_events(self._rt_serial[0])
                )
                await asyncio.sleep(0.1)
            elif self._ev_srv_task._state == "FINISHED":
                self.logger.warning("EventSrv 'finished', restart event server task")
                self._ev_srv_task = self.loop.create_task(
                    self.evnt_srv.watch_rt_events(self._rt_serial[0])
                )
                await asyncio.sleep(0.1)
        else:
            # New switch -----------
            m_chr = chr(int(self.mirror_mode_enabled))
            e_chr = chr(int(self.event_mode_enabled))
            cmd = RT_CMDS.SET_OPR_MODE.replace("<mirr>", m_chr).replace("<evnt>", e_chr)
            await self.hdlr.handle_router_cmd(rt_no, cmd)
            # ----------------------
            await self.routers[rt_no - 1].set_config_mode(False)
            print("\n")
            self.logger.info("Switched from Srv to Opr mode")
            self._opr_mode = True
            # Start event handler first, then enable mirror
            if self._ev_srv_task == []:
                self.logger.debug("Start EventSrv task")
                self._ev_srv_task = self.loop.create_task(
                    self.evnt_srv.watch_rt_events(self._rt_serial[0])
                )
                await asyncio.sleep(0.1)
        # Old switch -----------
        if self.mirror_mode_enabled:
            strt_mirr_cmd = RT_CMDS.START_MIRROR.replace(
                "<cyc>", chr(min(round(MIRROR_CYC_TIME * 100), 255))
            )
            await self.hdlr.handle_router_cmd(rt_no, strt_mirr_cmd)
            await asyncio.sleep(0.2)
        if self.event_mode_enabled:
            await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.START_EVENTS)
            await asyncio.sleep(0.2)
        # ----------------------

    async def stop_opr_mode(self, rt_no):
        """Turn on server mode: disable router events"""
        if not (self._opr_mode):
            return

        # Disable mirror first, then stop event handler
        # Serial reader still used by event server

        # New switch -----------
        # await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.SET_SRV_MODE)
        # ----------------------

        # Old switch -----------
        await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.STOP_EVENTS)
        await asyncio.sleep(0.2)
        await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.STOP_MIRROR)
        await asyncio.sleep(0.2)
        self.evnt_srv.evnt_running = False
        # ----------------------

        t_wait = 0.0
        while (self._ev_srv_task._state != "FINISHED") & (t_wait < 1.0):
            await asyncio.sleep(0.1)
            t_wait += 0.1
        if t_wait < 1.0:
            self.logger.info(
                f"EventSrv terminated successfully after {round(t_wait,1)} sec"
            )
        else:
            self._ev_srv_task.cancel()
            self.logger.info("EventSrv cancelled after 1 sec")
        self._ev_srv_task = []
        self._opr_mode = False

        # Old switch -----------
        await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.CLEAR_RT_SENDBUF)
        await self.routers[rt_no - 1].set_config_mode(True)
        # ----------------------

        print("\n")
        self.logger.info("Switched from Opr to Srv mode")

    async def set_initial_srv_mode(self, rt_no):
        """Turn on config mode: disable router events"""
        self._opr_mode = False
        self._ev_srv_task = []

        # Disable mirror first, then stop event handler
        await self.hdlr.handle_router_cmd(rt_no, RT_CMDS.CLEAR_RT_SENDBUF)
        await self.hdlr.handle_router_cmd_resp(rt_no, RT_CMDS.STOP_EVENTS)
        await self.hdlr.handle_router_cmd_resp(rt_no, RT_CMDS.STOP_MIRROR)
        await self.routers[rt_no - 1].set_config_mode(False)
        self.logger.debug("API mode turned off initially")
