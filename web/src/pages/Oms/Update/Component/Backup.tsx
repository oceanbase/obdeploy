import { intl } from '@/utils/intl';
import { ProForm, ProCard } from '@ant-design/pro-components';
import {
    Input,
    Space,
    Button,
    Modal,
    Alert,
    Select,
    Spin,
} from 'antd';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { CloseCircleOutlined, CheckCircleFilled, ExclamationCircleFilled, InfoCircleOutlined, CheckCircleOutlined, CloseCircleFilled } from '@ant-design/icons';
import { useRequest } from 'ahooks';;
import { useModel } from 'umi';
import CustomFooter from '@/component/CustomFooter';
import ExitBtn from '@/component/ExitBtn';
import { pathRule } from '@/pages/constants';
import { useEffect, useState } from 'react';
import { use } from 'i18next';

export default function Backup({
    setCurrent,
    current,
    setBackupStatus,
    backupStatus,
    openBackupModal,
    setOpenBackupModal,
    checkErrorInfo,
    setCheckErrorInfo,
    backupOmsLoading
}: API.StepProp) {
    const { ocpConfigData, setOcpConfigData, setErrorVisible, setErrorsList } =
        useModel('global');

    const [form] = ProForm.useForm();
    const backupMethod = ProForm.useWatch(['backup_method'], form);
    const backupPath = ProForm.useWatch(['backup_path'], form);
    const {
        run: backupOms,
    } = useRequest(OCP.backupOms, {
        manual: true,
        onSuccess: (res) => {
            if (res?.data?.success) {
                setBackupStatus('SUCCESSFUL');
            } else {
                setCheckErrorInfo(res?.data?.error);
                setBackupStatus('FAILED');
            }
        },
        onError: (res) => {
            setCheckErrorInfo(res?.data?.error);
            setBackupStatus('FAILED');
        },
    });

    const nextStep = () => {
        setOcpConfigData({
            ...ocpConfigData,
            backup_method: backupMethod,
            backup_path: backupPath,
        });
        setBackupStatus('INIT');
        setCurrent(current + 1);
        setErrorVisible(false);
        setErrorsList([]);
        setCheckErrorInfo('')
        window.scrollTo(0, 0);
    };

    const prevStep = () => {
        setBackupStatus('INIT');
        setCurrent(current - 1);
    };

    const backupStatusList = [
        {
            status: 'SUCCESSFUL',
            icon: <CheckCircleOutlined style={{ color: '#0ac185' }} />,
            text: intl.formatMessage({
                id: 'OBD.pages.Oms.Update.Component.Backup.DataBackupCompleted',
                defaultMessage: '数据备份完成',
            }),
            desc: intl.formatMessage({
                id: 'OBD.pages.Oms.Update.Component.Backup.WillAutomaticallyEnterUpgrade',
                defaultMessage: '将自动进入升级',
            }),

        },
        {
            status: 'FAILED',
            icon: <CloseCircleOutlined style={{ color: '#ff4b4b' }} />,
            text: intl.formatMessage({
                id: 'OBD.pages.Oms.Update.Component.Backup.DataBackupFailed',
                defaultMessage: '数据备份失败',
            }),
            progressColor: 'exception',
            // desc: '网络请求出错，请检查网络。这里显示失败原因,这里显示失败原因这里显示失败原因',
            desc: checkErrorInfo ? checkErrorInfo : intl.formatMessage({
                id: 'OBD.pages.Oms.Update.Component.Backup.NetworkRequestError',
                defaultMessage: '网络请求出错，请检查网络。这里显示失败原因,这里显示失败原因这里显示失败原因',
            }),
        },
        {
            status: 'RUNNING',
            icon: <InfoCircleOutlined style={{ color: '#006aff' }} />,
            text: intl.formatMessage({
                id: 'OBD.pages.Oms.Update.Component.Backup.DataBackupInProgress',
                defaultMessage: '正在进行数据备份',
            }),
            desc: intl.formatMessage({
                id: 'OBD.pages.Oms.Update.Component.Backup.WillAutomaticallyEnterUpgradeAfterBackup',
                defaultMessage: '备份完成后将自动进入升级, 请耐心等待',
            }),

        }
    ]
    const defaultPath = ocpConfigData?.currentUser === 'root' ? '/root/meta_backup_data' : `/home/${ocpConfigData?.currentUser}/oms/meta_backup_data`;

    return (
        <Space style={{ width: '100%' }} direction="vertical" size="middle">
            <Alert
                type="info"
                showIcon={true}
                message={intl.formatMessage({
                    id: 'OBD.pages.Oms.Update.Component.Backup.UpgradeProcessAlert',
                    defaultMessage: 'OMS 升级过程中将根据升级需要对元信息及监控数据进行变更，变更操作不可逆，建议对元信息及监控数据进行备份，避免因升级导致的不可预知风险。',
                })}
                style={{ height: 54 }}
            />
            <ProCard>
                <p
                    style={{ fontSize: 16, fontWeight: 500 }}
                >
                    {intl.formatMessage({
                        id: 'OBD.pages.Oms.Update.Component.Backup.DataBackup',
                        defaultMessage: '数据备份',
                    })}
                </p>
                <ProForm
                    form={form}
                    submitter={false}
                    initialValues={{
                        backup_method: ocpConfigData?.backup_method || 'data_backup',
                        backup_path: ocpConfigData?.backup_path || defaultPath,
                    }}
                >
                    <ProForm.Item
                        name={'backup_method'}
                        label={intl.formatMessage({
                            id: 'OBD.pages.Oms.Update.Component.Backup.BackupMethod',
                            defaultMessage: '备份方式',
                        })}
                        style={{ width: 343 }}
                        extra={
                            <>
                                {backupMethod === 'not_backup' ?
                                    <div style={{ color: '#ffac33' }}>
                                        <ExclamationCircleFilled style={{ marginRight: 4 }} />
                                        <span>{intl.formatMessage({
                                            id: 'OBD.pages.Oms.Update.Component.Backup.NotRecommendedNoBackup',
                                            defaultMessage: '不推荐"不备份"，如果 OMS 升级过程异常，可能导致 OMS 服务不可恢复',
                                        })}</span>
                                    </div>
                                    :
                                    <div>
                                        {intl.formatMessage({
                                            id: 'OBD.pages.Oms.Update.Component.Backup.OnlyBackupKeyMetadata',
                                            defaultMessage: '仅备份影响 OMS 运行的关键元信息数据，该备份方式可能导致 OMS 平台的监控及运维历史数据丢失',
                                        })}
                                    </div>}
                            </>
                        }
                    >
                        <Select
                            placeholder={intl.formatMessage({
                                id: 'OBD.component.ConnectConfig.PleaseEnter',
                                defaultMessage: '请输入',
                            })}
                            options={[
                                {
                                    label: intl.formatMessage({
                                        id: 'OBD.pages.Oms.Update.Component.Backup.BackupKeyMetadata',
                                        defaultMessage: '备份关键元信息数据',
                                    }),
                                    value: 'data_backup',
                                },
                                {
                                    label: intl.formatMessage({
                                        id: 'OBD.pages.Oms.Update.Component.Backup.NoBackup',
                                        defaultMessage: '不备份',
                                    }),
                                    value: 'not_backup',
                                }
                            ]}
                            onChange={(e) => {
                                setOcpConfigData({
                                    ...ocpConfigData,
                                    backup_method: e,
                                });
                                form.setFieldsValue({
                                    backup_method: e,
                                });
                            }}
                        />
                    </ProForm.Item>
                    {
                        backupMethod === 'data_backup' && (
                            <div style={{ display: 'flex' }}>
                                <ProForm.Item
                                    name={'backup_path'}
                                    label={intl.formatMessage({
                                        id: 'OBD.pages.Oms.Update.Component.Backup.BackupPath',
                                        defaultMessage: '备份路径',
                                    })}
                                    style={{ width: 343, marginRight: 8 }}
                                    rules={[
                                        {
                                            required: true,
                                            message: intl.formatMessage({
                                                id: 'OBD.pages.Oms.Update.Component.Backup.PleaseEnterBackupPath',
                                                defaultMessage: '请输入备份路径',
                                            }),
                                        },
                                        pathRule,
                                    ]}
                                    extra={
                                        <>
                                            {

                                                backupStatus === 'SUCCESSFUL' ?
                                                    <CheckCircleFilled style={{ color: '#0ac185' }} />
                                                    : backupStatus === 'FAILED' &&
                                                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                                            }

                                            <span
                                                style={{
                                                    marginLeft: 4,
                                                    color: backupStatus === 'FAILED' ? '#ff4d4f' : undefined
                                                }}>
                                                {
                                                    backupStatus === 'SUCCESSFUL' ?
                                                        intl.formatMessage({
                                                            id: 'OBD.pages.Oms.Update.Component.Backup.TestPassed',
                                                            defaultMessage: '校验通过',
                                                        })
                                                        : backupStatus === 'FAILED' ?
                                                            (checkErrorInfo ? checkErrorInfo : intl.formatMessage({
                                                                id: 'OBD.pages.Oms.Update.Component.Backup.InsufficientPathPermissions',
                                                                defaultMessage: '当前路径权限不足，请检查路径配置',
                                                            })) :
                                                            intl.formatMessage({
                                                                id: 'OBD.pages.Oms.Update.Component.Backup.SpecifyLocalPath',
                                                                defaultMessage: '请指定当前 OBD 所在节点的本地路径，保证可用空间至少 2 GiB 以上',
                                                            })}
                                            </span>
                                        </>
                                    }
                                >
                                    <Input
                                        placeholder={intl.formatMessage({
                                            id: 'OBD.pages.Oms.Update.Component.Backup.PleaseEnterBackupPath',
                                            defaultMessage: '请输入备份路径',
                                        })}
                                    />
                                </ProForm.Item>
                                <ProForm.Item label={<br />}>
                                    <Button

                                        onClick={() => {
                                            setCheckErrorInfo('')
                                            backupOms({ backup_path: backupPath, pre_check: true });
                                            setOcpConfigData({
                                                ...ocpConfigData,
                                                backup_method: backupMethod,
                                                backup_path: backupPath,
                                            })
                                        }}
                                    >
                                        {intl.formatMessage({
                                            id: 'OBD.pages.Oms.Update.Component.Backup.Test',
                                            defaultMessage: '校验',
                                        })}
                                    </Button>
                                </ProForm.Item>
                            </div>
                        )
                    }

                </ProForm>
            </ProCard>
            <Modal
                title={
                    <>
                        <Space style={{ fontSize: 16, fontWeight: 500 }}>
                            {backupStatusList.find(item => item.status === backupStatus)?.icon}
                            <span> {backupStatusList.find(item => item.status === backupStatus)?.text}</span>
                        </Space>
                    </>
                }
                open={openBackupModal}
                footer={null}
                closable={false}
                width={424}
            >
                <div style={{ color: '#5c6b8a', marginBottom: 8, marginLeft: 24 }}>
                    {backupStatusList.find(item => item.status === backupStatus)?.desc}
                </div>
                <Spin
                    spinning={backupOmsLoading}
                    style={{ width: 100, height: 100, paddingTop: 24, margin: '0 auto' }}
                />
            </Modal>
            <CustomFooter>
                <ExitBtn />
                <Button onClick={prevStep}>
                    {intl.formatMessage({
                        id: 'OBD.component.ConnectConfig.PreviousStep',
                        defaultMessage: '上一步',
                    })}
                </Button>
                <Button type="primary" onClick={nextStep} >
                    {intl.formatMessage({
                        id: 'OBD.component.ConnectConfig.NextStep',
                        defaultMessage: '下一步',
                    })}
                </Button>
            </CustomFooter>
        </Space>
    );
}