
from nintendo.nex import rmc, kerberos, \
	authentication, common, settings
import collections
import secrets
import datetime
import aioconsole
import utils
from dotenv import load_dotenv
import os
import logging
logging.basicConfig(level=logging.INFO)

load_dotenv()


User = collections.namedtuple("User", "pid name password")

users = [
	User(2, "Quazal Rendez-Vous", "password"),
	User(100, "guest", "MMQea3n!fsik")
]

def get_user_by_name(name):
	for user in users:
		if user.name == name:
			return user
			
def get_user_by_pid(pid):
	for user in users:
		if user.pid == pid:
			return user
			
def derive_key(user):
	deriv = kerberos.KeyDerivationOld(65000, 1024)
	return deriv.derive_key(user.password.encode("ascii"), user.pid)


class AuthenticationServer(authentication.AuthenticationServer):
	def __init__(self, settings):
		super().__init__()
		self.settings = settings
	
	async def login(self, client, username):
		# print("User trying to log in:", username)
		user = get_user_by_name(username)
		if not user:
			raise common.RMCError("RendezVous::InvalidUsername")
			
		server = get_user_by_name(utils.SECURE_SERVER)
		if not server:
			raise common.RMCError("Core::NotImplemented")
		
		url = common.StationURL(
			scheme="prudps", address=os.getenv("NEX_SERVER_IP"), port=os.getenv("NEX_SECURE_PORT"),
			PID=server.pid, CID=1, type=2,
			sid=1, stream=10
		)
		
		conn_data = authentication.RVConnectionData()
		conn_data.main_station = url
		conn_data.special_protocols = []
		conn_data.special_station = common.StationURL()
		conn_data.server_time = common.DateTime.fromtimestamp(datetime.datetime.utcnow().timestamp())
		
		response = rmc.RMCResponse()
		response.result = common.Result.success()
		response.pid = user.pid
		response.ticket = self.generate_ticket(user, server)
		response.connection_data = conn_data
		response.server_name = utils.NEX_SERVER_NAME
		return response
		
	def generate_ticket(self, source, target):
		settings = self.settings
		
		user_key = derive_key(source)
		server_key = derive_key(target)
		session_key = secrets.token_bytes(settings["kerberos.key_size"])
		
		internal = kerberos.ServerTicket()
		internal.timestamp = common.DateTime.now()
		internal.source = source.pid
		internal.session_key = session_key
		
		ticket = kerberos.ClientTicket()
		ticket.session_key = session_key
		ticket.target = target.pid
		ticket.internal = internal.encrypt(server_key, settings)
		
		return ticket.encrypt(user_key, settings)


async def main():
	s = settings.default()
	s.configure(utils.ACCESS_KEY, utils.NEX_VERSION)
	
	auth_servers = [
		AuthenticationServer(s)
	]
	secure_servers = [

	]
	
	server_key = derive_key(get_user_by_name(utils.SECURE_SERVER))
	async with rmc.serve(s, auth_servers, os.getenv("NEX_SERVER_IP"), os.getenv("NEX_AUTH_PORT")): # Start Authentication Server
		async with rmc.serve(s, secure_servers, os.getenv("NEX_SERVER_IP"), os.getenv("NEX_SECURE_PORT"), key=server_key): # Start Secure Server
			await aioconsole.ainput("Press ENTER to close..\n")