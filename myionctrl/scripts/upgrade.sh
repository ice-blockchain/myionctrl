#!/bin/bash
set -e

# Проверить sudo
if [ "$(id -u)" != "0" ]; then
	echo "Please run script as root"
	exit 1
fi

# Set default arguments
author="ice-blockchain"
repo="ion"
branch="master"
srcdir="/usr/src/"
bindir="/usr/bin/"
tmpdir="/tmp/ion_src/"

# Get arguments
while getopts a:r:b:g: flag
do
	case "${flag}" in
		a) author=${OPTARG};;
		r) repo=${OPTARG};;
		b) branch=${OPTARG};;
    g) git_url=${OPTARG};;
	esac
done

remote_url="https://github.com/${author}/${repo}.git"
if [ -n "${git_url}" ]; then
  remote_url="${git_url}"
fi

# Цвета
COLOR='\033[92m'
ENDC='\033[0m'

# Установить дополнительные зависимости
apt-get install -y libsecp256k1-dev libsodium-dev ninja-build fio rocksdb-tools liblz4-dev libjemalloc-dev automake libtool

# bugfix if the files are in the wrong place
wget "https://cdn.ice.io/mainnet/global.config.json" -O global.config.json
if [ -f "/var/ion-work/keys/liteserver.pub" ]; then
    echo "Ok"
else
	echo "bugfix"
	mkdir /var/ion-work/keys
    cp /usr/bin/ion/validator-engine-console/client /var/ion-work/keys/client
    cp /usr/bin/ion/validator-engine-console/client.pub /var/ion-work/keys/client.pub
    cp /usr/bin/ion/validator-engine-console/server.pub /var/ion-work/keys/server.pub
    cp /usr/bin/ion/validator-engine-console/liteserver.pub /var/ion-work/keys/liteserver.pub

	# fix validator.service
	sed -i 's/validator-engine\/ion-global.config.json/global.config.json/' /etc/systemd/system/validator.service
	systemctl daemon-reload
fi

if [ ! -d "${bindir}/openssl_3" ]; then
  git clone https://github.com/openssl/openssl ${bindir}/openssl_3
  cd ${bindir}/openssl_3
  git checkout openssl-3.1.4
  ./config
  make build_libs -j$(nproc)
  opensslPath=`pwd`
else
  opensslPath=${bindir}/openssl_3
fi

rm -rf ${tmpdir}/${repo}
mkdir -p ${tmpdir}/${repo}
cd ${tmpdir}/${repo}
echo "${remote_url} -> ${branch}"
git clone --recursive ${remote_url} . || exit 1

# Go to work dir
cd ${srcdir}/${repo}
ls -A1 | xargs rm -rf

# Update code
cp -rfT ${tmpdir}/${repo} .
git checkout ${branch}

git submodule sync --recursive
git submodule update

export CC=/usr/bin/clang
export CXX=/usr/bin/clang++
export CCACHE_DISABLE=1

# Update binary
cd ${bindir}/${repo}
ls --hide="*.config.json" | xargs -d '\n' rm -rf
rm -rf .ninja_*
memory=$(cat /proc/meminfo | grep MemAvailable | awk '{print $2}')
cpuNumber=$(cat /proc/cpuinfo | grep "processor" | wc -l)

cmake -DCMAKE_BUILD_TYPE=Release ${srcdir}/${repo} -GNinja -DION_USE_JEMALLOC=ON -DOPENSSL_FOUND=1 -DOPENSSL_INCLUDE_DIR=$opensslPath/include -DOPENSSL_CRYPTO_LIBRARY=$opensslPath/libcrypto.a
ninja -j ${cpuNumber} fift validator-engine lite-client validator-engine-console generate-random-id dht-server func tonlibjson rldp-http-proxy
systemctl restart validator

# Конец
echo -e "${COLOR}[1/1]${ENDC} ION components update completed"
exit 0
