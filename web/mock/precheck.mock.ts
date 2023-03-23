// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/deployments/:name/precheck': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 88,
        data: null,
        msg: '主四路复离些收素志标算才价具。',
        success: true,
      });
  },
};
