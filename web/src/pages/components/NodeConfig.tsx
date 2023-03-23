import { useEffect, useState, useRef } from 'react';
import { useModel } from 'umi';
import { Space, Button, Tooltip, Select, Popconfirm, message } from 'antd';
import { QuestionCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import {
  ProCard,
  ProForm,
  ProFormText,
  ProFormSelect,
  EditableProTable,
} from '@ant-design/pro-components';
import type {
  ProColumns,
  EditableFormInstance,
} from '@ant-design/pro-components';
import { getObdInfo } from '@/services/ob-deploy-web/Info';
import useRequest from '@/utils/useRequest';
import { handleQuit } from '@/utils';
import { commonStyle, pathRule } from '../constants';
import ServerTags from './ServerTags';
import styles from './index.less';

interface FormValues extends API.Components {
  auth?: {
    user?: string;
    password?: string;
  };
  home_path?: string;
}

export default function NodeConfig() {
  const {
    setCurrentStep,
    configData,
    setConfigData,
    currentType,
    lowVersion,
    handleQuitProgress,
    nameIndex,
    setNameIndex,
  } = useModel('global');
  const { components = {}, auth, home_path } = configData || {};
  const { oceanbase = {}, ocpexpress = {}, obproxy = {} } = components;
  const [form] = ProForm.useForm();
  const [editableForm] = ProForm.useForm();
  const tableFormRef = useRef<EditableFormInstance<API.DBConfig>>();

  const initDBConfigData = oceanbase?.topology?.length
    ? oceanbase?.topology?.map((item: API.Zone, index: number) => ({
        id: (Date.now() + index).toString(),
        ...item,
        servers: item?.servers?.map((server) => server?.ip),
      }))
    : [
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

  const homePathSuffix = `/${oceanbase.appname}`;

  const initHomePath = home_path
    ? home_path.substring(0, home_path.length - homePathSuffix.length)
    : undefined;

  const [dbConfigData, setDBConfigData] =
    useState<API.DBConfig[]>(initDBConfigData);
  const [editableKeys, setEditableRowKeys] = useState<React.Key[]>(() =>
    dbConfigData.map((item) => item.id),
  );
  // all servers
  const [allOBServer, setAllOBServer] = useState<string[]>([]);
  // all zone servers
  const [allZoneOBServer, setAllZoneOBServer] = useState<any>({});
  const [lastDeleteServer, setLastDeleteServer] = useState<string>('');

  const serverReg =
    /^((\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.){3}(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])?$/;

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
  });

  const handleDelete = (id: string) => {
    setDBConfigData(dbConfigData.filter((item) => item.id !== id));
  };

  const setData = (dataSource: FormValues) => {
    let newComponents: API.Components = {};
    if (currentType === 'all') {
      newComponents.obproxy = {
        ...(components.obproxy || {}),
        ...dataSource.obproxy,
      };
      if (!lowVersion) {
        newComponents.ocpexpress = {
          ...(components.ocpexpress || {}),
          ...dataSource?.ocpexpress,
        };
      }
      newComponents.obagent = {
        ...(components.obagent || {}),
        servers: allOBServer,
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
  };

  const nextStep = () => {
    const tableFormRefValidate = () => {
      return tableFormRef?.current?.validateFields().then((values) => {
        return values;
      });
    };

    const formValidate = () => {
      return form.validateFields().then((values) => {
        return values;
      });
    };

    Promise.all([tableFormRefValidate(), formValidate()]).then((result) => {
      const formValues = result?.[1];
      setData(formValues);
      setCurrentStep(3);
    });
  };

  const formatOptions = (data: string[]) =>
    data?.map((item) => ({ label: item, value: item }));

  const getAllServers = (dataSource: API.DBConfig[]) => {
    const allServersList = dataSource.map((item) => item.servers);
    let newAllOBServer: string[] = [];
    allServersList.forEach((item) => {
      if (item && item.length) {
        newAllOBServer = [...newAllOBServer, ...item];
      }
    });
    return newAllOBServer;
  };

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

  useEffect(() => {
    const allServers = getAllServers(dbConfigData);
    const allZoneServers: any = {};
    dbConfigData.forEach((item) => {
      allZoneServers[`${item.id}`] = item.servers;
    });
    const obproxyServers = form.getFieldValue(['obproxy', 'servers']);
    const ocpexpressServers = form.getFieldValue(['ocpexpress', 'servers']);
    const customOBproxyServers = obproxyServers?.filter(
      (item: string) =>
        !(allServers?.includes(item) || item === lastDeleteServer),
    );
    const customOcpexpressServers = ocpexpressServers?.filter(
      (item: string) =>
        !(allServers?.includes(item) || item === lastDeleteServer),
    );
    let obproxyServersValue;
    let ocpexpressServersValue;
    if (allServers?.length) {
      const checkPass = serverReg.test(allServers[0]);
      if (!obproxyServers?.length) {
        obproxyServersValue = [allServers[0]];
      } else {
        const newOBproxyServers: string[] = [];
        obproxyServers?.forEach((item: string) => {
          if (allServers?.includes(item)) {
            newOBproxyServers.push(item);
          }
        });
        if (newOBproxyServers?.length) {
          obproxyServersValue = [...customOBproxyServers, ...newOBproxyServers];
        } else if (customOBproxyServers?.length) {
          obproxyServersValue = customOBproxyServers;
        } else {
          obproxyServersValue = [allServers[0]];
          if (!checkPass) {
            form.setFields([
              {
                name: ['obproxy', 'servers'],
                errors: ['请选择正确的 OBProxy 节点'],
              },
            ]);
          }
        }
      }

      if (!ocpexpressServers?.length) {
        ocpexpressServersValue = [allServers[0]];
      } else {
        const newOcpexpressServers: string[] = [];
        ocpexpressServers?.forEach((item: string) => {
          if (allServers?.includes(item)) {
            newOcpexpressServers.push(item);
          }
        });
        if (newOcpexpressServers?.length) {
          ocpexpressServersValue = [
            ...customOcpexpressServers,
            ...newOcpexpressServers,
          ];
        } else if (customOcpexpressServers?.length) {
          ocpexpressServersValue = customOcpexpressServers;
        } else {
          ocpexpressServersValue = [allServers[0]];
          if (!checkPass) {
            form.setFields([
              {
                name: ['ocpexpress', 'servers'],
                errors: ['请选择正确的 OCPExpress 节点'],
              },
            ]);
          }
        }
      }
    } else {
      if (!customOBproxyServers?.length) {
        obproxyServersValue = undefined;
      } else {
        obproxyServersValue = customOBproxyServers;
      }
      if (!customOcpexpressServers?.length) {
        ocpexpressServersValue = undefined;
      } else {
        ocpexpressServersValue = customOcpexpressServers;
      }
    }

    form.setFieldsValue({
      obproxy: {
        servers: obproxyServersValue,
      },
      ocpexpress: {
        servers: ocpexpressServersValue,
      },
    });

    setAllOBServer(allServers);
    setAllZoneOBServer(allZoneServers);
  }, [dbConfigData, lastDeleteServer]);

  useEffect(() => {
    if (!auth?.user) {
      getUserInfo();
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
            '以英文字母开头，英文或数字结尾，可包含英文数字和下划线且长度在 2-32 个字符之间',
          ),
        );
      }
    }
    if (validtor) {
      return Promise.resolve();
    }
    return Promise.reject(new Error('Zone 名称已被占用'));
  };

  const ocpServersValidator = (_: any, value: string[]) => {
    let validtor = true;
    if (value?.length > 1) {
      return Promise.reject(new Error('仅可选择或输入一个节点'));
    }
    if (value && value.length) {
      value.some((item) => {
        validtor = serverReg.test(item.trim());
        return !serverReg.test(item.trim());
      });
    }
    if (validtor) {
      return Promise.resolve();
    }
    return Promise.reject(new Error('请选择正确的 OCPExpress 节点'));
  };

  const serversValidator = (_: any, value: string[], type: string) => {
    let validtor = true;
    if (value && value.length) {
      value.some((item) => {
        validtor = serverReg.test(item.trim());
        return !serverReg.test(item.trim());
      });
    }
    if (validtor) {
      return Promise.resolve();
    }
    if (type === 'OBServer') {
      return Promise.reject(new Error('请输入正确的 IP 地址'));
    } else {
      return Promise.reject(new Error('请选择正确的 OBProxy 节点'));
    }
  };

  const columns: ProColumns<API.DBConfig>[] = [
    {
      title: (
        <>
          Zone 名称
          <Tooltip title="可用区，表示集群内具有相似硬件可用性的一组节点，通常为同一个机架、机房或地域。">
            <QuestionCircleOutlined className="ml-10" />
          </Tooltip>
        </>
      ),
      dataIndex: 'name',
      width: 224,
      formItemProps: {
        rules: [
          { required: true, whitespace: false, message: '此项是必填项' },
          { validator: nameValidator },
        ],
      },
    },
    {
      title: (
        <>
          OBServer 节点
          <Tooltip title="数据库服务（OBServer）所在节点，包含 SQL 引擎、事务引擎和存储引擎，并服务多个数据分区。">
            <QuestionCircleOutlined className="ml-10" />
          </Tooltip>
        </>
      ),
      dataIndex: 'servers',
      formItemProps: {
        rules: [
          { required: true, message: '此项是必填项' },
          {
            validator: (_: any, value: string[]) =>
              serversValidator(_, value, 'OBServer'),
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
    {
      title: (
        <>
          RootServer 节点
          <Tooltip title="总控服务（RootService）所在节点，用于执行集群管理、服务器管理、自动负载均衡等操作。">
            <QuestionCircleOutlined className="ml-10" />
          </Tooltip>
        </>
      ),
      dataIndex: 'rootservice',
      formItemProps: {
        rules: [
          { required: true, message: '此项是必选项' },
          { pattern: serverReg, message: '请选择正确的 RootServer 节点' },
        ],
      },
      width: 224,
      renderFormItem: (_: any, { isEditable, record }: any) => {
        // rootservice options are items entered by the OBServer
        const options = record?.servers ? formatOptions(record?.servers) : [];
        return isEditable ? (
          <Select options={options} placeholder="请选择" />
        ) : null;
      },
    },
    {
      title: '',
      valueType: 'option',
      width: 20,
    },
  ];

  const initialValues: FormValues = {
    obproxy: {
      servers: obproxy?.servers?.length ? obproxy?.servers : undefined,
    },
    auth: {
      user: auth?.user || undefined,
      password: auth?.password || undefined,
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

  return (
    <ProForm
      form={form}
      submitter={false}
      onValuesChange={onValuesChange}
      initialValues={initialValues}
      grid={true}
    >
      <Space direction="vertical" size="middle">
        <ProCard className={styles.pageCard} title="数据库节点配置">
          <EditableProTable<API.DBConfig>
            className={styles.nodeEditabletable}
            columns={columns}
            rowKey="id"
            value={dbConfigData}
            editableFormRef={tableFormRef}
            onChange={setDBConfigData}
            recordCreatorProps={{
              newRecordType: 'dataSource',
              record: () => ({
                id: Date.now().toString(),
                name: `zone${nameIndex}`,
              }),
              onClick: () => setNameIndex(nameIndex + 1),
              creatorButtonText: '新增 Zone',
            }}
            editable={{
              type: 'multiple',
              form: editableForm,
              editableKeys,
              actionRender: (row) => {
                if (dbConfigData?.length === 1) {
                  return (
                    <Tooltip title="至少保留一个 zone">
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
                    title="确定删除该条 Zone 的相关配置吗？"
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
                      errors: ['请选择正确的 RootServer 节点'],
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
                  if (
                    allOBServer.includes(
                      editorServers[editorServers.length - 1],
                    )
                  ) {
                    message.warning('禁止输入重复节点');
                    const rawData = editorServers.slice(
                      0,
                      editorServers.length - 1,
                    );
                    editableForm.setFieldsValue({
                      [editableItem?.id]: {
                        servers: rawData?.length ? rawData : undefined,
                      },
                    });
                    return;
                  }
                  const errors = editableForm.getFieldError([
                    editableItem?.id,
                    'servers',
                  ]);
                  if (errors?.length) {
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
        {currentType === 'all' ? (
          <ProCard
            className={styles.pageCard}
            title="组件节点配置"
            bodyStyle={{ paddingBottom: '0' }}
          >
            <Space>
              {!lowVersion ? (
                <ProFormSelect
                  mode="tags"
                  name={['ocpexpress', 'servers']}
                  label="OCPExpress 节点"
                  fieldProps={{ style: commonStyle }}
                  placeholder="请选择"
                  rules={[
                    { required: true, message: '请选择或输入 OCPExpress 节点' },
                    { validator: ocpServersValidator },
                  ]}
                  options={formatOptions(allOBServer)}
                />
              ) : null}
              <ProFormSelect
                mode="tags"
                name={['obproxy', 'servers']}
                label="OBProxy 节点"
                fieldProps={{ style: { width: 504 }, maxTagCount: 3 }}
                placeholder="请选择"
                rules={[
                  { required: true, message: '请选择或输入 OBProxy 节点' },
                  {
                    validator: (_: any, value: string[]) =>
                      serversValidator(_, value, 'OBProxy'),
                  },
                ]}
                options={formatOptions(allOBServer)}
              />
            </Space>
          </ProCard>
        ) : null}
        <ProCard
          className={styles.pageCard}
          title="部署用户配置"
          bodyStyle={{ paddingBottom: '0' }}
        >
          <Space size={16}>
            <ProFormText
              name={['auth', 'user']}
              label="用户名"
              fieldProps={{ style: commonStyle }}
              placeholder="启动用户"
              rules={[
                { required: true, message: '请输入用户名' },
                {
                  pattern: /^([a-zA-Z0-9.]{1,20})$/,
                  message: '仅支持英文、数字和点且长度不超过20',
                },
              ]}
            />
            <ProFormText.Password
              name={['auth', 'password']}
              label={
                <>
                  密码
                  <Tooltip title="密码为空时，将使用密钥登录，请勿使用带口令的密钥">
                    <QuestionCircleOutlined className="ml-10" />
                  </Tooltip>
                </>
              }
              fieldProps={{
                style: { width: 328 },
                autoComplete: 'new-password',
              }}
              placeholder="若各节点间已完成免密配置，则密码可置空"
            />
          </Space>
        </ProCard>
        <ProCard
          className={styles.pageCard}
          title="软件路径配置"
          bodyStyle={{ paddingBottom: '0' }}
        >
          <ProFormText
            name="home_path"
            label="软件路径"
            fieldProps={{ style: { width: 568 }, addonAfter: homePathSuffix }}
            placeholder="/home/启动用户"
            rules={[{ required: true, message: '请输入软件路径' }, pathRule]}
          />
        </ProCard>
        <footer className={styles.pageFooterContainer}>
          <div className={styles.pageFooter}>
            <Space className={styles.foolterAction}>
              <Button
                onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
                data-aspm-click="c307506.d317278"
                data-aspm-desc="节点配置-退出"
                data-aspm-param={``}
                data-aspm-expo
              >
                退出
              </Button>
              <Tooltip title="当前页面配置已保存">
                <Button
                  onClick={prevStep}
                  data-aspm-click="c307506.d317277"
                  data-aspm-desc="节点配置-上一步"
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  上一步
                </Button>
              </Tooltip>
              <Button
                type="primary"
                onClick={nextStep}
                data-aspm-click="c307506.d317279"
                data-aspm-desc="节点配置-下一步"
                data-aspm-param={``}
                data-aspm-expo
              >
                下一步
              </Button>
            </Space>
          </div>
        </footer>
      </Space>
    </ProForm>
  );
}
