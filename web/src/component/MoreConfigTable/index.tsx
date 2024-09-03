import type { RulesDetail } from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import ConfigTable, {
  parameterValidator,
} from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import Parameter from '@/pages/Obdeploy/ClusterConfig/Parameter';
import { serverReg } from '@/utils';
import { getPasswordRules } from '@/utils/helper';
import { intl } from '@/utils/intl';
import { ProForm } from '@ant-design/pro-components';
import { useUpdateEffect } from 'ahooks';
import { Switch } from 'antd';
import type { FormInstance } from 'antd/lib/form';
import { useState } from 'react';

interface MoreConfigTableProps {
  form: FormInstance;
  switchChecked: boolean;
  switchOnChange: (checked: boolean) => void;
  datasource: any;
  loading: boolean;
}

export default function MoreConfigTable({
  form,
  switchChecked,
  switchOnChange,
  loading,
  datasource,
}: MoreConfigTableProps) {
  const proxyPasswordFormValue = ProForm.useWatch(
    ['obproxy', 'parameters', 'obproxy_sys_password', 'params'],
    form,
  );
  const authPasswordFormValue = ProForm.useWatch(
    ['obagent', 'parameters', 'http_basic_auth_password', 'params'],
    form,
  );
  const configserverAddressFormValue = ProForm.useWatch(
    ['obconfigserver', 'parameters', 'vip_address', 'params'],
    form,
  );
  const configserverPortFormValue = ProForm.useWatch(
    ['obconfigserver', 'parameters', 'vip_port', 'params'],
    form,
  );
  const [proxyParameterRules, setProxyParameterRules] = useState<RulesDetail>({
    rules: [() => ({ validator: parameterValidator })],
    targetTable: 'obproxy-ce',
    targetColumn: 'obproxy_sys_password',
  });
  const [authParameterRules, setAuthParameterRules] = useState<RulesDetail>({
    rules: [() => ({ validator: parameterValidator })],
    targetTable: 'obagent',
    targetColumn: 'http_basic_auth_password',
  });
  const [configserverAddressRules, setConfigserverAddressRules] =
    useState<RulesDetail>({
      rules: [],
      targetTable: 'ob-configserver',
      targetColumn: 'vip_address',
    });
  const [configserverPortRules, setConfigserverPortRules] =
    useState<RulesDetail>({
      rules: [],
      targetTable: 'ob-configserver',
      targetColumn: 'vip_port',
    });

  useUpdateEffect(() => {
    if (!proxyPasswordFormValue?.adaptive) {
      setProxyParameterRules({
        rules: getPasswordRules('ob'),
        targetTable: 'obproxy-ce',
        targetColumn: 'obproxy_sys_password',
      });
    } else {
      setProxyParameterRules({
        rules: [() => ({ validator: parameterValidator })],
        targetTable: 'obproxy-ce',
        targetColumn: 'obproxy_sys_password',
      });
    }
  }, [proxyPasswordFormValue]);
  useUpdateEffect(() => {
    if (!authPasswordFormValue?.adaptive) {
      setAuthParameterRules({
        rules: getPasswordRules('ocp'),
        targetTable: 'obagent',
        targetColumn: 'http_basic_auth_password',
      });
    } else {
      setAuthParameterRules({
        rules: [() => ({ validator: parameterValidator })],
        targetTable: 'obagent',
        targetColumn: 'http_basic_auth_password',
      });
    }
  }, [authPasswordFormValue]);
  useUpdateEffect(() => {
    if (
      !configserverAddressFormValue?.adaptive ||
      !configserverPortFormValue?.adaptive
    ) {
      // ip和端口可以都为空或者都不为空
      if (
        configserverAddressFormValue?.value ||
        configserverPortFormValue?.value
      ) {
        setConfigserverAddressRules({
          rules: [
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.Obdeploy.ClusterConfig.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
            () => ({
              validator: (_: any, param?: API.ParameterValue) => {
                if (serverReg.test(param?.value || '')) {
                  return Promise.resolve();
                }
                return Promise.reject(
                  intl.formatMessage({
                    id: 'OBD.Obdeploy.ClusterConfig.TheIpAddressFormatIs',
                    defaultMessage: 'ip格式错误',
                  }),
                );
              },
            }),
          ],

          targetTable: 'ob-configserver',
          targetColumn: 'vip_address',
        });
        setConfigserverPortRules({
          rules: [
            () => ({
              validator: (_: any, param?: API.ParameterValue) => {
                if (!param?.value) {
                  return Promise.reject(
                    intl.formatMessage({
                      id: 'OBD.Obdeploy.ClusterConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    }),
                  );
                }
                return Promise.resolve();
              },
            }),
          ],
          targetTable: 'ob-configserver',
          targetColumn: 'vip_port',
        });
      } else {
        setConfigserverAddressRules({
          rules: [],
          targetTable: 'ob-configserver',
          targetColumn: 'vip_address',
        });
        setConfigserverPortRules({
          rules: [],
          targetTable: 'ob-configserver',
          targetColumn: 'vip_port',
        });
        form.validateFields([
          ['obconfigserver', 'parameters', 'vip_address', 'params'],
          ['obconfigserver', 'parameters', 'vip_port', 'params'],
        ]);
      }
    }
  }, [configserverAddressFormValue, configserverPortFormValue]);
  return (
    <>
      <div style={{ height: 24, display: 'flex', alignItems: 'center' }}>
        <span
          style={{
            color: '#132039',
            fontWeight: 500,
            fontSize: 16,
            lineHeight: '24px',
          }}
        >
          {intl.formatMessage({
            id: 'OBD.pages.components.ClusterConfig.MoreConfigurations',
            defaultMessage: '更多配置',
          })}
        </span>
        <Switch
          className="ml-20"
          checked={switchChecked}
          onChange={switchOnChange}
        />
      </div>
      <ConfigTable
        showVisible={switchChecked}
        dataSource={datasource}
        loading={loading}
        customParameter={<Parameter />}
        parameterRules={[
          proxyParameterRules,
          authParameterRules,
          configserverAddressRules,
          configserverPortRules,
        ]}
      />
    </>
  );
}
