import {
  clusterNameReg,
  getErrorInfo,
  handleQuit,
  hasDuplicateIPs,
} from '@/utils';
import { getAllServers } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  DeleteOutlined,
} from '@ant-design/icons';
import { EditableFormInstance, EditableProTable, ProCard, ProForm, ProFormDigit, ProFormRadio, ProFormText } from '@ant-design/pro-components';
import {
  Button,
  Checkbox,
  Input,
  message,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { flattenDeep, } from 'lodash';
import { useEffect, useRef, useState } from 'react';
import { getLocale, history, useModel } from 'umi';
import {
  commonSelectStyle,
  pathRule,
} from '../constants';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';
import ServerTags from './ServerTags';
import validator from 'validator';
import InputPort from '@/component/InputPort';
import { omsDockerImages } from '@/services/component-change/componentChange';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import { encrypt } from '@/utils/encrypt';

type TableDataType = {
  key: string;
  name: string;
  onlyAll: boolean;
  desc: string;
  doc: string;
};

interface OMSDBConfig {
  id: string;
  name?: string;
  rootservice?: string;
  servers?: string[];
  cm_region: string;
  cm_location: string;
  cm_nodes: string[];
  cm_url?: string;
  cm_is_default?: boolean;
}

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export default function InstallConfig() {
  const {
    setCurrentStep,
    configData,
    setConfigData,
    DOCS_USER,
    setIsFirstTime,
    handleQuitProgress,
    getInfoByName,
    setErrorVisible,
    errorsList,
    setErrorsList,
    aliveTokenTimer,
    omsDockerData,
    setOmsDockerData,
    setNameIndex,
    setSelectedOmsType,
    OMS_DOCS
  } = useModel('global');


  const [form] = ProForm.useForm();
  const finalValidate = useRef<boolean>(false);
  const [editableForm] = ProForm.useForm<OMSDBConfig>();
  const tableFormRef = useRef<EditableFormInstance<OMSDBConfig>>();
  const [lastDeleteServer, setLastDeleteServer] = useState('');
  const isBlurTriggered = useRef<boolean>(false);
  const [checkStatus, setCheckStatus] = useState<'unchecked' | 'fail' | 'success'>('unchecked');
  const [checkOmsErrorInfo, setCheckOmsErrorInfo] = useState<string>('');

  const initDBConfigData = configData?.regions?.length
    ? configData?.regions?.map((item: any, index: number) => ({
      id: (Date.now() + index).toString(),
      ...item,
      cm_nodes: (item as any)?.cm_nodes || [],
      // 如果 configData 中有 cm_is_default，使用它；否则第一个项目默认勾选
      cm_is_default: item.cm_is_default !== undefined ? item.cm_is_default : (index === 0),
    }))
    : [];

  // 初始化 selectedFavorId：从 initDBConfigData 中找到 cm_is_default: true 的项
  const initSelectedFavorId = initDBConfigData.find((item: OMSDBConfig) => item.cm_is_default)?.id;

  const [dbConfigData, setDBConfigData] =
    useState<OMSDBConfig[]>(initDBConfigData);
  const [editableKeys, setEditableRowKeys] = useState<React.Key[]>([]);
  const [selectedFavorId, setSelectedFavorId] = useState<string | undefined>(initSelectedFavorId);

  // all servers
  const [allOBServer, setAllOBServer] = useState<string[]>([]);
  // all zone servers
  const [allZoneOBServer, setAllZoneOBServer] = useState<any>({});

  // 当前 OMS 选择的节点环境是否为单节点
  const standAlone = form.getFieldValue('mode') === 'compact' || form.getFieldValue('mode') === 'standard';


  // 同步 editableKeys 和 dbConfigData
  useEffect(() => {
    const keys = dbConfigData.map((item) => item.id);
    setEditableRowKeys(keys);
  }, [dbConfigData]);

  // 初始化时设置 editableKeys
  useEffect(() => {
    if (dbConfigData.length > 0 && editableKeys.length === 0) {
      const keys = dbConfigData.map((item) => item.id);
      setEditableRowKeys(keys);
    }
  }, [dbConfigData, editableKeys.length]);

  // 同步 selectedFavorId 和 dbConfigData 中的 cm_is_default
  // 只在初始化时或数据不一致时同步，避免覆盖用户的更改
  useEffect(() => {
    const favorItem = dbConfigData.find((item) => item.cm_is_default);
    const selectedItem = dbConfigData.find((item) => item.id === selectedFavorId);

    // 如果 selectedFavorId 对应的项已经有 cm_is_default: true，说明是用户操作，不修改
    if (selectedItem && selectedItem.cm_is_default) {
      return;
    }

    // 如果 dbConfigData 中有 cm_is_default: true 的项
    if (favorItem) {
      // 如果 selectedFavorId 为空或对应的项不存在，同步到 favorItem
      if (!selectedFavorId || !selectedItem) {
        setSelectedFavorId(favorItem.id);
      }
    } else if (!favorItem && dbConfigData.length > 0) {
      // 如果 dbConfigData 中没有 cm_is_default: true 的项
      // 只有在 selectedFavorId 为空或对应的项不存在时，才设置第一个为默认
      if (!selectedFavorId || !selectedItem) {
        setSelectedFavorId(dbConfigData[0].id);
        const updatedData = dbConfigData.map((item: OMSDBConfig, idx: number) => ({
          ...item,
          cm_is_default: idx === 0,
        }));
        setDBConfigData(updatedData);
      }
    }
  }, [dbConfigData]);

  // 使用 useWatch 监听表单 auth 字段的变化
  const formAuthUsername = ProForm.useWatch(['auth', 'username'], form);
  const formAuthPassword = ProForm.useWatch(['auth', 'password'], form);
  const formAuthSshPort = ProForm.useWatch(['auth', 'ssh_port'], form);


  // 初始化或重新初始化 dbConfigData 的函数
  const initDBConfigDataByMode = (mode?: string, forceInit = false) => {
    const currentMode = mode || form.getFieldValue('mode') || configData?.mode || 'standard';
    const isStandAlone = currentMode === 'compact' || currentMode === 'standard';

    // 如果有已保存的区域配置，优先使用
    const init = configData?.regions?.map((item: any, index: number) => ({
      id: (Date.now() + index).toString(),
      ...item,
      cm_nodes: (item as any)?.cm_nodes || [],
      // 如果 configData 中有 cm_is_default，使用它；否则第一个项目默认勾选
      cm_is_default: item.cm_is_default !== undefined ? item.cm_is_default : (index === 0),
    }));

    if (
      !forceInit &&
      configData?.regions?.length &&
      init?.every((item: any) => item.cm_nodes.length > 0)
    ) {
      setDBConfigData(init);

      // 初始化 selectedFavorId：从 init 中找到 cm_is_default: true 的项
      const favorItem = init.find((item: OMSDBConfig) => item.cm_is_default);
      if (favorItem) {
        setSelectedFavorId(favorItem.id);
      } else if (init.length > 0) {
        // 如果没有找到，设置第一个为默认
        setSelectedFavorId(init[0].id);
        // 更新第一个项的 cm_is_default
        const updatedInit = init.map((item: OMSDBConfig, idx: number) => ({
          ...item,
          cm_is_default: idx === 0,
        }));
        setDBConfigData(updatedInit);
      }

      // 初始化 allOBServer 和 allZoneOBServer
      const initAllServers = getAllServers(init as any, 'cm_nodes');
      setAllOBServer(initAllServers);

      const initAllZoneServers: any = {};
      init.forEach((item: any) => {
        initAllZoneServers[`${item.id}`] = item.cm_nodes || [];
      });
      setAllZoneOBServer(initAllZoneServers);
    } else {
      if (isStandAlone) {
        const mock = [
          {
            id: (Date.now() + 1).toString(),
            cm_region: 'default',
            cm_location: '1',
            cm_nodes: [],
            cm_url: undefined,
          },
        ];
        setDBConfigData(mock);
      } else {
        const mock = [
          {
            id: (Date.now() + 1).toString(),
            cm_region: 'default-1',
            cm_location: '1',
            cm_nodes: [],
            cm_is_default: true,
            cm_url: undefined,
          },
          {
            id: (Date.now() + 2).toString(),
            cm_region: 'default-2',
            cm_location: '2',
            cm_nodes: [],
            cm_is_default: false,
            cm_url: undefined,
          },
        ];
        setDBConfigData(mock);
        // 设置第一个项目为选中状态
        setSelectedFavorId(mock[0].id);
      }
    }
  };

  useEffect(() => {
    // 只在初始化时执行，或者当 dbConfigData 为空时执行
    if (dbConfigData.length === 0) {
      initDBConfigDataByMode();
    }
  }, [standAlone]);

  // 比较 configData 中的 auth 值与表单中的 auth 值，以及 regions中的nodes 与 configData中的servers
  useEffect(() => {
    // 获取表单中的 auth 值（使用 useWatch 监听到的值）
    const formAuth = {
      username: formAuthUsername,
      password: formAuthPassword,
      ssh_port: formAuthSshPort,
    };

    // 获取 configData 中的 auth 值
    const configAuth = {
      username: configData?.auth?.username,
      password: configData?.auth?.password,
      ssh_port: configData?.auth?.ssh_port,
    };

    // 统一处理字符串：去除前后空格，统一转换为字符串
    const normalizeString = (val: any) => {
      if (val === null || val === undefined) return '';
      return String(val).trim();
    };

    const formUsername = normalizeString(formAuth.username);
    const formPassword = normalizeString(formAuth.password);
    const formSshPort = normalizeString(formAuth.ssh_port);

    const configUsername = normalizeString(configAuth.username);
    const configPassword = normalizeString(configAuth.password);
    const configSshPort = normalizeString(configAuth.ssh_port);

    // 比较 auth 值是否一致
    const isAuthEqual =
      formUsername === configUsername &&
      formPassword === configPassword &&
      formSshPort === configSshPort;

    // 比较 regions 中的 nodes 与 configData 中的 servers
    // 从 dbConfigData（当前 regions）中提取所有 cm_nodes，扁平化并排序
    const currentNodes = flattenDeep(dbConfigData?.map((item: any) => item.cm_nodes || []) || [])
      .filter((node: string) => node && node.trim())
      .map((node: string) => node.trim())
      .sort();

    // 从 configData.servers 中提取节点（逗号分隔的字符串），分割、过滤、排序
    const configServers = (configData?.servers || '')
      .split(',')
      .filter((node: string) => node && node.trim())
      .map((node: string) => node.trim())
      .sort();

    // 比较节点数组是否一致
    const isNodesEqual = JSON.stringify(currentNodes) === JSON.stringify(configServers);

    // 当 omsDockerData 有数据时，如果 auth 或 servers 的数据有变化，checkStatus 变为 unchecked
    const hasOmsDockerData = omsDockerData && omsDockerData.length > 0;

    // 只有当值不一致时才设置为 unchecked
    if (!isAuthEqual || !isNodesEqual) {
      // 值不一样，设置为 unchecked
      // 特别是当 omsDockerData 有数据时，如果 auth 或 servers 有变化，必须设置为 unchecked
      setCheckStatus('unchecked');
      if (hasOmsDockerData) {
        // 只有当 omsDockerData 有数据且值不一致时，才清空 omsDockerData
        setOmsDockerData([]);
      }
    } else if (hasOmsDockerData) {
      // 值一样且 omsDockerData 有数据，设置为 success
      setCheckStatus('success');
    } else {
      // 值一样但 omsDockerData 没有数据，设置为 unchecked（需要校验）
      setCheckStatus('unchecked');
    }
  }, [configData?.auth?.username, configData?.auth?.password, configData?.auth?.ssh_port, configData?.servers, dbConfigData, form, omsDockerData, formAuthUsername, formAuthPassword, formAuthSshPort])


  const {
    run: omsDocker,
    // data: omsDockerData,
    loading: omsDockerLoading
  } = useRequest(omsDockerImages, {
    manual: true,
    onSuccess: ({ data }: any) => {
      // 同步更新 configData，确保表单值和 configData 一致
      if (data?.connect_error !== '' || data?.get_images_error !== '' || data?.length === 0) {
        const errorInfo = `${data?.connect_error}\n${data?.get_images_error}`;
        const defaultErrorInfo = intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ServiceConfig.TheCurrentVerificationFailedPlease',
          defaultMessage: '当前校验失败，请重新输入',
        })
        setCheckOmsErrorInfo(data?.length === 0 ? defaultErrorInfo : errorInfo);
        setCheckStatus('fail');
      } else {
        const formValues = form.getFieldsValue();
        // 从 dbConfigData 中提取所有节点，用于更新 servers 字段
        const allNodes = flattenDeep(dbConfigData?.map((item: any) => item.cm_nodes || []) || [])
          .filter((node: string) => node && node.trim())
          .map((node: string) => node.trim())
          .join(',');

        setConfigData((prev: any) => ({
          ...prev,
          auth: {
            ...prev?.auth,
            ...formValues?.auth,
          },
          regions: dbConfigData,
          servers: allNodes, // 同步更新 servers 字段
        }));
        setCheckStatus('success');
        setOmsDockerData(data?.oms_images?.filter((item: any) => item?.version?.includes('feature_')) || []);
      }
    },
    onError: () => {
      setCheckStatus('fail');
    },
  });

  // 当镜像数据加载完成且未设置选中值时，自动设置为第一个值（name:version 格式）
  useEffect(() => {
    if (omsDockerData?.length > 0 && !configData?.image) {
      setCheckStatus('success');
      const firstItem = omsDockerData[0];
      setConfigData((prev: any) => ({ ...prev, image: `${firstItem.name}:${firstItem.version}` }));
    }
  }, [omsDockerData, configData?.image, setConfigData]);

  const nameValidator = async (_: any, value: string) => {
    if (value) {
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
  };


  const nextStep = () => {
    if (form.getFieldsError(['appname'])[0].errors.length) return;

    const tableFormRefValidate = () => {
      finalValidate.current = true;
      return tableFormRef?.current?.validateFields().then((values) => {
        return values;
      });
    };
    const formValidate = () => {
      return form.validateFields().then((values) => {
        return values;
      });
    };

    Promise.all([tableFormRefValidate(), formValidate()])
      .then((result) => {
        const formValues = result?.[1];

        // 确保 dbConfigData 中的 cm_is_default 与 selectedFavorId 保持一致
        // 优先使用 selectedFavorId 来确定 cm_is_default，确保与勾选框状态一致
        const updatedDBConfigData = dbConfigData.map((item) => {
          // 如果 selectedFavorId 存在，使用它来确定 cm_is_default（这是最准确的）
          if (selectedFavorId !== undefined) {
            return {
              ...item,
              cm_is_default: item.id === selectedFavorId,
            };
          }
          // 如果 selectedFavorId 不存在，使用 dbConfigData 中已有的 cm_is_default 值
          // 确保至少有一个项被设置为默认（第一个项）
          const hasDefaultItem = dbConfigData.some((d) => d.cm_is_default === true);
          if (!hasDefaultItem && dbConfigData.length > 0) {
            // 如果没有默认项，设置第一个为默认
            return {
              ...item,
              cm_is_default: item.id === dbConfigData[0]?.id,
            };
          }
          // 保持原有的 cm_is_default 值（明确转换为布尔值）
          return {
            ...item,
            cm_is_default: Boolean(item.cm_is_default),
          };
        });

        let newComponents: API.Components = {
          regions: updatedDBConfigData,
          servers: updatedDBConfigData?.map((item: any) => item.cm_nodes).join(','),
          ...formValues,
        };

        setConfigData({
          ...configData,
          ...newComponents,
        });

        // 从 configData?.image 中提取 omsType
        // configData?.image 的格式可能是：
        // 1. name:version (如: oms-ce:feature_4.2.12_ce)
        // 2. 完整镜像路径 (如: reg.docker.alibaba-inc.com/oceanbase/oms-ce:feature_4.2.12_ce)
        let omsType: string | undefined;
        if (configData?.image) {
          // 尝试直接从 image 中提取版本号（如果包含 feature_）
          const featureMatch = configData.image.match(/feature_([^:]+)/);
          if (featureMatch && featureMatch[1]) {
            omsType = featureMatch[1];
          } else {
            // 如果无法直接提取，从 omsDockerData 中查找
            // 查找逻辑：匹配 name:version 格式
            const imageParts = configData.image.split(':');
            if (imageParts.length >= 2) {
              const imageName = imageParts[0].split('/').pop(); // 获取镜像名称（去除路径）
              const imageVersion = imageParts[imageParts.length - 1]; // 获取版本部分
              const matchedItem = omsDockerData?.find((item: any) => {
                // 匹配 name 和 version
                return item.name === imageName && item.version === imageVersion;
              });
              if (matchedItem) {
                omsType = matchedItem.version.split('feature_')[1];
              }
            }
          }
        }
        if (omsType) {
          setSelectedOmsType(omsType);
        }
        setCurrentStep(2);
        setIsFirstTime(false);
        setErrorVisible(false);
        setErrorsList([]);
        window.scrollTo(0, 0);
      })
      .finally(() => {
        finalValidate.current = false;
      });
  };

  const columns = [
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.ConnectionInfo.RegionIdentifier',
        defaultMessage: '地域标识',
      }),
      dataIndex: 'cm_location',
      formItemProps: {
        allowClear: false,
      },
      width: 80,
      renderFormItem: () => {
        return <Input disabled style={{ backgroundColor: '#f0f2f5', color: '#000000d9' }} />;
      },
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.ConnectionInfo.EnglishRegionIdentifier',
        defaultMessage: '英文地域标志',
      }),
      dataIndex: 'cm_region',
      width: 140,
      formItemProps: {
        rules: [
          {
            required: true,
            // whitespace: false,
            message: intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.ThisItemIsRequired',
              defaultMessage: '此项是必填项',
            }),
          },
          {
            validator: async (_: any, value: string) => {
              if (!value || !value.trim()) {
                return Promise.resolve();
              }
              const trimmedValue = value.trim();
              const duplicateCount = dbConfigData.filter(
                (item) => item.cm_region?.trim() === trimmedValue
              ).length;
              if (duplicateCount > 1) {
                return Promise.reject(
                  intl.formatMessage({
                    id: 'OBD.pages.Oms.InstallConfig.EnglishRegionIdentifierCannotBeRepeated',
                    defaultMessage: '英文地域标识不能重复',
                  })
                );
              }
              return Promise.resolve();
            },
          },
        ],
      },
    },
    ...(!standAlone
      ? [
        {
          title: intl.formatMessage({
            id: 'OBD.pages.Oms.ConnectionInfo.AccessPriority',
            defaultMessage: '访问优先',
          }),
          dataIndex: 'cm_is_default',
          width: 80,
          renderFormItem: (_: any, config: any) => {
            const { isEditable, record } = config;
            if (!isEditable) return null;

            const isChecked = selectedFavorId === record.id;

            return (
              <Checkbox
                checked={isChecked}
                onChange={(e) => {
                  const checked = e.target.checked;

                  if (checked) {
                    // 勾选当前项，取消其他所有项
                    setSelectedFavorId(record.id);
                    const newData = dbConfigData.map(item => ({
                      ...item,
                      cm_is_default: item.id === record.id
                    }));
                    setDBConfigData(newData);
                  } else {
                    // 取消勾选当前项
                    setSelectedFavorId(undefined);
                    const newData = dbConfigData.map(item => ({
                      ...item,
                      cm_is_default: false
                    }));
                    setDBConfigData(newData);
                  }
                }}
              />
            );
          },
        },
      ]
      : []),
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.ConnectionInfo.Node',
        defaultMessage: '节点',
      }),
      dataIndex: 'cm_nodes',
      formItemProps: {
        validateFirst: true,
        rules: [
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.ThisItemIsRequired',
              defaultMessage: '此项是必填项',
            }),
          },
          {
            validator: (_: any, value: string[]) => {
              if (value.length !== 0) {
                let inputServer = [];
                const currentV = value[value.length - 1];
                inputServer = allOBServer.concat(currentV);
                const serverValue = finalValidate.current
                  ? allOBServer
                  : inputServer;

                if (value?.some((item) => !validator.isIP(item))) {
                  return Promise.reject(
                    intl.formatMessage({
                      id: 'OBD.pages.Oms.InstallConfig.PleaseEnterCorrectIpNode',
                      defaultMessage: '请输入正确的 IP 节点',
                    }),
                  );
                } else if (
                  (hasDuplicateIPs(value) && dbConfigData.length === 1) ||
                  (hasDuplicateIPs(serverValue) && dbConfigData.length > 1)
                ) {
                  return Promise.reject(
                    intl.formatMessage({
                      id: 'OBD.component.NodeConfig.TheValidatorNode2',
                      defaultMessage: '禁止输入重复节点',
                    }),
                  );
                }
              }
              return Promise.resolve();
            },
          },
        ],
      },
      renderFormItem: (_: any, { isEditable, record }: any) => {
        return isEditable ? (
          <ServerTags
            name={record.id}
            standAlone={form.getFieldValue('mode') === 'standard'}
            setLastDeleteServer={setLastDeleteServer}
          />
        ) : null;
      },
    },

    {
      title: <div>
        CM 访问地址
        <span style={{ fontSize: 13 }}>
          （非VIP/DNS时端口必须和CM端口必须一致)
        </span>

      </div>,
      dataIndex: 'cm_url',
      // width: 280,
      formItemProps: (_: any, config: any) => {
        const { record } = config;
        return {
          validateFirst: true,
          validateTrigger: ['onChange'],
          rules: [
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.pages.components.NodeConfig.ThisOptionIsRequired',
                defaultMessage: '此项是必选项',
              }),
            },
            {
              validator: async (_: any, value: string) => {
                if (!value) {
                  return Promise.resolve();
                }
                // 验证 URL 格式：http://ip或域名:端口 或 https://ip或域名:端口
                // 支持域名和 IP 地址，域名可以包含字母、数字、连字符和点
                const urlPattern = /^https?:\/\/[\w.-]+:\d+$/;
                if (!urlPattern.test(value)) {
                  return Promise.reject(intl.formatMessage({
                    id: 'OBD.pages.Oms.InstallConfig.CmAccessAddressFormatShouldBe',
                    defaultMessage: 'CM 访问地址格式应为 http://ip或域名:端口',
                  }));
                }
                // 提取 IP 地址或域名进行验证
                const hostMatch = value.match(/^https?:\/\/([^:]+)/);
                if (hostMatch && hostMatch[1]) {
                  const host = hostMatch[1];
                  // 验证是否为有效的 IP 地址或域名
                  // 优先检查 IP 地址（支持 IPv4 和 IPv6）
                  const isValidIP = validator.isIP(host, '4') || validator.isIP(host, '6') || validator.isIP(host);
                  const isValidFQDN = validator.isFQDN(host, { require_tld: false });
                  // 也支持简单的域名格式（不强制要求 TLD），允许以数字开头和结尾（支持 IP 地址格式）
                  const isValidHostname = /^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$|^[\d\.]+$/.test(host);

                  if (!isValidIP && !isValidFQDN && !isValidHostname) {
                    return Promise.reject(intl.formatMessage({
                      id: 'OBD.pages.Oms.InstallConfig.PleaseEnterCorrectIpAddressOrDomain',
                      defaultMessage: '请输入正确的 IP 地址或域名',
                    }));
                  }
                }

                // 检查 CM 访问地址是否重复（排除当前行）
                // 只在格式完全正确时才检查重复，避免输入过程中的误报
                const trimmedUrl = value.trim();
                const currentRowId = record?.id;

                // 只有当 currentRowId 存在且值不为空时才进行重复检查
                if (currentRowId && trimmedUrl) {
                  // 先检查是否已经有重复错误信息（可能是 onValuesChange 设置的）
                  // 在验证开始时就检查，确保错误信息不会被清除
                  const currentErrors = tableFormRef?.current?.getFieldError([currentRowId, 'cm_url']);
                  const hasDuplicateError = currentErrors && currentErrors.length > 0 &&
                    (currentErrors.some((err: string) => err && err.includes('不能重复')) ||
                      currentErrors.some((err: string) => err && err.includes('CannotBeRepeated')));

                  // 检查重复：同时使用 dbConfigData 和表单值，确保获取到最准确的数据
                  let duplicateRow: any = null;
                  let allRowsForCheck: Array<{ id: string; cm_url?: string }> = [];

                  try {
                    // 从 tableFormRef 获取所有行的表单值
                    const formValues = tableFormRef?.current?.getFieldsValue() as any;

                    // 构建包含所有行最新值的数据列表
                    // 使用 dbConfigData 作为基础，因为它包含所有行的 id
                    allRowsForCheck = [];

                    // 遍历 dbConfigData 中的所有行
                    dbConfigData.forEach((item) => {
                      if (item.id === currentRowId) {
                        // 当前行，使用 validator 的 value 参数（最新输入值）
                        allRowsForCheck.push({
                          id: item.id,
                          cm_url: trimmedUrl
                        });
                      } else {
                        // 其他行，同时检查表单值和 dbConfigData，使用最新的值
                        let finalUrl: string | undefined = undefined;

                        // 优先从表单中获取值（表单中的值可能是最新的）
                        if (formValues && formValues[item.id]) {
                          const rowFormValue = formValues[item.id];
                          if (rowFormValue && typeof rowFormValue === 'object') {
                            const formUrl = rowFormValue.cm_url;
                            if (formUrl !== undefined && formUrl !== null && formUrl !== '') {
                              finalUrl = formUrl;
                            }
                          }
                        }

                        // 如果表单中没有值，使用 dbConfigData 中的值
                        if (finalUrl === undefined || finalUrl === '') {
                          finalUrl = item.cm_url;
                        }

                        allRowsForCheck.push({
                          id: item.id,
                          cm_url: finalUrl
                        });
                      }
                    });

                    // 检查是否有重复（排除当前行）
                    duplicateRow = allRowsForCheck.find((item) => {
                      // 排除当前行
                      if (item.id === currentRowId) {
                        return false;
                      }
                      // 检查是否有相同的 cm_url（去除空格后比较）
                      const itemUrl = item.cm_url?.trim();
                      // 只有当其他行的 cm_url 不为空且与当前值相同时，才认为是重复
                      return itemUrl && itemUrl.length > 0 && itemUrl === trimmedUrl;
                    });
                  } catch (e) {
                    // 如果获取表单值失败，直接使用 dbConfigData
                    // 同时构建 allRowsForCheck 用于后续错误设置
                    allRowsForCheck = dbConfigData.map((item) => ({
                      id: item.id,
                      cm_url: item.id === currentRowId ? trimmedUrl : item.cm_url
                    }));
                    duplicateRow = dbConfigData.find((item) => {
                      if (item.id === currentRowId) {
                        return false;
                      }
                      const itemUrl = item.cm_url?.trim();
                      return itemUrl && itemUrl.length > 0 && itemUrl === trimmedUrl;
                    });
                  }

                  const errorMessage = intl.formatMessage({
                    id: 'OBD.pages.Oms.InstallConfig.CmAccessAddressCannotBeRepeated',
                    defaultMessage: 'CM 访问地址不能重复',
                  });

                  // 如果找到重复项，报错
                  if (duplicateRow) {
                    // 设置错误信息：给所有包含重复地址的行设置错误
                    // 找出所有包含重复地址的行
                    const duplicateRowIds = new Set<string>();
                    duplicateRowIds.add(currentRowId);
                    duplicateRowIds.add(duplicateRow.id);

                    // 检查是否还有其他行也使用了相同的地址
                    allRowsForCheck.forEach((item: any) => {
                      if (item.id !== currentRowId && item.cm_url?.trim() === trimmedUrl) {
                        duplicateRowIds.add(item.id);
                      }
                    });

                    const fieldsToSet = Array.from(duplicateRowIds).map((rowId) => ({
                      name: [rowId, 'cm_url'],
                      errors: [errorMessage],
                    }));
                    tableFormRef?.current?.setFields(fieldsToSet);
                    return Promise.reject(errorMessage);
                  } else {
                    // 如果没有重复，清除所有行的重复错误信息
                    // 因为重复是相互的，如果当前行没有重复，其他行也不应该有重复错误
                    const allRowIds = dbConfigData.map((item) => item.id);
                    const fieldsToClear = allRowIds.map((rowId) => ({
                      name: [rowId, 'cm_url'],
                      errors: [],
                    }));
                    tableFormRef?.current?.setFields(fieldsToClear);
                    // 继续验证，不返回错误
                  }
                  // 如果没有找到重复，且之前也没有错误，正常返回
                }

                return Promise.resolve();
              },
              message: intl.formatMessage({
                id: 'OBD.pages.Oms.InstallConfig.PleaseEnterCorrectCmAccessAddress',
                defaultMessage: '请输入正确的 CM 访问地址',
              }),
            },
          ],
        };
      },
      renderFormItem: (_: any, config: any) => {
        const { isEditable, record } = config;
        if (!isEditable) return null;

        return (
          <Input
            placeholder={intl.formatMessage({
              id: 'OBD.pages.Oms.InstallConfig.PleaseEnterCmAccessAddress',
              defaultMessage: '格式：http://ip或域名:端口',
            })}
            onFocus={() => {
              // 当用户点击输入框时，先检查是否已有重复错误信息
              // 如果有，先保持错误信息，然后再触发验证
              if (record?.id) {
                const currentErrors = tableFormRef?.current?.getFieldError([record.id, 'cm_url']);
                const hasDuplicateError = currentErrors && currentErrors.length > 0 &&
                  (currentErrors.some((err: string) => err && err.includes('不能重复')) ||
                    currentErrors.some((err: string) => err && err.includes('CannotBeRepeated')));

                // 如果有重复错误，先保持错误信息
                if (hasDuplicateError) {
                  const errorMessage = intl.formatMessage({
                    id: 'OBD.pages.Oms.InstallConfig.CmAccessAddressCannotBeRepeated',
                    defaultMessage: 'CM 访问地址不能重复',
                  });
                  tableFormRef?.current?.setFields([
                    {
                      name: [record.id, 'cm_url'],
                      errors: [errorMessage],
                    },
                  ]);
                }

                // 延迟触发验证，确保错误信息已经设置
                setTimeout(() => {
                  tableFormRef?.current?.validateFields([record.id, 'cm_url']).catch(() => {
                    // 验证失败时已经显示错误，这里不需要处理
                  });
                }, 0);
              }
            }}
          />
        );
      },
    },
    {
      title: '',
      valueType: 'option',
      width: 20,
    },
  ];

  const handleDelete = (id: string) => {
    // 获取要删除的zone中的服务器
    const deletedZone = dbConfigData.find(item => item.id === id);
    const deletedServers = deletedZone?.cm_nodes || [];
    const wasDeletedZoneFavor = deletedZone?.cm_is_default || false;

    // 删除数据库节点配置
    const newDBConfigData = dbConfigData.filter((item) => item.id !== id);

    // 如果删除的是被勾选优先访问的行，需要重新设置其他行的优先访问状态
    if (wasDeletedZoneFavor && newDBConfigData.length > 0) {
      // 将第一个剩余行设置为优先访问
      newDBConfigData[0].cm_is_default = true;
      // 确保其他行都不勾选
      newDBConfigData.forEach((item, index) => {
        item.cm_is_default = index === 0;
      });
      // 更新 selectedFavorId
      setSelectedFavorId(newDBConfigData[0].id);
    } else if (wasDeletedZoneFavor) {
      // 如果删除的是选中项且没有剩余项，清空选中状态
      setSelectedFavorId(undefined);
    }

    setDBConfigData(newDBConfigData);

    // 立即计算新的allOBServer
    const newAllServers = getAllServers(newDBConfigData as any, 'cm_nodes');


    // 立即更新allOBServer状态，避免异步更新导致的问题
    setAllOBServer(newAllServers);

    // 更新allZoneOBServer
    const newAllZoneServers: any = {};
    newDBConfigData.forEach((item) => {
      newAllZoneServers[`${item.id}`] = item.cm_nodes || [];
    });
    setAllZoneOBServer(newAllZoneServers);
  };

  const oceanBaseInfo = {
    group: intl.formatMessage({
      id: 'OBD.pages.Oms.InstallConfig.Product',
      defaultMessage: '产品',
    }),
    key: 'database',
    content: [
      {
        key: 'oms',
        name: 'OMS',
        onlyAll: false,
        desc: intl.formatMessage({
          id: 'OBD.pages.Oms.InstallConfig.OmsDescription',
          defaultMessage: '是 OceanBase 数据库一站式数据传输和同步的产品。是集数据迁移、实时数据同步和增量数据订阅于一体的数据传输服务。',
        }),
        doc: OMS_DOCS,
        version_info: omsDockerData
      },
    ],
  };


  const getColumns = () => {
    const columns: ColumnsType<TableDataType> = [
      {
        title: intl.formatMessage({
          id: 'OBD.pages.Oms.InstallFinished.Product',
          defaultMessage: '产品',
        }),
        dataIndex: 'name',
        width: locale === 'zh-CN' ? 134 : 140,
        render: (name, record) => {
          return (
            <>
              {name}
            </>
          );
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.component.DeployConfig.Version',
          defaultMessage: '版本',
        }),
        dataIndex: 'version_info',
        width: 220,
        render: (text) => {
          // 确保 text 是数组
          const versionList = Array.isArray(text) ? text : [];

          // 获取当前选中的值，格式为 name:version
          const getCurrentValue = () => {
            if (configData?.image) {
              // 如果 configData.image 是 name:version 格式，直接使用
              if (configData.image.includes(':')) {
                return configData.image;
              }
              // 如果是 name，找到对应的项
              const selectedItem = versionList.find((item: any) => item.name === configData.image);
              if (selectedItem) {
                return `${selectedItem.name}:${selectedItem.version}`;
              }
            }
            // 默认使用第一个项
            if (versionList[0]) {
              return `${versionList[0].name}:${versionList[0].version}`;
            }
            return undefined;
          };

          // 获取当前选中的项，用于显示版本号
          const getSelectedItem = () => {
            const currentValue = getCurrentValue();
            if (!currentValue) return null;
            const [name, version] = currentValue.split(':');
            return versionList.find((item: any) => item.name === name && item.version === version) || versionList[0];
          };

          const selectedItem = getSelectedItem();
          const displayVersion = selectedItem?.version?.split('feature_')[1]?.toUpperCase() || selectedItem?.version || '';
          const isCommunityEdition = selectedItem?.version?.includes('ce') || false;

          return (
            <Tooltip title={checkStatus !== 'success' ? intl.formatMessage({
              id: 'OBD.pages.Oms.InstallConfig.ConfigureAndValidateBeforeSelecting',
              defaultMessage: '配置完上面的信息并校验通过才可选择',
            }) : versionList[0]?.version}>
              <Select
                labelInValue
                onChange={(option) => {
                  // option 是 { label, value } 格式，value 是 name:version
                  setConfigData({ ...configData, image: option.value })
                }}
                style={{ width: 207 }}
                popupClassName={styles?.popupClassName}
                // 部署用户未校验，无法触发镜像选择
                disabled={checkStatus !== 'success'}
                value={getCurrentValue() ? {
                  label: selectedItem ? (
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <span>V {displayVersion}</span>
                      {isCommunityEdition ? (
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
                  ) : '',
                  value: getCurrentValue(),
                } : undefined}
              >
                {Array.isArray(text) && text.length > 0 ? text.map((item: any) => {
                  const versionText = item.version.split('feature_')[1]?.toUpperCase() || item.version;

                  return (
                    <Select.Option value={`${item.name}:${item.version}`} key={item.name}>
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
        render: (_, record) => {
          return (
            <>
              {record?.desc || '-'}
              <a
                href={record?.doc}
                target="_blank"
              >
                {intl.formatMessage({
                  id: 'OBD.component.DeployConfig.LearnMore',
                  defaultMessage: '了解更多',
                })}
              </a>
            </>
          )
        }

      },
    ];

    return columns;
  };

  const handleCheckSystemUser = async () => {
    const { data: publicKey } = await getPublicKey();

    // 获取所有节点并扁平化
    const allNodes = flattenDeep(dbConfigData?.map((item) => item.cm_nodes || []) || []);
    let site = allNodes.filter(node => node && node.trim()).join(',');

    // 验证节点不为空
    if (!site || site.trim() === '') {
      message.error(intl.formatMessage({
        id: 'OBD.pages.Oms.InstallConfig.PleaseConfigureNodeInformationFirst',
        defaultMessage: '请先配置节点信息',
      }));
      return;
    }

    // 获取表单所有值
    const formValues = form.getFieldsValue();

    const username = form.getFieldValue(['auth', 'username']) || formValues?.auth?.username;
    const password = form.getFieldValue(['auth', 'password']) || formValues?.auth?.password;

    // 验证用户名不为空
    if (!username || username.trim() === '') {
      message.error(intl.formatMessage({
        id: 'OBD.pages.Oms.InstallConfig.PleaseEnterUsername',
        defaultMessage: '请输入用户名',
      }));
      return;
    }

    // 获取 ssh_port（表单中的端口字段）
    const sshPort = form.getFieldValue(['auth', 'ssh_port']) || formValues?.auth?.ssh_port || 22;

    const body = {
      oms_servers: site,
      username: username.trim(),
      password: password ? encrypt(password, publicKey) : encrypt('', publicKey),
      port: sshPort || 22
    }

    // 验证所有必需字段
    if (!body.oms_servers || !body.username || body.port === undefined || body.port === null) {

      message.error(intl.formatMessage({
        id: 'OBD.pages.Oms.InstallConfig.PleaseFillInCompleteValidationInformation',
        defaultMessage: '请填写完整的校验信息（节点、用户名、端口）',
      }));
      return;
    }
    omsDocker(body);

  };

  return (
    <Space className={styles.spaceWidth} direction="vertical" size="middle">
      <ProCard className={styles.pageCard} split="horizontal">
        <ProForm
          layout="vertical"
          form={form}
          submitter={false}
          initialValues={{
            mode: configData?.mode || 'standard',
            appname: configData?.appname || 'myoms',
            nginx_server_port: configData?.nginx_server_port || '8089',
            cm_server_port: configData?.cm_server_port || '8088',
            supervisor_server_port: configData?.supervisor_server_port || '9000',
            ghana_server_port: configData?.ghana_server_port || '8090',
            sshd_server_port: configData?.sshd_server_port || '2023',
            mount_path: configData?.mount_path,
            auth: {
              username: configData?.auth?.username,
              password: configData?.auth?.password,
              ssh_port: configData?.auth?.ssh_port || '22',
            },
          }}
        >

          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.BasicConfiguration',
              defaultMessage: '基本配置',
            })}
            className="card-padding-bottom-24"
            bodyStyle={{ paddingBottom: 0 }}
          >

            <ProFormText
              name={'appname'}
              label={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.DeploymentName',
                defaultMessage: '部署名称',
              })}
              fieldProps={{ style: commonSelectStyle }}
              placeholder={intl.formatMessage({
                id: 'OBD.pages.Oms.InstallConfig.PleaseEnterDeploymentName',
                defaultMessage: '请输入部署名称',
              })}
              validateTrigger={['onBlur', 'onChange']}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.pages.Oms.InstallConfig.PleaseEnterDeploymentName',
                    defaultMessage: '请输入部署名称',
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

          </ProCard>
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.DeploymentMode',
              defaultMessage: '部署模式',
            })}
            className="card-header-padding-top-0 card-padding-top-0 card-padding-bottom-0"
          >
            <ProFormRadio.Group
              name={'mode'}
              fieldProps={{
                optionType: 'default',
                style: { marginTop: 16 },
                value: configData?.mode || 'standard',
                onChange: (e) => {
                  const newMode = e.target.value;
                  setConfigData({ ...configData, mode: newMode });
                  // 同时更新表单值，确保 standAlone 能正确计算
                  form.setFieldsValue({ mode: newMode });

                  // 切换模式时，强制根据新模式重新初始化数据库节点配置
                  setTimeout(() => {
                    initDBConfigDataByMode(newMode, true);
                  }, 0);
                },
              }}
              options={[
                {
                  label: intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.SingleNode',
                    defaultMessage: '单节点',
                  }), value: 'standard'
                },
                {
                  label: intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.SingleRegionMultiNode',
                    defaultMessage: '单地域多节点',
                  }), value: 'compact'
                },
                {
                  label: intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.MultiRegionMultiNode',
                    defaultMessage: '多地域多节点',
                  }), value: 'multi'
                },
              ]}
            />

          </ProCard>
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.NodeConfiguration',
              defaultMessage: '节点配置',
            })}
            className="card-header-padding-top-0 card-padding-top-0 "
          >
            <EditableProTable<OMSDBConfig>
              className={styles.nodeEditabletable}
              columns={columns as any}
              rowKey="id"
              value={dbConfigData}
              editableFormRef={tableFormRef}
              onChange={(value) => setDBConfigData(value as OMSDBConfig[])}
              recordCreatorProps={
                // 单机版，关闭默认的新建按钮
                !standAlone
                  ? {
                    newRecordType: 'dataSource',
                    record: () => {
                      // 从现有的 dbConfigData 中找到最大的 cm_location
                      let maxLocation = 0;
                      if (dbConfigData.length > 0) {
                        const locations = dbConfigData.map((item) => {
                          const location = item.cm_location;
                          // cm_location 可能是字符串或数字，转换为数字
                          return typeof location === 'string'
                            ? parseInt(location, 10) || 0
                            : (typeof location === 'number' ? location : 0);
                        });
                        maxLocation = Math.max(...locations);
                      }
                      // 计算下一个索引
                      const nextIndex = maxLocation + 1;
                      // 更新全局 nameIndex 以便下次使用
                      setNameIndex(nextIndex);
                      return {
                        id: Date.now().toString(),
                        cm_region: `default-${nextIndex}`,
                        cm_is_default: false,
                        cm_location: nextIndex.toString(),
                        cm_nodes: [],
                      };
                    },
                    creatorButtonText: intl.formatMessage({
                      id: 'OBD.pages.Oms.InstallConfig.Add',
                      defaultMessage: '添加',
                    }),
                  }
                  : false
              }
              editable={{
                type: 'multiple',
                form: editableForm,
                editableKeys,
                actionRender: (row) => {
                  // 只有当行数大于2时才显示删除图标
                  if (dbConfigData?.length <= 2) {
                    return [];
                  }

                  if (!row?.cm_nodes?.length && !row?.cm_url) {
                    return [
                      <DeleteOutlined
                        key="delete"
                        onClick={() => handleDelete(row.id)}
                        style={{ color: '#8592ad' }}
                      />
                    ];
                  }
                  return [
                    <Popconfirm
                      key="confirm"
                      title={intl.formatMessage({
                        id: 'OBD.pages.Oms.InstallConfig.ConfirmDeleteNodeConfiguration',
                        defaultMessage: '确定删除该条节点的相关配置吗？',
                      })}
                      onConfirm={() => handleDelete(row.id)}
                    >
                      <DeleteOutlined style={{ color: '#8592ad' }} />
                    </Popconfirm>
                  ];
                },
                onValuesChange: (editableItem, recordList) => {
                  if (!editableItem?.id) {
                    return;
                  }
                  const editorServers =
                    editableItem?.cm_nodes?.map((item) => item.trim()) || [];
                  const cm_url = editableItem?.cm_url;
                  const cm_region = editableItem?.cm_region;
                  let newRootService = cm_url;


                  // 检查 cm_region 是否重复（独立校验，不影响其他字段）
                  if (cm_region && cm_region.trim()) {
                    const trimmedRegion = cm_region.trim();
                    const duplicateRow = recordList.find(
                      (item: any) => item.id !== editableItem.id && item.cm_region?.trim() === trimmedRegion
                    );
                    if (duplicateRow) {
                      // 只设置 cm_region 的错误信息，不影响其他字段
                      tableFormRef?.current?.setFields([
                        {
                          name: [editableItem.id, 'cm_region'],
                          errors: [
                            intl.formatMessage({
                              id: 'OBD.pages.Oms.InstallConfig.EnglishRegionIdentifierCannotBeRepeated',
                              defaultMessage: '英文地域标识不能重复',
                            })
                          ],
                        },
                      ]);
                    } else {
                      // 清除 cm_region 的错误信息（不影响其他字段）
                      const regionErrors = editableForm.getFieldError([
                        editableItem?.id,
                        'cm_region',
                      ]);
                      if (regionErrors.length > 0) {
                        tableFormRef?.current?.setFields([
                          {
                            name: [editableItem.id, 'cm_region'],
                            errors: [],
                          },
                        ]);
                      }
                    }
                  }

                  // 检查 cm_url 是否重复（独立校验，不受 cm_region 错误影响）
                  // 只在值符合基本格式时才检查，避免输入过程中频繁报错
                  if (cm_url && cm_url.trim()) {
                    const trimmedUrl = cm_url.trim();
                    // 先检查是否符合基本 URL 格式，只有格式正确时才检查重复
                    const urlPattern = /^https?:\/\/[\w\.-]+:\d+$/;
                    if (urlPattern.test(trimmedUrl)) {
                      // 检查重复：使用 recordList 和表单值，确保获取所有行的最新值
                      let duplicateUrlRow: any = null;
                      let allRowsForCheck: Array<{ id: string; cm_url?: string }> = [];
                      try {
                        // 首先尝试从表单获取所有行的最新值
                        const formValues = tableFormRef?.current?.getFieldsValue() as any;

                        // 构建包含所有行最新值的数据列表
                        // recordList 包含所有行的最新值（除了当前正在编辑的行）
                        // 对于当前行，使用 editableItem.cm_url（最新值）
                        // 对于其他行，优先使用 formValues，其次使用 recordList，最后使用 dbConfigData
                        allRowsForCheck = [];

                        // 遍历所有行（使用 recordList 作为基础，因为它包含最新值）
                        recordList.forEach((recordItem: any) => {
                          if (recordItem.id === editableItem.id) {
                            // 当前行，使用 editableItem 中的最新值
                            allRowsForCheck.push({
                              id: recordItem.id,
                              cm_url: trimmedUrl
                            });
                          } else {
                            // 其他行，优先使用表单中的最新值
                            let finalUrl = recordItem.cm_url;
                            if (formValues && formValues[recordItem.id]) {
                              const rowFormValue = formValues[recordItem.id];
                              const formUrl = rowFormValue?.cm_url;
                              if (formUrl !== undefined && formUrl !== null && formUrl !== '') {
                                finalUrl = formUrl;
                              }
                            }
                            allRowsForCheck.push({
                              id: recordItem.id,
                              cm_url: finalUrl
                            });
                          }
                        });

                        // 检查 dbConfigData 中是否有不在 recordList 中的行
                        dbConfigData.forEach((item: any) => {
                          const inRecordList = recordList.some((r: any) => r.id === item.id);
                          if (!inRecordList) {
                            // 如果不在 recordList 中，使用表单值或 dbConfigData 中的值
                            let finalUrl = item.cm_url;
                            if (formValues && formValues[item.id]) {
                              const rowFormValue = formValues[item.id];
                              const formUrl = rowFormValue?.cm_url;
                              if (formUrl !== undefined && formUrl !== null && formUrl !== '') {
                                finalUrl = formUrl;
                              }
                            }
                            allRowsForCheck.push({
                              id: item.id,
                              cm_url: finalUrl
                            });
                          }
                        });

                        // 检查是否有重复（排除当前行）
                        duplicateUrlRow = allRowsForCheck.find((item: any) => {
                          // 排除当前行
                          if (item.id === editableItem.id) {
                            return false;
                          }
                          // 检查是否有相同的 cm_url（去除空格后比较）
                          const itemUrl = item.cm_url?.trim();
                          return itemUrl && itemUrl.length > 0 && itemUrl === trimmedUrl;
                        });
                      } catch (e) {
                        // 如果获取表单值失败，使用 recordList
                        // 同时构建 allRowsForCheck 用于后续错误设置
                        allRowsForCheck = recordList.map((item: any) => ({
                          id: item.id,
                          cm_url: item.id === editableItem.id ? trimmedUrl : item.cm_url
                        }));
                        duplicateUrlRow = recordList.find((item: any) => {
                          if (item.id === editableItem.id) {
                            return false;
                          }
                          const itemUrl = item.cm_url?.trim();
                          return itemUrl && itemUrl === trimmedUrl;
                        });
                      }

                      if (duplicateUrlRow) {
                        // 设置错误信息：给所有包含重复地址的行设置错误
                        // 找出所有包含重复地址的行
                        const duplicateRowIds = new Set<string>();
                        duplicateRowIds.add(editableItem.id);
                        duplicateRowIds.add(duplicateUrlRow.id);

                        // 检查是否还有其他行也使用了相同的地址
                        allRowsForCheck.forEach((item: any) => {
                          if (item.id !== editableItem.id && item.cm_url?.trim() === trimmedUrl) {
                            duplicateRowIds.add(item.id);
                          }
                        });

                        const errorMessage = intl.formatMessage({
                          id: 'OBD.pages.Oms.InstallConfig.CmAccessAddressCannotBeRepeated',
                          defaultMessage: 'CM 访问地址不能重复',
                        });

                        const fieldsToSet = Array.from(duplicateRowIds).map((rowId) => ({
                          name: [rowId, 'cm_url'],
                          errors: [errorMessage],
                        }));
                        tableFormRef?.current?.setFields(fieldsToSet);
                      } else {
                        // 如果没有重复，清除所有行的重复错误信息
                        // 因为重复是相互的，如果当前行没有重复，其他行也不应该有重复错误
                        const allRowIds = dbConfigData.map((item) => item.id);
                        const fieldsToClear = allRowIds.map((rowId) => ({
                          name: [rowId, 'cm_url'],
                          errors: [],
                        }));
                        tableFormRef?.current?.setFields(fieldsToClear);
                      }
                    }
                  }

                  // 检查节点 IP 合法性和重复（与 validator 规则保持一致）
                  if (editorServers && editorServers.length > 0) {
                    // 检查是否有无效的 IP 地址（直接检查，不先过滤）
                    if (editorServers.some((item) => !validator.isIP(item))) {
                      // 设置 IP 格式错误
                      tableFormRef?.current?.setFields([
                        {
                          name: [editableItem.id, 'cm_nodes'],
                          errors: [
                            intl.formatMessage({
                              id: 'OBD.pages.Oms.InstallConfig.PleaseEnterCorrectIpNode',
                              defaultMessage: '请输入正确的 IP 节点',
                            })
                          ],
                        },
                      ]);
                      // 如果有无效 IP，不继续检查重复，直接返回
                      return;
                    }

                    // 1. 检查当前行内是否有重复
                    const trimmedServers = editorServers.map((s: string) => s.trim()).filter((s: string) => s);
                    if (hasDuplicateIPs(trimmedServers)) {
                      // 设置错误信息（只给当前行设置，因为行内重复只影响当前行）
                      tableFormRef?.current?.setFields([
                        {
                          name: [editableItem.id, 'cm_nodes'],
                          errors: [
                            intl.formatMessage({
                              id: 'OBD.component.NodeConfig.TheValidatorNode2',
                              defaultMessage: '禁止输入重复节点',
                            })
                          ],
                        },
                      ]);
                    } else {
                      // 如果当前行内没有重复，先清除当前行的行内重复错误（如果有的话）
                      const currentErrors = tableFormRef?.current?.getFieldError([editableItem.id, 'cm_nodes']);
                      const hasRowInternalDuplicateError = currentErrors && currentErrors.length > 0 &&
                        currentErrors.some((err: string) => err && err.includes('重复'));
                      if (hasRowInternalDuplicateError) {
                        // 先清除当前行的错误，后续检查跨行重复时可能会重新设置
                        tableFormRef?.current?.setFields([
                          {
                            name: [editableItem.id, 'cm_nodes'],
                            errors: [],
                          },
                        ]);
                      }
                      // 2. 检查与其他行是否有重复
                      // 收集所有行的节点数据（使用最新的表单值）
                      const allRowsData: Array<{ id: string; nodes: string[] }> = [];

                      // 尝试从表单获取所有行的最新值
                      try {
                        const formValues = tableFormRef?.current?.getFieldsValue() as any;
                        if (formValues) {
                          // 使用表单值获取所有行的节点
                          dbConfigData.forEach((item) => {
                            const rowFormValue = formValues[item.id];
                            const formNodes = rowFormValue?.cm_nodes;
                            // 对于当前行，使用 editorServers（最新值）
                            // 对于其他行，优先使用表单中的最新值
                            const nodes = item.id === editableItem.id
                              ? trimmedServers
                              : (formNodes !== undefined && formNodes !== null
                                ? (Array.isArray(formNodes) ? formNodes : [])
                                : (item.cm_nodes || []));
                            allRowsData.push({
                              id: item.id,
                              nodes: nodes
                                .filter((node: string) => node && typeof node === 'string' && node.trim() !== '')
                                .map((node: string) => node.trim())
                            });
                          });
                        } else {
                          // 如果无法获取表单值，使用 recordList
                          recordList.forEach((item: any) => {
                            const nodes = item.id === editableItem.id
                              ? trimmedServers
                              : (item.cm_nodes || []);
                            allRowsData.push({
                              id: item.id,
                              nodes: nodes
                                .filter((node: string) => node && typeof node === 'string' && node.trim() !== '')
                                .map((node: string) => node.trim())
                            });
                          });
                        }
                      } catch (e) {
                        // 如果获取表单值失败，使用 recordList
                        recordList.forEach((item: any) => {
                          const nodes = item.id === editableItem.id
                            ? trimmedServers
                            : (item.cm_nodes || []);
                          allRowsData.push({
                            id: item.id,
                            nodes: nodes
                              .filter((node: string) => node && typeof node === 'string' && node.trim() !== '')
                              .map((node: string) => node.trim())
                          });
                        });
                      }

                      // 找出所有包含重复节点的行
                      const duplicateRowIds = new Set<string>();
                      const errorMessage = intl.formatMessage({
                        id: 'OBD.component.NodeConfig.TheValidatorNode2',
                        defaultMessage: '禁止输入重复节点',
                      });

                      // 检查每一行的节点是否与其他行重复
                      allRowsData.forEach((rowData) => {
                        const { id: rowId, nodes: rowNodes } = rowData;
                        // 检查当前行的每个节点是否在其他行中也存在
                        const hasDuplicate = rowNodes.some((node: string) => {
                          return allRowsData.some((otherRowData) => {
                            if (otherRowData.id === rowId) {
                              return false; // 跳过自己
                            }
                            return otherRowData.nodes.includes(node);
                          });
                        });

                        if (hasDuplicate) {
                          duplicateRowIds.add(rowId);
                        }
                      });

                      // 给所有包含重复节点的行设置错误信息
                      if (duplicateRowIds.size > 0) {
                        const fieldsToSet = Array.from(duplicateRowIds).map((rowId) => ({
                          name: [rowId, 'cm_nodes'],
                          errors: [errorMessage],
                        }));
                        tableFormRef?.current?.setFields(fieldsToSet);
                      } else {
                        // 如果没有重复，清除所有行的重复错误信息
                        // 收集所有行的 id，清除它们的重复错误
                        const allRowIds = dbConfigData.map((item) => item.id);
                        const fieldsToClear = allRowIds.map((rowId) => ({
                          name: [rowId, 'cm_nodes'],
                          errors: [],
                        }));
                        tableFormRef?.current?.setFields(fieldsToClear);
                      }
                    }
                  }

                  // 使用 allZoneOBServer 判断节点是否变化
                  const beforeChangeServers = allZoneOBServer[`${editableItem?.id}`] || [];
                  const beforeChangeServersStr = JSON.stringify(beforeChangeServers.map((item: string) => item.trim()).sort());
                  const currentNodesStr = JSON.stringify(editorServers.sort());
                  const isNodesChanged = beforeChangeServersStr !== currentNodesStr;

                  if (editorServers.length) {
                    // 保持用户输入的 cm_url，不自动填充
                    newRootService = cm_url;

                    // 只在节点配置变化时，才检查并显示 127.0.0.1 的警告
                    if (isNodesChanged && editorServers.find((item) => item === '127.0.0.1')) {
                      message.warning(
                        intl.formatMessage({
                          id: 'OBD.component.MetaDBConfig.NodeConfig.B663132E',
                          defaultMessage:
                            '依据 OceanBase 最佳实践，建议使用非 127.0.0.1 IP 地址',
                        }),
                      );
                    }
                  }
                  editableForm.setFieldsValue({
                    [editableItem?.id]: {
                      cm_url: newRootService,
                    },
                  });
                  if (!newRootService) {
                    tableFormRef?.current?.setFields([
                      {
                        name: [editableItem.id, 'cm_url'],
                        touched: false,
                      },
                    ]);
                  }
                  const beforeChangeServersLength =
                    allZoneOBServer[`${editableItem?.id}`]?.length || 0;
                  if (
                    editorServers &&
                    editorServers.length &&
                    editorServers.length > beforeChangeServersLength
                  ) {
                    const errors = editableForm.getFieldError([
                      editableItem?.id,
                      'cm_nodes',
                    ]);
                    if (errors?.length) {
                      let errordom = document.getElementById(
                        `cm_nodes-${editableItem.id}`,
                      );
                      errordom?.focus();
                      tableFormRef?.current?.setFields([
                        {
                          name: [editableItem.id, 'cm_nodes'],
                          errors: errors,
                        },
                      ]);
                    } else {
                      editableForm.setFieldsValue({
                        [editableItem?.id]: {
                          cm_nodes: editorServers,
                        },
                      });
                    }
                  }
                  const newRecordList = recordList.map((item) => {
                    if (item.id === editableItem.id) {
                      return {
                        ...editableItem,
                        cm_url: newRootService,
                        cm_nodes: editorServers,
                        // 保持 cm_is_default 字段的同步，确保与 selectedFavorId 一致
                        cm_is_default: selectedFavorId !== undefined
                          ? item.id === selectedFavorId
                          : (item.cm_is_default !== undefined ? item.cm_is_default : false),
                      };
                    }
                    // 对于其他项，也确保 cm_is_default 与 selectedFavorId 一致
                    return {
                      ...item,
                      cm_is_default: selectedFavorId !== undefined
                        ? item.id === selectedFavorId
                        : item.cm_is_default,
                    };
                  });
                  setDBConfigData(newRecordList);

                  // 更新 allZoneOBServer
                  const newAllZoneServers = { ...allZoneOBServer };
                  newAllZoneServers[`${editableItem.id}`] = editorServers;
                  setAllZoneOBServer(newAllZoneServers);

                  // 更新 allOBServer
                  const newAllServers = getAllServers(newRecordList as any, 'cm_nodes');
                  setAllOBServer(newAllServers);
                },
                onChange: setEditableRowKeys,
              }}
            />
          </ProCard>
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.PortConfiguration',
              defaultMessage: '端口配置',
            })}
            className="card-header-padding-top-0 card-padding-bottom-0"
          >
            <Space size="large">
              <InputPort
                name={'nginx_server_port'}
                label={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.HttpServicePort',
                  defaultMessage: 'HTTP 服务端口',
                })}
                fieldProps={{ style: { width: 140 }, required: false }}
              />
              <InputPort
                name={'cm_server_port'}
                label={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.CmsServicePort',
                  defaultMessage: 'CM 服务端口',
                })}
                fieldProps={{ style: { width: 140 }, required: false }}
              />
              <InputPort
                name={'supervisor_server_port'}
                label={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.SupervisorServicePort',
                  defaultMessage: 'Supervisor 服务端口',
                })}
                fieldProps={{ style: { width: 140 }, required: false }}
              />
              <InputPort
                name={'ghana_server_port'}
                label={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.GhanaServicePort',
                  defaultMessage: 'Ghana 服务端口',
                })}
                fieldProps={{ style: { width: 140 }, required: false }}
              />
              <InputPort
                name={'sshd_server_port'}
                label={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.SshdServicePort',
                  defaultMessage: 'SSHD 服务端口',
                })}
                fieldProps={{ style: { width: 140 }, required: false }}
              />
            </Space>

          </ProCard>
          <ProCard
            className={styles.pageCard}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.DataDirectory',
              defaultMessage: '数据目录',
            })}
            bodyStyle={{ paddingBottom: '0' }}
          >
            <ProFormText
              name={'mount_path'}
              label={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.Path',
                defaultMessage: '路径',
              })}
              fieldProps={{ style: { width: 304 } }}
              placeholder={'/data/oms'}
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
          </ProCard>
          <ProCard
            className={styles.pageCard}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.DeploymentUserConfiguration',
              defaultMessage: '部署用户配置',
            })}
            bodyStyle={{ paddingBottom: '0' }}
          >
            <Space size="large">
              <ProFormText
                name={['auth', 'username']}
                label={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.Username',
                  defaultMessage: '用户名',
                })}
                fieldProps={{
                  style: { width: 304 },
                }}
                placeholder={intl.formatMessage({
                  id: 'OBD.src.component.MySelect.PleaseSelect',
                  defaultMessage: '请选择',
                })}
                required={false}
                extra={
                  <>
                    {intl.formatMessage({
                      id: 'OBD.pages.Oms.InstallConfig.PleaseProvideHostUsernameForAutomatedConfiguration',
                      defaultMessage: '请提供主机用户名用以自动化配置平台专用操作',
                    })}
                    <div>
                      {intl.formatMessage({
                        id: 'OBD.pages.Oms.InstallConfig.SystemUser',
                        defaultMessage: '系统用户',
                      })}
                      <a href={DOCS_USER} target="_blank" style={{ marginLeft: '4px', display: 'inline' }}>
                        {intl.formatMessage({
                          id: 'OBD.component.MetaDBConfig.UserConfig.ViewHelpDocuments',
                          defaultMessage: '查看帮助文档',
                        })}
                      </a>
                    </div>

                  </>
                }
                rules={[
                  {
                    required: true,
                    message: intl.formatMessage({
                      id: 'OBD.pages.Oms.InstallConfig.PleaseEnterUsername',
                      defaultMessage: '请输入用户名',
                    }),
                  },
                ]}
              />
              <ProFormText
                name={['auth', 'password']}
                style={{ width: 304 }}

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
                name={['auth', 'ssh_port']}
                label={
                  <span className={styles.labelText}>
                    {intl.formatMessage({
                      id: 'OBD.component.MetaDBConfig.UserConfig.SshPort',
                      defaultMessage: 'SSH端口',
                    })}
                  </span>
                }
                fieldProps={{
                  style: { width: 120 },
                }}
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
          </ProCard>
          <ProCard
            className="card-header-padding-top-0 card-padding-bottom-24  card-padding-top-0"
            style={{ display: 'flex' }}
          >
            <Button
              onClick={() => handleCheckSystemUser()}
              loading={omsDockerLoading}
            >
              {intl.formatMessage({
                id: 'OBD.pages.Oms.InstallConfig.Validation',
                defaultMessage: '校验',
              })}
            </Button>
            {checkStatus === 'success' && !omsDockerLoading && (
              <span style={{ color: 'rgba(77,204,162,1)', marginLeft: 12 }}>
                <CheckCircleFilled />
                <span style={{ marginLeft: 5 }}>
                  {intl.formatMessage({
                    id: 'OBD.pages.Oms.InstallConfig.CurrentValidationSuccessful',
                    defaultMessage: '当前校验成功',
                  })}
                </span>
              </span>
            )}
            {checkStatus === 'fail' && !omsDockerLoading && (
              <span style={{ color: 'rgba(255,75,75,1)', marginLeft: 12 }}>
                <CloseCircleFilled />
                <span style={{ marginLeft: 5 }}>
                  {checkOmsErrorInfo || intl.formatMessage({
                    id: 'OBD.component.OCPConfigNew.ServiceConfig.TheCurrentVerificationFailedPlease',
                    defaultMessage: '当前校验失败，请重新输入',
                  })}
                </span>
              </span>
            )}
          </ProCard>
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.InstallConfig.VersionSelection',
              defaultMessage: '版本选择',
            })}
            className="card-header-padding-top-0 card-padding-bottom-24  card-padding-top-0"
          >
            <Space
              className={styles.spaceWidth}
              direction="vertical"
              size="middle"
            >
              <ProCard
                type="inner"
                className={`${styles.componentCard}`}
                key={oceanBaseInfo.group}
              >
                <Table
                  className={styles.componentTable}
                  columns={getColumns()}
                  rowKey="key"
                  dataSource={oceanBaseInfo.content}
                  pagination={false}
                  rowClassName={() => ''}
                />
              </ProCard>
            </Space>
          </ProCard>
        </ProForm>
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
              disabled={checkStatus !== 'success'}
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
    </Space >
  );
}
