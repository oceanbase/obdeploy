import { intl } from '@/utils/intl';
import { DeleteOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import type {
  EditableFormInstance,
  ProColumns,
} from '@ant-design/pro-components';
import { EditableProTable, ProForm } from '@ant-design/pro-components';
import { Popconfirm, Select, Tooltip } from 'antd';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';

import ServerTags from '@/pages/Obdeploy/ServerTags';
import { serversValidator } from '@/utils';
import { getAllServers } from '@/utils/helper';
import styles from './index.less';

interface DataBaseNodeConfigProps {
  tableFormRef: React.MutableRefObject<
    EditableFormInstance<API.DBConfig> | undefined
  >;
  dbConfigData: API.DBConfig[];
  setDBConfigData: React.Dispatch<React.SetStateAction<API.DBConfig[]>>;
  finalValidate: React.MutableRefObject<boolean>;
}

export default function DataBaseNodeConfig({
  tableFormRef,
  dbConfigData,
  setDBConfigData,
  finalValidate,
}: DataBaseNodeConfigProps) {
  const { ocpConfigData, ocpNameIndex, setOcpNameIndex } = useModel('global');
  const { components = {} } = ocpConfigData || {};
  const { oceanbase = {} } = components;
  const [editableForm] = ProForm.useForm();
  const [allZoneOBServer, setAllZoneOBServer] = useState<any>({});
  const [allOBServer, setAllOBServer] = useState<string[]>([]);
  const [lastDeleteServer, setLastDeleteServer] = useState<string>('');
  const serverReg =
    /^((\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.){3}(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])?$/;

  const [editableKeys, setEditableRowKeys] = useState<React.Key[]>(() =>
    dbConfigData.map((item) => item.id),
  );
  const formatOptions = (data: string[]) =>
    data?.map((item) => ({ label: item, value: item }));
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
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.ItStartsWithALetter',
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
          id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.ZoneNameAlreadyOccupied',
          defaultMessage: 'Zone 名称已被占用',
        }),
      ),
    );
  };

  const columns: ProColumns<API.DBConfig>[] = [
    {
      title: (
        <>
          {intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.ZoneName',
            defaultMessage: 'Zone 名称',
          })}

          <Tooltip
            title={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.AZoneThatRepresentsA',
              defaultMessage:
                '可用区，表示集群内具有相似硬件可用性的一组节点，通常为同一个机架、机房或地域。',
            })}
          >
            <QuestionCircleOutlined className="ml-10" />
          </Tooltip>
        </>
      ),

      dataIndex: 'name',
      width: 224,
      formItemProps: {
        rules: [
          {
            required: true,
            whitespace: false,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.ThisItemIsRequired',
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
            id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.ObserverNodes',
            defaultMessage: 'OBServer 节点',
          })}

          <Tooltip
            title={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.TheNodeWhereDatabaseService',
              defaultMessage:
                '数据库服务（OBServer）所在节点，包含 SQL 引擎、事务引擎和存储引擎，并服务多个数据分区。',
            })}
          >
            <QuestionCircleOutlined className="ml-10" />
          </Tooltip>
        </>
      ),

      dataIndex: 'servers',
      formItemProps: {
        rules: [
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.ThisItemIsRequired',
              defaultMessage: '此项是必填项',
            }),
          },
          {
            validator: (_: any, value: string[]) => {
              return serversValidator(_, value, 'OBServer');
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
    {
      title: (
        <>
          {intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.RootserverNodes',
            defaultMessage: 'RootServer 节点',
          })}

          <Tooltip
            title={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.TheNodeWhereTheMaster',
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
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.ThisOptionIsRequired',
              defaultMessage: '此项是必选项',
            }),
          },
          {
            pattern: serverReg,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.SelectTheCorrectRootserverNode',
              defaultMessage: '请选择正确的 RootServer 节点',
            }),
          },
        ],
      },
      width: 224,
      renderFormItem: (_: any, { isEditable, record }: any) => {
        // rootservice options are items entered by the OBServer
        const options = record?.servers ? formatOptions(record?.servers) : [];
        return isEditable ? (
          <Select
            options={options}
            placeholder={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.PleaseSelect',
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
  ];

  const handleDelete = (id: string) => {
    setDBConfigData(dbConfigData.filter((item) => item.id !== id));
  };

  useEffect(() => {
    const allServers = getAllServers(dbConfigData);
    const allZoneServers: any = {};
    dbConfigData.forEach((item) => {
      allZoneServers[`${item.id}`] = item.servers || [];
    });
    setAllOBServer(allServers);
    setAllZoneOBServer(allZoneServers);
  }, [dbConfigData, lastDeleteServer]);

  return (
    <div className={styles.nodeConfigContainer}>
      <p className={styles.titleText} style={{ marginBottom: 4 }}>
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.DatabaseNodeConfiguration',
          defaultMessage: '数据库节点配置',
        })}
      </p>
      <EditableProTable<API.DBConfig>
        bordered={false}
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
            name: `zone${ocpNameIndex}`,
          }),
          onClick: () => setOcpNameIndex(ocpNameIndex + 1),
          creatorButtonText: intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.AddZone',
            defaultMessage: '新增 Zone',
          }),
          style: { margin: '0 0 10px 0' },
        }}
        editable={{
          type: 'multiple',
          form: editableForm,
          editableKeys,
          actionRender: (row) => {
            if (dbConfigData?.length === 1) {
              return (
                <Tooltip
                  title={intl.formatMessage({
                    id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.KeepAtLeastOneZone',
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
                  id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.AreYouSureYouWant',
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
            } else if (editorServers?.length === 1 && serversErrors.length) {
              tableFormRef?.current?.setFields([
                {
                  name: [editableItem.id, 'rootservice'],
                  errors: [
                    intl.formatMessage({
                      id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.SelectTheCorrectRootserverNode',
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
    </div>
  );
}
