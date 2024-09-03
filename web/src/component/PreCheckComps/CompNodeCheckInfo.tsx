import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import { Col, Tooltip } from 'antd';
import styles from './index.less';

interface ComponentsNodeConfig {
  name: string;
  servers: string[];
  key: string;
  isTooltip: boolean;
}

interface CompNodeCheckInfoProps {
  componentsNodeConfigList: ComponentsNodeConfig[];
  className?: string
}
export default function CompNodeCheckInfo({
  componentsNodeConfigList,
  className
}: CompNodeCheckInfoProps) {
  return (
    <ProCard
      title={intl.formatMessage({
        id: 'OBD.pages.components.CheckInfo.ComponentNodeConfiguration',
        defaultMessage: '组件节点配置',
      })}
      className={`${className} card-padding-bottom-24`}
    >
      <Col span={componentsNodeConfigList?.length === 1 ? 12 : 24}>
        <ProCard className={styles.infoSubCard} split="vertical">
          {componentsNodeConfigList.map((item: ComponentsNodeConfig) => (
            <ProCard title={item.name} key={item.key}>
              {item.isTooltip ? (
                <Tooltip title={item?.servers} placement="topLeft">
                  <div className="ellipsis">{item?.servers}</div>
                </Tooltip>
              ) : (
                item?.servers
              )}
            </ProCard>
          ))}
        </ProCard>
      </Col>
    </ProCard>
  );
}
