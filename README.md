![GitHub stars](https://img.shields.io/github/stars/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub forks](https://img.shields.io/github/forks/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub issues](https://img.shields.io/github/issues/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub pull requests](https://img.shields.io/github/issues-pr/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub last commit](https://img.shields.io/github/last-commit/ice-blockchain/myionctrl?style=flat-square&logo=github) ![GitHub license](https://img.shields.io/github/license/ice-blockchain/myionctrl?style=flat-square&logo=github)

# MyIonCtrl

MyIonCtrl is a console application that is used for launching and managing ION blockchain nodes.

The extended documentation can be found at https://docs.ice.io/v3/documentation/nodes/myionctrl/overview and https://docs.ice.io/v3/guidelines/nodes/overview.

## Operating Systems

It is recommended to use Ubuntu 22.04 LTS or Ubuntu 24.04 LTS for using MyIonCtrl. However, the full list of tested OS is below:

| Operating System | Status        |
|------------------|---------------|
| Ubuntu 20.04 LTS | OK            |
| Ubuntu 22.04 LTS | OK            |
| Ubuntu 24.04 LTS | OK            |
| Debian 10        | Deprecated    |
| Debian 11        | OK            |
| Debian 12        | OK            |
| Debian 13        | Not supported |

## Installation
Please note that during the installation and upgrade procedures, MyIonCtrl will need to escalate privileges using the `sudo` or `su` methods in order to upgrade / install system wide components. Depending on your environment, you may be prompted to enter the password for the root or sudo user.


### Modes
There are three main installation modes: `liteserver`, `validator` and `collator`. They all compile and install `ION` components and run node. Use `liteserver` mode if you want to use your node as Liteserver only.
Use `validator` mode if you want to participate in the validator elections (you still can use that node as Liteserver). Use `collator` if you want your node to collate blocks for validators.

Learn more about node types: https://docs.ice.io/v3/documentation/nodes/overview

### Install

1. Download installation script:
	```shell
	wget https://raw.githubusercontent.com/ice-blockchain/myionctrl/master/scripts/install.sh
	```

2. Run script with desired options:
	```shell
	sudo bash install.sh -m <mode>
	```
	Or for Debian:
	```shell
	su root -c 'bash install.sh -m <mode>'
	```

To view all available installation options use `sudo bash install.sh --help`

### Installation configuration

You can also configure some installation parameters using environment variables. For example:
* `VALIDATOR_CONSOLE_PORT` - port for validator console (default: random port in range 2000-65000)
* `LITESERVER_PORT` - port for liteserver (default: random port in range 2000-65000)
* `VALIDATOR_PORT` - port for validator (default: random port in range 2000-65000)

You can provide `env` file with allowed variables to installation script:
```shell
sudo bash install.sh -m <mode> --env-file /path/to/env/
```

### Interactive CLI installer

To install MyIonCtrl using convenient interactive CLI installer, run the installation script without providing mode to it:

```shell
sudo bash install.sh [args]
```
You will be prompted to choose the installation mode and other options.

To run the interactive installer in `dry-run` mode, which will show you all the options you have selected and command 
that will be executed during installation without actually installing MyIonCtrl, use flag `--print-env`:

```shell
sudo bash install.sh --print-env
```

After installation, you can run MyIonCtrl console using the command:
```shell
myionctrl
```

## Telemetry
By default, MyIonCtrl sends validator statistics to the https://ice.io server.
It is necessary to identify network abnormalities, as well as to quickly give feedback to developers.
To disable telemetry during installation, use the `-t` flag:
```sh
sudo bash install.sh -m <mode> -t
```

To disable telemetry after installation, do the following:
```sh
MyIonCtrl> set sendTelemetry false
```
