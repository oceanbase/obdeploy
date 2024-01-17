import { intl } from '@/utils/intl';
import { history } from 'umi';
import { useRef, useState } from 'react';
import { Tooltip, Space, Row, Col, Card, Button, Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { useModel } from 'umi';

import obSelectIcon from '../../../public/assets/welcome/ob-selected.png';
import obUnselectIcon from '../../../public/assets/welcome/ob-unselected.png';
import ocpSelectIcon from '../../../public/assets/welcome/ocp-selected.png';
import ocpUnselectIcon from '../../../public/assets/welcome/ocp-unselected.png';
import odcSelectIcon from '../../../public/assets/welcome/odc-selected.png';
import odcUnselectIcon from '../../../public/assets/welcome/odc-unselected.png';
import omsSelectIcon from '../../../public/assets/welcome/oms-selected.png';
import omsUnselectIcon from '../../../public/assets/welcome/oms-unselected.png';
import Banner from '@/component/Banner';
import ExitBtn from '@/component/ExitBtn';
import CustomFooter from '@/component/CustomFooter';

import styles from './index.less';

type ChooseResultType = 'obdeploy' | 'ocpInstaller';
interface CustomCardProps {
  disable: boolean;
  unselectIconPath: string;
  selectIconPath: string;
  title: string;
  detail: string;
  onClick?: (prop: string) => void;
  type?: string;
  tooltipText?: string;
  select?: boolean;
}

const getGuideConfigList = (onClick: any) => {
  const guideConfigList: CustomCardProps[] = [
    {
      disable: false,
      unselectIconPath: obUnselectIcon,
      selectIconPath: obSelectIcon,
      title: intl.formatMessage({
        id: 'OBD.pages.Guide.OceanbaseAndSupportingTools',
        defaultMessage: 'OceanBase 及配套工具',
      }),
      detail: intl.formatMessage({
        id: 'OBD.pages.Guide.DistributedDatabasesAndVariousTools',
        defaultMessage: '分布式数据库以及各类工具，方便客户管理、运维和使用',
      }),
      onClick: () => onClick('obdeploy'),
      type: 'obdeploy',
    },
    {
      disable: false,
      unselectIconPath: ocpUnselectIcon,
      selectIconPath: ocpSelectIcon,
      title: 'OCP',
      detail: intl.formatMessage({
        id: 'OBD.pages.Guide.OceanbaseCloudPlatformFullLifecycle',
        defaultMessage: 'OceanBase 云平台：对 OB 集群进行全生命周期管理',
      }),
      onClick: () => onClick('ocpInstaller'),
      type: 'ocpInstaller',
    },
    {
      disable: true,
      unselectIconPath: odcUnselectIcon,
      selectIconPath: odcSelectIcon,
      title: 'ODC',
      detail: intl.formatMessage({
        id: 'OBD.pages.Guide.OceanbaseDeveloperCenterManageDatabases',
        defaultMessage: 'OceanBase 开发者中心：对数据库&表进行管理',
      }),
    },
    {
      disable: true,
      unselectIconPath: omsUnselectIcon,
      selectIconPath: omsSelectIcon,
      title: 'OMS',
      detail: intl.formatMessage({
        id: 'OBD.pages.Guide.OceanbaseDataMigrationFastData',
        defaultMessage: 'OceanBase 数据迁移：对数据进行快速迁移',
      }),
    },
  ];

  return guideConfigList;
};

export default function Guide() {
  const [chooseResult, setChooseResult] =
    useState<ChooseResultType>('obdeploy');
  const guideConfigListRef = useRef<CustomCardProps[]>(
    getGuideConfigList(setChooseResult),
  );
  const { setCurrentStep: setOBCurrentStep, DOCS_PRODUCTION } = useModel('global');
  const CustomCard = ({
    disable = false,
    unselectIconPath,
    selectIconPath,
    title,
    detail,
    onClick,
    type,
    tooltipText,
    select,
  }: CustomCardProps) => {
    const CardWrap = (prop: React.PropsWithChildren<any>) => {
      if (disable) {
        return (
          <Tooltip
            align={{ offset: [40, 60] }}
            title={
              tooltipText ||
              intl.formatMessage({
                id: 'OBD.pages.Guide.TheProductIsUnderConstruction',
                defaultMessage: '产品正在建设中',
              })
            }
          >
            {prop.children}
          </Tooltip>
        );
      } else {
        return prop.children;
      }
    };

    return (
      <CardWrap>
        <Card
          bodyStyle={{ width: '100%' }}
          className={[
            disable
              ? styles.disableCustomCardContainer
              : styles.customCardContainer,
            select ? styles.customCardSelect : '',
          ].join(' ')}
          onClick={onClick && type ? () => onClick(type) : () => {}}
        >
          <div className={styles.cardHeader}>
            <img
              className={styles.cardImg}
              src={select ? selectIconPath : unselectIconPath}
              alt=""
            />

            <span
              className={disable ? styles.disableCardTitle : styles.cardTitle}
            >
              {title}
            </span>
          </div>
          <p className={disable ? styles.disableCardDetail : styles.cardDetail}>
            {detail}
          </p>
        </Card>
      </CardWrap>
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
        <span>
          {intl.formatMessage({
            id: 'OBD.pages.Guide.SelectAnInstallationProduct',
            defaultMessage: '请选择安装产品',
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

  const nextStep = (path: ChooseResultType) => {
    if (path === 'obdeploy') {
      setOBCurrentStep(1);
    }
    history.push(`/${path}`);
  };

  return (
    <div>
      <Banner
        title={intl.formatMessage({
          id: 'OBD.pages.Guide.WelcomeToTheOceanbaseDeployment',
          defaultMessage: '欢迎使用 OceanBase 部署向导',
        })}
      />
      <div className={styles.content} style={{ display: 'block' }}>
        <ProCard
          title={<Title />}
          style={{
            minWidth: '1040px',
            height: '100%',
            boxShadow:
              '0 2px 4px 0 rgba(19,32,57,0.02), 0 1px 6px -1px rgba(19,32,57,0.02), 0 1px 2px 0 rgba(19,32,57,0.03)',
          }}
          bodyStyle={{ height: 'calc(100% - 64px)' }}
          // divided={false}
        >
          <Row
            gutter={[24, 24]}
            style={{ height: '100%' }}
            justify="center"
            align="middle"
          >
            {guideConfigListRef.current.map((guideConfig, idx) => {
              let select = Boolean(
                guideConfig.type && chooseResult === guideConfig.type,
              );
              return (
                <Col key={idx} span={12} style={{ height: 'calc(50% - 12px)' }}>
                  <CustomCard
                    title={guideConfig.title}
                    detail={guideConfig.detail}
                    disable={guideConfig.disable}
                    unselectIconPath={guideConfig.unselectIconPath}
                    selectIconPath={guideConfig.selectIconPath}
                    onClick={guideConfig.onClick}
                    type={guideConfig.type}
                    tooltipText={guideConfig.tooltipText}
                    select={select}
                  />
                </Col>
              );
            })}
          </Row>
        </ProCard>
      </div>
      <CustomFooter>
        <ExitBtn />
        <Button
          type="primary"
          disabled={!chooseResult}
          data-aspm-click="c337188.d384331"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.pages.Guide.WizardSelectDeploymentTool',
            defaultMessage: '向导-选择部署工具',
          })}
          data-aspm-param={``}
          data-aspm-expo
          onClick={() => nextStep(chooseResult!)}
        >
          {intl.formatMessage({
            id: 'OBD.pages.Guide.Ok',
            defaultMessage: '确定',
          })}
        </Button>
      </CustomFooter>
    </div>
  );
}
