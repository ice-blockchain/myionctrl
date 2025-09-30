#!/bin/bash
set -e

# colors
COLOR='\033[92m'
ENDC='\033[0m'
mydir=`pwd`

# check sudo permissions
if [ "$(id -u)" != "0" ]; then
    echo "Please run script as root"
    exit 1
fi

author="ice-blockchain"
repo="myionctrl"
branch="master"
network="mainnet"
ion_node_version="master"  # Default version


show_help_and_exit() {
    echo 'Supported arguments:'
    echo ' -c  PATH         Provide custom config for ioninstaller.sh'
    echo ' -t               Disable telemetry'
    echo ' -i               Ignore minimum requirements'
    echo ' -d               Use pre-packaged dump. Reduces duration of initial synchronization.'
    echo ' -a               Set MyIonCtrl git repo author'
    echo ' -r               Set MyIonCtrl git repo'
    echo ' -b               Set MyIonCtrl git repo branch'
    echo ' -m  MODE         Install MyIonCtrl with specified mode (validator or liteserver)'
    echo ' -n  NETWORK      Specify the network (mainnet or testnet)'
    echo ' -v  VERSION      Specify the ion node version (commit, branch, or tag)'
    echo ' -u  USER         Specify the user to be used for MyIonCtrl installation'
    echo ' -p  PATH         Provide backup file for MyIonCtrl installation'
    echo ' -o               Install only MyIonCtrl. Must be used with -p'
    echo ' -l               Install only ION node'
    echo ' -h               Show this help'
    exit
}

if [[ "${1-}" =~ ^-*h(elp)?$ ]]; then
    show_help_and_exit
fi

# node install parameters
config="https://cdn.ice.io/mainnet/global.config.json"
telemetry=true
ignore=false
dump=false
only_mtc=false
only_node=false
backup=none
mode=none
cpu_required=16
mem_required=64000000  # 64GB in KB

while getopts ":c:tidola:r:b:m:n:v:u:p:h" flag; do
    case "${flag}" in
        c) config=${OPTARG};;
        t) telemetry=false;;
        i) ignore=true;;
        d) dump=true;;
        a) author=${OPTARG};;
        r) repo=${OPTARG};;
        b) branch=${OPTARG};;
        m) mode=${OPTARG};;
        n) network=${OPTARG};;
        v) ion_node_version=${OPTARG};;
        u) user=${OPTARG};;
        o) only_mtc=true;;
        l) only_node=true;;
        p) backup=${OPTARG};;
        h) show_help_and_exit;;
        *)
            echo "Flag -${flag} is not recognized. Aborting"
        exit 1 ;;
    esac
done


if [ "$only_mtc" = true ] && [ "$backup" = "none" ]; then
    echo "Backup file must be provided if only mtc installation"
    exit 1
fi


if [ "${mode}" = "none" ] && [ "$backup" = "none" ]; then  # no mode or backup was provided
    echo "Running cli installer"
    wget https://raw.githubusercontent.com/${author}/${repo}/${branch}/scripts/install.py
    pip3 install --break-system-packages inquirer==3.4.0
    python3 install.py
    exit
fi

# Set config based on network argument
if [ "${network}" = "testnet" ]; then
    config="https://cdn.ice.io/testnet/global.config.json"
    cpu_required=8
    mem_required=16000000  # 16GB in KB
fi

# check machine configuration
echo -e "${COLOR}[1/5]${ENDC} Checking system requirements"

cpus=$(lscpu | grep "CPU(s)" | head -n 1 | awk '{print $2}')
memory=$(cat /proc/meminfo | grep MemTotal | awk '{print $2}')

echo "This machine has ${cpus} CPUs and ${memory}KB of Memory"
if [ "$ignore" = false ] && ([ "${cpus}" -lt "${cpu_required}" ] || [ "${memory}" -lt "${mem_required}" ]); then
    echo "Insufficient resources. Requires a minimum of "${cpu_required}"  processors and  "${mem_required}" RAM."
    exit 1
fi

echo -e "${COLOR}[2/5]${ENDC} Checking for required ION components"
SOURCES_DIR=/usr/src
BIN_DIR=/usr/bin

# create dirs for OSX
if [[ "$OSTYPE" =~ darwin.* ]]; then
    SOURCES_DIR=/usr/local/src
    BIN_DIR=/usr/local/bin
    mkdir -p ${SOURCES_DIR}
fi

# check ION components
file1=${BIN_DIR}/ion/crypto/fift
file2=${BIN_DIR}/ion/lite-client/lite-client
file3=${BIN_DIR}/ion/validator-engine-console/validator-engine-console

if  [ ! -f "${file1}" ] || [ ! -f "${file2}" ] || [ ! -f "${file3}" ]; then
    echo "ION does not exists, building"
    wget https://raw.githubusercontent.com/${author}/${repo}/${branch}/scripts/ion_installer.sh -O /tmp/ion_installer.sh
    bash /tmp/ion_installer.sh -c ${config} -v ${ion_node_version}
fi

# Cloning myionctrl
echo -e "${COLOR}[3/5]${ENDC} Installing MyIonCtrl"
echo "https://github.com/${author}/${repo}.git -> ${branch}"

# remove previous installation
cd $SOURCES_DIR
rm -rf $SOURCES_DIR/myionctrl
pip3 uninstall --break-system-packages myionctrl
pip3 install --break-system-packages psutil==6.1.0 crc16==0.1.1 requests==2.32.3

git clone --depth 1 --branch ${branch} --recursive https://github.com/${author}/${repo}.git ${repo}  # TODO: return --recursive back when fix libraries
git config --global --add safe.directory $SOURCES_DIR/${repo}
cd $SOURCES_DIR/${repo}

pip3 install --break-system-packages -U .  # TODO: make installation from git directly

echo -e "${COLOR}[4/5]${ENDC} Running myioninstaller"
# DEBUG

if [ "${user}" = "" ]; then  # no user
    parent_name=$(ps -p $PPID -o comm=)
    user=$(whoami)
    if [ "$parent_name" = "sudo" ] || [ "$parent_name" = "su" ] || [ "$parent_name" = "python3" ]; then
        user=$(logname)
    fi
fi
echo "User: $user"
python3 -m myioninstaller -u ${user} -t ${telemetry} --dump ${dump} -m ${mode} --only-mtc ${only_mtc} --backup ${backup} --only-node ${only_node}

# create symbolic link if branch not eq myionctrl
if [ "${repo}" != "myionctrl" ]; then
    ln -sf ${SOURCES_DIR}/${repo} ${SOURCES_DIR}/myionctrl
fi

echo -e "${COLOR}[5/5]${ENDC} Myionctrl installation completed"
exit 0
