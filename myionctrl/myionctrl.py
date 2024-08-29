#!/usr/bin/env python3
# -*- coding: utf_8 -*-
import base64
import subprocess
import json
import psutil
import inspect
import pkg_resources
import socket

from functools import partial

from mypylib.mypylib import (
	int2ip,
	get_git_author_and_repo,
	get_git_branch,
	get_git_hash,
	check_git_update,
	get_service_status,
	get_service_uptime,
	get_load_avg,
	run_as_root,
	time2human,
	timeago,
	timestamp2datetime,
	get_timestamp,
	print_table,
	color_print,
	color_text,
	bcolors,
	Dict,
	MyPyClass
)

from mypyconsole.mypyconsole import MyPyConsole
from myioncore.myioncore import MyTonCore
from myioncore.functions import (
	Slashing,
	GetMemoryInfo,
	GetSwapInfo,
	GetBinGitHash,
)
from myioncore.telemetry import is_host_virtual
from myionctrl.migrate import run_migrations
from myionctrl.utils import GetItemFromList, timestamp2utcdatetime, fix_git_config

import sys, getopt, os


def Init(local, ion, console, argv):
	# Load translate table
	translate_path = pkg_resources.resource_filename('myionctrl', 'resources/translate.json')
	local.init_translator(translate_path)

	# this function substitutes local and ton instances if function has this args
	def inject_globals(func):
		args = []
		for arg_name in inspect.getfullargspec(func)[0]:
			if arg_name == 'local':
				args.append(local)
			elif arg_name == 'ion':
				args.append(ion)
		return partial(func, *args)

	# Create user console
	console.name = "MyIonCtrl"
	console.startFunction = inject_globals(PreUp)
	console.debug = ion.GetSettings("debug")

	console.AddItem("update", inject_globals(Update), local.translate("update_cmd"))
	console.AddItem("upgrade", inject_globals(Upgrade), local.translate("upgrade_cmd"))
	console.AddItem("installer", inject_globals(Installer), local.translate("installer_cmd"))
	console.AddItem("status", inject_globals(PrintStatus), local.translate("status_cmd"))
	console.AddItem("status_modes", inject_globals(mode_status), local.translate("status_modes_cmd"))
	console.AddItem("status_settings", inject_globals(settings_status), local.translate("settings_status_cmd"))
	console.AddItem("enable_mode", inject_globals(enable_mode), local.translate("enable_mode_cmd"))
	console.AddItem("disable_mode", inject_globals(disable_mode), local.translate("disable_mode_cmd"))
	console.AddItem("about", inject_globals(about), local.translate("about_cmd"))
	console.AddItem("get", inject_globals(GetSettings), local.translate("get_cmd"))
	console.AddItem("set", inject_globals(SetSettings), local.translate("set_cmd"))
	console.AddItem("rollback", inject_globals(rollback_to_mtc1), local.translate("rollback_cmd"))

	console.AddItem("seqno", inject_globals(Seqno), local.translate("seqno_cmd"))
	console.AddItem("getconfig", inject_globals(GetConfig), local.translate("getconfig_cmd"))
	console.AddItem("get_pool_data", inject_globals(GetPoolData), local.translate("get_pool_data_cmd"))

	console.AddItem("nw", inject_globals(CreatNewWallet), local.translate("nw_cmd"))
	console.AddItem("aw", inject_globals(ActivateWallet), local.translate("aw_cmd"))
	console.AddItem("wl", inject_globals(PrintWalletsList), local.translate("wl_cmd"))
	console.AddItem("iw", inject_globals(ImportWallet), local.translate("iw_cmd"))
	console.AddItem("swv", inject_globals(SetWalletVersion), local.translate("swv_cmd"))
	console.AddItem("ew", inject_globals(ExportWallet), local.translate("ex_cmd"))
	console.AddItem("dw", inject_globals(DeleteWallet), local.translate("dw_cmd"))

	console.AddItem("vas", inject_globals(ViewAccountStatus), local.translate("vas_cmd"))
	console.AddItem("vah", inject_globals(ViewAccountHistory), local.translate("vah_cmd"))
	console.AddItem("mg", inject_globals(MoveCoins), local.translate("mg_cmd"))
	console.AddItem("mgtp", inject_globals(MoveCoinsThroughProxy), local.translate("mgtp_cmd"))

	console.AddItem("nb", inject_globals(CreatNewBookmark), local.translate("nb_cmd"))
	console.AddItem("bl", inject_globals(PrintBookmarksList), local.translate("bl_cmd"))
	console.AddItem("db", inject_globals(DeleteBookmark), local.translate("db_cmd"))

	# console.AddItem("nr", inject_globals(CreatNewAutoTransferRule), local.translate("nr_cmd")) # "Добавить правило автопереводов в расписание / Create new auto transfer rule"
	# console.AddItem("rl", inject_globals(PrintAutoTransferRulesList), local.translate("rl_cmd")) # "Показать правила автопереводов / Show auto transfer rule list"
	# console.AddItem("dr", inject_globals(DeleteAutoTransferRule), local.translate("dr_cmd")) # "Удалить правило автопереводов из расписания / Delete auto transfer rule"

	# console.AddItem("nd", inject_globals(NewDomain), local.translate("nd_cmd"))
	# console.AddItem("dl", inject_globals(PrintDomainsList), local.translate("dl_cmd"))
	# console.AddItem("vds", inject_globals(ViewDomainStatus), local.translate("vds_cmd"))
	# console.AddItem("dd", inject_globals(DeleteDomain), local.translate("dd_cmd"))
	# console.AddItem("gdfa", inject_globals(GetDomainFromAuction), local.translate("gdfa_cmd"))

	console.AddItem("ol", inject_globals(PrintOffersList), local.translate("ol_cmd"))
	console.AddItem("od", inject_globals(OfferDiff), local.translate("od_cmd"))

	console.AddItem("el", inject_globals(PrintElectionEntriesList), local.translate("el_cmd"))
	console.AddItem("vl", inject_globals(PrintValidatorList), local.translate("vl_cmd"))
	console.AddItem("cl", inject_globals(PrintComplaintsList), local.translate("cl_cmd"))

	#console.AddItem("xrestart", inject_globals(Xrestart), local.translate("xrestart_cmd"))
	#console.AddItem("xlist", inject_globals(Xlist), local.translate("xlist_cmd"))
	#console.AddItem("gpk", inject_globals(GetPubKey), local.translate("gpk_cmd"))
	#console.AddItem("ssoc", inject_globals(SignShardOverlayCert), local.translate("ssoc_cmd"))
	#console.AddItem("isoc", inject_globals(ImportShardOverlayCert), local.translate("isoc_cmd"))

	from modules.custom_overlays import CustomOverlayModule
	module = CustomOverlayModule(ion, local)
	module.add_console_commands(console)

	from modules.collator_config import CollatorConfigModule
	module = CollatorConfigModule(ion, local)
	module.add_console_commands(console)

	if ion.using_validator():
		from modules.validator import ValidatorModule
		module = ValidatorModule(ion, local)
		module.add_console_commands(console)

		if ion.using_pool():  # add basic pool functions (pools_list, delete_pool, import_pool)
			from modules.pool import PoolModule
			module = PoolModule(ion, local)
			module.add_console_commands(console)

		if ion.using_nominator_pool():
			from modules.nominator_pool import NominatorPoolModule
			module = NominatorPoolModule(ion, local)
			module.add_console_commands(console)

		if ion.using_single_nominator():
			from modules.single_pool import SingleNominatorModule
			module = SingleNominatorModule(ion, local)
			module.add_console_commands(console)

		if ion.using_liquid_staking():
			from modules.controller import ControllerModule
			module = ControllerModule(ion, local)
			module.add_console_commands(console)

	console.AddItem("cleanup", inject_globals(cleanup_validator_db), local.translate("cleanup_cmd"))
	console.AddItem("benchmark", inject_globals(run_benchmark), local.translate("benchmark_cmd"))
	console.AddItem("activate_ion_storage_provider", inject_globals(activate_ion_storage_provider), local.translate("activate_ion_storage_provider_cmd"))

	# Process input parameters
	opts, args = getopt.getopt(argv,"hc:w:",["config=","wallets="])
	for opt, arg in opts:
		if opt == '-h':
			print ('myionctrl.py -c <configfile> -w <wallets>')
			sys.exit()
		elif opt in ("-c", "--config"):
			configfile = arg
			if not os.access(configfile, os.R_OK):
				print ("Configuration file " + configfile + " could not be opened")
				sys.exit()

			ion.dbFile = configfile
			ion.Refresh()
		elif opt in ("-w", "--wallets"):
			wallets = arg
			if not os.access(wallets, os.R_OK):
				print ("Wallets path " + wallets  + " could not be opened")
				sys.exit()
			elif not os.path.isdir(wallets):
				print ("Wallets path " + wallets  + " is not a directory")
				sys.exit()
			ion.walletsDir = wallets
	#end for

	local.db.config.logLevel = "debug" if console.debug else "info"
	local.db.config.isLocaldbSaving = False
	local.run()
#end define


def activate_ion_storage_provider(local, ion, args):
	wallet_name = "provider_wallet_001"
	wallet = ion.GetLocalWallet(wallet_name)
	account = ion.GetAccount(wallet.addrB64)
	if account.status == "active":
		color_print("activate_ion_storage_provider - {green}Already activated{endc}")
		#return
	ion.ActivateWallet(wallet)
	destination = "0:7777777777777777777777777777777777777777777777777777777777777777"
	ion_storage = ion.GetSettings("ion_storage")
	comment = f"tsp-{ion_storage.provider.pubkey}"
	flags = ["-n", "-C", comment]
	ion.MoveCoins(wallet, destination, 0.01, flags=flags)
	color_print("activate_ion_storage_provider - {green}OK{endc}")
#end define


def about(local, ion, args):
	from modules import get_mode, get_mode_settings
	if len(args) != 1:
		color_print("{red}Bad args. Usage:{endc} about <mode_name>")
	mode_name = args[0]
	mode = get_mode(mode_name)
	if mode is None:
		color_print(f"{{red}}Mode {mode_name} not found{{endc}}")
		return
	mode_settings = get_mode_settings(mode_name)
	color_print(f'''{{cyan}}===[ {mode_name} MODE ]==={{endc}}''')
	color_print(f'''Description: {mode.description}''')
	color_print('Enabled: ' + color_text('{green}yes{endc}' if ion.get_mode_value(mode_name) else '{red}no{endc}'))
	print('Settings:', 'no' if len(mode_settings) == 0 else '')
	for setting_name, setting in mode_settings.items():
		color_print(f'  {{bold}}{setting_name}{{endc}}: {setting.description}.\n    Default value: {setting.default_value}')
#end define


def check_installer_user(local):
	args = ["whoami"]
	process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
	username = process.stdout.decode("utf-8").strip()

	args = ["ls", "-lh", "/var/ion-work/keys/"]
	process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
	output = process.stdout.decode("utf-8")
	actual_user = output.split('\n')[1].split()[2]

	if username != actual_user:
		local.add_log(f'myionctrl was installed by another user. Probably you need to launch mtc with `{actual_user}` user.', 'error')
#end define


def PreUp(local: MyPyClass, ion: MyTonCore):
	CheckMyionctrlUpdate(local)
	check_installer_user(local)
	check_vport(local, ion)
	ion.check_adnl()
	warnings(local, ion)
	# CheckTonUpdate()
#end define


def Installer(args):
	# args = ["python3", "/usr/src/mytonctrl/mytoninstaller.py"]
	cmd = ["python3", "-m", "myioninstaller"]
	if args:
		cmd += ["-c", *args]
	subprocess.run(cmd)
#end define


def GetAuthorRepoBranchFromArgs(args):
	data = dict()
	arg1 = GetItemFromList(args, 0)
	arg2 = GetItemFromList(args, 1)
	if arg1:
		if "https://" in arg1:
			buff = arg1[8:].split('/')
			print(f"buff: {buff}")
			data["author"] = buff[1]
			data["repo"] = buff[2]
			tree = GetItemFromList(buff, 3)
			if tree:
				data["branch"] = GetItemFromList(buff, 4)
		else:
			data["branch"] = arg1
	if arg2:
		data["branch"] = arg2
	return data
#end define


def check_vport(local, ion):
	try:
		vconfig = ion.GetValidatorConfig()
	except:
		local.add_log("GetValidatorConfig error", "error")
		return
	addr = vconfig.addrs.pop()
	ip = int2ip(addr.ip)
	with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
		result = client_socket.connect_ex((ip, addr.port))
	if result != 0:
		color_print(local.translate("vport_error"))
#end define


def check_git(input_args, default_repo, text, default_branch='master'):
	src_dir = "/usr/src"
	git_path = f"{src_dir}/{default_repo}"
	fix_git_config(git_path)
	default_author = "ice-blockchain"

	# Get author, repo, branch
	local_author, local_repo = get_git_author_and_repo(git_path)
	local_branch = get_git_branch(git_path)

	# Set author, repo, branch
	data = GetAuthorRepoBranchFromArgs(input_args)
	need_author = data.get("author")
	need_repo = data.get("repo")
	need_branch = data.get("branch")

	# Check if remote repo is different from default
	if ((need_author is None and local_author != default_author) or 
		(need_repo is None and local_repo != default_repo)):
		remote_url = f"https://github.com/{local_author}/{local_repo}/tree/{need_branch if need_branch else local_branch}"
		raise Exception(f"{text} error: You are on {remote_url} remote url, to update to the tip use `{text} {remote_url}` command")
	elif need_branch is None and local_branch != default_branch:
		raise Exception(f"{text} error: You are on {local_branch} branch, to update to the tip of {local_branch} branch use `{text} {local_branch}` command")
	#end if

	if need_author is None:
		need_author = local_author
	if need_repo is None:
		need_repo = local_repo
	if need_branch is None:
		need_branch = local_branch
	check_branch_exists(need_author, need_repo, need_branch)
	return need_author, need_repo, need_branch
#end define

def check_branch_exists(author, repo, branch):
	url = f"https://github.com/{author}/{repo}.git"
	args = ["git", "ls-remote", "--heads", url, branch]
	process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
	output = process.stdout.decode("utf-8")
	if branch not in output:
		raise Exception(f"Branch {branch} not found in {url}")
#end define

def Update(local, args):
	repo = "myionctrl"
	author, repo, branch = check_git(args, repo, "update")

	# Run script
	update_script_path = pkg_resources.resource_filename('myionctrl', 'scripts/update.sh')
	runArgs = ["bash", update_script_path, "-a", author, "-r", repo, "-b", branch]
	exitCode = run_as_root(runArgs)
	if exitCode == 0:
		text = "Update - {green}OK{endc}"
	else:
		text = "Update - {red}Error{endc}"
	color_print(text)
	local.exit()
#end define

def Upgrade(ion, args):
	repo = "ion"
	author, repo, branch = check_git(args, repo, "upgrade")

	# bugfix if the files are in the wrong place
	liteClient = ion.GetSettings("liteClient")
	configPath = liteClient.get("configPath")
	pubkeyPath = liteClient.get("liteServer").get("pubkeyPath")
	if "ion-lite-client-test1" in configPath:
		liteClient["configPath"] = configPath.replace("lite-client/ion-lite-client-test1.config.json", "global.config.json")
	if "/usr/bin/ion" in pubkeyPath:
		liteClient["liteServer"]["pubkeyPath"] = "/var/ion-work/keys/liteserver.pub"
	ion.SetSettings("liteClient", liteClient)
	validatorConsole = ion.GetSettings("validatorConsole")
	privKeyPath = validatorConsole.get("privKeyPath")
	pubKeyPath = validatorConsole.get("pubKeyPath")
	if "/usr/bin/ion" in privKeyPath:
		validatorConsole["privKeyPath"] = "/var/ion-work/keys/client"
	if "/usr/bin/ion" in pubKeyPath:
		validatorConsole["pubKeyPath"] = "/var/ion-work/keys/server.pub"
	ion.SetSettings("validatorConsole", validatorConsole)

	# Run script
	upgrade_script_path = pkg_resources.resource_filename('myionctrl', 'scripts/upgrade.sh')
	runArgs = ["bash", upgrade_script_path, "-a", author, "-r", repo, "-b", branch]
	exitCode = run_as_root(runArgs)
	if ion.using_validator():
		try:
			from myioninstaller.myioninstaller import set_node_argument, get_node_args
			node_args = get_node_args()
			if node_args.get('--state-ttl') == '604800':
				set_node_argument(ion.local, ["--state-ttl", "-d"])
		except Exception as e:
			color_print(f"{{red}}Failed to set node argument: {e} {{endc}}")
	if exitCode == 0:
		text = "Upgrade - {green}OK{endc}"
	else:
		text = "Upgrade - {red}Error{endc}"
	color_print(text)
#end define

def rollback_to_mtc1(local, ion,  args):
	color_print("{red}Warning: this is dangerous, please make sure you've backed up myioncore's db.{endc}")
	a = input("Do you want to continue? [Y/n]\n")
	if a.lower() != 'y':
		print('aborted.')
		return
	ion.rollback_modes()

	workdir = local.buffer.my_work_dir
	version_file_path = os.path.join(workdir, 'VERSION')
	if os.path.exists(version_file_path):
		os.remove(version_file_path)

	rollback_script_path = pkg_resources.resource_filename('myionctrl', 'migrations/roll_back_001.sh')
	run_args = ["bash", rollback_script_path]
	run_as_root(run_args)
	local.exit()
#end define

def cleanup_validator_db(ion, args):
	cleanup_script_path = pkg_resources.resource_filename('myionctrl', 'scripts/cleanup.sh')
	run_args = ["bash", cleanup_script_path]
	exit_code = run_as_root(run_args)
#end define

def run_benchmark(ion, args):
	timeout = 200
	benchmark_script_path = pkg_resources.resource_filename('myionctrl', 'scripts/benchmark.sh')
	etabar_script_path = pkg_resources.resource_filename('myionctrl', 'scripts/etabar.py')
	benchmark_result_path = "/tmp/benchmark_result.json"
	run_args = ["python3", etabar_script_path, str(timeout), benchmark_script_path, benchmark_result_path]
	exit_code = run_as_root(run_args)
	with open(benchmark_result_path, 'rt') as file:
		text = file.read()
	if exit_code != 0:
		color_print("Benchmark - {red}Error:{endc} " + text)
		return
	#end if

	data = Dict(json.loads(text))
	table = list()
	table += [["Test type", "Read speed", "Write speed", "Read iops", "Write iops", "Random ops"]]
	table += [["Fio lite", data.lite.read_speed, data.lite.write_speed, data.lite.read_iops, data.lite.write_iops, None]] # RND-4K-QD64
	table += [["Fio hard", data.hard.read_speed, data.hard.write_speed, data.hard.read_iops, data.hard.write_iops, None]] # RND-4K-QD1
	table += [["RocksDB", None, None, None, None, data.full.random_ops]]
	print_table(table)
#end define

def CheckMyionctrlUpdate(local):
	git_path = local.buffer.my_dir
	result = check_git_update(git_path)
	if result is True:
		color_print(local.translate("myionctrl_update_available"))
#end define

def print_warning(local, warning_name: str):
	color_print("============================================================================================")
	color_print(local.translate(warning_name))
	color_print("============================================================================================")
#end define

def check_disk_usage(local, ion):
	usage = ion.GetDbUsage()
	if usage > 90:
		print_warning(local, "disk_usage_warning")
#end define

def check_sync(local, ion):
	validator_status = ion.GetValidatorStatus()
	if not validator_status.is_working or validator_status.out_of_sync >= 20:
		print_warning(local, "sync_warning")
#end define

def check_validator_balance(local, ion):
	validator_status = ion.GetValidatorStatus()
	if not validator_status.is_working or validator_status.out_of_sync >= 20:
		# Do not check the validator wallet balance if the node is not synchronized (via public lite-servers)
		return
	if ion.using_validator():
		validator_wallet = ion.GetValidatorWallet()
		validator_account = local.try_function(ion.GetAccount, args=[validator_wallet.addrB64])
		if validator_account is None:
			local.add_log(f"Failed to check validator wallet balance", "warning")
			return
		if validator_account.balance < 100:
			print_warning(local, "validator_balance_warning")
#end define

def check_vps(local, ion):
	if ion.using_validator():
		data = local.try_function(is_host_virtual)
		if data and data["virtual"]:
			color_print(f"Virtualization detected: {data['product_name']}")
#end define

def warnings(local, ion):
	check_disk_usage(local, ion)
	check_sync(local, ion)
	check_validator_balance(local, ion)
	check_vps(local, ion)
#end define

def CheckTonUpdate(local):
	git_path = "/usr/src/ion"
	result = check_git_update(git_path)
	if result is True:
		color_print(local.translate("ion_update_available"))
#end define

def PrintTest(local, args):
	print(json.dumps(local.buffer, indent=2))
#end define

def sl(ion, args):
	Slashing(ion.local, ion)
#end define


def mode_status(ion, args):
	from modules import get_mode
	modes = ion.get_modes()
	table = [["Name", "Status", "Description"]]
	for mode_name in modes:
		mode = get_mode(mode_name)
		status = color_text('{green}enabled{endc}' if modes[mode_name] else '{red}disabled{endc}')
		table.append([mode_name, status, mode.description])
	print_table(table)
#end define


def settings_status(ion, args):
	from modules import SETTINGS
	table = [["Name", "Description", "Mode", "Default value", "Current value"]]
	for name, setting in SETTINGS.items():
		current_value = ion.local.db.get(name)
		table.append([name, setting.description, setting.mode, setting.default_value, current_value])
	print_table(table)
#end define


def PrintStatus(local, ion, args):
	opt = None
	if len(args) == 1:
		opt = args[0]

	# Local status
	validator_status = ion.GetValidatorStatus()
	adnl_addr = ion.GetAdnlAddr()
	validator_index = None
	onlineValidators = None
	validator_efficiency = None
	validator_wallet = ion.GetValidatorWallet()
	validator_account = Dict()
	db_size = ion.GetDbSize()
	db_usage = ion.GetDbUsage()
	memory_info = GetMemoryInfo()
	swap_info = GetSwapInfo()
	statistics = ion.GetSettings("statistics")
	net_load_avg = ion.GetStatistics("netLoadAvg", statistics)
	disks_load_avg = ion.GetStatistics("disksLoadAvg", statistics)
	disks_load_percent_avg = ion.GetStatistics("disksLoadPercentAvg", statistics)

	all_status = validator_status.is_working == True and validator_status.out_of_sync < 20

	try:
		vconfig = ion.GetValidatorConfig()
		fullnode_adnl = base64.b64decode(vconfig.fullnode).hex().upper()
	except:
		fullnode_adnl = 'n/a'

	if all_status:
		network_name = ion.GetNetworkName()
		rootWorkchainEnabledTime_int = ion.GetRootWorkchainEnabledTime()
		config34 = ion.GetConfig34()
		config36 = ion.GetConfig36()
		totalValidators = config34["totalValidators"]
		
		if opt != "fast":
			onlineValidators = ion.GetOnlineValidators()
			validator_efficiency = ion.GetValidatorEfficiency()
		if onlineValidators:
			onlineValidators = len(onlineValidators)

		oldStartWorkTime = config36.get("startWorkTime")
		if oldStartWorkTime is None:
			oldStartWorkTime = config34.get("startWorkTime")
		shardsNumber = ion.GetShardsNumber()
		
		config15 = ion.GetConfig15()
		config17 = ion.GetConfig17()
		fullConfigAddr = ion.GetFullConfigAddr()
		fullElectorAddr = ion.GetFullElectorAddr()
		startWorkTime = ion.GetActiveElectionId(fullElectorAddr)
		validator_index = ion.GetValidatorIndex()
		
		offersNumber = ion.GetOffersNumber()
		complaintsNumber = ion.GetComplaintsNumber()
		
		tpsAvg = ion.GetStatistics("tpsAvg", statistics)
		
		if validator_wallet is not None:
			validator_account = ion.GetAccount(validator_wallet.addrB64)
	#end if

	if all_status:
		PrintTonStatus(local, network_name, startWorkTime, totalValidators, onlineValidators, shardsNumber, offersNumber, complaintsNumber, tpsAvg)
	PrintLocalStatus(local, adnl_addr, validator_index, validator_efficiency, validator_wallet, validator_account, validator_status, 
		db_size, db_usage, memory_info, swap_info, net_load_avg, disks_load_avg, disks_load_percent_avg, fullnode_adnl)
	if all_status:
		PrintTonConfig(local, fullConfigAddr, fullElectorAddr, config15, config17)
		PrintTimes(local, rootWorkchainEnabledTime_int, startWorkTime, oldStartWorkTime, config15)
#end define

def PrintTonStatus(local, network_name, startWorkTime, totalValidators, onlineValidators, shardsNumber, offersNumber, complaintsNumber, tpsAvg):
	#tps1 = tpsAvg[0]
	#tps5 = tpsAvg[1]
	#tps15 = tpsAvg[2]
	allValidators = totalValidators
	newOffers = offersNumber.get("new")
	allOffers = offersNumber.get("all")
	newComplaints = complaintsNumber.get("new")
	allComplaints = complaintsNumber.get("all")
	#tps1_text = bcolors.green_text(tps1)
	#tps5_text = bcolors.green_text(tps5)
	#tps15_text = bcolors.green_text(tps15)

	color_network_name = bcolors.green_text(network_name) if network_name == "mainnet" else bcolors.yellow_text(network_name)
	network_name_text = local.translate("ion_status_network_name").format(color_network_name)
	#tps_text = local.translate("ton_status_tps").format(tps1_text, tps5_text, tps15_text)
	onlineValidators_text = GetColorInt(onlineValidators, border=allValidators*2/3, logic="more")
	allValidators_text = bcolors.yellow_text(allValidators)
	validators_text = local.translate("ion_status_validators").format(onlineValidators_text, allValidators_text)
	shards_text = local.translate("ion_status_shards").format(bcolors.green_text(shardsNumber))
	newOffers_text = bcolors.green_text(newOffers)
	allOffers_text = bcolors.yellow_text(allOffers)
	offers_text = local.translate("ion_status_offers").format(newOffers_text, allOffers_text)
	newComplaints_text = bcolors.green_text(newComplaints)
	allComplaints_text = bcolors.yellow_text(allComplaints)
	complaints_text = local.translate("ion_status_complaints").format(newComplaints_text, allComplaints_text)

	if startWorkTime == 0:
		election_text = bcolors.yellow_text("closed")
	else:
		election_text = bcolors.green_text("open")
	election_text = local.translate("ion_status_election").format(election_text)

	color_print(local.translate("ion_status_head"))
	print(network_name_text)
	#print(tps_text)
	print(validators_text)
	print(shards_text)
	print(offers_text)
	print(complaints_text)
	print(election_text)
	print()
#end define

def PrintLocalStatus(local, adnlAddr, validatorIndex, validatorEfficiency, validatorWallet, validatorAccount, validator_status, dbSize, dbUsage, memoryInfo, swapInfo, netLoadAvg, disksLoadAvg, disksLoadPercentAvg, fullnode_adnl):
	if validatorWallet is None:
		return
	walletAddr = validatorWallet.addrB64
	walletBalance = validatorAccount.balance
	cpuNumber = psutil.cpu_count()
	loadavg = get_load_avg()
	cpuLoad1 = loadavg[0]
	cpuLoad5 = loadavg[1]
	cpuLoad15 = loadavg[2]
	netLoad1 = netLoadAvg[0]
	netLoad5 = netLoadAvg[1]
	netLoad15 = netLoadAvg[2]

	validatorIndex_text = GetColorInt(validatorIndex, 0, logic="more")
	validatorIndex_text = local.translate("local_status_validator_index").format(validatorIndex_text)
	validatorEfficiency_text = GetColorInt(validatorEfficiency, 10, logic="more", ending=" %")
	validatorEfficiency_text = local.translate("local_status_validator_efficiency").format(validatorEfficiency_text)
	adnlAddr_text = local.translate("local_status_adnl_addr").format(bcolors.yellow_text(adnlAddr))
	fullnode_adnl_text = local.translate("local_status_fullnode_adnl").format(bcolors.yellow_text(fullnode_adnl))
	walletAddr_text = local.translate("local_status_wallet_addr").format(bcolors.yellow_text(walletAddr))
	walletBalance_text = local.translate("local_status_wallet_balance").format(bcolors.green_text(walletBalance))

	# CPU status
	cpuNumber_text = bcolors.yellow_text(cpuNumber)
	cpuLoad1_text = GetColorInt(cpuLoad1, cpuNumber, logic="less")
	cpuLoad5_text = GetColorInt(cpuLoad5, cpuNumber, logic="less")
	cpuLoad15_text = GetColorInt(cpuLoad15, cpuNumber, logic="less")
	cpuLoad_text = local.translate("local_status_cpu_load").format(cpuNumber_text, cpuLoad1_text, cpuLoad5_text, cpuLoad15_text)

	# Memory status
	ramUsage = memoryInfo.get("usage")
	ramUsagePercent = memoryInfo.get("usagePercent")
	swapUsage = swapInfo.get("usage")
	swapUsagePercent = swapInfo.get("usagePercent")
	ramUsage_text = GetColorInt(ramUsage, 100, logic="less", ending=" Gb")
	ramUsagePercent_text = GetColorInt(ramUsagePercent, 90, logic="less", ending="%")
	swapUsage_text = GetColorInt(swapUsage, 100, logic="less", ending=" Gb")
	swapUsagePercent_text = GetColorInt(swapUsagePercent, 90, logic="less", ending="%")
	ramLoad_text = "{cyan}ram:[{default}{data}, {percent}{cyan}]{endc}"
	ramLoad_text = ramLoad_text.format(cyan=bcolors.cyan, default=bcolors.default, endc=bcolors.endc, data=ramUsage_text, percent=ramUsagePercent_text)
	swapLoad_text = "{cyan}swap:[{default}{data}, {percent}{cyan}]{endc}"
	swapLoad_text = swapLoad_text.format(cyan=bcolors.cyan, default=bcolors.default, endc=bcolors.endc, data=swapUsage_text, percent=swapUsagePercent_text)
	memoryLoad_text = local.translate("local_status_memory").format(ramLoad_text, swapLoad_text)

	# Network status
	netLoad1_text = GetColorInt(netLoad1, 300, logic="less")
	netLoad5_text = GetColorInt(netLoad5, 300, logic="less")
	netLoad15_text = GetColorInt(netLoad15, 300, logic="less")
	netLoad_text = local.translate("local_status_net_load").format(netLoad1_text, netLoad5_text, netLoad15_text)

	# Disks status
	disksLoad_data = list()
	for key, item in disksLoadAvg.items():
		diskLoad1_text = bcolors.green_text(item[0])  # TODO: this variables is unused. Why?
		diskLoad5_text = bcolors.green_text(item[1])  # TODO: this variables is unused. Why?
		diskLoad15_text = bcolors.green_text(item[2])
		diskLoadPercent1_text = GetColorInt(disksLoadPercentAvg[key][0], 80, logic="less", ending="%")  # TODO: this variables is unused. Why?
		diskLoadPercent5_text = GetColorInt(disksLoadPercentAvg[key][1], 80, logic="less", ending="%")  # TODO: this variables is unused. Why?
		diskLoadPercent15_text = GetColorInt(disksLoadPercentAvg[key][2], 80, logic="less", ending="%")
		buff = "{}, {}"
		buff = "{}{}:[{}{}{}]{}".format(bcolors.cyan, key, bcolors.default, buff, bcolors.cyan, bcolors.endc)
		disksLoad_buff = buff.format(diskLoad15_text, diskLoadPercent15_text)
		disksLoad_data.append(disksLoad_buff)
	disksLoad_data = ", ".join(disksLoad_data)
	disksLoad_text = local.translate("local_status_disks_load").format(disksLoad_data)

	# Thread status
	myioncoreStatus_bool = get_service_status("myioncore")
	validatorStatus_bool = get_service_status("validator")
	myioncoreUptime = get_service_uptime("myioncore")
	validatorUptime = get_service_uptime("validator")
	myioncoreUptime_text = bcolors.green_text(time2human(myioncoreUptime))
	validatorUptime_text = bcolors.green_text(time2human(validatorUptime))
	myioncoreStatus_color = GetColorStatus(myioncoreStatus_bool)
	validatorStatus_color = GetColorStatus(validatorStatus_bool)
	myioncoreStatus_text = local.translate("local_status_myioncore_status").format(myioncoreStatus_color, myioncoreUptime_text)
	validatorStatus_text = local.translate("local_status_validator_status").format(validatorStatus_color, validatorUptime_text)
	validator_out_of_sync_text = local.translate("local_status_validator_out_of_sync").format(GetColorInt(validator_status.out_of_sync, 20, logic="less", ending=" s"))

	validator_out_of_ser_text = local.translate("local_status_validator_out_of_ser").format(f'{validator_status.out_of_ser} blocks ago')

	dbSize_text = GetColorInt(dbSize, 1000, logic="less", ending=" Gb")
	dbUsage_text = GetColorInt(dbUsage, 80, logic="less", ending="%")
	dbStatus_text = local.translate("local_status_db").format(dbSize_text, dbUsage_text)
	
	# Mytonctrl and validator git hash
	mtcGitPath = "/usr/src/myionctrl"
	validatorGitPath = "/usr/src/ion"
	validatorBinGitPath = "/usr/bin/ion/validator-engine/validator-engine"
	mtcGitHash = get_git_hash(mtcGitPath, short=True)
	validatorGitHash = GetBinGitHash(validatorBinGitPath, short=True)
	fix_git_config(mtcGitPath)
	fix_git_config(validatorGitPath)
	mtcGitBranch = get_git_branch(mtcGitPath)
	validatorGitBranch = get_git_branch(validatorGitPath)
	mtcGitHash_text = bcolors.yellow_text(mtcGitHash)
	validatorGitHash_text = bcolors.yellow_text(validatorGitHash)
	mtcGitBranch_text = bcolors.yellow_text(mtcGitBranch)
	validatorGitBranch_text = bcolors.yellow_text(validatorGitBranch)
	mtcVersion_text = local.translate("local_status_version_mtc").format(mtcGitHash_text, mtcGitBranch_text)
	validatorVersion_text = local.translate("local_status_version_validator").format(validatorGitHash_text, validatorGitBranch_text)

	color_print(local.translate("local_status_head"))
	print(validatorIndex_text)
	print(validator_status.result_stats)
	print(validatorEfficiency_text)
	print(adnlAddr_text)
	print(fullnode_adnl_text)
	print(walletAddr_text)
	print(walletBalance_text)
	print(cpuLoad_text)
	print(netLoad_text)
	print(memoryLoad_text)
	
	print(disksLoad_text)
	print(myioncoreStatus_text)
	print(validatorStatus_text)
	print(validator_out_of_sync_text)
	print(validator_out_of_ser_text)
	print(dbStatus_text)
	print(mtcVersion_text)
	print(validatorVersion_text)
	print()
#end define

def GetColorInt(data, border, logic, ending=None):
	if data is None:
		result = "n/a"
	elif logic == "more":
		if data >= border:
			result = bcolors.green_text(data, ending)
		else:
			result = bcolors.red_text(data, ending)
	elif logic == "less":
		if data <= border:
			result = bcolors.green_text(data, ending)
		else:
			result = bcolors.red_text(data, ending)
	return result
#end define

def GetColorStatus(input):
	if input == True:
		result = bcolors.green_text("working")
	else:
		result = bcolors.red_text("not working")
	return result
#end define

def PrintTonConfig(local, fullConfigAddr, fullElectorAddr, config15, config17):
	validatorsElectedFor = config15["validatorsElectedFor"]
	electionsStartBefore = config15["electionsStartBefore"]
	electionsEndBefore = config15["electionsEndBefore"]
	stakeHeldFor = config15["stakeHeldFor"]
	minStake = config17["minStake"]
	maxStake = config17["maxStake"]

	fullConfigAddr_text = local.translate("ion_config_configurator_addr").format(bcolors.yellow_text(fullConfigAddr))
	fullElectorAddr_text = local.translate("ion_config_elector_addr").format(bcolors.yellow_text(fullElectorAddr))
	validatorsElectedFor_text = bcolors.yellow_text(validatorsElectedFor)
	electionsStartBefore_text = bcolors.yellow_text(electionsStartBefore)
	electionsEndBefore_text = bcolors.yellow_text(electionsEndBefore)
	stakeHeldFor_text = bcolors.yellow_text(stakeHeldFor)
	elections_text = local.translate("ion_config_elections").format(validatorsElectedFor_text, electionsStartBefore_text, electionsEndBefore_text, stakeHeldFor_text)
	minStake_text = bcolors.yellow_text(minStake)
	maxStake_text = bcolors.yellow_text(maxStake)
	stake_text = local.translate("ion_config_stake").format(minStake_text, maxStake_text)

	color_print(local.translate("ion_config_head"))
	print(fullConfigAddr_text)
	print(fullElectorAddr_text)
	print(elections_text)
	print(stake_text)
	print()
#end define

def PrintTimes(local, rootWorkchainEnabledTime_int, startWorkTime, oldStartWorkTime, config15):
	validatorsElectedFor = config15["validatorsElectedFor"]
	electionsStartBefore = config15["electionsStartBefore"]
	electionsEndBefore = config15["electionsEndBefore"]

	if startWorkTime == 0:
		startWorkTime = oldStartWorkTime
	#end if

	# Calculate time
	startValidation = startWorkTime
	endValidation = startWorkTime + validatorsElectedFor
	startElection = startWorkTime - electionsStartBefore
	endElection = startWorkTime - electionsEndBefore
	startNextElection = startElection + validatorsElectedFor

	# timestamp to datetime
	rootWorkchainEnabledTime = timestamp2utcdatetime(rootWorkchainEnabledTime_int)
	startValidationTime = timestamp2utcdatetime(startValidation)
	endValidationTime = timestamp2utcdatetime(endValidation)
	startElectionTime = timestamp2utcdatetime(startElection)
	endElectionTime = timestamp2utcdatetime(endElection)
	startNextElectionTime = timestamp2utcdatetime(startNextElection)

	# datetime to color text
	rootWorkchainEnabledTime_text = local.translate("times_root_workchain_enabled_time").format(bcolors.yellow_text(rootWorkchainEnabledTime))
	startValidationTime_text = local.translate("times_start_validation_time").format(GetColorTime(startValidationTime, startValidation))
	endValidationTime_text = local.translate("times_end_validation_time").format(GetColorTime(endValidationTime, endValidation))
	startElectionTime_text = local.translate("times_start_election_time").format(GetColorTime(startElectionTime, startElection))
	endElectionTime_text = local.translate("times_end_election_time").format(GetColorTime(endElectionTime, endElection))
	startNextElectionTime_text = local.translate("times_start_next_election_time").format(GetColorTime(startNextElectionTime, startNextElection))

	color_print(local.translate("times_head"))
	print(rootWorkchainEnabledTime_text)
	print(startValidationTime_text)
	print(endValidationTime_text)
	print(startElectionTime_text)
	print(endElectionTime_text)
	print(startNextElectionTime_text)
#end define

def GetColorTime(datetime, timestamp):
	newTimestamp = get_timestamp()
	if timestamp > newTimestamp:
		result = bcolors.green_text(datetime)
	else:
		result = bcolors.yellow_text(datetime)
	return result
#end define

def Seqno(ion, args):
	try:
		walletName = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} seqno <wallet-name>")
		return
	wallet = ion.GetLocalWallet(walletName)
	seqno = ion.GetSeqno(wallet)
	print(walletName, "seqno:", seqno)
#end define

def CreatNewWallet(ion, args):
	version = "v1"
	try:
		if len(args) == 0:
			walletName = ion.GenerateWalletName()
			workchain = 0
		else:
			workchain = int(args[0])
			walletName = args[1]
		if len(args) > 2:
			version = args[2]
		if len(args) == 4:
			subwallet = int(args[3])
		else:
			subwallet = 698983191 + workchain # 0x29A9A317 + workchain
	except:
		color_print("{red}Bad args. Usage:{endc} nw <workchain-id> <wallet-name> [<version> <subwallet>]")
		return
	wallet = ion.CreateWallet(walletName, workchain, version, subwallet=subwallet)
	table = list()
	table += [["Name", "Workchain", "Address"]]
	table += [[wallet.name, wallet.workchain, wallet.addrB64_init]]
	print_table(table)
#end define

def ActivateWallet(local, ion, args):
	try:
		walletName = args[0]
	except Exception as err:
		walletName = "all"
	if walletName == "all":
		ion.WalletsCheck()
	else:
		wallet = ion.GetLocalWallet(walletName)
		ion.ActivateWallet(wallet)
	color_print("ActivateWallet - {green}OK{endc}")
#end define

def PrintWalletsList(ion, args):
	table = list()
	table += [["Name", "Status", "Balance", "Ver", "Wch", "Address"]]
	data = ion.GetWallets()
	if (data is None or len(data) == 0):
		print("No data")
		return
	for wallet in data:
		account = ion.GetAccount(wallet.addrB64)
		if account.status != "active":
			wallet.addrB64 = wallet.addrB64_init
		table += [[wallet.name, account.status, account.balance, wallet.version, wallet.workchain, wallet.addrB64]]
	print_table(table)
#end define

def ImportWallet(ion, args):
	try:
		addr = args[0]
		key = args[1]
	except:
		color_print("{red}Bad args. Usage:{endc} iw <wallet-addr> <wallet-secret-key>")
		return
	name = ion.ImportWallet(addr, key)
	print("Wallet name:", name)
#end define

def SetWalletVersion(ion, args):
	try:
		addr = args[0]
		version = args[1]
	except:
		color_print("{red}Bad args. Usage:{endc} swv <wallet-addr> <wallet-version>")
		return
	ion.SetWalletVersion(addr, version)
	color_print("SetWalletVersion - {green}OK{endc}")
#end define

def ExportWallet(ion, args):
	try:
		name = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} ew <wallet-name>")
		return
	addr, key = ion.ExportWallet(name)
	print("Wallet name:", name)
	print("Address:", addr)
	print("Secret key:", key)
#end define

def DeleteWallet(ion, args):
	try:
		walletName = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} dw <wallet-name>")
		return
	if input("Are you sure you want to delete this wallet (yes/no): ") != "yes":
		print("Cancel wallet deletion")
		return
	wallet = ion.GetLocalWallet(walletName)
	wallet.Delete()
	color_print("DeleteWallet - {green}OK{endc}")
#end define

def ViewAccountStatus(ion, args):
	try:
		addrB64 = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} vas <account-addr>")
		return
	addrB64 = ion.GetDestinationAddr(addrB64)
	account = ion.GetAccount(addrB64)
	version = ion.GetVersionFromCodeHash(account.codeHash)
	statusTable = list()
	statusTable += [["Address", "Status", "Balance", "Version"]]
	statusTable += [[addrB64, account.status, account.balance, version]]
	codeHashTable = list()
	codeHashTable += [["Code hash"]]
	codeHashTable += [[account.codeHash]]
	historyTable = GetHistoryTable(ion, addrB64, 10)
	print_table(statusTable)
	print()
	print_table(codeHashTable)
	print()
	print_table(historyTable)
#end define

def ViewAccountHistory(ion, args):
	try:
		addr = args[0]
		limit = int(args[1])
	except:
		color_print("{red}Bad args. Usage:{endc} vah <account-addr> <limit>")
		return
	table = GetHistoryTable(ion, addr, limit)
	print_table(table)
#end define

def GetHistoryTable(ion, addr, limit):
	addr = ion.GetDestinationAddr(addr)
	account = ion.GetAccount(addr)
	history = ion.GetAccountHistory(account, limit)
	table = list()
	typeText = color_text("{red}{bold}{endc}")
	table += [["Time", typeText, "Coins", "From/To"]]
	for message in history:
		if message.srcAddr is None:
			continue
		srcAddrFull = f"{message.srcWorkchain}:{message.srcAddr}"
		destAddFull = f"{message.destWorkchain}:{message.destAddr}"
		if srcAddrFull == account.addrFull:
			type = color_text("{red}{bold}>>>{endc}")
			fromto = destAddFull
		else:
			type = color_text("{blue}{bold}<<<{endc}")
			fromto = srcAddrFull
		fromto = ion.AddrFull2AddrB64(fromto)
		#datetime = timestamp2datetime(message.time, "%Y.%m.%d %H:%M:%S")
		datetime = timeago(message.time)
		table += [[datetime, type, message.value, fromto]]
	return table
#end define

def MoveCoins(ion, args):
	try:
		walletName = args[0]
		destination = args[1]
		amount = args[2]
		flags = args[3:]
	except:
		color_print("{red}Bad args. Usage:{endc} mg <wallet-name> <account-addr | bookmark-name> <amount>")
		return
	wallet = ion.GetLocalWallet(walletName)
	destination = ion.GetDestinationAddr(destination)
	ion.MoveCoins(wallet, destination, amount, flags=flags)
	color_print("MoveCoins - {green}OK{endc}")
#end define

def MoveCoinsThroughProxy(ion, args):
	try:
		walletName = args[0]
		destination = args[1]
		amount = args[2]
	except:
		color_print("{red}Bad args. Usage:{endc} mgtp <wallet-name> <account-addr | bookmark-name> <amount>")
		return
	wallet = ion.GetLocalWallet(walletName)
	destination = ion.GetDestinationAddr(destination)
	ion.MoveCoinsThroughProxy(wallet, destination, amount)
	color_print("MoveCoinsThroughProxy - {green}OK{endc}")
#end define

def CreatNewBookmark(ion, args):
	try:
		name = args[0]
		addr = args[1]
	except:
		color_print("{red}Bad args. Usage:{endc} nb <bookmark-name> <account-addr | domain-name>")
		return
	if ion.IsAddr(addr):
		type = "account"
	else:
		type = "domain"
	#end if

	bookmark = dict()
	bookmark["name"] = name
	bookmark["type"] = type
	bookmark["addr"] = addr
	ion.AddBookmark(bookmark)
	color_print("CreatNewBookmark - {green}OK{endc}")
#end define

def PrintBookmarksList(ion, args):
	data = ion.GetBookmarks()
	if (data is None or len(data) == 0):
		print("No data")
		return
	table = list()
	table += [["Name", "Type", "Address / Domain", "Balance / Exp. date"]]
	for item in data:
		name = item.get("name")
		type = item.get("type")
		addr = item.get("addr")
		bookmark_data = item.get("data")
		table += [[name, type, addr, bookmark_data]]
	print_table(table)
#end define

def DeleteBookmark(ion, args):
	try:
		name = args[0]
		type = args[1]
	except:
		color_print("{red}Bad args. Usage:{endc} db <bookmark-name> <bookmark-type>")
		return
	ion.DeleteBookmark(name, type)
	color_print("DeleteBookmark - {green}OK{endc}")
#end define

# def CreatNewAutoTransferRule(args):
# 	try:
# 		name = args[0]
# 		addr = args[1]
# 	except:
# 		color_print("{red}Bad args. Usage:{endc} nr <rule-name> <account-addr | domain-name>")
# 		return
# 	rule = dict()
# 	rule["name"] = name
# 	rule["addr"] = addr
# 	ton.AddAutoTransferRule(rule)
# 	color_print("CreatNewAutoTransferRule - {green}OK{endc}")
# #end define

# def PrintAutoTransferRulesList(args):
# 	data = ton.GetRules()
# 	if (data is None or len(data) == 0):
# 		print("No data")
# 		return
# 	table = list()
# 	table += [["Name", "fix me"]]
# 	for item in data:
# 		table += [[item.get("name"), item.get("fix me")]]
# 	print_table(table)
# #end define

# def DeleteAutoTransferRule(args):
# 	print("fix me")
# #end define

def PrintOffersList(ion, args):
	data = ion.GetOffers()
	if (data is None or len(data) == 0):
 		print("No data")
 		return
	if "--json" in args:
		text = json.dumps(data, indent=2)
		print(text)
	else:
		table = list()
		table += [["Hash", "Config", "Votes", "W/L", "Approved", "Is passed"]]
		for item in data:
			hash = item.get("hash")
			votedValidators = len(item.get("votedValidators"))
			wins = item.get("wins")
			losses = item.get("losses")
			wl = "{0}/{1}".format(wins, losses)
			approvedPercent = item.get("approvedPercent")
			approvedPercent_text = "{0}%".format(approvedPercent)
			isPassed = item.get("isPassed")
			if "hash" not in args:
				hash = Reduct(hash)
			if isPassed == True:
				isPassed = bcolors.green_text("true")
			if isPassed == False:
				isPassed = bcolors.red_text("false")
			table += [[hash, item.config.id, votedValidators, wl, approvedPercent_text, isPassed]]
		print_table(table)
#end define

def OfferDiff(ion, args):
	try:
		offerHash = args[0]
		offerHash = offerHash
	except:
		color_print("{red}Bad args. Usage:{endc} od <offer-hash>")
		return
	ion.GetOfferDiff(offerHash)
#end define

def GetConfig(ion, args):
	try:
		configId = args[0]
		configId = int(configId)
	except:
		color_print("{red}Bad args. Usage:{endc} gc <config-id>")
		return
	data = ion.GetConfig(configId)
	text = json.dumps(data, indent=2)
	print(text)
#end define

def PrintComplaintsList(ion, args):
	past = "past" in args
	data = ion.GetComplaints(past=past)
	if (data is None or len(data) == 0):
		print("No data")
		return
	if "--json" in args:
		text = json.dumps(data, indent=2)
		print(text)
	else:
		table = list()
		table += [["Election id", "ADNL", "Fine (part)", "Votes", "Approved", "Is passed"]]
		for key, item in data.items():
			electionId = item.get("electionId")
			adnl = item.get("adnl")
			suggestedFine = item.get("suggestedFine")
			suggestedFinePart = item.get("suggestedFinePart")
			Fine_text = "{0} ({1})".format(suggestedFine, suggestedFinePart)
			votedValidators = len(item.get("votedValidators"))
			approvedPercent = item.get("approvedPercent")
			approvedPercent_text = "{0}%".format(approvedPercent)
			isPassed = item.get("isPassed")
			if "adnl" not in args:
				adnl = Reduct(adnl)
			if isPassed == True:
				isPassed = bcolors.green_text("true")
			if isPassed == False:
				isPassed = bcolors.red_text("false")
			table += [[electionId, adnl, Fine_text, votedValidators, approvedPercent_text, isPassed]]
		print_table(table)
#end define

def NewDomain(ion, args):
	try:
		domainName = args[0]
		walletName = args[1]
		adnlAddr = args[2]
	except:
		color_print("{red}Bad args. Usage:{endc} nd <domain-name> <wallet-name> <site-adnl-addr>")
		return
	domain = dict()
	domain["name"] = domainName
	domain["adnlAddr"] = adnlAddr
	domain["walletName"] = walletName
	ion.NewDomain(domain)
	color_print("NewDomain - {green}OK{endc}")
#end define

def PrintDomainsList(ion, args):
	data = ion.GetDomains()
	if (data is None or len(data) == 0):
		print("No data")
		return
	table = list()
	table += [["Domain", "Wallet", "Expiration date", "ADNL address"]]
	for item in data:
		domainName = item.get("name")
		walletName = item.get("walletName")
		endTime = item.get("endTime")
		endTime = timestamp2datetime(endTime, "%d.%m.%Y")
		adnlAddr = item.get("adnlAddr")
		table += [[domainName, walletName, endTime, adnlAddr]]
	print_table(table)
#end define

def ViewDomainStatus(ion, args):
	try:
		domainName = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} vds <domain-name>")
		return
	domain = ion.GetDomain(domainName)
	endTime = domain.get("endTime")
	endTime = timestamp2datetime(endTime, "%d.%m.%Y")
	adnlAddr = domain.get("adnlAddr")
	table = list()
	table += [["Domain", "Expiration date", "ADNL address"]]
	table += [[domainName, endTime, adnlAddr]]
	print_table(table)
#end define

def DeleteDomain(ion, args):
	try:
		domainName = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} dd <domain-name>")
		return
	ion.DeleteDomain(domainName)
	color_print("DeleteDomain - {green}OK{endc}")
#end define

def GetDomainFromAuction(ion, args):
	try:
		walletName = args[0]
		addr = args[1]
	except:
		color_print("{red}Bad args. Usage:{endc} gdfa <wallet-name> <addr>")
		return
	ion.GetDomainFromAuction(walletName, addr)
	color_print("GetDomainFromAuction - {green}OK{endc}")
#end define

def PrintElectionEntriesList(ion, args):
	past = "past" in args
	data = ion.GetElectionEntries(past=past)
	if (data is None or len(data) == 0):
		print("No data")
		return
	if "--json" in args:
		text = json.dumps(data, indent=2)
		print(text)
	else:
		table = list()
		table += [["ADNL", "Pubkey", "Wallet", "Stake", "Max-factor"]]
		for key, item in data.items():
			adnl = item.get("adnlAddr")
			pubkey = item.get("pubkey")
			walletAddr = item.get("walletAddr")
			stake = item.get("stake")
			maxFactor = item.get("maxFactor")
			if "adnl" not in args:
				adnl = Reduct(adnl)
			if "pubkey" not in args:
				pubkey = Reduct(pubkey)
			if "wallet" not in args:
				walletAddr = Reduct(walletAddr)
			table += [[adnl, pubkey, walletAddr, stake, maxFactor]]
		print_table(table)
#end define

def PrintValidatorList(ion, args):
	past = "past" in args
	data = ion.GetValidatorsList(past=past)
	if (data is None or len(data) == 0):
		print("No data")
		return
	if "--json" in args:
		text = json.dumps(data, indent=2)
		print(text)
	else:
		table = list()
		table += [["ADNL", "Pubkey", "Wallet", "Efficiency", "Online"]]
		for item in data:
			adnl = item.get("adnlAddr")
			pubkey = item.get("pubkey")
			walletAddr = item.get("walletAddr")
			efficiency = item.get("efficiency")
			online = item.get("online")
			if "adnl" not in args:
				adnl = Reduct(adnl)
			if "pubkey" not in args:
				pubkey = Reduct(pubkey)
			if "wallet" not in args:
				walletAddr = Reduct(walletAddr)
			if "offline" in args and online != False:
				continue
			if online == True:
				online = bcolors.green_text("true")
			if online == False:
				online = bcolors.red_text("false")
			table += [[adnl, pubkey, walletAddr, efficiency, online]]
		print_table(table)
#end define

def Reduct(item):
	item = str(item)
	if item is None:
		result = None
	else:
		end = len(item)
		result = item[0:6] + "..." + item[end-6:end]
	return result
#end define

def GetSettings(ion, args):
	try:
		name = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} get <settings-name>")
		return
	result = ion.GetSettings(name)
	print(json.dumps(result, indent=2))
#end define

def SetSettings(ion, args):
	try:
		name = args[0]
		value = args[1]
	except:
		color_print("{red}Bad args. Usage:{endc} set <settings-name> <settings-value>")
		return
	if name == 'usePool' or name == 'useController':
		mode_name = 'nominator-pool' if name == 'usePool' else 'liquid-staking'
		color_print(f"{{red}} Error: set {name} ... is deprecated and does not work {{endc}}."
					f"\nInstead, use {{bold}}enable_mode {mode_name}{{endc}}")
		return
	force = False
	if len(args) > 2:
		if args[2] == "--force":
			force = True
	from modules import get_setting
	setting = get_setting(name)
	if setting is None and not force:
		color_print(f"{{red}} Error: setting {name} not found.{{endc}} Use flag --force to set it anyway")
		return
	if setting is not None and setting.mode is not None:
		if not ion.get_mode_value(setting.mode) and not force:
			color_print(f"{{red}} Error: mode {setting.mode} is disabled.{{endc}} Use flag --force to set it anyway")
			return
	ion.SetSettings(name, value)
	color_print("SetSettings - {green}OK{endc}")
#end define


def enable_mode(local, ion, args):
	try:
		name = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} enable_mode <mode_name>")
		return
	ion.enable_mode(name)
	color_print("enable_mode - {green}OK{endc}")
	local.exit()
#end define

def disable_mode(local, ion, args):
	try:
		name = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} disable_mode <mode_name>")
		return
	ion.disable_mode(name)
	color_print("disable_mode - {green}OK{endc}")
	local.exit()
#end define

def Xrestart(inputArgs):
	if len(inputArgs) < 2:
		color_print("{red}Bad args. Usage:{endc} xrestart <timestamp> <args>")
		return
	xrestart_script_path = pkg_resources.resource_filename('myionctrl', 'scripts/xrestart.py')
	args = ["python3", xrestart_script_path]  # TODO: Fix path
	args += inputArgs
	exitCode = run_as_root(args)
	if exitCode == 0:
		text = "Xrestart - {green}OK{endc}"
	else:
		text = "Xrestart - {red}Error{endc}"
	color_print(text)
#end define

def Xlist(args):
	color_print("Xlist - {green}OK{endc}")
#end define

def GetPubKey(ion, args):
	adnlAddr = ion.GetAdnlAddr()
	pubkey = ion.GetPubKey(adnlAddr)
	print("pubkey:", pubkey)
#end define

def SignShardOverlayCert(ion, args):
	try:
		adnl = args[0]
		pubkey = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} ssoc <pubkey>")
		return
	ion.SignShardOverlayCert(adnl, pubkey)
#end define

def ImportShardOverlayCert(ion, args):
	ion.ImportShardOverlayCert()
#end define

def GetPoolData(ion, args):
	try:
		pool_name = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} get_pool_data <pool-name | pool-addr>")
		return
	if ion.IsAddr(pool_name):
		pool_addr = pool_name
	else:
		pool = ion.GetLocalPool(pool_name)
		pool_addr = pool.addrB64
	pool_data = ion.GetPoolData(pool_addr)
	print(json.dumps(pool_data, indent=4))
#end define


### Start of the program
def myionctrl():
	local = MyPyClass('myionctrl.py')
	myioncore_local = MyPyClass('myioncore.py')
	ion = MyTonCore(myioncore_local)
	console = MyPyConsole()

	# migrations
	restart = run_migrations(local, ion)

	if not restart:
		Init(local, ion, console, sys.argv[1:])
		console.Run()
#end define
