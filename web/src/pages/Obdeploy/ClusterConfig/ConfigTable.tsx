import { pathReg } from '@/pages/constants';
import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import { Form, Space, Spin, Table, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { getLocale } from 'umi';
import EnStyles from '../indexEn.less';
import ZhStyles from '../indexZh.less';
import Parameter from './Parameter';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export type RulesDetail = {
  targetTable?:
    | 'oceanbase-ce'
    | 'obproxy-ce'
    | 'ocp-express'
    | 'obagent'
    | 'ob-configserver';
  rules: any;
  targetColumn?: string;
};
interface ConfigTableProps {
  showVisible: boolean;
  dataSource: API.NewParameterMeta[];
  loading: boolean;
  customParameter?: JSX.Element;
  parameterRules?: RulesDetail[] | RulesDetail;
}

export const parameterValidator = (_: any, value?: API.ParameterValue) => {
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
  rulesList?: RulesDetail[],
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
        const { defaultValue, defaultUnit } = record.parameterValue;
        let rules = [() => ({ validator: parameterValidator })];
        const param = {
          defaultValue,
        };
        if (defaultUnit) param.defaultUnit = defaultUnit;
        if (rulesList?.length) {
          const targetRuleDetail = rulesList.find(
            (item) => item.targetColumn === record.name,
          );
          if (targetRuleDetail) rules = targetRuleDetail.rules;
        }
        if (record.name === 'log_dir') {
          rules.push(() => ({
            validator: (_, value) => {
              if (pathReg.test(value?.value || '') || value?.adaptive) {
                return Promise.resolve();
              }
              return Promise.reject(
                intl.formatMessage({
                  id: 'OBD.pages.constants.AnAbsolutePathThatStarts.1',
                  defaultMessage:
                    '以 “/” 开头的绝对路径，只能包含字母、数字和特殊字符（-_:@/.）',
                }),
              );
            },
          }));
        }
        return (
          <Form.Item
            validateFirst={true}
            className={styles.inlineFormItem}
            name={[componentKey, 'parameters', record.name || '', 'params']}
            rules={rules}
          >
            <Parameter {...param} />
          </Form.Item>
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
/**
 *
 * @param parameterRules
 * 用于动态自定义某些字段的校验规则 RulesDetail | RulesDetail[]
 * 涉及到多个table需要传数组，rule需要通过targetTable字段映射到对应的table
 */
export default function ConfigTable({
  showVisible,
  dataSource,
  loading,
  parameterRules,
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
            {/* moreItem表示某一个组件,如 obproxy、ocp-express */}
            {dataSource.map((moreItem) => {
              // 每一项表示组件中的某一个参数的rules
              let rulesList: RulesDetail[] = [];
              if (parameterRules) {
                if (Array.isArray(parameterRules)) {
                  rulesList = parameterRules.filter(
                    (item) => item.targetTable === moreItem.component,
                  );
                } else {
                  rulesList.push(parameterRules);
                }
              }
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
                      rulesList,
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
