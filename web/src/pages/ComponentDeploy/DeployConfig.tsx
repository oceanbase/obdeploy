import CustomFooter from '@/component/CustomFooter';
import SelectCluster from '@/component/SelectCluster';
import { useComponents } from '@/hooks/useComponents';
import { componentChangeDeploymentsInfo } from '@/services/component-change/componentChange';
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
import { componentVersionTypeToComponent } from '../constants';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface DeployConfigProps {
  clusterList?: API.DataListDeployName_;
}

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
        // 切换集群  全选
        // 组件挂载 如果有选择的组件就不重新选 如果没有选择的组件全选
        if (undeployedComponents && !selectedConfig.length)
          setSelectedConfig(undeployedComponents);
      }
    },
  });

  const componentsList = componentsListRes?.data;

  const getColumns = (component: API.BestComponentInfo) => {
    const targetComponent = componentsGroupInfo.find((comp) =>
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
        render: (text) => {
          return (
            <span>
              {targetComponent?.content[0].name || text}
              {deployed
                ? intl.formatMessage({
                    id: 'OBD.pages.ComponentDeploy.DeployConfig.Deployed',
                    defaultMessage: '（已部署）',
                  })
                : null}
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
   * tip:如果选择 OCPExpress，则 OBAgent 则自动选择，无需提示
   * 如果不选择 OBAgent, 则 OCPExpress 则自动不选择，无需提示
   */
  const handleSelect = (
    record: { component_name: string },
    selected: boolean,
  ) => {
    if (!selected) {
      const newConfig = [];
      let target = false;
      target =
        record.component_name === 'obagent' &&
        selectedConfig.includes('ocp-express');
      for (const val of selectedConfig) {
        if (target && val === 'ocp-express') continue;
        if (val !== record.component_name) {
          newConfig.push(val);
        }
      }
      setSelectedConfig(newConfig);
    } else {
      if (
        record.component_name === 'ocp-express' &&
        !selectedConfig.includes('obagent')
      ) {
        setSelectedConfig([
          ...selectedConfig,
          record.component_name,
          'obagent',
        ]);
      } else {
        setSelectedConfig([...selectedConfig, record.component_name]);
      }
    }
  };

  const preStep = () => {
    history.push('/guide');
  };

  const nextStep = () => {
    const selectedComponent = componentsList?.component_list.filter(
      (component) => selectedConfig.includes(component.component_name),
    );
    if (selectedComponent) {
      let tempConfig: API.ComponentChangeConfig = {};
      for (let selector of selectedComponent) {
        tempConfig[
          componentVersionTypeToComponent[selector.component_name] ||
            selector.component_name
        ] = {
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
      selectedConfig.includes(comp.component_name),
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
              componentsList?.component_list.map((component, index) => (
                <Space key={index} className={styles.spaceWidth}>
                  <ProCard
                    style={component.deployed ? { paddingLeft: 48 } : {}}
                    type="inner"
                    className={`${styles.componentCard}`}
                  >
                    <Table
                      rowSelection={
                        component.component_name !== 'prometheus' &&
                        component.component_name !== 'grafana' &&
                        !component.deployed
                          ? {
                              hideSelectAll: true,
                              selectedRowKeys: selectedConfig,
                              onSelect: handleSelect,
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
            disabled={selectedConfig.length === 0}
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
