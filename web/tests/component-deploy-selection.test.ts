import {
  buildComponentParameterFormValues,
  prepareComponentChangeSelection,
} from '../src/pages/ComponentDeploy/utils';

describe('component change deployment selection', () => {
  it('removes an already deployed obagent automatically selected by prometheus', () => {
    const selection = prepareComponentChangeSelection(
      [
        { component_name: 'obagent', deployed: 1 },
        { component_name: 'prometheus', deployed: 0 },
        { component_name: 'grafana', deployed: 0 },
      ],
      ['prometheus', 'obagent'],
    );

    expect(selection.selectedComponents.map(
      (component) => component.component_name,
    )).toEqual(['prometheus']);
    expect(selection.nextSelectedConfig).toEqual(['prometheus']);
  });

  it('keeps an undeployed dependency selected for the current change', () => {
    const selection = prepareComponentChangeSelection(
      [
        { component_name: 'obagent', deployed: 0 },
        { component_name: 'prometheus', deployed: 0 },
      ],
      ['prometheus', 'obagent'],
    );

    expect(selection.nextSelectedConfig).toEqual([
      'obagent',
      'prometheus',
    ]);
  });

  it('does not allow a deployment step containing only deployed components', () => {
    const selection = prepareComponentChangeSelection(
      [{ component_name: 'obagent', deployed: 1 }],
      ['obagent'],
    );

    expect(selection.selectedComponents).toEqual([]);
    expect(selection.nextSelectedConfig).toEqual([]);
  });
});

describe('component change advanced parameter initialization', () => {
  it('initializes every selected component in the form store', () => {
    const componentNames: Record<string, string> = {
      obproxy: 'obproxy-ce',
      obagent: 'obagent',
      obconfigserver: 'ob-configserver',
      grafana: 'grafana',
      prometheus: 'prometheus',
      alertmanager: 'alertmanager',
    };
    const components = Object.keys(componentNames).reduce<Record<string, any>>(
      (result, key) => {
        result[key] = { component: componentNames[key], parameters: [] };
        return result;
      },
      {},
    );
    const parameterConfig = Object.keys(componentNames).map((key) => ({
      component: componentNames[key],
      componentKey: key,
      label: key,
      configParameter: [
        {
          name: 'required_parameter',
          default: '',
          require: true,
          type: 'String',
        },
      ],
    })) as API.NewParameterMeta[];

    const values = buildComponentParameterFormValues(
      components,
      Object.keys(componentNames),
      parameterConfig,
      (component, _parameters, config) => {
        const item = config.find(({ component: name }) => name === component)
          ?.configParameter[0];
        return {
          [item!.name]: {
            params: {
              adaptive: item!.auto,
              require: item!.require,
              value: item!.default,
            },
          },
        };
      },
    );

    expect(Object.keys(values)).toEqual(Object.keys(componentNames));
    Object.values(values).forEach(({ parameters }) => {
      expect(parameters.required_parameter.params).toMatchObject({
        adaptive: undefined,
        require: true,
        value: '',
      });
    });
  });

  it('does not add components that are not part of this deployment', () => {
    expect(
      buildComponentParameterFormValues(
        { grafana: {}, prometheus: { component: 'prometheus' } },
        ['grafana', 'prometheus'],
        [],
        () => undefined,
      ),
    ).toEqual({ prometheus: { parameters: undefined } });
  });
});
