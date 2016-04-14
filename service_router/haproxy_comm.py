import io
import socket
from contextlib import closing
from typing import List

class HAProxyComm:
	def __init__(self, socket_name: str):
		self._socket = socket_name

	def enable_server(self, backend: str, server: str):
		pass

	def disable_server(self, backend: str, server: str):
		pass

	def save_state(self, file: str) -> None:
		with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as sock, open(file, 'wb') as fo:
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

		return recv.getvalue().decode().splitlines()
