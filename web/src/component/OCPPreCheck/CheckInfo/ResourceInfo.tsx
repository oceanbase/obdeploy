import { intl } from '@/utils/intl';
import { Row, Col, Typography } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import type { ResourceInfoPropType } from './type';
import styles from './index.less';
import { leftCardStyle } from '.';
import { ocpAddonAfter } from '@/constant/configuration';
import PasswordCard from '@/component/PasswordCard';
interface BasicInfoProps {
  isNewDB: boolean;
  resourceInfoProp: ResourceInfoPropType;
}

const { Text } = Typography;

export default function ResourceInfo({
  isNewDB,
  resourceInfoProp,
}: BasicInfoProps) {
  const {
    serviceConfig,
    resourcePlan,
    memory_size,
    tenantConfig,
    monitorConfig,
    ocpServer,
    userConfig,
  } = resourceInfoProp;
  const serviceMap: any = {
    admin_password: intl.formatMessage({
      id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.AdminPassword',
      defaultMessage: 'Admin密码',
    }),
    home_path: intl.formatMessage({
      id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.SoftwarePath',
      defaultMessage: '软件路径',
    }),
    log_dir: intl.formatMessage({
      id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.LogPath',
      defaultMessage: '日志路径',
    }),
    soft_dir: intl.formatMessage({
      id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.PackagePath',
      defaultMessage: '软件包路径',
    }),
    ocp_site_url: 'ocp.site.url',
  };
  return (
    <ProCard className={styles.pageCard} split="horizontal">
      <Row gutter={16}>
        {!isNewDB && userConfig && (
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.DeployUserConfiguration',
              defaultMessage: '部署用户配置',
            })}
            className="card-padding-bottom-24"
          >
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard
                  style={leftCardStyle}
                  title={intl.formatMessage({
                    id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.Username',
                    defaultMessage: '用户名',
                  })}
                >
                  <Text
                    style={{ width: 200 }}
                    ellipsis={{ tooltip: userConfig.user }}
                  >
                    {userConfig.user}
                  </Text>
                </ProCard>
                <PasswordCard password={userConfig.password} />
                <ProCard
                  title={intl.formatMessage({
                    id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.SshPort',
                    defaultMessage: 'SSH端口',
                  })}
                >
                  {userConfig.port || '-'}
                </ProCard>
              </ProCard>
            </Col>
          </ProCard>
        )}

        {!isNewDB && ocpServer && (
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.OcpDeploymentSelection',
              defaultMessage: 'OCP 部署选择',
            })}
            className="card-padding-bottom-24"
          >
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                {ocpServer.map((server, idx) => (
                  <ProCard key={idx} colSpan={10} title={`节点${idx + 1}`}>
                    {server}
                  </ProCard>
                ))}
              </ProCard>
            </Col>
          </ProCard>
        )}

        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.ServiceConfiguration',
            defaultMessage: '服务配置',
          })}
          className="card-padding-bottom-24"
        >
          <Row gutter={16}>
            <Col span={24}>
              <ProCard className={styles.infoSubCard} split="vertical">
                {serviceConfig &&
                  Object.keys(serviceConfig).map((key, idx) => {
                    let path =
                      key === 'home_path'
                        ? `${serviceConfig[key]}${ocpAddonAfter}`
                        : `${serviceConfig[key]}`;
                    return (
                      <ProCard key={idx} colSpan={6} title={serviceMap[key]}>
                        <Text
                          style={{ width: 200 }}
                          ellipsis={{ tooltip: path }}
                        >
                          {path}
                        </Text>
                      </ProCard>
                    );
                  })}
              </ProCard>
            </Col>
          </Row>
        </ProCard>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.ResourcePlanning',
            defaultMessage: '资源规划',
          })}
          className="card-padding-bottom-24"
        >
          <Col span={6}>
            <ProCard className={styles.infoSubCard} split="vertical">
              {/* <ProCard colSpan={8} title="管理集群数量">
                  {resourcePlan.cluster}
                 </ProCard>
                 <ProCard colSpan={8} title="管理租户数量">
                  {resourcePlan.tenant}
                 </ProCard> */}
              <ProCard
                title={intl.formatMessage({
                  id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.ManageTheNumberOfHosts',
                  defaultMessage: '管理主机数量',
                })}
              >
                {resourcePlan.machine}
              </ProCard>
            </ProCard>
          </Col>
        </ProCard>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.ResourceConfiguration',
            defaultMessage: '资源配置',
          })}
          className="card-padding-bottom-24"
        >
          <Col span={6}>
            <ProCard className={styles.infoSubCard} split="vertical">
              <ProCard
                title={intl.formatMessage({
                  id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.OcpApplicationMemory',
                  defaultMessage: 'OCP 应用内存',
                })}
              >
                {memory_size} GiB
              </ProCard>
            </ProCard>
          </Col>
        </ProCard>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.MetadataTenantConfiguration',
            defaultMessage: '元信息租户配置',
          })}
          className={`card-padding-bottom-24`}
          split="horizontal"
        >
          <Row gutter={[16, 16]} style={{ padding: '24px' }}>
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard
                  colSpan={10}
                  title={intl.formatMessage({
                    id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.TenantName',
                    defaultMessage: '租户名称',
                  })}
                >
                  {tenantConfig.info.tenant_name}
                </ProCard>
                <ProCard
                  colSpan={14}
                  title={intl.formatMessage({
                    id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.Password',
                    defaultMessage: '密码',
                  })}
                >
                  {tenantConfig.info.password}
                </ProCard>
              </ProCard>
            </Col>
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard colSpan={10} title="CPU">
                  {tenantConfig.resource.cpu} VCPUS
                </ProCard>
                <ProCard
                  colSpan={14}
                  title={intl.formatMessage({
                    id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.Memory',
                    defaultMessage: '内存',
                  })}
                >
                  {tenantConfig.resource.memory} GiB
                </ProCard>
              </ProCard>
            </Col>
          </Row>
        </ProCard>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.MonitorDataTenantConfiguration',
            defaultMessage: '监控数据租户配置',
          })}
          className={`card-padding-bottom-24`}
          split="horizontal"
        >
          <Row gutter={[16, 16]} style={{ padding: '24px' }}>
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard
                  colSpan={10}
                  title={intl.formatMessage({
                    id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.TenantName',
                    defaultMessage: '租户名称',
                  })}
                >
                  {monitorConfig.info.tenant_name}
                </ProCard>
                <ProCard
                  colSpan={14}
                  title={intl.formatMessage({
                    id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.Password',
                    defaultMessage: '密码',
                  })}
                >
                  {monitorConfig.info.password}
                </ProCard>
              </ProCard>
            </Col>
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard colSpan={10} title="CPU">
                  {monitorConfig.resource.cpu} VCPUS
                </ProCard>
                <ProCard
                  colSpan={14}
                  title={intl.formatMessage({
                    id: 'OBD.OCPPreCheck.CheckInfo.ResourceInfo.Memory',
                    defaultMessage: '内存',
                  })}
                >
                  {monitorConfig.resource.memory} GiB
                </ProCard>
              </ProCard>
            </Col>
          </Row>
        </ProCard>
      </Row>
    </ProCard>
  );
}
