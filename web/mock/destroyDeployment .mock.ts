// @ts-ignore
import { Request, Response } from 'express';

export default {
  'DELETE /api/v1/deployments/:name': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 92,
        data: null,
        msg: '光月便此应先与速资因变家接。',
        success: true,
      });
  },
};
