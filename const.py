"""Constants for SmartHub"""

from typing import Final


OWN_IP = "192.168.178.110"
ANY_IP = "0.0.0.0"
SMHUB_PORT = 7777
EVENT_PORT = 7778
CONF_PORT = 7780
QUERY_PORT = 30718
OWN_INGRESS_IP = "172.30.32.1"
ALLOWED_INGRESS_IPS = ["172.30.32.2"]
INGRESS_PORT = 8099
RT_DEF_ADDR = 1
RT_BAUDRATE = [19200, 38400]
RT_TIMEOUT = 5
MIRROR_CYC_TIME = 1
RD_DELAY = 0.1
DATA_FILES_DIR = "./"
DATA_FILES_ADDON_DIR = "/config/"
FWD_TABLE_FILE = "ip_table.fwd"
WEB_FILES_DIR = "./web/"
LOGGING_DEF_FILE = "logging_def.yaml"
HOMEPAGE = "configurator.html"
HUB_HOMEPAGE = "hub.html"
CONF_HOMEPAGE = "home.html"
NOT_AUTH_PAGE = "not_auth.html"
SIDE_MENU_FILE = "side-menu.html"
LICENSE_PAGE = "licenses.html"
LICENSE_TABLE = "license_table.html"
LICENSE_PATH = "web/license_files/"
CONFIG_TEMPLATE_FILE = "config_template.html"
SETTINGS_TEMPLATE_FILE = "settings_template.html"
AUTOMATIONS_TEMPLATE_FILE = "automations_template.html"
AUTOMATIONEDIT_TEMPLATE_FILE = "automation_edit_template.html"


class SMHUB_INFO:
    """Holds information."""

    SW_VERSION = "1.3.6"
    TYPE = "Smart Hub"
    TYPE_CODE = "20"
    SERIAL = "RBPI"


class API_CATEGS:
    "Categries of API handlers"
    DATA = 10
    SETTINGS = 20
    ACTIONS = 30
    FILES = 40
    SETUP = 50
    ADMIN = 60
    FORWARD = 80


class API_DATA:
    """Command descriptors for data API."""

    # MODOVW_PATHQUEST = 256 * 1 + 1
    MODOVW_DIRECT = 256 * 1 + 2
    MODOVW_NEW = 256 * 1 + 3
    MODOVW_FW = 256 * 1 + 4

    # SMG_PATHQUEST = 256 * 2 + 1
    # SMGS_PATHQUEST = 256 * 2 + 2
    # SMG_FTPSEND = 256 * 2 + 3
    # SMGS_FTPSEND = 256 * 2 + 4
    # SMG_FTPREAD = 256 * 2 + 5
    # SMGS_FTPREAD = 256 * 2 + 6
    SMGS_PCREAD = 256 * 2 + 7

    # SMC_PATHQUEST = 256 * 3 + 1
    # SMCS_PATHQUEST = 256 * 3 + 2
    # SMC_FTPSEND = 256 * 3 + 3
    # SMCS_FTPSEND = 256 * 3 + 4
    # SMC_FTPREAD = 256 * 3 + 5
    # SMCS_FTPREAD = 256 * 3 + 6
    SMCS_PCREAD = 256 * 3 + 7

    # SMR_PATHQUEST = 256 * 4 + 1
    # SMR_FTPSEND = 256 * 4 + 2
    SMR_PCREAD = 256 * 4 + 3
    RSTAT_PCREAD = 256 * 4 + 4
    RT_NAME_FW_NM_PCREAD = 256 * 4 + 5

    MOD_STAT_PCREAD = 256 * 5 + 1
    MOD_CSTAT_PCREAD = 256 * 5 + 2  # compact status

    SMHUB_BOOTQUEST = 256 * 6 + 1
    SMHUB_GETINFO = 256 * 6 + 2
    SMHUB_UPDATE = 256 * 6 + 3

    DESC_PCREAD = 256 * 7 + 1


class API_SETTINGS:
    """Command descriptors for settings API."""

    DTQUEST = 256 * 1 + 1
    DTSET = 256 * 1 + 2
    MDQUEST = 256 * 2 + 1
    MDSET = 256 * 2 + 2
    VERQUEST = 256 * 30 + 0
    MIRRSTART = 256 * 40 + 1
    MIRRSTOP = 256 * 40 + 2
    EVENTSTART = 256 * 40 + 7
    EVENTSTOP = 256 * 40 + 8
    MD_SETTINGS = 256 * 50 + 1
    CONN_TST = 256 * 100 + 0


class API_ACTIONS:
    """Command descriptors for interactions API."""

    OUT_ON = 256 * 1 + 1
    OUT_OFF = 256 * 1 + 2
    DIMM_SET = 256 * 1 + 3
    COVR_SET = 256 * 1 + 4
    TEMP_SET = 256 * 2 + 1
    VIS_CMD = 256 * 3 + 1
    COLL_CMD = 256 * 4 + 1
    DIR_CMD = 256 * 5 + 1

    SET_OPR_MODE = 256 * 10 + 1
    SET_SRV_MODE = 256 * 10 + 2

    OUTP_OFF = 256 * 11 + 0
    OUTP_ON = 256 * 11 + 1
    OUTP_TOGL = 256 * 11 + 2
    OUTP_TIME = 256 * 11 + 3
    OUTP_VAL = 256 * 11 + 4

    OUTP_RBG_OFF = 256 * 12 + 0
    OUTP_RBG_ON = 256 * 12 + 1
    OUTP_RBG_TOGL = 256 * 12 + 2
    OUTP_RBG_TIME = 256 * 12 + 3
    OUTP_RBG_VAL = 256 * 12 + 4
    OUTP_RBG_RD = 256 * 12 + 5
    OUTP_RBG_GN = 256 * 12 + 6
    OUTP_RBG_BL = 256 * 12 + 7
    OUTP_RBG_WH = 256 * 12 + 10

    MODLIGHT_OFF = 256 * 13 + 0
    MODLIGHT_ON = 256 * 13 + 1
    MODLIGHT_TOGL = 256 * 13 + 2
    MODLIGHT_TIME = 256 * 13 + 3
    MODLIGHT_COL = 256 * 13 + 4

    COVER_STOP = 256 * 14 + 0
    COVER_UP = 256 * 14 + 1
    COVER_DOWN = 256 * 14 + 2
    COVER_PERC = 256 * 14 + 3
    COVER_TILT = 256 * 14 + 4

    FLAG_RESET = 256 * 15 + 0
    FLAG_SET = 256 * 15 + 1
    FLAG_TIME = 256 * 15 + 3

    LOGIC_RESET = 256 * 16 + 0
    LOGIC_SET = 256 * 16 + 1
    COUNTR_UP = 256 * 16 + 2
    COUNTR_DOWN = 256 * 16 + 3
    COUNTR_VAL = 256 * 16 + 4

    MSG_RESET = 256 * 17 + 0
    MSG_SET = 256 * 17 + 1
    MSG_TIME = 256 * 17 + 3

    BUZZER_SET = 256 * 18 + 1


class API_FILES:
    """Command descriptors for files API."""

    SMM_SEND = 256 * 0 + 1
    SMM_TO_MOD = 256 * 0 + 2
    SMM_DISC = 256 * 0 + 3

    SMG_SEND = 256 * 1 + 1
    SMG_TO_MOD = 256 * 1 + 2
    SMG_DISC = 256 * 1 + 3
    SMG_STAT = 256 * 1 + 4

    SMC_SEND = 256 * 2 + 1
    SMC_TO_MOD = 256 * 2 + 2
    SMC_DISC = 256 * 2 + 3
    SMC_STAT = 256 * 2 + 4

    SMR_SEND = 256 * 3 + 1
    SMR_TO_RT = 256 * 3 + 2
    SMR_DISC = 256 * 3 + 3
    SMR_STAT = 256 * 3 + 4

    BIN_SEND = 256 * 4 + 1
    BIN_MOD = 256 * 4 + 2
    BIN_DISC = 256 * 4 + 3
    BIN_AUTO_MOD = 256 * 4 + 4

    STAT_MOD_UPD = 256 * 4 + 11
    STAT_RT_UPD = 256 * 4 + 12
    STAT_TRANSF = 256 * 4 + 13

    SMG_SMC_MOD = 256 * 5 + 1

    SMB_SEND = 256 * 6 + 1
    SMB_QUEST = 256 * 6 + 2

    LOG_QUEST = 256 * 7 + 1


class API_SETUP:
    """Command descriptors for communication API."""

    KEY_TEACH = 256 * 1 + 1
    KEY_DEL = 256 * 1 + 2
    KEY_DEL_LIST = 256 * 1 + 3
    KEY_PAIR = 256 * 1 + 4
    KEY_STAT = 256 * 1 + 5
    KEY_LOG_DEL = 256 * 1 + 6
    KEY_LOG_RD = 256 * 1 + 7
    KEY_DEL_ALL = 256 * 1 + 8
    KEY_LOG_RDSTAT = 256 * 1 + 9
    KEY_VERS = 256 * 1 + 10
    KEY_RD_EF = 256 * 1 + 11
    KEY_RD_HUB = 256 * 1 + 12
    KEY_RDT_EF = 256 * 1 + 13
    KEY_RDT_FS = 256 * 1 + 14
    KEY_WRT_SF = 256 * 1 + 15
    KEY_WRT_FE = 256 * 1 + 16

    GET_IRDA = 256 * 2 + 1

    AIR_RD = 256 * 2 + 2
    AIR_FILE_RD = 256 * 2 + 3
    AIR_FILE_WT = 256 * 2 + 4
    AIR_CAL = 256 * 2 + 5


class API_ADMIN:
    """Command descriptors for admin API."""

    SMHUB_REINIT = 256 * 0 + 0
    SMHUB_INFO = 256 * 0 + 1
    SMHUB_RESTART = 256 * 0 + 2
    SMHUB_REBOOT = 256 * 0 + 3
    SMHUB_NET_INFO = 256 * 0 + 4
    SMHUB_LOG_LEVEL = 256 * 0 + 5

    RT_START_FWD = 256 * 1 + 1
    RT_RD_MODERRS = 256 * 1 + 2
    RT_LAST_MODERR = 256 * 1 + 3
    RT_RESTART = 256 * 1 + 4
    RT_CHAN_STAT = 256 * 1 + 5
    RT_CHAN_SET = 256 * 1 + 6
    RT_CHAN_RST = 256 * 1 + 7
    RT_FWD_STARTED = 256 * 1 + 8
    RT_SET_MODADDR = 256 * 1 + 9
    RT_RST_MODADDR = 256 * 1 + 10
    RT_COMM_STAT = 256 * 1 + 11
    RT_RST_COMMERR = 256 * 1 + 12
    RT_FWD_SET = 256 * 1 + 13
    RT_FWD_DEL = 256 * 1 + 14
    RT_FWD_DELALL = 256 * 1 + 15
    RT_SYS_RESTART = 256 * 1 + 16
    RT_BOOT_STAT = 256 * 1 + 17

    MD_RESTART = 256 * 3 + 1
    MD_CHAN_SET = 256 * 3 + 6
    MD_CHAN_RST = 256 * 3 + 7

    RT_WRAPPER_SEND = 256 * 4 + 0
    RT_WRAPPER_RECV = 256 * 4 + 1


class API_FORWARD:
    """Command forwarded from other Smart Hub or Smart IP"""

    FWD_TABLE_DEL = 256 * 0 + 0
    FWD_TABLE_RD = 256 * 0 + 1
    FWD_TABLE_ADD = 256 * 0 + 2
    FWD_TABLE_SET = 256 * 0 + 3
    FWD_TO_SMHUB = 256 * 1 + 1


class API_RESPONSE:
    """Response for status messages."""

    smg_upload_stat = "\x28\x01\x04<rtr><mod>\x01\x00<flg>\xff\xff?"
    smc_upload_stat = "\x28\x02\x04<rtr><mod>\x01\x00<flg>\xff\xff?"
    smr_upload_stat = "\x28\x03\x04<rtr>\x00\x01\x00<flg>\xff\xff?"
    bin_upload_stat = "\x28\x04\x0d<rtr>\x00\x03\x00<pkg><flg><pkgs>\xff\xff?"
    modfw_flash_stat = "\x28\x04\x0b<rtr>\x00<lenl><lenh><protocol>\xff\xff?"
    rtfw_flash_stat = "\x28\x04\x0c<rtr>\x00\x03\x00<rtr><pkgl><pkgh>\xff\xff?"
    keylog_upload_stat = "\x32\x01\x09<rtr><mod>\x03\x00<flg>\x00\x00\xff\xff?"
    event_trigger = "\x32\x01\x09<rtr><mod>\x03\x00<event><arg1><arg2>\xff\xff?"


def_cmd = b"\xa8\x21\x00\x0bSmartConfig\x05michlS\x05\x14d\x00\x00\x00\x00\x00\x58\x23?"
def_len = 0x21


class RT_CMDS:
    """Define router command strings with placeholders."""

    SET_SRV_MODE = "\x2a<rtr>\x06\x85\x00\xff"
    SET_OPR_MODE = "\x2a<rtr>\x08\x85\x01<mirr><evnt>\xff"

    GET_DATE = "\x2a<rtr>\x07\xbe\x4c\x44\xff"
    GET_TIME = "\x2a<rtr>\x07\xbe\x4c\x54\xff"
    SET_DATE = "\x2a<rtr>\x0a\xbe\x53\x44<day><mon><yr>\xff"
    SET_TIME = "\x2a<rtr>\x0a\xbe\x53\x54<sec><min><hr>\xff"

    GET_MODE_NAME = "\x2a<rtr>\x07\x68\x4c<mno>\xff"
    GET_GLOB_MODE = "\x2a<rtr>\x05\x88\xff"
    SET_GLOB_MODE = "\x2a<rtr>\x06\x89<md>\xff"
    GET_GRP_MODE = "\x2a<rtr>\x08\x89\x4f\x4c<grp>\xff"
    SET_GRP_MODE = "\x2a<rtr>\x09\x89\x4f\x53<grp><md>\xff"
    GET_GRPS_MODE = "\x2a<rtr>\x07\x89\x4f\x01\xff"
    SET_GRPS_MODE = "\x2a<rtr>\x47\x89\x4f\x02<mds>\xff"  # len: 0x47 = 7 + 64

    GET_RT_NAME = "\x2a<rtr>\x06\x67\x4c\xff"
    GET_RT_STATUS = "\x2a<rtr>\x06\x64L\xff"
    GET_RT_SW_VERSION = "\x2a<rtr>\x05\xc8\xff"
    GET_RT_SERNO = "\x2a<rtr>\x06\x69\x4c\xff"
    GET_RT_CHANS = "\x2a<rtr>\x07\x63\x50\x4c\xff"
    GET_RT_TIMEOUT = "\x2a<rtr>\x07\x66\x01\x4c\xff"
    GET_RT_GRPNO = "\x2a<rtr>\x08\x66\x01\x89\x01\xff"
    GET_RT_GRPMOD_STAT = "\x2a<rtr>\x07\x89\x4f\x01\xff"
    GET_RT_GRPMODE_DEP = "\x2a<rtr>\x08\x66\x01\x89\x65\xff"
    GET_RT_DAYNIGHT = "\x2a<rtr>\x06\x8c\x4c\xff"
    GET_RT_MODENAM = "\x2a<rtr>\x07\x68\x4c<umd>\xff"
    SEND_RT_NAME = "\x2a<rtr>\xff\x67\x53"
    CLEAR_RT_SENDBUF = "\x2a<rtr\x07\x66\x02\xc8\xff"
    SEND_RT_TIMEOUT = "\x2a<rtr>\x08\x66\x01\x54<tout>\xff"
    SEND_RT_GRPNO = "\x2a<rtr>\xff\x66\x01\x89\x02"
    SET_MOD_GROUP = "\x2a<rtr>\x0a\x66\x01\x89\x53<mod><grp>\xff"
    SEND_RT_GRPMODE_DEP = "\x2a<rtr>\xff\x66\x01\x89\x66"
    SEND_RT_DAYNIGHT = "\x2a<rtr>\xff\x8c\x4c"
    SEND_RT_MODENAM = "\x2a<rtr>\xff\x68\x53<umd>\x01"
    START_RT_FORW_MOD = "\x2a<rtr>\x09\x44<mod>\x05\xc7\x58\xff"
    START_RT_FORW_SYS = "\x2a<rtr>\x06\x58\x58\xff"
    RT_FORW_SET = "\x2a<rtr>\x0a\x58\x01<mod_src><cmd_src><rt_trg><mod_trg>\xff"
    RT_FORW_DEL_1 = "\x2a<rtr>\x0a\x58\x00<mod_src><cmd_src><rt_trg><mod_trg>\xff"
    RT_FORW_DEL_ALL = "\x2a<rtr>\x06\x58\x65\xff"
    RT_FORW_DEL_INT = "\x2a<rtr>\x06\x58\x65\xff"

    GET_RT_CHAN_STAT = "\x2a<rtr>\x07\xee\x01\x43\xff"
    SET_RT_CHAN = "\x2a<rtr>\x08\xee\x02\x43<msk>\xff"
    RES_RT_CHAN = "\x2a<rtr>\x08\xee\x03\x43<msk>\xff"
    GET_RT_BOOTSTAT = "\x2a<rtr>\x06\x6a\x4c\xff"

    GET_MD_COMMSTAT = "\x2a<rtr>\x07\x65<mod>x\xff"
    RST_MD_COMMSTAT = "\x2a<rtr>\x07\x65<mod>L\xff"
    RST_MD_ERRORS = "\x2a<rtr>\x06\x65\xfd\xff"
    GET_MD_LASTERR = "\x2a<rtr>\x06\x65\xfe\xff"
    GET_MD_ERRORS = "\x2a<rtr>\x06\x64\xff\xff"

    GET_RT_MODULES = "\x2a<rtr>\x06\x63\x01\xff"
    SEND_RT_CHANS = "\x2a<rtr>\xff\x63\x50\x53"
    DEL_MD_ADDR = "\x2a<rtr>\x07\x63\xb4<mod>\xff"
    SET_MD_ADDR = "\x2a<rtr>\x08\x63\x4d<ch><mdnew>\xff"  # define in router
    NEXT_MD_ADDR = "\x2a<rtr>\x08\x63\x6e<ch><mdnew>\xff"
    CHG_MD_ADDR = "\x2a<rtr>\x0c\x44<mod>\x08\x01<rtr><mdnew>\x42\x53\xff"

    GET_AIR_QUAL = "\x2a<rtr>\x0a\x44<mod>\x06\xd2\x03\x14\xff"
    CAL_AIR_QUAL = "\x2a<rtr>\x0f\x44<mod>\x0b\xd2\x03\x14\x01<prc_good><good_long><prc_bad><bad_long>\xff"

    RT_REBOOT = "\x2a<rtr>\x0a\xf0\x52\x45\x53\x45\x54\xff"
    MD_REBOOT = "\x2a<rtr>\x0d\x44<mod>\x09\xf0RESET\xff"

    GET_MOD_SMC = "\x2a<rtr>\x0a\x44<mod>\x06\xc7<area><pckg>\xff"
    SEND_MOD_SMC = "\x2a<rtr><len>\x44<mod><l4>\xc7"

    START_EVENTS = "\x2a<rtr>\x07\x86\xff\x64\xff"
    STOP_EVENTS = "\x2a<rtr>\x07\x86\xfe\x64\xff"
    START_MIRROR = "\x2a<rtr>\x07\x87\xfc<cyc>\xff"
    STOP_MIRROR = "\x2a<rtr>\x06\x87\xfe\xff"
    GET_MOD_MIRROR = "\x2a<rtr>\x06\x87<mod>\xff"

    SET_OUT_ON = "\x2a<rtr>\x0c\x44<mod>\x08\x0a\x45<outl><outm><outh>\xff"
    SET_OUT_OFF = "\x2a<rtr>\x0c\x44<mod>\x08\x0b\x41<outl><outm><outh>\xff"
    SET_FLAG_ON = "\x2a<rtr>\x0b\x44<mod>\x07\x0a\x4d<flgl><flgh>\xff"
    SET_FLAG_OFF = "\x2a<rtr>\x0b\x44<mod>\x07\x0b\x4e<flgl><flgh>\xff"
    SET_GLB_FLAG_ON = "\x2a<rtr>\x08\x0a\x1e<flgl><flgh>\xff"
    SET_GLB_FLAG_OFF = "\x2a<rtr>\x08\x0b\x1f<flgl><flgh>\xff"
    SET_DIMM_VAL = "\x2a<rtr>\x0a\x44<mod>\x06\x0f<out><val>\xff"
    SET_COVER_POS = "\x2a<rtr>\x0c\x44<mod>\x08\x12\x45<sob><out><val>\xff"
    SET_TEMP = "\x2a<rtr>\x0b\x44<mod>\x07\xdc<sel><tmpl><tmph>\xff"
    CALL_VIS_CMD = "\x2a<rtr>\x0d\x44<mod>\x09\x1f\xc7\x00\x1f<cmdh><cmdl>\xff"  # hi/lo
    CALL_DIR_CMD = "\x2a<rtr>\x09\x44<mod>\x05\x20<cmd>\xff"
    CALL_COLL_CMD = "\x2a<rtr>\x06\x32<cmd>\xff"

    SET_LOGIC_UNIT = "\x2a<rtr>\x0d\x44<mod>\x09\x06\x01\x53<lno><md><act>\xff"
    # SET_LOGIC_INP = "\x2a<rtr>\x0b\x44<mod>\x07\x04\x00<sr><inp>\xff"
    SET_COUNTER_VAL = "\x2a<rtr>\x0d\x44<mod>\x09\x06\x00<lno>\x05<val>\x00\xff"
    SET_LOGIC_INP = "\x2a<rtr>\x0c\x44<mod>\x08\x09\x45\x00<sr><inp>\xff"
    # SET_COUNTER_VAL = "\x2a<rtr>\x0e\x44<mod>\x0a\x09\x45\x00<lno>\x05<val>\x00\xff"

    SET_RGB_AMB_COL = "\x2a<rtr>\x10\x44<mod>\x0c\x23\x01\x02\x64<r><g><b>\x03\x00\xff"
    SWOFF_RGB_AMB = "\x2a<rtr>\x10\x44<mod>\x0c\x23\x02\x02\x64\x00\x00\x00\x03\x00\xff"
    SET_RGB_CORNR = "\x2a<rtr>\x10\x44<mod>\x0c\x23\x01\x01<cnr><r><g><b>\x01\x01\xff"
    SWOFF_RGB_CORNR = (
        "\x2a<rtr>\x10\x44<mod>\x0c\x23\x02\x01<cnr>\x00\x00\x00\x01\x01\xff"
    )
    SET_RGB_LED = "\x2a<rtr>\x10\x44<mod>\x0c\x23<tsk><md><inp><r><g><b><tl><th>\xff"

    SET_COVER_SETTGS = "\x2a<rtr>\x0a\x44<mod>\x06\x15\x4f<set>\xff"
    SET_COVER_TIME = "\x2a<rtr>\x0d\x44<mod>\x09\x11<sob><int><out><vala><valb>\xff"
    SET_INP_TIMES = "\x2a<rtr>\x0a\x44<mod>\x06\x02<tshrt><tlng>\xff"
    SET_INP_MODES = "\x2a<rtr>\x0c\x44<mod>\x08\x14\x4b<i_1_8><i_9_16><i_17_24>\xff"
    SET_DIMM_SPEED = "\x2a<rtr>\x09\x44<mod>\x05\x10<tdim>\xff"
    SET_DIMM_MODES = "\x2a<rtr>\x0f\x44<mod>\x0b\x10\x00\x50\x48\x41\x53\x45<msk>\xff"
    SET_T_LIM = "\x2a<rtr>\x0b\x44<mod>\x07\xdc\x64<Tlow><Thigh>\xff"
    SET_CLIMATE = "\x2a<rtr>\x0a\x44<mod>\x06\x04\x53<set>\xff"
    SET_DISPL_CONTR = "\x2a<rtr>\x0a\x44<mod>\x06\x03\x53<set>\xff"
    SET_MOD_NAME = "\x2a<rtr>\x12\x44<mod>\x0e\x67\x53<cnt><name8>\xff"
    SET_MOD_SERIAL = "\x2a<rtr>\x19\x44<mod>\x15\x69<cnt>"
    GET_MOD_SERIAL = "\x2a<rtr>\x09\x44<mod>\x05\x69\x4c\xff"
    SET_MOD_LANG = "\x2a<rtr>\x0a\x44<mod>\x06\x3c\x53<lang>\xff"
    SET_MOD_SUPPLY = "\x2a<rtr>\x0a\x44<mod>\x06\x07\x01<set>\xff"
    SET_MOD_T_LIGHT = "\x2a<rtr>\x0a\x44<mod>\x06\x03\x5a<tim>\xff"
    SET_T1_OR_T2 = "\x2a<rtr>\x0a\x44<mod>\x06\x04\xc8<set>\xff"
    SET_AD = "\x2a<rtr>\x0a\x44<mod>\x06\xda\x01<set>\xff"
    SET_MOT_DET = "\x2a<rtr>\x0c\x44<mod>\x08\x05\x45<lvl><tim><led>\xff"
    SET_EKEY_VERS = "\x2a<rtr>\x0b\x44<mod>\x07\xa9\x01\x63<ver>\xff"
    SET_EKEY_TEACH = "\x2a<rtr>\x0d\x44<mod>\x09\xa9\x01\x4e<usr><fgr><tim>\xff"
    DEL_EKEY_1 = "\x2a<rtr>\x0c\x44<mod>\x08\xa9\x01\x4c<usr><fgr>\xff"
    DEL_EKEY_ALL = "\x2a<rtr>\x0c\x44<mod>\x08\xa9\x01\x4c\xff\xff\xff"
    SET_EKEY_PAIR = "\x2a<rtr>\x0b\x44<mod>\x07\xa9\x01\x62\x41\xff"
    GET_EKEY_STAT = "\x2a<rtr>\x08\x44<mod>\x04\x64\xff"
    RES_EKEY_LOG = "\x2a<rtr>\x0a\x44<mod>\x06\xa9\x05\x52\xff"
    GET_EKEY_LOG_STRT = "\x2a<rtr>\x0a\x44<mod>\x06\xa9\x05\x01\xff"
    GET_EKEY_LOG_REST = "\x2a<rtr>\x0a\x44<mod>\x06\xa9\x05\x02\xff"
    GET_EKEY_TO_FANS = "\x2a<rtr>\x0c\x44<mod>\x08\xa9\x01\x93\x00\x00\xff"
    GET_EKEY_TO_HUB = "\x2a<rtr>\x0b\x44<mod>\x07\xa9\x01\x53<pkg>\xff"
    SET_PIN = "\x2a<rtr>\x0e\x44<mod>\x0a\xa8\x01\x32<p1><p2><p3><p4>\xff"

    UPDATE_STAT = "\x2a<rtr>\x06\xc7\x00\xff"
    UPDATE_MOD_PKG = "\x2a<rtr><len>\xc7<pno><pcnt><blen><buf>\xff"
    FLASH_MOD_FW = "\x2a<rtr>\x0a\x89\x49\x53\x50\x56<mod>\xff"
    MOD_FLASH_STAT = "\x2a<rtr>\x06\xc9\x5a\xff"
    UPDATE_RT_PKG = "\x2a<rtr><len>\xc9\x46<pno><buf>\xff"
    SET_ISP_MODE = "\x2a<rtr>\x0b\xc9\x49\x53\x50\x53<lenl><lenh>\xff"
    SYSTEM_RESTART = "\x2a<rtr>\x08\xc9\x4e\x45\x55\xff"


class RT_RESP:
    """Define router command ids."""

    DATA = 0
    ADDRESS = 1
    FLAG_GLOB = 10
    COLL_CMD = 50
    DIRECT_CMD = 68
    FORW_CMD = 87
    FORW_CHG = 88
    FLAG_GLOB_CHG = 89
    MODULES = 99
    RT_STATUS = 100
    COMM_STATUS = 101
    RT_SETTINGS = 102
    RT_NAME = 103
    MOD_NAMES = 104
    SER_NO = 105
    BOOT_PROBLEMS = 106
    MIRR_STAT = 135
    SYS_MODE = 136
    SYS_MODE_CHG = 137
    RD_MEMORY = 138
    MOD_ADDR_CHG = 139
    DAY_NIGHT = 140
    DATE_TIME = 190
    UPDATE_STAT = 199
    VERSION = 200
    RT_TRANSFER = 201
    SUPPLY_POW = 238
    NN1 = 250
    NN2 = 251
    RT_INBOOT = 253
    NN3 = 254


class MStatIdx:
    """Definition of module status index values."""

    BYTE_COUNT = 0  # in compact status included
    ADDR = 1
    MOD_DESC = 2  # low, high
    MODE = 4
    INP_1_8 = 5
    INP_9_16 = 6
    INP_17_24 = 7
    AD_1 = 8
    AD_2 = 9
    OUT_1_8 = 10
    OUT_9_16 = 11
    OUT_17_24 = 12
    USE_230V = 13
    DIM_1 = 14
    DIM_2 = 15
    DIM_3 = 16
    DIM_4 = 17
    AOUT_1 = 18
    AOUT_2 = 19
    TEMP_ROOM = 20
    TEMP_PWR = 22
    TEMP_EXT = 24
    HUM = 26
    AQI = 27
    LUM = 28
    MOV = 30
    IR_H = 31  # General field 1
    IR_L = 32  # General field 2
    WIND = 31
    WINDP = 32
    ROLL_POS = 33  # 1..8: 33..40 bei SC: Roll 3..5
    BLAD_POS = 41  # 1..8: 41..48
    T_SETP_0 = 49  # low/high
    T_SETP_1 = 51  # low/high
    RAIN = 53  # General field 3
    Gen_4 = 54
    USER_CNT = 55
    FINGER_CNT = 56
    MODULE_STAT = 57  # Errors, etc
    COUNTER = 58  # type, max_cnt, val
    COUNTER_TYP = 58  # type, 10 for counter
    COUNTER_MAX = 59  # max_cnt
    COUNTER_VAL = 60  # cnt val
    LOGIC_OUT = 88  # 1..8, 89 9..16
    FLAG_LOC = 90  # 1..8, 91 9..16 Logic-Ausgänge
    END = 92  # incl. byte_count


class MirrIdx:
    """Definition of full mirror index values."""

    ADDR = 0
    MOD_DESC = 1  # low, high
    MODE = 3
    INP_1_8 = 4
    INP_9_16 = 5
    INP_17_24 = 6
    AD_1 = 7
    AD_2 = 8
    OUT_1_8 = 9
    OUT_9_16 = 10
    OUT_17_24 = 11
    USE_230V = 12
    DIM_1 = 13
    DIM_2 = 14
    DIM_3 = 15
    DIM_4 = 16
    AOUT_1 = 17
    AOUT_2 = 18
    TEMP_ROOM = 19
    TEMP_OUTSIDE = 19  # low, high
    TEMP_PWR = 21
    TEMP_EXT = 23
    HUM = 25
    AQI = 26
    LUM = 27
    MOV = 29
    LED_I = 30  # not included in status
    IR_H = 31
    IR_L = 32
    WIND = 33  # for smart nature (wrong indices?)
    WINDP = 34  # for smart nature (wrong indices?)
    COVER_T = 33  # 1..8
    COVER_POS = 41  # 1..8
    # T_SETP_0 = 48  # low/high, alter Stand?
    BLAD_T = 49  # 1..8
    BLAD_POS = 57  # 1..8
    T_SHORT = 65
    T_LONG = 66
    T_DIM = 67
    SWMOD_1_8 = 68
    SWMOD_9_16 = 69
    SWMOD_17_24 = 70
    T_SETP_1 = 71
    T_SETP_2 = 73
    T_LIM = 75
    CLIM_SETTINGS = 77
    RAIN = 78
    DISPL_CONTR = 79
    DCF77_STAT = 79
    MOD_RESTARTED = 80
    MODMEM_DEL = 81
    MEM_ERR = 82  # low, high
    SW_CNT = 84  # low, high
    TIME_ERR = 86
    OVER_TEMP = 87
    USER_CNT = 88
    FINGER_CNT = 89
    MOV_LVL = 90
    MOV_TIME = 91
    MOD_NAME = 92  # 32 chars, eof = 0
    MOD_SERIAL = 124  # 16 chars, eof = 0
    SW_VERSION = 140  # 22 chars, eof = 0
    MODULE_STAT = 162
    PWR_VERSION = 163  # 6 chars
    SUPPLY_PRIO = 169
    MOD_LIGHT_TIM = 170
    MOD_LANG = 171
    TMP_CTL_MD = 172  # Temp controller 1 or 2
    SMC_CRC = 173  # high, low
    COVER_SETTINGS = 175
    COVER_POL = 176  # 1..4, 177 5..8 val 1 = down
    COVER_INTERP = 178  # 178 .. 185 1..8
    LOGIC = 186  # type, max_cnt, val;    logic 1..10
    COUNTER_TYP = 186  # type, 5 for counter
    COUNTER_MAX = 187  # max_cnt; max_inputs
    COUNTER_VAL = 188  # cnt val; input state for gates
    LOGIC_OUT = 216  # 1..8, 217 9..10 for logic gates
    FLAG_LOC = 218  # 1..8, 219 9..10
    STAT_AD24_ACTIVE = 220  # in24 used as AD input
    PWR_ID = 221  # power unit id
    DIMM_MODE = 222  # dimm mode
    SMKEY_STAT = 222  # Smart Key status
    SMG_CRC = 222  # Einstellungen CRC low, high
    I_224 = 224
    I_225 = 225
    END = 226  # length of mirror


# Subset of mirror for compact version
CStatBlkIdx = [
    (MirrIdx.ADDR, MirrIdx.MOV + 1),
    (MirrIdx.IR_H, MirrIdx.IR_L + 1),
    (MirrIdx.COVER_POS, MirrIdx.COVER_POS + 8),
    (MirrIdx.BLAD_POS, MirrIdx.BLAD_POS + 8),
    (MirrIdx.T_SETP_1, MirrIdx.T_SETP_2 + 2),
    (MirrIdx.RAIN, MirrIdx.DISPL_CONTR + 1),
    (MirrIdx.USER_CNT, MirrIdx.FINGER_CNT + 1),
    (MirrIdx.MODULE_STAT, MirrIdx.MODULE_STAT + 1),
    (MirrIdx.LOGIC, MirrIdx.FLAG_LOC + 2),
]

SMGIdx = [
    MirrIdx.ADDR,
    MirrIdx.MOD_DESC,
    MirrIdx.MOD_DESC + 1,
    MirrIdx.LED_I,
    # following values are stored in Mirr only once, polarity separate
    # only start value valid, mirror contains only 8 values each
    *range(MirrIdx.COVER_T, MirrIdx.COVER_T + 16),
    *range(MirrIdx.BLAD_T, MirrIdx.BLAD_T + 16),
    MirrIdx.T_SHORT,
    MirrIdx.T_LONG,
    MirrIdx.T_DIM,
    MirrIdx.SWMOD_1_8,
    MirrIdx.SWMOD_9_16,
    MirrIdx.SWMOD_17_24,
    MirrIdx.T_SETP_1,
    MirrIdx.T_SETP_1 + 1,
    MirrIdx.T_SETP_2,
    MirrIdx.T_SETP_2 + 1,
    MirrIdx.T_LIM,
    MirrIdx.T_LIM + 1,
    MirrIdx.CLIM_SETTINGS,
    MirrIdx.DISPL_CONTR,
    MirrIdx.MOV_LVL,
    MirrIdx.MOV_TIME,
    *range(MirrIdx.MOD_NAME, MirrIdx.MOD_NAME + 32),
    *range(MirrIdx.MOD_SERIAL, MirrIdx.MOD_SERIAL + 16),
    *range(MirrIdx.SW_VERSION, MirrIdx.SW_VERSION + 22),
    *range(MirrIdx.PWR_VERSION, MirrIdx.PWR_VERSION + 6),
    MirrIdx.SUPPLY_PRIO,
    MirrIdx.MOD_LIGHT_TIM,
    MirrIdx.MOD_LANG,
    MirrIdx.TMP_CTL_MD,
    MirrIdx.COVER_SETTINGS,
    *range(MirrIdx.LOGIC, MirrIdx.LOGIC + 2),  # Skip logic values
    *range(MirrIdx.LOGIC + 3, MirrIdx.LOGIC + 5),
    *range(MirrIdx.LOGIC + 6, MirrIdx.LOGIC + 8),
    *range(MirrIdx.LOGIC + 9, MirrIdx.LOGIC + 11),
    *range(MirrIdx.LOGIC + 12, MirrIdx.LOGIC + 14),
    *range(MirrIdx.LOGIC + 15, MirrIdx.LOGIC + 17),
    *range(MirrIdx.LOGIC + 18, MirrIdx.LOGIC + 20),
    *range(MirrIdx.LOGIC + 21, MirrIdx.LOGIC + 23),
    *range(MirrIdx.LOGIC + 24, MirrIdx.LOGIC + 26),
    *range(MirrIdx.LOGIC + 27, MirrIdx.LOGIC + 29),
    MirrIdx.STAT_AD24_ACTIVE,
    MirrIdx.PWR_ID,
    MirrIdx.DIMM_MODE,
]


class MSetIdx:
    """Definition of module settings index values."""

    SHUTTER_TIMES = 4
    TILT_TIMES = 20
    INP_STATE = 39  # 3 bytes
    HW_VERS = 83
    HW_VERS_ = 100
    SW_VERS = 100
    SW_VERS_ = 122
    SHUTTER_STAT = 132


class RtStatIIdx:
    """Indices for router status index into router status"""

    ADDR = 0
    CHANNELS = 1
    TIMEOUT = 2
    GROUPS = 3
    GROUP_DEPEND = 4
    NAME = 5
    UMODE_NAMES = 6
    SERIAL = 7
    DAY_NIGHT = 8
    SW_VERSION = 9
    DATE = 10
    GRP_MODE = 11


class SYS_MODES:
    """Habitron system modes."""

    Config = 0x4B
    Update = 0x49


class RT_STAT_CODES:
    """OK, not OK codes."""

    SYS_PROBLEMS = 74
    SYS_OK = 78
    MIRROR_ACTIVE = 74
    MIRROR_STOPPED = 78
    SYS_BOOTING = 74
    SYS_RUNNING = 78
    PKG_ERR = 70
    PKG_OK = 79


MODULE_CODES: Final[dict[str, str]] = {
    "\x01\x01": "Smart Controller XL-1",
    "\x01\x02": "Smart Controller XL-2",
    "\x01\x03": "Smart Controller XL-2 (LE2)",
    # "\x01\x0a": "Smart Controller X",
    "\x0a\x01": "Smart Out 8/R",
    "\x0a\x02": "Smart Out 8/T",
    "\x0a\x14": "Smart Dimm",
    "\x0a\x15": "Smart Dimm-1",
    "\x0a\x16": "Smart Dimm-2",
    "\x0a\x1e": "Smart IO 2",  # Unterputzmodul
    "\x0a\x32": "Smart Out 8/R-1",
    "\x0a\x33": "Smart Out 8/R-2",
    "\x0b\x1e": "Smart In 8/24V",
    "\x0b\x1f": "Smart In 8/24V-1",
    "\x0b\x01": "Smart In 8/230V",
    "\x14\x01": "Smart Nature",
    "\x1e\x01": "Fanekey",
    "\x1e\x03": "Smart GSM",
    "\x1e\x28": "FanMatrix",
    "\x32\x01": "Smart Controller Mini",
    # "\x32\x28": "Smart Sensors",
    "\x50\x64": "Smart Detect 180",
    "\x50\x65": "Smart Detect 360",
    "\x50\x66": "Smart Detect 180-2",
}

MODULE_TYPES: Final[dict[str, str]] = {
    "\x01\x02": "Smart Controller XL-2",
    "\x01\x03": "Smart Controller XL-2 (LE2)",
    # "\x01\x0a": "Smart Controller X",
    "\x32\x01": "Smart Controller Mini",
    "\x0a\x02": "Smart Out 8/T",
    "\x0a\x16": "Smart Dimm-2",
    "\x0a\x1e": "Smart IO2",  # Unterputzmodul
    "\x0a\x33": "Smart Out 8/R-2",
    "\x0b\x1f": "Smart In 8/24V-1",
    "\x0b\x01": "Smart In 8/230V",
    "\x14\x01": "Smart Nature",
    "\x1e\x01": "Fanekey",
    "\x1e\x03": "Smart GSM",
    "\x50\x66": "Smart Detect 180-2",
    "\x50\x65": "Smart Detect 360",
}


class IfDescriptor:
    """Habitron interface descriptor."""

    def __init__(self, iname, inmbr, itype) -> None:
        self.name: str = iname
        self.nmbr: int = inmbr
        self.type: int = itype


class LgcDescriptor(IfDescriptor):
    """Habitron logic interface descriptor."""

    def __init__(self, iname, inmbr, itype, iinputs) -> None:
        super().__init__(iname, inmbr, itype)
        self.inputs: int = iinputs


LGC_TYPES: dict[int, str] = {
    1: "AND",
    2: "NAND",
    3: "OR",
    4: "NOR",
}

FingerNames = [
    "Kleiner Finger links",
    "Ringfinger links",
    "Mittelfinger links",
    "Zeigefinger links",
    "Daumen links",
    "Daumen rechts",
    "Zeigefinger rechts",
    "Mittelfinger rechts",
    "Ringfinger rechts",
    "Kleiner Finger rechts",
]


class HA_EVENTS:
    """Identifier for home assistant events, e.g. input changes."""

    BUTTON = 1
    SWITCH = 2
    OUTPUT = 3
    COV_VAL = 4
    BLD_VAL = 5
    DIM_VAL = 6
    FINGER = 7
    IR_CMD = 8
    FLAG = 9
    CNT_VAL = 10
    PERCNT = 11
    DIR_CMD = 12
    MOVE = 13
    MODE = 15
    SYS_ERR = 16

    EVENT_DICT: dict[int, str] = {
        1: "Button",
        2: "Switch",
        3: "Output",
        4: "Cover position",
        5: "Blind position",
        6: "Dimm value",
        7: "Ekey finger",
        8: "IR command",
        9: "Flag",
        10: "Counter value",
        11: "Percent",
        12: "Direct command",
        13: "Motion",
        15: "Mode",
        16: "System error",
    }


DAY_NIGHT_MODES: dict[int, str] = {
    -1: "inaktiv",
    0: "nur Zeit",
    1: "Zeit und Helligkeit",
    2: "Zeit oder Helligkeit",
    3: "nur Helligkeit",
}
DAY_NIGHT_MODES_HELP: dict[int, str] = {
    -1: "Keine Umschaltung an diesem Wochentag",
    0: "Umschaltung zur Uhrzeit",
    1: "Umschaltung nach der Uhrzeit und beim Erreichen der Helligkeitsschwelle",
    2: "Umschaltung entweder zur Uhrzeit oder beim Erreichen der Helligkeitsschwelle",
    3: "Umschaltung beim Erreichen der Helligkeitsschwelle",
}
