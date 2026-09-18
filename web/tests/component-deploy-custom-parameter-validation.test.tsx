const React = require('react');
const { act, create } = require('react-test-renderer');

const mockQueryComponentParameters = jest.fn();
const mockSetCurrent = jest.fn();
const mockSetComponentsMoreConfig = jest.fn();
const mockSetComponentsMoreConfigSignature = jest.fn();
const mockSetComponentsMore = jest.fn();
const mockSetComponentConfig = jest.fn();
const mockSetErrorVisible = jest.fn();
const mockSetErrorsList = jest.fn();
const mockSetPreCheckInfoOk = jest.fn();
const mockFormValues: Record<string, any> = {};
let mockValidationBlocked = false;

const mergeValues = (target: Record<string, any>, source: Record<string, any>) => {
  Object.entries(source).forEach(([key, value]) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      target[key] = target[key] || {};
      mergeValues(target[key], value);
    } else {
      target[key] = value;
    }
  });
};

const mockForm = {
  getFieldsValue: jest.fn(() => mockFormValues),
  setFieldValue: jest.fn((path: string[], value: any) => {
    let target = mockFormValues;
    path.slice(0, -1).forEach((key) => {
      target[key] = target[key] || {};
      target = target[key];
    });
    target[path[path.length - 1]] = value;
  }),
  setFieldsValue: jest.fn((values: Record<string, any>) => {
    mergeValues(mockFormValues, values);
  }),
  validateFields: jest.fn(() => ({
    then: (onValid: (values: Record<string, any>) => void) => {
      const parameter =
        mockFormValues.prometheus?.parameters?.required_parameter?.params;
      mockValidationBlocked = Boolean(
        parameter?.require && !parameter?.adaptive && !parameter?.value,
      );
      if (!mockValidationBlocked) {
        onValid(mockFormValues);
      }
      return {
        catch: (onInvalid: (error: any) => void) => {
          if (mockValidationBlocked) {
            onInvalid({
              errorFields: [
                {
                  name: [
                    'prometheus',
                    'parameters',
                    'required_parameter',
                    'params',
                  ],
                },
              ],
            });
          }
        },
      };
    },
  })),
};

const mockComponentDeployModel = {
  selectedConfig: ['prometheus'],
  deployUser: 'admin',
  setCurrent: mockSetCurrent,
  current: 2,
  componentsMore: true,
  setComponentsMore: mockSetComponentsMore,
  componentsMoreConfig: [],
  setComponentsMoreConfig: mockSetComponentsMoreConfig,
  componentsMoreConfigSignature: '',
  setComponentsMoreConfigSignature: mockSetComponentsMoreConfigSignature,
  lowVersion: false,
  componentConfig: {
    appname: 'component-change',
    deployUser: 'admin',
    home_path: '/home/admin/component-change',
    prometheus: {
      component: 'prometheus',
      version: '2.0.0',
      parameters: [],
      servers: ['127.0.0.1'],
      basic_auth_users: { admin: 'password' },
    },
  },
  setComponentConfig: mockSetComponentConfig,
  setPreCheckInfoOk: mockSetPreCheckInfoOk,
};

const mockGlobalModel = {
  setErrorVisible: mockSetErrorVisible,
  setErrorsList: mockSetErrorsList,
  errorsList: [],
  handleQuitProgress: jest.fn(),
};

jest.mock('@umijs/max', () => ({
  getLocale: () => 'zh-CN',
  useModel: (name: string) =>
    name === 'componentDeploy' ? mockComponentDeployModel : mockGlobalModel,
}));

jest.mock('@/utils/useRequest', () => ({
  __esModule: true,
  default: () => ({ run: mockQueryComponentParameters }),
}));

jest.mock('@/services/ob-deploy-web/Components', () => ({
  queryComponentParameters: jest.fn(),
}));

jest.mock('@/services/component-change/componentChange', () => ({
  componentChangeConfig: jest.fn(),
}));

jest.mock('@/services/ob-deploy-web/Common', () => ({
  getPublicKey: jest.fn(),
}));

jest.mock('ahooks', () => ({
  useRequest: () => ({ loading: false, run: jest.fn() }),
  useUpdateEffect: () => undefined,
}));

jest.mock('@/utils', () => ({
  getErrorInfo: (error: any) => error,
  handleQuit: jest.fn(),
  PASSWORD_REGEX: /.*/,
  serversValidator: jest.fn(() => Promise.resolve()),
  validatePassword: jest.fn(() => () => Promise.resolve()),
}));

jest.mock('@/utils/helper', () => ({
  formatMoreConfig: (items: any[]) => items,
  generateComplexPwd: jest.fn(() => 'complex-password'),
  generatePwd: jest.fn(() => 'password'),
  getInitialParameters: (
    component: string,
    _parameters: any[],
    parameterConfig: any[],
  ) => {
    const config = parameterConfig.find((item) => item.component === component);
    if (!config) return undefined;
    return Object.fromEntries(
      config.configParameter.map((item: any) => [
        item.name,
        {
          ...item,
          key: item.name,
          params: {
            value: item.default,
            adaptive: item.auto,
            require: item.require,
            type: item.type,
          },
        },
      ]),
    );
  },
}));

jest.mock('@/utils/intl', () => ({
  intl: { formatMessage: ({ defaultMessage }: any) => defaultMessage },
}));

jest.mock('@/pages/constants', () => ({
  configServerComponent: 'ob-configserver',
  grafanaComponent: 'grafana',
  obagentComponent: 'obagent',
  onlyComponentsKeys: [
    'obproxy',
    'obagent',
    'obconfigserver',
    'grafana',
    'prometheus',
    'alertmanager',
    'obshell Dashboard',
  ],
  pathRule: {},
  prometheusComponent: 'prometheus',
  alertManagerComponent: 'alertmanager',
  allComponentsKeys: ['prometheus'],
  componentsConfig: {
    prometheus: { labelName: 'Prometheus', name: 'Prometheus' },
  },
  componentVersionTypeToComponent: {},
  configServerComponentKey: 'obconfigserver',
  obproxyComponent: 'obproxy',
}));

jest.mock('@/pages/Obdeploy/ClusterConfig', () => ({
  formatParameters: (parameters: any) => parameters,
}));

jest.mock('@/pages/Obdeploy/CheckInfo', () => ({
  formatConfigData: jest.fn(),
}));

jest.mock('@ant-design/pro-components', () => {
  const React = require('react');
  const Container = ({ children }: any) => React.createElement('div', null, children);
  const ProForm = ({ children }: any) => React.createElement('form', null, children);
  ProForm.useForm = () => [mockForm];
  ProForm.useWatch = () => undefined;
  return {
    ProCard: Container,
    ProForm,
    ProFormSelect: () => null,
    ProFormText: () => null,
  };
});

jest.mock('antd', () => {
  const React = require('react');
  const Container = ({ children }: any) => React.createElement('div', null, children);
  const Table = ({ columns, dataSource }: any) =>
    React.createElement(
      'table-view',
      null,
      dataSource.flatMap((record: any, rowIndex: number) =>
        columns.map((column: any, columnIndex: number) =>
          React.createElement(
            React.Fragment,
            { key: `${rowIndex}-${columnIndex}` },
            column.render
              ? column.render(record[column.dataIndex], record, rowIndex)
              : null,
          ),
        ),
      ),
    );
  return {
    Alert: Container,
    Button: ({ children, ...props }: any) =>
      React.createElement('button', props, children),
    Col: Container,
    Form: {
      Item: ({ children, ...props }: any) =>
        React.createElement('form-item', props, children),
    },
    Input: { Password: () => null },
    Row: Container,
    Space: Container,
    Spin: Container,
    Table,
    Tooltip: Container,
  };
});

jest.mock('@ant-design/icons', () => {
  const React = require('react');
  return {
    CaretDownOutlined: () => React.createElement('caret-down'),
    CaretRightOutlined: () => React.createElement('caret-right'),
    ExclamationCircleFilled: () => null,
    InfoCircleFilled: () => null,
  };
});
jest.mock('@oceanbase/ui', () => ({ Password: () => null }));
jest.mock('@/component/ComponentsPort', () => () => null);
jest.mock('@/component/MoreConfigTable', () => {
  const React = require('react');
  return (props: any) => React.createElement('more-config-table', props);
});
jest.mock('@/pages/Obdeploy/ClusterConfig/Parameter', () => () => null);
jest.mock('@/component/PreCheckComps', () => {
  const React = require('react');
  return {
    CompDetailCheckInfo: (props: any) =>
      React.createElement('component-detail-check', props),
    CompNodeCheckInfo: (props: any) =>
      React.createElement('component-node-check', props),
    DeployedCompCheckInfo: (props: any) =>
      React.createElement('deployed-component-check', props),
    PathCheckInfo: (props: any) => React.createElement('path-check', props),
    UserCheckInfo: (props: any) => React.createElement('user-check', props),
  };
});
jest.mock('@/component/CustomFooter', () => {
  const React = require('react');
  return ({ children }: any) => React.createElement('footer', null, children);
});

const ComponentConfig = require('@/pages/ComponentDeploy/ComponentConfig').default;
const PreCheckInfo = require('@/pages/ComponentDeploy/PreCheckInfo').default;
const ConfigTable = require('@/pages/Obdeploy/ClusterConfig/ConfigTable').default;
const MoreConfigTable = jest.requireActual('@/component/MoreConfigTable').default;

const flushPromises = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
};

describe('component change custom parameter validation', () => {
  let renderer: any;

  beforeEach(() => {
    Object.keys(mockFormValues).forEach((key) => delete mockFormValues[key]);
    mockValidationBlocked = false;
    mockQueryComponentParameters.mockReset();
    mockSetCurrent.mockReset();
    mockSetComponentsMoreConfig.mockReset();
    mockSetComponentsMoreConfigSignature.mockReset();
    mockSetComponentsMore.mockReset();
    mockSetComponentConfig.mockReset();
    mockSetErrorVisible.mockReset();
    mockSetErrorsList.mockReset();
    mockSetPreCheckInfoOk.mockReset();
    mockForm.setFieldsValue.mockClear();
    mockForm.setFieldValue.mockClear();
    mockForm.validateFields.mockClear();
    mockComponentDeployModel.lowVersion = false;
    mockComponentDeployModel.componentsMore = true;
    mockComponentDeployModel.componentsMoreConfig = [];
    mockComponentDeployModel.componentsMoreConfigSignature = '';
    mockQueryComponentParameters.mockResolvedValue({
      success: true,
      data: {
        items: [
          {
            component: 'prometheus',
            componentKey: 'prometheus',
            label: 'Prometheus',
            configParameter: [
              {
                name: 'required_parameter',
                default: '',
                require: true,
                type: 'String',
              },
            ],
          },
        ],
      },
    });
    (global as any).window = { scrollTo: jest.fn() };
  });

  afterEach(() => {
    act(() => renderer?.unmount());
    delete (global as any).window;
  });

  it('blocks the first next-step attempt when a Prometheus custom parameter is required and empty', async () => {
    await act(async () => {
      renderer = create(<ComponentConfig />);
    });
    await flushPromises();

    expect(mockQueryComponentParameters).toHaveBeenCalledWith({
      filters: [
        {
          component: 'prometheus',
          version: '2.0.0',
          is_essential_only: true,
        },
      ],
    });
    expect(mockForm.setFieldValue).toHaveBeenCalledWith(
      ['prometheus', 'parameters'],
      {
        required_parameter: expect.objectContaining({
          params: expect.objectContaining({
            adaptive: undefined,
            require: true,
            value: '',
          }),
        }),
      },
    );
    expect(
      renderer.root.findByType('more-config-table').props
        .keepMountedWhenHidden,
    ).toBe(true);

    const nextButton = renderer.root
      .findAllByType('button')
      .find((button: any) => button.props.type === 'primary');
    expect(nextButton).toBeDefined();
    act(() => nextButton.props.onClick());

    expect(mockForm.validateFields).toHaveBeenCalled();
    expect(mockValidationBlocked).toBe(true);
    expect(mockSetCurrent).not.toHaveBeenCalled();
    expect(mockSetComponentsMore).toHaveBeenCalledWith(true);
  });

  it('does not submit while custom parameter metadata is still loading', async () => {
    let resolveQuery: (value: any) => void = () => undefined;
    mockQueryComponentParameters.mockReturnValue(
      new Promise((resolve) => {
        resolveQuery = resolve;
      }),
    );

    await act(async () => {
      renderer = create(<ComponentConfig />);
    });

    const nextButton = renderer.root
      .findAllByType('button')
      .find((button: any) => button.props.type === 'primary');
    expect(nextButton.props.disabled).toBe(true);
    act(() => nextButton.props.onClick());
    expect(mockForm.validateFields).not.toHaveBeenCalled();
    expect(mockSetCurrent).not.toHaveBeenCalled();

    await act(async () => resolveQuery({ success: false }));
    await flushPromises();
  });

  it('refreshes parameter metadata instead of trusting a cache from another selection', async () => {
    mockComponentDeployModel.componentsMoreConfig = [
      {
        component: 'grafana',
        version: 'old-version',
        configParameter: [],
      },
    ];
    mockComponentDeployModel.componentsMoreConfigSignature = 'old-signature';

    await act(async () => {
      renderer = create(<ComponentConfig />);
    });
    await flushPromises();

    expect(mockQueryComponentParameters).toHaveBeenCalledWith({
      filters: [
        {
          component: 'prometheus',
          version: '2.0.0',
          is_essential_only: true,
        },
      ],
    });
  });

  it('does not register stale cached parameters while the panel is collapsed', async () => {
    mockComponentDeployModel.componentsMore = false;
    mockComponentDeployModel.componentsMoreConfig = [
      {
        component: 'grafana',
        version: 'old-version',
        configParameter: [
          {
            name: 'old_required_parameter',
            parameterValue: { adaptive: false, require: true, value: '' },
          },
        ],
      },
    ];
    mockComponentDeployModel.componentsMoreConfigSignature = 'old-signature';

    await act(async () => {
      renderer = create(<ComponentConfig />);
    });
    await flushPromises();

    expect(mockQueryComponentParameters).not.toHaveBeenCalled();
    expect(
      renderer.root.findByType('more-config-table').props.datasource,
    ).toEqual([]);
  });

  it('reuses matching cached metadata when returning to the same component version', async () => {
    const cachedConfig = [
      {
        component: 'prometheus',
        version: '2.0.0',
        configParameter: [],
      },
    ];
    mockComponentDeployModel.componentsMore = false;
    mockComponentDeployModel.componentsMoreConfig = cachedConfig;
    mockComponentDeployModel.componentsMoreConfigSignature = JSON.stringify([
      {
        component: 'prometheus',
        version: '2.0.0',
        is_essential_only: true,
      },
    ]);

    await act(async () => {
      renderer = create(<ComponentConfig />);
    });
    await flushPromises();

    expect(mockQueryComponentParameters).not.toHaveBeenCalled();
    expect(
      renderer.root.findByType('more-config-table').props.datasource,
    ).toBe(cachedConfig);
  });

  it('does not refresh current metadata when validation reopens the panel', async () => {
    await act(async () => {
      renderer = create(<ComponentConfig />);
    });
    await flushPromises();
    expect(mockQueryComponentParameters).toHaveBeenCalledTimes(1);

    mockComponentDeployModel.componentsMore = false;
    act(() => renderer.update(<ComponentConfig />));
    const nextButton = renderer.root
      .findAllByType('button')
      .find((button: any) => button.props.type === 'primary');
    act(() => nextButton.props.onClick());
    expect(mockSetComponentsMore).toHaveBeenLastCalledWith(true);

    mockComponentDeployModel.componentsMore = true;
    act(() => renderer.update(<ComponentConfig />));
    await flushPromises();
    expect(mockQueryComponentParameters).toHaveBeenCalledTimes(1);
  });

  it('loads custom parameters for a low-version deployment without throwing', async () => {
    mockComponentDeployModel.lowVersion = true;

    await act(async () => {
      renderer = create(<ComponentConfig />);
    });
    await flushPromises();

    expect(mockQueryComponentParameters).toHaveBeenCalled();
    expect(mockForm.setFieldValue).toHaveBeenCalledWith(
      ['prometheus', 'parameters'],
      expect.any(Object),
    );
  });

  it('renders the component precheck for a low-version deployment without throwing', () => {
    mockComponentDeployModel.lowVersion = true;

    act(() => {
      renderer = create(<PreCheckInfo />);
    });

    const nodeCheck = renderer.root.findByType('component-node-check');
    expect(nodeCheck.props.componentsNodeConfigList).toEqual([
      expect.objectContaining({ key: 'prometheus', name: 'Prometheus' }),
    ]);
  });

  it('keeps custom parameter fields registered while the panel is collapsed', () => {
    act(() => {
      renderer = create(
        <ConfigTable
          dataSource={[
            {
              component: 'prometheus',
              label: 'Prometheus',
              configParameter: [
                {
                  name: 'required_parameter',
                  description: 'required parameter',
                  parameterValue: {
                    adaptive: false,
                    defaultValue: '',
                    require: true,
                    type: 'String',
                    value: '',
                  },
                },
              ],
            },
          ]}
          loading={false}
          keepMountedWhenHidden
          showMetaPassword={false}
          showVisible={false}
        />,
      );
    });

    expect(
      renderer.root.findAllByType('form-item').some((item: any) =>
        item.props.name?.includes('required_parameter'),
      ),
    ).toBe(true);
  });

  it('preserves the default unmount behavior for other ConfigTable callers', () => {
    act(() => {
      renderer = create(
        <ConfigTable
          dataSource={[
            {
              component: 'prometheus',
              label: 'Prometheus',
              configParameter: [
                {
                  name: 'required_parameter',
                  description: 'required parameter',
                  parameterValue: {
                    adaptive: false,
                    defaultValue: '',
                    require: true,
                    type: 'String',
                    value: '',
                  },
                },
              ],
            },
          ]}
          loading={false}
          showMetaPassword={false}
          showVisible={false}
        />,
      );
    });

    expect(renderer.root.findAllByType('form-item')).toHaveLength(0);
  });

  it('forwards keepMountedWhenHidden through MoreConfigTable', () => {
    act(() => {
      renderer = create(
        <MoreConfigTable
          datasource={[
            {
              component: 'prometheus',
              label: 'Prometheus',
              configParameter: [
                {
                  name: 'required_parameter',
                  description: 'required parameter',
                  parameterValue: {
                    adaptive: false,
                    defaultValue: '',
                    require: true,
                    type: 'String',
                    value: '',
                  },
                },
              ],
            },
          ]}
          form={mockForm}
          keepMountedWhenHidden
          loading={false}
          switchChecked={false}
          switchOnChange={jest.fn()}
        />,
      );
    });

    expect(renderer.root.findAllByType('form-item')).not.toHaveLength(0);
  });

  it('uses the parent state when an error expands the custom parameter panel', () => {
    const switchOnChange = jest.fn();
    act(() => {
      renderer = create(
        <MoreConfigTable
          datasource={[]}
          form={mockForm}
          loading={false}
          switchChecked={false}
          switchOnChange={switchOnChange}
        />,
      );
    });
    expect(renderer.root.findAllByType('caret-right')).toHaveLength(1);

    act(() => {
      renderer.update(
        <MoreConfigTable
          datasource={[]}
          form={mockForm}
          loading={false}
          switchChecked={true}
          switchOnChange={switchOnChange}
        />,
      );
    });
    expect(renderer.root.findAllByType('caret-down')).toHaveLength(1);

    const toggle = renderer.root
      .findAllByType('div')
      .find((node: any) => typeof node.props.onClick === 'function');
    act(() => toggle.props.onClick());
    expect(switchOnChange).toHaveBeenLastCalledWith(false);
  });
});
