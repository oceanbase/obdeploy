import CustomFooter from '@/component/CustomFooter';
import { DEL_STATUS_MAP, NO_CONNECT_COMP_STATUS } from '@/constant';
import type { SelectedComponent } from '@/models/componentUninstall';
import {
  componentChangeDelComponent,
  componentChangeDelComponentTask,
  componentChangeNodeCheck2,
  componentChangeTask2,
  removeComponent,
} from '@/services/component-change/componentChange';
import { getErrorInfo, handleQuit } from '@/utils';
import { intl } from '@/utils/intl';
import { requestPipeline } from '@/utils/useRequest';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  ExclamationCircleFilled,
  ExclamationCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { getLocale, useModel } from '@umijs/max';
import { useRequest } from 'ahooks';
import {
  Badge,
  Button,
  message,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Table,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { pick } from 'lodash';
import { useEffect, useState } from 'react';
import {
  componentsConfig,
  componentVersionTypeToComponent,
} from '../constants';

import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

enum Result {
  SUCCESSFUL = 'SUCCESSFUL',
  FAILED = 'FAILED',
  RUNNING = 'RUNNING',
}

enum ServersCheckType {
  CHECKING = 'CHECKING',
  ERROR = 'ERROR',
  SUCCESSFUL = 'SUCCESSFUL',
}

enum DeleteStatus {
  ERROR = 'ERROR',
  DELETING = 'DELETING',
  SUCCESSFUL = 'SUCCESSFUL',
  PENDING = 'PENDING',
}

enum TaskStatus {
  SUCCESSFUL = 'SUCCESSFUL',
  FAILED = 'FAILED',
  RUNNING = 'RUNNING',
  PENDING = 'PENDING',
}

type DataSourceItem = {
  component: string;
  version: string;
  node: string;
  serversCheck: ServersCheckType;
  status: TaskStatus;
  result?: Result;
  deleteStatus: DeleteStatus; // 移除状态，只有连通性检查不通过时会用上
  log?: any;
};

const getInitialData = (
  selectedComponents: SelectedComponent[],
): DataSourceItem[] => {
  return selectedComponents.map((comp) => ({
    component: comp.component_name,
    version: comp.version,
    node: comp.node,
    serversCheck: ServersCheckType.CHECKING,
    status: TaskStatus.PENDING,
    deleteStatus: DeleteStatus.PENDING,
  }));
};

export default function Uninstall() {
  const { selectedCluster, selectedComponents, setCurrent } =
    useModel('componentUninstall');
  const { setErrorVisible, setErrorsList, errorsList, handleQuitProgress } =
    useModel('global');
  const componentNames = selectedComponents.map((item) => item.component_name);
  const [unInstallResult, setUnInstallResult] = useState('RUNNING');
  const [dataSource, setDataSource] = useState<DataSourceItem[]>(
    getInitialData(selectedComponents),
  );

  const { run: checkNode } = useRequest(componentChangeNodeCheck2, {
    manual: true,
    onSuccess: ({ success, data }) => {
      if (success) {
        setDataSource((preState) =>
          preState.map((item) => ({
            ...item,
            status: TaskStatus.RUNNING,
            serversCheck:
              data?.components_server.find(
                (checkItem) => checkItem.component_name === item.component,
              )?.failed_servers.length === 0
                ? ServersCheckType.SUCCESSFUL
                : ServersCheckType.ERROR, // failed_servers 为空数组表示连通性测试通过
          })),
        );
        const checkPassedComp = componentNames.filter((comp) => {
          const tempComp = data?.components_server.find(
            (item) => item.component_name === comp,
          );
          return tempComp?.failed_servers.length === 0 ? true : false;
        });
        if (checkPassedComp.length) {
          delComponent({
            name: selectedCluster?.name!,
            component_name: checkPassedComp,
            force: false,
          });
        }
      }
    },
    onError: (e) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });
  const { run: delComponent } = useRequest(componentChangeDelComponent, {
    manual: true,
    onSuccess: ({ success }) => {
      if (success) {
        getTask({ name: selectedCluster?.name! });
        getLog({
          name: selectedCluster?.name!,
          component_name: componentNames,
        });
      }
    },
    onError: (e) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const {
    run: getTask,
    refresh,
    data: taskData,
  } = useRequest(componentChangeTask2, {
    manual: true,
    onSuccess: ({ success, data }) => {
      if (success) {
        setUnInstallResult(data?.status);
        if (data?.status === TaskStatus.RUNNING) {
          setTimeout(() => {
            refresh();
          }, 500);
        } else {
          setDataSource((preState) => {
            const result = preState.map((preItem: any) => {
              const comp = data?.info?.find(
                (item) => item.component === preItem.component,
              );
              return comp
                ? {
                    ...preItem,
                    status: comp?.status,
                    result: comp?.result,
                    deleteStatus:
                      comp?.result === Result.FAILED
                        ? DeleteStatus.ERROR
                        : DeleteStatus.SUCCESSFUL,
                  }
                : preItem;
            });
            return result;
          });
        }
      }
    },
    onError: (e) => {
      if (!requestPipeline.processExit) {
        setTimeout(() => {
          refresh();
        }, 500);
      }
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const { run: getLog, refresh: reGetLog } = useRequest(
    componentChangeDelComponentTask,
    {
      manual: true,
      onSuccess: ({ success, data }) => {
        if (success) {
          setDataSource((preState) =>
            preState.map((preItem: any) => ({
              ...preItem,
              log: data?.items.find(
                (item) => item.component_name === preItem.component,
              )?.log,
            })),
          );
          if (unInstallResult === 'RUNNING') {
            setTimeout(() => {
              reGetLog();
            }, 500);
          }
        }
      },
      onError: (e) => {
        if (
          !requestPipeline.processExit &&
          taskData?.data?.status === TaskStatus.RUNNING
        ) {
          setTimeout(() => {
            reGetLog();
          }, 500);
        }
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  // 初始化某个组件的状态
  const initialComp = (compnentName: string) => {
    setDataSource((preDataSource) => {
      return preDataSource.map((item) => {
        if (item.component === compnentName) {
          return {
            ...pick(item, ['component', 'version', 'node', 'serversCheck']),
            status: TaskStatus.RUNNING,
            deleteStatus: DeleteStatus.DELETING,
            result: Result.RUNNING,
          };
        }
        return item;
      });
    });
  };

  const retryDelComp = (compnentName: string) => {
    initialComp(compnentName);
    delComponent({
      name: selectedCluster!.name,
      component_name: [compnentName],
      force: false,
    });
  };
  const forceDelComp = (compnentName: string) => {
    initialComp(compnentName);
    delComponent({
      name: selectedCluster!.name,
      component_name: [compnentName],
      force: true,
    });
  };

  // 强制移除
  const { run: removeComp } = useRequest(removeComponent, {
    manual: true,
    onSuccess: ({ success, data }, params) => {
      //强制移除失败
      let deleteStatus =
        !data || !success ? DeleteStatus.ERROR : DeleteStatus.SUCCESSFUL;
      if (deleteStatus === DeleteStatus.ERROR) {
        message.error(
          intl.formatMessage({
            id: 'OBD.pages.ComponentUninstall.Uninstall.ForcedRemovalFailed',
            defaultMessage: '强制移除失败',
          }),
        );
      }

      setDataSource((preState) =>
        preState.map((preItem) => {
          if (preItem.component === params[0]?.components[0]) {
            return {
              ...preItem,
              status:
                deleteStatus === DeleteStatus.ERROR
                  ? TaskStatus.FAILED
                  : TaskStatus.SUCCESSFUL,
              deleteStatus,
            };
          }
          return { ...preItem };
        }),
      );
    },
    onError: (e) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const ViewLog = ({ log }: { log: string }) => {
    return (
      <Tooltip
        color="#ffffff"
        overlayStyle={{ overflow: 'visible' }}
        overlayClassName={styles.viewLogContent}
        overlayInnerStyle={{
          width: 520,
          height: 400,
          color: '#132039',
          overflow: 'scroll',
          overflowX: 'hidden',
          padding: '16px 16px 0px 16px',
          backgroundColor: 'black',
        }}
        title={
          <pre style={{ overflow: 'auto', marginBottom: 0 }}>{log || ''}</pre>
        }
      >
        <Button style={{ paddingLeft: 0 }} type="link">
          {intl.formatMessage({
            id: 'OBD.pages.ComponentUninstall.Uninstall.ViewRunningLogs',
            defaultMessage: '查看运行日志',
          })}
        </Button>
      </Tooltip>
    );
  };
  const getColumns = (): ColumnsType<DataSourceItem> => {
    return [
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.Uninstall.Component',
          defaultMessage: '组件',
        }),
        dataIndex: 'component',
        render: (compnentName) => (
          <span>
            {
              componentsConfig[
                componentVersionTypeToComponent[compnentName] || compnentName
              ]?.showComponentName
            }
          </span>
        ),
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.Uninstall.Version',
          defaultMessage: '版本',
        }),
        dataIndex: 'version',
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.Uninstall.Node',
          defaultMessage: '节点',
        }),
        dataIndex: 'node',
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.Uninstall.Connectivity',
          defaultMessage: '连通性',
        }),
        dataIndex: 'serversCheck',
        render: (serversCheck: ServersCheckType) => {
          if (serversCheck === ServersCheckType.ERROR) {
            return (
              <div>
                <CloseCircleFilled
                  style={{
                    color: '#ff6a80',
                    marginRight: 6,
                  }}
                />

                {intl.formatMessage({
                  id: 'OBD.pages.ComponentUninstall.Uninstall.UnableToConnect',
                  defaultMessage: '无法连接',
                })}
              </div>
            );
          }
          if (serversCheck === ServersCheckType.CHECKING) {
            return (
              <div>
                <Spin
                  style={{ marginRight: 6 }}
                  indicator={<LoadingOutlined spin />}
                  size="small"
                />
                {intl.formatMessage({
                  id: 'OBD.pages.ComponentUninstall.Uninstall.Checking',
                  defaultMessage: '检查中',
                })}
              </div>
            );
          }
          if (serversCheck === ServersCheckType.SUCCESSFUL) {
            return (
              <div>
                <CheckCircleFilled
                  style={{ color: '#0ac185', marginRight: 6 }}
                />

                {intl.formatMessage({
                  id: 'OBD.pages.ComponentUninstall.Uninstall.Normal',
                  defaultMessage: '正常',
                })}
              </div>
            );
          }
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.Uninstall.UninstallStatus',
          defaultMessage: '卸载状态',
        }),
        dataIndex: 'status',
        render: (val: TaskStatus, record) => {
          return (
            <div className={styles.delStatusContainer}>
              {record.serversCheck === ServersCheckType.ERROR ? (
                <>
                  <Badge
                    status={NO_CONNECT_COMP_STATUS[record.deleteStatus]?.status}
                  />

                  <span style={{ marginLeft: 8, marginRight: 5 }}>
                    {NO_CONNECT_COMP_STATUS[record.deleteStatus]?.text || '-'}
                  </span>
                  {record.deleteStatus === DeleteStatus.ERROR ||
                  record.deleteStatus === DeleteStatus.PENDING ? (
                    <Tooltip
                      title={intl.formatMessage(
                        {
                          id: 'OBD.pages.ComponentUninstall.Uninstall.NodeRecordnodeCannotBeAccessed',
                          defaultMessage:
                            '节点 {recordNode} 无法访问，相关组件无法被卸载，请登录本节点自行处理，或者进行强制移除',
                        },
                        { recordNode: record.node },
                      )}
                    >
                      <ExclamationCircleFilled style={{ color: '#ffac33' }} />
                    </Tooltip>
                  ) : null}
                </>
              ) : (
                <>
                  <Badge
                    status={
                      DEL_STATUS_MAP[val]?.status ||
                      DEL_STATUS_MAP[record.result].status
                    }
                  />

                  <span style={{ marginLeft: 8 }}>
                    {DEL_STATUS_MAP[val]?.text ||
                      DEL_STATUS_MAP[record.result].text ||
                      '-'}
                  </span>
                </>
              )}
            </div>
          );
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.Uninstall.Operation',
          defaultMessage: '操作',
        }),
        width: 284,
        render: (_, record) => {
          // 无法连接
          if (record.serversCheck === ServersCheckType.ERROR) {
            if (
              record.deleteStatus === DeleteStatus.ERROR ||
              record.deleteStatus === DeleteStatus.PENDING
            ) {
              return (
                <Popconfirm
                  title={
                    <div style={{ width: 229 }}>
                      {intl.formatMessage({
                        id: 'OBD.pages.ComponentUninstall.Uninstall.AreYouSureYouWant',
                        defaultMessage:
                          '确定要强制移除吗？系统仅去除 OceanBase 数据库与组件之间的依赖关系，不会在主机端卸载本组件。',
                      })}
                    </div>
                  }
                  okText={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.Uninstall.Ok',
                    defaultMessage: '确定',
                  })}
                  cancelText={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.Uninstall.Cancel',
                    defaultMessage: '取消',
                  })}
                  onConfirm={() =>
                    removeComp({
                      name: selectedCluster?.name!,
                      components: [record.component],
                    })
                  }
                >
                  <Button
                    disabled={record.deleteStatus === DeleteStatus.ERROR}
                    style={{ paddingLeft: 0 }}
                    type="link"
                  >
                    {intl.formatMessage({
                      id: 'OBD.pages.ComponentUninstall.Uninstall.ForceRemoval',
                      defaultMessage: '强制移除',
                    })}
                  </Button>
                </Popconfirm>
              );
            }
            return '-';
          }
          if (record.status === TaskStatus.PENDING) return '-';
          if (record.result === Result.FAILED)
            return (
              <Space>
                <ViewLog log={record.log} />
                <Popconfirm
                  title={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.Uninstall.AreYouSureYouWant.1',
                    defaultMessage: '确定要重试卸载此组件吗？',
                  })}
                  okText={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.Uninstall.Ok',
                    defaultMessage: '确定',
                  })}
                  cancelText={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.Uninstall.Cancel',
                    defaultMessage: '取消',
                  })}
                  onConfirm={() => retryDelComp(record.component)}
                >
                  <Button type="link">
                    {intl.formatMessage({
                      id: 'OBD.pages.ComponentUninstall.Uninstall.Retry',
                      defaultMessage: '重试',
                    })}
                  </Button>
                </Popconfirm>
                <Popconfirm
                  okText={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.Uninstall.Ok',
                    defaultMessage: '确定',
                  })}
                  cancelText={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.Uninstall.Cancel',
                    defaultMessage: '取消',
                  })}
                  title={intl.formatMessage({
                    id: 'OBD.pages.ComponentUninstall.Uninstall.AreYouSureYouWant.2',
                    defaultMessage: '确定要强制卸载此组件吗？',
                  })}
                  onConfirm={() => forceDelComp(record.component)}
                >
                  <Button type="link">
                    {intl.formatMessage({
                      id: 'OBD.pages.ComponentUninstall.Uninstall.ForceUninstall',
                      defaultMessage: '强制卸载',
                    })}
                  </Button>
                </Popconfirm>
              </Space>
            );

          if (record.status === TaskStatus.RUNNING)
            return <ViewLog log={record.log} />;
          if (record.result === Result.SUCCESSFUL)
            return <ViewLog log={record.log} />;
        },
      },
    ];
  };

  const handleFinished = () => {
    Modal.confirm({
      title: intl.formatMessage({
        id: 'OBD.pages.ComponentUninstall.Uninstall.DoYouWantToExit',
        defaultMessage: '是否要退出页面？',
      }),
      okText: intl.formatMessage({
        id: 'OBD.pages.ComponentUninstall.Uninstall.Exit',
        defaultMessage: '退出',
      }),
      cancelText: intl.formatMessage({
        id: 'OBD.pages.ComponentUninstall.Uninstall.Cancel',
        defaultMessage: '取消',
      }),
      okButtonProps: { type: 'primary', danger: true },
      content: intl.formatMessage({
        id: 'OBD.pages.ComponentUninstall.Uninstall.BeforeExitingMakeSureThat',
        defaultMessage: '退出前，请确保已完成卸载操作。',
      }),
      icon: <ExclamationCircleOutlined style={{ color: '#ff4b4b' }} />,
      onOk: () => {
        handleQuit(handleQuitProgress, setCurrent, true, 3);
      },
    });
  };

  // 检查是否存在卸载中、待卸载、移除中的状态的组件
  const checkDataStatus = () => {
    return dataSource.some(
      (item) =>
        item.deleteStatus === DeleteStatus.DELETING ||
        item.result === Result.RUNNING ||
        item.result === Result.FAILED ||
        item.status === TaskStatus.RUNNING ||
        item.status === TaskStatus.PENDING,
    );
  };

  useEffect(() => {
    if (selectedCluster && selectedComponents.length) {
      checkNode({
        name: selectedCluster?.name!,
        component_name: componentNames,
      });
    }
  }, []);

  return (
    <div id="delContainer" className={styles.deleteContainer}>
      <ProCard
        title={intl.formatMessage({
          id: 'OBD.pages.ComponentUninstall.Uninstall.UninstallComponents',
          defaultMessage: '卸载组件',
        })}
        bodyStyle={{ paddingBottom: 24 }}
      >
        <Table
          columns={getColumns()}
          rowKey={'component'}
          dataSource={dataSource}
          pagination={false}
        />
      </ProCard>
      <CustomFooter>
        <Button
          style={{ height: 36, width: 80 }}
          disabled={checkDataStatus()}
          onClick={handleFinished}
          type="primary"
        >
          {intl.formatMessage({
            id: 'OBD.pages.ComponentUninstall.Uninstall.Complete',
            defaultMessage: '完成',
          })}
        </Button>
      </CustomFooter>
    </div>
  );
}
