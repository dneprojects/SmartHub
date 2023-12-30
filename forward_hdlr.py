import struct
import os
import json
import socket
from pymodbus.utilities import computeCRC
from const import API_FORWARD as spec
from const import DATA_FILES_DIR, FWD_TABLE_FILE, SMHUB_PORT
from hdlr_class import HdlrBase


class ForwardHdlr(HdlrBase):
    """Handling of all actions messages."""

    def __init__(self, api_srv) -> None:
        super().__init__(api_srv)
        self.read_mapping()

    async def process_message(self):
        """Parse message, prepare and send router command"""

        match self._spec:
            case spec.FWD_TABLE_DEL:
                file_name = DATA_FILES_DIR + FWD_TABLE_FILE
                if os.path.exists(file_name):
                    os.remove(file_name)
                self.fwd_mapping = dict()
                self.response = "OK"
                return
            case spec.FWD_TABLE_RD:
                self.response = f"{self.fwd_mapping}"
                return
            case spec.FWD_TABLE_ADD:
                self.check_arg(
                    self._p4,
                    range(1, 65),
                    "Error: mapped router id out of range 1..64",
                )
                self.check_arg(
                    len(self._args),
                    [4],
                    "Error: number of ip bytes must be 4",
                )
                if self.args_err:
                    return

                self.fwd_mapping[
                    f"{self._p4}"
                ] = f"{self._args[0]}.{self._args[1]}.{self._args[2]}.{self._args[3]}"
                self.save_mapping()
                self.response = f"{self.fwd_mapping}"
                return
            case spec.FWD_TABLE_SET:
                self.fwd_mapping = dict
                for map_idx in range[self._p5]:
                    mi = 5 * map_idx
                    if mi in range(1, 65):
                        key = f"{self._args[mi]}"
                        self.fwd_mapping[
                            key
                        ] = f"{self._args[mi + 1]}.{self._args[mi + 2]}.{self._args[mi + 3]}.{self._args[mi + 4]}"
                    else:
                        self.logger.warning(f"Invalid router id in mapping table: {mi}")
                self.save_mapping()
                self.response = f"{self.fwd_mapping}"
                return
            case spec.FWD_TO_SMHUB:
                forw_ip = self.api_srv._client_ip
                if forw_ip == 0:
                    self.response = f"Could not lookup router ID for IP {forw_ip} with forward message {self._args}"
                    self.args_err = True
                self.check_router_no(self._p4)
                if self.args_err:
                    return
                self.logger.info(
                    f"Received forward message {self._args} from IP {forw_ip}"
                )
                src_rt = self.lookup_forward_mapping(forw_ip)
                if src_rt is None:
                    self.response = (
                        f"IP {forw_ip} of forward command not found in table"
                    )
                    self.args_err = True
                    self.logger.warning(self.response)
                    return
                self.response = await self.api_srv.routers[
                    self._p4
                ].hdlr.forward_message(src_rt, self._args)
                return
            case _:
                self.response = f"Unknown API forward command: {self.msg._cmd_grp} {struct.pack('<h', self._spec)[1]} {struct.pack('<h', self._spec)[0]}"
                self.logger.warning(self.response)
                return

    async def send_forward_response(self, response: bytes):
        """Send forward response to remote router via network."""
        t_rt = response[7]
        t_mod = response[8]
        t_ip = self.fwd_mapping[f"{t_rt}"]
        # Wrap message
        r_len = len(response)
        cmd_prefix = f"\xa8\0\0\x08SmartHub\x04passS\x05\x50\x01\x01{chr(t_rt)}{chr(t_mod)}{chr(r_len & 0xFF)}{chr(r_len >> 8)}"
        cmd_postfix = "\x3f"
        full_string = cmd_prefix + response.decode("iso8859-1")
        cmd_len = len(full_string) + 3
        full_string = (
            full_string[0]
            + chr(cmd_len & 0xFF)
            + chr(cmd_len >> 8)
            + full_string[3 : cmd_len - 3]
        )
        cmd_crc = computeCRC(full_string.encode("iso8859-1"))
        cmd_postfix = chr(cmd_crc >> 8) + chr(cmd_crc & 0xFF) + cmd_postfix
        full_string += cmd_postfix

        sck = socket.socket()  # Create a socket object
        sck.connect((t_ip, SMHUB_PORT))
        sck.settimeout(20)  # 10 seconds
        try:
            sck.send(full_string.encode("iso8859-1"))  # Send command

            resp_bytes = sck.recv(30)
            if len(resp_bytes) < 30:
                return b"OK", 0
            resp_len = resp_bytes[29] * 256 + resp_bytes[28]
            resp_bytes = b""
            while len(resp_bytes) < resp_len + 3:
                buffer = sck.recv(resp_len + 3)
                resp_bytes = resp_bytes + buffer
            resp_bytes = resp_bytes[0:resp_len]
        except TimeoutError as exc:
            resp_bytes = b"Timeout error"
            self.logger.info(
                f"Timeout error after sending forward response to router {t_rt} at {t_ip}"
            )
        sck.close()
        return resp_bytes

    def read_mapping(self) -> dict | None:
        """Read forward mapping from file"""
        file_name = DATA_FILES_DIR + FWD_TABLE_FILE
        if os.path.exists(file_name):
            with open(file_name, "r") as fid:
                self.fwd_mapping = json.load(fid)
            return
        else:
            self.fwd_mapping = dict()

    def save_mapping(self):
        """Save forward mapping to file"""
        file_name = DATA_FILES_DIR + FWD_TABLE_FILE
        with open(file_name, "w") as fid:
            json.dump(self.fwd_mapping, fid)

    def lookup_forward_mapping(self, rt_ip: str) -> int | None:
        """Find router id from ip."""
        for rt_id, ip in self.fwd_mapping.items():
            if ip == rt_ip:
                return rt_id
        return
