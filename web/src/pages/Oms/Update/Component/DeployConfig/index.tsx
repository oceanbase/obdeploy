import { commonSelectStyle, pathRule, } from '@/pages/constants';
import {
  takeOverOms,
  getOmsUpgradeInfo,
  getCurrentUser,
} from '@/services/ocp_installer_backend/OCP';
import {
  clusterNameReg,
  getErrorInfo,
  serverReg,
} from '@/utils';
import { getTailPath } from '@/utils/helper';
import { intl } from '@/utils/intl';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { ProCard, ProForm, ProFormText, ProFormItem, ProFormDigit, } from '@ant-design/pro-components';
import { useRequest } from 'ahooks';
import {
  Button,
  Col,
  Input,
  message,
  Radio,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { FormInstance } from 'antd/lib/form';
import { isEmpty } from 'lodash';
import { useEffect, useRef, useState } from 'react';
import { getLocale, history, useModel } from 'umi';
import EnStyles from '../../../indexEn.less';
import ZhStyles from '../../../indexZh.less';
import CustomFooter from '@/component/CustomFooter';
import ExitBtn from '@/component/ExitBtn';
import type {
  TableDataType,
} from './constants';
import { encrypt } from '@/utils/encrypt';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import { omsDockerImages } from '@/services/component-change/componentChange';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;
export default function DeployConfig({
  setCurrent,
  current,
  clusterList,
  getClusterListLoading
}: API.StepProp & {
  connectForm?: FormInstance<any>;
}) {
  const {
    getInfoByName,
    setErrorVisible,
    errorsList,
    setErrorsList,
    ocpConfigData,
    setOcpConfigData,
    OMS_DOCS,
    setOmsTakeoverData,
    omsTakeoverData,
    setOmsDockerData,
    omsDockerData,
  } = useModel('global');

  const [form] = ProForm.useForm();
  const [installType, setInstallType] = useState('obd_install');
  const [updateType, setUpdateType] = useState(ocpConfigData?.upgrade_mode || 'offline');
  const [nextLoading, setNextLoading] = useState(false);
  const [checkConnectionStatus, setCheckConnectionStatus] = useState<
    'unchecked' | 'fail' | 'success'
  >('unchecked');
  const [checkErrorInfo, setCheckErrorInfo] = useState<string>('');
  const isNextStepRef = useRef(false); // 标记是否正在点击 nextStep
  const currentVersionRef = useRef<string | null>(null); // 保存当前版本号

  // 使用 useWatch 监听 cluster_name 字段的变化
  const obdClusterName = ProForm.useWatch('obd_cluster_name', form);
  const notObdClusterName = ProForm.useWatch('not_obd_cluster_name', form);
  const formClusterName = installType === 'obd_install' ? obdClusterName : notObdClusterName;

  const checkRegInfo = {
    reg: clusterNameReg,
    msg: intl.formatMessage({
      id: 'OBD.component.DeployConfig.ItStartsWithALetter',
      defaultMessage:
        '以英文字母开头、英文或数字结尾，可包含英文、数字和下划线，且长度为 2 ~ 32',
    }),
  };

  // 版本比较函数：比较两个版本号，返回 true 表示 version1 > version2
  const compareVersions = (version1: string, version2: string): boolean => {
    const parseVersion = (v: string) => {
      if (!v) return [];
      // 提取版本号：去除 feature_ 前缀
      let version = v.split('feature_')[1] || v;
      // 去除后缀（如 _ce, _CE, _business, _el7_x86 等），只保留主版本号部分
      // 匹配从第一个下划线开始到结尾的所有内容（如 _ce_el7_x86 或 _business_el7_x86）
      version = version.replace(/_.*$/, '');
      // 将版本号按点分割并转换为数字数组
      const parts = version.split('.').map(part => {
        const num = parseInt(part, 10);
        return isNaN(num) ? 0 : num;
      });
      return parts;
    };
    const v1 = parseVersion(version1);
    const v2 = parseVersion(version2);
    const maxLen = Math.max(v1.length, v2.length);

    for (let i = 0; i < maxLen; i++) {
      const part1 = v1[i] || 0;
      const part2 = v2[i] || 0;
      if (part1 > part2) return true;
      if (part1 < part2) return false;
    }
    return false;
  };

  const getColumns = () => {
    const columns: ColumnsType<TableDataType> = [
      {
        title: intl.formatMessage({
          id: 'OBD.component.DeployConfig.ProductName',
          defaultMessage: '产品名称',
        }),
        dataIndex: 'name',
        width: locale === 'zh-CN' ? 134 : 140,
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.Oms.Update.Component.DeployConfig.OriginalVersion',
          defaultMessage: '原版本',
        }),
        dataIndex: 'install_type',
        width: 100,
        render: (_) => {
          const displayVersion = omsUpgradeInfo?.current_version?.split('feature_')[1]?.toUpperCase() || omsUpgradeInfo?.current_version || '';
          return <span>{displayVersion || '-'}</span>;
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.Oms.Update.Component.DeployConfig.TargetVersion',
          defaultMessage: '目标版本',
        }),
        dataIndex: 'version_info',
        width: 220,
        render: (text,) => {
          // 确保 text 是数组
          const versionList = Array.isArray(text) ? text : [];

          // 获取当前选中的值，格式为 version 字符串
          const getCurrentValue = () => {
            // 如果 version 明确设置为 null，说明被清空了，返回 undefined
            if (ocpConfigData?.version === null) {
              return undefined;
            }
            if (ocpConfigData?.version) {
              // 如果 configData.version 存在，直接使用
              return ocpConfigData.version;
            }
            // 如果 ocpConfigData 不存在或为空对象，且版本列表有数据，默认使用第一个版本
            if (versionList.length > 0 && (!ocpConfigData || Object.keys(ocpConfigData).length === 0)) {
              return versionList[0].version;
            }
            return undefined;
          };

          // 获取当前选中的项，用于显示版本号
          const getSelectedItem = () => {
            const currentValue = getCurrentValue();
            if (!currentValue) return null;
            return versionList.find((item: any) => item.version === currentValue) || versionList[0];
          };

          const selectedItem = getSelectedItem();
          const currentValue = getCurrentValue();

          return (
            <Tooltip title={!formClusterName ? intl.formatMessage({
              id: 'OBD.pages.Oms.InstallConfig.ConfigureAndValidateBeforeSelecting',
              defaultMessage: '配置完上面的信息并校验通过才可选择',
            }) : versionList[0]?.version}>
              <Select
                labelInValue
                value={currentValue && selectedItem ? {
                  label: (
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <span>V {selectedItem.version.split('feature_')[1]?.toUpperCase() || selectedItem.version}</span>
                      {selectedItem.version.includes('ce') ? (
                        <Tag className="default-tag ml-8" style={{ marginLeft: 8 }}>
                          {intl.formatMessage({
                            id: 'OBD.component.DeployConfig.CommunityEdition',
                            defaultMessage: '社区版',
                          })}
                        </Tag>
                      ) : (
                        <Tag className="blue-tag ml-8" style={{ marginLeft: 8 }}>
                          {intl.formatMessage({
                            id: 'OBD.component.DeployConfig.CommercialEdition',
                            defaultMessage: '商业版',
                          })}
                        </Tag>
                      )}
                    </div>
                  ),
                  value: currentValue,
                } : undefined}
                onChange={(option) => {
                  setOcpConfigData({
                    ...ocpConfigData,
                    version: option.value,
                  })
                }}
                style={{ width: 207 }}
                popupClassName={styles?.popupClassName}
                disabled={!formClusterName}
              >
                {Array.isArray(text) && text.length > 0 ? text.map((item: any) => {
                  const versionText = item.version.split('feature_')[1]?.toUpperCase() || item.version;
                  return (
                    <Select.Option value={item.version} key={item.version}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        V {versionText}
                        {item.version.includes('ce') ? (
                          <Tag className="default-tag ml-8">
                            {intl.formatMessage({
                              id: 'OBD.component.DeployConfig.CommunityEdition',
                              defaultMessage: '社区版',
                            })}
                          </Tag>
                        ) : (
                          <Tag className="blue-tag ml-8">
                            {intl.formatMessage({
                              id: 'OBD.component.DeployConfig.CommercialEdition',
                              defaultMessage: '商业版',
                            })}
                          </Tag>
                        )}
                      </div>
                    </Select.Option>
                  );
                }) : null}
              </Select>
            </Tooltip>
          );
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.component.DeployConfig.Description',
          defaultMessage: '描述',
        }),
        dataIndex: 'componentInfo',
        render: (_, record) => (
          <>
            {record.desc || '-'}
            <a
              href={record.doc}
              target="_blank"
            >
              {intl.formatMessage({
                id: 'OBD.component.DeployConfig.LearnMore',
                defaultMessage: '了解更多',
              })}
            </a>
          </>
        ),
      },
    ];

    return columns;
  };

  const nameValidator = async (_: any, value: string) => {
    if (value) {
      if (!checkRegInfo.reg.test(value)) {
        return Promise.reject(new Error(checkRegInfo.msg));
      }
      // 如果正在点击 nextStep，跳过 API 调用
      if (isNextStepRef.current) {
        return Promise.resolve();
      }
      try {
        const { success, data } = await getInfoByName({ name: value });
        if (success) {
          if (['CONFIGURED', 'DESTROYED'].includes(data?.status)) {
            return Promise.resolve();
          }
          setNextLoading(false);
          return Promise.reject(
            new Error(
              intl.formatMessage(
                {
                  id: 'OBD.component.DeployConfig.ADeploymentNameWithValue',
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

  const defaultErrorInfo = intl.formatMessage({
    id: 'OBD.component.OCPConfigNew.ServiceConfig.TheCurrentVerificationFailedPlease',
    defaultMessage: '当前校验失败，请重新输入',
  })

  const { run: getTakeOverOms, loading: takeOverOmsLoading } = useRequest(
    takeOverOms,
    {
      manual: true,
      onSuccess: ({ data }) => {
        setOmsTakeoverData(data);
        // 保存当前版本号到 ref
        if (data?.version) {
          currentVersionRef.current = data.version;
        }
        if (data?.success) {
          // 校验成功
          setCheckConnectionStatus('success');
          setCheckErrorInfo('');
        } else {
          // 校验失败：设置失败状态和错误信息
          setCheckConnectionStatus('fail');
          const errorMsg = (!data?.error || data?.error?.length === 0) ? defaultErrorInfo : data?.error;
          setCheckErrorInfo(errorMsg);
        }
      },
      onError: (error: any) => {
        // 网络错误或其他异常
        setCheckConnectionStatus('fail');
        const errorMsg = error?.response?.data?.detail || error?.message || defaultErrorInfo;
        setCheckErrorInfo(errorMsg);
      },
    },
  );

  const { data: getOmsUpgradeInfoRes, run: getOmsUpgrade, loading: getOmsUpgradeLoading } = useRequest(
    getOmsUpgradeInfo,
    {
      manual: true,
      onError: () => {
        // 静默处理错误，避免显示不必要的错误提示
        // 集群列表获取失败不影响升级流程
      },
    },
  );

  const omsUpgradeInfo = getOmsUpgradeInfoRes?.data;

  const noAvailableImageErrorInfo = intl.formatMessage({
    id: 'OBD.pages.Oms.Update.Component.DeployConfig.NoAvailableUpgradeImage',
    defaultMessage: '无可用升级镜像，请先在 OMS 节点加载目标镜像',
  })
  const {
    run: omsDocker,
    loading: omsDockerLoading
  } = useRequest(omsDockerImages, {
    manual: true,
    onSuccess: ({ data }: any) => {
      // 使用 ref 中保存的当前版本号
      const currentVersion = currentVersionRef.current || omsTakeoverData?.version;

      // 过滤版本，只保留比 currentVersion 大的版本
      let filteredImages = data?.oms_images || [];
      if (currentVersion && Array.isArray(filteredImages)) {
        filteredImages = filteredImages.filter((item: any) => {
          if (!item?.version) {
            return false;
          }
          const isGreater = compareVersions(item.version, currentVersion);
          return isGreater;
        });
      }
      setOmsDockerData(filteredImages);
      if (data?.connect_error !== '' || data?.get_images_error !== '' || filteredImages?.length === 0) {
        // 有错误或没有可用镜像，设置失败状态和错误信息
        setCheckConnectionStatus('fail');
        const errorInfo = `${data?.connect_error}\n${data?.get_images_error}`;
        setCheckErrorInfo(filteredImages?.length === 0 ? noAvailableImageErrorInfo : errorInfo);
      } else {
        // 成功获取镜像列表
        setCheckConnectionStatus('success');
        setCheckErrorInfo('');
      }
    },
    onError: (error: any) => {
      // 网络错误或其他异常
      setCheckConnectionStatus('fail');
      const errorMsg = error?.response?.data?.detail || error?.message || noAvailableImageErrorInfo;
      setCheckErrorInfo(errorMsg);
    },
  });

  const {
    data: getCurrentUserData,
  } = useRequest(getCurrentUser, {
    defaultParams: [{}],
    onSuccess: ({ data }) => {
      if (data) {
        setOcpConfigData((prev) => ({
          ...prev,
          currentUser: data,
        }));
      }
    },
  });

  const currentUser = getCurrentUserData?.data;
  const defaultPath = currentUser === 'root' ? '/root/upgrade_tmp_data' : `/home/${currentUser}/oms/upgrade_tmp_data`;

  // 当 currentUser 有值且 upgrade_mode 为 online 时，设置 path 默认值
  useEffect(() => {
    if (currentUser && updateType === 'online') {
      // 延迟设置，确保表单字段已渲染
      const timer = setTimeout(() => {
        // 只有当 ocpConfigData.path 没有值时才设置默认值
        const currentPath = ocpConfigData?.path || form.getFieldValue('path');
        if (!currentPath) {
          form.setFieldsValue({
            path: defaultPath,
          });
          // 同时更新 ocpConfigData
          setOcpConfigData((prev) => ({
            ...prev,
            path: defaultPath,
          }));
        }
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [currentUser, updateType, form]);


  const oceanBaseInfo = {
    group: intl.formatMessage({
      id: 'OBD.pages.Oms.Update.Component.DeployConfig.Product',
      defaultMessage: '产品',
    }),
    key: 'database',
    content: [
      {
        key: 'oms',
        name: 'OMS',
        onlyAll: false,
        desc: intl.formatMessage({
          id: 'OBD.pages.Oms.Update.Component.DeployConfig.OmsDescription',
          defaultMessage: '是 OceanBase 数据库一站式数据传输和同步的产品。是集数据迁移、实时数据同步和增量数据订阅于一体的数据传输服务。',
        }),
        doc: OMS_DOCS,
        version_info: omsUpgradeInfo?.dest_versions
      },
    ],
  };

  const prevStep = () => {
    setOcpConfigData({});
    setErrorVisible(false);
    setErrorsList([]);
    history.push('/guide?update');
  };

  const nextStep = () => {
    setNextLoading(true);
    // 设置标志，避免 nameValidator 触发 API 请求
    isNextStepRef.current = true;

    form.validateFields().then(() => {
      try {
        const allFormValues = form.getFieldsValue();
        const isObdInstall = (allFormValues?.install_type || installType) === 'obd_install';
        const baseConfig = ocpConfigData || {};

        // 获取目标版本号（优先级：baseConfig > 表单值 > omsUpgradeInfo 第一个版本）
        const targetVersion = baseConfig?.version
          || allFormValues?.version
          || (isObdInstall ? omsUpgradeInfo?.dest_versions?.[0]?.version : undefined);

        // 获取镜像名称
        const getImageName = (): string | undefined => {
          if (!targetVersion) return undefined;

          if (isObdInstall) {
            // OBD 部署：从 omsUpgradeInfo 获取
            return omsUpgradeInfo?.dest_versions?.find((item: any) => item.version === targetVersion)?.name;
          } else {
            // 非 OBD 部署：从 omsDockerData 获取
            if (omsDockerData && Array.isArray(omsDockerData)) {
              return omsDockerData.find((item: any) => item.version === targetVersion)?.name
                || omsDockerData[0]?.name;
            }
          }
          return undefined;
        };

        // 构建配置数据：先合并 baseConfig 和表单值，再设置关键字段
        const newOcpConfigData: any = {
          ...baseConfig,
          ...allFormValues,
          // 核心字段（优先级：表单值 > 状态值 > baseConfig值）
          install_type: allFormValues?.install_type ?? installType ?? baseConfig?.install_type ?? 'obd_install',
          upgrade_mode: allFormValues?.upgrade_mode ?? updateType ?? baseConfig?.upgrade_mode ?? 'offline',
          cluster_name: formClusterName,
          // 版本和镜像相关字段
          version: targetVersion || baseConfig?.version,
          image_name: getImageName(),
          current_version: omsUpgradeInfo?.current_version ?? baseConfig?.current_version,
        };

        // 非 OBD 部署的字段
        if (!isObdInstall) {
          Object.assign(newOcpConfigData, {
            host: allFormValues?.host ?? baseConfig?.host,
            container_name: allFormValues?.container_name ?? baseConfig?.container_name,
            user: allFormValues?.user ?? baseConfig?.user,
            password: allFormValues?.password ?? baseConfig?.password,
            port: allFormValues?.port ?? baseConfig?.port,
          });
        }

        // online 模式需要 path 字段
        if (newOcpConfigData.upgrade_mode === 'online') {
          newOcpConfigData.path = allFormValues?.path ?? baseConfig?.path;
        }
        // 更新状态
        setOcpConfigData(newOcpConfigData);
        setCurrent(current + 1);
        setErrorVisible(false);
        setErrorsList([]);
        setNextLoading(false);
        isNextStepRef.current = false;
      } catch (error) {
        console.error('nextStep 执行错误:', error);
        setNextLoading(false);
        isNextStepRef.current = false;
      }
    }).catch(() => {
      setNextLoading(false);
      isNextStepRef.current = false;
    });
  };

  const obdInstall = (form.getFieldsValue()?.install_type) === 'obd_install'

  const handleCheckConnection = async () => {
    const { host, container_name, user, password, port } = form.getFieldsValue();
    const { data: publicKey } = await getPublicKey();
    const data = {
      host,
      container_name,
      user,
      password: password ? encrypt(password, publicKey) : encrypt('', publicKey),
      port,
    }
    const body = {
      username: user.trim(),
      password: password ? encrypt(password, publicKey) : encrypt('', publicKey),
      port,
    }
    if (formClusterName) {
      getTakeOverOms({ cluster_name: formClusterName }, data).then(({ data }) => {
        if (data?.success) {
          // 确保 currentVersionRef 已更新
          if (data?.version && !currentVersionRef.current) {
            currentVersionRef.current = data.version;
          }
          omsDocker({
            ...body,
            oms_servers: data?.nodes,
          })
        }
      })

    } else {
      message.error(intl.formatMessage({
        id: 'OBD.pages.Oms.Update.Component.DeployConfig.PleaseCompleteDeploymentName',
        defaultMessage: '请完善部署名称',
      }))
    }
  };

  // 当 ClusterName 变化时，获取 OMS 升级信息
  useEffect(() => {
    if (formClusterName && obdInstall) {
      getOmsUpgrade({ name: formClusterName });
    }
  }, [formClusterName]);


  // 当镜像数据加载完成且未设置选中值时，自动设置为第一个值
  useEffect(() => {
    if (omsDockerData?.length > 0 && omsTakeoverData?.success === true && !obdInstall) {
      setCheckConnectionStatus('success');
      const firstItem = omsDockerData[0];
      if (firstItem?.version) {
        setOcpConfigData((prev: any) => ({ ...prev, version: firstItem.version }));
        // 同时更新表单值
        form.setFieldsValue({
          version: firstItem.version,
        });
      }
    } else if (omsTakeoverData?.success === false) {
      setCheckConnectionStatus('fail');
    }
  }, [omsDockerData, omsTakeoverData]);

  // 当版本数据加载完成后，自动设置第一个版本为默认值
  useEffect(() => {
    if (omsUpgradeInfo?.dest_versions && Array.isArray(omsUpgradeInfo.dest_versions) && omsUpgradeInfo.dest_versions.length > 0 && obdInstall) {
      // 如果还没有设置 image，则默认选择第一个版本
      setOcpConfigData((prevConfigData) => {
        if (!prevConfigData?.version) {
          const firstVersion = omsUpgradeInfo.dest_versions[0]?.version;
          if (firstVersion) {
            return { ...prevConfigData, version: firstVersion };
          }
        }
        return prevConfigData;
      });
    }
  }, [omsUpgradeInfo?.dest_versions]);

  useEffect(() => {
    if (ocpConfigData?.install_type) {
      setInstallType(ocpConfigData?.install_type);
    }
  }, [ocpConfigData?.install_type]);

  return (
    <>
      <Spin spinning={getOmsUpgradeLoading || getClusterListLoading}>
        <Space className={styles.spaceWidth} direction="vertical" size="middle">
          <ProForm
            form={form}
            initialValues={{
              install_type: ocpConfigData?.install_type || 'obd_install',
              upgrade_mode: ocpConfigData?.upgrade_mode || 'offline',
              obd_cluster_name: ocpConfigData?.cluster_name,
              not_obd_cluster_name: ocpConfigData?.cluster_name,
              path: ocpConfigData?.path || defaultPath,
              host: ocpConfigData?.host,
              container_name: ocpConfigData?.container_name,
              user: ocpConfigData?.user,
              password: ocpConfigData?.password,
              port: ocpConfigData?.port,
              version: ocpConfigData?.version,
            }}
            layout="vertical"
            submitter={false}
          >
            <ProCard
              headStyle={{ color: '#132039' }}
              bodyStyle={{ paddingBottom: 0 }}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.Update.Component.DeployConfig.DeploymentSource',
                defaultMessage: '部署来源',
              })}
              className="card-padding-bottom-24"
            >

              <ProFormItem
                name="install_type"
                label={intl.formatMessage({
                  id: 'OBD.pages.Oms.Update.Component.DeployConfig.OriginalDeploymentMethod',
                  defaultMessage: '原部署方式',
                })}
                rules={[
                  {
                    required: true,
                    message: intl.formatMessage({
                      id: 'OBD.src.component.MySelect.PleaseSelect',
                      defaultMessage: '请选择',
                    }),
                  },
                ]}
                validateTrigger={['onBlur', 'onChange']}
              >
                <Radio.Group
                  value={installType}
                  onChange={(e) => {
                    setInstallType(e.target.value);
                    // 同时更新表单值
                    form.setFieldsValue({
                      install_type: e.target.value,
                    });

                  }}
                >
                  <Radio value="obd_install">{intl.formatMessage({
                    id: 'OBD.pages.Oms.Update.Component.DeployConfig.ObdDeployment',
                    defaultMessage: 'obd 部署',
                  })}</Radio>
                  <Radio value="not_obd_install">{intl.formatMessage({
                    id: 'OBD.pages.Oms.Update.Component.DeployConfig.NonObdDeployment',
                    defaultMessage: '非 obd 部署',
                  })}</Radio>
                </Radio.Group>
              </ProFormItem>
              {
                installType === 'obd_install' ?
                  <ProFormItem
                    name="obd_cluster_name"
                    label={intl.formatMessage({
                      id: 'OBD.pages.Oms.Update.Component.DeployConfig.DeploymentName',
                      defaultMessage: '部署名称',
                    })}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.Oms.Update.Component.DeployConfig.PleaseSelectDeploymentName',
                          defaultMessage: '请选择部署名称',
                        }),
                      },
                    ]}
                    validateTrigger={['onBlur']}
                  >
                    <Select
                      style={commonSelectStyle}
                      options={clusterList?.items?.map((item) => ({
                        label: item.name,
                        value: item.name,
                      }))}
                      placeholder={intl.formatMessage({
                        id: 'OBD.src.component.MySelect.PleaseSelect',
                        defaultMessage: '请选择',
                      })}
                    />
                  </ProFormItem> :
                  <ProFormItem
                    name="not_obd_cluster_name"
                    label={intl.formatMessage({
                      id: 'OBD.pages.Oms.Update.Component.DeployConfig.DeploymentName',
                      defaultMessage: '部署名称',
                    })}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.Oms.Update.Component.DeployConfig.PleaseEnterDeploymentName',
                          defaultMessage: '请输入部署名称',
                        }),
                      },
                      {
                        pattern: clusterNameReg,
                        message: intl.formatMessage({
                          id: 'OBD.pages.Obdeploy.InstallConfig.ItStartsWithALetter',
                          defaultMessage:
                            '以英文字母开头、英文或数字结尾，可包含英文、数字和下划线，且长度为 2 ~ 32',
                        }),
                      },
                      { validator: nameValidator },
                    ]}
                    validateTrigger={['onBlur']}

                  >
                    <Input
                      style={commonSelectStyle}
                      onBlur={() => {
                        // 输入完成后触发校验
                        form.validateFields(['not_obd_cluster_name']).catch(() => { });
                      }}
                      disabled={checkConnectionStatus === 'success' && !isEmpty(omsTakeoverData)}
                    />
                  </ProFormItem>
              }


            </ProCard>
            {
              !obdInstall && <>
                <ProCard title={intl.formatMessage({
                  id: 'OBD.pages.Oms.Update.Component.DeployConfig.ConnectionInformation',
                  defaultMessage: '连接信息',
                })}
                  className="card-header-padding-top-0 card-padding-bottom-24 "
                >
                  <Row gutter={[0, 0]}  >
                    <Col span={24} >
                      <Space size="large" >
                        <ProFormText
                          name={'host'}
                          label={intl.formatMessage({
                            id: 'OBD.pages.Oms.Update.Component.DeployConfig.OmsNodeAddress',
                            defaultMessage: 'OMS 节点地址',
                          })}
                          fieldProps={{ style: commonSelectStyle }}
                          placeholder={intl.formatMessage({
                            id: 'OBD.src.component.MyInput.PleaseEnter',
                            defaultMessage: '请输入',
                          })}
                          disabled={checkConnectionStatus === 'success' && !isEmpty(omsTakeoverData)}
                          extra={
                            <>
                              <div>{intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.ProvideOmsNodeAddress',
                                defaultMessage: '请提供 OMS 服务任意一个 OMS 节点的访问地址和',
                              })}</div>
                              <div>{intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.AccessInformation',
                                defaultMessage: '访问信息, 以便系统能够成功连接并获取 OMS 服务',
                              })}</div>
                              <div>{intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.RelevantData',
                                defaultMessage: '的相关数据',
                              })}</div>
                            </>
                          }
                          rules={[
                            {
                              required: true,
                              message: intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.PleaseEnterAccessAddress',
                                defaultMessage: '请输入访问地址',
                              }),
                            }, {
                              pattern: serverReg,
                              message: intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.PleaseEnterCorrectAccessAddress',
                                defaultMessage: '请输入正确的访问地址',
                              }),
                            }
                          ]}
                        />
                        <ProFormText
                          name={'container_name'}
                          label={intl.formatMessage({
                            id: 'OBD.pages.Oms.Update.Component.DeployConfig.OmsContainerName',
                            defaultMessage: 'OMS 容器名称',
                          })}
                          fieldProps={{ style: commonSelectStyle }}
                          placeholder={intl.formatMessage({
                            id: 'OBD.src.component.MyInput.PleaseEnter',
                            defaultMessage: '请输入',
                          })}
                          disabled={checkConnectionStatus === 'success' && !isEmpty(omsTakeoverData)}
                          extra={
                            <>
                              <br />
                              <br />
                              <br />
                            </>
                          }
                          rules={[
                            {
                              required: true,
                              message: intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.PleaseEnterOmsContainerName',
                                defaultMessage: '请输入 OMS 容器名称',
                              }),
                            },
                          ]}
                        />
                      </Space>
                      <Space size="large">
                        <ProFormText
                          name={'user'}
                          label={intl.formatMessage({
                            id: 'OBD.pages.Oms.Update.Component.DeployConfig.Username',
                            defaultMessage: '用户名',
                          })}
                          fieldProps={{ style: commonSelectStyle }}
                          placeholder={intl.formatMessage({
                            id: 'OBD.src.component.MyInput.PleaseEnter',
                            defaultMessage: '请输入',
                          })}
                          required={false}
                          disabled={checkConnectionStatus === 'success' && !isEmpty(omsTakeoverData)}
                          rules={[
                            {
                              required: true,
                              message: intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.PleaseEnterUsername',
                                defaultMessage: '请输入用户名',
                              }),
                            },

                          ]}
                          extra={
                            <>
                              <div>{intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.ProvideHostUser',
                                defaultMessage: '需提供主机操作系统的用户以便安装程序进行自动化',
                              })}</div>
                              <div>{intl.formatMessage({
                                id: 'OBD.pages.Oms.Update.Component.DeployConfig.UserNeedsSudoPermission',
                                defaultMessage: '配置，该用户名需具有 sudo 权限',
                              })}</div>
                            </>
                          }
                        />
                        <ProFormText
                          name={'password'}
                          style={commonSelectStyle}
                          disabled={checkConnectionStatus === 'success' && !isEmpty(omsTakeoverData)}
                          label={
                            <span className={styles.labelText}>
                              {intl.formatMessage({
                                id: 'OBD.component.MetaDBConfig.UserConfig.PasswordOptional',
                                defaultMessage: '密码（可选）',
                              })}
                            </span>
                          }
                          extra={
                            <>
                              <br />
                              <br />
                            </>
                          }
                        >
                          <Input.Password
                            autoComplete="new-password"
                            placeholder={intl.formatMessage({
                              id: 'OBD.component.MetaDBConfig.UserConfig.IfYouHaveConfiguredPassword',
                              defaultMessage: '如已配置免密登录，则无需再次输入密码',
                            })}
                          />
                        </ProFormText>
                        <ProFormDigit
                          style={{ padding: 0 }}
                          name={'port'}
                          initialValue={22}
                          label={
                            <span className={styles.labelText}>
                              {intl.formatMessage({
                                id: 'OBD.component.MetaDBConfig.UserConfig.SshPort',
                                defaultMessage: 'SSH端口',
                              })}
                            </span>
                          }
                          disabled={checkConnectionStatus === 'success' && !isEmpty(omsTakeoverData)}
                          fieldProps={{ style: { width: 120 } }}
                          placeholder={intl.formatMessage({
                            id: 'OBD.component.MetaDBConfig.UserConfig.PleaseEnter',
                            defaultMessage: '请输入',
                          })}
                          extra={
                            <>
                              <br />
                              <br />
                            </>
                          }
                          rules={[
                            {
                              required: true,
                              message: intl.formatMessage({
                                id: 'OBD.component.MetaDBConfig.UserConfig.PleaseEnter',
                                defaultMessage: '请输入',
                              }),
                            },
                          ]}
                        />
                      </Space>
                    </Col>
                    <Col span={24}>
                      <Button
                        loading={takeOverOmsLoading || omsDockerLoading}
                        onClick={() => {
                          // 开始新的校验时，重置状态但不清空错误信息（等校验结果出来后再更新）
                          setCheckConnectionStatus('unchecked');
                          setCheckErrorInfo('');
                          handleCheckConnection()
                        }}
                      >
                        接管
                      </Button>
                      {checkConnectionStatus === 'success' && (
                        <span style={{ color: 'rgba(77,204,162,1)', marginLeft: 12 }}>
                          <CheckCircleFilled />
                          <span style={{ marginLeft: 5 }}>
                            当前接管成功
                          </span>
                        </span>
                      )}
                      {checkConnectionStatus === 'fail' && checkErrorInfo && (
                        <span style={{ color: 'rgba(255,75,75,1)', marginLeft: 12 }}>
                          <CloseCircleFilled />
                          <span style={{ marginLeft: 5 }}>
                            {
                              checkErrorInfo
                            }
                          </span>
                        </span>
                      )}

                    </Col>
                  </Row>
                </ProCard>
              </>
            }
            <ProCard
              headStyle={{ color: '#132039' }}
              title={
                <>
                  <span style={{ color: '#132039' }}>
                    升级配置
                  </span>
                </>
              }
              className={`card-header-padding-top-0 card-padding-bottom-24 ${obdInstall ? 'card-padding-top-0' : ''}`}
            >
              {
                obdInstall ? <Space
                  className={styles.spaceWidth}
                  direction="vertical"
                  size="middle"
                >
                  <ProCard
                    className={`${styles.componentCard}`}
                    type="inner"
                  >
                    <Table
                      columns={getColumns()}
                      pagination={false}
                      dataSource={oceanBaseInfo?.content}
                      rowKey="name"
                    />
                  </ProCard>
                </Space>
                  :
                  <ProFormItem
                    name={'version'}
                    label={'OMS Docker 镜像'}
                    style={commonSelectStyle}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.components.NodeConfig.PleaseSelect',
                          defaultMessage: '请选择',
                        }),
                      },
                    ]}
                  >
                    {(() => {
                      // 确保版本列表是数组
                      const versionList = Array.isArray(omsDockerData) ? omsDockerData : [];

                      // 获取当前选中的值，格式为 version 字符串
                      const getCurrentValue = () => {
                        // 如果 version 明确设置为 null，说明被清空了，返回 undefined
                        if (ocpConfigData?.version === null) {
                          return undefined;
                        }
                        if (ocpConfigData?.version) {
                          // 如果 configData.version 存在，直接使用
                          return ocpConfigData.version;
                        }
                        // 如果 ocpConfigData 不存在或为空对象，且版本列表有数据，默认使用第一个版本
                        if (versionList.length > 0 && (!ocpConfigData || Object.keys(ocpConfigData).length === 0)) {
                          return versionList[0]?.version;
                        }
                        return undefined;
                      };

                      // 获取当前选中的项，用于显示版本号
                      const getSelectedItem = () => {
                        const currentValue = getCurrentValue();
                        if (!currentValue) return null;
                        return versionList.find((item: any) => item.version === currentValue) || versionList[0];
                      };

                      const selectedItem = getSelectedItem();
                      const currentValue = getCurrentValue();
                      const isDisabled = checkConnectionStatus !== 'success';

                      return (
                        <Tooltip
                          title={isDisabled ? intl.formatMessage({
                            id: 'OBD.pages.Oms.InstallConfig.ConfigureAndValidateBeforeSelecting',
                            defaultMessage: '配置完上面的信息并校验通过才可选择',
                          }) : versionList[0]?.version}
                        >
                          <Select
                            labelInValue
                            value={currentValue && selectedItem ? {
                              label: (
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                  <span>V {selectedItem.version?.split('feature_')[1]?.toUpperCase() || selectedItem.version}</span>
                                  {selectedItem.version?.includes('ce') ? (
                                    <Tag className="default-tag ml-8" style={{ marginLeft: 8 }}>
                                      {intl.formatMessage({
                                        id: 'OBD.component.DeployConfig.CommunityEdition',
                                        defaultMessage: '社区版',
                                      })}
                                    </Tag>
                                  ) : (
                                    <Tag className="blue-tag ml-8" style={{ marginLeft: 8 }}>
                                      {intl.formatMessage({
                                        id: 'OBD.component.DeployConfig.CommercialEdition',
                                        defaultMessage: '商业版',
                                      })}
                                    </Tag>
                                  )}
                                </div>
                              ),
                              value: currentValue,
                            } : undefined}
                            onChange={(option) => {
                              setOcpConfigData({
                                ...ocpConfigData,
                                version: option.value,
                              });
                              // 同时更新表单值
                              form.setFieldsValue({
                                version: option.value,
                              });
                            }}
                            style={{ width: '100%' }}
                            popupClassName={styles?.popupClassName}
                            disabled={isDisabled}
                          >
                            {versionList.length > 0 ? versionList.map((item: any) => {
                              const versionText = item.version?.split('feature_')[1]?.toUpperCase() || item.version;
                              return (
                                <Select.Option value={item.version} key={item.version}>
                                  <div style={{ display: 'flex', alignItems: 'center' }}>
                                    V {versionText}
                                    {item.version?.includes('ce') ? (
                                      <Tag className="default-tag ml-8">
                                        {intl.formatMessage({
                                          id: 'OBD.component.DeployConfig.CommunityEdition',
                                          defaultMessage: '社区版',
                                        })}
                                      </Tag>
                                    ) : (
                                      <Tag className="blue-tag ml-8">
                                        {intl.formatMessage({
                                          id: 'OBD.component.DeployConfig.CommercialEdition',
                                          defaultMessage: '商业版',
                                        })}
                                      </Tag>
                                    )}
                                  </div>
                                </Select.Option>
                              );
                            }) : null}
                          </Select>
                        </Tooltip>
                      );
                    })()}
                  </ProFormItem>
              }

            </ProCard>

            <ProCard title={intl.formatMessage({
              id: 'OBD.pages.Oms.Update.Component.DeployConfig.UpgradeMethod',
              defaultMessage: '升级方式',
            })}>
              <ProFormItem
                name="upgrade_mode"
                validateTrigger={['onBlur', 'onChange']}
              >
                <Radio.Group
                  value={updateType}
                  onChange={(e) => {
                    setUpdateType(e.target.value);
                    // 同时更新表单值
                    form.setFieldsValue({
                      upgrade_mode: e.target.value,
                      path: '',
                    });
                    setOcpConfigData({
                      ...ocpConfigData,
                      path: '',
                    })
                  }}
                  style={updateType === 'online' ? { marginBottom: 24 } : {}}
                >
                  <Radio value="offline">
                    {intl.formatMessage({
                      id: 'OBD.pages.Oms.Update.Component.DeployConfig.OfflineUpgrade',
                      defaultMessage: '停服升级',
                    })}
                    <Tooltip title={intl.formatMessage({
                      id: 'OBD.pages.Oms.Update.Component.DeployConfig.OfflineUpgradeTooltip',
                      defaultMessage: '通过部署新版镜像容器来替换旧版容器，升级过程中运行链路将出现短暂中断。',
                    })}>
                      <QuestionCircleOutlined style={{ color: '#8592AD', marginLeft: '4px' }} />
                    </Tooltip>
                  </Radio>
                  <Radio value="online">
                    {intl.formatMessage({
                      id: 'OBD.pages.Oms.Update.Component.DeployConfig.OnlineUpgrade',
                      defaultMessage: '在线升级',
                    })}
                    <Tooltip title={intl.formatMessage({
                      id: 'OBD.pages.Oms.Update.Component.DeployConfig.OnlineUpgradeTooltip',
                      defaultMessage: '在原有容器内直接替换组件包实现升级，确保运行链路全程无中断。',
                    })}>
                      <QuestionCircleOutlined style={{ color: '#8592AD', marginLeft: '4px' }} />
                    </Tooltip>
                  </Radio>
                </Radio.Group>
                {
                  updateType === 'online' &&
                  <ProFormText
                    name={'path'}
                    label={intl.formatMessage({
                      id: 'OBD.pages.Oms.Update.Component.DeployConfig.UpgradeFilePath',
                      defaultMessage: '存放升级文件路径',
                    })}
                    fieldProps={{ style: { width: 400 } }}
                    placeholder={defaultPath}
                    required={false}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.Oms.InstallConfig.PleaseEnterPath',
                          defaultMessage: '请输入路径',
                        }),
                      },
                      pathRule,
                    ]}
                  />
                }
              </ProFormItem>
            </ProCard>
          </ProForm>
        </Space>
      </Spin >
      <CustomFooter>
        <ExitBtn />
        <Button
          data-aspm-click="ca54435.da43437"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.component.DeployConfig.DeploymentConfigurationPreviousStep',
            defaultMessage: '部署配置-上一步',
          })}
          data-aspm-param={``}
          data-aspm-expo
          onClick={prevStep}
        >
          {intl.formatMessage({
            id: 'OBD.component.DeployConfig.PreviousStep',
            defaultMessage: '上一步',
          })}
        </Button>
        <Button
          data-aspm-click="ca54435.da43438"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.component.DeployConfig.DeploymentConfigurationNextStep',
            defaultMessage: '部署配置-下一步',
          })}
          data-aspm-param={``}
          data-aspm-expo
          type="primary"
          disabled={
            getOmsUpgradeLoading ||
            takeOverOmsLoading ||
            (obdInstall ?
              (isEmpty(getOmsUpgradeInfoRes) || !omsUpgradeInfo?.dest_versions?.length)
              : (checkConnectionStatus === 'fail' || checkConnectionStatus === 'unchecked'))
          }
          onClick={nextStep}
          loading={nextLoading}
        >
          {intl.formatMessage({
            id: 'OBD.component.DeployConfig.NextStep',
            defaultMessage: '下一步',
          })}
        </Button>
      </CustomFooter>
    </>
  );
}
