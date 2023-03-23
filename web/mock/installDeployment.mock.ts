// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/deployments/:name/install': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 67,
        data: null,
        msg: '根么高力林厂争由公就识非车。',
        success: true,
      });
  },
};
