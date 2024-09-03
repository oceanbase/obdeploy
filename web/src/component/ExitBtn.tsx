import { PathType } from '@/pages/type';
import * as Process from '@/services/ocp_installer_backend/Process';
import { errorHandler } from '@/utils';
import { getTailPath } from '@/utils/helper';
import { intl } from '@/utils/intl';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { Button, Modal } from 'antd';
import { history, useModel, useRequest } from 'umi';

const defaultContentText = intl.formatMessage({
  id: 'OBD.src.component.ExitBtn.AfterExitingTheDeploymentAnd',
  defaultMessage: '退出后，部署安装工作将被终止，请谨慎操作。',
});

export default function ExitBtn() {
  const { setInstallStatus, setInstallResult } = useModel('ocpInstallData');
  const path: PathType = getTailPath() as PathType;
  const ocpTextMap = {
    title: intl.formatMessage({
      id: 'OBD.src.component.ExitBtn.ExitTheOcpDeploymentInstaller',
      defaultMessage: '退出 OCP 部署安装程序',
    }),
    content: defaultContentText,
  };
  const pathTextMap = {
    componentDeploy: {
      title: intl.formatMessage({
        id: 'OBD.src.component.ExitBtn.ExitTheComponentDeploymentProgram',
        defaultMessage: '退出组件部署程序',
      }),
      content: defaultContentText,
    },
    update: {
      title: intl.formatMessage({
        id: 'OBD.src.component.ExitBtn.ExitTheOcpUpgradeProgram',
        defaultMessage: '退出 OCP 升级程序',
      }),
      content: intl.formatMessage({
        id: 'OBD.src.component.ExitBtn.AfterExitingTheUpgradeWill',
        defaultMessage: '退出后，升级工作将被终止，请谨慎操作',
      }),
    },
    guide: {
      title: intl.formatMessage({
        id: 'OBD.src.component.ExitBtn.ExitTheOceanbaseDeploymentWizard',
        defaultMessage: '退出 OceanBase 部署向导',
      }),
      content: defaultContentText,
    },
    obdeploy: {
      title: intl.formatMessage({
        id: 'OBD.src.component.ExitBtn.ExitTheDeploymentProgram',
        defaultMessage: '退出部署程序',
      }),
      content: intl.formatMessage({
        id: 'OBD.src.component.ExitBtn.AfterExitingTheDeploymentWill',
        defaultMessage: '退出后，部署工作将被终止，请谨慎操作。',
      }),
    },
    install: ocpTextMap,
    configuration: ocpTextMap,
    ocpInstaller: ocpTextMap,
    default: ocpTextMap,
  };
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
          title: pathTextMap[path]?.title ?? pathTextMap.default.title,
          icon: <ExclamationCircleOutlined style={{ color: '#FF4B4B' }} />,
          content: pathTextMap[path]?.content ?? pathTextMap.default.content,
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
