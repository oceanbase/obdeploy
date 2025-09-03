import { tenantsChangeLog } from '@/services/component-change/componentChange';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { clusterNameReg, getErrorInfo, IPValidator } from '@/utils';
import { encrypt } from '@/utils/encrypt';
import { requestPipeline } from '@/utils/useRequest';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { useModel } from '@umijs/max';
import { useRequest } from 'ahooks';
import {
  Alert,
  Button,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Radio,
  Result,
  Select,
  Space,
  Steps,
  theme,
  Tooltip,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';
import ContentWithQuestion from '../ContentWithQuestion';
import InstallProcessComp from '../InstallProcessComp';

import { ProCard } from '@ant-design/pro-components';
import { getLocale } from '@umijs/max';
import EnStyles from '../InstallProcessComp/indexEn.less';
import ZhStyles from '../InstallProcessComp/indexZh.less';
const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

const { Text } = Typography;

import { insertPwd } from '@/utils/helper';
import { intl } from '@/utils/intl';
import { isGte4_2_5 } from '@/utils/package';
import { ProForm } from '@ant-design/pro-components';
import NP from 'number-precision';
import CustomPasswordInput from '../CustomPasswordInput';
import { MsgInfoType } from '../OCPConfigNew';
export enum ResultType {
  OBInstall = 'obInstall',
  CompInstall = 'componentInstall',
  TenantInstall = 'tenantInstall',
}

interface CreatTenantProps {
  type: ResultType;
  obConnectInfo: string;
  open: boolean;
  setOpen: (open: boolean) => void;
}

let timerProgress: NodeJS.Timer;

const mysqlCharset = [
  {
    value: 'utf8mb4',
    label: 'utf8mb4',
  },
  {
    value: 'utf16',
    label: 'utf16',
  },
  {
    value: 'gbk',
    label: 'gbk',
  },
  {
    value: 'gb18030',
    label: 'gb18030',
  },
  {
    value: 'binary',
    label: 'binary',
  },
];

const oracleCharset = [
  {
    value: 'utf8',
    label: 'utf8',
  },

  {
    value: 'gbk',
    label: 'gbk',
  },
];

const timeZoneList = [
  {
    value: '-12:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.AFB8B1F2',
      defaultMessage: '(GMT-12:00)日界线西',
    }),
  },
  {
    value: '-11:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.512347D5',
      defaultMessage: '(GMT-11:00)萨摩亚群岛',
    }),
  },
  {
    value: '-10:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.4A592AD8',
      defaultMessage: '(GMT-10:00)夏威夷',
    }),
  },
  {
    value: '-09:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.64BBF72A',
      defaultMessage: '(GMT-09:00)阿拉斯加',
    }),
  },
  {
    value: '-08:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.12DDA775',
      defaultMessage: '(GMT-08:00)太平洋时间(美国和加拿大)',
    }),
  },
  {
    value: '-07:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.A526C472',
      defaultMessage: '(GMT-07:00)亚利桑那',
    }),
  },

  {
    value: '-06:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.6DE9D158',
      defaultMessage: '(GMT-06:00)中部时间(美国和加拿大)',
    }),
  },
  {
    value: '-05:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.F751AECB',
      defaultMessage: '(GMT-05:00)东部时间(美国和加拿大)',
    }),
  },
  {
    value: '-04:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.4F58EE7C',
      defaultMessage: '(GMT-04:00)大西洋时间(美国和加拿大)',
    }),
  },
  {
    value: '-03:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.5F2A703A',
      defaultMessage: '(GMT-03:00)巴西利亚',
    }),
  },
  {
    value: '-02:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.AD3B3CED',
      defaultMessage: '(GMT-02:00)中大西洋',
    }),
  },
  {
    value: '-01:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.89B06ADD',
      defaultMessage: '(GMT-01:00)亚速尔群岛',
    }),
  },
  {
    value: '+0:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.D1B40C56',
      defaultMessage: '(GMT)格林威治标准时间',
    }),
  },

  {
    value: '+01:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.D28BE5DC',
      defaultMessage: '(GMT+01:00)萨拉热窝',
    }),
  },
  {
    value: '+02:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.6492A6B7',
      defaultMessage: '(GMT+02:00)开罗',
    }),
  },
  {
    value: '+03:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.F8B62B34',
      defaultMessage: '(GMT+03:00)莫斯科',
    }),
  },
  {
    value: '+04:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.183E598E',
      defaultMessage: '(GMT+04:00)阿布扎比',
    }),
  },
  {
    value: '+05:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.1A3399C4',
      defaultMessage: '(GTM+5:00)伊斯兰堡',
    }),
  },

  {
    value: '+06:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.BA1E4672',
      defaultMessage: '(GTM+6:00)达卡',
    }),
  },

  {
    value: '+07:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.2D49A949',
      defaultMessage: '(GMT+07:00)曼谷、河内',
    }),
  },
  {
    value: '+08:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.F0DC8CC9',
      defaultMessage: '(GMT+08:00)中国标准时间',
    }),
  },

  {
    value: '+09:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.625DB17B',
      defaultMessage: '(GMT+09:00)首尔',
    }),
  },
  {
    value: '+10:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.81E055EC',
      defaultMessage: '(GMT+10:00)关岛',
    }),
  },
  {
    value: '+11:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.9909B89C',
      defaultMessage: '(GMT+11:00)所罗门群岛',
    }),
  },
  {
    value: '+12:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.23DB617B',
      defaultMessage: '(GMT+12:00)斐济',
    }),
  },
  {
    value: '+13:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.2AA58012',
      defaultMessage: '(GMT+13:00)努库阿勒法',
    }),
  },
  {
    value: '+14:00',
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.93E1FC39',
      defaultMessage: '(GMT+14:00)基里巴斯',
    }),
  },
];

const modeList = [
  {
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.843EF3D8',
      defaultMessage: '最大占用',
    }),
    value: 'max',
  },
  {
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.712F99F5',
      defaultMessage: '最小可用',
    }),
    value: 'min',
  },
  {
    label: intl.formatMessage({
      id: 'OBD.Obdeploy.CreateTenantDrawer.E6153D70',
      defaultMessage: '自定义',
    }),
    value: 'diy',
  },
];

const COLLATE_CONFIG = {
  utf8: {
    collateList: [
      'utf8mb4_general_ci',
      'utf8mb4_bin',
      'utf8mb4_unicode_ci',
      'utf8mb4_unicode_520_ci',
      'utf8mb4_croatian_ci',
      'utf8mb4_czech_ci',
      'utf8mb4_0900_ai_ci',
    ],
  },
  utf16: { collateList: ['utf16_general_ci', 'utf16_unicode_ci', 'utf16_bin'] },
  gbk: { collateList: ['gbk_chinese_ci', 'gbk_bin'] },
  gb18030: { collateList: ['gb18030_chinese_ci', 'gb18030_bin'] },
  binary: { collateList: ['binary'] },
};

export default function CreatTenantDrawer({
  open,
  setOpen,
  obConnectInfo,
  obConnectUrl,
  setObConnectInfo,
}: CreatTenantProps) {
  const [form] = Form.useForm();
  const { token } = theme.useToken();
  const [current, setCurrent] = useState(0);
  const {
    setCurrentStep,
    configData,
    setErrorVisible,
    setErrorsList,
    errorsList,
    scenarioParam,
  } = useModel('global');

  const modeValue = ProForm.useWatch(['mode'], form);

  const [logData, setLogData] = useState<API.InstallLog>({});
  const [installStatus, setInstallStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [currentPage, setCurrentPage] = useState(true);
  const [statusData, setStatusData] = useState<API.TaskInfo>({});
  const [paramsData, setParamsData] = useState<API.TaskInfo>({});
  const [taskId, setTaskId] = useState<API.TaskInfo>('');

  const [tenantPwd, settenantPwd] = useState<string>('');

  const [tenantPwdMsgInfo, settenantPwdMsgInfo] = useState<MsgInfoType>();

  const name = configData?.components?.oceanbase?.appname;
  const version = configData?.components?.oceanbase?.version;

  const { data: getUnitResource, run: getResource } = useRequest(
    OCP.getUnitResource,
    {
      manual: true,
      defaultParams: [{ name }],
    },
  );

  const unitResourceData = getUnitResource?.data || {};
  const { cpu_capacity, log_disk_capacity, mem_capacity } = unitResourceData;

  const { data: getScenarioData, run: getScenario } = useRequest(
    OCP.getScenario,
    {
      manual: true,
      defaultParams: [{ name }],
    },
  );

  const scenarioData = getScenarioData?.data?.items || [];
  const optimizeList = scenarioData?.map((item) => ({
    ...item,
    value: item.value,
    label: item.type,
  }));

  const extractSize = (capacity, type) => {
    return Number(capacity?.[type]?.split('G')[0]) ?? 0;
  };

  const { run: handleInstallLog } = useRequest(tenantsChangeLog, {
    manual: true,
    onSuccess: ({ success, data }) => {
      if (success && installStatus === 'RUNNING') {
        setLogData(data || {});
        setTimeout(() => {
          handleInstallLog({ name, taskId });
        }, 1000);
      }
    },
    onError: (e) => {
      if (installStatus === 'RUNNING') {
        setTimeout(() => {
          handleInstallLog({ name, taskId });
        }, 1000);
      }
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const { run: failedInstallLog } = useRequest(tenantsChangeLog, {
    manual: true,
    onSuccess: ({ success, data }) => {
      setLogData(data || {});
    },
  });

  const { run: fetchTenantStatus } = useRequest(OCP.getTenantsTaskStatus, {
    manual: true,
    onSuccess: ({ success, data }: API.OBResponseTaskInfo_) => {
      if (success) {
        setStatusData(data || {});
        clearInterval(timerProgress);
        setInstallStatus(data?.result);
        if (data?.result === 'FAILED') {
          failedInstallLog({ name, taskId, detail_log: true }, {});
        }
        if (data?.status !== 'RUNNING') {
          setCurrentPage(false);
          setTimeout(() => {
            setCurrentStep(6);
            setErrorVisible(false);
            setErrorsList([]);
          }, 2000);

          if (open) {
            const colonIndex = obConnectUrl.indexOf(':');
            const ip = obConnectUrl.slice(0, colonIndex);
            const port = obConnectUrl.slice(colonIndex + 1);
            if (
              paramsData?.mode === 'oracle' &&
              data?.result === 'SUCCESSFUL'
            ) {
              const info = `obclient -h${ip} -uSYS@${paramsData?.tenant_name} -P${port}`;
              setObConnectInfo(insertPwd(info, paramsData?.password));
            } else if (
              paramsData?.mode === 'mysql' &&
              data?.result === 'SUCCESSFUL'
            ) {
              setObConnectInfo(insertPwd(data?.message, paramsData?.password));
            }
          }
        } else {
          setTimeout(() => {
            fetchTenantStatus({ name, taskId });
          }, 1000);
        }
        const newProgress = NP.divide(data?.finished, data?.total).toFixed(2);
        setProgress(newProgress);
        let step = NP.minus(newProgress, progress);
        let stepNum = 1;
        timerProgress = setInterval(() => {
          const currentProgressNumber = NP.plus(
            progress,
            NP.times(NP.divide(step, 100), stepNum),
          );

          if (currentProgressNumber >= 1) {
            clearInterval(timerProgress);
          } else {
            stepNum += 1;
            setShowProgress(currentProgressNumber);
          }
        }, 10);
      }
    },
    onError: (e: any) => {
      if (currentPage && !requestPipeline.processExit) {
        setTimeout(() => {
          fetchTenantStatus({ name, taskId });
        }, 1000);
      }
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const { run: createTenants, loading } = useRequest(OCP.createTenants, {
    manual: true,
    onSuccess: (res) => {
      setCurrent(current + 1);
      const taskId = res?.data?.id;
      setTaskId(taskId);
      handleInstallLog({ name, taskId });
      fetchTenantStatus({ name, taskId });
      setInstallStatus('RUNNING');
    },
  });

  const handleExit = () => {
    setCurrent(0);
    setOpen(false);
    form.resetFields();
    settenantPwd('');
  };

  const capacityMap = {
    CPU: cpu_capacity,
    内存: mem_capacity,
    日志盘: log_disk_capacity,
  };

  const validateCapacity = (rule, value, callback, type) => {
    const capacity = capacityMap[type];

    const minValue =
      type === 'CPU' ? capacity.min : extractSize(capacity, 'min');
    const maxValue =
      type === 'CPU' ? capacity.max : extractSize(capacity, 'max');

    if (value < minValue) {
      callback(
        new Error(
          intl.formatMessage(
            {
              id: 'OBD.Obdeploy.CreateTenantDrawer.7C6FEDEE',
              defaultMessage: '${type}值不能小于最小值',
            },
            { type: type },
          ),
        ),
      );
    } else if (value > maxValue) {
      callback(
        new Error(
          intl.formatMessage(
            {
              id: 'OBD.Obdeploy.CreateTenantDrawer.2315DA6C',
              defaultMessage: '${type}值不能超过最大值',
            },
            { type: type },
          ),
        ),
      );
    } else {
      callback();
    }
  };

  const settingsV = ProForm.useWatch(['settings'], form);

  useEffect(() => {
    if (settingsV === 'min') {
      form.setFieldsValue({
        cpu_size: cpu_capacity?.min,
        memory_size: extractSize(mem_capacity, 'min'),
        log_disk_size: extractSize(log_disk_capacity, 'min'),
      });
    } else if (settingsV === 'max') {
      form.setFieldsValue({
        cpu_size: cpu_capacity?.max,
        memory_size: extractSize(mem_capacity, 'max'),
        log_disk_size: extractSize(log_disk_capacity, 'max'),
      });
    }
  }, [settingsV, unitResourceData]);

  useEffect(() => {
    if (modeValue === 'mysql') {
      form.setFieldsValue({
        charset: 'utf8mb4',
      });
    } else {
      form.setFieldsValue({
        charset: 'utf8',
      });
    }
  }, [modeValue, open]);

  useEffect(() => {
    if (open === true) {
      getResource({ name });
      getScenario({ name });
    }

    form.setFieldsValue({
      settings: 'max',
      lower_case_table_names: 1,
      ip: 'diy',
      time_zone: '+08:00',
      mode: 'mysql',
      optimize: scenarioParam?.value || 'complex_oltp',
    });
  }, [open]);

  const tenantPwdChange = (password: string) => {
    form.setFieldValue(['password'], password);
    form.validateFields([['password']]);
    settenantPwd(password);
  };

  const basicFrom = () => {
    return (
      <Form
        name="basic"
        autoComplete="off"
        form={form}
        layout="vertical"
        requiredMark={false}
      >
        <Alert
          style={{ margin: '24px 0' }}
          message={intl.formatMessage({
            id: 'OBD.Obdeploy.CreateTenantDrawer.56D55DA6',
            defaultMessage:
              'sys 租户仅用来管理集群，如将其作为业务租户使用，可能会引起系统运行异常。',
          })}
          type="warning"
          showIcon
        />

        <Form.Item
          label={intl.formatMessage({
            id: 'OBD.Obdeploy.CreateTenantDrawer.CD7DC288',
            defaultMessage: '租户名称',
          })}
          name="tenant_name"
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.Obdeploy.CreateTenantDrawer.87DC2D5C',
                defaultMessage: '请输入租户名称',
              }),
            },
            {
              pattern: clusterNameReg,
              message: intl.formatMessage({
                id: 'OBD.Obdeploy.CreateTenantDrawer.E9FE307C',
                defaultMessage: '租户名称不符合规范',
              }),
              validateTrigger: 'onChange',
            },
          ]}
          extra={
            <>
              <div>
                {intl.formatMessage({
                  id: 'OBD.Obdeploy.CreateTenantDrawer.4A4314AB',
                  defaultMessage: '· 仅支持字母开头；字母或数字结尾',
                })}
              </div>
              <div>
                {intl.formatMessage({
                  id: 'OBD.Obdeploy.CreateTenantDrawer.34085B9B',
                  defaultMessage: '· 支持 2 - 32 个字符',
                })}
              </div>
              <div>
                {intl.formatMessage({
                  id: 'OBD.Obdeploy.CreateTenantDrawer.373FF04B',
                  defaultMessage: '· 特殊符号仅支持下划线',
                })}
              </div>
            </>
          }
        >
          <Input
            placeholder={intl.formatMessage({
              id: 'OBD.Obdeploy.CreateTenantDrawer.F7A2CEF3',
              defaultMessage: '请输入',
            })}
          />
        </Form.Item>

        <Form.Item
          label={intl.formatMessage({
            id: 'OBD.Obdeploy.CreateTenantDrawer.8A350062',
            defaultMessage: '租户模式',
          })}
          name="mode"
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.Obdeploy.CreateTenantDrawer.0583ED0D',
                defaultMessage: '请输入租户模式',
              }),
            },
          ]}
        >
          <Select
            style={{ width: 300 }}
            options={[
              { value: 'mysql', label: 'MySQL' },
              {
                value: 'oracle',
                label: 'Oracle',
                disabled:
                  configData?.components?.oceanbase?.component ===
                  'oceanbase-ce',
              },
            ]}
            placeholder={intl.formatMessage({
              id: 'OBD.Obdeploy.CreateTenantDrawer.6551A76B',
              defaultMessage: '请选择',
            })}
          />
        </Form.Item>
        <Form.Item noStyle shouldUpdate>
          {() => {
            return (
              <CustomPasswordInput
                msgInfo={tenantPwdMsgInfo}
                setMsgInfo={settenantPwdMsgInfo}
                form={form}
                onChange={tenantPwdChange}
                useFor="ob"
                value={tenantPwd}
                name={['password']}
                label={intl.formatMessage({
                  id: 'OBD.Obdeploy.CreateTenantDrawer.4B27F284',
                  defaultMessage: '租户 root 密码',
                })}
                innerInputStyle={{ width: 408 }}
                showTip={false}
                placeholder={intl.formatMessage({
                  id: 'OBD.Obdeploy.CreateTenantDrawer.2C2FA075',
                  defaultMessage: '请输入',
                })}
              />
            );
          }}
        </Form.Item>
        <Form.Item
          label={intl.formatMessage({
            id: 'OBD.Obdeploy.CreateTenantDrawer.D59B3A43',
            defaultMessage: '模式配置',
          })}
          name="settings"
        >
          <Radio.Group>
            {modeList.map((item) => {
              return (
                <Radio.Button value={item.value} key={item.value}>
                  {item.label}
                </Radio.Button>
              );
            })}
          </Radio.Group>
        </Form.Item>
        <Form.Item noStyle shouldUpdate>
          {() => {
            const setValueDisabled = settingsV === 'min' || settingsV === 'max';
            return (
              <Space size={24}>
                <Form.Item
                  label="CPU"
                  name="cpu_size"
                  rules={[
                    {
                      validator: (_, value, callback) =>
                        validateCapacity(_, value, callback, 'CPU'),
                    },
                  ]}
                  extra={
                    !setValueDisabled &&
                    intl.formatMessage(
                      {
                        id: 'OBD.Obdeploy.CreateTenantDrawer.46AF3040',
                        defaultMessage:
                          '可配置范围 [${cpu_capacity?.min}，${cpu_capacity?.max}]',
                      },
                      {
                        cpu_capacityMin: cpu_capacity?.min,
                        cpu_capacityMax: cpu_capacity?.max,
                      },
                    )
                  }
                >
                  <InputNumber
                    addonAfter="vCPUs"
                    style={{ color: '#c1cbe0' }}
                    disabled={setValueDisabled}
                    min={cpu_capacity?.min}
                    max={cpu_capacity?.max}
                  />
                </Form.Item>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.D5F41A43',
                    defaultMessage: '内存',
                  })}
                  name="memory_size"
                  rules={[
                    {
                      validator: (rule, value, callback) =>
                        validateCapacity(
                          rule,
                          value,
                          callback,
                          intl.formatMessage({
                            id: 'OBD.Obdeploy.CreateTenantDrawer.997628B6',
                            defaultMessage: '内存',
                          }),
                        ),
                    },
                  ]}
                  extra={
                    !setValueDisabled &&
                    intl.formatMessage(
                      {
                        id: 'OBD.Obdeploy.CreateTenantDrawer.7DB285FB',
                        defaultMessage:
                          "可配置范围 [${extractSize(mem_capacity, 'min')}，${extractSize(mem_capacity, 'max')}]",
                      },
                      {
                        CallExpression0: extractSize(mem_capacity, 'min'),
                        CallExpression1: extractSize(mem_capacity, 'max'),
                      },
                    )
                  }
                >
                  <InputNumber
                    addonAfter="GiB"
                    style={{ color: '#c1cbe0' }}
                    disabled={setValueDisabled}
                    min={extractSize(mem_capacity, 'min')}
                    max={extractSize(mem_capacity, 'max')}
                  />
                </Form.Item>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.F88F3980',
                    defaultMessage: '日志盘',
                  })}
                  name="log_disk_size"
                  rules={[
                    {
                      validator: (rule, value, callback) =>
                        validateCapacity(
                          rule,
                          value,
                          callback,
                          intl.formatMessage({
                            id: 'OBD.Obdeploy.CreateTenantDrawer.267AD133',
                            defaultMessage: '日志盘',
                          }),
                        ),
                    },
                  ]}
                  extra={
                    !setValueDisabled &&
                    intl.formatMessage(
                      {
                        id: 'OBD.Obdeploy.CreateTenantDrawer.6ACF27D3',
                        defaultMessage:
                          "可配置范围 [${extractSize(log_disk_capacity, 'min')}，${extractSize(log_disk_capacity, 'max')}]",
                      },
                      {
                        CallExpression0: extractSize(log_disk_capacity, 'min'),
                        CallExpression1: extractSize(log_disk_capacity, 'max'),
                      },
                    )
                  }
                >
                  <InputNumber
                    style={{ color: '#c1cbe0' }}
                    addonAfter="GiB"
                    disabled={setValueDisabled}
                    min={extractSize(log_disk_capacity, 'min')}
                    max={extractSize(log_disk_capacity, 'max')}
                  />
                </Form.Item>
              </Space>
            );
          }}
        </Form.Item>
        {/* 小于425版本的不展示此配置项 */}
        {isGte4_2_5(version) && optimizeList.length > 0 && (
          <Form.Item noStyle shouldUpdate>
            {() => {
              const optimizeValue = form.getFieldValue('optimize');
              const dec = optimizeList?.find(
                (item) => item.value === optimizeValue,
              )?.desc;
              return (
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.76BFF66C',
                    defaultMessage: '业务负载类型',
                  })}
                  name="optimize"
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.Obdeploy.CreateTenantDrawer.D310A07A',
                        defaultMessage: '请输入业务负载类型',
                      }),
                    },
                  ]}
                  extra={
                    <Tooltip title={dec}>
                      <p
                        style={{
                          overflow: 'hidden',
                          whiteSpace: 'nowrap',
                          textOverflow: 'ellipsis',
                          wordBreak: 'keep-all',
                          width: '550px',
                        }}
                      >
                        {dec}
                      </p>
                    </Tooltip>
                  }
                >
                  <Select style={{ width: 300 }} options={optimizeList} />
                </Form.Item>
              );
            }}
          </Form.Item>
        )}

        <Form.Item noStyle shouldUpdate>
          {() => {
            const ipV = form.getFieldValue('ip');
            const charsetValue = form.getFieldValue('charset');
            const real = charsetValue === 'utf8mb4' ? 'utf8' : charsetValue;
            const getCharsetList = COLLATE_CONFIG[real]?.collateList || [];

            return (
              <>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.955306EE',
                    defaultMessage: '字符集',
                  })}
                  name="charset"
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.Obdeploy.CreateTenantDrawer.9A3F36F7',
                        defaultMessage: '请输入字符集',
                      }),
                    },
                  ]}
                >
                  <Select
                    style={{ width: 300 }}
                    options={
                      modeValue !== 'mysql' ? oracleCharset : mysqlCharset
                    }
                    onChange={() => {
                      form.setFieldsValue({
                        collate: undefined,
                      });
                    }}
                  />
                </Form.Item>

                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.955306E3',
                    defaultMessage: '字符序',
                  })}
                  name="collate"
                  initialValue={'utf8mb4_general_ci'}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.Obdeploy.CreateTenantDrawer.9A3F36F0',
                        defaultMessage: '请输入字符序',
                      }),
                    },
                  ]}
                >
                  <Select
                    style={{ width: 300 }}
                    options={getCharsetList?.map((item) => ({
                      label: item,
                      value: item,
                    }))}
                  />
                </Form.Item>

                {modeValue === 'mysql' && (
                  <Form.Item
                    label={
                      <ContentWithQuestion
                        content={intl.formatMessage({
                          id: 'OBD.Obdeploy.CreateTenantDrawer.E139E5CB',
                          defaultMessage: '表名大小写敏感',
                        })}
                        tooltip={{
                          title: (
                            <>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.0D3C1AE5',
                                  defaultMessage:
                                    '·0:表名将按照指定的大小写形式进行存储，并以区分大小写形式进行比较。',
                                })}
                              </div>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.7B721489',
                                  defaultMessage:
                                    '·1:表名将按照小写形式进行存储，并以不区分大小写形式进行比较。',
                                })}
                              </div>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.F00332E1',
                                  defaultMessage:
                                    '·2:表名将按照指定的大小写形式进行存储，并以不区分大小写形式进行比较。',
                                })}
                              </div>
                            </>
                          ),
                        }}
                      />
                    }
                    name="lower_case_table_names"
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.Obdeploy.CreateTenantDrawer.73578D0F',
                          defaultMessage: '请输入表名大小写敏感',
                        }),
                      },
                    ]}
                  >
                    <Select
                      style={{ width: 300 }}
                      options={[
                        {
                          value: 0,
                          label: 0,
                        },
                        {
                          value: 1,
                          label: 1,
                        },
                        {
                          value: 2,
                          label: 2,
                        },
                      ]}
                    />
                  </Form.Item>
                )}

                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.032FB1E4',
                    defaultMessage: '时区',
                  })}
                  name="time_zone"
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.Obdeploy.CreateTenantDrawer.5C5D055C',
                        defaultMessage: '请选择时区',
                      }),
                    },
                  ]}
                >
                  <Select style={{ width: 300 }} options={timeZoneList} />
                </Form.Item>

                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.C864AA2F',
                    defaultMessage: 'IP 地址白名单',
                  })}
                  name="ip"
                  extra={
                    ipV !== 'diy' && (
                      <div style={{ color: '#ffac33', marginLeft: '15%' }}>
                        <ExclamationCircleOutlined />
                        <span style={{ marginLeft: '4px' }}>
                          {intl.formatMessage({
                            id: 'OBD.Obdeploy.CreateTenantDrawer.A9A662D8',
                            defaultMessage: '存在访问安全风险，请谨慎操作',
                          })}
                        </span>
                      </div>
                    )
                  }
                >
                  <Radio.Group
                    options={[
                      {
                        label: intl.formatMessage({
                          id: 'OBD.Obdeploy.CreateTenantDrawer.89BFAD21',
                          defaultMessage: '自定义',
                        }),
                        value: 'diy',
                      },
                      {
                        label: intl.formatMessage({
                          id: 'OBD.Obdeploy.CreateTenantDrawer.2F6A54FE',
                          defaultMessage: '所有 IP 都可访问',
                        }),
                        value: 'all',
                      },
                    ]}
                  />
                </Form.Item>
                {ipV === 'diy' && (
                  <Form.Item
                    label={
                      <>
                        {intl.formatMessage({
                          id: 'OBD.Obdeploy.CreateTenantDrawer.A5BA0E8D',
                          defaultMessage: '自定义 IP',
                        })}

                        <Tooltip
                          title={
                            <div>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.11F62CAB',
                                  defaultMessage:
                                    '在这里指定允许登陆的客户端列表，支持的格式有：',
                                })}
                              </div>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.78852217',
                                  defaultMessage:
                                    'IP地址，示例：127.0.0.10,127.0.0.11',
                                })}
                              </div>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.7B7FD132',
                                  defaultMessage:
                                    '子网/掩码，示例：127.0.0.0/24',
                                })}
                              </div>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.919372C8',
                                  defaultMessage:
                                    '模糊匹配，示例：127.0.0.% 或 127.0.0._',
                                })}
                              </div>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.19E8DCE3',
                                  defaultMessage:
                                    '多种格式混合，示例：127.0.0.10,127.0.0.11,127.0.0.%,127.0.0._,127.0.0.0/24',
                                })}
                              </div>
                              <div>
                                {intl.formatMessage({
                                  id: 'OBD.Obdeploy.CreateTenantDrawer.BF3CDD4E',
                                  defaultMessage:
                                    '特殊说明：% 表示所有客户端都可以连接',
                                })}
                              </div>
                            </div>
                          }
                        >
                          <a style={{ marginLeft: '8px' }}>
                            {intl.formatMessage({
                              id: 'OBD.Obdeploy.CreateTenantDrawer.CC120606',
                              defaultMessage: '查看配置说明',
                            })}
                          </a>
                        </Tooltip>
                      </>
                    }
                    name="ob_tcp_invited_nodes"
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.Obdeploy.CreateTenantDrawer.D0A397E0',
                          defaultMessage: '请输入自定义 IP',
                        }),
                      },
                      {
                        validator: (_: any, value: string[]) => {
                          if (!value || value.length === 0) {
                            return Promise.resolve();
                          }
                          return IPValidator(_, value);
                        },
                      },
                    ]}
                    extra={intl.formatMessage({
                      id: 'OBD.Obdeploy.CreateTenantDrawer.5AB93DB7',
                      defaultMessage: '127.0.0.1 也会同时加到租户白名单中',
                    })}
                  >
                    <Select
                      mode="tags"
                      placeholder={intl.formatMessage({
                        id: 'OBD.Obdeploy.CreateTenantDrawer.222B9E21',
                        defaultMessage:
                          '请输入 IP 地址，多个 IP 地址请以逗号分隔',
                      })}
                      style={{ width: '100%' }}
                      tokenSeparators={[',']}
                    />
                  </Form.Item>
                )}
              </>
            );
          }}
        </Form.Item>
      </Form>
    );
  };

  const steps = [
    {
      title: intl.formatMessage({
        id: 'OBD.Obdeploy.CreateTenantDrawer.B52A2A6E',
        defaultMessage: '配置信息',
      }),
      content: basicFrom(),
    },
    {
      title: intl.formatMessage({
        id: 'OBD.Obdeploy.CreateTenantDrawer.6FCFBF9B',
        defaultMessage: '创建',
      }),
      content: (
        <div>
          {installStatus !== 'RUNNING' && (
            <Result
              style={{ paddingBottom: 8 }}
              icon={
                <img
                  src={
                    installStatus === 'SUCCESSFUL'
                      ? '/assets/successful.png'
                      : '/assets/failed.png'
                  }
                  alt="resultLogo"
                  style={{
                    width: 89,
                    height: 68,
                    position: 'relative',
                    right: '-8px',
                  }}
                />
              }
              title={
                <div style={{ fontSize: '14px', fontWeight: 500 }}>
                  {installStatus === 'SUCCESSFUL'
                    ? intl.formatMessage({
                        id: 'OBD.Obdeploy.CreateTenantDrawer.4BC7690D',
                        defaultMessage: '业务租户创建成功',
                      })
                    : intl.formatMessage({
                        id: 'OBD.Obdeploy.CreateTenantDrawer.6C92D589',
                        defaultMessage: '业务租户创建失败',
                      })}
                </div>
              }
            />
          )}
          <div
            style={
              installStatus !== 'RUNNING' && statusData?.result !== 'FAILED'
                ? {
                    backgroundColor: token.colorFillAlter,
                    padding: '16px 24px',
                  }
                : {}
            }
          >
            {installStatus === 'RUNNING' ? (
              <InstallProcessComp
                logData={logData}
                installStatus={installStatus}
                statusData={statusData}
                showProgress={showProgress}
                progressCoverWidth={182}
                type="tenant"
              />
            ) : installStatus === 'SUCCESSFUL' ? (
              <Descriptions
                column={1}
                title={intl.formatMessage({
                  id: 'OBD.Obdeploy.CreateTenantDrawer.48FFB735',
                  defaultMessage: '基本信息',
                })}
              >
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.ED2D91F7',
                    defaultMessage: '租户名称',
                  })}
                >
                  {paramsData?.tenant_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.3CB81EB9',
                    defaultMessage: '租户模式',
                  })}
                >
                  {paramsData?.mode || '-'}
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.C9129FF1',
                    defaultMessage: '租户 root 密码',
                  })}
                >
                  <Text
                    copyable={{ text: paramsData?.password || '-' }}
                    style={{ color: '#006aff' }}
                  >
                    {paramsData?.password}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.CDA6AF99',
                    defaultMessage: '连接字符串',
                  })}
                >
                  <Text
                    copyable={{
                      text:
                        paramsData?.mode !== 'oracle'
                          ? statusData?.message &&
                            insertPwd(statusData?.message, paramsData?.password)
                          : obConnectInfo,
                    }}
                    style={{ color: '#006aff' }}
                  >
                    {paramsData?.mode !== 'oracle'
                      ? statusData?.message &&
                        insertPwd(statusData?.message, paramsData?.password)
                      : obConnectInfo}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.1BF73436',
                    defaultMessage: '配置模式',
                  })}
                >
                  {modeList?.find((item) => item.value === paramsData?.settings)
                    ?.label || '-'}
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.C6F78769',
                    defaultMessage: '租户规格',
                  })}
                >
                  {`${paramsData?.cpu_size}vCPUs ${paramsData?.memory_size}Gi ${paramsData?.log_disk_size} GiB`}
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.0CFF5A55',
                    defaultMessage: '业务负载类型',
                  })}
                >
                  {paramsData?.optimize || '-'}
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.A17440B8',
                    defaultMessage: '字符集',
                  })}
                >
                  {paramsData?.charset || '-'}
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.A17440B',
                    defaultMessage: '字符序',
                  })}
                >
                  {paramsData?.collate || '-'}
                </Descriptions.Item>
                {paramsData?.mode !== 'oracle' && (
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: 'OBD.Obdeploy.CreateTenantDrawer.51E589C8',
                      defaultMessage: '表名大小写敏感',
                    })}
                  >
                    {paramsData?.lower_case_table_names || 1}
                  </Descriptions.Item>
                )}
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.00463776',
                    defaultMessage: '时区',
                  })}
                >
                  {timeZoneList?.find(
                    (item) => item.value === paramsData?.time_zone,
                  )?.label || '-'}
                </Descriptions.Item>
                <Descriptions.Item
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.CreateTenantDrawer.CED1DCF1',
                    defaultMessage: 'IP 地址白名单',
                  })}
                >
                  {paramsData?.ip !== 'all'
                    ? paramsData?.ob_tcp_invited_nodes?.join(',')
                    : intl.formatMessage({
                        id: 'OBD.Obdeploy.CreateTenantDrawer.5E904F23',
                        defaultMessage: '所有 IP 都可以访问',
                      })}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <ProCard
                title={intl.formatMessage({
                  id: 'OBD.Obdeploy.CreateTenantDrawer.F60C4820',
                  defaultMessage: '部署日志',
                })}
                className={styles.installSubCard}
              >
                <pre className={styles.installLog} id="installLog">
                  {logData?.log}
                  {
                    <div className={styles.shapeContainer}>
                      <div className={styles.shape}></div>
                      <div className={styles.shape}></div>
                      <div className={styles.shape}></div>
                      <div className={styles.shape}></div>
                    </div>
                  }
                </pre>
              </ProCard>
            )}
          </div>
        </div>
      ),
    },
  ];

  const items = steps.map((item) => ({ key: item.title, title: item.title }));

  return (
    <Drawer
      title={intl.formatMessage({
        id: 'OBD.Obdeploy.CreateTenantDrawer.D594E0A5',
        defaultMessage: '创建业务租户',
      })}
      width={610}
      onClose={() => {
        if (current <= 0) handleExit();
      }}
      open={open}
      // 部署中，不要取消按钮
      closable={current > 0 ? false : true}
      destroyOnClose={true}
      footer={
        current < steps.length - 1 ? (
          <Space>
            <Button
              type="primary"
              loading={loading}
              onClick={async () => {
                const { data: publicKey } = await getPublicKey();
                form.validateFields().then((values) => {
                  setParamsData(values);
                  const {
                    ob_tcp_invited_nodes,
                    lower_case_table_names,
                    password,
                    cpu_size,
                    memory_size,
                    log_disk_size,
                  } = values;
                  const invited_nodes =
                    ob_tcp_invited_nodes === undefined
                      ? "'%'"
                      : `'127.0.0.1,${ob_tcp_invited_nodes.join(',')},'`;

                  const params = {
                    ...values,
                    ip: undefined,
                    settings: undefined,
                    cpu_size: undefined,
                    ob_tcp_invited_nodes: undefined,
                    lower_case_table_names: undefined,
                    max_cpu: cpu_size,
                    min_cpu: cpu_size,
                    memory_size: `${memory_size}G`,
                    log_disk_size: `${log_disk_size}G`,
                    variables:
                      modeValue === 'mysql'
                        ? `ob_tcp_invited_nodes=${invited_nodes},lower_case_table_names=${lower_case_table_names}`
                        : `ob_tcp_invited_nodes=${invited_nodes}`,
                    password: encrypt(password, publicKey),
                  };
                  createTenants({ name }, params);
                });
              }}
            >
              {intl.formatMessage({
                id: 'OBD.Obdeploy.CreateTenantDrawer.FCCB14CC',
                defaultMessage: '下一步:创建业务租户',
              })}
            </Button>
            <Button
              onClick={() => {
                setOpen(false);
                form.resetFields();
                settenantPwd('');
              }}
            >
              {intl.formatMessage({
                id: 'OBD.Obdeploy.CreateTenantDrawer.D42DEEBD',
                defaultMessage: '取消',
              })}
            </Button>
          </Space>
        ) : (
          current === 1 &&
          installStatus !== 'RUNNING' && (
            <Button type="primary" onClick={() => handleExit()}>
              {intl.formatMessage({
                id: 'OBD.Obdeploy.CreateTenantDrawer.13978457',
                defaultMessage: '退出',
              })}
            </Button>
          )
        )
      }
    >
      <Steps
        current={current}
        items={items}
        style={{ width: '330px', marginLeft: '22%' }}
      />
      <div>{steps[current].content}</div>
    </Drawer>
  );
}
