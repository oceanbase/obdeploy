import { getObdInfo } from '@/services/ob-deploy-web/Info';
import {
  dnsValidator,
  getErrorInfo,
  handleQuit,
  hasDuplicateIPs,
  serverReg,
  serversValidator,
} from '@/utils';
import { getAllServers } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import {
  CaretDownOutlined,
  CaretRightOutlined,
  DeleteOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import type {
  EditableFormInstance,
  ProColumns,
} from '@ant-design/pro-components';
import {
  EditableProTable,
  ProCard,
  ProForm,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import {
  Button,
  Col,
  Form,
  message,
  Popconfirm,
  Row,
  Select,
  Space,
  Tooltip,
} from 'antd';
import { useEffect, useRef, useState } from 'react';
import { getLocale, useModel } from 'umi';
import validator from 'validator';
import {
  commonServerStyle,
  commonStyle,
  configServerComponent,
  grafanaComponent,
  obagentComponent,
  obproxyComponent,
  pathRule,
  prometheusComponent,
} from '../constants';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';
import ServerTags from './ServerTags';
import TooltipInput from './TooltipInput';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface FormValues extends API.Components {
  auth?: {
    user?: string;
    password?: string;
    port?: number;
  };
  home_path?: string;
}

export default function NodeConfig() {
  const {
    selectedConfig,
    setCurrentStep,
    configData,
    setConfigData,
    lowVersion,
    handleQuitProgress,
    nameIndex,
    setNameIndex,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const { components = {}, auth, home_path } = configData || {};
  const {
    oceanbase = {},
    ocpexpress = {},
    obproxy = {},
    prometheus = {},
    grafana = {},
    obconfigserver = {},
  } = components;
  const [form] = ProForm.useForm();
  const [editableForm] = ProForm.useForm();
  const finalValidate = useRef<boolean>(false);
  const tableFormRef = useRef<EditableFormInstance<API.DBConfig>>();
  const [show, setShow] = useState<boolean>(false);

  // 当前 OB 环境是否为单机版
  const standAlone = oceanbase?.component === 'oceanbase-standalone';

  const initDBConfigData = oceanbase?.topology?.length
    ? oceanbase?.topology?.map((item: API.Zone, index: number) => ({
        id: (Date.now() + index).toString(),
        ...item,
        servers: item?.servers?.map((server) => server?.ip),
      }))
    : [];

  const homePathSuffix = `/${oceanbase.appname}`;

  const initHomePath = home_path
    ? home_path.substring(0, home_path.length - homePathSuffix.length)
    : undefined;

  const [dbConfigData, setDBConfigData] =
    useState<API.DBConfig[]>(initDBConfigData);
  const [editableKeys, setEditableRowKeys] = useState<React.Key[]>(() =>
    dbConfigData.map((item) => item.id),
  );

  useEffect(() => {
    const init = oceanbase?.topology?.map((item: API.Zone, index: number) => ({
      id: (Date.now() + index).toString(),
      ...item,
      servers: item?.servers?.map((server) => server?.ip),
    }));

    if (
      oceanbase?.topology?.length &&
      init?.every((item) => item.servers.length > 0)
    ) {
      setDBConfigData(init);
      setEditableRowKeys(init?.map((item) => item.id));
    } else {
      if (standAlone) {
        const mock = [
          {
            id: (Date.now() + 1).toString(),
            name: 'zone1',
            servers: [],
            rootservice: undefined,
          },
        ];
        setDBConfigData(mock);
        setEditableRowKeys(mock?.map((item) => item.id));
      } else {
        const mock = [
          {
            id: (Date.now() + 1).toString(),
            name: 'zone1',
            servers: [],
            rootservice: undefined,
          },
          {
            id: (Date.now() + 2).toString(),
            name: 'zone2',
            servers: [],
            rootservice: undefined,
          },
          {
            id: (Date.now() + 3).toString(),
            name: 'zone3',
            servers: [],
            rootservice: undefined,
          },
        ];
        setDBConfigData(mock);
        setEditableRowKeys(mock?.map((item) => item.id));
      }
    }
  }, [standAlone]);

  // all servers
  const [allOBServer, setAllOBServer] = useState<string[]>([]);
  // all zone servers
  const [allZoneOBServer, setAllZoneOBServer] = useState<any>({});
  const [lastDeleteServer, setLastDeleteServer] = useState<string>('');

  const { run: getUserInfo } = useRequest(getObdInfo, {
    onSuccess: ({ success, data }: API.OBResponseServiceInfo_) => {
      if (success) {
        form.setFieldsValue({
          auth: {
            user: data?.user || undefined,
          },
          home_path: data?.user === 'root' ? '/root' : `/home/${data?.user}`,
        });
      }
    },
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const handleDelete = (id: string) => {
    setDBConfigData(dbConfigData.filter((item) => item.id !== id));
  };

  const setData = (dataSource: FormValues) => {
    let newComponents: API.Components = {};
    const currentDnsType = dataSource.obproxy?.dnsType === 'vip';
    if (selectedConfig.includes(obproxyComponent)) {
      newComponents.obproxy = {
        ...(components.obproxy || {}),
        ...dataSource.obproxy,
        dnsType: undefined,
        dns: !currentDnsType ? dataSource.obproxy?.dns : undefined,
        vip_port: currentDnsType ? dataSource.obproxy?.vip_port : undefined,
        vip_address: currentDnsType
          ? dataSource.obproxy?.vip_address
          : undefined,
      };
    }
    if (selectedConfig.includes(obagentComponent)) {
      newComponents.obagent = {
        ...(components.obagent || {}),
        servers: allOBServer,
      };
    }
    if (selectedConfig.includes(configServerComponent)) {
      newComponents.obconfigserver = {
        ...(components.obconfigserver || {}),
        ...dataSource?.obconfigserver,
      };
    }
    if (selectedConfig.includes(grafanaComponent)) {
      newComponents.grafana = {
        ...(components?.grafana || {}),
        ...dataSource.grafana,
      };
    }
    if (selectedConfig.includes(prometheusComponent)) {
      newComponents.prometheus = {
        ...(components?.prometheus || {}),
        ...dataSource.prometheus,
      };
    }

    newComponents.oceanbase = {
      ...(components.oceanbase || {}),
      topology: dbConfigData?.map((item) => ({
        ...item,
        servers: item?.servers?.map((server) => ({ ip: server })),
      })),
    };
    setConfigData({
      ...configData,
      components: newComponents,
      auth: dataSource.auth,
      home_path: `${
        dataSource.home_path
          ? `${dataSource.home_path}${homePathSuffix}`
          : undefined
      }`,
    });
  };

  const prevStep = () => {
    const formValues = form.getFieldsValue(true);
    setData(formValues);
    setCurrentStep(1);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const nextStep = () => {
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
        setData(formValues);
        setCurrentStep(3);
        setErrorVisible(false);
        setErrorsList([]);
        window.scrollTo(0, 0);
      })
      .finally(() => {
        finalValidate.current = false;
      });
  };

  const formatOptions = (data: string[]) =>
    data?.map((item) => ({ label: item, value: item }));

  const onValuesChange = (values: FormValues) => {
    if (values?.auth?.user) {
      form.setFieldsValue({
        home_path:
          values?.auth?.user === 'root'
            ? '/root'
            : `/home/${values?.auth?.user}`,
      });
    }
  };

  const getComponentServers = (
    component:
      | 'obproxy'
      | 'ocpexpress'
      | 'obconfigserver'
      | 'grafana'
      | 'prometheus',
  ): string[] => {
    const allServers = getAllServers(dbConfigData);
    const compoentServers = form.getFieldValue([component, 'servers']);
    const componentTextMap = {
      obproxy: 'OBProxy',
      ocpexpress: 'OCP Express',
      obconfigserver: 'obconfigserver',
      prometheus: 'prometheus',
      grafana: 'grafana',
    };
    const customComponentServers = compoentServers?.filter(
      (item: string) =>
        !(allServers?.includes(item) || item === lastDeleteServer),
    );
    let componentServerValue;
    if (allServers?.length) {
      const checkPass = serverReg.test(allServers[0]);
      if (!compoentServers?.length) {
        componentServerValue = [allServers[0]];
      } else {
        const newComponentServers: string[] = compoentServers?.filter(
          (item: string) => allServers?.includes(item),
        );
        if (newComponentServers?.length) {
          componentServerValue = [
            ...customComponentServers,
            ...newComponentServers,
          ];
        } else if (customComponentServers?.length) {
          componentServerValue = customComponentServers;
        } else {
          componentServerValue = [allServers[0]];
          if (!checkPass) {
            form.setFields([
              {
                name: [component, 'servers'],
                errors: [
                  intl.formatMessage(
                    {
                      id: 'OBD.pages.Obdeploy.NodeConfig.SelectTheCorrectComponenttextmapcomponentNode',
                      defaultMessage:
                        '请选择正确的{{componentTextMapComponent}}节点',
                    },
                    { componentTextMapComponent: componentTextMap[component] },
                  ),
                ],
              },
            ]);
          }
        }
      }
    } else {
      if (!customComponentServers?.length) {
        componentServerValue = undefined;
      } else {
        componentServerValue = customComponentServers;
      }
    }
    return componentServerValue;
  };

  useEffect(() => {
    const allServers = getAllServers(dbConfigData);
    const allZoneServers: any = {};
    dbConfigData.forEach((item) => {
      allZoneServers[`${item.id}`] = item.servers || [];
    });
    form.setFieldsValue({
      obproxy: {
        servers: getComponentServers('obproxy'),
      },
      obconfigserver: {
        servers: getComponentServers('obconfigserver'),
      },
      grafana: {
        servers: getComponentServers('grafana'),
      },
      prometheus: {
        servers: getComponentServers('prometheus'),
      },
    });

    setAllOBServer(allServers);
    setAllZoneOBServer(allZoneServers);
  }, [dbConfigData, lastDeleteServer]);

  useEffect(() => {
    if (!auth?.user) {
      getUserInfo();
    }
    if (obproxy?.dns !== undefined || obproxy?.vip_address !== undefined) {
      setShow(true);
    }
  }, []);

  const nameValidator = ({ field }: any, value: string) => {
    const currentId = field.split('.')[0];
    let validtor = true;
    const reg = /^[a-zA-Z]([a-zA-Z0-9_]{0,30})[a-zA-Z0-9]$/;
    if (value) {
      if (reg.test(value)) {
        dbConfigData.some((item) => {
          if (currentId !== item.id && item.name === value) {
            validtor = false;
            return true;
          }
          return false;
        });
      } else {
        return Promise.reject(
          new Error(
            intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.ItStartsWithALetter',
              defaultMessage:
                '以英文字母开头，英文或数字结尾，可包含英文数字和下划线且长度在 2-32 个字符之间',
            }),
          ),
        );
      }
    }
    if (validtor) {
      return Promise.resolve();
    }
    return Promise.reject(
      new Error(
        intl.formatMessage({
          id: 'OBD.pages.components.NodeConfig.ZoneNameAlreadyOccupied',
          defaultMessage: 'Zone 名称已被占用',
        }),
      ),
    );
  };

  const ocpServersValidator = (_: any, value: string[]) => {
    if (value?.length > 1) {
      return Promise.reject(
        new Error(
          intl.formatMessage({
            id: 'OBD.pages.components.NodeConfig.OnlyOneNodeCanBe',
            defaultMessage: '仅可选择或输入一个节点',
          }),
        ),
      );
    }
    if (value?.some((item) => !validator.isIP(item))) {
      return Promise.reject(
        new Error(
          intl.formatMessage({
            id: 'OBD.pages.components.NodeConfig.SelectTheCorrectOcpExpress',
            defaultMessage: '请选择正确的 OCP Express 节点',
          }),
        ),
      );
    } else {
      return Promise.resolve();
    }
  };

  const columns: ProColumns<API.DBConfig>[] = [
    {
      title: (
        <>
          {intl.formatMessage({
            id: 'OBD.pages.components.NodeConfig.ZoneName',
            defaultMessage: 'Zone 名称',
          })}

          <Tooltip
            title={intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.AZoneThatRepresentsA',
              defaultMessage:
                '可用区，表示集群内具有相似硬件可用性的一组节点，通常为同一个机架、机房或地域。',
            })}
          >
            <QuestionCircleOutlined className="ml-10" />
          </Tooltip>
        </>
      ),

      dataIndex: 'name',

      ...(standAlone ? { width: '30%' } : { width: 224 }),
      formItemProps: {
        rules: [
          {
            required: true,
            whitespace: false,
            message: intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.ThisItemIsRequired',
              defaultMessage: '此项是必填项',
            }),
          },
          { validator: nameValidator },
        ],
      },
    },
    {
      title: (
        <>
          {intl.formatMessage({
            id: 'OBD.pages.components.NodeConfig.ObserverNodes',
            defaultMessage: 'OBServer 节点',
          })}

          <Tooltip
            title={intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.TheNodeWhereDatabaseService',
              defaultMessage:
                '数据库服务（OBServer）所在节点，包含 SQL 引擎、事务引擎和存储引擎，并服务多个数据分区。',
            })}
          >
            <QuestionCircleOutlined className="ml-10" />
          </Tooltip>
        </>
      ),
      ...(standAlone ? { width: '30%' } : {}),

      dataIndex: 'servers',
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
                      id: 'OBD.component.NodeConfig.TheValidatorNode',
                      defaultMessage: '请输入正确的 OBProxy 节点',
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
            setLastDeleteServer={setLastDeleteServer}
          />
        ) : null;
      },
    },
    ...(!standAlone
      ? [
          {
            title: (
              <>
                {intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.RootserverNodes',
                  defaultMessage: 'RootServer 节点',
                })}

                <Tooltip
                  title={intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.TheNodeWhereTheMaster',
                    defaultMessage:
                      '总控服务（RootService）所在节点，用于执行集群管理、服务器管理、自动负载均衡等操作。',
                  })}
                >
                  <QuestionCircleOutlined className="ml-10" />
                </Tooltip>
              </>
            ),

            dataIndex: 'rootservice',
            formItemProps: {
              rules: [
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.ThisOptionIsRequired',
                    defaultMessage: '此项是必选项',
                  }),
                },
                {
                  pattern: serverReg,
                  message: intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.SelectTheCorrectRootserverNode',
                    defaultMessage: '请选择正确的 RootServer 节点',
                  }),
                },
              ],
            },
            width: 224,
            renderFormItem: (_: any, { isEditable, record }: any) => {
              // rootservice options are items entered by the OBServer
              const options = record?.servers
                ? formatOptions(record?.servers)
                : [];
              return isEditable ? (
                <Select
                  options={options}
                  placeholder={intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.PleaseSelect',
                    defaultMessage: '请选择',
                  })}
                />
              ) : null;
            },
          },
          {
            title: '',
            valueType: 'option',
            width: 20,
          },
        ]
      : []),
  ];

  const initialValues: FormValues = {
    obproxy: {
      servers: obproxy?.servers?.length ? obproxy?.servers : undefined,
      vip_address: obproxy?.vip_address,
      dns: obproxy?.dns,
      dnsType: obproxy?.vip_address !== undefined ? 'vip' : 'dns',
      vip_port: obproxy?.vip_port || 2883,
    },
    prometheus: {
      servers: prometheus?.servers?.length ? prometheus?.servers : undefined,
    },
    grafana: {
      servers: grafana?.servers?.length ? grafana?.servers : undefined,
    },
    obconfigserver: {
      servers: obconfigserver?.servers?.length
        ? obconfigserver?.servers
        : undefined,
    },
    auth: {
      user: auth?.user || undefined,
      password: auth?.password || undefined,
      port: auth?.port || 22,
    },
    home_path: initHomePath,
  };
  if (!lowVersion) {
    initialValues.ocpexpress = {
      servers: ocpexpress?.servers?.length
        ? [ocpexpress?.servers[0]]
        : undefined,
    };
  }

  const componentsToCheck = [
    obproxyComponent,
    configServerComponent,
    prometheusComponent,
    grafanaComponent,
  ];
  const shouldIncludeComponent = componentsToCheck.some((component) =>
    selectedConfig.includes(component),
  );

  const dns = ProForm.useWatch(['obproxy', 'dnsType'], form);

  return (
    <ProForm
      form={form}
      submitter={false}
      onValuesChange={onValuesChange}
      initialValues={initialValues}
      grid={true}
      validateTrigger={['onBlur', 'onChange']}
    >
      <Space direction="vertical" size="middle">
        <ProCard
          className={styles.pageCard}
          title={intl.formatMessage({
            id: 'OBD.pages.components.NodeConfig.DatabaseNodeConfiguration',
            defaultMessage: '数据库节点配置',
          })}
        >
          <EditableProTable<API.DBConfig>
            className={styles.nodeEditabletable}
            columns={columns}
            rowKey="id"
            value={dbConfigData}
            editableFormRef={tableFormRef}
            onChange={setDBConfigData}
            recordCreatorProps={
              // 单机版，关闭默认的新建按钮
              !standAlone
                ? {
                    newRecordType: 'dataSource',
                    record: () => ({
                      id: Date.now().toString(),
                      name: `zone${nameIndex}`,
                    }),
                    onClick: () => setNameIndex(nameIndex + 1),
                    creatorButtonText: intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.AddZone',
                      defaultMessage: '新增 Zone',
                    }),
                  }
                : false
            }
            editable={{
              type: 'multiple',
              form: editableForm,
              editableKeys,
              actionRender: (row) => {
                if (dbConfigData?.length === 1) {
                  return (
                    <Tooltip
                      title={intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.KeepAtLeastOneZone',
                        defaultMessage: '至少保留一个 zone',
                      })}
                    >
                      <span className={styles.disabledDel}>
                        <DeleteOutlined />
                      </span>
                    </Tooltip>
                  );
                }
                if (!row?.servers?.length && !row?.rootservice) {
                  return (
                    <DeleteOutlined
                      onClick={() => handleDelete(row.id)}
                      style={{ color: '#8592ad' }}
                    />
                  );
                }
                return (
                  <Popconfirm
                    title={intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.AreYouSureYouWant',
                      defaultMessage: '确定删除该条 Zone 的相关配置吗？',
                    })}
                    onConfirm={() => handleDelete(row.id)}
                  >
                    <DeleteOutlined style={{ color: '#8592ad' }} />
                  </Popconfirm>
                );
              },
              onValuesChange: (editableItem, recordList) => {
                if (!editableItem?.id) {
                  return;
                }
                const editorServers =
                  editableItem?.servers?.map((item) => item.trim()) || [];
                const rootService = editableItem?.rootservice;
                let newRootService = rootService;
                const serversErrors = editableForm.getFieldError([
                  editableItem?.id,
                  'servers',
                ]);

                if (editorServers.length) {
                  if (!rootService || !editorServers.includes(rootService)) {
                    newRootService = editorServers[0];
                  }
                  if (editorServers.find((item) => item === '127.0.0.1')) {
                    message.warning(
                      intl.formatMessage({
                        id: 'OBD.component.MetaDBConfig.NodeConfig.B663132E',
                        defaultMessage:
                          '依据 OceanBase 最佳实践，建议使用非 127.0.0.1 IP 地址',
                      }),
                    );
                  }
                } else {
                  newRootService = undefined;
                }
                editableForm.setFieldsValue({
                  [editableItem?.id]: {
                    rootservice: newRootService,
                  },
                });
                if (!newRootService) {
                  tableFormRef?.current?.setFields([
                    {
                      name: [editableItem.id, 'rootservice'],
                      touched: false,
                    },
                  ]);
                } else if (
                  editorServers?.length === 1 &&
                  serversErrors.length
                ) {
                  tableFormRef?.current?.setFields([
                    {
                      name: [editableItem.id, 'rootservice'],
                      errors: [
                        intl.formatMessage({
                          id: 'OBD.pages.components.NodeConfig.SelectTheCorrectRootserverNode',
                          defaultMessage: '请选择正确的 RootServer 节点',
                        }),
                      ],
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
                    'servers',
                  ]);
                  if (errors?.length) {
                    let errordom = document.getElementById(
                      `server-${editableItem.id}`,
                    );
                    errordom?.focus();
                    tableFormRef?.current?.setFields([
                      {
                        name: [editableItem.id, 'servers'],
                        errors: errors,
                      },
                    ]);
                  } else {
                    editableForm.setFieldsValue({
                      [editableItem?.id]: {
                        servers: editorServers,
                      },
                    });
                  }
                }
                const newRecordList = recordList.map((item) => {
                  if (item.id === editableItem.id) {
                    return {
                      ...editableItem,
                      rootservice: newRootService,
                      servers: editorServers,
                    };
                  }
                  return item;
                });
                setDBConfigData(newRecordList);
              },
              onChange: setEditableRowKeys,
            }}
          />
        </ProCard>
        {shouldIncludeComponent ? (
          <ProCard
            className={styles.pageCard}
            title={intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.ComponentNodeConfiguration',
              defaultMessage: '组件节点配置',
            })}
            bodyStyle={{ paddingBottom: '0', paddingLeft: '8px' }}
          >
            {selectedConfig.includes(obproxyComponent) && (
              <div style={{ paddingLeft: '16px' }}>
                <ProFormSelect
                  mode="tags"
                  name={['obproxy', 'servers']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.ObproxyNodes',
                    defaultMessage: 'OBProxy 节点',
                  })}
                  fieldProps={{ style: commonServerStyle, maxTagCount: 3 }}
                  placeholder={intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.PleaseSelect',
                    defaultMessage: '请选择',
                  })}
                  validateFirst
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.SelectOrEnterObproxyNodes',
                        defaultMessage: '请选择或输入 OBProxy 节点',
                      }),
                    },
                    {
                      validator: (_: any, value: string[]) =>
                        serversValidator(_, value, 'OBProxy'),
                    },
                  ]}
                  options={formatOptions(allOBServer)}
                />
                <div
                  style={{
                    background: '#f8fafe',
                    marginTop: 16,
                    marginBottom: 16,
                    padding: 16,
                  }}
                >
                  <Space size={8} onClick={() => setShow(!show)}>
                    {show ? <CaretDownOutlined /> : <CaretRightOutlined />}

                    <Tooltip
                      title={intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.B4449024',
                        defaultMessage:
                          '用于业务访问 OceanBase 集群，建议部署多节点 OBProxy 时提供 VIP/DNS 地址，避免后期更改 OBProxy 访问地址。若不配置，系统默认选择第一个 IP 地址设置连接串。',
                      })}
                    >
                      <span>
                        {intl.formatMessage({
                          id: 'OBD.pages.components.obproxyConfig.D42DEEB1',
                          defaultMessage: '负载均衡管理',
                        })}
                      </span>
                      <QuestionCircleOutlined style={{ marginLeft: 4 }} />
                    </Tooltip>
                  </Space>
                  {show && (
                    <Row gutter={[8, 0]} style={{ marginTop: 24 }}>
                      <Col span={8}>
                        <ProFormSelect
                          mode="single"
                          name={['obproxy', 'dnsType']}
                          label={intl.formatMessage({
                            id: 'OBD.pages.components.NodeConfig.B4449036',
                            defaultMessage: '访问方式',
                          })}
                          placeholder={intl.formatMessage({
                            id: 'OBD.pages.components.NodeConfig.PleaseSelect',
                            defaultMessage: '请选择',
                          })}
                          options={[
                            {
                              label: intl.formatMessage({
                                id: 'OBD.pages.components.NodeConfig.B4449037',
                                defaultMessage: 'VIP',
                              }),
                              value: 'vip',
                            },
                            {
                              label: intl.formatMessage({
                                id: 'OBD.pages.components.NodeConfig.B4449038',
                                defaultMessage: 'DNS（域名）',
                              }),
                              value: 'dns',
                            },
                          ]}
                        />
                      </Col>
                      {
                        <>
                          <Col span={8}>
                            <ProFormText
                              name={
                                dns === 'vip'
                                  ? ['obproxy', 'vip_address']
                                  : ['obproxy', 'dns']
                              }
                              label={
                                dns === 'vip' ? (
                                  intl.formatMessage({
                                    id: 'OBD.pages.components.NodeConfig.B4449039',
                                    defaultMessage: 'IP 地址',
                                  })
                                ) : (
                                  <Tooltip
                                    title={intl.formatMessage({
                                      id: 'OBD.pages.components.NodeConfig.B4449034',
                                      defaultMessage:
                                        '用于指向 VIP 及端口的配置信息，平台未提供 VIP 与域名的映射关系，需自行准备域名解析服务。',
                                    })}
                                  >
                                    {intl.formatMessage({
                                      id: 'OBD.pages.components.NodeConfig.B4449033',
                                      defaultMessage: '域名',
                                    })}
                                    <QuestionCircleOutlined
                                      style={{ marginLeft: 4 }}
                                    />
                                  </Tooltip>
                                )
                              }
                              formItemProps={{
                                rules: [
                                  {
                                    required: true,
                                    message: '此项是必填项',
                                  },
                                  ...[
                                    dns === 'vip'
                                      ? {
                                          validator: (
                                            _: any,
                                            value: string[],
                                          ) =>
                                            serversValidator(
                                              _,
                                              [value],
                                              'OBServer',
                                            ),
                                        }
                                      : {
                                          validator: (
                                            _: any,
                                            value: string[],
                                          ) => dnsValidator(_, [value]),
                                        },
                                  ],
                                ],
                              }}
                            />
                          </Col>
                          {dns === 'vip' && (
                            <Col span={8}>
                              <ProFormDigit
                                name={['obproxy', 'vip_port']}
                                label={intl.formatMessage({
                                  id: 'OBD.pages.components.NodeConfig.B4449032',
                                  defaultMessage: '访问端口',
                                })}
                                fieldProps={{ style: commonStyle }}
                                placeholder={intl.formatMessage({
                                  id: 'OBD.pages.components.NodeConfig.PleaseEnter',
                                  defaultMessage: '请输入',
                                })}
                              />
                            </Col>
                          )}
                        </>
                      }
                    </Row>
                  )}
                </div>
              </div>
            )}
            <Row gutter={[16, 0]}>
              {selectedConfig.includes(prometheusComponent) && (
                <Col span={8}>
                  <ProFormSelect
                    mode="tags"
                    name={['prometheus', 'servers']}
                    label={'Prometheus 节点'}
                    fieldProps={{ style: commonServerStyle, maxTagCount: 3 }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.PleaseSelect',
                      defaultMessage: '请选择',
                    })}
                    validateFirst
                    rules={[
                      {
                        required: true,
                        message: '请选择或输入 Prometheus 节点',
                      },
                      {
                        validator: (_: any, value: string[]) =>
                          serversValidator(_, value, 'OBServer'),
                      },
                    ]}
                    options={formatOptions(allOBServer)}
                  />
                </Col>
              )}

              {selectedConfig.includes(grafanaComponent) && (
                <Col span={8}>
                  <ProFormSelect
                    mode="tags"
                    name={['grafana', 'servers']}
                    label={'Grafana 节点'}
                    fieldProps={{ style: commonServerStyle, maxTagCount: 3 }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.PleaseSelect',
                      defaultMessage: '请选择',
                    })}
                    validateFirst
                    rules={[
                      {
                        required: true,
                        message: '请选择或输入 grafana 节点',
                      },
                      {
                        validator: (_: any, value: string[]) =>
                          serversValidator(_, value, 'OBServer'),
                      },
                    ]}
                    options={formatOptions(allOBServer)}
                  />
                </Col>
              )}

              {selectedConfig.includes(configServerComponent) && (
                <Col span={6}>
                  <ProFormSelect
                    mode="tags"
                    name={['obconfigserver', 'servers']}
                    label={intl.formatMessage({
                      id: 'OBD.pages.Obdeploy.NodeConfig.ObconfigserverNodes',
                      defaultMessage: 'OBConfigServer 节点',
                    })}
                    fieldProps={{
                      style: commonServerStyle,
                    }}
                    validateFirst
                    placeholder={intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.PleaseSelect',
                      defaultMessage: '请选择',
                    })}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.Obdeploy.NodeConfig.SelectOrEnterObConfigserver',
                          defaultMessage: '请选择或输入 OB ConfigServer 节点',
                        }),
                      },
                      {
                        validator: (_: any, value: string[]) =>
                          serversValidator(_, value, 'obconfigserver'),
                      },
                    ]}
                    options={formatOptions(allOBServer)}
                  />
                </Col>
              )}
            </Row>
          </ProCard>
        ) : null}
        <ProCard
          className={styles.pageCard}
          title={
            <>
              部署连接配置
              <span className={styles.titleExtra}>
                请确保您选择的用户名和密码在如上所有主机上保持一致
              </span>
            </>
          }
          bodyStyle={{ paddingBottom: '0' }}
        >
          <Space size={16}>
            <ProFormText
              name={['auth', 'user']}
              label={intl.formatMessage({
                id: 'OBD.pages.components.NodeConfig.Username',
                defaultMessage: '用户名',
              })}
              fieldProps={{ style: commonStyle }}
              placeholder={intl.formatMessage({
                id: 'OBD.pages.components.NodeConfig.StartUser',
                defaultMessage: '启动用户',
              })}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.EnterAUsername',
                    defaultMessage: '请输入用户名',
                  }),
                },
                {
                  pattern: /^([a-zA-Z0-9.]{1,20})$/,
                  message: intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.OnlyEnglishNumbersAndDots',
                    defaultMessage: '仅支持英文、数字和点且长度不超过20',
                  }),
                },
              ]}
            />

            {locale === 'zh-CN' ? (
              <ProFormText.Password
                name={['auth', 'password']}
                label={
                  <>
                    {intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.Password',
                      defaultMessage: '密码',
                    })}

                    <Tooltip
                      title={intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.IfThePasswordIsEmpty',
                        defaultMessage:
                          '密码为空时，将使用密钥登录，请勿使用带口令的密钥',
                      })}
                    >
                      <QuestionCircleOutlined className="ml-10" />
                    </Tooltip>
                  </>
                }
                fieldProps={{
                  style: { width: 328 },
                  autoComplete: 'new-password',
                }}
                placeholder={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.IfThePasswordFreeConfiguration',
                  defaultMessage: '若各节点间已完成免密配置，则密码可置空',
                })}
              />
            ) : (
              <Form.Item
                name={['auth', 'password']}
                label={
                  <>
                    {intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.Password',
                      defaultMessage: '密码',
                    })}

                    <Tooltip
                      title={intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.IfThePasswordIsEmpty',
                        defaultMessage:
                          '密码为空时，将使用密钥登录，请勿使用带口令的密钥',
                      })}
                    >
                      <QuestionCircleOutlined className="ml-10" />
                    </Tooltip>
                  </>
                }
              >
                <TooltipInput
                  name="auth_password"
                  placeholder={intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.IfThePasswordFreeConfiguration',
                    defaultMessage: '若各节点间已完成免密配置，则密码可置空',
                  })}
                  fieldProps={{
                    style: { width: 328 },
                    autoComplete: 'new-password',
                  }}
                  isPassword
                />
              </Form.Item>
            )}

            <ProFormDigit
              name={['auth', 'port']}
              label={intl.formatMessage({
                id: 'OBD.pages.components.NodeConfig.SshPort',
                defaultMessage: 'SSH 端口',
              })}
              fieldProps={{ style: commonStyle }}
              placeholder={intl.formatMessage({
                id: 'OBD.pages.components.NodeConfig.PleaseEnter',
                defaultMessage: '请输入',
              })}
            />
          </Space>
        </ProCard>
        <ProCard
          className={styles.pageCard}
          title={intl.formatMessage({
            id: 'OBD.pages.components.NodeConfig.SoftwarePathConfiguration',
            defaultMessage: '软件路径配置',
          })}
          bodyStyle={{ paddingBottom: '0' }}
        >
          <ProFormText
            name="home_path"
            label={intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.SoftwarePath',
              defaultMessage: '软件路径',
            })}
            fieldProps={{ style: { width: 568 }, addonAfter: homePathSuffix }}
            placeholder={intl.formatMessage({
              id: 'OBD.pages.components.NodeConfig.HomeStartUser',
              defaultMessage: '/home/启动用户',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.EnterTheSoftwarePath',
                  defaultMessage: '请输入软件路径',
                }),
              },
              pathRule,
            ]}
          />
        </ProCard>
        <footer className={styles.pageFooterContainer}>
          <div className={styles.pageFooter}>
            <Space className={styles.foolterAction}>
              <Button
                onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
                data-aspm-click="c307506.d317278"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.NodeConfigurationExit',
                  defaultMessage: '节点配置-退出',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.Exit',
                  defaultMessage: '退出',
                })}
              </Button>
              <Tooltip
                title={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.TheCurrentPageConfigurationHas',
                  defaultMessage: '当前页面配置已保存',
                })}
              >
                <Button
                  onClick={prevStep}
                  data-aspm-click="c307506.d317277"
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.NodeConfigurationPreviousStep',
                    defaultMessage: '节点配置-上一步',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  {intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.PreviousStep',
                    defaultMessage: '上一步',
                  })}
                </Button>
              </Tooltip>
              <Button
                type="primary"
                onClick={nextStep}
                data-aspm-click="c307506.d317279"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.NodeConfigurationNext',
                  defaultMessage: '节点配置-下一步',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.NextStep',
                  defaultMessage: '下一步',
                })}
              </Button>
            </Space>
          </div>
        </footer>
      </Space>
    </ProForm>
  );
}
