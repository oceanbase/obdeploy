import { useModel } from 'umi';
import CheckInfo from './CheckInfo';
import { Alert, Tabs, TabsProps } from 'antd';
import TopoComponent from './TopoComponent';
import styles from './TopoCheck.less';
import { useState } from 'react';
import { intl } from '@/utils/intl';

export default function TopoCheck(
    {
        deployMode,
    }: {
        deployMode: string,
    }) {

    const { configData } = useModel('global');
    const { oceanbase } = configData?.components || {};
    const [activeKey, setActiveKey] = useState<string>('checkInfo');

    const items: TabsProps['items'] = [
        {
            key: 'checkInfo',
            label: '配置信息',
            children: <CheckInfo
                deployMode={deployMode}
            />,
        },
        {
            key: 'topo',
            label: '拓扑图',
            children: <TopoComponent />,
        },
    ];

    return <>
        {
            (oceanbase?.topology?.length > 1)
                ?
                <>
                    <Alert
                        message={intl.formatMessage({
                            id: 'OBD.pages.components.CheckInfo.OceanbaseTheInstallationInformationConfiguration',
                            defaultMessage:
                                'OceanBase 安装信息配置已完成，请检查并确认以下配置信息，确定后开始预检查。',
                        })}
                        type="info"
                        showIcon
                    />
                    <Tabs
                        defaultActiveKey="checkInfo"
                        activeKey={activeKey}
                        onChange={(key) => setActiveKey(key)}
                        items={items}
                        className={`${styles.topoCheckTabs} ${activeKey === 'topo' ? styles.showBorder : ''}`}
                    />
                </>
                : <CheckInfo deployMode={deployMode} />
        }
    </>;
}
