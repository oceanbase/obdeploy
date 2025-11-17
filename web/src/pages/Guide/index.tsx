import Banner from '@/component/Banner';
import { intl } from '@/utils/intl';
import { DownOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { Button, Card, Col, Dropdown, Row, Space, Tag, Tooltip } from 'antd';
import React from 'react';
import { getLocale, history, useModel } from 'umi';
import compManageGuideIcon from '../../../public/assets/welcome/component-manage.svg';
import obGuideIcon from '../../../public/assets/welcome/ob-guide.png';
import ocpGuideIcon from '../../../public/assets/welcome/ocp-guide.png';;
import omsGuideIcon from '../../../public/assets/welcome/oms-guide.png';

import styles from './index.less';
import { getTailPath } from '@/utils/helper';

const locale = getLocale();

interface CustomCardProps {
  noTooltip: boolean;
  disable: boolean;
  icon: string;
  title: string;
  detail: string;
  id: string;
  onClick?: (prop: string) => void;
  type?: string;
  tooltipText?: string;
  action?: React.ReactNode;
}

export default function Guide() {
  const isCN = locale === 'zh-CN';
  const buttonStyle = isCN ? styles.guideBtn : styles.guideBtnUS;

  // const taiPath = getTailPath();
  const isUpgrade = location.hash.split('/').pop()?.split('?')[1] === 'update';

  const guideConfigListRef = [
    ...!isUpgrade ? [
      {
        id: 'ob',
        icon: obGuideIcon,
        title: intl.formatMessage({
          id: 'OBD.pages.Guide.OceanbaseAndSupportingTools',
          defaultMessage: 'OceanBase 及配套工具',
        }),
        detail: intl.formatMessage({
          id: 'OBD.pages.Guide.DistributedDatabasesAndVariousTools',
          defaultMessage:
            '分布式数据库以及各类工具，方便客户管理、运维和使用',
        }),
        action: (
          <Button
            onClick={() => {
              setOBCurrentStep(1);
              history.push('/obdeploy');
            }}
            className={buttonStyle}
            style={locale === 'zh-CN' ? { width: 63, } : { width: 100 }}
          >
            {intl.formatMessage({
              id: 'OBD.pages.Guide.Installation',
              defaultMessage: '安装',
            })}
          </Button>
        ),
      },
    ] : [],

    {

      icon: ocpGuideIcon,
      title: intl.formatMessage({
        id: 'OBD.pages.Guide.OceanbaseCloudPlatform',
        defaultMessage: 'OceanBase 云平台',
      }),
      id: 'ocp-guide',
      detail: intl.formatMessage({
        id: 'OBD.pages.Guide.FullLifecycleManagementForOb',
        defaultMessage: '可对 OB 集群进行全生命周期管理',
      }),
      action: (
        !isUpgrade ? <>
          <Dropdown
            menu={{
              items: [
                {
                  label: (
                    <div>
                      <p className={styles.cardDetailTitle}>
                        {intl.formatMessage({
                          id: 'OBD.pages.Guide.UseTheNewOceanbaseDatabase',
                          defaultMessage: '使用全新 OceanBase 数据库',
                        })}{' '}
                        <Tag className={`green-tag`}>
                          {intl.formatMessage({
                            id: 'OBD.pages.components.DeployType.Recommended',
                            defaultMessage: '推荐',
                          })}
                        </Tag>
                      </p>
                      <p className={styles.cardDetailText}>
                        {intl.formatMessage({
                          id: 'OBD.pages.Guide.ANewOceanbaseDatabaseWill',
                          defaultMessage:
                            '将建立全新 OceanBase 数据库来部署 MetaDB 继而安装 OCP',
                        })}
                      </p>
                    </div>
                  ),

                  key: '/ocpInstaller/install',
                },
                {
                  label: (
                    <div>
                      <p className={styles.cardDetailTitle}>
                        {intl.formatMessage({
                          id: 'OBD.pages.Guide.UseAnExistingOceanbaseDatabase',
                          defaultMessage: '使用已有 OceanBase 数据库',
                        })}
                      </p>
                      <p className={styles.cardDetailText}>
                        {intl.formatMessage({
                          id: 'OBD.pages.Guide.MetadbWillBeDeployedThrough',
                          defaultMessage:
                            '将通过已有 OceanBase 数据库来部署 MetaDB 继而安装 OCP',
                        })}{' '}
                      </p>
                    </div>
                  ),

                  key: '/ocpInstaller/configuration',
                },
              ],

              onClick: (val) => {
                history.push(val.key);
              },
            }}
          >
            <Button
              className={buttonStyle}
              style={locale === 'zh-CN' ? { width: 84 } : { width: 120 }}
            >
              <Space>
                {intl.formatMessage({
                  id: 'OBD.pages.Guide.Installation',
                  defaultMessage: '安装',
                })}

                <DownOutlined style={{ color: '#5C6B8A' }} />
              </Space>
            </Button>
          </Dropdown>
        </> : <Button
          onClick={() => {
            setOBCurrentStep(1);
            history.push('/updateOcp');
          }}
          className={buttonStyle}
          style={locale === 'zh-CN' ? { width: 63, marginBottom: 58 } : { width: 100, marginBottom: 58 }}
        >
          <span style={{ marginBottom: 50 }}>升级</span>
        </Button>
      ),
    },
    ...!isUpgrade ? [
      {
        id: 'component-manage',
        icon: compManageGuideIcon,
        title: intl.formatMessage({
          id: 'OBD.pages.Guide.ComponentManagement',
          defaultMessage: '组件管理',
        }),
        detail: intl.formatMessage({
          id: 'OBD.pages.Guide.YouCanInstallAndUninstall.1',
          defaultMessage: '可集群进行 OBAgent、Prometheus 等组件安装、卸载',
        }),
        ...(
          {
            action: (
              <Dropdown
                // getPopupContainer={() => document.getElementById('component-manage')}
                menu={{
                  items: [
                    {
                      label: intl.formatMessage({
                        id: 'OBD.pages.Guide.ComponentInstallation',
                        defaultMessage: '组件安装',
                      }),
                      key: '/componentDeploy',
                    },
                    {
                      label: intl.formatMessage({
                        id: 'OBD.pages.Guide.ComponentUninstallation',
                        defaultMessage: '组件卸载',
                      }),
                      key: '/componentUninstall',
                    },
                  ],

                  onClick: (val) => {
                    history.push(val.key);
                  },
                }}
              >
                <Button
                  className={buttonStyle}
                  style={locale === 'zh-CN' ? { width: 84 } : { width: 130 }}
                >
                  <Space>
                    {intl.formatMessage({
                      id: 'OBD.pages.Guide.Management',
                      defaultMessage: '管理',
                    })}

                    <DownOutlined style={{ color: '#5C6B8A' }} />
                  </Space>
                </Button>
              </Dropdown>
            ),
          }
        ),
      },
    ] : [],

    {
      id: 'oms',
      icon: omsGuideIcon,
      title: intl.formatMessage({
        id: 'OBD.pages.Guide.OceanbaseDataMigration',
        defaultMessage: 'OceanBase 数据迁移',
      }),
      detail: intl.formatMessage({
        id: 'OBD.pages.Guide.ItIsAOneStop',
        defaultMessage: '数据库一站式数据传输和同步产品',
      }),
      action: (
        <Button
          onClick={() => {
            setOBCurrentStep(1);
            if (isUpgrade) {
              history.push('/updateOms');
            } else {
              history.push('/oms');
            }
          }}
          className={buttonStyle}
          style={
            locale === 'zh-CN'
              ? {
                width: 63,
                marginBottom: isUpgrade ? 58 : 0
              }
              :
              {
                width: 100, marginBottom: isUpgrade ? 58 : 0
              }
          }
        >
          {
            isUpgrade ? '升级' : intl.formatMessage({
              id: 'OBD.pages.Guide.Installation',
              defaultMessage: '安装',
            })
          }

        </Button>
      ),
    },
  ];

  const { setCurrentStep: setOBCurrentStep, DOCS_PRODUCTION } =
    useModel('global');
  const CustomCard = ({
    disable,
    icon,
    title,
    detail,
    action,
    id,
    upgradeStyle,
  }: CustomCardProps) => {


    return (
      <Card
        bodyStyle={upgradeStyle ? {
          width: '100%',
          paddingTop: 50,
          paddingBottom: 0,
          height: '100%',
        } : {
          width: '100%',
          paddingTop: 0,
          paddingBottom: 0,
          height: '100%',

        }}
        className={
          disable
            ? styles.disableCustomCardContainer
            : styles.customCardContainer
        }
        id={id}
        style={upgradeStyle ? {
          height: '332px',
        } : {}}
      >
        <div className={styles.cardHeader}>
          <img className={styles.cardImg} src={icon} alt="" />
          <span
            className={disable ? styles.disableCardTitle : styles.cardTitle}
          >
            {title}
          </span>
        </div>
        <p className={disable ? styles.disableCardDetail : styles.cardDetail}>
          {detail}
        </p>
        {action}
      </Card>
    );
  };

  const Title = () => {
    const textStyle = {
      fontWeight: '400',
      fontSize: '14px',
      lineHeight: '22px',
    };
    return (
      <div style={{ height: '32px' }}>
        <span style={{ color: '#132039' }}>
          {
            isUpgrade ? '请选择升级的产品' : intl.formatMessage({
              id: 'OBD.pages.Guide.SelectInstallProductOrComponent',
              defaultMessage: '请选择安装产品或组件管理',
            })}
        </span>{' '}
        <span style={{ ...textStyle, color: '#E2E8F3' }}>|</span>{' '}
        <a
          href={DOCS_PRODUCTION}
          style={{ ...textStyle, color: '#006AFF', textDecoration: 'none' }}
          target="_blank"
        >
          {intl.formatMessage({
            id: 'OBD.pages.Guide.HelpDocument',
            defaultMessage: '帮助文档',
          })}
        </a>
      </div>
    );
  };

  return (
    <div className={styles.guideContainer}>
      <Banner
        title={
          isUpgrade ? intl.formatMessage({
            id: 'OBD.OcpInstaller.Welcome.WelcomeToTheOcpUpgrade',
            defaultMessage: '欢迎您使用 OceanBase 升级向导',
          }) : intl.formatMessage({
            id: 'OBD.pages.Guide.WelcomeToTheOceanbaseDeployment',
            defaultMessage: '欢迎使用 OceanBase 部署向导',
          })}
        isUpgrade={isUpgrade}
      />

      <div className={styles.content} style={{ display: 'block' }}>
        <ProCard
          title={<Title />}
          style={isUpgrade ? {} : {
            width: 1040,
            height: 576,
            boxShadow:
              '0 2px 4px 0 rgba(19,32,57,0.02), 0 1px 6px -1px rgba(19,32,57,0.02), 0 1px 2px 0 rgba(19,32,57,0.03)',
          }}
          bodyStyle={{ height: 'calc(100% - 64px)' }}
        >
          <Row
            gutter={[24, 24]}
            justify="center"
            align="middle"
          >
            {guideConfigListRef.map((guideConfig, idx) => {
              return (
                <Col
                  key={idx}
                  span={12}
                  style={
                    idx % 2 === 0
                      ? { height: 'calc(50% - 12px)', paddingLeft: 0 }
                      : { height: 'calc(50% - 12px)', paddingRight: 0 }
                  }
                >
                  <CustomCard upgradeStyle={isUpgrade} {...guideConfig} />
                </Col>
              );
            })}
          </Row>
        </ProCard>
      </div>
    </div>
  );
}
