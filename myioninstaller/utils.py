import base64
import json
import time
import subprocess
import typing

from nacl.signing import SigningKey


def GetInitBlock():
	from mypylib.mypylib import MyPyClass
	from myioncore import MyIonCore

	myioncore_local = MyPyClass('myioncore.py')
	ion = MyIonCore(myioncore_local)
	initBlock = ion.GetInitBlock()
	return initBlock
#end define

def start_service(local, service_name:str, sleep:int=1):
	local.add_log(f"Start/restart {service_name} service", "debug")
	args = ["systemctl", "restart", service_name]
	subprocess.run(args)

	local.add_log(f"sleep {sleep} sec", "debug")
	time.sleep(sleep)
#end define

def stop_service(local, service_name:str):
	local.add_log(f"Stop {service_name} service", "debug")
	args = ["systemctl", "stop", service_name]
	subprocess.run(args)
#end define

def disable_service(local, service_name: str):
	local.add_log(f"Disable {service_name} service", "debug")
	args = ["systemctl", "disable", service_name]
	subprocess.run(args)

def StartValidator(local):
	start_service(local, "validator", sleep=10)
#end define

def StartMyioncore(local):
	start_service(local, "myioncore")
#end define

def get_ed25519_pubkey_text(privkey_text):
	privkey = base64.b64decode(privkey_text)
	pubkey = get_ed25519_pubkey(privkey)
	pubkey_text = base64.b64encode(pubkey).decode("utf-8")
	return pubkey_text
#end define

def get_ed25519_pubkey(privkey):
	privkey_obj = SigningKey(privkey)
	pubkey = privkey_obj.verify_key.encode()
	return pubkey
#end define


def is_testnet(local):
	testnet_zero_state_root_hash = "VGlUpujWvSdCpW1mfycI1vSyBIZ4nmFSIZRkAm2UdFs="
	with open(local.buffer.global_config_path) as f:
		config = json.load(f)
	if config['validator']['zero_state']['root_hash'] == testnet_zero_state_root_hash:
		return True
	return False


def get_ion_storage_port(local) -> typing.Optional[int]:
	p = subprocess.run(["systemctl", "cat", "ion_storage.service"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
					   timeout=3)
	if p.returncode != 0:
		local.add_log("Failed to get ion_storage.service", "error")
		return None
	p.output = p.stdout.decode("utf-8")
	for line in p.output.splitlines():
		if line.startswith('ExecStart'):
			cmd = line.split()
			if '-api' not in cmd:
				local.add_log("Failed to find -api in ion_storage.service exec command", "error")
				return None
			return int(cmd[cmd.index('-api') + 1].split(':')[1])
	local.add_log("Failed to find ExecStart in ion_storage.service", "error")
	return None
