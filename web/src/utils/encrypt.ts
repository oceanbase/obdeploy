import JSEncrypt from 'jsencrypt';
import { cloneDeep } from 'lodash';

export const encrypt = (text: string, publicKey: string): string | false => {
  const encrypt = new JSEncrypt();
  encrypt.setPublicKey(publicKey);
  return encrypt.encrypt(text);
};

/**
 * 预检查时通过config加密密码
 */
export const encryptPwdForConfig = (
  configData: API.DeploymentConfig,
  publicKey: string,
) => {
  const newConfigData = cloneDeep(configData);
  const { obagent, obproxy, oceanbase, ocpserver, ocpexpress } =
    newConfigData.components || newConfigData;
  if (newConfigData.auth?.password)
    newConfigData.auth.password =
      encrypt(newConfigData.auth.password, publicKey) ||
      newConfigData.auth.password;
  if (obagent?.parameters) {
    obagent?.parameters.forEach((param) => {
      if (param.key === 'http_basic_auth_password') {
        param.value = encrypt(param.value, publicKey) || param.value;
      }
    });
  }
  if (obproxy?.parameters) {
    obproxy?.parameters.forEach((param) => {
      if (param.key === 'obproxy_sys_password' && param.value) {
        param.value = encrypt(param.value, publicKey) || param.value;
      }
    });
  }
  if (oceanbase?.root_password) {
    oceanbase.root_password =
      encrypt(oceanbase.root_password, publicKey) || oceanbase.root_password;
  }
  if (ocpserver?.admin_password) {
    ocpserver.admin_password =
      encrypt(ocpserver.admin_password, publicKey) || ocpserver.admin_password;
  }
  if (ocpserver?.meta_tenant.password) {
    ocpserver.meta_tenant.password =
      encrypt(ocpserver.meta_tenant.password, publicKey) ||
      ocpserver.meta_tenant.password;
  }
  if (ocpserver?.monitor_tenant.password) {
    ocpserver.monitor_tenant.password =
      encrypt(ocpserver.monitor_tenant.password, publicKey) ||
      ocpserver.monitor_tenant.password;
  }
  if(ocpserver?.metadb?.password){
    ocpserver.metadb.password =  encrypt(ocpserver.metadb.password, publicKey) ||
    ocpserver.metadb.password;
  }
  if (ocpexpress?.admin_passwd) {
    ocpexpress.admin_passwd =
      encrypt(ocpexpress.admin_passwd, publicKey) || ocpexpress.admin_passwd;
  }
  if (obproxy?.obproxy_sys_password) {
    obproxy.obproxy_sys_password =
      encrypt(obproxy.obproxy_sys_password, publicKey) ||
      obproxy.obproxy_sys_password;
  }
  return newConfigData;
};
