#!/bin/bash
if [ `id -u` != 0 ] ; then
    echo "Please use root to run"
fi

obd_dir=`dirname $0`
python_bin='/usr/bin/python'
python_path=`whereis python`
for bin in ${python_path[@]}; do
    if [ -x $bin ]; then
        python_bin=$bin
        break 1
    fi
done

read -p "Enter python path [default $python_bin]:"
if [ "x$REPLY" != "x" ]; then
    python_bin=$REPLY
fi

rm -fr /usr/obd && mkdir -p /usr/obd
cp -r -d $obd_dir/* /usr/obd
cd /usr/obd/plugins && ln -sf oceanbase oceanbase-ce
cp -f /usr/obd/profile/obd.sh /etc/profile.d/obd.sh
rm -fr /usr/obd/mirror/remote && mkdir -p /usr/obd/mirror/remote
cd /usr/obd/mirror/remote && wget https://mirrors.aliyun.com/oceanbase/OceanBase.repo
rm -fr /usr/bin/obd
CID=`git log |head -n1 | awk -F' ' '{print $2}'`
BRANCH=`git branch | grep -e "^\*" | awk -F' ' '{print $2}'`
DATE=`date '+%b %d %Y %H:%M:%S'`
cat /usr/obd/_cmd.py | sed "s/<CID>/$CID/" | sed "s/<B_BRANCH>/$BRANCH/" | sed "s/<B_TIME>/$DATE/" > /usr/obd/obd.py
echo -e "#!/bin/bash\n$python_bin /usr/obd/obd.py \$*" > /usr/bin/obd
chmod +x /usr/bin/obd
echo -e 'Installation of obd finished successfully\nPlease source /etc/profile.d/obd.sh to enable it'