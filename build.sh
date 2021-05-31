# /bin/bash
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
rm -fr $obd_dir/mirror/remote -p $obd_dir/mirror/remote && cd $obd_dir/mirror/remote
wget http://yum.tbsite.net/mirrors/oceanbase/OceanBase.repo
cp -r -d $obd_dir/* /usr/obd
cd /usr/obd/plugins && ln -sf oceanbase oceanbase-ce
cp -f /usr/obd/profile/obd.sh /etc/profile.d/obd.sh
rm -fr /usr/bin/obd
echo -e "# /bin/bash\n$python_bin /usr/obd/_cmd.py \$*" > /usr/bin/obd
chmod +x /usr/bin/obd
echo -e 'Installation of obd finished successfully\nPlease source /etc/profile.d/obd.sh to enable it'