import { componentsConfig } from '@/pages/constants';
import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import { Col, Row } from 'antd';
import styles from './index.less';

interface DeployedCompCheckInfoProps {
  componentsList: API.TableComponentInfo[];
  className?: string;
}

export default function DeployedCompCheckInfo({
  componentsList,
  className
}: DeployedCompCheckInfoProps) {
  return (
    <ProCard
      title={intl.formatMessage({
        id: 'OBD.pages.components.CheckInfo.DeployComponents',
        defaultMessage: '部署组件',
      })}
      className={`${className} card-padding-bottom-24`}
    >
      <Row gutter={16}>
        {componentsList.map((item: API.TableComponentInfo, index: number) => (
          <Col
            span={12}
            style={index > 1 ? { marginTop: 16 } : {}}
            key={item.key}
          >
            <ProCard
              className={styles.infoSubCard}
              split="vertical"
              key={item.key}
            >
              <ProCard
                colSpan={10}
                title={intl.formatMessage({
                  id: 'OBD.pages.components.CheckInfo.Component',
                  defaultMessage: '组件',
                })}
              >
                {item?.showComponentName}
              </ProCard>
              <ProCard
                colSpan={7}
                title={intl.formatMessage({
                  id: 'OBD.pages.components.CheckInfo.Type',
                  defaultMessage: '类型',
                })}
              >
                {componentsConfig[item.key]?.type}
              </ProCard>
              <ProCard
                colSpan={7}
                title={intl.formatMessage({
                  id: 'OBD.pages.components.CheckInfo.Version',
                  defaultMessage: '版本',
                })}
              >
                {item?.version}
              </ProCard>
            </ProCard>
          </Col>
        ))}
      </Row>
    </ProCard>
  );
}
