import { intl } from '@/utils/intl';
import { Button } from 'antd';
import { useRequest, history } from 'umi';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { Modal } from '@oceanbase/design';
import { errorHandler } from '@/utils';
import { useModel } from 'umi';
import * as Process from '@/services/ocp_installer_backend/Process';
import { PathType } from '@/pages/type';
import { getTailPath } from '@/utils/helper';

export default function ExitBtn() {
  const { setInstallStatus, setInstallResult } = useModel('ocpInstallData');
  const path: PathType = getTailPath() as PathType;
  // 退出
  const { run: suicide, loading: suicideLoading } = useRequest(
    Process.suicide,
    {
      manual: true,
      onSuccess: () => {
        if (path === 'configuration' || path === 'install') {
          setInstallStatus('');
          setInstallResult('');
        }
        history.push(`/quit?path=${path}`);
      },
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    },
  );

  return (
    <Button
      loading={suicideLoading}
      spm={intl.formatMessage({
        id: 'OBD.src.component.ExitBtn.DeploymentConfigurationExit',
        defaultMessage: '部署配置-退出',
      })}
      onClick={() => {
        Modal.confirm({
          title:
            path === 'update'
              ? intl.formatMessage({
                  id: 'OBD.src.component.ExitBtn.ExitTheOcpUpgradeProgram',
                  defaultMessage: '退出 OCP 升级程序',
                })
              : path === 'guide'
              ? intl.formatMessage({
                  id: 'OBD.src.component.ExitBtn.ExitTheOceanbaseDeploymentWizard',
                  defaultMessage: '退出 OceanBase 部署向导',
                })
              : intl.formatMessage({
                  id: 'OBD.src.component.ExitBtn.ExitTheOcpDeploymentInstaller',
                  defaultMessage: '退出 OCP 部署安装程序',
                }),
          icon: <ExclamationCircleOutlined style={{ color: '#FF4B4B' }} />,
          content:
            path === 'update'
              ? intl.formatMessage({
                  id: 'OBD.src.component.ExitBtn.AfterExitingTheUpgradeWill',
                  defaultMessage: '退出后，升级工作将被终止，请谨慎操作',
                })
              : intl.formatMessage({
                  id: 'OBD.src.component.ExitBtn.AfterExitingTheDeploymentAnd',
                  defaultMessage: '退出后，部署安装工作将被终止，请谨慎操作。',
                }),

          okText: intl.formatMessage({
            id: 'OBD.src.component.ExitBtn.Exit',
            defaultMessage: '退出',
          }),
          okButtonProps: {
            danger: true,
          },
          onOk: () => {
            suicide();
          },
        });
      }}
    >
      {intl.formatMessage({
        id: 'OBD.src.component.ExitBtn.Exit',
        defaultMessage: '退出',
      })}
    </Button>
  );
}
