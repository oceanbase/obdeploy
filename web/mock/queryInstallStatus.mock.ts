// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments/:name/install': (req: Request, res: Response) => {
    res.status(200).send({
      code: 88,
      data: {
        total: 86,
        finished: 91,
        current: '标同有决心处听情式从温志切百石干。',
        status: 'success',
        msg: '起区院难门厂来书治结外说别过记质。',
        info: [],
      },
      msg: '也通统矿己厂这何志物特象子。',
      success: true,
    });
  },
};
