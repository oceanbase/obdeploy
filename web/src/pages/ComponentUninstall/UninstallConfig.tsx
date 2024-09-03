import CustomFooter from '@/component/CustomFooter';
import SelectCluster from '@/component/SelectCluster';
import { useComponents } from '@/hooks/useComponents';
import {
  componentChangeDepends,
  componentChangeDeploymentsInfo,
  componentChangeDeploymentsName,
} from '@/services/component-change/componentChange';
import { handleQuit } from '@/utils';
import { intl } from '@/utils/intl';
import { InfoCircleOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { getLocale, history, useModel } from '@umijs/max';
import { useRequest } from 'ahooks';
import { Button, Empty, Modal, Space, Spin, Table, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { pick, uniq } from 'lodash';
import { useEffect } from 'react';
import {
  componentVersionTypeToComponent,
  configServerComponent,
} from '../constants';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export default function UninstallConfig() {
  const { handleQuitProgress } = useModel('global');
  const {
    current,
    setCurrent,
    selectedCluster,
    setSelectedCluster,
    selectedComponents,
    setSelectedComponents,
  } = useModel('componentUninstall');
  const componentsGroupInfo = useComponents(true);
  const { data: clusterListsRes, loading } = useRequest(
    componentChangeDeploymentsName,
  );
  const { data: componentDependsRes, run: getCompDepends } = useRequest(
    componentChangeDepends,
    { manual: true },
  );
  const {
    data: componentsListRes,
    loading: componentsLoading,
    run: getComponents,
  } = useRequest(componentChangeDeploymentsInfo, {
    manual: true,
  });
  const clusterList = clusterListsRes?.data;
  const componentsList = componentsListRes?.data?.component_list;
  const componentDepends = componentDependsRes?.data?.items;

  const getColumns = (component: API.BestComponentInfo) => {
    const targetComponent = componentsGroupInfo.find((comp) =>
      comp.content.some(
        (item) =>
          item.key ===
            componentVersionTypeToComponent[component.component_name] ||
          item.key === component.component_name,
      ),
    );
    const columns: ColumnsType<any> = [
      {
        title: targetComponent?.group,
        dataIndex: 'component_name',
        width: 195,
        className: styles.firstContent,
        render: (text) => (
          <span> {targetComponent?.content[0].name || text}</span>
        ),
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.UninstallConfig.Version',
          defaultMessage: '版本',
        }),
        dataIndex: 'component_info',
        width: 130,
        render: () => (
          <div>
            {component.version}
            <Tag className="default-tag ml-8">
              {intl.formatMessage({
                id: 'OBD.pages.ComponentUninstall.UninstallConfig.Latest',
                defaultMessage: '最新',
              })}
            </Tag>
          </div>
        ),
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.UninstallConfig.DeployNodes',
          defaultMessage: '部署节点',
        }),
        dataIndex: 'node',
        render: () => (
          <div>
            {component.node}
            <a
              className={styles.learnMore}
              href={targetComponent?.content[0].doc}
              target="_blank"
            >
              {intl.formatMessage({
                id: 'OBD.pages.ComponentUninstall.UninstallConfig.LearnMore',
                defaultMessage: '了解更多',
              })}
            </a>
          </div>
        ),
      },
    ];

    return columns;
  };

  const getNeedSelectComps = (selectedCompNames: string[]) => {
    let res: string[] = [...selectedCompNames];
    for (let selector of selectedCompNames) {
      componentDepends?.forEach((item) => {
        if (
          item.component_name !== selector &&
          item.depends.includes(selector)
        ) {
          res.push(item.component_name);
        }
      });
    }
    res = uniq(res);
    if (res.length > selectedCompNames.length) {
      return getNeedSelectComps(res);
    }
    return res;
  };

  // 获取需要被取消勾选的组件
  const getUnneedselectComps = (unselectedCompNames: string[]): string[] => {
    let res = [...unselectedCompNames];
    for (let unselector of unselectedCompNames) {
      const depends =
        componentDepends?.find((item) => item.component_name === unselector)
          ?.depends || [];
      res.push(...depends);
    }
    res = uniq(
      res.filter((item) =>
        componentsList?.some((comp) => comp.component_name === item),
      ),
    );
    if (res.length > unselectedCompNames.length) {
      return getUnneedselectComps(res);
    }
    return res;
  };

  /**
   * @description
   * 选中某个组件后，如果该组件是另一个组件的依赖项，那这个组件也要被勾选上
   * 取消选中某个组件之后，则该组件依赖项也取消勾选
   * （比如： ocpexpress 依赖 obagent都处于勾选状态，现在不卸载 ocpexpress了，这样也不能卸载 obagent，因为 ocpexpress 还依赖 obagent）
   */
  const handleSelect = (record: API.BestComponentInfo, selected: boolean) => {
    if (selected) {
      const needSelectComps = getNeedSelectComps([record.component_name]);
      const comps = componentsList
        ?.filter(
          (comp) =>
            needSelectComps.includes(comp.component_name) &&
            // 选择的组件里不能包含已经选择了的组件
            !selectedComponents.some(
              (item) => item.component_name === comp.component_name,
            ),
        )
        .map((item) => pick(item, ['component_name', 'version', 'node']));
      setSelectedComponents([...selectedComponents, ...comps]);
    } else {
      const unneedSelectComps = getUnneedselectComps([record.component_name]);

      setSelectedComponents((curState) => {
        return [
          ...curState.filter(
            (item) => !unneedSelectComps.includes(item.component_name),
          ),
        ];
      });
    }
  };

  const preStep = () => {
    history.push('/guide');
  };
  const nextStep = () => {
    if (selectedCluster && selectedComponents.length) {
      setCurrent(current + 1);
    }
  };
  const handleUnInstall = () => {
    Modal.confirm({
      title: intl.formatMessage({
        id: 'OBD.pages.ComponentUninstall.UninstallConfig.AreYouSureYouWant',
        defaultMessage: '确认要卸载选择的组件吗？',
      }),
      okText: intl.formatMessage({
        id: 'OBD.pages.ComponentUninstall.UninstallConfig.Ok',
        defaultMessage: '确定',
      }),
      cancelText: intl.formatMessage({
        id: 'OBD.pages.ComponentUninstall.UninstallConfig.Cancel',
        defaultMessage: '取消',
      }),
      okButtonProps: { type: 'primary', danger: true },
      onOk: nextStep,
    });
  };

  const selectClusterChange = (val: string) => {
    try {
      setSelectedCluster(val ? JSON.parse(val) : undefined);
    } catch (e) {
      console.error(e);
    }
  };
  useEffect(() => {
    if (selectedCluster) {
      setSelectedComponents([]);
      getComponents({ name: selectedCluster.name });
      getCompDepends({ name: selectedCluster.name });
    }
  }, [selectedCluster]);

  return (
    <Spin spinning={loading || componentsLoading}>
      <Space className={styles.spaceWidth} direction="vertical" size="middle">
        <ProCard className={styles.pageCard} split="horizontal">
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.ComponentUninstall.UninstallConfig.UnloadObjects',
              defaultMessage: '卸载对象',
            })}
            bodyStyle={{ paddingBottom: 16 }}
            className="card-padding-bottom-24"
          >
            <SelectCluster
              value={selectedCluster}
              onChange={selectClusterChange}
              options={clusterList?.items}
            />
          </ProCard>
          <ProCard
            title={
              <>
                {
                  <span>
                    {intl.formatMessage({
                      id: 'OBD.pages.ComponentUninstall.UninstallConfig.SelectUninstallComponent',
                      defaultMessage: '选择卸载组件',
                    })}
                  </span>
                }

                <span className={styles.titleExtra}>
                  <InfoCircleOutlined style={{ marginRight: 4 }} />
                  {intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.UninstallConfig.ByDefaultComponentsWithDependencies',
                    defaultMessage: '系统会默认卸载存在相互依赖关系的组件',
                  })}
                </span>
              </>
            }
            className="card-header-padding-top-0 card-padding-bottom-24  card-padding-top-0"
          >
            {componentsList ? (
              componentsList.filter((item) => item.deployed).length ? (
                componentsList
                  .filter((item) => item.deployed)
                  .map((component, index) => (
                    <Space key={index} className={styles.spaceWidth}>
                      <ProCard type="inner" className={styles.componentCard}>
                        <Table
                          rowSelection={{
                            hideSelectAll: true,
                            selectedRowKeys: selectedComponents.map(
                              (comp) => comp.component_name,
                            ),
                            onSelect: handleSelect,
                            getCheckboxProps: (record) => ({
                              disabled:
                                record.component_name === configServerComponent,
                            }),
                            renderCell: (
                              checked,
                              record,
                              index,
                              originNode,
                            ) => {
                              if (
                                record.component_name === configServerComponent
                              ) {
                                return (
                                  <Tooltip
                                    title={intl.formatMessage({
                                      id: 'OBD.pages.ComponentUninstall.UninstallConfig.CurrentlyConfigserverCannotBeUninstalled',
                                      defaultMessage:
                                        '暂不支持卸载 configserver',
                                    })}
                                  >
                                    {originNode}
                                  </Tooltip>
                                );
                              }
                              return originNode;
                            },
                          }}
                          rowKey="component_name"
                          columns={getColumns(component)}
                          className={styles.componentTable}
                          dataSource={[component]}
                          pagination={false}
                        />
                      </ProCard>
                    </Space>
                  ))
              ) : (
                <div className={styles.emptyContent}>
                  <Empty
                    imageStyle={{ height: 48 }}
                    description={intl.formatMessage({
                      id: 'OBD.pages.ComponentUninstall.UninstallConfig.NoComponentsAvailable',
                      defaultMessage: '暂无可用组件',
                    })}
                  />
                </div>
              )
            ) : (
              <div className={styles.emptyContent}>
                <Empty
                  imageStyle={{ height: 48 }}
                  description={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.UninstallConfig.SelectAClusterFirst',
                    defaultMessage: '请先选择集群',
                  })}
                />
              </div>
            )}
          </ProCard>
        </ProCard>
        <CustomFooter>
          <Button
            onClick={() => handleQuit(handleQuitProgress, setCurrent, false, 3)}
          >
            {intl.formatMessage({
              id: 'OBD.pages.ComponentUninstall.UninstallConfig.Exit',
              defaultMessage: '退出',
            })}
          </Button>
          <Button onClick={preStep}>
            {intl.formatMessage({
              id: 'OBD.pages.ComponentUninstall.UninstallConfig.PreviousStep',
              defaultMessage: '上一步',
            })}
          </Button>
          <Button
            disabled={selectedComponents.length === 0 || !selectedCluster}
            type="primary"
            onClick={handleUnInstall}
          >
            {intl.formatMessage({
              id: 'OBD.pages.ComponentUninstall.UninstallConfig.Uninstall',
              defaultMessage: '卸载',
            })}
          </Button>
        </CustomFooter>
      </Space>
    </Spin>
  );
}
