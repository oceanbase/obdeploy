import { intl } from '@/utils/intl';
import { ProCard, ProForm, ProFormDigit } from '@ant-design/pro-components';
import { Input, Tooltip, Button, Row, message, Form } from 'antd';
import { FormInstance } from 'antd/lib/form';
import {
  QuestionCircleOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
} from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useModel, getLocale } from 'umi';
import { useUpdateEffect } from 'ahooks';
import { copyText } from '@/utils/helper';
import {
  generateRandomPassword as generatePassword,
  passwordRules,
  siteReg,
} from '@/utils';
import styles from './index.less';
import CustomPasswordInput from '../CustomPasswordInput';
import { ocpAddonAfter } from '@/constant/configuration';
import { MsgInfoType } from './index';

interface ServiceConfigProps {
  form: FormInstance<any>;
  adminMsgInfo: MsgInfoType;
  setAdminMsgInfo: React.Dispatch<
    React.SetStateAction<MsgInfoType | undefined>
  >;
}

const multipleNodesDesc = intl.formatMessage({
  id: 'OBD.component.OCPConfigNew.ServiceConfig.WeRecommendThatYouUse',
  defaultMessage:
    '建议使用负载均衡的地址作为外部访问 OCP 网站的入口, 实现 OCP 服务高可用。如无，您可选择使用 OCP 的节点 IP+端口进行设置，请后续登录 OCP 后进入系统管理->系统参数变更 ocp.site.url（重启生效）',
});
const locale = getLocale();

export default function ServiceConfig({
  form,
  adminMsgInfo,
  setAdminMsgInfo,
}: ServiceConfigProps) {
  const [checkStatus, setCheckStatus] = useState<
    'unchecked' | 'fail' | 'success'
  >('unchecked');
  const { ocpConfigData } = useModel('global');
  const { isSingleOcpNode, deployUser, useRunningUser } =
    useModel('ocpInstallData');
  const { components = {} } = ocpConfigData;
  const { ocpserver = {} } = components;
  const [adminPassword, setAdminPassword] = useState<string>(
    ocpserver.admin_password || '',
  );

  const ip =
    form.getFieldValue(['ocpserver', 'servers']) || ocpserver.servers || [];
  const defaultSiteUrl =
    (ocpserver.ocp_site_url || isSingleOcpNode === true) && ip.length
      ? `http://${ip[0]}:8080`
      : '';
  const [siteUrl, setSiteUrl] = useState<string>(defaultSiteUrl);
  const setPassword = (password: string) => {
    form.setFieldValue(['ocpserver', 'admin_password'], password);
    form.validateFields([['ocpserver', 'admin_password']]);
    setAdminPassword(password);
  };

  const handleCheckSystemUser = () => {
    let site = form.getFieldValue(['ocpserver', 'ocp_site_url']);
    if (siteReg.test(site)) {
      setCheckStatus('success');
    } else {
      setCheckStatus('fail');
    }
  };

  const siteUrlChange = (e: any) => {
    let { value } = e.target;
    setCheckStatus('unchecked');
    setSiteUrl(value);
    form.setFieldValue(['ocpserver', 'ocp_site_url'], value);
  };

  useEffect(() => {
    if (typeof isSingleOcpNode !== 'undefined' && !ocpserver.ocp_site_url) {
      if (isSingleOcpNode && ip.length) {
        let url = `http://${ip[0]}:8080`;
        setSiteUrl(url);
        form.setFieldValue(['ocpserver', 'ocp_site_url'], url);
      } else {
        setSiteUrl('');
        form.setFieldValue(['ocpserver', 'ocp_site_url'], '');
      }
    }
  }, [isSingleOcpNode]);

  useEffect(() => {
    form.setFieldsValue({
      ocpserver: {
        home_path:
          !useRunningUser && deployUser === 'root'
            ? `/${deployUser}`
            : `/home/${deployUser}`,
        log_dir: `/home/${deployUser}/logs`,
        soft_dir: `/home/${deployUser}/software`,
      },
    });
  }, [deployUser]);

  return (
    <ProCard
      title={intl.formatMessage({
        id: 'OBD.component.OCPConfigNew.ServiceConfig.ServiceConfiguration',
        defaultMessage: '服务配置',
      })}
      style={{ width: '100%' }}
    >
      <CustomPasswordInput
        form={form}
        value={adminPassword}
        onChange={setPassword}
        msgInfo={adminMsgInfo}
        setMsgInfo={setAdminMsgInfo}
        name={['ocpserver', 'admin_password']}
        showCopyBtn
        label={
          <>
            {intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ServiceConfig.AdminPassword',
              defaultMessage: 'Admin 密码',
            })}

            <Tooltip
              title={intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ServiceConfig.ThePasswordMustBeTo.2',
                defaultMessage:
                  "密码需满足：长度为 8~32 个字符，支持字母、数字和特殊字符，且至少包含大、小写字母、数字和特殊字符各 2 个，支持的特殊字符为~!@#%^&*_-+=`|(){}[]:;',.?/",
              })}
            >
              <QuestionCircleOutlined className="ml-10" />
            </Tooltip>
          </>
        }
      />

      <ProForm.Item
        name={['ocpserver', 'home_path']}
        style={{ width: 552 }}
        label={intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ServiceConfig.SoftwarePath',
          defaultMessage: '软件路径',
        })}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ServiceConfig.EnterTheSoftwarePath',
              defaultMessage: '请输入软件路径',
            }),
          },
        ]}
      >
        <Input addonAfter={<span>{ocpAddonAfter}</span>} />
      </ProForm.Item>
      <Row>
        <ProForm.Item
          name={['ocpserver', 'log_dir']}
          style={{ width: 343, marginRight: 12 }}
          label={intl.formatMessage({
            id: 'OBD.component.OCPConfigNew.ServiceConfig.LogPath',
            defaultMessage: '日志路径',
          })}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ServiceConfig.EnterALogPath',
                defaultMessage: '请输入日志路径',
              }),
            },
          ]}
        >
          <Input />
        </ProForm.Item>
        <ProForm.Item
          name={['ocpserver', 'soft_dir']}
          style={{ width: 343 }}
          label={intl.formatMessage({
            id: 'OBD.component.OCPConfigNew.ServiceConfig.PackagePath',
            defaultMessage: '软件包路径',
          })}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ServiceConfig.EnterThePackagePath',
                defaultMessage: '请输入软件包路径',
              }),
            },
          ]}
        >
          <Input />
        </ProForm.Item>
      </Row>
      <Row>
        <ProForm.Item
          style={{ width: 343, marginRight: '72px' }}
          name={['ocpserver', 'ocp_site_url']}
          label={
            <>
              ocp.site.url
              <Tooltip
                title={intl.formatMessage({
                  id: 'OBD.component.OCPConfigNew.ServiceConfig.AddressForExternalAccessTo',
                  defaultMessage:
                    '外部访问OCP网站的地址：要求以http/https开始，包含VIP地址/域名/端口的网址，且结尾不含斜杠 /',
                })}
              >
                <QuestionCircleOutlined className="ml-10" />
              </Tooltip>
            </>
          }
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ServiceConfig.EnterOcpSiteUrl',
                defaultMessage: '请输入ocp.site.url',
              }),
            },
          ]}
        >
          <div>
            <div style={{ display: 'flex' }}>
              <div>
                <Input
                  value={siteUrl}
                  onChange={siteUrlChange}
                  onBlur={() => {
                    form.validateFields([['ocpserver', 'ocp_site_url']]);
                  }}
                  // placeholder="例如：http://localhost:8080"
                  style={{ width: 328 }}
                />

                {checkStatus === 'success' && (
                  <div style={{ color: 'rgba(77,204,162,1)', marginTop: 4 }}>
                    <CheckCircleFilled />
                    <span style={{ marginLeft: 5 }}>
                      {intl.formatMessage({
                        id: 'OBD.component.OCPConfigNew.ServiceConfig.TheCurrentVerificationIsSuccessful',
                        defaultMessage: '当前校验成功，请进行下一步',
                      })}
                    </span>
                  </div>
                )}

                {checkStatus === 'fail' && (
                  <div style={{ color: 'rgba(255,75,75,1)', marginTop: 4 }}>
                    <CloseCircleFilled />
                    <span style={{ marginLeft: 5 }}>
                      {intl.formatMessage({
                        id: 'OBD.component.OCPConfigNew.ServiceConfig.TheCurrentVerificationFailedPlease',
                        defaultMessage: '当前校验失败，请重新输入',
                      })}
                    </span>
                  </div>
                )}
              </div>
              <Button
                style={{ marginLeft: 12 }}
                onClick={() => handleCheckSystemUser()}
              >
                {intl.formatMessage({
                  id: 'OBD.component.OCPConfigNew.ServiceConfig.Verification',
                  defaultMessage: '校 验',
                })}
              </Button>
            </div>
            {isSingleOcpNode === false && (
              <p style={{ marginTop: 8 }}>{multipleNodesDesc}</p>
            )}
          </div>
        </ProForm.Item>
        <div style={locale === 'zh-CN' ? {} : { marginLeft: 40 }}>
          <ProFormDigit
            name={['ocpserver', 'port']}
            label={intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ServiceConfig.ServicePort',
              defaultMessage: '服务端口',
            })}
            // fieldProps={{ style: commonStyle }}
            placeholder={intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ServiceConfig.PleaseEnter',
              defaultMessage: '请输入',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.component.OCPConfigNew.ServiceConfig.PleaseEnter',
                  defaultMessage: '请输入',
                }),
              },
            ]}
          />
        </div>
      </Row>
    </ProCard>
  );
}
