import { intl } from '@/utils/intl';
import React, { useState } from 'react';
import { history } from 'umi';
import { Button, Card, Result, Tag, Col, Row } from '@oceanbase/design';
import { Alert } from 'antd';
import { useRequest, useUpdateEffect } from 'ahooks';
import { errorHandler } from '@/utils';
import * as Process from '@/services/ocp_installer_backend/Process';
import Banner from '@/component/Banner';
import CustomFooter from '@/component/CustomFooter';
import ExitBtn from '@/component/ExitBtn';
import styles from './index.less';

export interface IndexProps {
  location: {
    query: { type: string };
  };
}

type ConfigMethodType = 'ocpInstaller/configuration' | 'ocpInstaller/install';
type InstallIconType =
  | '/assets/welcome/new-db-selected.svg'
  | '/assets/welcome/new-db-unselected.svg';
type ConfigurationIconType =
  | '/assets/welcome/old-db-selected.svg'
  | '/assets/welcome/old-db-unselected.svg';
//创建新的数据库——》install
//使用已有的 ——》configuration
const Index: React.FC<IndexProps> = ({
  location: {
    query: { type },
  },
}) => {
  let isUpdate, isHaveMetadb;
  const [configMethod, setConfigMethod] = useState<ConfigMethodType>(
    'ocpInstaller/install',
  );
  const [installIcon, setInstallIcon] = useState<InstallIconType>(
    '/assets/welcome/new-db-selected.svg',
  );
  const [configurationIcon, setConfigurationIcon] =
    useState<ConfigurationIconType>('/assets/welcome/old-db-unselected.svg');
  // useEffect(() => {
  //   dispatch({
  //     type: 'global/update',
  //     payload: {
  //       isUpdate: type === 'upgrade',
  //     },
  //   });
  // }, [type]);
  // 退出
  const { run: suicide, loading: suicideLoading } = useRequest(
    Process.suicide,
    {
      manual: true,
      onSuccess: (res) => {
        if (res?.success) {
          // dispatch({
          //   type: 'global/update',
          //   payload: {
          //     installStatus: '',
          //     installResult: '',
          //   },
          // });
          history.push(`/quit`);
        }
      },
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    },
  );

  const features = [
    {
      name: intl.formatMessage({
        id: 'OBD.OcpInstaller.Index.LifecycleManagementOM',
        defaultMessage: '全生命周期管理（运维管控）',
      }),
      description: intl.formatMessage({
        id: 'OBD.OcpInstaller.Index.OcpImplementsUnifiedManagementOf',
        defaultMessage:
          'OCP 实现对 OceanBase 资源的统一管理，实现了对资源的创建、备份恢复、监控告警、巡检、自治、升级、删除等全生命周期管理。',
      }),
    },
    {
      name: intl.formatMessage({
        id: 'OBD.OcpInstaller.Index.MonitoringAlarm',
        defaultMessage: '监控告警',
      }),
      description: intl.formatMessage({
        id: 'OBD.OcpInstaller.Index.OcpMonitorsOceanbaseFromDifferent',
        defaultMessage:
          'OCP 支持从主机、集群、租户等不同维度对 OceanBase 进行监控，并且提供包括钉钉、微信、邮件等多种不同的告警方式，保障集群安全 。',
      }),
    },
    {
      name: intl.formatMessage({
        id: 'OBD.OcpInstaller.Index.BackupAndRecovery',
        defaultMessage: '备份恢复',
      }),
      description: intl.formatMessage({
        id: 'OBD.OcpInstaller.Index.OcpProvidesBackupAndRecovery',
        defaultMessage:
          'OCP 提供对 OceanBase 集群、租户的备份恢复能力，支持自动将全量、增量、日志备份到NAS、OSS等存储类型，支持一键恢复操作。',
      }),
    },
    // 自动的判断商业版还是社区版改起来比较多。我们这次先直接下掉
    // 商业版特有
    // {
    //   name: '容灾管理',
    //   description:
    //     'OCP 支持自动化部署主备集群，实现对业务的容灾保护，支持主备集群解藕、主备切换演练，容灾应急切换等运维能力对集群进行管理。',
    // },
    {
      name: intl.formatMessage({
        id: 'OBD.OcpInstaller.Index.DiagnosticOptimization',
        defaultMessage: '诊断优化',
      }),
      description: intl.formatMessage({
        id: 'OBD.OcpInstaller.Index.OcpProvidesClosedLoopDiagnostics',
        defaultMessage:
          'OCP 针对 SQL 提供从感知、根因分析、执行建议的闭环诊断能力。OCP 同时还实现了从集群复制、会话、死锁、容量等维度的诊断能力。',
      }),
    },
    // 商业版特有
    // {
    //   name: '自治服务',
    //   description:
    //     'OCP 将多年的 OceanBase 集群的专家经验沉淀为产品功能，提供从事件感知、根因分析、自治自愈到告警通知、应急处理的全链路自治能力。',
    // },
  ];

  const mouseLeaveInstall = () => {
    if (configMethod !== 'ocpInstaller/install') {
      setInstallIcon('/assets/welcome/new-db-unselected.svg');
    }
  };

  const mouseLeaveConfiguration = () => {
    if (configMethod !== 'ocpInstaller/configuration') {
      setConfigurationIcon('/assets/welcome/old-db-unselected.svg');
    }
  };

  useUpdateEffect(() => {
    if (configMethod === 'ocpInstaller/install') {
      setInstallIcon('/assets/welcome/new-db-selected.svg');
      setConfigurationIcon('/assets/welcome/old-db-unselected.svg');
    } else {
      setConfigurationIcon('/assets/welcome/old-db-selected.svg');
      setInstallIcon('/assets/welcome/new-db-unselected.svg');
    }
  }, [configMethod]);

  return (
    <div>
      {isUpdate ? (
        <div
          className={styles.updateContainer}
          data-aspm="c323726"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.OcpInstaller.Index.UpgradeWelcomePage',
            defaultMessage: '升级欢迎页',
          })}
          data-aspm-param={``}
          data-aspm-expo
        >
          <div className={styles.upgrade}>
            <div className={styles.title}>
              {intl.formatMessage({
                id: 'OBD.OcpInstaller.Index.WelcomeToTheOcpUpgrade',
                defaultMessage: '欢迎使用 OCP 升级向导',
              })}
            </div>
            <div className={styles.descriptions}>
              OceanBase Cloud Platfrom upgrade wizard
            </div>
            <Button
              type="primary"
              size="large"
              className={styles.startBtn}
              onClick={() => {
                history.push(`/update`);
              }}
            >
              {intl.formatMessage({
                id: 'OBD.OcpInstaller.Index.StartUpgradingToV',
                defaultMessage: '开始升级至 V 4.0.3',
              })}
            </Button>
          </div>
        </div>
      ) : (
        <div
          className={styles.container}
          data-aspm="c323727"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.OcpInstaller.Index.InstallTheWelcomePage',
            defaultMessage: '安装欢迎页',
          })}
          data-aspm-param={``}
          data-aspm-expo
        >
          <Banner
            title={intl.formatMessage({
              id: 'OBD.OcpInstaller.Index.WelcomeToTheOcpDeployment',
              defaultMessage: '欢迎使用 OCP 部署向导',
            })}
          />
          <div className={styles.content} style={{ display: 'block' }}>
            <Card
              divided={false}
              title={intl.formatMessage({
                id: 'OBD.OcpInstaller.Index.SelectAMetadbConfigurationMethod',
                defaultMessage: '请为 OCP 选择一个 MetaDB 的配置方式',
              })}
            >
              <Alert
                type="info"
                showIcon={true}
                // message={}
                description={intl.formatMessage({
                  id: 'OBD.OcpInstaller.Index.MetadbIsAnImportantPart',
                  defaultMessage:
                    'MetaDB 是 OCP 重要组成部分，MetaDB 为 OCP 的管理元信息及监控数据提供底层存储能力，OCP-Server 通过调用 MetaDB 数据为您提供 OceanBase 数据库全生命周期管理服务。',
                })}
                style={{
                  marginBottom: 24,
                  // height: 54
                }}
              />

              <Row gutter={24}>
                <Col span={12}>
                  <div
                    onClick={() => setConfigMethod('ocpInstaller/install')}
                    onMouseEnter={() =>
                      setInstallIcon('/assets/welcome/new-db-selected.svg')
                    }
                    onMouseLeave={mouseLeaveInstall}
                  >
                    <Result
                      className={`${styles.intallType} ${
                        configMethod === 'ocpInstaller/install'
                          ? styles.selected
                          : null
                      }`}
                      icon={<img src={installIcon} />}
                      status="success"
                      title={intl.formatMessage({
                        id: 'OBD.OcpInstaller.Index.CreateANewOceanbaseDatabase',
                        defaultMessage: '创建全新的 OceanBase 数据库',
                      })}
                      subTitle={intl.formatMessage({
                        id: 'OBD.OcpInstaller.Index.MetadbAsOcp',
                        defaultMessage: '作为 OCP 的 MetaDB',
                      })}
                      extra={[
                        <Tag key="install" color="success">
                          {intl.formatMessage({
                            id: 'OBD.OcpInstaller.Index.Recommend',
                            defaultMessage: '推荐',
                          })}
                        </Tag>,
                      ]}
                    />
                  </div>
                </Col>
                <Col span={12}>
                  <div
                    onClick={() =>
                      setConfigMethod('ocpInstaller/configuration')
                    }
                    onMouseEnter={() =>
                      setConfigurationIcon(
                        '/assets/welcome/old-db-selected.svg',
                      )
                    }
                    onMouseLeave={mouseLeaveConfiguration}
                  >
                    <Result
                      className={`${styles.intallType} ${
                        configMethod === 'ocpInstaller/configuration'
                          ? styles.selected
                          : null
                      }`}
                      icon={<img src={configurationIcon} />}
                      status="success"
                      title={intl.formatMessage({
                        id: 'OBD.OcpInstaller.Index.UseAnExistingOceanbaseDatabase',
                        defaultMessage: '使用已有的 OceanBase 数据库',
                      })}
                      subTitle={intl.formatMessage({
                        id: 'OBD.OcpInstaller.Index.MetadbAsOcp',
                        defaultMessage: '作为 OCP 的 MetaDB',
                      })}
                      extra={[
                        <div key="configuration" style={{ height: 22 }} />,
                      ]}
                    />
                  </div>
                </Col>
              </Row>
            </Card>
          </div>
          <CustomFooter>
            <ExitBtn />
            <Button onClick={() => history.push('guide')}>
              {intl.formatMessage({
                id: 'OBD.OcpInstaller.Index.PreviousStep',
                defaultMessage: '上一步',
              })}
            </Button>
            <Button
              type="primary"
              disabled={isHaveMetadb === ''}
              onClick={() => history.push(configMethod)}
            >
              {intl.formatMessage({
                id: 'OBD.OcpInstaller.Index.Ok',
                defaultMessage: '确定',
              })}
            </Button>
          </CustomFooter>
        </div>
      )}
    </div>
  );
};

export default Index;
