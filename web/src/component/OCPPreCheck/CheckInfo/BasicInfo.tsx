import { intl } from '@/utils/intl';
import { Row, Col, Tag } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import { getLocale } from 'umi';

import type { BasicInfoProp } from './type';
import styles from './index.less';
import { leftCardStyle } from '.';
interface BasicInfoProps {
  basicInfoProp: BasicInfoProp;
}

const locale = getLocale();
export default function BasicInfo({ basicInfoProp }: BasicInfoProps) {
  return (
    <ProCard className={styles.pageCard} split="horizontal">
      <Row gutter={16}>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.BasicInfo.InstallationConfiguration',
            defaultMessage: '安装配置',
          })}
          className="card-padding-bottom-24"
        >
          <Col span={12}>
            <ProCard className={styles.infoSubCard} split="vertical">
              <ProCard
                style={leftCardStyle}
                title={intl.formatMessage({
                  id: 'OBD.OCPPreCheck.CheckInfo.BasicInfo.ClusterName',
                  defaultMessage: '集群名称',
                })}
              >
                {basicInfoProp.appname}
              </ProCard>
              <ProCard
                title={intl.formatMessage({
                  id: 'OBD.OCPPreCheck.CheckInfo.BasicInfo.InstallationType',
                  defaultMessage: '安装类型',
                })}
              >
                {basicInfoProp.type}
              </ProCard>
            </ProCard>
          </Col>
        </ProCard>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.BasicInfo.ProductVersion',
            defaultMessage: '产品版本',
          })}
          className="card-padding-bottom-24"
        >
          <Row gutter={[0, 0]} style={{ flexDirection: 'column' }}>
            {basicInfoProp.productsInfo.map((versionInfo, idx) => (
              <Col key={idx} span={14}>
                <ProCard
                  style={
                    idx !== basicInfoProp.productsInfo.length - 1
                      ? { marginBottom: 16 }
                      : {}
                  }
                  className={styles.infoSubCard}
                  split="vertical"
                >
                  <ProCard
                    style={locale === 'zh-CN' ? leftCardStyle : { width: 288 }}
                    title={intl.formatMessage({
                      id: 'OBD.OCPPreCheck.CheckInfo.BasicInfo.Product',
                      defaultMessage: '产品',
                    })}
                  >
                    {versionInfo.productName}
                    {typeof versionInfo.isCommunity !== 'undefined' && (
                      <Tag className={styles.versionTag}>
                        {versionInfo.isCommunity
                          ? intl.formatMessage({
                              id: 'OBD.OCPPreCheck.CheckInfo.BasicInfo.CommunityEdition',
                              defaultMessage: '社区版',
                            })
                          : intl.formatMessage({
                              id: 'OBD.OCPPreCheck.CheckInfo.BasicInfo.CommercialEdition',
                              defaultMessage: '商业版',
                            })}
                      </Tag>
                    )}
                  </ProCard>
                  <ProCard
                    title={intl.formatMessage({
                      id: 'OBD.OCPPreCheck.CheckInfo.BasicInfo.Version',
                      defaultMessage: '版本',
                    })}
                  >
                    V {versionInfo.version}
                  </ProCard>
                </ProCard>
              </Col>
            ))}
          </Row>
        </ProCard>
      </Row>
    </ProCard>
  );
}
