from enum import IntEnum, Enum


class Flags(IntEnum):
	@classmethod
	def flags(cls, value):
		return tuple(flag for flag in cls if value & flag)

class ServerState(Enum):
	SRV_ST_STOPPED = 0   # the server is down. Please keep set to zero.
	SRV_ST_STARTING = 1  # the server is warming up (up but throttled)
	SRV_ST_RUNNING = 2   # the server is fully up
	SRV_ST_STOPPING = 3  # the server is up but soft-stopping (eg: 404)

class ServerAdmin(Flags):
	SRV_ADMF_FMAINT = 0x01  # the server was explicitly forced into maintenance
	SRV_ADMF_IMAINT = 0x02  # the server has inherited the maintenance status from a tracked server
	SRV_ADMF_CMAINT = 0x04  # the server is in maintenance because of the configuration
	SRV_ADMF_FDRAIN = 0x08  # the server was explicitly forced into drain state
	SRV_ADMF_IDRAIN = 0x10  # the server has inherited the drain status from a tracked server
#	SRV_ADMF_MAINT = 0x03   # mask to check if any maintenance flag is present
#	SRV_ADMF_DRAIN = 0x18   # mask to check if any drain flag is present

class CheckResult(Enum):
	CHK_RES_UNKNOWN = 0   # initialized to this by default
	CHK_RES_NEUTRAL = 1   # valid check but no status information
	CHK_RES_FAILED = 2    # check failed
	CHK_RES_PASSED = 3    # check succeeded and server is fully up again
	CHK_RES_CONDPASS = 4  # check reports the server doesn't want new sessions

class CheckState(Flags):
	CHK_ST_INPROGRESS = 0x0001  # a check is currently running
	CHK_ST_CONFIGURED = 0x0002  # this check is configured and may be enabled
	CHK_ST_ENABLED = 0x0004     # this check is currently administratively enabled
	CHK_ST_PAUSED = 0x0008      # checks are paused because of maintenance (health only)
	CHK_ST_AGENT = 0x0010       # check is an agent check (otherwise it's a health check)


# noinspection PyInconsistentIndentation
class CheckStatus(Enum):
	HCHK_STATUS_UNKNOWN = 0    # Unknown
	HCHK_STATUS_INI = 1        # Initializing
	HCHK_STATUS_START = 2      # Check started

	# Below we have finished checks
	HCHK_STATUS_CHECKED = 3    # DUMMY STATUS
	HCHK_STATUS_HANA = 4       # Health analyze detected enough consecutive errors
	HCHK_STATUS_SOCKERR = 5    # Socket error

	HCHK_STATUS_L4OK = 6       # L4 check passed, for example tcp connect
	HCHK_STATUS_L4TOUT = 7     # L4 timeout
	HCHK_STATUS_L4CON = 8      # L4 connection problem, for example:
	#  "Connection refused" (tcp rst) or "No route to host" (icmp)

	HCHK_STATUS_L6OK = 9       # L6 check passed
	HCHK_STATUS_L6TOUT = 10    # L6(SSL) timeout
	HCHK_STATUS_L6RSP = 11     # L6 invalid response - protocol error

	HCHK_STATUS_L7TOUT = 12    # L7 (HTTP/SMTP) timeout
	HCHK_STATUS_L7RSP = 13     # L7 invalid response - protocol error

	# Below we have layer 5 - 7 data available
	HCHK_STATUS_L57DATA = 14   # DUMMY STATUS
	HCHK_STATUS_L7OKD = 15     # L7 check passed
	HCHK_STATUS_L7OKCD = 16    # L7 check conditionally passed
	HCHK_STATUS_L7STS = 17     # L7 response error, for example HTTP 5xx

	HCHK_STATUS_PROCERR = 18   # External process check failure
	HCHK_STATUS_PROCTOUT = 19  # External process check timeout
	HCHK_STATUS_PROCOK = 20    # External process check passed
