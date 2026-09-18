export const getOcpUserPaths = (user?: string) => {
  if (!user) return undefined;
  const userHome = user === 'root' ? '/root' : `/home/${user}`;
  return {
    home_path: userHome,
    log_dir: `${userHome}/logs`,
    soft_dir: `${userHome}/software`,
  };
};

export const getDeployUserAfterSshChange = (
  useRuntimeUser: boolean,
  currentDeployUser: string | undefined,
  sshUser: string,
) => (useRuntimeUser ? currentDeployUser : sshUser);

export const getConfiguredLaunchUser = (
  useRuntimeUser: boolean,
  launchUser?: string,
) => (useRuntimeUser ? launchUser : undefined);

export const getEffectiveOcpUser = (
  useRuntimeUser: boolean,
  launchUser?: string,
  sshUser?: string,
  fallbackUser?: string,
) => (useRuntimeUser ? launchUser : sshUser || fallbackUser);
