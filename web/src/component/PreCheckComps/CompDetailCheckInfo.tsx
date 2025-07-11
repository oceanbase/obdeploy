import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import { Col, Input, Row, Space, Table, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import styles from './index.less';

interface CompDetailCheckInfo {
  clusterConfigInfo: {
    key: string;
    group: string;
    content: {
      label: string;
      value: string | React.ReactNode;
      colSpan: number;
    }[];
    more: { label: string; parameters: any }[];
  }[];
}

export default function CompDetailCheckInfo({
  clusterConfigInfo,
}: CompDetailCheckInfo) {
  const { configData } = useModel('global');
  const { components = {} } = configData || {};
  const { oceanbase = {} } = components;
  const getMoreColumns = (label: string) => {
    const columns: ColumnsType<API.MoreParameter> = [
      {
        title:
          oceanbase.component === 'oceanbase-standalone'
            ? 'oceanbaseStandalone 参数名称'
            : label,
        dataIndex: 'key',
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.ParameterValue',
          defaultMessage: '参数值',
        }),
        dataIndex: 'value',
        render: (text, record) => {
          const content = record.key.includes('password') ? (
            <Input.Password
              value={text}
              visibilityToggle={true}
              readOnly
              bordered={false}
              style={{ padding: 0 }}
            />
          ) : (
            <span>{text}</span>
          );
          return record.adaptive
            ? intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.Adaptive',
                defaultMessage: '自动分配',
              })
            : content || '-';
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.Introduction',
          defaultMessage: '介绍',
        }),
        dataIndex: 'description',
        render: (text) => (
          <Tooltip title={text} placement="topLeft">
            <div className="ellipsis">{text}</div>
          </Tooltip>
        ),
      },
    ];

    return columns;
  };

  return (
    <ProCard split="horizontal">
      <Row gutter={16}>
        {clusterConfigInfo?.map((item, index) => (
          <ProCard
            title={item.group}
            key={item.key}
            className={`${
              index >= 1
                ? 'card-header-padding-top-0 card-padding-bottom-24'
                : 'card-padding-bottom-24'
            }`}
          >
            <Col span={24}>
              <ProCard
                bodyStyle={{ flexWrap: 'wrap' }}
                className={`${styles.infoSubCard} ${styles.clusterConfigCard}`}
                split="vertical"
              >
                {item.content.map((subItem) => (
                  <ProCard
                    title={subItem.label}
                    key={subItem.label}
                    colSpan={subItem.colSpan}
                  >
                    {subItem.value}
                  </ProCard>
                ))}
              </ProCard>
            </Col>
            {item?.more?.length ? (
              <Space
                direction="vertical"
                size="middle"
                style={{ marginTop: 16 }}
              >
                {item?.more.map((moreItem) => {
                  // obproxy_sys_password 不单独展示
                  const obproxyPassword =
                    moreItem?.parameters?.length === 1 &&
                    moreItem?.parameters[0]?.key === 'obproxy_sys_password';
                  return (
                    <ProCard
                      className={styles.infoSubCard}
                      style={{ border: '1px solid #e2e8f3' }}
                      split="vertical"
                      key={moreItem.label}
                    >
                      <Table
                        className={`${styles.infoCheckTable}  ob-table`}
                        columns={getMoreColumns(moreItem.label)}
                        dataSource={moreItem?.parameters}
                        pagination={false}
                        scroll={{ y: 300 }}
                        rowKey="key"
                      />
                    </ProCard>
                  );
                })}
              </Space>
            ) : null}
          </ProCard>
        ))}
      </Row>
    </ProCard>
  );
}
