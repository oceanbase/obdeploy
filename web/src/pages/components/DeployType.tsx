import { useEffect, useState } from 'react';
import { Space, Card, Tag } from 'antd';
import styles from './index.less';

interface Props {
  value?: string;
  onChange?: (value: string) => void;
}

const optionConfig = [
  {
    label: (
      <>
        完全部署<Tag className={`${styles.typeTag} green-tag ml-8`}>推荐</Tag>
      </>
    ),
    value: 'all',
    desc: '配置数据库集群及相关生态工具，提供全套数据库运维管理服务',
  },
  {
    label: '精简部署',
    value: 'ob',
    desc: '只配置数据库集群，以最精简的数据库内核能力提供服务',
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
