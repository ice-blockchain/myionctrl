#!/usr/bin/env python3
# -*- coding: utf_8 -*-l

import time

from mypylib.mypylib import MyPyClass
from myioncore import MyIonCore, Sleep


local = MyPyClass('./tests')
local.db["config"]["logLevel"] = "info"
load = 100
ion = MyIonCore(local)


def Init():
	wallets = list()
	local.buffer["wallets"] = wallets
	walletsNameList = ion.GetWalletsNameList()
	
	# Create tests wallet
	testsWalletName = "tests_hwallet"
	testsWallet = ion.CreateHighWallet(testsWalletName)

	# Check tests wallet balance
	account = ion.GetAccount(testsWallet.addr)
	local.AddLog("wallet: {addr}, status: {status}, balance: {balance}".format(addr=testsWallet.addr, status=account.status, balance=account.balance))
	if account.balance == 0:
		raise Exception(testsWallet.name + " wallet balance is empty.")
	if account.status == "uninit":
		ion.SendFile(testsWallet.bocFilePath, testsWallet)

	# Create wallets
	for i in range(load):
		walletName = "w_" + str(i)
		if walletName not in walletsNameList:
			wallet = ion.CreateWallet(walletName)
		else:
			wallet = ion.GetLocalWallet(walletName)
		wallets.append(wallet)
	#end for

	# Fill up wallets
	buff_wallet = None
	buff_seqno = None
	destList = list()
	for wallet in wallets:
		wallet.account = ion.GetAccount(wallet.addr)
		need = 20 - wallet.account.balance
		if need > 10:
			destList.append([wallet.addr_init, need])
		elif need < -10:
			need = need * -1
			buff_wallet = wallet
			buff_wallet.oldseqno = ion.GetSeqno(wallet)
			ion.MoveGrams(wallet, testsWallet.addr, need, wait=False)
			local.AddLog(testsWallet.name + " <<< " + wallet.name)
	if buff_wallet:
		ion.WaitTransaction(buff_wallet, False)
	#end for

	# Move grams from highload wallet
	ion.MoveGramsFromHW(testsWallet, destList)

	# Activate wallets
	for wallet in wallets:
		if wallet.account.status == "uninit":
			wallet.oldseqno = ion.GetSeqno(wallet)
			ion.SendFile(wallet.bocFilePath)
		local.AddLog(str(wallet.subwallet) + " - OK")
	ion.WaitTransaction(wallets[-1])
#end define

def Work():
	wallets = local.buffer["wallets"]
	for i in range(load):
		if i + 1 == load:
			i = -1
		#end if
		
		wallet1 = wallets[i]
		wallet2 = wallets[i+1]
		wallet1.oldseqno = ion.GetSeqno(wallet1)
		ion.MoveGrams(wallet1, wallet2.addr, 3.14, wait=False)
		local.AddLog(wallet1.name + " >>> " + wallet2.name)
	ion.WaitTransaction(wallets[-1])
#end define

def General():
	Init()
	while True:
		time.sleep(1)
		Work()
		local.AddLog("Work - OK")
	#end while
#end define



###
### Start test
###

local.Run()
load = 100
local.StartCycle(General, sec=1)
Sleep()
