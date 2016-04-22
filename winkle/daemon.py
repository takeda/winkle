import atexit
import fcntl
import grp
import logging
import os.path
import pwd
# import string
# import subprocess
import socket
import sys
import time

from contextlib import closing
from typing import Callable, Optional

# from pkg_resources import resource_string

log = logging.getLogger(__name__)

# def install(config):
# 	user, group = config['user'], config['group']
# 	uid, gid = get_ids(user, group)
#
# 	if os.getuid() != 0:
# 		print("This command requires root permissions")
# 		sys.exit(os.EX_USAGE)
#
# 	for file in [config['logfile'], config['pidfile']]:
# 		dir = os.path.dirname(file)
# 		print("Ensuring that %s exists and is owned by %s:%s" % (dir, uid, gid))
#
# 		try:
# 			os.makedirs(dir)
# 		except OSError:
# 			pass
#
# 		os.chown(dir, uid, gid)
# 		os.chmod(dir, 0o755)
#
# 	sysname = os.uname()[0]
# 	if sysname == 'Linux':
# 		rc = '/etc/init.d'
# 	elif sysname == 'FreeBSD':
# 		rc = '/usr/local/etc/rc.d'
# 	else:
# 		rc = '/etc/rc.d'
#
# 	script_file = os.path.join(rc, 'etmagent')
#
# 	template = resource_string(__name__, 'files/etmagent.in').decode('us-ascii')
# 	rc_script = string.Template(template).safe_substitute({
# 		'subs_pid_file': config['pidfile'],
# 		'subs_etmagent_bin': sys.argv[0],
# 		'subs_options': '-u %s:%s -p %s -l %s' % (user, group, config['pidfile'], config['logfile'])
# 	})
#
# 	print("Installing %s init script" % script_file)
# 	with open(script_file, 'w') as fo:
# 		fo.write(rc_script)
# 		os.fchmod(fo.fileno(), 0o755)
#
# 	print("Enabling etmagent service")
# 	subprocess.check_call(["chkconfig", "--add", "etmagent"])

def get_ids(user, group):
	user = pwd.getpwnam(user)[2]
	group = grp.getgrnam(group)[2]

	return user, group

def reduce_privileges(uid):
	if os.getuid() != 0:
		return

	user, group = uid

	os.setgid(group)
	os.setuid(user)

def create_pidfile(pidfile: str) -> Optional[int]:
	fd = os.open(pidfile, os.O_RDWR | os.O_CREAT)
	try:
		fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
	except (OSError, IOError):
		os.close(fd)
		print("It appears that the winkle is already running; exiting.")
		return None

	@atexit.register
	def remove_pidfile():
		log.debug("Removing pid file")
		os.unlink(pidfile)
		os.close(fd)

	return fd

def write_pidfile(pid_fd: int) -> None:
	log.debug("Writing pid file")
	os.truncate(pid_fd, 0)
	os.write(pid_fd, str(os.getpid()).encode('us-ascii'))

def daemonize(pidfile: str, func: Callable[[], None], *args, **kwargs) -> None:
	pid_fd = create_pidfile(pidfile)
	if not pid_fd:
		sys.exit(os.EX_UNAVAILABLE)

	parent, child = socket.socketpair()

	try:
		pid = os.fork()
	except OSError as e:
		print("Error when trying to launch into background: %s" % e)
		sys.exit(os.EX_OSERR)

	if pid == 0:
		try:
			parent.close()

			# Obtain lock to the file from the parent (this time wait for it)
			try:
				log.debug("Waiting for pid file unlock from the parent")
				child.send(b'x')
				fcntl.lockf(pid_fd, fcntl.LOCK_EX)
				child.close()
			except (OSError, IOError):
				log.error("Unable to obtain lock for the pid file; this should never happen")
				sys.exit(os.EX_OSERR)

			write_pidfile(pid_fd)

			# Start a new session
			os.setsid()

			with open(os.devnull, 'br+') as devnull:
				for i in range(3):
					os.dup2(devnull.fileno(), i)

			func(*args, **kwargs)
		except:
			log.exception("Got an unhandled error")
			raise
	else:
		child.close()
		parent.recv(1)
		parent.close()

		log.debug("Freeing lock for pid file to the child")
		fcntl.lockf(pid_fd, fcntl.LOCK_UN)
		# noinspection PyProtectedMember
		os._exit(os.EX_OK)  # ensure we don't call atexit() (i.e. don't remove the pid file)

	sys.exit(os.EX_OK)
