#!/bin/bash
full=true
while getopts f flag; do
	case "${flag}" in
		f) full=false
	esac
done

# Проверить sudo
if [ "$(id -u)" != "0" ]; then
	echo "Please run script as root"
	exit 1
fi

# Цвета
COLOR='\033[34m'
ENDC='\033[0m'

# Остановка служб
systemctl stop validator
systemctl stop myioncore
systemctl stop dht-server

# Переменные
str=$(systemctl cat myioncore | grep User | cut -d '=' -f2)
user=$(echo ${str})

# Удаление служб
rm -rf /etc/systemd/system/validator.service
rm -rf /etc/systemd/system/myioncore.service
rm -rf /etc/systemd/system/dht-server.service
systemctl daemon-reload

# Удаление файлов
if $full; then
	echo "removing Ton node"
	rm -rf /usr/src/ion
	rm -rf /usr/bin/ion
	rm -rf /var/ion-work
	rm -rf /var/ion-dht-server
fi

rm -rf /usr/src/myionctrl
rm -rf /usr/src/mtc-jsonrpc
rm -rf /usr/src/pyionv3
rm -rf /tmp/myion*
rm -rf /usr/local/bin/myioninstaller/
rm -rf /usr/local/bin/myioncore/myioncore.db
rm -rf /home/${user}/.local/share/myionctrl
rm -rf /home/${user}/.local/share/myioncore/myioncore.db

# Удаление ссылок
if $full; then
	echo "removing ion node"
	rm -rf /usr/bin/fift
	rm -rf /usr/bin/liteclient
	rm -rf /usr/bin/validator-console
fi
rm -rf /usr/bin/myionctrl

# removing pip packages
pip3 uninstall -y myionctrl
pip3 uninstall -y ion-http-api

# Конец
echo -e "${COLOR}Uninstall Complete${ENDC}"
