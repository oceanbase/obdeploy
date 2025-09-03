import { intl } from '@/utils/intl';
import { Row, Col, Input, Tooltip } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import styles from './index.less';
import type { ConnectInfoType } from './type';

interface ConnectInfoProps {
  connectInfoProp: ConnectInfoType[];
}
export default function ConnectInfo({ connectInfoProp }: ConnectInfoProps) {
  return (
    <ProCard split="horizontal">
      <ProCard
        title={intl.formatMessage({
          id: 'OBD.OCPPreCheck.CheckInfo.ConnectInfo.ConnectionInformation',
          defaultMessage: '连接信息',
        })}
        className={`card-padding-bottom-24`}
        split="horizontal"
      >
        <Row gutter={[16, 16]} style={{ padding: '24px' }}>
          {connectInfoProp.map((connectInfo, idx) => (
            <Col key={idx} span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                {connectInfo.map((item, _idx) => {
                  return (
                    <ProCard key={_idx} colSpan={10} title={item.label}>
                      {
                        item.label === '密码' ? (
                          <Tooltip
                            title={item.value}
                            placement="topLeft"
                          >
                            <Input.Password
                              value={item.value}
                              visibilityToggle={true}
                              readOnly
                              bordered={false}
                              style={{ padding: 0 }}
                            />
                          </Tooltip>
                        ) : (
                          item.value
                        )
                      }
                    </ProCard>
                  )
                })}
              </ProCard>
            </Col>
          ))}
        </Row>
      </ProCard>
    </ProCard>
  );
}
