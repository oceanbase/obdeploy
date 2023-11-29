import { intl } from '@/utils/intl';
import { Space } from 'antd';
import { getLocale } from 'umi';

import styles from './indexZh.less';
interface ConfigTableProps {
  dataSource: API.NewParameterMeta[];
  loading: boolean;
}
const locale = getLocale();
const getMoreColumns = () => {
  const columns = [
    {
      title: intl.formatMessage({
        id: 'OBD.component.MetaDBConfig.ConfigTable.ClusterParameterName',
        defaultMessage: '集群参数名称',
      }),
      dataIndex: 'name',
      width: 250,
      render: (text: string) => text || '-',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.component.MetaDBConfig.ConfigTable.ParameterValue',
        defaultMessage: '参数值',
      }),
      width: locale === 'zh-CN' ? 280 : 360,
      dataIndex: 'parameterValue',
      render: () => {
        return (
          <h1>
            {intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.ConfigTable.ParameterValue',
              defaultMessage: '参数值',
            })}
          </h1>
          // <Form.Item
          //   className={styles.inlineFormItem}
          //   name={[componentKey, 'parameters', record.name || '', 'params']}
          //   rules={[{ validator: parameterValidator }]}
          // >
          //   <Parameter />
          // </Form.Item>
        );
      },
    },
    {
      title: intl.formatMessage({
        id: 'OBD.component.MetaDBConfig.ConfigTable.Introduction',
        defaultMessage: '介绍',
      }),
      dataIndex: 'description',
      render: (text:string) =>
        text ? <div className="ellipsis">{text}</div> : '-',
    },
  ];

  return columns;
};

export default function ConfigTable() {
  return (
    <Space
      className={styles.spaceWidth}
      direction="vertical"
      size="middle"
      style={{ minHeight: 50, marginTop: 16 }}
    >
      aa
    </Space>
  );
}
