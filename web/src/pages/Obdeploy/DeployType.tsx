import { intl } from '@/utils/intl';
import { useEffect, useState } from 'react';
import { Space, Card, Tag } from 'antd';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface Props {
  value?: string;
  onChange?: (value: string) => void;
}

const optionConfig = [
  {
    label: (
      <>
        {intl.formatMessage({
          id: 'OBD.pages.components.DeployType.FullyDeployed',
          defaultMessage: '完全部署',
        })}
        <Tag className={`${styles.typeTag} green-tag ml-8`}>
          {intl.formatMessage({
            id: 'OBD.pages.components.DeployType.Recommended',
            defaultMessage: '推荐',
          })}
        </Tag>
      </>
    ),

    value: 'all',
    desc: intl.formatMessage({
      id: 'OBD.pages.components.DeployType.ConfigureDatabaseClustersAndRelated',
      defaultMessage:
        '配置数据库集群及相关生态工具，提供全套数据库运维管理服务',
    }),
  },
  {
    label: intl.formatMessage({
      id: 'OBD.pages.components.DeployType.ThinDeployment',
      defaultMessage: '精简部署',
    }),
    value: 'ob',
    desc: intl.formatMessage({
      id: 'OBD.pages.components.DeployType.OnlyDatabaseClustersAreConfigured',
      defaultMessage: '只配置数据库集群，以最精简的数据库内核能力提供服务',
    }),
  },
];

export default function DeployType({ value, onChange }: Props) {
  const [selectValue, setSelectValue] = useState(value || 'all');

  useEffect(() => {
    if (value && value !== selectValue) {
      setSelectValue(value);
    }
  }, [value]);

  useEffect(() => {
    if (onChange) {
      onChange(selectValue);
    }
  }, [selectValue]);
  return (
    <Space size="middle">
      {optionConfig.map((item) => (
        <div className={styles.deployTypeCardContailer} key={item.value}>
          <Card
            className={`${styles.deployTypeCard} ${
              value === item.value ? styles.selectedDeployTypeCard : ''
            }`}
            onClick={() => setSelectValue(item.value)}
          >
            {item.label}
          </Card>
          <span
            className={`${styles.typeDesc} ${
              value === item.value ? styles.selectedTypeDesc : ''
            }`}
          >
            {item.desc}
          </span>
        </div>
      ))}
    </Space>
  );
}
