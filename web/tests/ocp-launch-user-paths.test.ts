import {
  getConfiguredLaunchUser,
  getDeployUserAfterSshChange,
  getEffectiveOcpUser,
  getOcpUserPaths,
} from '../src/component/OCPConfigNew/helper';

describe('OCP runtime user paths', () => {
  test('uses the runtime user home for a non-root user', () => {
    expect(getOcpUserPaths('ocp')).toEqual({
      home_path: '/home/ocp',
      log_dir: '/home/ocp/logs',
      soft_dir: '/home/ocp/software',
    });
  });

  test('uses /root consistently for root', () => {
    expect(getOcpUserPaths('root')).toEqual({
      home_path: '/root',
      log_dir: '/root/logs',
      soft_dir: '/root/software',
    });
  });

  test('does not generate paths before a user is provided', () => {
    expect(getOcpUserPaths()).toBeUndefined();
  });
});

describe('OCP runtime user form state', () => {
  test('editing the SSH user does not replace the selected runtime user', () => {
    expect(getDeployUserAfterSshChange(true, 'ocp', 'root')).toBe('ocp');
  });

  test('editing the SSH user updates the deploy user by default', () => {
    expect(getDeployUserAfterSshChange(false, 'ocp', 'admin')).toBe('admin');
  });

  test('unchecking the option removes a previously configured launch_user', () => {
    expect(getConfiguredLaunchUser(false, 'ocp')).toBeUndefined();
  });

  test('checking the option submits launch_user', () => {
    expect(getConfiguredLaunchUser(true, 'ocp')).toBe('ocp');
  });
});

describe('OCP effective runtime user', () => {
  test('uses launch_user when running OCP as another user', () => {
    expect(getEffectiveOcpUser(true, 'ocp', 'root')).toBe('ocp');
  });

  test('uses the SSH login user by default', () => {
    expect(getEffectiveOcpUser(false, undefined, 'admin')).toBe('admin');
  });

  test('falls back to the stored deploy user while form data initializes', () => {
    expect(getEffectiveOcpUser(false, undefined, undefined, 'admin')).toBe(
      'admin',
    );
  });
});
