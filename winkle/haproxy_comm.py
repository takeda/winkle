import csv
import io
import socket
from contextlib import closing
from pathlib import Path
from typing import List, Dict, Any

from .haproxy_comm_enums import ServerState, ServerAdmin, CheckStatus, CheckResult, CheckState

csv.register_dialect('haproxy', delimiter=' ', quoting=csv.QUOTE_NONE)

T_SERVERS_STATE = Dict[str, Dict[str, Any]]

class HAProxyComm:
	def __init__(self, socket_name: str):
		self._socket = socket_name

	def get_backends(self):
		response = self._command('show backend')
		assert response[0] == '# name', 'Unexpected response from HAProxy'
		return response[1:]

	def get_servers_state(self, backend: str) -> T_SERVERS_STATE:
		response = self._command('show servers state %s' % backend)
		assert response[0] == '1', "Unsupported version of HAProxy output"

		reader = csv.DictReader(response[1:], dialect='haproxy')
		reader.fieldnames = reader.fieldnames[1:]  # HAProxy marks fields with '#'

		state = {}
		for row in reader:
			row['srv_op_state'] = ServerState(int(row['srv_op_state']))
			row['srv_admin_state'] = ServerAdmin.flags(int(row['srv_admin_state']))
			row['srv_check_status'] = CheckStatus(int(row['srv_check_status']))
			row['srv_check_result'] = CheckResult(int(row['srv_check_result']))
			row['srv_check_state'] = CheckState.flags(int(row['srv_check_state']))
			row['srv_agent_state'] = CheckState.flags(int(row['srv_agent_state']))
			state[row['srv_name']] = row

		return state

	def is_server_disabled(self, backend: str, server: str, servers_state: T_SERVERS_STATE = None):
		if servers_state is None:
			servers_state = self.get_servers_state(backend)

		return ServerAdmin.SRV_ADMF_FMAINT in servers_state[server]['srv_admin_state']

	def enable_server(self, backend: str, server: str):
		self._command('enable server %s/%s' % (backend, server))

	def disable_server(self, backend: str, server: str):
		self._command('disable server %s/%s' % (backend, server))

	def save_state(self, file: Path) -> None:
		with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as sock, file.open('wb') as fo:
			sock.connect(self._socket)
			sock.sendall(b'show servers state\n')

			while True:
				buff = sock.recv(1024)
				if len(buff) == 0:
					break
				fo.write(buff)

	def _command(self, command: str) -> List[str]:
		recv = io.BytesIO()
		with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as sock:
			sock.connect(self._socket)
			sock.sendall('{}\n'.format(command).encode())

			while True:
				buff = sock.recv(1024)
				if len(buff) == 0:
					break

				recv.write(buff)

		result = recv.getvalue().decode().splitlines()

		# truncate empty lines at the end
		while len(result) > 0 and result[-1] == '':
			result = result[0:-1]

		return result