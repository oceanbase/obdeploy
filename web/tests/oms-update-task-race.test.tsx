const { act, create } = require('react-test-renderer');
const React = require('react');

const mockNotificationApi = {
  destroy: jest.fn(),
  error: jest.fn(),
};
const mockModalDestroy = jest.fn();
const mockModalApi = {
  confirm: jest.fn(() => ({ destroy: mockModalDestroy })),
};
const mockHistory = { push: jest.fn() };
const mockRequestOptions = new Map<any, any>();
const mockRequestPipeline = { data: [] as any[], processExit: false };

const mockOcp = {
  backupOms: jest.fn(),
  getOmsDisplay: jest.fn(),
  getOmsInstallTask: jest.fn(),
  getOmsInstallTaskLog: jest.fn(),
  getOmsReinstallTask: jest.fn(),
  getOmsReinstallTaskLog: jest.fn(),
  getOmsUpgradePrecheckTask: jest.fn(),
  getOmsUpgradeTask: jest.fn(),
  getOmsUpgradeTaskLog: jest.fn(),
  listOmsDeployments: jest.fn(),
  precheckOmsUpgrade: jest.fn(),
  upgradeOms: jest.fn(),
};

const mockModels: Record<string, any> = {};

function mockUseTestRequest(service: (...args: any[]) => any, options: any = {}) {
  const serviceRef = React.useRef(service);
  const optionsRef = React.useRef(options);
  const [data, setData] = React.useState<any>();
  serviceRef.current = service;
  optionsRef.current = options;
  mockRequestOptions.set(service, options);

  const run = React.useCallback((...args: any[]) => {
    return Promise.resolve()
      .then(() => serviceRef.current(...args))
      .then((response) => {
        setData(response);
        optionsRef.current.onSuccess?.(response);
        return response;
      })
      .catch((error) => {
        optionsRef.current.onError?.(error);
        return undefined;
      });
  }, []);
  const cancel = React.useCallback(() => undefined, []);

  return { run, refresh: run, cancel, data, loading: false };
}

jest.mock('@umijs/max', () => ({
  history: mockHistory,
  useLocation: () => ({ search: '?step=2' }),
  useModel: (name: string) => mockModels[name],
}));

jest.mock('antd', () => ({
  Modal: { useModal: () => [mockModalApi, null] },
  notification: { useNotification: () => [mockNotificationApi, null] },
}));

jest.mock('ahooks', () => ({ useRequest: mockUseTestRequest }));

jest.mock('@/utils/useRequest', () => ({
  __esModule: true,
  default: mockUseTestRequest,
  requestPipeline: mockRequestPipeline,
}));

jest.mock('@/services/ocp_installer_backend/OCP', () => mockOcp);
jest.mock('@/services/ob-deploy-web/oms', () => ({
  queryInstallLogOms: jest.fn(),
  queryInstallStatusOms: jest.fn(),
}));
jest.mock('@/utils', () => ({
  errorHandler: jest.fn(),
  getErrorInfo: (error: any) => error,
}));
jest.mock('@/utils/intl', () => ({
  intl: { formatMessage: ({ defaultMessage }: any) => defaultMessage },
}));

jest.mock('@oceanbase/design', () => {
  const React = require('react');
  const Container = ({ children }: any) => React.createElement('div', null, children);
  return {
    Button: ({ children, ...props }: any) => React.createElement('button', props, children),
    Form: { useForm: () => [{}] },
    message: {},
    Space: Container,
    Tooltip: Container,
  };
});
jest.mock('@oceanbase/ui', () => {
  const React = require('react');
  return {
    PageContainer: ({ children }: any) => React.createElement('main', null, children),
  };
});

jest.mock('@/component/CustomFooter', () => {
  const React = require('react');
  return ({ children }: any) => React.createElement('footer', null, children);
});
jest.mock('@/component/ExitBtn', () => () => null);
jest.mock('@/component/Steps', () => {
  const React = require('react');
  return () => React.createElement('steps-view');
});
jest.mock('@/component/InstallProcessComp', () => {
  const React = require('react');
  return (props: any) => React.createElement('process-view', props);
});
jest.mock('@/constant/configuration', () => ({
  METADB_OMS_UPDATE: [],
  STEPS_KEYS_UPDATE_OMS: [],
}));
jest.mock('@/pages/Oms/Update/Component/DeployConfig', () => () => null);
jest.mock('@/pages/Oms/Update/Component/ConnectionInfo', () => () => null);
jest.mock('@/pages/Oms/Update/Component/UpdatePreCheck', () => () => null);
jest.mock('@/pages/Oms/Update/Component/Backup', () => {
  const React = require('react');
  return () => React.createElement('backup-view');
});
jest.mock('@/pages/Oms/InstallFinished', () => {
  const React = require('react');
  return () => React.createElement('finished-view');
});

const Update = require('@/pages/Oms/Update').default;
const InstallProcess = require('@/pages/Oms/InstallProcess').default;

const flushPromises = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
};

const setModelValue = (model: any, key: string) => (value: any) => {
  model[key] = typeof value === 'function' ? value(model[key]) : value;
};

const findNextButton = (root: any) =>
  root.findAllByType('button').find((button) => button.props.type === 'primary');

describe.each(['online', 'offline'])('OMS %s upgrade task lifecycle', (upgradeMode) => {
  let renderer: any;
  let preserveStaleTerminalState: boolean;
  let resolveStatus: (value: any) => void;

  beforeEach(() => {
    jest.useFakeTimers();
    (global as any).window = {
      clearTimeout,
      open: jest.fn(),
      setTimeout,
    };
    Object.values(mockOcp).forEach((mockFn) => mockFn.mockReset());
    mockNotificationApi.destroy.mockReset();
    mockNotificationApi.error.mockReset();
    mockModalApi.confirm.mockClear();
    mockModalDestroy.mockReset();
    mockHistory.push.mockReset();
    mockRequestOptions.clear();
    mockRequestPipeline.data = [];
    mockRequestPipeline.processExit = false;

    const globalModel: any = {
      configData: {},
      errorsList: [],
      omsConfigData: {
        backup_method: 'not_backup',
        cluster_name: 'oms',
        image_name: 'example/oms-ce',
        upgrade_mode: upgradeMode,
        version: '4.2.14',
      },
      setCurrentStep: jest.fn(),
    };
    globalModel.setErrorVisible = setModelValue(globalModel, 'errorVisible');
    globalModel.setErrorsList = setModelValue(globalModel, 'errorsList');

    const installModel: any = {
      connectId: 7,
      installResult: 'FAILED',
      installStatus: 'FINISHED',
      isReinstall: false,
      logData: { log: 'stale task 7 failure' },
    };
    preserveStaleTerminalState = true;
    installModel.setConnectId = setModelValue(installModel, 'connectId');
    installModel.setInstallResult = (value: any) => {
      if (!(preserveStaleTerminalState && value === 'RUNNING')) {
        installModel.installResult = value;
      }
    };
    installModel.setInstallStatus = (value: any) => {
      if (!(preserveStaleTerminalState && value === 'RUNNING')) {
        installModel.installStatus = value;
      }
    };
    installModel.setIsReinstall = setModelValue(installModel, 'isReinstall');
    installModel.setLogData = setModelValue(installModel, 'logData');

    mockModels.global = globalModel;
    mockModels.ocpInstallData = installModel;

    mockOcp.upgradeOms.mockResolvedValue({ success: true, data: { id: 8 } });
    mockOcp.getOmsUpgradeTask.mockImplementation(() =>
      new Promise((resolve) => {
        resolveStatus = resolve;
      }),
    );
    mockOcp.getOmsUpgradeTaskLog.mockResolvedValue({
      success: true,
      data: { log: 'task 8 running' },
    });
  });

  afterEach(() => {
    act(() => renderer?.unmount());
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    delete (global as any).window;
  });

  it.each(['SUCCESSFUL', 'FAILED'])(
    'ignores a stale terminal result until the new task finishes as %s',
    async (terminalResult) => {
    await act(async () => {
      renderer = create(<Update />);
    });

    const nextButton = findNextButton(renderer.root);
    expect(nextButton).toBeDefined();
    await act(async () => {
      nextButton?.props.onClick();
    });
    await flushPromises();

    expect(mockOcp.upgradeOms).toHaveBeenCalledWith(expect.objectContaining({
      cluster_name: 'oms',
      upgrade_mode: upgradeMode,
    }));
    expect(mockOcp.getOmsUpgradeTask).toHaveBeenCalledWith({
      cluster_name: 'oms',
      task_id: 8,
    });
    expect(mockOcp.getOmsUpgradeTaskLog).toHaveBeenCalledWith({
      cluster_name: 'oms',
      task_id: 8,
    });
    expect(renderer.root.findAllByType('process-view')).toHaveLength(1);
    expect(renderer.root.findAllByType('finished-view')).toHaveLength(0);
    expect(mockModels.ocpInstallData.installStatus).toBe('FINISHED');
    expect(mockModels.ocpInstallData.installResult).toBe('FAILED');

    preserveStaleTerminalState = false;
    if (terminalResult === 'FAILED') {
      mockOcp.getOmsUpgradeTaskLog.mockRejectedValueOnce(
        new Error('final log unavailable'),
      );
    }
    await act(async () => {
      resolveStatus({
        success: true,
        data: { status: 'FINISHED', result: terminalResult },
      });
    });
    await flushPromises();

    expect(renderer.root.findAllByType('process-view')).toHaveLength(0);
    expect(renderer.root.findAllByType('finished-view')).toHaveLength(1);
    expect(mockModels.ocpInstallData.installStatus).toBe('FINISHED');
    expect(mockModels.ocpInstallData.installResult).toBe(terminalResult);
    },
  );
});

describe('OMS upgrade polling feedback isolation', () => {
  let renderer: any;

  beforeEach(() => {
    jest.useFakeTimers();
    (global as any).window = {
      clearTimeout,
      open: jest.fn(),
      setTimeout,
    };
    Object.values(mockOcp).forEach((mockFn) => mockFn.mockReset());
    mockNotificationApi.destroy.mockReset();
    mockNotificationApi.error.mockReset();
    mockModalApi.confirm.mockClear();
    mockModalDestroy.mockReset();
    mockHistory.push.mockReset();
    mockRequestOptions.clear();
    mockRequestPipeline.data = [{ code: 'ERR_NETWORK', source: 'other-page' }];
    mockRequestPipeline.processExit = false;

    const globalModel: any = {
      configData: {},
      errorVisible: false,
      errorsList: [],
      omsConfigData: { cluster_name: 'oms' },
      setCurrentStep: jest.fn(),
    };
    globalModel.setErrorVisible = jest.fn(setModelValue(globalModel, 'errorVisible'));
    globalModel.setErrorsList = jest.fn(setModelValue(globalModel, 'errorsList'));

    const installModel: any = {
      connectId: 8,
      installResult: 'RUNNING',
      installStatus: 'RUNNING',
      isReinstall: false,
      logData: {},
    };
    installModel.setInstallResult = jest.fn(setModelValue(installModel, 'installResult'));
    installModel.setInstallStatus = jest.fn(setModelValue(installModel, 'installStatus'));
    installModel.setLogData = jest.fn(setModelValue(installModel, 'logData'));

    mockModels.global = globalModel;
    mockModels.ocpInstallData = installModel;
    mockOcp.getOmsUpgradeTaskLog.mockResolvedValue({
      success: true,
      data: { log: 'upgrade running' },
    });
  });

  afterEach(() => {
    act(() => renderer?.unmount());
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    delete (global as any).window;
  });

  it('keeps transient polling failures local and closes the modal on recovery', async () => {
    let statusCalls = 0;
    mockOcp.getOmsUpgradeTask.mockImplementation(() => {
      statusCalls += 1;
      if (statusCalls <= 5) {
        return Promise.reject(Object.assign(new Error('temporary polling failure'), {
          code: 'ERR_NETWORK',
        }));
      }
      return Promise.resolve({
        success: true,
        data: { status: 'RUNNING', result: 'RUNNING' },
      });
    });

    await act(async () => {
      renderer = create(<InstallProcess type="update" taskId={8} />);
    });
    await flushPromises();

    expect(mockRequestOptions.get(mockOcp.getOmsUpgradeTask)).toEqual(
      expect.objectContaining({ skipRequestPipeline: true }),
    );
    expect(mockRequestOptions.get(mockOcp.getOmsUpgradeTaskLog)).toEqual(
      expect.objectContaining({ skipRequestPipeline: true }),
    );
    expect(mockRequestPipeline.data).toEqual([
      { code: 'ERR_NETWORK', source: 'other-page' },
    ]);

    expect(mockModels.global.setErrorVisible).not.toHaveBeenCalled();
    expect(mockModels.global.setErrorsList).not.toHaveBeenCalled();
    expect(mockModalApi.confirm).not.toHaveBeenCalled();

    for (let retry = 0; retry < 4; retry += 1) {
      await act(async () => {
        jest.advanceTimersByTime(2000);
      });
      await flushPromises();
    }

    expect(statusCalls).toBe(5);
    expect(mockModalApi.confirm).toHaveBeenCalledTimes(1);
    expect(mockNotificationApi.error).not.toHaveBeenCalled();
    expect(mockModels.global.setErrorVisible).not.toHaveBeenCalled();
    expect(mockModels.global.setErrorsList).not.toHaveBeenCalled();

    await act(async () => {
      jest.advanceTimersByTime(2000);
    });
    await flushPromises();

    expect(statusCalls).toBe(6);
    expect(mockModalDestroy).toHaveBeenCalledTimes(1);
    expect(mockModels.ocpInstallData.installResult).toBe('RUNNING');
    expect(mockModels.ocpInstallData.installStatus).toBe('RUNNING');
  });
});
