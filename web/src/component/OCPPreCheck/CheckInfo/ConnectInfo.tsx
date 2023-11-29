import { intl } from '@/utils/intl';
import { Row, Col } from 'antd';
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
                {connectInfo.map((item, _idx) => (
                  <ProCard key={_idx} colSpan={10} title={item.label}>
                    {item.value}
                  </ProCard>
                ))}
              </ProCard>
            </Col>
          ))}
          {/* <Col span={12}>
             <ProCard className={styles.infoSubCard} split="vertical">
               <ProCard colSpan={10} title="主机IP">
                 111.222.3333
               </ProCard>
               <ProCard colSpan={14} title="访问端口">
                 2882
               </ProCard>
             </ProCard>
            </Col>
            <Col span={12}>
             <ProCard  className={styles.infoSubCard} split="vertical">
               <ProCard colSpan={10} title="访问账号">
                 root@sys
               </ProCard>
               <ProCard colSpan={14} title="密码">
                 12345
               </ProCard>
             </ProCard>
            </Col> */}
        </Row>
      </ProCard>
    </ProCard>
  );
}
