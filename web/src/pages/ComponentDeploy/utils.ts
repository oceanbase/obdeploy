type ComponentDeployment = {
  component_name: string;
  deployed?: number;
};

type ComponentConfig = {
  component?: string;
  parameters?: API.MoreParameter[];
};

/**
 * Keep only components that are selected for this change and are not already
 * deployed. This list is also the source of truth for subsequent steps.
 */
export const prepareComponentChangeSelection = <T extends ComponentDeployment>(
  components: T[] | undefined,
  selectedConfig: string[],
) => {
  const selectedComponents = components?.filter(
    (component) =>
      component.deployed !== 1 &&
      selectedConfig.includes(component.component_name),
  ) || [];

  return {
    selectedComponents,
    nextSelectedConfig: selectedComponents.map(
      (component) => component.component_name,
    ),
  };
};

/**
 * Initialize the form store for every component whose advanced parameters were
 * loaded asynchronously. Without this, untouched fields only exist in the
 * Parameter component's local state and validation receives `undefined`.
 */
export const buildComponentParameterFormValues = (
  components: Record<string, ComponentConfig>,
  componentKeys: string[],
  parameterConfig: API.NewParameterMeta[],
  getInitialParameters: (
    component: string,
    parameters: API.MoreParameter[],
    parameterConfig: API.NewParameterMeta[],
  ) => any,
) =>
  componentKeys.reduce<Record<string, { parameters: any }>>((values, key) => {
    const component = components[key];
    if (component?.component) {
      values[key] = {
        parameters: getInitialParameters(
          component.component,
          component.parameters || [],
          parameterConfig,
        ),
      };
    }
    return values;
  }, {});
