import asyncio
from asyncio.tasks import Task
import logging
import json
import os
import websockets
from websockets import ConnectionClosedOK, WebSocketClientProtocol
from const import DATA_FILES_ADDON_DIR, DATA_FILES_DIR, HA_EVENTS
from forward_hdlr import ForwardHdlr


class EVENT_IDS:
    """Identifier of router events, e.g. input changes."""

    FLG_CHG = 6
    LOGIC_CHG = 7
    OUT_ON = 10
    OUT_OFF = 11
    IRDA_SHORT = 23
    IRDA_LONG = 24
    IRDA_LONG_END = 25
    SYS_ERR = 101
    BTN_SHORT = 150
    BTN_LONG = 151
    SW_ON = 152
    SW_OFF = 153
    BTN_LONG_END = 154
    EKEY_FNGR = 169
    DIR_CMD = 253


class WEBSOCK_MSG:
    """Predefined messages for websocket commands."""

    auth_msg = {"type": "auth", "access_token": ""}
    ping_msg = {"id": 1, "type": "ping"}
    call_service_msg = {
        "id": 1,
        "type": "call_service",
        "domain": "habitron",
        "service": "update_entity",
        "service_data": {
            "hub_uid": "",
            "rtr_nmbr": 1,
            "mod_nmbr": 0,
            "evnt_type": 0,
            "evnt_arg1": 0,
            "evnt_arg2": 0,
        },
    }


class EventServer:
    """Reacts on habitron events and sends to home assistant websocket"""

    def __init__(self, api_srv):
        self.api_srv = api_srv
        self._hass_ip = api_srv._hass_ip
        self._client_ip = api_srv._client_ip
        self._uri = ""
        self.logger = logging.getLogger(__name__)
        self.ev_srv_task: Task
        self.ev_srv_task_running = False
        self.websck: WebSocketClientProtocol
        self.auth_token: str | None = os.getenv("SUPERVISOR_TOKEN")
        self.notify_id = 1
        self.evnt_running = False
        self.msg_appended = False
        self.busy_starting = False
        self.websck_is_closed = True
        self.default_token: str
        self.token_ok = True

    def get_ident(self) -> str | None:
        """Return token"""
        try:
            if self.api_srv.is_addon:
                data_file_path = DATA_FILES_ADDON_DIR
            else:
                data_file_path = DATA_FILES_DIR
            with open(data_file_path + "settings.set", mode="rb") as fid:
                id_str = fid.read().decode("iso8859-1")
            fid.close()
            ip_len = ord(id_str[0])
            if self.api_srv.is_addon and ip_len > 16:
                # No ip, take str as token, generated manually
                return id_str.replace("\n", "")
            self.api_srv._client_ip = id_str[1 : ip_len + 1]
            self._client_ip = self.api_srv._client_ip
            id_str = id_str[ip_len + 1 :]
            ip_len = ord(id_str[0])
            self.api_srv._hass_ip = id_str[1 : ip_len + 1]
            self._hass_ip = self.api_srv._hass_ip
            tok_len = ord(id_str[ip_len + 1])
            tok_str = id_str[ip_len + 2 : ip_len + 2 + tok_len]
            if not self.api_srv.is_addon:
                for nmbr in self.api_srv.sm_hub.lan_mac.split(":"):
                    idx = int("0x" + nmbr, 0) & 0x7F
                    if idx < tok_len:
                        tok_str = tok_str[:idx] + tok_str[-1] + tok_str[idx:-1]
            return tok_str
        except Exception as err_msg:
            self.logger.error(
                f"Failed to open '{data_file_path}settings.set': {err_msg}; event server can't transmit events"
            )
            return None

    def extract_rest_msg(self, rt_event: bytes, msg_len: int) -> bytes:
        """Check for more appended messages."""
        if len(rt_event) > msg_len:
            tail = rt_event[msg_len - 1 :]
            self.logger.warning(f"Second event message: {tail}")
            self.logger.info(f"     Complete message: {rt_event}")
            self.msg_appended = True
            return tail
        return b""

    async def watch_rt_events(self, rt_rd):
        """Task for handling router responses and events in api mode"""

        self.logger.debug("Event server started")
        self.busy_starting = True
        self.evnt_running = True
        rtr_id = 100  # inital value, will be taken from event messages
        await self.open_websocket()
        tail: bytes = b""

        recvd_byte = b"\00"  # Initialization for resync
        while self.evnt_running:
            self.busy_starting = False
            # Fast loop, immediate checks here without message/handler
            await asyncio.sleep(0.02)  # short break for other processes
            try:
                # Get prefix
                if self.msg_appended:
                    try:
                        # Don't read new message, generate new prefix
                        prefix = ("\xff#" + chr(rtr_id) + chr(len(tail) + 4)).encode(
                            "iso8859-1"
                        )
                    except:  # noqa: E722
                        # If something goes wrong, rtr_id and tail are without value
                        prefix = ("\xff#" + chr(1) + chr(4)).encode("iso8859-1")
                elif recvd_byte == b"\xff":
                    # Last loop of resync found first 2 bytes, reduce prefix to 2
                    prefix = b"\xff\x23" + await rt_rd.readexactly(2)
                    recvd_byte = b"\00"  # Turn off special condition
                else:
                    # Normal behaviour, read prefix of 4 bytes
                    prefix = await rt_rd.readexactly(4)

                if (prefix[3] == 0) or (prefix[0] != 0xFF) or (prefix[1] != 0x23):
                    # Something went wrong, start reading until sequence 0xFF 0x23 found
                    self.logger.warning("API mode router message with length=0, resync")
                    resynced = False
                    while not resynced:
                        recvd_byte = b"\00"
                        while recvd_byte != b"\xff":
                            # Look for new start byte
                            recvd_byte = await rt_rd.readexactly(1)
                        resynced = await rt_rd.readexactly(1) == b"\x23"
                        # continue with 'elif recvd_byte == b"\xff":'

                elif prefix[3] < 4:
                    self.logger.warning(
                        f"API mode router message too short, length: {prefix[3]-3} bytes"
                    )
                else:
                    # Read rest of message
                    if not (self.msg_appended):
                        rtr_id = prefix[2]
                        tail = await rt_rd.readexactly(prefix[3] - 3)
                    else:
                        # tail already taken from previous message
                        self.msg_appended = False

                    rt_event = prefix + tail
                    if len(tail) == 1:
                        self.logger.info(
                            f"API mode router message too short, tail: {tail}"
                        )
                        msg_len = 0
                    else:
                        msg_len = await self.parse_event_message(
                            rt_event, rt_rd, rtr_id
                        )
                    if msg_len:
                        # Looks if message is longer than expexted msg_len
                        tail = self.extract_rest_msg(rt_event, msg_len)

            except RuntimeError as err_msg:
                self.logger.error(f"Event server runtime error: {err_msg.args[0]}")
                await self.close_websocket()
                if not await self.ping_pong_reconnect():
                    self.logger.warning(
                        "Webwocket reconnect failed, websocket closed, event server terminated"
                    )
                    await self.api_srv.set_server_mode(rtr_id)
                    await self.stop()
                    await self.api_srv.set_operate_mode(rtr_id)
            except Exception as error_msg:
                # Use to get cancel event in api_server
                self.logger.error(
                    f"Event server exception: {error_msg}, event server still running"
                )

    async def parse_event_message(self, rt_event, rt_rd, rtr_id) -> int:
        """Parse event code."""

        m_len = 0  # Correct length of parsed message, will be returned

        if (rt_event[4] == 133) and (rt_event[5] == 1):
            # Response should have been received before, not in event watcher
            self.logger.debug(
                "Warning, router event message: Operate mode started, should have been received in Srv mode"
            )
            self.logger.debug(f"     Complete meassage sent: {rt_event}")
            self.api_srv._opr_mode = True
            m_len = 9

        elif (rt_event[4] == 133) and (rt_event[5] == 0):
            # Last response in Opr mode, shut down event watcher
            self.logger.debug(
                "API mode router message: Mirror/events stopped, stopping router event watcher"
            )
            # if len(rt_rd._buffer) > 0:
            #     prefix = await rt_rd.readexactly(4)
            #     tail = await rt_rd.readexactly(prefix[3] - 3)
            #     rt_event = prefix + tail
            self.evnt_running = False

        elif rt_event[4] == 100:  # router chan status
            if rt_event[6] != 0:
                self.api_srv.routers[rtr_id - 1].chan_status = rt_event[5:47]
                self.logger.debug(
                    f"API mode router message: Router channel status, mode 0: {rt_event[6]}"
                )
            else:
                self.logger.warning(
                    "API mode router message: Router channel status with mode=0, discarded"
                )
            m_len = 48

        elif rt_event[4] == 50:
            self.logger.debug(
                f"API mode router message, collective command: {rt_event[5]}"
            )
            m_len = 7

        elif rt_event[4] == 68:
            self.logger.debug(
                f"API mode router message, direct command: Module {rt_event[5]} - Command {rt_event[6:-1]}"
            )
            m_len = rt_event[8] + 8

        elif rt_event[4] == 87:
            # Forward command response
            self.logger.info(
                f"API mode router message, forward response: {rt_event[4:-1]}"
            )
            if self.fwd_hdlr is None:
                # Instantiate once if needed
                self.fwd_hdlr = ForwardHdlr(self.api_srv)
                self.logger.info("Forward handler instantiated")
            await self.fwd_hdlr.send_forward_response(rt_event[4:-1])
            self.msg_appended = False

        elif rt_event[4] == 134:  # 0x86: System event
            m_len = await self.notify_system_events(rt_event, rtr_id)

        elif rt_event[4] == 135:  # 0x87: System mirror
            # rt_hdlr parses msg, initiates module status update, get events
            mirr_events = self.api_srv.routers[rtr_id - 1].hdlr.parse_event(
                rt_event[1:]
            )
            if (mirr_events is not None) and (mirr_events != []):
                # send event to IP client
                await self.notify_mirror_events(mirr_events, rtr_id)
            m_len = 232

        elif rt_event[4] == 137:  # System mode
            if (rt_event[3] == 6) and (rt_event[5] != 75):
                self.api_srv.routers[rtr_id - 1].mode0 = rt_event[5]
                self.logger.debug(
                    f"API mode router message, system mode: {rt_event[5]}"
                )
            elif rt_event[3] != 6:
                self.logger.warning(
                    f"API mode router message, invalid system mode length: {rt_event}"
                )
            else:
                self.logger.debug("API mode router message, system mode: 'Config'")

        else:
            # Discard resonse of API command
            self.logger.warning(
                f"API mode router message, response discarded: {rt_event}"
            )
        return m_len

    async def notify_mirror_events(self, mirr_events, rtr_id):
        """Check for multiple events and call notify."""
        for m_event in mirr_events:
            if (m_event[1] == HA_EVENTS.FLAG) and (m_event[2] > 999):
                # Multiple events
                hi_byte = False
                msk = m_event[2] - 1000
                val = m_event[3]
                if msk > 999:
                    hi_byte = True
                    msk -= 1000
                for flg_no in range(8):
                    if (msk & (i_msk := 1 << flg_no)) > 0:
                        if hi_byte:
                            flg_no += 8
                        val = int((val & i_msk) > 0)
                        ev_list = [m_event[0], m_event[1], flg_no, val]
                        await self.notify_event(rtr_id, ev_list)
            else:
                await self.notify_event(rtr_id, m_event)

    async def notify_system_events(self, rt_event, rtr_id) -> int:
        """Parse received event message and call notify."""

        ev_list = None
        if rt_event[5] == 254:
            self.logger.info("Event mode started")
            m_len = 8
        elif rt_event[5] == 255:
            self.logger.info("Event mode stopped")
            m_len = 8
        elif rt_event[6] == 163:
            self.logger.warning(f"Unknown event command 163: {rt_event[6:-1]}")
            m_len = 7
        elif rt_event[3] == 6:
            self.logger.warning(f"Unknown event command: {rt_event[6:-1]}")
            m_len = 7
        else:
            mod_id = rt_event[5]
            event_id = rt_event[6]
            args = rt_event[7:-1]
            self.logger.debug(
                f"New router event type {event_id} from module {mod_id}: {args}"
            )
            m_len = 9
            match event_id:
                case EVENT_IDS.BTN_SHORT:
                    ev_list = [mod_id, HA_EVENTS.BUTTON, args[0], 1]
                case EVENT_IDS.BTN_LONG:
                    ev_list = [mod_id, HA_EVENTS.BUTTON, args[0], 2]
                case EVENT_IDS.BTN_LONG_END:
                    ev_list = [mod_id, HA_EVENTS.BUTTON, args[0], 3]
                case EVENT_IDS.SW_ON:
                    ev_list = [mod_id, HA_EVENTS.SWITCH, args[0], 1]
                case EVENT_IDS.SW_OFF:
                    ev_list = [mod_id, HA_EVENTS.SWITCH, args[0], 0]
                case EVENT_IDS.OUT_ON:
                    ev_list = [mod_id, HA_EVENTS.OUTPUT, args[0], 1]
                case EVENT_IDS.OUT_OFF:
                    ev_list = [mod_id, HA_EVENTS.OUTPUT, args[0], 0]
                case EVENT_IDS.EKEY_FNGR:
                    m_len += 1
                    ev_list = [
                        mod_id,
                        HA_EVENTS.FINGER,
                        args[0],
                        args[1],
                    ]
                case EVENT_IDS.IRDA_SHORT:
                    m_len += 1
                    ev_list = [
                        mod_id,
                        HA_EVENTS.IR_CMD,
                        args[0],
                        args[1],
                    ]
                case EVENT_IDS.FLG_CHG:
                    m_len += 1
                    ev_list = [mod_id, HA_EVENTS.FLAG, args[0], args[1]]
                case EVENT_IDS.LOGIC_CHG:
                    m_len += 1
                    ev_list = [
                        mod_id,
                        HA_EVENTS.CNT_VAL,
                        args[0],
                        args[1],
                    ]
                case EVENT_IDS.DIR_CMD:
                    ev_list = [mod_id, HA_EVENTS.DIR_CMD, args[0], 0]
                case EVENT_IDS.SYS_ERR:
                    m_len += 1
                    ev_list = [0, HA_EVENTS.SYS_ERR, args[0], args[1]]
                case 68:
                    m_len = rt_event[8] + 7
                    self.logger.warning(f"Event 68: {rt_event}")
                    return m_len
                case _:
                    self.logger.warning(f"Unknown event id: {event_id}")
                    return m_len
            await self.notify_event(rtr_id, ev_list)
        return m_len

    async def notify_event(self, rtr: int, event: list[int]):
        """Trigger event on remote host (e.g. home assistant)"""

        if self.websck_is_closed:
            success = await self.open_websocket()
        else:
            success = True
        if not success:
            self.logger.warning("Failed to send event via websocket, open failed")
            return
        if event is None:
            return
        try:
            evnt_data = {
                "hub_uid": self.api_srv.sm_hub._host_ip,
                "rtr_nmbr": rtr,
                "mod_nmbr": event[0],
                "evnt_type": event[1],
                "evnt_arg1": event[2],
                "evnt_arg2": event[3],
            }
            self.logger.debug(f"Event alerted: {evnt_data}")
            event_cmd = WEBSOCK_MSG.call_service_msg
            self.notify_id += 1
            event_cmd["id"] = self.notify_id
            event_cmd["service_data"] = evnt_data

            await self.websck.send(json.dumps(event_cmd))  # Send command
            resp = await self.websck.recv()
            self.logger.debug(f"Notify returned {resp}")

        except ConnectionClosedOK:
            self.logger.warning(
                "Connection closed by HA server, terminating event server task"
            )
            self.websck_is_closed = True
            self.evnt_running = False
            await self.stop()
            await self.api_srv.set_server_mode(1)
        except Exception as error_msg:
            # Use to get cancel event in api_server
            self.logger.error(f"Could not connect to event server: {error_msg}")
            self.websck_is_closed = True
            if await self.ping_pong_reconnect():
                # Retry
                await self.websck.send(json.dumps(event_cmd))  # Send command
                resp = await self.websck.recv()
                self.logger.debug(f"Notify returned {resp}")

    async def ping_pong_reconnect(self) -> bool:
        """Check for living websocket connection, reconnect if needed."""
        success = await self.open_websocket()
        if success:
            try:
                event_cmd = WEBSOCK_MSG.ping_msg
                self.notify_id += 1
                event_cmd["id"] = self.notify_id
                await self.websck.send(json.dumps(event_cmd))  # Send command
                resp = await self.websck.recv()
                if json.loads(resp)["type"] == "pong":
                    self.logger.debug("Received pong from event server")
                    return True
                else:
                    self.logger.error(
                        f"Could not receive pong from event server, received: {resp}"
                    )
                    return False
            except Exception as error_msg:
                self.logger.error(f"Could not send ping to event server: {error_msg}")
                await self.close_websocket()
                return False
        self.logger.error("Could not reconnect to event server")
        return False

    async def open_websocket(self, retry=True) -> bool:
        """Opens web socket connection to home assistant."""

        if not self.websck_is_closed:
            return True
        if self.api_srv._netw_blocked:
            # First run, don't start websocket, HA is not ready
            return False

        if self.api_srv.is_addon:
            # SmartHub running with Home Assistant, use internal websocket
            self.logger.info("Open internal add-on websocket to home assistant.")
            self._uri = "ws://supervisor/core/websocket"
            self.logger.debug(f"URI: {self._uri}")
            self.auth_token = os.getenv("SUPERVISOR_TOKEN")
        else:
            # Stand-alone SmartHub, use external websocket connection to host ip
            self.logger.info("Open websocket to home assistant.")
            self.auth_token = self.get_ident()
            self._client_ip = self.api_srv._client_ip
            self._uri = "ws://<ip>:8123/api/websocket".replace("<ip>", self._client_ip)
            self.logger.debug(f"URI: {self._uri}")
            # supervisor_token  "2f428d27e04db95b4c844b451af4858fba585aac82f70ee6259cf8ec1834a00abf6a448f49ee18d3fc162f628ce6f479fe4647c6f8624f88"
            # token for local docker:    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxZDZkZWY4MjZmYzI0Yzg0OGUwMTAxYTUyMWE1ZTI0ZSIsImlhdCI6MTcxMDk1MTQ2MSwiZXhwIjoyMDI2MzExNDYxfQ.CG3kAoZSPHexOkztWk15Z3lg9v3avxbXJVb_PNXXU1I"
            # token for 192.168.178.160: token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI5NGY2ZjMyZjdhYjE0NzAzYmI4MTc5YjZhOTdhYzdjNSIsImlhdCI6MTcxMzYyMjgxNywiZXhwIjoyMDI4OTgyODE3fQ.2iJQuKgpavJOelH_WHEDe06X2XmAmyHB3FlzkDPl4e0"
            # token for SmartCenter 5:   token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmN2UxMGFhNzcyZTE0ZWY0OGFmOTkzNDVlOTIwNTNlNiIsImlhdCI6MTcxMzUxNDM4MSwiZXhwIjoyMDI4ODc0MzgxfQ.9kpjxhElmWAqTY2zwSsTyLSZiJQZkaV5FX8Pyj9j8HQ"

        if self.api_srv.is_addon and (self.auth_token is None or not self.token_ok):
            # addon uses environment variable
            self.auth_token = os.getenv("SUPERVISOR_TOKEN")
            self.logger.info(
                f"Auth not valid, retry getting SUPERVISOR_TOKEN token: {self.auth_token}"
            )

        if self.auth_token is None:
            if self.api_srv.is_addon:
                self.logger.error(
                    "Websocket auth token is none, open_websocket failed."
                )
            else:
                self.logger.error(
                    "Websocket stored token is none, open_websocket failed"
                )
            self.websck_is_closed = True
            self.token_ok = False
            return False

        try:
            if self.api_srv.is_addon:
                self.websck = await websockets.connect(
                    self._uri,
                    extra_headers={"Authorization": f"Bearer {self.auth_token}"},
                    open_timeout=3,
                )
            else:
                self.websck = await websockets.connect(self._uri, open_timeout=3)
            resp = await self.websck.recv()
        except Exception as err_msg:
            await self.close_websocket()
            self.logger.error(f"Websocket connect failed: {err_msg}")
            self.websck_is_closed = True
            self.token_ok = False
            return False
        if json.loads(resp)["type"] == "auth_required":
            try:
                msg = WEBSOCK_MSG.auth_msg
                msg["access_token"] = self.auth_token
                await self.websck.send(json.dumps(msg))
                resp = await self.websck.recv()
                self.logger.info(
                    f"Websocket connecting to {self._uri}, response: {resp}"
                )
                if json.loads(resp)["type"] == "auth_invalid":
                    self.logger.error(
                        f"Websocket authentification failed: {json.loads(resp)['message']}"
                    )
                    await self.close_websocket()
                    self.token_ok = False
                    if retry:
                        await self.open_websocket(retry=False)
                    return False
            except Exception as err_msg:
                self.logger.error(f"Websocket authentification failed: {err_msg}")
                await self.close_websocket()
                self.token_ok = False
                return False
        else:
            self.logger.info(f"Websocket connected to {self._uri}, response: {resp}")
            self.token_ok = True
        self.websck_is_closed = False
        return True

    async def close_websocket(self):
        """Close websocket, if object still available."""
        if not self.websck_is_closed:
            try:
                await asyncio.wait_for(asyncio.shield(self.websck.close()), timeout=1)
                self.websck_is_closed = True
                self.logger.debug("Websocket closed")
            except TimeoutError:
                self.logger.warning("Timeout closing websocket, removing entry anyway")
                self.websck_is_closed = True
                self.logger.debug("Websocket still closing")
            except Exception as err_msg:
                self.logger.warning(f"Websocket close failed: {err_msg}")

    async def start(self):
        """Start event server task."""
        if self.running():
            return
        if self.api_srv._init_mode:
            return
        if self.busy_starting:
            self.logger.debug("New EventSrv task is aleady starting")
            return
        self.busy_starting = True
        self.logger.debug("Starting new EventSrv task")
        self.ev_srv_task = self.api_srv.loop.create_task(
            self.watch_rt_events(self.api_srv._rt_serial[0])
        )
        self.ev_srv_task_running = True

    async def stop(self):
        """Stop running event server task."""
        self.evnt_running = False
        if not self.ev_srv_task_running:
            return
        self.logger.debug("Stopping EventSrv task")
        self.evnt_running = False
        # waiting for event server to receive response and shut down
        t_wait = 0.0
        t_max = 2.0
        if not self.running():
            self.logger.debug("No EventSrv running, already stopped")
        else:
            while (self.ev_srv_task._state != "FINISHED") and (t_wait < t_max):
                await asyncio.sleep(0.1)
                t_wait += 0.1
            if t_wait < t_max:
                self.logger.debug(
                    f"EventSrv terminated successfully after {round(t_wait,1)} sec"
                )
            else:
                self.ev_srv_task.cancel()
                self.logger.debug(f"EventSrv stoppped after {t_max} sec")
            self.ev_srv_task_running = False
            # await self.close_websocket()

    def running(self) -> bool:
        """Check status of event server task, set and retrun status flag."""
        if not self.ev_srv_task_running:
            self.logger.debug(
                "Event server not running, no EventSrv object instantiated"
            )
            return self.ev_srv_task_running
        if self.ev_srv_task.done():
            self.logger.debug("Event server not running, EventSrv 'done'")
            self.ev_srv_task_running = False
        if self.ev_srv_task.cancelled():
            self.logger.debug("Event server not running, EventSrv 'cancelled'")
            self.ev_srv_task_running = False
        return self.ev_srv_task_running
