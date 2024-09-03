import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import { Col, Tooltip } from 'antd';
import styles from './index.less';

interface PathCheckInfoProps {
  home_path: string;
  className?: string;
}

export default function PathCheckInfo({
  home_path,
  className,
}: PathCheckInfoProps) {
  return (
    <ProCard
      title={intl.formatMessage({
        id: 'OBD.pages.components.CheckInfo.SoftwarePathConfiguration',
        defaultMessage: '软件路径配置',
      })}
      className={`${className} card-padding-bottom-24`}
    >
      <Col span={12}>
        <ProCard className={styles.infoSubCard} split="vertical">
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.SoftwarePath',
              defaultMessage: '软件路径',
            })}
          >
            <Tooltip title={home_path} placement="topLeft">
              {home_path}
            </Tooltip>
          </ProCard>
        </ProCard>
      </Col>
    </ProCard>
  );
}
