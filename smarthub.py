import asyncio
import logging
from logging import config
import yaml
import serial
import serial.tools.list_ports
import serial_asyncio
import re
import socket
import uuid
import os
import psutil
import cpuinfo
from const import (
    OWN_IP,
    SMHUB_PORT,
    QUERY_PORT,
    ANY_IP,
    RT_DEF_ADDR,
    RT_BAUDRATE,
    RT_TIMEOUT,
    RT_CMDS,
)
from api_server import ApiServer
from config_server import ConfigServer


class SMHUB_INFO:
    """Holds information."""

    SW_VERSION = "0.9.8"
    TYPE = "Smart Hub"
    TYPE_CODE = "20"
    SERIAL = "RBPI"


class QueryServer:
    """Server class for network queries seraching Smart Hubs"""

    def __init__(self, lp, sm_hub):
        self.loop = lp
        self.sm_hub = sm_hub
        self.logger = logging.getLogger(__name__)
        self._q_running = False

    async def initialize(self):
        """Starting the server"""
        resp_header = "\x00\x00\x00\xf7"
        version_str = SMHUB_INFO.SW_VERSION.replace(".", "")[::-1]
        type_str = SMHUB_INFO.TYPE_CODE
        serial_str = SMHUB_INFO.SERIAL
        empty_str_10 = "0000000000"
        mac_str = ""
        for nmbr in self.sm_hub.lan_mac.split(":"):
            mac_str += chr(int(nmbr, 16))
        self.resp_str = (
            resp_header
            + chr(0)
            + version_str
            + type_str
            + empty_str_10
            + serial_str
            + mac_str
        ).encode("iso8859-1")

    async def handle_smhub_query(self, ip_reader, ip_writer):
        """Network server handler to receive api commands."""

        while True:
            # Read api command from network
            query = await ip_reader.read(1024)
            ip_writer.write(self.resp_str)
            await asyncio.sleep(0.04)

    async def run_query_srv(self):
        """Server for handling Smart Hub queries."""
        try:
            self.q_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.q_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)
            self.q_sock.bind((ANY_IP, QUERY_PORT))
            self.q_sock.settimeout(0.00002)
            self.logger.info("Query server started")

            self._q_running = True
            while self._q_running:
                try:
                    data, addr = self.q_sock.recvfrom(10)
                except Exception as error_msg:
                    await asyncio.sleep(0.4)
                else:
                    self.q_sock.sendto(self.resp_str, addr)
        except Exception as error_msg:
            self.logger.error(f"Error in query server: {error_msg}")

    def close_query_srv(self):
        """Closing connection"""
        self._q_running = False
        self.q_sock.close()


class SmartHub:
    """Holds methods of Smart Hub."""

    def __init__(self, loop, logger) -> None:
        self.loop = loop
        self.tg = asyncio.TaskGroup()
        self.logger = logger
        self.api_srv: ApiServer = []
        self.q_srv: QueryServer = []
        self.conf_srv: ConfigServer = []
        self.get_mac()
        self._serial = ""
        self._pi_model = ""
        self._cpu_info = ""
        self._host = ""
        self._host_ip = ""
        self.info = self.get_info()
        self.logger.info("Smart Hub starting...")
        self.skip_init = False
        self.restart = False

    def reboot_hub(self):
        """Reboot hardware."""
        self.logger.warning("Reboot of Smart Hub host requested")
        os.system("sudo reboot")

    def restart_hub(self, skip_init):
        """Restart SmartIP software."""
        self.skip_init = skip_init > 0
        self.restart = True
        self.logger.warning("Restart of sm_hub process requested")
        self.server.close()
        self.q_srv.close_query_srv()
        for tsk in self.tg._tasks:
            self.logger.info(f"Terminating task {tsk.get_name()}")
            tsk.cancel()

    def get_mac(self):
        """Ask for own mac address."""
        if "eth0" in psutil.net_if_addrs():
            self.lan_mac = psutil.net_if_addrs()["eth0"][-1].address
        else:
            self.lan_mac = psutil.net_if_addrs()["end0"][-1].address
        self.wlan_mac = psutil.net_if_addrs()["wlan0"][-1].address
        self.curr_mac = ":".join(re.findall("..", "%012x" % uuid.getnode()))
        return

    def get_host_ip(self):
        """Return own ip."""
        return self._host_ip

    def get_version(self):
        """Return version string"""
        return SMHUB_INFO.SW_VERSION

    def get_serial(self):
        """Return version string"""
        return SMHUB_INFO.SERIAL

    def get_type(self):
        """Return version string"""
        return SMHUB_INFO.TYPE

    def get_info(self):
        """Return information on Smart Gateway hardware and software"""  # Get cpu statistics

        if self._serial == "":
            get_all = True
            try:
                with open("/sys/firmware/devicetree/base/model") as f:
                    self._pi_model = f.read()[:-1]
                    f.close()
                with open("/sys/firmware/devicetree/base/serial-number") as f:
                    self._serial = f.read()[:-1]
                    f.close()
            except Exception as err_msg:
                self.logger.warning(
                    "Could not access devicetree, using default information"
                )
                self._pi_model = "Raspberry Pi 4 Model B Rev 1.4"
                self._serial = "10000000e3d90xxx"
            self._cpu_info = cpuinfo.get_cpu_info()
        else:
            get_all = False

        if "hardware_raw" in self._cpu_info.keys():
            hardware_raw = self._cpu_info["hardware_raw"]
        else:
            hardware_raw = "BCM2712"
        info_str = "hardware:\n  platform:\n"
        info_str = info_str + "    type: " + self._pi_model + "\n"
        info_str = info_str + "    serial: " + self._serial + "\n"
        info_str = info_str + "  cpu:\n"
        info_str = (
            info_str
            + "    type: "
            + self._cpu_info["arch_string_raw"]
            + " "
            + hardware_raw
            + "\n"
        )
        info_str = (
            info_str + "    frequency current: " + str(psutil.cpu_freq()[0]) + "MHz\n"
        )
        info_str = (
            info_str + "    frequency max: " + str(psutil.cpu_freq()[-1]) + "MHz\n"
        )
        info_str = info_str + "    load: " + str(psutil.cpu_percent()) + "%\n"
        info_str = (
            info_str
            + "    temperature: "
            + str(round(psutil.sensors_temperatures()["cpu_thermal"][0].current, 1))
            + "°C\n"
        )
        # Calculate memory information
        memory = psutil.virtual_memory()
        info_str = info_str + "  memory:\n"
        info_str = (
            info_str
            + "    free: "
            + str(round(memory.available / 1024.0 / 1024.0, 1))
            + " MB\n"
        )
        info_str = (
            info_str
            + "    total: "
            + str(round(memory.total / 1024.0 / 1024.0, 1))
            + " MB\n"
        )
        info_str = info_str + "    percent: " + str(memory.percent) + "%\n"
        # Calculate disk information
        disk = psutil.disk_usage("/")
        info_str = info_str + "  disk:\n"
        info_str = (
            info_str
            + "    free: "
            + str(round(disk.free / 1024.0 / 1024.0 / 1024.0, 1))
            + " GB\n"
        )
        info_str = (
            info_str
            + "    total: "
            + str(round(disk.total / 1024.0 / 1024.0 / 1024.0, 1))
            + " GB\n"
        )
        info_str = info_str + "    percent: " + str(disk.percent) + "%\n"
        if get_all:
            # Get network info
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self._host_ip = s.getsockname()[0]
            s.close()
            self._host = socket.getfqdn()
        info_str = info_str + "  network:\n"
        info_str = info_str + f"    host: {self._host}\n"
        info_str = info_str + f"    ip: {self._host_ip}\n"
        info_str = info_str + f"    mac: {self.curr_mac}\n"
        info_str = info_str + f"    lan mac: {self.lan_mac}\n"
        info_str = info_str + f"    wlan mac: {self.wlan_mac}\n"

        info_str = info_str + "software:\n"
        info_str = info_str + f"  type: {SMHUB_INFO.TYPE}\n"
        info_str = info_str + f"  version: {SMHUB_INFO.SW_VERSION}\n"

        # Get logging levels
        log_level_cons = self.logger.root.handlers[0].level
        log_level_file = self.logger.root.handlers[1].level
        info_str = info_str + "  loglevel:\n"
        info_str = info_str + f"    console: {log_level_cons}\n"
        info_str = info_str + f"    file: {log_level_file}\n"
        return info_str

    async def run_api_server(self, loop, api_srv):
        """Main server for serving Smart IP calls."""
        self.server = await asyncio.start_server(
            api_srv.handle_api_command, self._host_ip, SMHUB_PORT
        )
        self.logger.info("API server started")
        async with self.server:
            try:
                await self.server.serve_forever()
            except:
                self.logger.warning("Server stopped, restarting Smart IP ...")
                return self.skip_init


def setup_logging():
    """Initialze logging settings."""

    with open("./smhub_logging.yaml", "r") as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)
    if logging.root.handlers == []:
        logging.config.dictConfig(config)
    logging.root.handlers[1].doRollover()
    logging.root.propogate = True
    return logging.getLogger(__name__)


async def open_serial_interface(device, logger) -> (any, any):
    """Open serial connection of given device."""

    logger.info(f"Try to open serial connection: {device}")
    ser_rd, ser_wr = await serial_asyncio.open_serial_connection(
        url=device,
        baudrate=RT_BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=RT_TIMEOUT,
        xonxoff=False,
    )

    if len(ser_rd._buffer) > 0:
        await ser_rd.readexactly(len(ser_rd._buffer))
        logger.info(f"Emptied serial read buffer of {device}")
    return (ser_rd, ser_wr)


async def init_serial(logger):
    """Open and initialize serial interface to router."""

    def calc_CRC(buf) -> bytes:
        """Caclulates simple xor checksum"""
        chksum = 0
        buf = buf[:-1]
        for byt in buf:
            chksum ^= ord(byt)
        buf += chr(chksum)
        return buf

    router_booting = True

    # For Pi5: "dtparam=uart0_console" into config.txt on sd boot partition
    def_device = "/dev/serial0"  # ["/dev/ttyS0", "/dev/ttyS1", "/dev/ttyAMA0", "/dev/tty1", "/dev/tty0"]
    try:
        rt_serial = await open_serial_interface(def_device, logger)
    except Exception as err_msg:
        logger.info(f"Error opening {def_device}: {err_msg}")

    try:
        new_query = True
        while router_booting:
            if new_query:
                rt_cmd = calc_CRC(
                    RT_CMDS.STOP_MIRROR.replace("<rtr>", chr(RT_DEF_ADDR))
                )
                rt_serial[1].write(rt_cmd.encode("iso8859-1"))
            reading = asyncio.ensure_future(rt_serial[0].read(1024))
            await asyncio.sleep(0.2)
            if reading._state == "FINISHED":
                resp_buf = reading.result()
                if len(resp_buf) < 4:
                    # sometimes just 0xff comes, needs another read
                    logger.warning(f"Unexpected short test response: {resp_buf}")
                    new_query = False
                elif new_query & (resp_buf[4] == 0x87):
                    logger.info(f"Router available")
                    router_booting = False
                elif (not new_query) & (resp_buf[3] == 0x87):
                    logger.info(f"Router available")
                    router_booting = False
                elif new_query & (resp_buf[4] == 0xFD):  # 253
                    logger.info(f"Waiting for router booting...")
                    await asyncio.sleep(5)
                    new_query = True
                elif (not new_query) & (resp_buf[3] == 0xFD):  # 253
                    logger.info(f"Waiting for router booting...")
                    await asyncio.sleep(5)
                    new_query = True
                else:
                    logger.warning(f"Unexpected test response: {resp_buf}")
                    new_query = True
            else:
                raise Exception(f"No test response received")
                new_query = True
    except Exception as err_msg:
        logger.error(f"Error during test stop mirror command: {err_msg}")
        rt_serial = None
    return rt_serial


async def close_serial_interface(rt_serial):
    """Closes connection, uses writer"""
    rt_serial[1].close()
    await rt_serial[1].wait_closed()


async def main(init_flag, ev_loop):
    """Open serial connection, start server, and tasks"""
    init_flag = True
    startup_ok = False
    retry_max = 3
    retry_serial = retry_max
    logger = setup_logging()
    try:
        # Instantiate SmartHub object
        sm_hub = SmartHub(ev_loop, logger)
        rt_serial = None
        while (rt_serial == None) & (retry_serial >= 0):
            if retry_serial < retry_max:
                logger.warning(
                    f"Initialization of serial connection failed, retry {retry_max-retry_serial}"
                )
            rt_serial = await init_serial(logger)
            retry_serial -= 1
        if rt_serial == None:
            init_flag = False
            logger.error(f"Initialization of serial connection failed")
        # Instantiate config server object
        logger.debug("Initializing config server")
        sm_hub.conf_srv = ConfigServer(sm_hub)
        await sm_hub.conf_srv.initialize()
        # Instantiate query object
        logger.debug("Initializing query server")
        sm_hub.q_srv = QueryServer(ev_loop, sm_hub)
        await sm_hub.q_srv.initialize()
        # Instantiate api_server object
        logger.debug("Initializing API server")
        sm_hub.api_srv = ApiServer(ev_loop, sm_hub, rt_serial)
        if init_flag:
            await sm_hub.api_srv.get_initial_status()
        else:
            logger.warning("Initialization of router and modules skipped")
        startup_ok = True
    except Exception as error_msg:
        # Start failed ...
        logger.error(f"Smart Hub start failed, exception: {error_msg}")
    if not (startup_ok):
        # ... retry restarting main()
        logger.warning("Smart Hub main restarting")
        return 0

    # Initialization successfulle done, start servers
    try:
        async with sm_hub.tg:
            logger.debug("Starting API server")
            skip_init = sm_hub.tg.create_task(
                sm_hub.run_api_server(ev_loop, sm_hub.api_srv), name="api_srv"
            )
            logger.debug("Starting query server")
            sm_hub.tg.create_task(sm_hub.q_srv.run_query_srv(), name="q_srv")
            logger.debug("Starting config server")
            await sm_hub.conf_srv.prepare()
            sm_hub.tg.create_task(sm_hub.conf_srv.site.start(), name="conf_srv")
            logger.info("Config server running")
    except Exception as err_msg:
        logger.error(
            f"Error starting servers, SmartHub already running? Msg: {err_msg}"
        )
        logger.warning("Program terminates in 4 s.")
        await asyncio.sleep(4)
        exit()

    # Waiting until finished
    try:
        await asyncio.wait(sm_hub.tg)
    except Exception as err_msg:
        pass
    rt_serial[1].close()
    if sm_hub.restart:
        return 1
    elif skip_init:
        return -1
    else:
        return 1


init_count = 0
init_flag = True
# init_flag = False
ev_loop = asyncio.new_event_loop()
while True:
    if init_count > 2:
        init_flag = False  # Restart without initialization
    term_flg = ev_loop.run_until_complete(main(init_flag, ev_loop))
    if term_flg == 0:
        init_count += 1
    elif term_flg == -1:
        init_flag = False
        init_count = 0
    else:
        init_flag = True
        init_count = 0
