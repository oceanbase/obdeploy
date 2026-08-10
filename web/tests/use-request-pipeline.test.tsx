const React = require('react');
const { act, create } = require('react-test-renderer');

const mockUnderlyingUseRequest = jest.fn();
const mockHandleResponseError = jest.fn();

jest.mock('@umijs/max', () => ({
  useRequest: (...args: any[]) => mockUnderlyingUseRequest(...args),
}));
jest.mock('@/utils', () => ({
  handleResponseError: mockHandleResponseError,
}));
jest.mock('@/pages/Layout', () => ({ requestHandler: jest.fn() }));
jest.mock('antd', () => ({ message: {} }));

const useCustomRequest = require('@/utils/useRequest').default;
const { requestPipeline } = require('@/utils/useRequest');

const service = jest.fn();

function RequestHarness({ options }: { options: any }) {
  useCustomRequest(service, options);
  return React.createElement('request-harness');
}

describe('custom useRequest pipeline isolation', () => {
  let renderer: any;
  let capturedOptions: any;

  beforeEach(() => {
    capturedOptions = undefined;
    requestPipeline.data = [];
    requestPipeline.processExit = false;
    mockHandleResponseError.mockReset();
    mockUnderlyingUseRequest.mockReset();
    mockUnderlyingUseRequest.mockImplementation((_service, options) => {
      capturedOptions = options;
      return { data: undefined };
    });
  });

  afterEach(() => {
    act(() => renderer?.unmount());
  });

  it('does not read or write the shared pipeline when isolation is enabled', () => {
    const existingError = { code: 'ERR_NETWORK', source: 'other-page' };
    const pollingError = { code: 'ERR_NETWORK', source: 'oms-upgrade' };
    const onError = jest.fn();
    const onSuccess = jest.fn();
    requestPipeline.data = [existingError];

    act(() => {
      renderer = create(
        <RequestHarness
          options={{ skipRequestPipeline: true, onError, onSuccess }}
        />,
      );
    });
    act(() => capturedOptions.onError(pollingError));
    act(() => capturedOptions.onSuccess({ success: true }));

    expect(requestPipeline.data).toEqual([existingError]);
    expect(onError).toHaveBeenCalledWith(pollingError);
    expect(onSuccess).toHaveBeenCalledWith({ success: true });
  });

  it('preserves the existing shared pipeline behavior by default', () => {
    const error = { code: 'ERR_NETWORK' };
    const onError = jest.fn();

    act(() => {
      renderer = create(<RequestHarness options={{ onError }} />);
    });
    act(() => capturedOptions.onError(error));

    expect(requestPipeline.data).toEqual([error]);
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ errorPipeline: [error] }),
    );

    act(() => capturedOptions.onSuccess({ success: true }));
    expect(requestPipeline.data).toEqual([]);
  });
});
