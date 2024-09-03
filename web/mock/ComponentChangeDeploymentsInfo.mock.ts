// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/component_change/deployment/detail': (
    req: Request,
    res: Response,
  ) => {
    res.status(200).send({
      code: 84,
      data: {
        component_list: [
          {
            component_name: 'ob-configserver',
            version: '',
            deployed: 0,
            node: '',
            component_info: [
              {
                estimated_size: 24259515,
                version: '1.0.0',
                type: 'remote',
                release: '2.el7',
                arch: 'x86_64',
                md5: '18687f6085f7a2f6c8a409d09912959589e0bdf0d2086fba1f0e2cebaec525cd',
                version_type: '',
              },
            ],
          },
          {
            component_name: 'prometheus',
            version: '',
            deployed: 1,
            node: '',
            component_info: [
              {
                estimated_size: 211224073,
                version: '2.37.1',
                type: 'remote',
                release: '10000102022110211.el7',
                arch: 'x86_64',
                md5: '39e4b09f16d6e3cae76382b2b176102ca001c52d451381eb2e5a50941c5d86f1',
                version_type: '',
              },
              {
                estimated_size: 211224073,
                version: '2.37.1',
                type: 'remote',
                release: '10000102022110211.el7',
                arch: 'x86_64',
                md5: '62d20b25430f0e5be7783ed5661bb42428ad61915150b7028b74e0468bfb8c4f',
                version_type: '',
              },
            ],
          },
          {
            component_name: 'grafana',
            version: '',
            deployed: 1,
            node: '',
            component_info: [
              {
                estimated_size: 177766248,
                version: '7.5.17',
                type: 'remote',
                release: '1',
                arch: 'x86_64',
                md5: 'f0c86571a2987ee6338a42b79bc1a38aebe2b07500d0120ee003aa7dd30973a5',
                version_type: '',
              },
              {
                estimated_size: 177766248,
                version: '7.5.17',
                type: 'remote',
                release: '1',
                arch: 'x86_64',
                md5: '9f81466722c5971fbad649a134f994fc1470dd4f76c360f744e2b06af559f6e5',
                version_type: '',
              },
            ],
          },
          {
            component_name: 'ocp-express',
            version: '',
            deployed: 0,
            node: '1.1.1.1',
            component_info: [
              {
                estimated_size: 78426196,
                version: '4.2.2',
                type: 'remote',
                release: '100000022024011120.el7',
                arch: 'x86_64',
                md5: '74a00bfb44909e81990a32ae0087180de6586816a917dcb49fab2b9082ca6e33',
                version_type: '',
              },
            ],
          },
          {
            component_name: 'obagent',
            version: '',
            deployed: 0,
            node: '',
            component_info: [
              {
                estimated_size: 72919140,
                version: '4.2.2',
                type: 'remote',
                release: '100000042024011120.el7',
                arch: 'x86_64',
                md5: '988b403da97f57801e05857122317ae8ea913853bb7bee7538ca6dcfcadc088a',
                version_type: '',
              },
            ],
          },
          {
            component_name: 'obproxy-ce',
            version: '',
            deployed: 0,
            node: '',
            component_info: [
              {
                estimated_size: 688373235,
                version: '4.2.3.0',
                type: 'remote',
                release: '3.el7',
                arch: 'x86_64',
                md5: '7ca6c000887b90db111093180e6984bf4cf8f7380a948870f3eb2ac30be38f37',
                version_type: '',
              },
              {
                estimated_size: 673773899,
                version: '4.2.0.0',
                type: 'remote',
                release: '7.el7',
                arch: 'x86_64',
                md5: 'da8953ed07a09b41d08140e865f108353b05914f8f774cdd40802ae6b8d3c14c',
                version_type: '',
              },
            ],
          },
        ],
      },
      msg: '数准才必持引市才以只定革等走容。',
      success: true,
    });
  },
};
