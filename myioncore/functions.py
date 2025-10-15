#!/usr/bin/env python3
# -*- coding: utf_8 -*-l
import datetime
import os
import sys
import psutil
import time
import json
import base64
import requests
import subprocess

from mypylib import MyPyClass
from myioncore.myioncore import MyIonCore
from myionctrl.utils import fix_git_config
from myioninstaller.config import GetConfig
from mypylib.mypylib import (
    b2mb,
    get_timestamp,
    get_internet_interface_name,
    get_git_hash,
    get_load_avg,
    thr_sleep,
)
from myioncore.telemetry import *
from myioninstaller.node_args import get_node_args


def Init(local):
    # Event reaction
    if ("-e" in sys.argv):
        x = sys.argv.index("-e")
        event_name = sys.argv[x+1]
        Event(local, event_name)
    # end if

    local.run()

    # statistics
    local.buffer.blocksData = dict()
    local.buffer.transData = dict()
    local.buffer.network = [None]*15*6
    local.buffer.diskio = [None]*15*6

    # scan blocks
    local.buffer.masterBlocksList = list()
    local.buffer.prevShardsBlock = dict()
    local.buffer.blocksNum = 0
    local.buffer.transNum = 0
# end define


def Event(local, event_name):
    if event_name == "enableVC":
        EnableVcEvent(local)
    elif event_name == "validator down":
        ValidatorDownEvent(local)
    elif event_name.startswith("enable_mode"):
        enable_mode(local, event_name)
    elif event_name == "enable_btc_teleport":
        enable_btc_teleport(local)
    elif event_name.startswith("setup_collator"):
        setup_collator(local, event_name)
    local.exit()
# end define


def EnableVcEvent(local):
    local.add_log("start EnableVcEvent function", "debug")
    # Создать новый кошелек для валидатора
    ion = MyIonCore(local)
    wallet = ion.CreateWallet("validator_wallet_001", -1)
    local.db["validatorWalletName"] = wallet.name

    # Создать новый ADNL адрес для валидатора
    adnlAddr = ion.CreateNewKey()
    ion.AddAdnlAddrToValidator(adnlAddr)
    local.db["adnlAddr"] = adnlAddr

    # Сохранить
    local.save()
# end define


def ValidatorDownEvent(local):
    local.add_log("start ValidatorDownEvent function", "debug")
    local.add_log("Validator is down", "error")
# end define


def enable_mode(local, event_name: str):
    ion = MyIonCore(local)
    mode = event_name.split("_")[-1]
    if mode in ("liteserver", "collator"):
        ion.disable_mode('validator')
    ion.enable_mode(mode)
#end define

def enable_btc_teleport(local):
    local.add_log("start enable_btc_teleport function", "debug")
    ion = MyIonCore(local)
    if not ion.using_validator():
        local.add_log("Skip installing BTC Teleport as node is not a validator", "info")
        return
    from modules.btc_teleport import BtcTeleportModule
    BtcTeleportModule(ion, local).init(reinstall=True)


def setup_collator(local, event_name: str):
    local.add_log("start setup_collator function", "debug")
    ion = MyIonCore(local)
    from modules.collator import CollatorModule
    shards = event_name.split("_")[2:]
    CollatorModule(ion, local).setup_collator(shards)


def Elections(local, ion):
    use_pool = ion.using_pool()
    use_liquid_staking = ion.using_liquid_staking()
    if use_pool:
        ion.PoolsUpdateValidatorSet()
    if use_liquid_staking:
        ion.ControllersUpdateValidatorSet()
    ion.RecoverStake()
    if ion.using_validator():
        ion.ElectionEntry()


def Statistics(local):
    ReadNetworkData(local)
    SaveNetworkStatistics(local)
    # ReadTransData(local, scanner)
    SaveTransStatistics(local)
    ReadDiskData(local)
    SaveDiskStatistics(local)
# end define


def ReadDiskData(local):
    timestamp = get_timestamp()
    disks = GetDisksList()
    buff = psutil.disk_io_counters(perdisk=True)
    data = dict()
    for name in disks:
        data[name] = dict()
        data[name]["timestamp"] = timestamp
        data[name]["busyTime"] = buff[name].busy_time
        data[name]["readBytes"] = buff[name].read_bytes
        data[name]["writeBytes"] = buff[name].write_bytes
        data[name]["readCount"] = buff[name].read_count
        data[name]["writeCount"] = buff[name].write_count
    # end for

    local.buffer.diskio.pop(0)
    local.buffer.diskio.append(data)
# end define


def SaveDiskStatistics(local):
    data = local.buffer.diskio
    data = data[::-1]
    zerodata = data[0]
    buff1 = data[1*6-1]
    buff5 = data[5*6-1]
    buff15 = data[15*6-1]
    if buff5 is None:
        buff5 = buff1
    if buff15 is None:
        buff15 = buff5
    # end if

    disksLoadAvg = dict()
    disksLoadPercentAvg = dict()
    iopsAvg = dict()
    disks = GetDisksList()
    for name in disks:
        if zerodata[name]["busyTime"] == 0:
            continue
        diskLoad1, diskLoadPercent1, iops1 = CalculateDiskStatistics(
            zerodata, buff1, name)
        diskLoad5, diskLoadPercent5, iops5 = CalculateDiskStatistics(
            zerodata, buff5, name)
        diskLoad15, diskLoadPercent15, iops15 = CalculateDiskStatistics(
            zerodata, buff15, name)
        disksLoadAvg[name] = [diskLoad1, diskLoad5, diskLoad15]
        disksLoadPercentAvg[name] = [diskLoadPercent1,
                                     diskLoadPercent5, diskLoadPercent15]
        iopsAvg[name] = [iops1, iops5, iops15]
    # end fore

    # save statistics
    statistics = local.db.get("statistics", dict())
    statistics["disksLoadAvg"] = disksLoadAvg
    statistics["disksLoadPercentAvg"] = disksLoadPercentAvg
    statistics["iopsAvg"] = iopsAvg
    local.db["statistics"] = statistics
# end define


def CalculateDiskStatistics(zerodata, data, name):
    if data is None:
        return None, None, None
    data = data[name]
    zerodata = zerodata[name]
    timeDiff = zerodata["timestamp"] - data["timestamp"]
    busyTimeDiff = zerodata["busyTime"] - data["busyTime"]
    diskReadDiff = zerodata["readBytes"] - data["readBytes"]
    diskWriteDiff = zerodata["writeBytes"] - data["writeBytes"]
    diskReadCountDiff = zerodata["readCount"] - data["readCount"]
    diskWriteCountDiff = zerodata["writeCount"] - data["writeCount"]
    diskLoadPercent = busyTimeDiff / 1000 / timeDiff * \
        100  # /1000 - to second, *100 - to percent
    diskLoadPercent = round(diskLoadPercent, 2)
    diskRead = diskReadDiff / timeDiff
    diskWrite = diskWriteDiff / timeDiff
    diskReadCount = diskReadCountDiff / timeDiff
    diskWriteCount = diskWriteCountDiff / timeDiff
    diskLoad = b2mb(diskRead + diskWrite)
    iops = round(diskReadCount + diskWriteCount, 2)
    return diskLoad, diskLoadPercent, iops
# end define


def GetDisksList():
    data = list()
    buff = os.listdir("/sys/block/")
    for item in buff:
        if "loop" in item:
            continue
        data.append(item)
    # end for
    data.sort()
    return data
# end define


def ReadNetworkData(local):
    timestamp = get_timestamp()
    interfaceName = get_internet_interface_name()
    buff = psutil.net_io_counters(pernic=True)
    buff = buff[interfaceName]
    data = dict()
    data["timestamp"] = timestamp
    data["bytesRecv"] = buff.bytes_recv
    data["bytesSent"] = buff.bytes_sent
    data["packetsSent"] = buff.packets_sent
    data["packetsRecv"] = buff.packets_recv

    local.buffer.network.pop(0)
    local.buffer.network.append(data)
# end define


def SaveNetworkStatistics(local):
    data = local.buffer.network
    data = data[::-1]
    zerodata = data[0]
    buff1 = data[1*6-1]
    buff5 = data[5*6-1]
    buff15 = data[15*6-1]
    if buff5 is None:
        buff5 = buff1
    if buff15 is None:
        buff15 = buff5
    # end if

    netLoadAvg = dict()
    ppsAvg = dict()
    networkLoadAvg1, ppsAvg1 = CalculateNetworkStatistics(zerodata, buff1)
    networkLoadAvg5, ppsAvg5 = CalculateNetworkStatistics(zerodata, buff5)
    networkLoadAvg15, ppsAvg15 = CalculateNetworkStatistics(zerodata, buff15)
    netLoadAvg = [networkLoadAvg1, networkLoadAvg5, networkLoadAvg15]
    ppsAvg = [ppsAvg1, ppsAvg5, ppsAvg15]

    # save statistics
    statistics = local.db.get("statistics", dict())
    statistics["netLoadAvg"] = netLoadAvg
    statistics["ppsAvg"] = ppsAvg
    local.db["statistics"] = statistics
# end define


def CalculateNetworkStatistics(zerodata, data):
    if data is None:
        return None, None
    timeDiff = zerodata["timestamp"] - data["timestamp"]
    bytesRecvDiff = zerodata["bytesRecv"] - data["bytesRecv"]
    bytesSentDiff = zerodata["bytesSent"] - data["bytesSent"]
    packetsRecvDiff = zerodata["packetsRecv"] - data["packetsRecv"]
    packetsSentDiff = zerodata["packetsSent"] - data["packetsSent"]
    bitesRecvAvg = bytesRecvDiff / timeDiff * 8
    bitesSentAvg = bytesSentDiff / timeDiff * 8
    packetsRecvAvg = packetsRecvDiff / timeDiff
    packetsSentAvg = packetsSentDiff / timeDiff
    netLoadAvg = b2mb(bitesRecvAvg + bitesSentAvg)
    ppsAvg = round(packetsRecvAvg + packetsSentAvg, 2)
    return netLoadAvg, ppsAvg
# end define


def save_node_statistics(local, ion):
    status = ion.GetValidatorStatus(no_cache=True)
    if status.unixtime is None:
        return
    data = {'timestamp': status.unixtime}

    def get_ok_error(value: str):
        ok, error = value.split()
        return int(ok.split(':')[1]), int(error.split(':')[1])

    if 'total.collated_blocks.master' in status:
        master_ok, master_error = get_ok_error(status['total.collated_blocks.master'])
        shard_ok, shard_error = get_ok_error(status['total.collated_blocks.shard'])
        data['collated_blocks'] = {
            'master': {'ok': master_ok, 'error': master_error},
            'shard': {'ok': shard_ok, 'error': shard_error},
        }
    if 'total.validated_blocks.master' in status:
        master_ok, master_error = get_ok_error(status['total.validated_blocks.master'])
        shard_ok, shard_error = get_ok_error(status['total.validated_blocks.shard'])
        data['validated_blocks'] = {
            'master': {'ok': master_ok, 'error': master_error},
            'shard': {'ok': shard_ok, 'error': shard_error},
        }
    if 'total.ext_msg_check' in status:
        ok, error = get_ok_error(status['total.ext_msg_check'])
        data['ext_msg_check'] = {'ok': ok, 'error': error}
    if 'total.ls_queries_ok' in status and 'total.ls_queries_error' in status:
        data['ls_queries'] = {}
        for k in status['total.ls_queries_ok'].split():
            if k.startswith('TOTAL'):
                data['ls_queries']['ok'] = int(k.split(':')[1])
        for k in status['total.ls_queries_error'].split():
            if k.startswith('TOTAL'):
                data['ls_queries']['error'] = int(k.split(':')[1])
    statistics = local.db.get("statistics", dict())

    # if time.time() - int(status.start_time) <= 60:  # was node restart <60 sec ago, resetting node statistics
    #     statistics['node'] = []

    if 'node' not in statistics:
        statistics['node'] = []

    if statistics['node']:
        if int(status.start_time) > statistics['node'][-1]['timestamp']:
            # node was restarted, reset node statistics
            statistics['node'] = []

    # statistics['node']: [stats_from_election_id, stats_from_prev_min, stats_now]

    election_id = ion.GetConfig34(no_cache=True)['startWorkTime']
    if len(statistics['node']) == 0:
        statistics['node'] = [None, data]
    elif len(statistics['node']) < 3:
        statistics['node'].append(data)
    elif len(statistics['node']) == 3:
        if statistics['node'][0] is None:
            if 0 < data['timestamp'] - election_id < 90:
                statistics['node'][0] = data
        elif statistics['node'][0]['timestamp'] < election_id:
            statistics['node'][0] = data
        temp = statistics.get('node', []) + [data]
        temp.pop(1)
        statistics['node'] = temp
    local.db["statistics"] = statistics
    local.save()


def ReadTransData(local, scanner):
    transData = local.buffer.transData
    SetToTimeData(transData, scanner.transNum)
    ShortTimeData(transData)
# end define


def SetToTimeData(timeDataList, data):
    timenow = int(time.time())
    timeDataList[timenow] = data
# end define


def ShortTimeData(data, max=120, diff=20):
    if len(data) < max:
        return
    buff = data.copy()
    data.clear()
    keys = sorted(buff.keys(), reverse=True)
    for item in keys[:max-diff]:
        data[item] = buff[item]
# end define


def SaveTransStatistics(local):
    tps1 = GetTps(local, 60)
    tps5 = GetTps(local, 60*5)
    tps15 = GetTps(local, 60*15)

    # save statistics
    statistics = local.db.get("statistics", dict())
    statistics["tpsAvg"] = [tps1, tps5, tps15]
    local.db["statistics"] = statistics
# end define


def GetDataPerSecond(data, timediff):
    if len(data) == 0:
        return
    timenow = sorted(data.keys())[-1]
    now = data.get(timenow)
    prev = GetItemFromTimeData(data, timenow-timediff)
    if prev is None:
        return
    diff = now - prev
    result = diff / timediff
    result = round(result, 2)
    return result
# end define


def GetItemFromTimeData(data, timeneed):
    if timeneed in data:
        result = data.get(timeneed)
    else:
        result = data[min(data.keys(), key=lambda k: abs(k-timeneed))]
    return result
# end define


def GetTps(local, timediff):
    data = local.buffer.transData
    tps = GetDataPerSecond(data, timediff)
    return tps
# end define


def GetBps(local, timediff):
    data = local.buffer.blocksData
    bps = GetDataPerSecond(data, timediff)
    return bps
# end define


def GetBlockTimeAvg(local, timediff):
    bps = GetBps(local, timediff)
    if bps is None or bps == 0:
        return
    result = 1/bps
    result = round(result, 2)
    return result
# end define


def Offers(local, ion):
    save_offers = ion.GetSaveOffers()
    if save_offers:
        ion.offers_gc(save_offers)
    else:
        return
    offers = ion.GetOffers()
    for offer in offers:
        offer_hash = offer.get("hash")
        if offer_hash in save_offers:
            offer_pseudohash = offer.get("pseudohash")
            save_offer = save_offers.get(offer_hash)
            if isinstance(save_offer, list):  # new version of save offers {"hash": ["pseudohash", param_id]}
                save_offer_pseudohash = save_offer[0]
            else:  # old version of save offers {"hash": "pseudohash"}
                save_offer_pseudohash = save_offer
            if offer_pseudohash == save_offer_pseudohash and offer_pseudohash is not None:
                ion.VoteOffer(offer)
# end define

def Telemetry(local, ion):
    return
    sendTelemetry = local.db.get("sendTelemetry")
    if sendTelemetry is not True:
        return
    # end if

    # Get validator status
    data = dict()
    data["adnlAddr"] = ion.GetAdnlAddr()
    data["validatorStatus"] = ion.GetValidatorStatus()
    data["cpuNumber"] = psutil.cpu_count()
    data["cpuLoad"] = get_load_avg()
    data["netLoad"] = ion.GetStatistics("netLoadAvg")
    data["tps"] = ion.GetStatistics("tpsAvg")
    data["disksLoad"] = ion.GetStatistics("disksLoadAvg")
    data["disksLoadPercent"] = ion.GetStatistics("disksLoadPercentAvg")
    data["iops"] = ion.GetStatistics("iopsAvg")
    data["pps"] = ion.GetStatistics("ppsAvg")
    data["dbUsage"] = ion.GetDbUsage()
    data["memory"] = GetMemoryInfo()
    data["swap"] = GetSwapInfo()
    data["uname"] = GetUname()
    data["vprocess"] = GetValidatorProcessInfo()
    data["dbStats"] = local.try_function(get_db_stats)
    data["nodeArgs"] = local.try_function(get_node_args)
    data["modes"] = local.try_function(ion.get_modes)
    data["cpuInfo"] = {'cpuName': local.try_function(get_cpu_name), 'virtual': local.try_function(is_host_virtual)}
    data["validatorDiskName"] = local.try_function(get_validator_disk_name)
    data["pings"] = local.try_function(get_pings_values)

    # Get git hashes
    gitHashes = dict()
    mtc_path = "/usr/src/myionctrl"
    local.try_function(fix_git_config, args=[mtc_path])
    gitHashes["myionctrl"] = get_git_hash(mtc_path)
    gitHashes["validator"] = GetBinGitHash(
        "/usr/bin/ion/validator-engine/validator-engine")
    data["gitHashes"] = gitHashes
    data["stake"] = local.db.get("stake")

    # Get validator config
    vconfig = ion.GetValidatorConfig()
    data["fullnode_adnl"] = vconfig.fullnode

    # Send data to ioncenter server
    liteUrl_default = "https://telemetry.ice.io/report_status"
    liteUrl = local.db.get("telemetryLiteUrl", liteUrl_default)
    output = json.dumps(data)
    resp = requests.post(liteUrl, data=output, timeout=3)
# end define


def GetBinGitHash(path, short=False):
    if not os.path.isfile(path):
        return
    args = [path, "--version"]
    process = subprocess.run(args, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
    output = process.stdout.decode("utf-8")
    if "build information" not in output:
        return
    buff = output.split(' ')
    start = buff.index("Commit:") + 1
    result = buff[start].replace(',', '')
    if short is True:
        result = result[:7]
    return result
# end define


def OverlayTelemetry(local, ion):
    sendTelemetry = local.db.get("sendTelemetry")
    if sendTelemetry is not True:
        return
    # end if

    # Get validator status
    data = dict()
    data["adnlAddr"] = ion.GetAdnlAddr()
    data["overlaysStats"] = ion.GetOverlaysStats()

    # Send data to ioncenter server
    overlayUrl_default = "https://telemetry.ice.io/report_overlays"
    overlayUrl = local.db.get("overlayTelemetryUrl", overlayUrl_default)
    output = json.dumps(data)
    resp = requests.post(overlayUrl, data=output, timeout=3)
# end define


def Complaints(local, ion):
    validatorIndex = ion.GetValidatorIndex()
    if validatorIndex < 0:
        return
    # end if

    # Voting for complaints
    config32 = ion.GetConfig32()
    election_id = config32.get("startWorkTime")
    complaints = ion.GetComplaints(election_id)  # get complaints from Elector
    valid_complaints = ion.get_valid_complaints(complaints, election_id)
    for c in valid_complaints.values():
        complaint_hash = c.get("hash")
        ion.VoteComplaint(election_id, complaint_hash)
# end define


def Slashing(local, ion):
    is_slashing = local.db.get("isSlashing")
    is_validator = ion.using_validator()
    if is_slashing is not True or not is_validator:
        return

    # Creating complaints
    slash_time = local.buffer.slash_time
    config32 = ion.GetConfig32()
    start = config32.get("startWorkTime")
    end = config32.get("endWorkTime")
    config15 = ion.GetConfig15()
    ts = get_timestamp()
    if not(end < ts < end + config15['stakeHeldFor']):  # check that currently is freeze time
        return
    local.add_log("slash_time {}, start {}, end {}".format(slash_time, start, end), "debug")
    if slash_time != start:
        end -= 60
        ion.CheckValidators(start, end)
        local.buffer.slash_time = start
# end define


def save_past_events(local, ion):
    local.try_function(ion.GetElectionEntries)
    local.try_function(ion.GetComplaints)
    local.try_function(ion.GetValidatorsList, args=[True])  # cache past vl


def ScanLiteServers(local, ion):
    # Считать список серверов
    filePath = ion.liteClient.configPath
    file = open(filePath, 'rt')
    text = file.read()
    file.close()
    data = json.loads(text)

    # Пройтись по серверам
    result = list()
    liteservers = data.get("liteservers")
    for index in range(len(liteservers)):
        try:
            ion.liteClient.Run("last", index=index)
            result.append(index)
        except:
            pass
    # end for

    # Записать данные в базу
    local.db["liteServers"] = result
# end define


def check_initial_sync(local, ion):
    if not ion.in_initial_sync():
        return
    validator_status = ion.GetValidatorStatus()
    if validator_status.initial_sync:
        return
    if validator_status.out_of_sync < 20:
        ion.set_initial_sync_off()
        return


def gc_import(local, ion):
    if not ion.local.db.get('importGc', False):
        return
    local.add_log("GC import is running", "debug")
    import_path = '/var/ion-work/db/import'
    files = os.listdir(import_path)
    if not files:
        local.add_log("No files left to import", "debug")
        ion.local.db['importGc'] = False
        return
    try:
        status = ion.GetValidatorStatus()
        node_seqno = int(status.shardclientmasterchainseqno)
    except Exception as e:
        local.add_log(f"Failed to get shardclientmasterchainseqno: {e}", "warning")
        return
    removed = 0
    for file in files:
        file_seqno = int(file.split('.')[1])
        if node_seqno > file_seqno + 101:
            try:
                os.remove(os.path.join(import_path, file))
                removed += 1
            except PermissionError:
                local.add_log(f"Failed to remove file {file}: Permission denied", "error")
                continue
    local.add_log(f"Removed {removed} import files up to {node_seqno} seqno", "debug")


def backup_myioncore_logs(local: MyPyClass, ion: MyIonCore):
    logs_path = os.path.join(ion.tempDir, 'old_logs')
    os.makedirs(logs_path, exist_ok=True)
    for file in os.listdir(logs_path):
        file_path = os.path.join(logs_path, file)
        if time.time() - os.path.getmtime(file_path) < 3600:  # check that last file was created not less than an hour ago
            return
    now = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    log_backup_tmp_path = os.path.join(logs_path, 'myioncore_log_' + now + '.log')
    subprocess.run(["cp", local.buffer.log_file_name, log_backup_tmp_path])
    ion.clear_dir(logs_path)


def check_myioncore_db(local: MyPyClass, ion: MyIonCore):
    try:
        local.read_db(local.buffer.db_path)
        backup_path = local.buffer.db_path + ".backup"
        if not os.path.isfile(backup_path) or time.time() - os.path.getmtime(backup_path) > 3600*6:
            ion.create_self_db_backup()
        return
    except Exception as e:
        print(f'Failed to read myioncore db: {e}')
        local.add_log(f"Failed to read myioncore db: {e}", "error")
    ion.CheckConfigFile(None, None)  # get myioncore db from backup


def General(local):
    local.add_log("start General function", "debug")
    ion = MyIonCore(local)
    # scanner = Dict()
    # scanner.Run()

    # Start threads
    local.start_cycle(Statistics, sec=10, args=(local, ))
    local.start_cycle(Telemetry, sec=60, args=(local, ion, ))
    local.start_cycle(OverlayTelemetry, sec=7200, args=(local, ion, ))
    local.start_cycle(backup_myioncore_logs, sec=3600*4, args=(local, ion, ))
    local.start_cycle(check_myioncore_db, sec=600, args=(local, ion, ))

    if local.db.get("onlyNode"):  # myioncore service works only for telemetry
        thr_sleep()
        return

    local.start_cycle(Elections, sec=600, args=(local, ion, ))
    local.start_cycle(Offers, sec=600, args=(local, ion, ))
    local.start_cycle(save_past_events, sec=300, args=(local, ion, ))

    t = 600
    if ion.GetNetworkName() != 'mainnet':
        t = 60
    local.start_cycle(Complaints, sec=t, args=(local, ion, ))
    local.start_cycle(Slashing, sec=t, args=(local, ion, ))

    local.start_cycle(ScanLiteServers, sec=60, args=(local, ion,))

    local.start_cycle(save_node_statistics, sec=60, args=(local, ion, ))

    from modules.custom_overlays import CustomOverlayModule
    local.start_cycle(CustomOverlayModule(ion, local).custom_overlays, sec=60, args=())

    from modules.alert_bot import AlertBotModule
    local.start_cycle(AlertBotModule(ion, local).check_status, sec=60, args=())

    from modules.prometheus import PrometheusModule
    local.start_cycle(PrometheusModule(ion, local).push_metrics, sec=30, args=())

    from modules.btc_teleport import BtcTeleportModule
    local.start_cycle(BtcTeleportModule(ion, local).auto_vote_offers, sec=180, args=())

    if ion.in_initial_sync():
        local.start_cycle(check_initial_sync, sec=120, args=(local, ion))

    if ion.local.db.get('importGc'):
        local.start_cycle(gc_import, sec=300, args=(local, ion))

    thr_sleep()
# end define


def myioncore():
    from mypylib.mypylib import MyPyClass

    local = MyPyClass('myioncore.py')
    print('Local DB path:', local.buffer.db_path)
    Init(local)
    General(local)
