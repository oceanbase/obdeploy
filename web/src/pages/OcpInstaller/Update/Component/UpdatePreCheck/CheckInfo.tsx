import ArrowIcon from '@/component/Icon/ArrowIcon';
import NewIcon from '@/component/Icon/NewIcon';
import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import {
    Alert,
    Card,
    Col,
    Row,
    Table,
} from 'antd';
import React from 'react';
import { useModel } from 'umi';
import styles from './index.less';

export interface UpdatePreCheckProps {
    updateInfo?: API.connectMetaDB;
    getOcpInfoLoading?: boolean;
    cluster_name: string;
}

const CheckInfo: React.FC<UpdatePreCheckProps> = ({
    updateInfo,
    getOcpInfoLoading,
    cluster_name,
}) => {
    const { ocpConfigData, DOCS_SOP } = useModel('global');
    const version: string = ocpConfigData?.components?.ocpserver?.version;

    return (
        <div
            data-aspm="c323725"
            data-aspm-desc={intl.formatMessage({
                id: 'OBD.Component.UpdatePreCheck.UpgradeEnvironmentPreCheckPage',
                defaultMessage: '升级环境预检查页',
            })}
            data-aspm-param={``}
            data-aspm-expo
            style={{ paddingBottom: 70 }}
        >
            <>
                <Alert
                    type="info"
                    showIcon={true}
                    message=""
                    description={'系统会根据 MetaDB 配置信息获取 OCP 相关配置信息，为保证管理功能一致性，升级程序将升级平台管理服务 OCP Server。请检查并确认以下配置信息，确定后开始预检查。'}
                    style={{
                        margin: '16px 0',
                    }}
                />

                <ProCard
                    title={intl.formatMessage({
                        id: 'OBD.Component.UpdatePreCheck.InstallationConfiguration',
                        defaultMessage: '安装配置',
                    })}
                    className="card-padding-bottom-24"
                >
                    <Col span={12}>
                        <ProCard className={styles.infoSubCard} split="vertical">
                            <ProCard
                                colSpan={10}
                                title={intl.formatMessage({
                                    id: 'OBD.Component.UpdatePreCheck.ClusterName',
                                    defaultMessage: '集群名称',
                                })}
                            >
                                {cluster_name}
                            </ProCard>
                            <ProCard
                                colSpan={14}
                                title={intl.formatMessage({
                                    id: 'OBD.Component.UpdatePreCheck.UpgradeType',
                                    defaultMessage: '升级类型',
                                })}
                            >
                                {intl.formatMessage({
                                    id: 'OBD.Component.UpdatePreCheck.UpgradeAll',
                                    defaultMessage: '全部升级',
                                })}
                            </ProCard>
                        </ProCard>
                    </Col>
                </ProCard>
                <Card
                    loading={getOcpInfoLoading}
                    title={intl.formatMessage({
                        id: 'OBD.Component.UpdatePreCheck.UpgradeConfigurationInformation',
                        defaultMessage: '升级配置信息',
                    })}
                    bordered={false}
                    bodyStyle={{
                        paddingBottom: 24,
                    }}
                >
                    <Row gutter={[24, 16]}>
                        <Col span={24}>
                            <div className={styles.ocpVersion}>
                                {intl.formatMessage({
                                    id: 'OBD.Component.UpdatePreCheck.PreUpgradeVersion',
                                    defaultMessage: '升级前版本：',
                                })}
                                <span>V {updateInfo?.ocp_version}</span>
                            </div>
                            <div
                                style={{
                                    float: 'left',
                                    margin: '0 45px',
                                    textAlign: 'center',
                                    lineHeight: '69px',
                                }}
                            >
                                <ArrowIcon height={30} width={42} />
                            </div>
                            <div className={styles.ocpVersion}>
                                {intl.formatMessage({
                                    id: 'OBD.Component.UpdatePreCheck.UpgradedVersion',
                                    defaultMessage: '升级后版本：',
                                })}

                                <span>V {version}</span>
                                <NewIcon
                                    size={36}
                                    style={{
                                        position: 'relative',
                                        top: -12,
                                    }}
                                />
                            </div>
                        </Col>
                    </Row>
                    <div
                        style={{
                            marginTop: 24,
                            borderRadius: 8,
                            border: '1px solid #CDD5E4',
                            overflow: 'hidden',
                        }}
                    >
                        <Table
                            loading={getOcpInfoLoading}
                            columns={[
                                {
                                    title: intl.formatMessage({
                                        id: 'OBD.Component.UpdatePreCheck.ComponentName',
                                        defaultMessage: '组件名称',
                                    }),
                                    dataIndex: 'name',
                                    width: '20%',
                                },
                                {
                                    title: intl.formatMessage({
                                        id: 'OBD.Component.UpdatePreCheck.NodeIp',
                                        defaultMessage: '节点 IP',
                                    }),
                                    dataIndex: 'ip',
                                    render: (ip, record) => {
                                        if (!ip || ip === '') {
                                            return '-';
                                        }
                                        return ip.map((item: string, index: number) => <span key={index}>{item} </span>);
                                    },
                                },
                            ]}
                            rowKey="name"
                            pagination={false}
                            dataSource={
                                updateInfo?.component ? updateInfo?.component : []
                            }
                        />
                    </div>
                    {updateInfo?.tips && (
                        <p style={{ color: '#8592AD', fontSize: 14, fontWeight: 400 }}>
                            {intl.formatMessage({
                                id: 'OBD.Component.UpdatePreCheck.MetadbSharesMetaTenantResources',
                                defaultMessage:
                                    'MetaDB与MonitorDB共享Meta租户资源，容易造成OCP运行异常，强烈建议您新建Monitor租户，并进行MetaDB数据清理和MonitorDB数据迁移，详情请参考《',
                            })}
                            <a href={DOCS_SOP} target="_blank">
                                SOP
                            </a>
                            》
                        </p>
                    )}
                </Card>
            </>
        </div>
    );
};

export default CheckInfo;
