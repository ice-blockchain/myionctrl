![GitHub stars](https://img.shields.io/github/stars/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub forks](https://img.shields.io/github/forks/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub issues](https://img.shields.io/github/issues/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub pull requests](https://img.shields.io/github/issues-pr/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub last commit](https://img.shields.io/github/last-commit/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub license](https://img.shields.io/github/license/ice-blockchain/myionctrl?style=flat-square&logo=github)

<!-- omit from toc -->
# MyIonCtrl

<!-- omit from toc --> 
## Contents

- [What is MyIonCtrl?](#what-is-mytionctrl)
- [MyIonCtrl Documentation](#myionctrl-documentation)
- [Functionality](#functionality)
	- [List of tested operating systems](#list-of-tested-operating-systems)
- [Installation](#installation)
	- [Installation scripts overview](#installation-scripts-overview)
	- [Installation modes](#installation-modes)
	- [Installation for Ubuntu](#installation-for-ubuntu)
	- [Installation for Debian](#installation-for-debian)
- [Telemetry](#telemetry)
- [MyIonCtrl installer mode](#myionctrl-installer-mode)
	- [Web admin panel](#web-admin-panel)
	- [Local copy of ioncenter](#local-copy-of-ioncenter)
- [Useful links](#useful-links)


# What is MyIonCtrl?
MyIonCtrl is a console application that serves as a convenient wrapper for `fift`, `lite-client`, and `validator-engine-console`. It has been specifically developed for node (validator) management tasks on the Linux operating system.

![MyIonCtrl Status](screens/myionctrl-status.png)

# MyIonCtrl Documentation

Myionctrl's documentation can be found at https://docs.ice.io/participate/run-nodes/myionctrl.

# Functionality
- [x] Show ION network status
- [x] Management of local wallets
	- [x] Create local wallet
	- [x] Activate local wallet
	- [x] Show local wallets
	- [x] Import wallet from file (.pk)
	- [x] Save wallet address to file (.addr)
	- [x] Delete local wallet
- [x] Show account status
	- [x] Show account balance
	- [x] Show account history
	- [x] Show account status from bookmarks
- [x] Transferring funds to the wallet
	- [x] Transfer of a fixed amount
	- [x] Transfer of the entire amount (all)
	- [x] Transfer of the entire amount with wallet deactivation (alld)
	- [x] Transferring funds to the wallet from bookmarks
	- [x] Transferring funds to a wallet through a chain of self-deleting wallets
- [x] Manage bookmarks
	- [x] Add account to bookmarks
	- [x] Show bookmarks
	- [x] Delete bookmark
- [x] Offer management
	- [x] Show offers
	- [x] Vote for the proposal
	- [x] Automatic voting for previously voted proposals
- [x] Controlling the validator
	- [x] Participate in the election of a validator
	- [x] Return bet + reward
	- [x] Autostart validator on abnormal termination (systemd)
	- [x] Send validator statistics to https://ice.io

## List of tested operating systems
| Operating System              | Status                     |
|-------------------------------|----------------------------|
| Ubuntu 16.04 LTS (Xenial Xerus) | Error: ION compilation error |
| Ubuntu 18.04 LTS (Bionic Beaver) | OK                       |
| Ubuntu 20.04 LTS (Focal Fossa) | OK                       |
| Ubuntu 22.04 LTS (Jammy Jellyfish) | OK                   |
| Debian 8 | Error: Unable to locate package libgsl-dev   |
| Debian 9 | Error: ION compilation error                 |
| Debian 10 | OK                                         |

# Installation
## Installation scripts overview
- `ioninstaller.sh`: clones `ION` and` myionctrl` sources to `/usr/src/ion` and`/usr/src/myionctrl` folders, compiles programs from sources and writes them to `/usr/bin/`.
- `myioninstaller.py`: configures the validator and `myionctrl`; generates validator connection keys.

## Installation modes
There are two installation modes: `liteserver` and `validator`. They both **compile** and install `ION` components and run the node/validator. Use `liteserver` mode if you want to use your node as Liteserver only.
Use `validator` mode if you want to participate in the validator elections (you still can use that node as Liteserver).

Learn more about node types: https://docs.ice.io/participate/nodes/node-types

## Installation for Ubuntu
1. Download and execute the `install.sh` script in the desired installation mode. During installation the script prompts you for the superuser password several times.
	```sh
	wget https://raw.githubusercontent.com/ice-blockchain/myionctrl/master/scripts/install.sh
	sudo bash install.sh -m <mode>
	```

2. Done. You can try to run the `myionctrl` console now.
	```sh
	myionctrl
	```


## Installation for Debian
1. Download and execute the `install.sh` script in the desired installation mode. During installation the script prompts you for the superuser password several times.
	```sh
	wget https://raw.githubusercontent.com/ice-blockchain/myionctrl/master/scripts/install.sh
	su root -c 'bash install.sh -m <mode>'
	```

2. Done. You can try to run the `myionctrl` console now.
	```sh
	myionctrl
	```

# Telemetry
By default, `myionctrl` sends validator statistics to the https://ice.io server.
It is necessary to identify network abnormalities, as well as to quickly give feedback to developers.
To disable telemetry during installation, use the `-t` flag:
```sh
sudo bash install.sh -m <mode> -t
```

To disable telemetry after installation, do the following:
```sh
MyIonCtrl> set sendTelemetry false
```

# MyIonCtrl installer mode

## Web admin panel
To control the node/validator through the browser, you need to install an additional module:
`myionctrl` -> `installer` -> `enable JR`

Next, you need to create a password for connection:
`myionctrl` -> `installer` -> `setwebpass`

Ready. Now you can go to https://ionadmin.org site and log in with your credentials.
git: https://github.com/igroman787/mtc-jsonrpc

## Local copy of ioncenter
To set up a local https://ice.io copy on your server, install an additional module:
`myionctrl` ->`installer` -> `enable PT`

Ready. A local copy of ioncenter is available at `http://<server-ip-address>:8000`
git: https://github.com/igroman787/pyionv3

# Useful links
* https://docs.ice.io/
