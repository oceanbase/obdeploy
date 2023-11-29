import { Space, Table, Spin, Form, Tooltip, InputNumber } from 'antd';
import { ProCard, ProForm } from '@ant-design/pro-components';
import { getLocale } from 'umi';
import type { ColumnsType } from 'antd/es/table';

import { intl } from '@/utils/intl';
import Parameter from './Parameter';
import EnStyles from '../indexEn.less';
import ZhStyles from '../indexZh.less';
import { ReactElement } from 'react';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;
interface ConfigTableProps {
  showVisible: boolean;
  dataSource: API.NewParameterMeta[];
  loading: boolean;
  customParameter?: JSX.Element;
}

const parameterValidator = (_: any, value?: API.ParameterValue) => {
  if (value?.adaptive) {
    return Promise.resolve();
  } else if (value?.require && !value?.value) {
    return Promise.reject(
      new Error(
        intl.formatMessage({
          id: 'OBD.pages.components.ClusterConfig.RequiredForCustomParameters',
          defaultMessage: '自定义参数时必填',
        }),
      ),
    );
  }
  return Promise.resolve();
};

const getMoreColumns = (
  label: string,
  componentKey: string,
  customParameter?: JSX.Element,
) => {
  const columns: ColumnsType<API.NewConfigParameter> = [
    {
      title: label,
      dataIndex: 'name',
      width: 250,
      render: (text) => text || '-',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.Obdeploy.ClusterConfig.ConfigTable.ParameterValue',
        defaultMessage: '参数值',
      }),
      width: locale === 'zh-CN' ? 280 : 360,
      dataIndex: 'parameterValue',
      render: (parameterValue, record) => {
        return (
          <ProForm.Item
            className={styles.inlineFormItem}
            name={[componentKey, 'parameters', record.name || '', 'params']}
            // rules={[{ validator: parameterValidator }]}
          >
            <Parameter />
          </ProForm.Item>
        );
      },
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.ClusterConfig.Introduction',
        defaultMessage: '介绍',
      }),
      dataIndex: 'description',
      render: (text, record) =>
        text ? (
          <Form.Item
            className={styles.inlineFormItem}
            name={[
              componentKey,
              'parameters',
              record.name || '',
              'description',
            ]}
          >
            <Tooltip title={text}>
              <div className="ellipsis">{text}</div>
            </Tooltip>
          </Form.Item>
        ) : (
          '-'
        ),
    },
  ];

  return columns;
};

export default function ConfigTable({
  showVisible,
  dataSource,
  loading,
  customParameter,
}: ConfigTableProps) {
  return (
    <>
      {showVisible ? (
        <Spin spinning={loading}>
          <Space
            className={styles.spaceWidth}
            direction="vertical"
            size="middle"
            style={{ minHeight: 50, marginTop: 16 }}
          >
            {dataSource.map((moreItem) => {
              return (
                <ProCard
                  className={styles.infoSubCard}
                  style={{ border: '1px solid #e2e8f3' }}
                  split="vertical"
                  key={moreItem.component}
                >
                  <Table
                    className={`${styles.moreConfigTable} ob-table`}
                    columns={getMoreColumns(
                      moreItem.label,
                      moreItem.componentKey,
                      customParameter,
                    )}
                    rowKey="name"
                    dataSource={moreItem.configParameter}
                    scroll={{ y: 300 }}
                    pagination={false}
                  />
                </ProCard>
              );
            })}
          </Space>
        </Spin>
      ) : null}
    </>
  );
}
