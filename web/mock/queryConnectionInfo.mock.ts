// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments/:name/connection': (req: Request, res: Response) => {
    res.status(200).send({
      code: 98,
      data: {
        total: 75,
        items: [
          {
            component: '群直则于律清住用军温技其识们条型按。',
            access_url: 'https://procomponents.ant.design/',
            user: '心实立质业去京保查电话深。',
            password: 'string(16)',
            connect_url: 'https://preview.pro.ant.design/dashboard/analysis',
          },
          {
            component: '严没民道多员快受京积属广拉信命造。',
            access_url: 'https://procomponents.ant.design/',
            user: '两得农知类几队统风入具满查广。',
            password: 'string(16)',
            connect_url: 'https://ant.design',
          },
          {
            component: '根克作由因车正实论温具越。',
            access_url: 'https://github.com/umijs/dumi',
            user: '满研划高很前文入采打圆没最斗。',
            password: 'string(16)',
            connect_url: 'https://procomponents.ant.design/',
          },
        ],
      },
      msg: '深压该二报志月大习水器然日思。',
      success: true,
    });
  },
};
