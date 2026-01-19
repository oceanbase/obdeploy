import ErrorCompToolTip from '@/component/ErrorCompToolTip';
import { useComponents } from '@/hooks/useComponents';
import {
  queryAllComponentVersions,
  queryComponentParameters,
} from '@/services/ob-deploy-web/Components';
import {
  destroyDeployment,
  getDeployment,
  getScenarioType,
} from '@/services/ob-deploy-web/Deployments';
import { listRemoteMirrors } from '@/services/ob-deploy-web/Mirror';
import {
  checkLowVersion,
  clusterNameReg,
  getErrorInfo,
  handleQuit,
} from '@/utils';
import { formatMoreConfig } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import {
  CopyOutlined,
  InfoCircleOutlined,
  SafetyCertificateFilled,
} from '@ant-design/icons';
import { ProCard, ProForm, ProFormText } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  message,
  Modal,
  Radio,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import copy from 'copy-to-clipboard';
import { divide, isNull } from 'lodash';
import NP from 'number-precision';
import { useEffect, useRef, useState } from 'react';
import { getLocale, history, useModel } from 'umi';
import {
  alertManagerComponent,
  allComponentsName,
  commonStyle,
  configServerComponent,
  grafanaComponent,
  obagentComponent,
  obproxyComponent,
  oceanbaseComponent,
  oceanbaseStandaloneComponent,
  prometheusComponent,
} from '../constants';
import { getParamstersHandler } from './ClusterConfig/helper';
import DeleteDeployModal from './DeleteDeployModal';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

type rowDataType = {
  key: string;
  name: string;
  onlyAll: boolean;
  desc: string;
  doc: string;
};

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

const mirrors = ['oceanbase.community.stable', 'oceanbase.development-kit'];

export default function InstallConfig({
  deployMode,
  setDeployMode
}: {
  deployMode: string,
  setDeployMode: (mode: string) => void
}) {
  const {
    initAppName,
    setCurrentStep,
    configData,
    setConfigData,
    lowVersion,
    setLowVersion,
    isFirstTime,
    setIsFirstTime,
    isDraft,
    setIsDraft,
    componentsVersionInfo,
    setComponentsVersionInfo,
    handleQuitProgress,
    getInfoByName,
    setErrorVisible,
    errorsList,
    setErrorsList,
    selectedConfig,
    setSelectedConfig,
    aliveTokenTimer,
    OBD_DOCS,
    OBD_STANDALONE_DOCS,
    setScenarioParam,
    loadTypeVisible,
    setLoadTypeVisible,
    selectedLoadType,
    setSelectedLoadType,
  } = useModel('global');

  const [form] = ProForm.useForm();

  const { components, home_path } = configData || {};
  const { oceanbase } = components || {};
  const [obVersionValue, setOBVersionValue] = useState<string | undefined>(
    undefined,
  );
  const [scenarioTypeList, setScenarioTypeList] =
    useState<API.ScenarioType[]>();
  const [hasDraft, setHasDraft] = useState(false);
  const [deleteLoadingVisible, setDeleteLoadingVisible] = useState(false);
  const [deleteName, setDeleteName] = useState('');
  const [deployMemory, setDeployMemory] = useState(0);
  const [componentsMemory, setComponentsMemory] = useState(0);
  const [oceanbaseType, setOceanbaseType] = useState<string>('');
  const [componentLoading, setComponentLoading] = useState(false);
  const draftNameRef = useRef();

  // 当前 OB 环境是否为单机版
  // const standAlone = deployMode === 'standalone';
  const standAlone = oceanbaseType === 'standalone';

  const componentsGroupInfo = useComponents(true, standAlone);

  const oceanBaseInfo = {
    group: intl.formatMessage({
      id: 'OBD.pages.components.InstallConfig.Database',
      defaultMessage: '数据库',
    }),
    key: 'database',
    content: [
      {
        key: standAlone ? oceanbaseStandaloneComponent : oceanbaseComponent,
        name: 'OceanBase Database',
        onlyAll: false,
        desc: intl.formatMessage({
          id: 'OBD.pages.components.InstallConfig.ItIsAFinancialLevel',
          defaultMessage:
            '是金融级分布式数据库，具备数据强一致、高扩展、高可用、高性价比、稳定可靠等特征。',
        }),
        doc: standAlone ? OBD_STANDALONE_DOCS : OBD_DOCS,
      },
    ],
  };

  const errorCommonHandle = (e: any) => {
    const errorInfo = getErrorInfo(e);
    setErrorVisible(true);
    setErrorsList([...errorsList, errorInfo]);
  };

  const { run: fetchDeploymentInfo, loading } = useRequest(getDeployment, {
    onError: errorCommonHandle,
  });

  const { run: handleDeleteDeployment } = useRequest(destroyDeployment, {
    onError: errorCommonHandle,
  });

  const { run: fetchListRemoteMirrors, data: listRemoteMirror } = useRequest(
    listRemoteMirrors,
    {
      onSuccess: () => {
        setComponentLoading(false);
      },
      onError: ({ response, data, type }: any) => {
        if (response?.status === 503) {
          setTimeout(() => {
            fetchListRemoteMirrors();
          }, 1000);
        } else {
          errorCommonHandle({ response, data, type });
          setComponentLoading(false);
        }
      },
    },
  );

  const { run: fetchAllComponentVersions, loading: versionLoading } =
    useRequest(queryAllComponentVersions, {
      onSuccess: async ({
        success,
        data,
      }: API.OBResponseDataListComponent_) => {
        if (success) {
          const newComponentsVersionInfo = {};
          const oceanbaseVersionsData = data?.items?.filter((item) =>
            deployComponent.includes(
              item.name,
            ),
          );
          const initOceanbaseVersionInfo =
            oceanbaseVersionsData[0]?.info[0] || {};
          const newSelectedOceanbaseVersionInfo =
            oceanbaseVersionsData[0]?.info?.filter(
              (item) => item.md5 === oceanbase?.package_hash,
            )?.[0];

          const currentOceanbaseVersionInfo =
            newSelectedOceanbaseVersionInfo || initOceanbaseVersionInfo;
          data?.items?.forEach((item) => {
            if (allComponentsName.includes(item.name)) {
              if (item?.info?.length) {
                const initVersionInfo = item?.info[0] || {};
                if (
                  item.name === oceanbaseComponent ||
                  item.name === oceanbaseStandaloneComponent
                ) {
                  setOceanbaseType(currentOceanbaseVersionInfo?.version_type);
                  setOBVersionValue(
                    `${currentOceanbaseVersionInfo?.version}-${currentOceanbaseVersionInfo?.release}-${currentOceanbaseVersionInfo?.md5}`,
                  );
                  newComponentsVersionInfo[item.name] = {
                    ...currentOceanbaseVersionInfo,
                    dataSource: item.info || [],
                  };
                } else if (item.name === obproxyComponent) {
                  let currentObproxyVersionInfo = {};
                  item?.info?.some((subItem) => {
                    if (
                      subItem?.version_type ===
                      currentOceanbaseVersionInfo?.version_type
                    ) {
                      currentObproxyVersionInfo = subItem;
                      return true;
                    }
                    return false;
                  });
                  // 如果没有匹配到对应版本类型的 obproxy，使用第一个可用的版本
                  if (Object.keys(currentObproxyVersionInfo).length === 0) {
                    currentObproxyVersionInfo = item?.info?.[0] || {};
                  }
                  newComponentsVersionInfo[item.name] = {
                    ...currentObproxyVersionInfo,
                    // 保持与其他组件一致的数据结构，包含 dataSource
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
            }
          } else {
            setComponentLoading(false);
          }
        }
      },
      onError: ({ response, data, type }: any) => {
        if (response?.status === 503) {
          setTimeout(() => {
            fetchAllComponentVersions();
          }, 1000);
        } else {
          const errorInfo = getErrorInfo({ response, data, type });
          setErrorVisible(true);
          setErrorsList([...errorsList, errorInfo]);
          setComponentLoading(false);
        }
      },
    });

  const nameValidator = async (_: any, value: string) => {
    if (value) {
      if (hasDraft || isDraft) {
        return Promise.resolve();
      }
      if (!clusterNameReg.test(value)) {
        return Promise.reject(
          new Error(
            intl.formatMessage({
              id: 'OBD.pages.Obdeploy.InstallConfig.ItStartsWithALetter',
              defaultMessage:
                '以英文字母开头、英文或数字结尾，可包含英文、数字和下划线，且长度为 2 ~ 32',
            }),
          ),
        );
      }
      try {
        const { success, data } = await getInfoByName({ name: value });
        if (success) {
          if (['CONFIGURED', 'DESTROYED'].includes(data?.status)) {
            return Promise.resolve();
          }
          return Promise.reject(
            new Error(
              intl.formatMessage(
                {
                  id: 'OBD.pages.components.InstallConfig.ADeploymentNameWithValue',
                  defaultMessage: '已存在为 {value} 的部署名称，请指定新名称',
                },
                { value: value },
              ),
            ),
          );
        }
        return Promise.resolve();
      } catch ({ response, data, type }: any) {
        if (response?.status === 404) {
          return Promise.resolve();
        } else {
          const errorInfo = getErrorInfo({ response, data, type });
          setErrorVisible(true);
          setErrorsList([...errorsList, errorInfo]);
        }
      }
    }
  };

  const preStep = () => {
    if (aliveTokenTimer.current) {
      clearTimeout(aliveTokenTimer.current);
      aliveTokenTimer.current = null;
    }
    history.push('/guide');
    sessionStorage.removeItem('componentSelect');
  };

  const nextStep = () => {
    if (form.getFieldsError(['appname'])[0].errors.length) return;
    form.validateFields().then((values) => {
      const lastAppName = oceanbase?.appname || initAppName;
      let newHomePath = home_path;
      if (values?.appname !== lastAppName && home_path) {
        const firstHalfHomePath = home_path.split(`/${lastAppName}`)[0];
        newHomePath = `${firstHalfHomePath}/${values?.appname}`;
      }
      if (scenarioTypeList?.length) {
        setScenarioParam({
          key: 'scenario',
          value: selectedLoadType,
          adaptive: false,
        });
      } else {
        setScenarioParam(null);
      }

      let newComponents: API.Components = {
        oceanbase: {
          ...(components?.oceanbase || {}),
          component:
            componentsVersionInfo?.[oceanbaseComponent]?.version_type === 'ce'
              ? 'oceanbase-ce'
              : componentsVersionInfo?.[oceanbaseComponent]?.version_type ===
                'business'
                ? 'oceanbase'
                : 'oceanbase-standalone',
          appname: values?.appname,
          version: standAlone
            ? componentsVersionInfo?.[oceanbaseStandaloneComponent]?.version
            : componentsVersionInfo?.[oceanbaseComponent]?.version,
          release: standAlone
            ? componentsVersionInfo?.[oceanbaseStandaloneComponent]?.release
            : componentsVersionInfo?.[oceanbaseComponent]?.release,
          package_hash: standAlone
            ? componentsVersionInfo?.[oceanbaseStandaloneComponent]?.md5
            : componentsVersionInfo?.[oceanbaseComponent]?.md5,
        },
      };

      if (selectedConfig.includes(obproxyComponent) && !standAlone) {
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
      }
      if (selectedConfig.includes(obagentComponent)) {
        newComponents.obagent = {
          ...(components?.obagent || {}),
          component: obagentComponent,
          version: componentsVersionInfo?.[obagentComponent]?.version,
          release: componentsVersionInfo?.[obagentComponent]?.release,
          package_hash: componentsVersionInfo?.[obagentComponent]?.md5,
        };
      }
      if (selectedConfig.includes(grafanaComponent)) {
        newComponents.grafana = {
          ...(components?.grafana || {}),
          component: grafanaComponent,
          version: componentsVersionInfo?.[grafanaComponent]?.version,
          release: componentsVersionInfo?.[grafanaComponent]?.release,
          package_hash: componentsVersionInfo?.[grafanaComponent]?.md5,
        };
      }
      if (selectedConfig.includes(prometheusComponent)) {
        newComponents.prometheus = {
          ...(components?.prometheus || {}),
          component: prometheusComponent,
          version: componentsVersionInfo?.[prometheusComponent]?.version,
          release: componentsVersionInfo?.[prometheusComponent]?.release,
          package_hash: componentsVersionInfo?.[prometheusComponent]?.md5,
        };
      }
      if (selectedConfig.includes(alertManagerComponent)) {
        newComponents.alertmanager = {
          ...(components?.alertmanager || {}),
          component: alertManagerComponent,
          version: componentsVersionInfo?.[alertManagerComponent]?.version,
          release: componentsVersionInfo?.[alertManagerComponent]?.release,
          package_hash: componentsVersionInfo?.[alertManagerComponent]?.md5,
        };
      }

      if (selectedConfig.includes(configServerComponent) && !standAlone) {
        newComponents.obconfigserver = {
          ...(components?.obconfigserver || {}),
          component: configServerComponent,
          version: componentsVersionInfo?.[configServerComponent]?.version,
          release: componentsVersionInfo?.[configServerComponent]?.release,
          package_hash: componentsVersionInfo?.[configServerComponent]?.md5,
        };
      }
      const anc = [configServerComponent, obproxyComponent];
      if (standAlone && selectedConfig) {
        setSelectedConfig(selectedConfig.filter((item) => !anc.includes(item)));
      }
      if (
        (oceanbaseType === 'ce' || oceanbaseType === 'business') &&
        components?.oceanbase?.component === 'oceanbase-standalone'
      ) {
        newComponents.oceanbase = {
          ...newComponents.oceanbase,
          topology: undefined,
        };
      } else if (
        oceanbaseType === 'standalone' &&
        (components?.oceanbase?.component === 'oceanbase-ce' ||
          components?.oceanbase?.component === 'oceanbase')
      ) {
        newComponents.oceanbase = {
          ...newComponents.oceanbase,
          topology: undefined,
        };
      }
      setConfigData({
        ...configData,
        components: newComponents,
        home_path: newHomePath,
      });

      setCurrentStep(2);
      setIsFirstTime(false);
      setErrorVisible(false);
      setErrorsList([]);
      window.scrollTo(0, 0);
    });
    // 是否为初次点击部署组件
    sessionStorage.setItem('componentSelect', 'true');
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
    setOceanbaseType(newSelectedVersionInfo?.version_type);
    let currentObproxyVersionInfo = {};
    componentsVersionInfo?.[obproxyComponent]?.dataSource?.some(
      (item: API.service_model_components_ComponentInfo) => {
        if (item?.version_type === newSelectedVersionInfo?.version_type) {
          currentObproxyVersionInfo = item;
          return true;
        }
        return false;
      },
    );
    // 如果没有匹配到对应版本类型的 obproxy，使用第一个可用的版本
    if (Object.keys(currentObproxyVersionInfo).length === 0) {
      currentObproxyVersionInfo = componentsVersionInfo?.[obproxyComponent]?.dataSource?.[0] || {};
    }
    setComponentsVersionInfo({
      ...componentsVersionInfo,
      [oceanbaseComponent]: {
        ...componentsVersionInfo[oceanbaseComponent],
        ...newSelectedVersionInfo,
      },
      [obproxyComponent]: {
        ...componentsVersionInfo[obproxyComponent],
        ...currentObproxyVersionInfo,
        // 保持与其他组件一致的数据结构，包含 dataSource
        dataSource: componentsVersionInfo[obproxyComponent]?.dataSource || [],
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
    const blankWindow = window.open('about:blank');
    if (blankWindow) {
      blankWindow.location.href = url;
    } else {
      window.location.href = url;
    }
  };

  // 根据部署模式选择部署类型
  const deployComponent = deployMode === 'distributed' ? [oceanbaseComponent] : [oceanbaseStandaloneComponent, oceanbaseComponent];
  const combinedDataSources = deployComponent
    .flatMap((component) => componentsVersionInfo[component]?.dataSource || [])
    .filter((dataSource) => dataSource !== undefined);

  const getColumns = (group: string, supportCheckbox: boolean) => {
    const columns: ColumnsType<API.TableComponentInfo> = [
      {
        title: group,
        dataIndex: 'name',
        width: supportCheckbox ? 147 : 175,
        className: supportCheckbox ? styles.firstCell : '',
        render: (text, record) => {
          return (
            <>
              {text}
              {!componentsVersionInfo[record.key]?.version ? (
                <ErrorCompToolTip
                  title={intl.formatMessage({
                    id: 'OBD.pages.Obdeploy.InstallConfig.UnableToObtainTheInstallation',
                    defaultMessage: '无法获取安装包，请检查安装程序配置。',
                  })}
                  status="error"
                />
              ) : null}
            </>
          );
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.InstallConfig.Version',
          defaultMessage: '版本',
        }),
        dataIndex: 'version',
        width: locale === 'zh-CN' ? 130 : 144,
        className: styles.secondCell,
        render: (_, record) => {
          const versionInfo = componentsVersionInfo[record.key] || {};

          if (
            record?.key === oceanbaseComponent ||
            record?.key === oceanbaseStandaloneComponent
          ) {
            return (
              <Select
                value={obVersionValue}
                optionLabelProp="data_value"
                style={{ width: 100, marginTop: '-4px' }}
                onChange={(value) =>
                  onVersionChange(value, combinedDataSources)
                }
                popupClassName={styles?.popupClassName}
              >
                {combinedDataSources?.map(
                  (item: API.service_model_components_ComponentInfo) => (
                    <Select.Option
                      value={`${item?.version}-${item?.release}-${item?.md5}`}
                      data_value={item?.version}
                      key={`${item?.version}-${item?.release}-${item?.md5}`}
                    >
                      {item?.version}
                      {item?.release ? `-${item?.release}` : ''}
                      {item?.version_type === 'ce' ? (
                        <Tag className="default-tag ml-8">
                          {intl.formatMessage({
                            id: 'OBD.pages.components.InstallConfig.CommunityEdition',
                            defaultMessage: '社区版',
                          })}
                        </Tag>
                      ) : item?.version_type === 'business' ? (
                        <Tag className="blue-tag ml-8">
                          {intl.formatMessage({
                            id: 'OBD.pages.components.InstallConfig.CommercialEdition',
                            defaultMessage: '商业版',
                          })}
                        </Tag>
                      ) : (
                        <Tag className="blue-tag ml-8">单机版</Tag>
                      )}

                      {item?.type === 'local' ? (
                        <span className={styles.localTag}>
                          <SafetyCertificateFilled />
                          {intl.formatMessage({
                            id: 'OBD.pages.components.InstallConfig.LocalImage',
                            defaultMessage: '本地镜像',
                          })}
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
                <Tag className="default-tag ml-8">
                  {intl.formatMessage({
                    id: 'OBD.pages.components.InstallConfig.Latest',
                    defaultMessage: '最新',
                  })}
                </Tag>
              </>
            ) : (
              '-'
            );
          }
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.InstallConfig.Description',
          defaultMessage: '描述',
        }),
        dataIndex: 'desc',
        className: styles.thirdCell,
        render: (text, record) => {
          let disabled = false;
          return (
            <div className={styles.descContent}>
              <p style={{ marginRight: 24, maxWidth: 556, marginTop: 0 }}>
                {text || '-'}
              </p>
              <a
                className={styles.learnMore}
                onClick={() => {
                  if (!disabled) directTo(record.doc);
                }}
                target="_blank"
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.InstallConfig.LearnMore',
                  defaultMessage: '了解更多',
                })}
              </a>
            </div>
          );
        },
      },
    ];

    return columns;
  };

  const handleCopy = (content: string) => {
    copy(content);
    message.success(
      intl.formatMessage({
        id: 'OBD.pages.components.InstallConfig.CopiedSuccessfully',
        defaultMessage: '复制成功',
      }),
    );
  };

  /**
   * @description
   * 组件选择逻辑：
   * 如果选择obagent，只勾选自己，不自动选择其他组件
   * 如果选择prometheus，则obagent自动选择
   * 如果选择 grafana，则 OBAgent和prometheus 则自动选择
   * 如果选择alertmanager，则prometheus、OBAgent自动选择
   * 取消勾选obagent，grafana、prometheus和alertmanager也取消掉
   * 取消勾选prometheus，grafana和alertmanager也取消掉
   * 取消勾选alertmanager，只取消掉自己
   * 取消勾选grafana，只取消掉自己
   */
  const handleSelect = (record: rowDataType, selected: boolean) => {
    // 组件依赖关系映射：选择某个组件时，需要自动选择的依赖组件
    const selectDependencies: Record<string, string[]> = {
      [obagentComponent]: [],
      [prometheusComponent]: [obagentComponent],
      [grafanaComponent]: [obagentComponent, prometheusComponent],
      [alertManagerComponent]: [prometheusComponent, obagentComponent],
    };

    // 取消选择时的依赖关系映射：取消某个组件时，需要同时取消的组件
    const unselectDependencies: Record<string, string[]> = {
      [obagentComponent]: [
        obagentComponent,
        grafanaComponent,
        prometheusComponent,
        alertManagerComponent,
      ],
      [prometheusComponent]: [
        prometheusComponent,
        grafanaComponent,
        alertManagerComponent,
      ],
      [alertManagerComponent]: [alertManagerComponent],
      [grafanaComponent]: [grafanaComponent],
    };

    if (selected) {
      // 选择逻辑
      const newConfig = [...selectedConfig];
      const dependencies = selectDependencies[record.key] || [];

      // 添加依赖组件
      dependencies.forEach((comp) => {
        if (!newConfig.includes(comp)) {
          newConfig.push(comp);
        }
      });

      // 添加当前组件
      if (!newConfig.includes(record.key)) {
        newConfig.push(record.key);
      }

      setSelectedConfig(newConfig);
    } else {
      // 取消选择逻辑
      const toRemove = unselectDependencies[record.key] || [record.key];
      const newConfig = selectedConfig.filter(
        (comp) => !toRemove.includes(comp),
      );

      setSelectedConfig(newConfig);
    }
  };

  const rowSelection = {
    hideSelectAll: true,
    onSelect: handleSelect,
    // 默认勾选项，需排除掉缺少必要安装包
    selectedRowKeys: selectedConfig?.filter((item: string) => {
      return componentsVersionInfo[item]?.version;
    }),
    getCheckboxProps: (record) => ({
      disabled: !componentsVersionInfo[record.key]?.version,
    }),
  };
  const caculateSize = (originSize: number): string => {
    return NP.divide(NP.divide(originSize, 1024), 1024).toFixed(2);
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
              title: intl.formatMessage({
                id: 'OBD.pages.components.InstallConfig.TheFollowingHistoricalConfigurationsOf',
                defaultMessage: '检测到系统中存在以下部署失败的历史配置',
              }),
              okText: intl.formatMessage({
                id: 'OBD.pages.components.InstallConfig.ContinueDeployment',
                defaultMessage: '继续部署',
              }),
              cancelText: intl.formatMessage({
                id: 'OBD.pages.components.InstallConfig.Ignore',
                defaultMessage: '忽略',
              }),
              closable: true,
              width: 424,
              content: (
                <Space direction="vertical" size="middle">
                  <div style={{ color: '#5C6B8A' }}>
                    {intl.formatMessage({
                      id: 'OBD.pages.components.InstallConfig.ContinuingDeploymentWillCleanUp',
                      defaultMessage:
                        '继续部署将先清理失败的历史部署环境，是否继续历史部署流程？',
                    })}
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
  }, [deployMode]);

  // 判断是否开启在线仓库
  const remoteMirror = listRemoteMirror?.items?.find(
    (item) => item.name === 'OceanBase-community-stable-el7',
  );

  useEffect(() => {
    let deployMemory: number = 0;
    if (standAlone) {
      deployMemory +=
        componentsVersionInfo?.[oceanbaseStandaloneComponent]?.estimated_size ||
        0;
    } else {
      deployMemory +=
        componentsVersionInfo?.[oceanbaseComponent]?.estimated_size || 0;
    }

    let componentsMemory: number = 0;
    const keys = Object.keys(componentsVersionInfo);
    keys.forEach((key) => {
      if (key !== oceanbaseComponent && selectedConfig.includes(key)) {
        componentsMemory += componentsVersionInfo[key]?.estimated_size || 0;
      }
    });
    setDeployMemory(deployMemory);
    setComponentsMemory(componentsMemory);
  }, [componentsVersionInfo, selectedConfig]);

  useEffect(() => {
    form.setFieldsValue({
      appname: configData?.components?.oceanbase?.appname || initAppName,
    });
  }, [configData]);


  useEffect(() => {
    if (obVersionValue) {
      getScenarioType(obVersionValue).then((res) => {
        if (res.success) {
          setScenarioTypeList(res.data?.items);
        }
      });
    }
  }, [obVersionValue]);

  useEffect(() => {
    if (!scenarioTypeList?.length && loadTypeVisible) {
      setLoadTypeVisible(false);
    }
    if (scenarioTypeList?.length && !loadTypeVisible) {
      setLoadTypeVisible(true);
    }
  }, [scenarioTypeList]);

  useEffect(() => {
    const componentSelect = sessionStorage.getItem('componentSelect');
    if (isNull(componentSelect)) {
      if (!standAlone) {
        // 分布式，默认勾选项，只取 obproxy
        setSelectedConfig(['obproxy']);
      } else {
        setSelectedConfig([]);
      }
    }
  }, []);

  return (
    <Spin spinning={loading || componentLoading}>
      <Space className={styles.spaceWidth} direction="vertical" size="middle">
        <ProCard className={styles.pageCard} split="horizontal">
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.InstallConfig.DeploymentConfiguration',
              defaultMessage: '部署配置',
            })}
            className="card-padding-bottom-24"
            bodyStyle={{ paddingBottom: 0 }}
          >
            <ProForm
              form={form}
              submitter={false}
              initialValues={{
                appname: oceanbase?.appname || initAppName,
              }}
            >
              <ProFormText
                name="appname"
                label={intl.formatMessage({
                  id: 'OBD.pages.components.InstallConfig.ClusterName',
                  defaultMessage: '集群名称',
                })}
                fieldProps={{ style: commonStyle }}
                placeholder={intl.formatMessage({
                  id: 'OBD.pages.components.InstallConfig.EnterAClusterName',
                  defaultMessage: '请输入集群名称',
                })}
                validateTrigger={['onBlur', 'onChange']}
                disabled={isDraft}
                rules={[
                  {
                    required: true,
                    message: intl.formatMessage({
                      id: 'OBD.pages.components.InstallConfig.EnterAClusterName',
                      defaultMessage: '请输入集群名称',
                    }),
                    validateTrigger: 'onChange',
                  },
                  {
                    pattern: clusterNameReg,
                    message: intl.formatMessage({
                      id: 'OBD.pages.Obdeploy.InstallConfig.ItStartsWithALetter',
                      defaultMessage:
                        '以英文字母开头、英文或数字结尾，可包含英文、数字和下划线，且长度为 2 ~ 32',
                    }),

                    validateTrigger: 'onChange',
                  },
                  { validator: nameValidator, validateTrigger: 'onBlur' },
                ]}
              />
            </ProForm>
          </ProCard>
          <ProCard
            title={
              <span style={{ fontWeight: '400' }}>
                部署模式
              </span>
            }
            headStyle={{ paddingTop: 0 }}
            bodyStyle={{ paddingBottom: 24, paddingTop: 8 }}
          >

            <Radio.Group
              optionType='button'
              value={deployMode}
              onChange={(e) => {
                setDeployMode(e.target.value)
                setOceanbaseType('');
                setOBVersionValue(undefined);
              }
              }
            >
              <Tooltip
                color={'#fff'}
                placement='bottom'
                overlayInnerStyle={{ width: 400 }}
                title={
                  <div style={{ color: '#132039' }}>
                    分布式集群是 OceanBase 的企业级原生分布式数据库架构，相较于集中式单机，分布式集群具备金融级高可用以及平滑扩缩容能力，高度兼容 Oracle（仅商业版）/MySQL 模式，适用于对数据安全要求较高的核心业务系统。
                  </div>
                }
              >
                <Radio value="distributed">分布式</Radio>
              </Tooltip>
              <Tooltip
                color={'#fff'}
                placement='bottom'
                overlayInnerStyle={{ width: 400 }}
                title={
                  <div style={{ color: '#132039' }}>
                    相较于分布式集群，单机集中式仅需一台主机，部署简单，即开即用。但无多副本及扩缩容能力，适用于开发测试以及数据安全要求不高的业务系统。
                  </div>
                }
              >
                <Radio value="standalone">单机</Radio>
              </Tooltip>

            </Radio.Group>

          </ProCard>
          <ProCard
            title={
              <>
                <span style={{ fontWeight: '400' }}>
                  {intl.formatMessage({
                    id: 'OBD.pages.Obdeploy.InstallConfig.DeployADatabase',
                    defaultMessage: '部署数据库',
                  })}
                </span>
                <span className={styles.titleExtra}>
                  <InfoCircleOutlined style={{ marginRight: 4 }} />{' '}
                  {intl.formatMessage(
                    {
                      id: 'OBD.pages.components.InstallConfig.EstimatedInstallationRequiresSizeMb',
                      defaultMessage: '预计安装需要 {size}MB 空间',
                    },
                    { size: caculateSize(deployMemory) },
                  )}
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
              {(remoteMirror?.available === false ||
                listRemoteMirror?.items?.length === 0) &&
                combinedDataSources?.length === 0 && (
                  <Alert
                    message={
                      <>
                        {intl.formatMessage({
                          id: 'OBD.pages.components.InstallConfig.IfTheCurrentEnvironmentCannot',
                          defaultMessage:
                            '如当前环境无法正常访问外网，建议使用 OceanBase 离线安装包进行安装部署。',
                        })}
                        <a
                          href="https://open.oceanbase.com/softwareCenter/community"
                          target="_blank"
                        >
                          {intl.formatMessage({
                            id: 'OBD.pages.components.InstallConfig.GoToDownloadOfflineInstallation',
                            defaultMessage: '前往下载离线安装',
                          })}
                        </a>
                      </>
                    }
                    type="error"
                    showIcon
                    style={{ marginTop: '16px' }}
                  />
                )}

              {((remoteMirror?.enabled === false &&
                remoteMirror?.available === true) ||
                listRemoteMirror?.items?.length === 0) &&
                combinedDataSources?.length === 0 && (
                  <Alert
                    message={
                      <>
                        {intl.formatMessage({
                          id: 'OBD.pages.components.InstallConfig.IfTheCurrentEnvironmentHas',
                          defaultMessage:
                            '如当前环境可正常访问外网，可启动 OceanBase 在线镜像仓库，或联系您的镜像仓库管理员。',
                        })}
                        <Tooltip
                          overlayClassName={styles.commandTooltip}
                          title={
                            <div>
                              {intl.formatMessage({
                                id: 'OBD.pages.components.InstallConfig.RunTheCommandOnThe',
                                defaultMessage:
                                  '请在主机上执行一下命令启用在线镜像仓库',
                              })}
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
                          <a>
                            {intl.formatMessage({
                              id: 'OBD.pages.components.InstallConfig.HowToEnableOnlineImage',
                              defaultMessage: '如何启用在线镜像仓库',
                            })}
                          </a>
                        </Tooltip>
                      </>
                    }
                    type="error"
                    showIcon
                    style={{ marginTop: '16px' }}
                  />
                )}

              <ProCard
                type="inner"
                className={`${styles.componentCard}`}
                key={oceanBaseInfo.group}
              >
                <Table
                  className={styles.componentTable}
                  columns={getColumns(oceanBaseInfo.group, false)}
                  rowKey="key"
                  dataSource={oceanBaseInfo.content}
                  pagination={false}
                  rowClassName={() => { }}
                />
              </ProCard>
            </Space>
          </ProCard>
          {loadTypeVisible && (
            <ProCard
              title={
                <>
                  <span style={{ fontWeight: '400' }}>
                    {intl.formatMessage({
                      id: 'OBD.pages.Obdeploy.InstallConfig.LoadType',
                      defaultMessage: '负载类型',
                    })}
                  </span>

                  <span className={styles.titleExtra}>
                    负载类型主要影响 SQL
                    类大查询判断时间（参数：large_query_threshold），对 OLTP
                    类型业务的 RT 可能存在较大影响，请谨慎选择。
                  </span>
                </>
              }
              headStyle={{ paddingTop: 0 }}
              bodyStyle={{ paddingBottom: 24, paddingTop: 8 }}
            >
              <Space
                className={styles.spaceWidth}
                direction="vertical"
                size="small"
              >
                <ProCard type="inner" className={`${styles.componentCard}`}>
                  <Table
                    className={styles.componentTable}
                    pagination={false}
                    columns={[
                      {
                        title: intl.formatMessage({
                          id: 'OBD.pages.Obdeploy.InstallConfig.Type',
                          defaultMessage: '类型',
                        }),
                        dataIndex: 'type',
                        width: 340,
                        render: (_, record) => {
                          return (
                            <>
                              <Select
                                value={selectedLoadType}
                                style={{ width: 292 }}
                                onChange={(value) => setSelectedLoadType(value)}
                                options={scenarioTypeList?.map((item) => ({
                                  label: item.type,
                                  value: item.value,
                                }))}
                              />
                              <div
                                style={{
                                  fontSize: '12px',
                                  color: '#8592ad',
                                }}
                              >
                                {record.desc}
                              </div>
                            </>
                          );
                        },
                      },
                    ]}
                    dataSource={[
                      {
                        type: selectedLoadType,
                        desc: scenarioTypeList?.find(
                          (item) => item.value === selectedLoadType,
                        )?.desc,
                      },
                    ]}
                    rowKey="key"
                  />
                </ProCard>
              </Space>
            </ProCard>
          )}

          <ProCard
            title={
              <>
                {intl.formatMessage({
                  id: 'OBD.pages.components.InstallConfig.OptionalComponents',
                  defaultMessage: '部署组件',
                })}

                <span className={styles.titleExtra}>
                  <InfoCircleOutlined style={{ marginRight: 4 }} />{' '}
                  {intl.formatMessage(
                    {
                      id: 'OBD.pages.components.InstallConfig.EstimatedInstallationRequiresSizeMb',
                      defaultMessage: '预计部署需要 {size}MB 空间',
                    },
                    { size: caculateSize(componentsMemory) },
                  )}
                </span>
              </>
            }
            className="card-header-padding-top-0 card-padding-bottom-24  card-padding-top-0"
          >
            {componentsGroupInfo.map((componentInfo) => (
              <Space
                className={styles.spaceWidth}
                direction="vertical"
                size="middle"
              >
                <ProCard
                  type="inner"
                  className={`${styles.componentCard}`}
                  key={componentInfo.group}
                >
                  <Table
                    rowSelection={rowSelection}
                    className={styles.componentTable}
                    columns={getColumns(componentInfo.group, true)}
                    rowKey="key"
                    dataSource={componentInfo.content}
                    pagination={false}
                    rowClassName={() => { }}
                  />
                </ProCard>
              </Space>
            ))}
          </ProCard>
        </ProCard>
        <footer className={styles.pageFooterContainer}>
          <div className={styles.pageFooter}>
            <Space className={styles.foolterAction}>
              <Button
                onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
                data-aspm-click="c307507.d317381"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.InstallConfig.DeploymentConfigurationExit',
                  defaultMessage: '部署配置-退出',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.InstallConfig.Exit',
                  defaultMessage: '退出',
                })}
              </Button>
              <Button onClick={preStep}>
                {intl.formatMessage({
                  id: 'OBD.pages.Obdeploy.InstallConfig.PreviousStep',
                  defaultMessage: '上一步',
                })}
              </Button>
              <Button
                type="primary"
                onClick={nextStep}
                disabled={lowVersion || versionLoading || componentLoading}
                data-aspm-click="c307507.d317280"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.InstallConfig.DeploymentConfigurationNextStep',
                  defaultMessage: '部署配置-下一步',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.InstallConfig.NextStep',
                  defaultMessage: '下一步',
                })}
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
