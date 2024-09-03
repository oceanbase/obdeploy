import { intl } from '@/utils/intl';
import { ProForm, ProCard } from '@ant-design/pro-components';
import {
  Input,
  Space,
  Tooltip,
  Button,
  message,
  Modal,
} from 'antd';
import { QuestionCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import { useModel } from 'umi';

import * as Metadb from '@/services/ocp_installer_backend/Metadb';
import { encrypt } from '@/utils/encrypt';
import CustomFooter from '../CustomFooter';
import InputPort from '../InputPort';
import ExitBtn from '../ExitBtn';
import styles from './index.less';
const InputWidthStyle = { width: 328 };

type FormValues = {
  metadb: {
    host: string;
    port: number;
    user: string;
    password: string;
  };
};

export default function ConnectConfig({ setCurrent, current }: API.StepProp) {
  const { ocpConfigData, setOcpConfigData, setErrorVisible, setErrorsList } =
    useModel('global');
  const { components = {} } = ocpConfigData;
  const { ocpserver = {}, oceanbase = {} } = components;
  const { metadb = {} } = ocpserver;
  const cluster_name = oceanbase?.appname;
  const { host, port, user, password } = metadb;
  const [form] = ProForm.useForm();
  const setData = (dataSource: FormValues) => {
    let newOcpserver = {
      ...ocpserver,
      ...dataSource,
    };
    setOcpConfigData({
      ...ocpConfigData,
      components: {
        ...components,
        ocpserver: newOcpserver,
      },
    });
  };
  // 通过 connection 方式创建一个 metadb 连接
  const { run: createMetadbConnection, loading } = useRequest(
    Metadb.createMetadbConnection,
    {
      manual: true,
      onError: ({ data }: any) => {
        const errorInfo =
          data?.detail?.msg || (data?.detail[0] && data?.detail[0]?.msg);
        Modal.error({
          title: intl.formatMessage({
            id: 'OBD.component.ConnectConfig.MetadbConnectionFailedPleaseCheck',
            defaultMessage: 'MetaDB 连接失败，请检查连接配置',
          }),
          icon: <CloseCircleOutlined />,
          content: errorInfo,
          okText: intl.formatMessage({
            id: 'OBD.component.ConnectConfig.IKnow',
            defaultMessage: '我知道了',
          }),
        });
      },
    },
  );

  const nextStep = () => {
    form
      .validateFields()
      .then(async (values) => {
        const { host, port, user, password } = values.metadb;
        const { data: publicKey } = await getPublicKey();
        createMetadbConnection(
          { sys: true },
          {
            host,
            port,
            user,
            password: encrypt(password, publicKey) || password,
            cluster_name,
          },
        ).then(() => {
          setData(values);
          setCurrent(current + 1);
          setErrorVisible(false);
          setErrorsList([]);
          window.scrollTo(0, 0);
        });
      })
      .catch(({ errorFields }) => {
        const errorName = errorFields?.[0].name;
        form.scrollToField(errorName);
        message.destroy();
      });
  };
  const prevStep = () => {
    setCurrent(current - 1);
  };
  const initialValues: FormValues = {
    metadb: {
      host: host || undefined,
      port: port || 2883,
      user: user || 'root@sys',
      password: password || undefined,
    },
  };
  return (
    <Space style={{ width: '100%' }} direction="vertical" size="middle">
      <ProCard>
        <p className={styles.titleText}>
          {intl.formatMessage({
            id: 'OBD.component.ConnectConfig.ConnectionInformation',
            defaultMessage: '连接信息',
          })}
        </p>
        <ProForm
          form={form}
          submitter={false}
          validateTrigger={['onBlur', 'onChange']}
          initialValues={initialValues}
        >
          <ProForm.Item
            name={['metadb', 'host']}
            label={intl.formatMessage({
              id: 'OBD.component.ConnectConfig.MetadbAccessAddress',
              defaultMessage: 'MetaDB 访问地址',
            })}
            style={InputWidthStyle}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.component.ConnectConfig.PleaseEnterMetadbAccessAddress',
                  defaultMessage: '请输入 MetaDB 访问地址',
                }),
              },
              {
                pattern: /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/,
                message: intl.formatMessage({
                  id: 'OBD.component.ConnectConfig.TheMetadbAccessAddressFormat',
                  defaultMessage: 'MetaDB 访问地址格式不正确',
                }),
              },
            ]}
          >
            <Input
              placeholder={intl.formatMessage({
                id: 'OBD.component.ConnectConfig.PleaseEnterMetadbAccessAddress',
                defaultMessage: '请输入 MetaDB 访问地址',
              })}
            />
          </ProForm.Item>
          <InputPort
            name={['metadb', 'port']}
            label={intl.formatMessage({
              id: 'OBD.component.ConnectConfig.MetadbAccessPort',
              defaultMessage: 'MetaDB 访问端口',
            })}
            message={intl.formatMessage({
              id: 'OBD.component.ConnectConfig.EnterTheMetadbAccessPort',
              defaultMessage: '请输入 MetaDB 访问端口',
            })}
            fieldProps={{ style: InputWidthStyle }}
          />

          <ProForm.Item
            name={['metadb', 'user']}
            label={intl.formatMessage({
              id: 'OBD.component.ConnectConfig.MetadbAccessAccount',
              defaultMessage: 'MetaDB 访问账号',
            })}
            style={InputWidthStyle}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.component.ConnectConfig.EnterAMetadbAccessAccount',
                  defaultMessage: '请输入 MetaDB 访问账号',
                }),
              },
            ]}
          >
            <Input
              placeholder={intl.formatMessage({
                id: 'OBD.component.ConnectConfig.PleaseEnter',
                defaultMessage: '请输入',
              })}
            />
          </ProForm.Item>
          <ProForm.Item
            label={
              <>
                {intl.formatMessage({
                  id: 'OBD.component.ConnectConfig.MetadbAccessPassword',
                  defaultMessage: 'MetaDB 访问密码',
                })}

                <Tooltip
                  title={intl.formatMessage({
                    id: 'OBD.component.ConnectConfig.OcpPlatformAdministratorAccountPassword',
                    defaultMessage: 'OCP 平台管理员账号密码',
                  })}
                >
                  <QuestionCircleOutlined className="ml-10" />
                </Tooltip>
              </>
            }
            name={['metadb', 'password']}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.component.ConnectConfig.EnterMetadbAccessPassword',
                  defaultMessage: '请输入 MetaDB 访问密码',
                }),
              },
            ]}
            style={InputWidthStyle}
          >
            <Input.Password
              placeholder={intl.formatMessage({
                id: 'OBD.component.ConnectConfig.PleaseEnter',
                defaultMessage: '请输入',
              })}
            />
          </ProForm.Item>
        </ProForm>
      </ProCard>
      <CustomFooter>
        <ExitBtn />
        <Button onClick={prevStep}>
          {intl.formatMessage({
            id: 'OBD.component.ConnectConfig.PreviousStep',
            defaultMessage: '上一步',
          })}
        </Button>
        <Button type="primary" loading={loading} onClick={nextStep}>
          {intl.formatMessage({
            id: 'OBD.component.ConnectConfig.NextStep',
            defaultMessage: '下一步',
          })}
        </Button>
      </CustomFooter>
    </Space>
  );
}
