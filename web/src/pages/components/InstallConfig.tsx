import { useEffect, useState, useRef } from 'react';
import { useModel } from 'umi';
import {
  Space,
  Button,
  Form,
  Tag,
  Table,
  Alert,
  Tooltip,
  Select,
  Modal,
  Spin,
  message,
} from 'antd';
import { ProCard, ProForm, ProFormText } from '@ant-design/pro-components';
import {
  CloseOutlined,
  SafetyCertificateFilled,
  InfoOutlined,
  InfoCircleOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import useRequest from '@/utils/useRequest';
import { queryAllComponentVersions } from '@/services/ob-deploy-web/Components';
import {
  queryDeploymentInfoByTaskStatusType,
  deleteDeployment,
} from '@/services/ob-deploy-web/Deployments';
import { listRemoteMirrors } from '@/services/ob-deploy-web/Mirror';
import { handleQuit, handleResponseError, checkLowVersion } from '@/utils';
import NP from 'number-precision';
import copy from 'copy-to-clipboard';
import DeployType from './DeployType';
import DeleteDeployModal from './DeleteDeployModal';
import {
  commonStyle,
  allComponentsName,
  oceanbaseComponent,
  obproxyComponent,
  ocpexpressComponent,
  obagentComponent,
} from '../constants';
import styles from './index.less';

interface FormValues {
  type?: string;
}

const appnameReg = /^[a-zA-Z]([a-zA-Z0-9]{0,19})$/;

const componentsGroupInfo = [
  {
    group: '数据库',
    key: 'database',
    content: [
      {
        key: oceanbaseComponent,
        name: 'OceanBase Database',
        onlyAll: false,
        desc: '是金融级分布式数据库，具备数据强一致、高扩展、高可用、高性价比、稳定可靠等特征。',
        doc: 'https://www.oceanbase.com/docs/oceanbase-database-cn',
      },
    ],
  },
  {
    group: '代理',
    key: 'agency',
    onlyAll: true,
    content: [
      {
        key: obproxyComponent,
        name: 'OBProxy',
        onlyAll: true,
        desc: '是 OceanBase 数据库专用的代理服务器，可以将用户 SQL 请求转发至最佳目标 OBServer 。',
        doc: 'https://www.oceanbase.com/docs/odp-enterprise-cn',
      },
    ],
  },
  {
    group: '工具',
    key: 'tool',
    onlyAll: true,
    content: [
      {
        key: ocpexpressComponent,
        name: 'OCPExpress',
        onlyAll: true,
        desc: '是专为 OceanBase 设计的管控平台，可实现对集群、租户的监控管理、诊断等核心能力。',
        doc: 'https://www.oceanbase.com/docs/common-oceanbase-database-cn-0000000001626262',
      },
      {
        key: obagentComponent,
        name: 'OBAgent',
        onlyAll: true,
        desc: '是一个监控采集框架。OBAgent 支持推、拉两种数据采集模式，可以满足不同的应用场景。',
        doc: 'https://www.oceanbase.com/docs/common-oceanbase-database-cn-10000000001576872',
      },
    ],
  },
];

const mirrors = ['oceanbase.community.stable', 'oceanbase.development-kit'];

export default function InstallConfig() {
  const {
    initAppName,
    setCurrentStep,
    configData,
    setConfigData,
    currentType,
    setCurrentType,
    lowVersion,
    isFirstTime,
    setIsFirstTime,
    isDraft,
    setIsDraft,
    componentsVersionInfo,
    setComponentsVersionInfo,
    handleQuitProgress,
    getInfoByName,
    setLowVersion,
  } = useModel('global');
  const { components, home_path } = configData || {};
  const { oceanbase } = components || {};
  const [existNoVersion, setExistNoVersion] = useState(false);
  const [obVersionValue, setOBVersionValue] = useState<string | undefined>(
    undefined,
  );
  const [hasDraft, setHasDraft] = useState(false);
  const [deleteLoadingVisible, setDeleteLoadingVisible] = useState(false);
  const [deleteName, setDeleteName] = useState('');
  const [installMemory, setInstallMemory] = useState(0);
  const [form] = ProForm.useForm();
  const [unavailableList, setUnavailableList] = useState<string[]>([]);
  const [componentLoading, setComponentLoading] = useState(false);
  const draftNameRef = useRef();

  const { run: fetchDeploymentInfo, loading } = useRequest(
    queryDeploymentInfoByTaskStatusType,
  );
  const { run: handleDeleteDeployment } = useRequest(deleteDeployment);
  const { run: fetchListRemoteMirrors } = useRequest(listRemoteMirrors, {
    skipStatusError: true,
    onSuccess: () => {
      setComponentLoading(false);
    },
    onError: ({ response, data }: any) => {
      if (response?.status === 503) {
        setTimeout(() => {
          fetchListRemoteMirrors();
        }, 1000);
      } else {
        if (response) {
          const errorInfo = data?.msg || data?.detail || response?.statusText;
          handleResponseError(errorInfo);
        }
        setComponentLoading(false);
      }
    },
  });

  const judgVersions = (type: string, source: API.ComponentsVersionInfo) => {
    if (type === 'all') {
      if (Object.keys(source).length !== allComponentsName.length) {
        setExistNoVersion(true);
      } else {
        setExistNoVersion(false);
      }
    } else {
      if (
        !(source?.[oceanbaseComponent] && source?.[oceanbaseComponent]?.version)
      ) {
        setExistNoVersion(true);
      } else {
        setExistNoVersion(false);
      }
    }
  };

  const { run: fetchAllComponentVersions, loading: versionLoading } =
    useRequest(queryAllComponentVersions, {
      skipStatusError: true,
      onSuccess: async ({
        success,
        data,
      }: API.OBResponseDataListComponent_) => {
        if (success) {
          const newComponentsVersionInfo = {};
          data?.items?.forEach((item) => {
            if (allComponentsName.includes(item.name)) {
              if (item?.info?.length) {
                const initVersionInfo = item?.info[0] || {};
                if (item.name === oceanbaseComponent) {
                  const newSelectedVersionInfo = item.info.filter(
                    (item) => item.md5 === oceanbase?.package_hash,
                  )?.[0];
                  const currentSelectedVersionInfo =
                    newSelectedVersionInfo || initVersionInfo;
                  setOBVersionValue(
                    `${currentSelectedVersionInfo?.version}-${currentSelectedVersionInfo?.release}-${currentSelectedVersionInfo?.md5}`,
                  );
                  newComponentsVersionInfo[item.name] = {
                    ...currentSelectedVersionInfo,
                    dataSource: item.info || [],
                  };
                } else {
                  newComponentsVersionInfo[item.name] = {
                    ...initVersionInfo,
                    dataSource: item.info || [],
                  };
                }
              }
            }
          });

          const noVersion =
            Object.keys(newComponentsVersionInfo).length !==
            allComponentsName.length;
          judgVersions(currentType, newComponentsVersionInfo);
          setComponentsVersionInfo(newComponentsVersionInfo);

          if (noVersion) {
            const { success: mirrorSuccess, data: mirrorData } =
              await fetchListRemoteMirrors();
            if (mirrorSuccess) {
              const nameList: string[] = [];
              if (mirrorData?.total < 2) {
                const mirrorName = mirrorData?.items?.map(
                  (item: API.Mirror) => item.section_name,
                );
                const noDataName = [...mirrorName, ...mirrors].filter(
                  (name) =>
                    mirrors.includes(name) && !mirrorName.includes(name),
                );
                noDataName.forEach((name) => {
                  nameList.push(name);
                });
              }
              if (mirrorData?.total) {
                mirrorData?.items?.forEach((item: API.Mirror) => {
                  if (!item.available) {
                    nameList.push(item.section_name);
                  }
                });
              }
              setUnavailableList(nameList);
            }
          } else {
            setComponentLoading(false);
          }
        }
      },
      onError: ({ response, data }: any) => {
        if (response?.status === 503) {
          setTimeout(() => {
            fetchAllComponentVersions();
          }, 1000);
        } else {
          if (response) {
            const errorInfo = data?.msg || data?.detail || response?.statusText;
            handleResponseError(errorInfo);
          }
          setComponentLoading(false);
        }
      },
    });

  const onValuesChange = (values: FormValues) => {
    if (values?.type) {
      setCurrentType(values?.type);
      judgVersions(values?.type, componentsVersionInfo);
    }
  };

  const nameValidator = async (_: any, value: string) => {
    if (value) {
      if (hasDraft || isDraft) {
        return Promise.resolve();
      }
      if (!appnameReg.test(value)) {
        return Promise.reject(
          new Error('首字母英文且仅支持英文、数字，长度不超过20'),
        );
      }
      try {
        const { success, data } = await getInfoByName({ name: value });
        if (success) {
          if (['CONFIGURED', 'DESTROYED'].includes(data?.status)) {
            return Promise.resolve();
          }
          return Promise.reject(
            new Error(`已存在为 ${value} 的部署名称，请指定新名称`),
          );
        }
        return Promise.resolve();
      } catch (e: any) {
        const { response, data } = e;
        if (response?.status === 404) {
          return Promise.resolve();
        } else {
          handleResponseError(
            data?.msg || data?.detail || response?.statusText,
          );
        }
      }
    }
  };

  const nextStep = () => {
    form.validateFields().then((values) => {
      const lastAppName = oceanbase?.appname || initAppName;
      let newHomePath = home_path;
      if (values?.appname !== lastAppName && home_path) {
        const firstHalfHomePath = home_path.split(`/${lastAppName}`)[0];
        newHomePath = `${firstHalfHomePath}/${values?.appname}`;
      }
      let newComponents: API.Components = {
        oceanbase: {
          ...(components?.oceanbase || {}),
          component:
            componentsVersionInfo?.[oceanbaseComponent]?.version_type === 'ce'
              ? 'oceanbase-ce'
              : 'oceanbase',
          appname: values?.appname,
          version: componentsVersionInfo?.[oceanbaseComponent]?.version,
          release: componentsVersionInfo?.[oceanbaseComponent]?.release,
          package_hash: componentsVersionInfo?.[oceanbaseComponent]?.md5,
        },
      };
      if (currentType === 'all') {
        newComponents.obproxy = {
          ...(components?.obproxy || {}),
          component:
            componentsVersionInfo?.[obproxyComponent]?.version_type === 'ce'
              ? 'obproxy-ce'
              : 'obproxy',
          version: componentsVersionInfo?.[obproxyComponent]?.version,
          release: componentsVersionInfo?.[obproxyComponent]?.release,
          package_hash: componentsVersionInfo?.[obproxyComponent]?.md5,
        };
        if (!lowVersion) {
          newComponents.ocpexpress = {
            ...(components?.ocpexpress || {}),
            component: ocpexpressComponent,
            version: componentsVersionInfo?.[ocpexpressComponent]?.version,
            release: componentsVersionInfo?.[ocpexpressComponent]?.release,
            package_hash: componentsVersionInfo?.[ocpexpressComponent]?.md5,
          };
        }
        newComponents.obagent = {
          ...(components?.obagent || {}),
          component: obagentComponent,
          version: componentsVersionInfo?.[obagentComponent]?.version,
          release: componentsVersionInfo?.[obagentComponent]?.release,
          package_hash: componentsVersionInfo?.[obagentComponent]?.md5,
        };
      }
      setConfigData({
        ...configData,
        components: newComponents,
        home_path: newHomePath,
      });
      setCurrentStep(2);
      setIsFirstTime(false);
    });
  };

  const onVersionChange = (
    value: string,
    dataSource: API.service_model_components_ComponentInfo[],
  ) => {
    const md5 = value.split('-')[2];
    setOBVersionValue(value);
    const newSelectedVersionInfo = dataSource.filter(
      (item) => item.md5 === md5,
    )[0];
    setComponentsVersionInfo({
      ...componentsVersionInfo,
      [oceanbaseComponent]: {
        ...componentsVersionInfo[oceanbaseComponent],
        ...newSelectedVersionInfo,
      },
    });
    setLowVersion(
      !!(
        newSelectedVersionInfo.version &&
        checkLowVersion(newSelectedVersionInfo.version.split('')[0])
      ),
    );
  };

  const directTo = (url: string) => {
    // 在新的标签页中打开
    const blankWindow = window.open('about:blank');
    if (blankWindow) {
      blankWindow.location.href = url;
    } else {
      // 兜底逻辑，在当前标签页打开
      window.location.href = url;
    }
  };

  const getColumns = (group: string) => {
    const columns: ColumnsType<API.TableComponentInfo> = [
      {
        title: group,
        dataIndex: 'name',
        width: 195,
        render: (text, record) => {
          if (currentType === 'all') {
            return (
              <>
                {text}
                {record.key === ocpexpressComponent && lowVersion ? (
                  <Tooltip title=" OCPExpress 仅支持 4.0 及以上版本 OceanBase Database。">
                    <span className={`${styles.iconContainer} warning-color`}>
                      <InfoOutlined className={styles.icon} />
                    </span>
                  </Tooltip>
                ) : !componentsVersionInfo[record.key]?.version ? (
                  <Tooltip title="无法获取安装包，请检查安装程序配置。">
                    <span className={`${styles.iconContainer} error-color`}>
                      <CloseOutlined className={styles.icon} />
                    </span>
                  </Tooltip>
                ) : null}
              </>
            );
          }
          return text;
        },
      },
      {
        title: '版本',
        dataIndex: 'version',
        width: 130,
        render: (_, record) => {
          const versionInfo = componentsVersionInfo[record.key] || {};
          if (record?.key === oceanbaseComponent) {
            return (
              <Select
                value={obVersionValue}
                optionLabelProp="data_value"
                style={{ width: 100 }}
                onChange={(value) =>
                  onVersionChange(value, versionInfo?.dataSource)
                }
                popupClassName={styles?.popupClassName}
              >
                {versionInfo?.dataSource?.map(
                  (item: API.service_model_components_ComponentInfo) => (
                    <Select.Option
                      value={`${item.version}-${item?.release}-${item.md5}`}
                      data_value={item.version}
                      key={`${item.version}-${item?.release}-${item.md5}`}
                    >
                      {item.version}
                      {item?.release ? `-${item?.release}` : ''}
                      {item.version_type === 'ce' ? (
                        <Tag className="default-tag ml-8">社区版</Tag>
                      ) : (
                        <Tag className="blue-tag ml-8">商业版</Tag>
                      )}

                      {item?.type === 'local' ? (
                        <span className={styles.localTag}>
                          <SafetyCertificateFilled />
                          本地镜像
                        </span>
                      ) : (
                        ''
                      )}
                    </Select.Option>
                  ),
                )}
              </Select>
            );
          } else {
            return versionInfo?.version ? (
              <>
                {versionInfo?.version}
                <Tag className="default-tag ml-8">最新</Tag>
              </>
            ) : (
              '-'
            );
          }
        },
      },
      {
        title: '描述',
        dataIndex: 'desc',
        render: (text, record) => {
          let disabled = false;
          if (
            (record.key === ocpexpressComponent && lowVersion) ||
            (currentType === 'ob' && record.onlyAll)
          ) {
            disabled = true;
          }
          return (
            <>
              {text || '-'}
              <a
                className={styles.learnMore}
                onClick={() => {
                  if (!disabled) directTo(record.doc);
                }}
                target="_blank"
              >
                了解更多
              </a>
            </>
          );
        },
      },
    ];
    return columns;
  };

  const handleCopy = (content: string) => {
    copy(content);
    message.success('复制成功');
  };

  useEffect(() => {
    setComponentLoading(true);
    if (isFirstTime) {
      fetchAllComponentVersions();
      fetchDeploymentInfo({ task_status: 'DRAFT' }).then(
        ({ success: draftSuccess, data: draftData }: API.OBResponse) => {
          if (draftSuccess && draftData?.items?.length) {
            const defaultValue = draftData?.items[0]?.name;
            draftNameRef.current = defaultValue;
            setHasDraft(true);
            Modal.confirm({
              title: '检测到系统中存在以下部署失败的历史配置',
              okText: '继续部署',
              cancelText: '忽略',
              closable: true,
              width: 424,
              content: (
                <Space direction="vertical" size="middle">
                  <div style={{ color: '#5C6B8A' }}>
                    继续部署将先清理失败的历史部署环境，是否继续历史部署流程？
                  </div>
                  <Select
                    style={commonStyle}
                    onChange={(value) => (draftNameRef.current = value)}
                    defaultValue={defaultValue}
                  >
                    {draftData?.items?.map((item) => (
                      <Select.Option key={item.name} value={item.name}>
                        {item.name}
                      </Select.Option>
                    ))}
                  </Select>
                </Space>
              ),
              onOk: () => {
                return new Promise<void>(async (resolve) => {
                  try {
                    const { success: deleteSuccess } =
                      await handleDeleteDeployment({
                        name: draftNameRef.current,
                      });
                    if (deleteSuccess) {
                      resolve();
                      setDeleteName(draftNameRef.current);
                      setDeleteLoadingVisible(true);
                    }
                  } catch {
                    setIsDraft(false);
                    resolve();
                  }
                });
              },
              onCancel: () => {
                setIsDraft(false);
                setHasDraft(false);
              },
            });
          } else {
            setIsDraft(false);
          }
        },
      );
    } else {
      fetchAllComponentVersions();
    }
  }, []);

  useEffect(() => {
    let newInstallMemory = 0;
    if (currentType === 'ob') {
      newInstallMemory =
        componentsVersionInfo?.[oceanbaseComponent]?.estimated_size;
    } else {
      const keys = Object.keys(componentsVersionInfo);
      keys.forEach((key) => {
        newInstallMemory =
          newInstallMemory + componentsVersionInfo[key]?.estimated_size;
      });
    }
    setInstallMemory(newInstallMemory);
  }, [componentsVersionInfo, currentType]);

  useEffect(() => {
    form.setFieldsValue({ type: currentType });
  }, [currentType]);

  useEffect(() => {
    form.setFieldsValue({
      appname: configData?.components?.oceanbase?.appname || initAppName,
    });
  }, [configData]);

  return (
    <Spin spinning={loading}>
      <Space className={styles.spaceWidth} direction="vertical" size="middle">
        <ProCard className={styles.pageCard} split="horizontal">
          <ProCard title="部署配置" className="card-padding-bottom-24">
            <ProForm
              form={form}
              submitter={false}
              initialValues={{
                appname: oceanbase?.appname || initAppName,
                type: currentType,
              }}
              onValuesChange={onValuesChange}
            >
              <ProFormText
                name="appname"
                label="集群名称"
                fieldProps={{ style: commonStyle }}
                placeholder="请输入集群名称"
                validateTrigger={['onBlur', 'onChange']}
                disabled={isDraft}
                rules={[
                  {
                    required: true,
                    message: '请输入集群名称',
                    validateTrigger: 'onChange',
                  },
                  {
                    pattern: appnameReg,
                    message: '首字母英文且仅支持英文、数字，长度不超过20',
                    validateTrigger: 'onChange',
                  },
                  { validator: nameValidator, validateTrigger: 'onBlur' },
                ]}
              />
              <Form.Item
                name="type"
                label="部署类型"
                className="form-item-no-bottom"
              >
                <DeployType />
              </Form.Item>
            </ProForm>
          </ProCard>
          <ProCard
            title={
              <>
                部署组件
                <span className={styles.titleExtra}>
                  <InfoCircleOutlined /> 预计安装需要{' '}
                  {NP.divide(NP.divide(installMemory, 1024), 1024).toFixed(2)}{' '}
                  MB 空间
                </span>
              </>
            }
            className="card-header-padding-top-0 card-padding-bottom-24  card-padding-top-0"
          >
            <Space
              className={styles.spaceWidth}
              direction="vertical"
              size="middle"
            >
              {existNoVersion ? (
                unavailableList?.length ? (
                  <Alert
                    message={
                      <>
                        如当前环境无法正常访问外网，建议使用 OceanBase
                        离线安装包进行安装部署。
                        <a
                          href="https://open.oceanbase.com/softwareCenter/community"
                          target="_blank"
                        >
                          前往下载离线安装
                        </a>
                      </>
                    }
                    type="error"
                    showIcon
                    style={{ marginTop: '16px' }}
                  />
                ) : (
                  <Alert
                    message={
                      <>
                        如当前环境可正常访问外网，可启动 OceanBase
                        在线镜像仓库，或联系您的镜像仓库管理员。
                        <Tooltip
                          overlayClassName={styles.commandTooltip}
                          title={
                            <div>
                              请在主机上执行一下命令启用在线镜像仓库
                              <br /> obd mirror enable
                              oceanbase.community.stable
                              oceanbase.development-kit
                              <a>
                                <CopyOutlined
                                  onClick={() =>
                                    handleCopy(
                                      'obd mirror enable oceanbase.community.stable oceanbase.development-kit',
                                    )
                                  }
                                />
                              </a>
                            </div>
                          }
                        >
                          <a>如何启用在线镜像仓库</a>
                        </Tooltip>
                      </>
                    }
                    type="error"
                    showIcon
                    style={{ marginTop: '16px' }}
                  />
                )
              ) : null}
              <Spin spinning={componentLoading}>
                {componentsGroupInfo.map((info) => (
                  <ProCard
                    type="inner"
                    className={`${styles.componentCard} ${
                      currentType === 'ob' && info.onlyAll
                        ? styles.disabledCard
                        : ''
                    }`}
                    key={info.group}
                  >
                    <Table
                      className={styles.componentTable}
                      columns={getColumns(info.group)}
                      rowKey="key"
                      dataSource={info.content}
                      pagination={false}
                      rowClassName={(record) => {
                        if (
                          (record.key === ocpexpressComponent && lowVersion) ||
                          (currentType === 'ob' && record?.onlyAll)
                        ) {
                          return styles.disabledRow;
                        }
                      }}
                    />
                  </ProCard>
                ))}
              </Spin>
            </Space>
          </ProCard>
        </ProCard>
        <footer className={styles.pageFooterContainer}>
          <div className={styles.pageFooter}>
            <Space className={styles.foolterAction}>
              <Button
                onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
                data-aspm-click="c307507.d317381"
                data-aspm-desc="部署配置-退出"
                data-aspm-param={``}
                data-aspm-expo
              >
                退出
              </Button>
              <Button
                type="primary"
                onClick={nextStep}
                disabled={
                  lowVersion ||
                  existNoVersion ||
                  versionLoading ||
                  componentLoading
                }
                data-aspm-click="c307507.d317280"
                data-aspm-desc="部署配置-下一步"
                data-aspm-param={``}
                data-aspm-expo
              >
                下一步
              </Button>
            </Space>
          </div>
        </footer>
        {deleteLoadingVisible && (
          <DeleteDeployModal
            visible={deleteLoadingVisible}
            name={deleteName}
            onCancel={() => setDeleteLoadingVisible(false)}
            setOBVersionValue={setOBVersionValue}
          />
        )}
      </Space>
    </Spin>
  );
}
