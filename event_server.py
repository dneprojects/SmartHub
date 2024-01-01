import aioserial
import logging
import socket
import json
import os
import websockets
from pymodbus.utilities import computeCRC as ModbusComputeCRC
from const import DATA_FILES_DIR, EVENT_PORT, API_RESPONSE, MirrIdx, HA_EVENTS
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
        self.websck = []
        self.token = None
        self.notify_id = 1
        self.evnt_running = False
        self.msg_appended = False

    def get_ident(self) -> str:
        """Return token"""
        try:
            with open(DATA_FILES_DIR + "settings.set", mode="rb") as fid:
                id_str = fid.read().decode("iso8859-1")
            fid.close()
            for nmbr in self.api_srv.sm_hub.lan_mac.split(":"):
                idx = int("0x" + nmbr, 0) & 0x7F
                id_str = id_str[:idx] + id_str[-1] + id_str[idx:-1]
            return id_str
        except Exception as err_msg:
            self.logger.error(
                f"Failed to open {DATA_FILES_DIR + 'settings.set'}, event server can't transmit events"
            )
            return None

    async def open_websocket(self):
        """Opens web socket connection to home assistant."""

        if (self.websck == None) | (self.websck == []):
            if self.api_srv.is_addon:
                self.logger.info("Open internal add-on websocket to home assistant.")
            else:
                self.logger.info("Open websocket to home assistant.")
        else:
            return

        if self.api_srv.is_addon:
            # SmartHub running with Home Assistant, use internal websocket
            self._uri = "ws://supervisor/core/websocket"
            self.logger.debug(f"URI: {self._uri}")
            self.token = os.getenv("SUPERVISOR_TOKEN")
        else:
            if self._client_ip == "":
                self._client_ip = self.api_srv._client_ip
            self._uri = "ws://<ip>:8123/api/websocket".replace("<ip>", self._client_ip)
            self.logger.debug(f"URI: {self._uri}")
            # token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJjMWI1ZjgyNmUxMDg0MjFhYWFmNTZlYWQ0ZThkZGNiZSIsImlhdCI6MTY5NDUzNTczOCwiZXhwIjoyMDA5ODk1NzM4fQ.0YZWyuQn5DgbCAfEWZXbQZWaViNBsR4u__LjC4Zf2lY"
            # token for 192.168.178.133: token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlYjQ2MTA4ZjUxOTU0NTY3Yjg4ZjUxM2Q5ZjBkZWRlYSIsImlhdCI6MTY5NDYxMDEyMywiZXhwIjoyMDA5OTcwMTIzfQ.3LtGwhonmV2rAbRnKqEy3WYRyqiS8DTh3ogx06pNz1g"
            # token for 192.168.178.140: token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4OTNlZDJhODU2ZmY0ZDQ3YmVlZDE2MzIyMmU1ODViZCIsImlhdCI6MTcwMjgyMTYxNiwiZXhwIjoyMDE4MTgxNjE2fQ.NT-WSwkG9JN8f2cCt5fXlP4A8FEOAgDTrS1sdhB0ioo"
            self.token = self.get_ident()

        if self.token == None:
            if self.api_srv.is_addon:
                self.logger.error(
                    "Websocket supervisor token is none, open_websocket failed."
                )
            else:
                self.logger.error(
                    "Websocket stored token is none, open_websocket failed."
                )
            self.websck = None
            return

        try:
            if self.api_srv.is_addon:
                self.websck = await websockets.connect(
                    self._uri,
                    extra_headers={"Authorization": f"Bearer {self.token}"},
                )
            else:
                self.websck = await websockets.connect(self._uri)
            resp = await self.websck.recv()
        except Exception as err_msg:
            self.logger.error(f"Websocket connect failed: {err_msg}")
            self.websck = []
            return
        if json.loads(resp)["type"] == "auth_required":
            try:
                msg = WEBSOCK_MSG.auth_msg
                msg["access_token"] = self.token
                await self.websck.send(json.dumps(msg))
                resp = await self.websck.recv()
                self.logger.info(
                    f"Websocket connected to {self._uri}, response: {resp}"
                )
            except Exception as err_msg:
                self.logger.error(f"Websocket connect failed: {err_msg}")
                self.websck = []
                return
        else:
            self.logger.info(f"Websocket connected to {self._uri}, response: {resp}")
        return

    def extract_rest_msg(self, rt_event, msg_len):
        """Check for more appended messages."""
        if len(rt_event) > msg_len:
            tail = rt_event[msg_len - 1 :]
            self.logger.warning(f"Second event message: {tail}")
            self.msg_appended = True
            return tail

    async def watch_rt_events(self, rt_rd: aioserial.AioSerial):
        """Task for handling router responses and events in api mode"""

        self.logger.info("Event server running")
        self.evnt_running = True

        await self.open_websocket()

        recvd_byte = b"\00"  # Initialization for resync
        while self.evnt_running:
            # Fast loop, immediate checks here without message/handler
            try:
                # Get prefix
                if self.msg_appended:
                    try:
                        # Don't read new message, generate new prefix
                        prefix = ("\xff#" + chr(rtr_id) + chr(len(tail) + 4)).encode(
                            "iso8859-1"
                        )
                    except:
                        # If something goes wrong, rtr_id and tail are without value
                        prefix = ("\xff#" + chr(0) + chr(4)).encode("iso8859-1")
                elif recvd_byte == b"\xff":
                    # Last loop of while found first 2 bytes, reduce prefix to 2
                    prefix = b"\xff\x23" + await rt_rd.readexactly(2)
                    recvd_byte = b"\00"  # Turn off special condition
                else:
                    # Normal behaviour, read prefix of 4 bytes
                    prefix = await rt_rd.readexactly(4)

                if (prefix[3] == 0) | (prefix[0] != 0xFF) | (prefix[1] != 0x23):
                    # Something went wrong, start reading until sequence 0xFF 0x23 found
                    self.logger.warning("API mode router message with length=0, resync")
                    resynced = False
                    while not resynced:
                        recvd_byte = b"\00"
                        while recvd_byte != b"\xff":
                            # Look for new start byte
                            recvd_byte = await rt_rd.readexactly(1)
                        resynced = await rt_rd.readexactly(1) == b"\x23"

                elif prefix[3] < 4:
                    self.logger.warning(
                        f"API mode router message too short: {prefix[3]-3} bytes"
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
                            f"API mode router message too short: {tail[0]}"
                        )
                    elif (rt_event[4] == 133) & (rt_event[5] == 1):
                        # Response should have been received before, not in event watcher
                        self.logger.info("Router event message: Operate mode started")
                        self.api_srv._opr_mode = True
                        tail = self.extract_rest_msg(rt_event, 7)
                    elif (rt_event[4] == 133) & (rt_event[5] == 0):
                        # Last response in Opr mode, shut down event watcher
                        self.logger.info(
                            "API mode router message: Mirror/events stopped, stopping router event watcher"
                        )
                        if len(rt_rd._buffer) > 0:
                            prefix = await rt_rd.readexactly(4)
                            tail = await rt_rd.readexactly(prefix[3] - 3)
                            rt_event = prefix + tail
                        self.evnt_running = False
                    elif rt_event[4] == 100:  # router chan status
                        if rt_event[6] != 0:
                            self.api_srv.routers[rtr_id - 1].chan_status = rt_event[
                                5:47
                            ]
                            self.logger.debug(
                                f"API mode router message: Router channel status, mode 0: {rt_event[6]}"
                            )
                        else:
                            self.logger.warning(
                                "API mode router message: Router channel status with mode=0, discarded"
                            )
                        tail = self.extract_rest_msg(rt_event, 48)
                    elif rt_event[4] == 68:
                        self.logger.debug(
                            f"API mode router message, direct command: Module {rt_event[5]} - Command {rt_event[6:-1]}"
                        )
                        tail = self.extract_rest_msg(rt_event, rt_event[8] + 8)
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
                        ev_list = None
                        if rt_event[5] == 254:
                            self.logger.info("Event mode started")
                            m_len = 8
                        elif rt_event[5] == 255:
                            self.logger.info("Event mode stopped")
                            m_len = 8
                        elif rt_event[6] == 163:
                            self.logger.warning(
                                f"Unknown event command 163: {rt_event[6:-1]}"
                            )
                            m_len = 7
                        elif rt_event[3] == 6:
                            self.logger.warning(
                                f"Unknown event command: {rt_event[6:-1]}"
                            )
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
                                        HA_EVENTS.COUNTER,
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
                                case other:
                                    self.logger.warning(f"Unknown event id: {event_id}")
                                    return
                            await self.notify_event(rtr_id, ev_list)
                        tail = self.extract_rest_msg(rt_event, m_len)

                    elif rt_event[4] == 135:  # 0x87: System mirror
                        # rt_hdlr parses msg, initiates module status update, get events
                        mirr_events = self.api_srv.routers[rtr_id - 1].hdlr.parse_event(
                            rt_event[1:]
                        )
                        if mirr_events != None:
                            # send event to IP client
                            await self.handle_mirror_events(mirr_events, rtr_id)

                        tail = self.extract_rest_msg(rt_event, 232)
                    elif rt_event[4] == 137:  # System mode
                        if (rt_event[3] == 6) & (rt_event[5] != 75):
                            self.api_srv.routers[rtr_id - 1].mode0 = rt_event[5]
                            self.logger.debug(
                                f"API mode router message, system mode: {rt_event[5]}"
                            )
                        elif rt_event[3] != 6:
                            self.logger.warning(
                                f"API mode router message, invalid system mode length: {rt_event}"
                            )
                        else:
                            self.logger.debug(
                                f"API mode router message, system mode: 'Config'"
                            )
                    else:
                        # Discard resonse of API command
                        self.logger.warning(
                            f"API mode router message, response discarded: {rt_event}"
                        )
                        pass
            except Exception as error_msg:
                # Use to get cancel event in api_server
                self.logger.error(
                    f"Event server exception: {error_msg}, event server still running"
                )

    async def handle_mirror_events(self, mirr_events, rtr_id):
        """Check for multiple events and call notify."""
        for m_event in mirr_events:
            if (m_event[1] == HA_EVENTS.FLAG) & (m_event[2] > 999):
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

    async def notify_event(self, rtr: int, event: [int]):
        """Trigger event on remote host (e.g. home assistant)"""

        if (self.websck == []) | (self.websck == None):
            await self.open_websocket()
        if event == None:
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
            if self.websck == None:
                return
            event_cmd = WEBSOCK_MSG.call_service_msg
            self.notify_id += 1
            event_cmd["id"] = self.notify_id
            event_cmd["service_data"] = evnt_data

            await self.websck.send(json.dumps(event_cmd))  # Send command
            resp = await self.websck.recv()
            self.logger.debug(f"Notify returned {resp}")

        except Exception as error_msg:
            # Use to get cancel event in api_server
            self.logger.error(f"Could not connect to event server: {error_msg}")
            self.websck = []
            if await self.ping_pong_reconnect():
                # Retry
                await self.websck.send(json.dumps(event_cmd))  # Send command
                resp = await self.websck.recv()
                self.logger.debug(f"Notify returned {resp}")

    async def ping_pong_reconnect(self) -> bool:
        """Check for living websocket connection, reconnect if needed."""
        await self.open_websocket()
        if self.websck != []:
            try:
                event_cmd = WEBSOCK_MSG.ping_msg
                self.notify_id += 1
                event_cmd["id"] = self.notify_id
                await self.websck.send(json.dumps(event_cmd))  # Send command
                resp = await self.websck.recv()
                if json.loads(resp)["type"] == "pong":
                    self.logger.debug(f"Received pong from event server")
                    return True
                else:
                    self.logger.error(
                        f"Could not receive pong from event server, received: {resp}"
                    )
                    return False
            except Exception as error_msg:
                self.logger.error(f"Could not send ping to event server: {error_msg}")
                self.websck = []
                return False
        self.logger.error(f"Could not reconnect to event server")
        return False
