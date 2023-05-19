// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/deployments/:name/precheck': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 63,
        data: null,
        msg: '局风厂很物类面还队张土将。',
        success: true,
      });
  },
};
