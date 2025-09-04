import CustomFooter from '@/component/CustomFooter';
import ErrorCompToolTip from '@/component/ErrorCompToolTip';
import SelectCluster from '@/component/SelectCluster';
import { useComponents } from '@/hooks/useComponents';
import { componentChangeDeploymentsInfo } from '@/services/component-change/componentChange';
import { queryAllComponentVersions } from '@/services/ob-deploy-web/Components';
import { checkLowVersion, handleQuit } from '@/utils';
import { intl } from '@/utils/intl';
import { InfoCircleOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { getLocale, history, useModel } from '@umijs/max';
import { useRequest, useUpdateEffect } from 'ahooks';
import { Button, Empty, Space, Spin, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useEffect, useState } from 'react';
import DataEmpty from '../../.././/public/assets/data-empty.svg';
import { alertManagerComponent, componentVersionTypeToComponent, configServerComponent, grafanaComponent, obagentComponent, prometheusComponent } from '../constants';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';
const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface DeployConfigProps {
  clusterList?: API.DataListDeployName_;
}

type rowDataType = {
  key: string;
  name: string;
  component_name: string;
  onlyAll: boolean;
  desc: string;
  doc: string;
};

export default function DeployConfig({ clusterList }: DeployConfigProps) {
  const {
    componentConfig,
    setComponentConfig,
    setCurrent,
    current,
    setDeployUser,
    setLowVersion,
    selectedConfig,
    setSelectedConfig,
    selectedCluster,
    setSelectedCluster,
    setDeployedComps,
  } = useModel('componentDeploy');
  const { handleQuitProgress } = useModel('global');
  const componentsGroupInfo = useComponents(true);
  const [memorySize, setMemorySize] = useState<number>(0);

  const {
    data: componentsListRes,
    run: getComponents,
    loading: compLoading,
  } = useRequest(componentChangeDeploymentsInfo, {
    manual: true,
    onSuccess: ({ success, data }) => {
      if (success) {
        setDeployedComps(
          data?.component_list
            .filter((comp) => comp.deployed)
            .map((comp) => comp.component_name) || [],
        );
        const undeployedComponents = data?.component_list
          .filter((item) => !item.deployed)
          .map((item) => item.component_name);
        // 切换集群时不清空已选择的组件，也不自动全选
        // 让用户手动选择需要的组件
      }
    },
  });

  const componentsList = componentsListRes?.data;

  // 获取当前所有的安装包
  const { data: allComponentVersions } = useRequest(
    queryAllComponentVersions,
    {},
  );

  const componentNameList = componentsList?.component_list?.map(
    (item) => item.component_name,
  );

  const realComponent = allComponentVersions?.data?.items?.map((item) => ({
    ...item,
    name:
      item.name === 'obproxy' && item?.info[0]?.version_type === 'ce'
        ? 'obproxy-ce'
        : item.name,
  }));

  const oceanbaseVersionsData = realComponent?.filter((item) =>
    componentNameList?.includes(item.name),
  );

  const getColumns = (component: API.BestComponentInfo) => {
    const targetComponent = componentsGroupInfo?.find((comp) =>
      comp.content.some(
        (item) =>
          item.key ===
          componentVersionTypeToComponent[component.component_name] ||
          item.key === component.component_name,
      ),
    );
    const { deployed } = component;
    const columns: ColumnsType<any> = [
      {
        title: targetComponent?.group,
        dataIndex: 'component_name',
        className: styles.firstCell,
        width: 160,
        render: (text, record) => {
          const UnableToObtainTheAvailable = oceanbaseVersionsData?.find(
            (i) => i.name === record.component_name,
          );
          return (
            <span>
              {targetComponent?.content[0].name || text}
              {deployed
                ? intl.formatMessage({
                  id: 'OBD.pages.ComponentDeploy.DeployConfig.Deployed',
                  defaultMessage: '（已部署）',
                })
                : null}
              {!UnableToObtainTheAvailable && !deployed ? (
                <ErrorCompToolTip
                  title={intl.formatMessage({
                    id: 'OBD.component.DeployConfig.UnableToObtainTheAvailable',
                    defaultMessage: '无法获取可用安装包',
                  })}
                  status="error"
                />
              ) : null}
            </span>
          );
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentDeploy.DeployConfig.Version',
          defaultMessage: '版本',
        }),
        className: styles.secondCell,
        dataIndex: 'component_info',
        width: 130,
        render: (component_info) => {
          return (
            <div style={{ height: '100%' }}>
              {deployed ? component.version : component_info[0]?.version}
              <Tag className="default-tag ml-8">
                {intl.formatMessage({
                  id: 'OBD.pages.ComponentDeploy.DeployConfig.Latest',
                  defaultMessage: '最新',
                })}
              </Tag>
            </div>
          );
        },
      },
      {
        title: deployed
          ? intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.DeployConfig.DeployNodes',
            defaultMessage: '部署节点',
          })
          : intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.DeployConfig.Description',
            defaultMessage: '描述',
          }),
        dataIndex: deployed ? 'node' : 'desc',
        className: styles.thirdCell,
        render: (_) => {
          return (
            <div className={styles.descContent}>
              <p style={{ maxWidth: 556, margin: '0 24px 0 0' }}>
                {deployed ? component.node : targetComponent?.content[0].desc}
              </p>
              <a
                className={styles.learnMore}
                href={targetComponent?.content[0].doc}
                target="_blank"
              >
                {intl.formatMessage({
                  id: 'OBD.pages.ComponentDeploy.DeployConfig.LearnMore',
                  defaultMessage: '了解更多',
                })}
              </a>{' '}
            </div>
          );
        },
      },
    ];

    return columns;
  };

  /**
 * tip:
 * 如果选择grafana/prometheus，则 OBAgent 则自动选择，无需提示
 * 如果选择 grafana，则 OBAgent&&prometheus 则自动选择，无需提示
 * 如果不选择 OBAgent, 则 grafana/prometheus 则自动不选择，无需提示
 * 用户取消勾选prometheus，granfana也取消掉
 */
  const handleSelect = (record: rowDataType, selected: boolean) => {
    if (!selected) {
      let newConfig = [],
        target = false;
      // 根据不同的组件类型，决定需要取消选择的相关组件
      let componentsToRemove: string[] = [];

      if (record.component_name === obagentComponent) {
        // 取消勾选obagent，grafana和prometheus也取消掉
        componentsToRemove = [obagentComponent, grafanaComponent, prometheusComponent];
      } else if (record.component_name === prometheusComponent) {
        // 取消勾选prometheus，grafana也取消掉，但alertmanager可以独立存在
        componentsToRemove = [prometheusComponent, grafanaComponent];
      } else if (record.component_name === alertManagerComponent) {
        // 取消勾选alertmanager，只取消掉自己
        componentsToRemove = [alertManagerComponent];
      } else if (record.component_name === grafanaComponent) {
        // 取消勾选grafana，只取消掉自己
        componentsToRemove = [grafanaComponent];
      } else if (record.component_name === configServerComponent) {
        // 取消勾选obconfigserver，只取消掉自己
        componentsToRemove = [configServerComponent];
      }

      // 保留不在取消列表中的组件
      for (let val of selectedConfig) {
        if (!componentsToRemove.includes(val)) {
          newConfig.push(val);
        }
      }
      setSelectedConfig(newConfig);
    } else {
      // 根据不同的组件类型，决定需要自动选择的相关组件
      let componentsToAdd: string[] = [record.component_name];

      if (record.component_name === prometheusComponent) {
        // 如果选择prometheus，则OBAgent自动选择
        if (!selectedConfig.includes(obagentComponent)) {
          componentsToAdd.push(obagentComponent);
        }
      } else if (record.component_name === grafanaComponent) {
        // 如果选择grafana，则OBAgent和prometheus自动选择
        if (!selectedConfig.includes(obagentComponent)) {
          componentsToAdd.push(obagentComponent);
        }
        if (!selectedConfig.includes(prometheusComponent)) {
          componentsToAdd.push(prometheusComponent);
        }
      } else if (record.component_name === alertManagerComponent) {
        // 如果选择alertmanager，只选择自己，不自动选择其他组件
        // 用户可以根据需要手动选择 Prometheus 和 OBAgent
        // componentsToAdd 已经包含了 record.component_name，无需额外处理
      }

      // 添加新选择的组件和依赖组件
      setSelectedConfig([...selectedConfig, ...componentsToAdd]);
    }
  };

  const preStep = () => {
    history.push('/guide');
  };
  // 排除缺少安装包的组件
  const UnableCom = oceanbaseVersionsData
    ?.filter((i) => selectedConfig?.includes(i.name))
    ?.map((item) => item.name) || [];


  const nextStep = () => {
    // 排除掉已部署的组件，只选择未部署的组件
    const deployedComponentsList = componentsList?.component_list?.filter(item => item.deployed !== 1)
    const selectedComponent = deployedComponentsList?.filter(
      (component) => selectedConfig?.includes(component.component_name),
    );

    if (selectedComponent) {
      let tempConfig: API.ComponentChangeConfig = {};
      for (let selector of selectedComponent) {
        const key = componentVersionTypeToComponent[selector.component_name] ||
          selector.component_name;
        tempConfig[key] = {
          component: selector.component_name,
          version: selector.component_info?.[0]?.version,
          package_hash: selector.component_info?.[0]?.md5,
          release: selector.component_info?.[0]?.release,
        };
      }
      Object.keys(componentConfig).forEach((key) => {
        if (tempConfig[key]) {
          tempConfig[key] = { ...tempConfig[key], ...componentConfig[key] };
        }
      });
      if (tempConfig.obagent) {
        tempConfig.obagent.servers = selectedCluster?.ob_servers || [];
      }
      setComponentConfig({
        ...tempConfig,
        appname: selectedCluster?.name,
        home_path: componentConfig?.home_path,
      });
    }
    setDeployUser(selectedCluster!.deploy_user);
    setCurrent(current + 1);
    window.scrollTo(0, 0);
  };

  const selectClusterChange = (val: string) => {
    try {
      setSelectedCluster(val ? JSON.parse(val) : undefined);
    } catch (e) {
      console.error(e);
    }
  };

  useUpdateEffect(() => {
    if (selectedCluster) {
      // 切换集群的时候需要重置选中的组件
      setSelectedConfig([]);
      setLowVersion(checkLowVersion(selectedCluster.ob_version));
      getComponents({ name: selectedCluster.name });
    }
  }, [selectedCluster]);

  useEffect(() => {
    if (selectedCluster) {
      setLowVersion(checkLowVersion(selectedCluster.ob_version));
      getComponents({ name: selectedCluster.name });
    }
  }, []);

  useEffect(() => {
    const tempComp = componentsList?.component_list.filter((comp) =>
      selectedConfig?.includes(comp.component_name),
    );
    if (tempComp?.length) {
      setMemorySize(
        tempComp
          .map((item) => item.component_info?.[0]?.estimated_size || 0)
          .reduce((pre, cur) => pre + cur),
      );
    } else if (tempComp?.length === 0) {
      setMemorySize(0);
    }
  }, [selectedConfig]);

  return (
    <Spin spinning={compLoading}>
      <Space
        className={`${styles.spaceWidth} ${styles.deployContent} `}
        direction="vertical"
        size="middle"
      >
        <ProCard className={styles.pageCard} split="horizontal">
          <ProCard
            title={
              <span style={{ color: '#132039' }}>
                {intl.formatMessage({
                  id: 'OBD.pages.ComponentDeploy.DeployConfig.DeployObjects',
                  defaultMessage: '部署对象',
                })}
              </span>
            }
            className="card-padding-bottom-16"
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
                <span style={{ color: '#132039' }}>
                  {intl.formatMessage({
                    id: 'OBD.pages.ComponentDeploy.DeployConfig.SelectDeploymentComponent',
                    defaultMessage: '选择部署组件',
                  })}
                </span>
                {componentsList?.component_list ? (
                  <span className={styles.titleExtra}>
                    <InfoCircleOutlined style={{ marginRight: 4 }} />
                    {intl.formatMessage(
                      {
                        id: 'OBD.pages.components.InstallConfig.EstimatedInstallationRequiresSizeMb',
                        defaultMessage: '预计安装需要 {size}MB 空间',
                      },
                      { size: (memorySize / (1 << 20)).toFixed(2) },
                    )}
                  </span>
                ) : null}
              </>
            }
            className="card-header-padding-top-0 card-padding-bottom-24  card-padding-top-0"
          >
            {componentsList?.component_list ? (
              [...componentsList.component_list].reverse().map((component, index) => (
                <Space key={index} className={styles.spaceWidth}>
                  <ProCard
                    style={component.deployed ? { paddingLeft: 48 } : {}}
                    type="inner"
                    className={`${styles.componentCard}`}
                  >
                    <Table
                      rowSelection={
                        !component.deployed
                          ? {
                            hideSelectAll: true,
                            // 使用用户实际选择的组件列表
                            selectedRowKeys: selectedConfig,
                            onSelect: handleSelect,
                            getCheckboxProps: (record) => ({
                              disabled: !oceanbaseVersionsData?.find(
                                (i) => i.name === record.component_name,
                              ),
                              name: record.component_name,
                            }),
                          }
                          : undefined
                      }
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
                  image={DataEmpty}
                  description={intl.formatMessage({
                    id: 'OBD.pages.ComponentDeploy.DeployConfig.SelectAClusterFirst',
                    defaultMessage: '请先选择集群',
                  })}
                />
              </div>
            )}
          </ProCard>
        </ProCard>
        <CustomFooter>
          <Button
            onClick={() => handleQuit(handleQuitProgress, setCurrent, false, 5)}
          >
            {intl.formatMessage({
              id: 'OBD.pages.ComponentDeploy.DeployConfig.Exit',
              defaultMessage: '退出',
            })}
          </Button>
          <Button onClick={preStep}>
            {intl.formatMessage({
              id: 'OBD.pages.ComponentDeploy.DeployConfig.PreviousStep',
              defaultMessage: '上一步',
            })}
          </Button>
          <Button
            disabled={selectedConfig?.length === 0}
            type="primary"
            onClick={nextStep}
          >
            {intl.formatMessage({
              id: 'OBD.pages.ComponentDeploy.DeployConfig.NextStep',
              defaultMessage: '下一步',
            })}
          </Button>
        </CustomFooter>
      </Space>
    </Spin>
  );
}
