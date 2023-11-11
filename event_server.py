import aioserial
import logging
import socket
import json
import websockets
from pymodbus.utilities import computeCRC as ModbusComputeCRC
from const import DATA_FILES_DIR, EVENT_PORT, API_RESPONSE, MirrIdx
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
        self._uri = "ws://<ip>:8123/api/websocket".replace("<ip>", self._client_ip)
        self.logger = logging.getLogger(__name__)
        self.websck = []
        self.notify_id = 1
        self.evnt_running = False
        self.msg_appended = False

    def get_ident(self) -> str:
        """Return token"""
        try:
            with open(DATA_FILES_DIR + "settings.set", mode="rb") as fid:
                id_str = fid.read().decode("iso8859-1")
            fid.close()
            for nmbr in self.api_srv.sm_hub.mac.split(":"):
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

        if self._client_ip == "":
            self._client_ip = self.api_srv._client_ip
        self._uri = "ws://<ip>:8123/api/websocket".replace("<ip>", self._client_ip)

        # token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJjMWI1ZjgyNmUxMDg0MjFhYWFmNTZlYWQ0ZThkZGNiZSIsImlhdCI6MTY5NDUzNTczOCwiZXhwIjoyMDA5ODk1NzM4fQ.0YZWyuQn5DgbCAfEWZXbQZWaViNBsR4u__LjC4Zf2lY"
        # token for 192.168.178.133: token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlYjQ2MTA4ZjUxOTU0NTY3Yjg4ZjUxM2Q5ZjBkZWRlYSIsImlhdCI6MTY5NDYxMDEyMywiZXhwIjoyMDA5OTcwMTIzfQ.3LtGwhonmV2rAbRnKqEy3WYRyqiS8DTh3ogx06pNz1g"
        token = self.get_ident()

        if token != None:
            try:
                self.websck = await websockets.connect(self._uri)
            except Exception as err_msg:
                self.logger.error(f"Websocket connect failed: {err_msg}")
                self.websck = []
                return
            resp = await self.websck.recv()
            if json.loads(resp)["type"] == "auth_required":
                msg = WEBSOCK_MSG.auth_msg
                msg["access_token"] = token
                await self.websck.send(json.dumps(msg))
                resp = await self.websck.recv()
            self.logger.info(f"Websocket connected to {self._uri}, response: {resp}")
        else:
            self.websck = None
        return

    def extract_rest_msg(self, rt_event, msg_len):
        """Check for more appended messages."""
        if len(rt_event) > msg_len:
            tail = rt_event[msg_len - 1 :]
            self.logger.debug(f"Second event message: {tail}")
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
                    # Last loop of while found first byte, reduce prefix to 3
                    prefix = recvd_byte + await rt_rd.readexactly(3)
                    recvd_byte = b"\00"  # Turn off special condition
                else:
                    # Normal behaviour, read prefix of 4 bytes
                    prefix = await rt_rd.readexactly(4)

                if prefix[3] == 0:
                    # Something went wrong, start reading until 0xFF found
                    self.logger.warning("Router message with length=0, resync")
                    recvd_byte = b"\00"
                    while recvd_byte != b"\xff":
                        # Look for new start byte
                        recvd_byte = await rt_rd.readexactly(1)
                elif prefix[3] < 4:
                    self.logger.warning(
                        f"Router event message too short: {prefix[3]-3} bytes"
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
                            f"Unexpected short router event message: {tail[0]}"
                        )
                    elif (rt_event[4] == 135) & (rt_event[5] == 252):
                        self.logger.info("Router event message: Mirror started")
                        self.api_srv._api_mode = True
                        tail = self.extract_rest_msg(rt_event, 7)
                    elif (rt_event[4] == 135) & (rt_event[5] == 254):
                        self.logger.info(
                            "Router event message: Mirror stopped, stopping router event watcher"
                        )
                        self.evnt_running = False
                        tail = self.extract_rest_msg(rt_event, 7)
                        # self.api_srv._ev_hdlr.cancel()
                    elif rt_event[4] == 100:  # router chan status
                        if rt_event[6] != 0:
                            self.api_srv.routers[rtr_id - 1].chan_status = rt_event[
                                5:47
                            ]
                        else:
                            self.logger.warning(
                                "Router channel status with mode=0, discarded"
                            )
                        tail = self.extract_rest_msg(rt_event, 48)
                    elif rt_event[4] == 68:
                        self.logger.info(
                            f"Direct command: Module {rt_event[5]} - Command {rt_event[6:-1]}"
                        )
                    elif rt_event[4] == 87:
                        # Forward command response
                        self.logger.debug(f"Forward response: {rt_event[4:-1]}")
                        if self.fwd_hdlr is None:
                            # Instantiate once if needed
                            self.fwd_hdlr = ForwardHdlr(self.api_srv)
                            self.logger.debug("Forward handler instantiated")
                        await self.fwd_hdlr.send_forward_response(rt_event[4:-1])
                        self.msg_appended = False
                    elif rt_event[4] == 134:  # 0x86: System event
                        if rt_event[5] == 254:
                            self.logger.info("Event mode started")
                            m_len = 8
                        elif rt_event[5] == 255:
                            self.logger.info("Event mode stopped")
                            m_len = 8
                        elif rt_event[6] == 163:
                            self.logger.warning(
                                f"Unknown event command: {rt_event[6:-1]}"
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
                            self.logger.info(
                                f"New router event type {event_id} from module {mod_id}: {args}"
                            )
                            m_len = 9
                            match event_id:
                                case EVENT_IDS.BTN_SHORT:
                                    ev_list = [mod_id, 1, args[0], 1]
                                case EVENT_IDS.BTN_LONG:
                                    ev_list = [mod_id, 1, args[0], 2]
                                case EVENT_IDS.BTN_LONG_END:
                                    ev_list = [mod_id, 1, args[0], 3]
                                case EVENT_IDS.SW_ON:
                                    ev_list = [mod_id, 2, args[0], 1]
                                case EVENT_IDS.SW_OFF:
                                    ev_list = [mod_id, 2, args[0], 0]
                                case EVENT_IDS.OUT_ON:
                                    ev_list = [mod_id, 3, args[0], 1]
                                case EVENT_IDS.OUT_OFF:
                                    ev_list = [mod_id, 3, args[0], 0]
                                case EVENT_IDS.EKEY_FNGR:
                                    m_len += 1
                                    ev_list = [mod_id, 4, args[0], args[1]]
                                case EVENT_IDS.IRDA_SHORT:
                                    m_len += 1
                                    ev_list = [mod_id, 5, args[0], args[1]]
                                case EVENT_IDS.FLG_CHG:
                                    m_len += 1
                                    ev_list = [mod_id, 6, args[0], args[1]]
                                case EVENT_IDS.LOGIC_CHG:
                                    m_len += 1
                                    ev_list = [mod_id, 7, args[0], args[1]]
                                case EVENT_IDS.DIR_CMD:
                                    ev_list = [mod_id, 9, args[0], 0]
                                case EVENT_IDS.SYS_ERR:
                                    m_len += 1
                                    ev_list = [0, 10, args[0], args[1]]
                                case 68:
                                    self.logger.warning(f"Event 68: {rt_event}")
                                case other:
                                    self.logger.warning(f"Unknown event id: {event_id}")
                                    return
                            await self.notify_event(rtr_id, ev_list)
                        tail = self.extract_rest_msg(rt_event, m_len)

                    elif rt_event[4] == 135:  # 0x87: System mirror
                        # strip first byte 0xff and pass to rt_hdlr
                        # rt_hdlr initiates module status update, and sending event to IP client
                        update_info = self.api_srv.routers[rtr_id - 1].hdlr.parse_event(
                            rt_event[1:]
                        )
                        tail = self.extract_rest_msg(rt_event, 232)
                        # if update_info != None:
                        #     no_updates = round(len(update_info) / 4)
                        #     for u_i in range(no_updates):
                        #         mod_id = update_info[4 * u_i]
                        #         stat_idx = int(update_info[4 * u_i + 1])
                        #         old_val = int(update_info[4 * u_i + 2])
                        #         new_val = int(update_info[4 * u_i + 3])
                        # if stat_idx in [
                        #     MirrIdx.OUT_1_8,
                        #     MirrIdx.OUT_9_16,
                        #     MirrIdx.OUT_17_24,
                        # ]:
                        #     # output change
                        #     event = chr(mod_id) + "\x03"
                        #     out_byte = stat_idx - MirrIdx.OUT_1_8
                        #     diff = abs(new_val - old_val)
                        #     for out_no in range(8):
                        #         if diff & 1 << out_no:
                        #             break
                        #     out_no += out_byte * 8 + 1
                        #     new_val = int((new_val & diff) > 0)
                        #     event += chr(out_no) + chr(new_val)
                        #     await self.notify_event(
                        #         rtr_id, event.encode("iso8859-1")
                        #     )
                        # elif stat_idx in [
                        #     MirrIdx.INP_1_8,
                        #     MirrIdx.INP_9_16,
                        #     MirrIdx.INP_17_24,
                        # ]:
                        #     # input change
                        #     event = chr(mod_id) + "\x01"
                        #     inp_byte = stat_idx - MirrIdx.INP_1_8
                        #     diff = abs(new_val - old_val)
                        #     for inp_no in range(8):
                        #         if diff & (1 << inp_no):
                        #             break
                        #     inp_nmbr = inp_no + inp_byte * 8 + 1
                        #     if (new_val & (1 << inp_no)) > 0:
                        #         # This method only detects long press
                        #         event += chr(inp_nmbr) + chr(2)
                        #     else:
                        #         # new_val == 0, end of long press
                        #         event += chr(inp_nmbr) + chr(3)
                        #     await self.notify_event(
                        #         rtr_id, event.encode("iso8859-1")
                        #     )
                    else:
                        # Discard resonse of API command
                        self.logger.warning(f"API response discarded: {rt_event}")
                        pass
            except Exception as error_msg:
                # Use to get cancel event in api_server
                self.logger.error(f"Event server exception: {error_msg}")
                self.evnt_running = False
                self.api_srv._api_mode = False
                self.api_srv._ev_srv_task = []

    async def notify_event(self, rtr: int, event: [int]):
        """Trigger event on remote host (e.g. home assistant)"""

        if (self.websck == []) | (self.websck == None):
            await self.open_websocket()

        try:
            evnt_data = {
                "rtr_nmbr": rtr,
                "mod_nmbr": event[0],
                "evnt_type": event[1],
                "evnt_arg1": event[2],
                "evnt_arg2": event[3],
            }
            self.logger.info(f"Event alerted: {evnt_data}")
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
