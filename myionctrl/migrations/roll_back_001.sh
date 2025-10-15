pip3 uninstall -y myionctrl

cd /usr/src
rm -rf myionctrl
git clone --recursive -b myionctrl1 https://github.com/ice-blockchain/myionctrl

echo "Updating /usr/src/myionctrl"
echo "/usr/bin/python3 /usr/src/myionctrl/myionctrl.py $@" > /usr/src/myionctrl
chmod +x /usr/src/myionctrl

echo "Updating myioncore service"
sed -i 's\-m myioncore\/usr/src/myionctrl/myioncore.py\g' /etc/systemd/system/myioncore.service
systemctl daemon-reload
systemctl restart myioncore

echo "Done"
